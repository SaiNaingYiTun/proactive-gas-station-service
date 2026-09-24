import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"

import cv2
import math
import queue
import re
import threading
import time
import uuid
from datetime import datetime

from backend import send_detection, send_entry_update, send_exit
from color_classification import estimate_vehicle_color_with_confidence
from config import (
    CAMERA_INDEX, COLOR_MIN_CONF, COLOR_MODEL_MIN_INTERVAL_SEC, COLOR_REQUIRED_HITS,
    COLOR_SINGLE_HIT_PROMOTION_MIN_CONF, DEBUG_COLOR, DEBUG_OCR_SAVE_INPUTS,
    DEBUG_OCR_VERBOSE, DETECTION_ROI, DISPLAY_SCALE, DRAW_DETECTION_ROIS,
    CAMERA_RECONNECT_DELAY_SEC, DETECTED_GRACE_SEC, ENABLE_MAKE_MODEL, EXIT_AFTER_SEC, EXIT_ARM_Y, EXIT_CROSS_Y,
    FILE_EOF_DRAIN_TIMEOUT_SEC,
    EXIT_MIN_TRACK_FRAMES, EXIT_TRACK_ROI, FRAME_H, FRAME_W,
    ATTRIBUTE_FALLBACK_SEC, MAKE_MODEL_MIN_CONF, MAKE_MODEL_MIN_INTERVAL_SEC, MIN_PLATE_AREA_PIXELS, MIN_PLATE_AREA_RATIO,
    ENTRY_DIRECTION_SPLIT_Y, VEHICLE_FRAME_EDGE_MARGIN,
    MIN_PLATE_BOX_H, MIN_PLATE_BOX_W, OCR_MIN_CONF, PLATE_LINE_SPLIT_RATIO, PLATE_NUMBER_ALLOWLIST,
    OCR_DRAIN_GRACE_SEC, OCR_MAX_JOBS_PER_TRACK, PLATE_CHANGE_MIN_CONF_GAIN,
    PLATE_TRACKER_CANDIDATES, PROVINCE_ALLOWLIST, SINGLE_READ_PROMOTION_MIN_CONF, TRACK_DISPLAY_MAX_AGE_SEC,
    TRACK_REASSOCIATE_IOU, VEHICLE_TRACK_GAP_SEC,
    VEHICLE_ENTRY_ROI, YOLO_EVERY_N, YOLO_VEHICLE_MIN_CONF, ENABLE_PROVINCE_OCR,
)
from detector import find_plate_yolo_candidates
from make_model_classifier import infer_make_model
from make_model_stabilizer import MakeModelStabilizer
from ocr import _is_thai_text, _normalize_thai_text, ocr_best
from plate_filter import is_plausible_plate_text, normalize_plate_text, plates_roughly_agree
from province_parser import match_province
from stabilizer import PlateStabilizer
from thai_plate_recognizer import recognize_thai_plate
from tracker import BurstTracker
from utils import normalize_plate_crop, put_label
from vehicle_detector import find_vehicle_tracks, reset_vehicle_tracker


# Mutable so the desktop app (app.py) can turn on plate-crop saving and pick
# a folder at runtime, without setting the DEBUG_OCR_SAVE_INPUTS env var
# (which always writes to ./debug_crops).
save_crops_enabled = False
save_crops_dir = "./debug_crops"


def set_crop_saving(enabled, directory=None):
    global save_crops_enabled, save_crops_dir
    save_crops_enabled = bool(enabled)
    if directory:
        save_crops_dir = directory


ocr_queue = queue.Queue(maxsize=8)

attributes_queue = queue.Queue(maxsize=16)
backend_queue = queue.Queue(maxsize=16)
sessions_lock = threading.Lock()
vehicle_sessions = {}

session_aliases = {}
stop_flag = False


def _new_session(track_id, now):
    return {
        "id": track_id,
        "tracker": BurstTracker(PLATE_TRACKER_CANDIDATES, MIN_PLATE_BOX_W, MIN_PLATE_BOX_H),
        "plate_stabilizer": PlateStabilizer(5, 2, 8, 0.85),
        "province_stabilizer": PlateStabilizer(5, 1, 8, 1.0),
        "make_model_stabilizer": MakeModelStabilizer(5, 2, 8),
        "plate": "", "province": "", "plate_conf": 0.0,
        "plate_hits": 0, "detected_logged": False, "detected_ready_at": None,
        "provisional_plate": "", "provisional_province": "", "provisional_conf": 0.0,
        "provisional_logged": False,
        "color": "unknown", "color_conf": 0.0,
        "color_scores": {}, "color_counts": {}, "color_logged": False,
        "last_color_debug": None, "last_color_attempt": 0.0, "color_job_pending": False,
        "make": "unknown", "model": "unknown", "mm_conf": 0.0, "last_make_attempt": 0.0,
        "make_logged": False, "make_job_pending": False,
        "box": None, "plate_box": None, "is_entering": None,
        "first_seen": now, "last_seen": now, "frames": 0,
        "exit_armed": False, "exit_crossed": False,
        "entry_sent": False, "exit_sent": False,
        "entry_event_id": None, "entry_make_sent": "unknown", "entry_skip_logged": False,
        "ocr_jobs_pending": 0, "ocr_jobs_submitted": 0,
    }


def _box_iou(first, second):
    """Return the overlap ratio for boxes expressed as (x, y, width, height)."""
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def _current_session_id(track_id):
    """Resolve an old ByteTrack ID to its current logical-session ID."""
    seen = set()
    while track_id in session_aliases and track_id not in seen:
        seen.add(track_id)
        track_id = session_aliases[track_id]
    return track_id


def _get_session(track_id, now, box=None):
    with sessions_lock:
        current_track_id = _current_session_id(track_id)
        session = vehicle_sessions.get(current_track_id)
        if session is not None:
            return session

        if box is not None:
            candidates = [
                (old_track_id, old_session)
                for old_track_id, old_session in vehicle_sessions.items()
                if now - old_session["last_seen"] <= VEHICLE_TRACK_GAP_SEC
                and old_session["box"] is not None
                and _box_iou(box, old_session["box"]) >= TRACK_REASSOCIATE_IOU
            ]
            if candidates:
                old_track_id, session = max(
                    candidates,
                    key=lambda item: _box_iou(box, item[1]["box"]),
                )
                del vehicle_sessions[old_track_id]
            
                session_aliases[old_track_id] = track_id
                for alias, target in list(session_aliases.items()):
                    if target == old_track_id:
                        session_aliases[alias] = track_id
                session["id"] = track_id
                vehicle_sessions[track_id] = session
                return session

        session = _new_session(track_id, now)
        vehicle_sessions[track_id] = session
        return session


def _vehicle_fully_framed(box, margin=VEHICLE_FRAME_EDGE_MARGIN):
    """Whether this vehicle's box sits clear of every frame edge.

    See VEHICLE_FRAME_EDGE_MARGIN in config.py for why a box touching the
    frame boundary means the crop is a fragment of the vehicle, not the whole
    thing."""
    x, y, w, h = box
    return x > margin and y > margin and x + w < FRAME_W - margin and y + h < FRAME_H - margin


def _classify_direction(box):
    """Guess whether a freshly-created session is entering from the road or
    already inside and now leaving, from where its box first sits within
    VEHICLE_ENTRY_ROI. See ENTRY_DIRECTION_SPLIT_Y in config.py."""
    _, y, _, h = box
    return y + h / 2 < ENTRY_DIRECTION_SPLIT_Y


def _attribute_ready(session, now):
    """Whether this session has enough information to be sent to the backend."""
    if session["is_entering"]:
        return True
    return (
        session["plate_box"] is not None
        or now - session["first_seen"] >= ATTRIBUTE_FALLBACK_SEC
    )


def _plate_vehicle_match(plate_box, vehicles):
    """Return the exact tracked vehicle that owns this plausible plate box."""
    px, py, pw, ph = plate_box
    center_x, center_y = px + pw / 2, py + ph / 2
    for vehicle in vehicles:
        vx, vy, vw, vh = vehicle["box"]
        margin_x, margin_y = max(12, int(vw * 0.10)), max(12, int(vh * 0.12))
        contains = vx - margin_x <= center_x <= vx + vw + margin_x and vy - margin_y <= center_y <= vy + vh + margin_y
        # A registration occupies only a small part of its vehicle.  The old
        # generous limits allowed a white roof or road marking inside a car's
        # bounding box to be sent to OCR as a "plate".
        small = pw <= vw * 0.40 and ph <= vh * 0.25 and pw * ph <= vw * vh * 0.08
        if contains and small:
            return vehicle
    return None


def _is_in_station_driveway(vehicle):
    """Only tracks whose centres enter the configured driveway may create sessions."""
    x, y, w, h = vehicle["box"]
    center_x, center_y = x + w / 2, y + h / 2
    x1, y1, x2, y2 = VEHICLE_ENTRY_ROI
    return x1 <= center_x <= x2 and y1 <= center_y <= y2


def _queue_entry_if_ready(session):
    """Send the backend an entry event once this session has a colour and plate."""
    if session["entry_sent"] or session["color_conf"] < COLOR_MIN_CONF:
        return
    if session["exit_armed"]:
        if not session["entry_skip_logged"]:
            session["entry_skip_logged"] = True
            print(
                f"[ENTRY-SKIPPED] track={session['id']} color={session['color']} "
                f"make={session['make']} box={session['box']} -- exit already armed "
                "(this vehicle passed through the exit corridor before its colour was "
                "confirmed), so no entry is sent",
                flush=True,
            )
        return
    event_id = str(uuid.uuid4())
    try:
        backend_queue.put_nowait({
            "type": "entry", "event_id": event_id, "track_id": session["id"],
            "plate": session["plate"], "conf": session["plate_conf"],
            "color": session["color"], "make": session["make"],
            "seen_at": session["first_seen"],
        })
        session["entry_sent"] = True
        session["entry_event_id"], session["entry_make_sent"] = event_id, session["make"]
    except queue.Full:
        pass


def _queue_entry_update_if_needed(session):
    """Send the backend an entry update if this session's make has changed."""
    if (
        not session["entry_sent"]
        or session["entry_make_sent"] != "unknown"
        or session["make"] == "unknown"
    ):
        return
    try:
        backend_queue.put_nowait({
            "type": "entry_update", "event_id": session["entry_event_id"], "track_id": session["id"],
            "color": session["color"], "make": session["make"],
        })
        session["entry_make_sent"] = session["make"]
    except queue.Full:
        pass


def _queue_exit_if_needed(session, reason, seen_at):
    """Send the backend an exit event once this session has a plate and hasn't already sent one."""
    if session["exit_sent"] or not session["plate"]:
        return
    try:
        backend_queue.put_nowait({
            "type": "exit", "event_id": str(uuid.uuid4()), "track_id": session["id"],
            "plate": session["plate"], "color": session["color"], "make": session["make"],
            "entry_event_id": session["entry_event_id"], "reason": reason,
            "seen_at": seen_at,
        })
        session["exit_sent"] = True
    except queue.Full:
        pass


def _has_pending_ocr_work():
    """Return whether any queued or running OCR job still needs the GPU."""
    with sessions_lock:
        return any(session["ocr_jobs_pending"] > 0 for session in vehicle_sessions.values())


def _pending_work_remaining():
    """Return whether any queued or running job still needs the GPU."""
    if not (ocr_queue.empty() and attributes_queue.empty() and backend_queue.empty()):
        return True
    with sessions_lock:
        return any(
            session["ocr_jobs_pending"] > 0 or session["color_job_pending"] or session["make_job_pending"]
            for session in vehicle_sessions.values()
        )


def _build_detected_message(session, track_id):
    return (
        f"[DETECTED] track={track_id} plate={session['plate']} "
        f"province={session['province']} conf={session['plate_conf']:.2f} "
        f"hits={session['plate_hits']} color={session['color']} "
        f"color_conf={session['color_conf']:.2f} make={session['make']} "
        f"mm_conf={session['mm_conf']:.2f}"
    )


def _mark_detected_ready(session, now):
    """Mark this session as ready to print a [DETECTED] line once its make/model has resolved or DETECTED_GRACE_SEC has elapsed.  Must be called while
    holding sessions_lock."""
    if (
        session["detected_ready_at"] is None
        and session["plate"]
        and session["color_conf"] >= COLOR_MIN_CONF
    ):
        session["detected_ready_at"] = now


def _detected_message_if_ready(session, track_id, now):
    """Return the [DETECTED] line once ready, holding it for up to
    DETECTED_GRACE_SEC to give make/model a chance to resolve first.  Must be
    called while holding sessions_lock."""
    if session["detected_logged"] or session["detected_ready_at"] is None:
        return None
    make_resolved = session["mm_conf"] >= MAKE_MODEL_MIN_CONF
    grace_elapsed = now - session["detected_ready_at"] >= DETECTED_GRACE_SEC
    if not (make_resolved or grace_elapsed):
        return None
    session["detected_logged"] = True
    return _build_detected_message(session, track_id)


def _apply_color_result(session, track_id, color, color_conf, now):
    """Fold one colour attempt's result into the session.  Must be called
    while holding sessions_lock.  Returns any message(s) to print, or None."""
    if color_conf < COLOR_MIN_CONF:
        return None
    session["color_scores"][color] = session["color_scores"].get(color, 0.0) + color_conf
    session["color_counts"][color] = session["color_counts"].get(color, 0) + 1
    best = max(session["color_scores"], key=session["color_scores"].get)
    hits = session["color_counts"][best]
    best_conf = session["color_scores"][best] / hits
    # A single read this confident is trusted immediately rather than
    # waiting on a second agreeing one -- see COLOR_SINGLE_HIT_PROMOTION_MIN_CONF.
    single_hit_promoted = hits == 1 and best_conf >= COLOR_SINGLE_HIT_PROMOTION_MIN_CONF
    if hits < COLOR_REQUIRED_HITS and not single_hit_promoted:
        return None
    session["color"] = best
    session["color_conf"] = best_conf
    _queue_entry_if_ready(session)
    message = None
    if not session["color_logged"]:
        session["color_logged"] = True
        tag = " (single read)" if single_hit_promoted else ""
        message = (
            f"[COLOR] track={track_id} color={best} "
            f"color_conf={session['color_conf']:.2f}{tag} "
            f"plate={session['plate'] or '<pending>'}"
        )
    _mark_detected_ready(session, now)
    if DEBUG_COLOR and session["last_color_debug"] != best:
        session["last_color_debug"] = best
        debug_message = f"[VEHICLE] track={track_id} color={best} conf={session['color_conf']:.2f}"
        message = f"{message}\n{debug_message}" if message else debug_message
    return message


def _apply_make_result(session, track_id, make, mm_model, mm_conf, now):
    """Fold one make/model attempt's result into the session.  Must be
    called while holding sessions_lock.  Returns a message to print, or
    None."""
    if mm_conf < MAKE_MODEL_MIN_CONF:
        return None
    result = session["make_model_stabilizer"].offer(make, mm_model, mm_conf, now)
    if not result:
        return None
    session["make"], session["model"], session["mm_conf"] = result["make"], result["model"], result["conf"]
    _queue_entry_update_if_needed(session)
    if session["make_logged"]:
        return None
    session["make_logged"] = True
    return f"[MAKE] track={track_id} make={session['make']} mm_conf={session['mm_conf']:.2f} hits={result['hits']}"


def attributes_worker():
    
    while not stop_flag:
        try:
            job = attributes_queue.get(timeout=1)
        except queue.Empty:
            continue
        track_id, crop, job_type = job["track_id"], job["crop"], job["type"]
        pending_key = "color_job_pending" if job_type == "color" else "make_job_pending"
        try:
            if crop is None or crop.size == 0:
                continue
            # OCR priority can still matter by the time this job is actually
            # popped, even though the caller checked it before enqueueing.
            if _has_pending_ocr_work():
                continue
            now = time.time()
            message = None
            if job_type == "color":
                try:
                    color, color_conf = estimate_vehicle_color_with_confidence(crop)
                except Exception as error:
                    color, color_conf = "unknown", 0.0
                    print(f"[COLOR] track={track_id} skipped: {error}", flush=True)
                with sessions_lock:
                    session = vehicle_sessions.get(_current_session_id(track_id))
                    if session is not None:
                        message = _apply_color_result(session, track_id, color, color_conf, now)
            else:
                try:
                    make, mm_model, mm_conf = infer_make_model(crop, track_id=track_id)
                except Exception as error:
                    make, mm_model, mm_conf = "unknown", "unknown", 0.0
                    print(f"[MAKE] track={track_id} skipped: {error}", flush=True)
                with sessions_lock:
                    session = vehicle_sessions.get(_current_session_id(track_id))
                    if session is not None:
                        message = _apply_make_result(session, track_id, make, mm_model, mm_conf, now)
            if message:
                print(message, flush=True)
        finally:
            with sessions_lock:
                session = vehicle_sessions.get(_current_session_id(track_id))
                if session is not None:
                    session[pending_key] = False


def backend_worker():
    while not stop_flag:
        try:
            job = backend_queue.get(timeout=1)
        except queue.Empty:
            continue
        if job["type"] == "entry":
            response = send_detection(
                job["event_id"], job["plate"], job["conf"], job["color"], job["make"], job["seen_at"]
            )
            if response:
                tag = "NEW" if response.get("is_new_visit") else "seen again"
                print(f"[{tag}] track={job['track_id']} plate={job['plate'] or '<none yet>'} color={job['color']}", flush=True)
        elif job["type"] == "entry_update":
            response = send_entry_update(job["event_id"], job["color"], job["make"])
            if response:
                print(f"[ENTRY-UPDATE] track={job['track_id']} make={job['make']} -> {response.get('status')}", flush=True)
        elif job["type"] == "exit" and send_exit(
            job["event_id"], job["plate"], job["color"], job["make"], job.get("entry_event_id"), job["seen_at"]
        ):
            print(f"[EXIT] track={job['track_id']} plate={job['plate']} reason={job['reason']}", flush=True)


def ocr_worker():
    while not stop_flag:
        try:
            job = ocr_queue.get(timeout=1)
        except queue.Empty:
            continue
        track_id, crop = job["track_id"], job["crop"]
        try:
            if crop is None or crop.size == 0:
                continue
            if DEBUG_OCR_SAVE_INPUTS or save_crops_enabled:
                target_dir = save_crops_dir if save_crops_enabled else "./debug_crops"
                os.makedirs(target_dir, exist_ok=True)
                cv2.imwrite(os.path.join(target_dir, f"ocr_input_{track_id}_{time.time():.0f}.jpg"), crop)
            split = int(crop.shape[0] * PLATE_LINE_SPLIT_RATIO)
            if split <= 0 or split >= crop.shape[0]:
                continue
            trained_result = recognize_thai_plate(crop)
            char_plate = normalize_plate_text(trained_result["plate"])
            char_conf = trained_result["confidence"]
            province_raw, province_conf = (
                trained_result["province_code"],
                trained_result["province_confidence"],
            )
            province_from_model = bool(province_raw)
            
            easy_plate, easy_conf = ocr_best(crop[:split, :], PLATE_NUMBER_ALLOWLIST)
            easy_plate = normalize_plate_text(easy_plate)
            char_ok = char_plate and char_conf >= OCR_MIN_CONF and is_plausible_plate_text(char_plate)
            easy_ok = easy_plate and easy_conf >= OCR_MIN_CONF and is_plausible_plate_text(easy_plate)
            if not char_ok and not easy_ok:
                
                alternate = normalize_plate_crop(crop[:split, :], target_w=1400)
                candidates = []
                if alternate is not None:
                    alt_plate, alt_conf = ocr_best(alternate, PLATE_NUMBER_ALLOWLIST, threshold=0.20)
                    alt_plate = normalize_plate_text(alt_plate)
                    if is_plausible_plate_text(alt_plate):
                        candidates = [(alt_plate, alt_conf)]
                agree = True  
            elif char_ok and easy_ok:
                agree = plates_roughly_agree(char_plate, easy_plate)
                candidates = [(char_plate, char_conf), (easy_plate, easy_conf)]
            else:
                candidates = [(char_plate, char_conf)] if char_ok else [(easy_plate, easy_conf)]
                agree = True  
            if ENABLE_PROVINCE_OCR and not province_from_model:
                province_raw, province_conf = ocr_best(
                    crop[split:, :],
                    PROVINCE_ALLOWLIST,
                    normalizer=_normalize_thai_text,
                    validator=_is_thai_text,
                )
        except (cv2.error, ValueError, OverflowError) as error:
            if DEBUG_OCR_VERBOSE:
                print(f"[OCR] track={track_id} skipped: {error}", flush=True)
            continue
        finally:
            with sessions_lock:
                session_id = _current_session_id(track_id)
                if session_id in vehicle_sessions:
                    session = vehicle_sessions[session_id]
                    session["ocr_jobs_pending"] = max(0, session["ocr_jobs_pending"] - 1)

        if not candidates and DEBUG_OCR_VERBOSE:
            print(f"[OCR] track={track_id} rejected: neither engine produced a usable read", flush=True)
        
        province = province_raw if province_from_model else match_province(province_raw)
        now = time.time()
        with sessions_lock:
            session = vehicle_sessions.get(_current_session_id(track_id))
            if session is None:
                continue
            if province:
                hit = session["province_stabilizer"].offer(province, province_conf, province, now)
                if hit:
                    province = hit["text"]
            
            for plate, conf in candidates:
                if agree and (
                    conf > session["provisional_conf"]
                    or (
                        conf == session["provisional_conf"]
                        and len(plate) > len(session["provisional_plate"])
                    )
                ):
                    session["provisional_plate"] = plate
                    session["provisional_province"] = province
                    session["provisional_conf"] = conf
                stable = session["plate_stabilizer"].offer(plate, conf, province, now)
                if stable is None:
                    if DEBUG_OCR_VERBOSE:
                        print(
                            f"[OCR] track={track_id} candidate={plate} conf={conf:.2f} "
                            "waiting for matching read (1/2)",
                            flush=True,
                        )
                    continue
                if (
                    session["plate"]
                    and stable["text"] != session["plate"]
                    and (
                        session["entry_sent"]
                        or stable["conf"] < session["plate_conf"] + PLATE_CHANGE_MIN_CONF_GAIN
                    )
                ):
                    if DEBUG_OCR_VERBOSE:
                        print(
                            f"[OCR] track={track_id} kept plate={session['plate']} "
                            f"instead of conflicting read={stable['text']} "
                            f"(conf={stable['conf']:.2f})",
                            flush=True,
                        )
                    continue
                session["plate"], session["province"], session["plate_conf"] = stable["text"], stable["province"], stable["conf"]
                session["plate_hits"] = stable["hits"]
                _queue_entry_if_ready(session)
                _mark_detected_ready(session, now)


def _update_vehicle_session(vehicle, frame, now):
    track_id = vehicle["id"]
    vx, vy, vw, vh = vehicle["box"]
    center_x, center_y = vx + vw / 2, vy + vh / 2
    session = _get_session(track_id, now, vehicle["box"])
    with sessions_lock:
        if session["is_entering"] is None:
            session["is_entering"] = _classify_direction(vehicle["box"])
        session["box"], session["last_seen"], session["frames"] = vehicle["box"], now, session["frames"] + 1
        session_frame_count = session["frames"]

    crop = frame[max(0, vy):min(frame.shape[0], vy + vh), max(0, vx):min(frame.shape[1], vx + vw)]
    if crop.size == 0:
        return
    
    ocr_busy = _has_pending_ocr_work()
    with sessions_lock:
        color_is_stable = session["color_conf"] >= COLOR_MIN_CONF
        color_due = now - session["last_color_attempt"] >= COLOR_MODEL_MIN_INTERVAL_SEC
        make_is_stable = session["mm_conf"] >= MAKE_MODEL_MIN_CONF
        make_due = now - session["last_make_attempt"] >= MAKE_MODEL_MIN_INTERVAL_SEC
        if (
            not color_is_stable
            and not session["color_job_pending"]
            and color_due
            and not ocr_busy
            and _attribute_ready(session, now)
        ):
            session["last_color_attempt"] = now
            session["color_job_pending"] = True
            try:
                attributes_queue.put_nowait({"type": "color", "track_id": track_id, "crop": crop.copy()})
            except queue.Full:
                session["color_job_pending"] = False
        if (
            ENABLE_MAKE_MODEL
            and not make_is_stable
            and not session["make_job_pending"]
            and make_due
            and not ocr_busy
            and _attribute_ready(session, now)
            and _vehicle_fully_framed(vehicle["box"])
        ):
            session["last_make_attempt"] = now
            session["make_job_pending"] = True
            try:
                attributes_queue.put_nowait({"type": "make", "track_id": track_id, "crop": crop.copy()})
            except queue.Full:
                session["make_job_pending"] = False

    ex1, ey1, ex2, ey2 = EXIT_TRACK_ROI
    in_exit_track_roi = ex1 <= center_x <= ex2 and ey1 <= center_y <= ey2
    detected_message = None
    with sessions_lock:
        
        detected_message = _detected_message_if_ready(session, track_id, now)
        if in_exit_track_roi and center_y >= EXIT_ARM_Y:
            session["exit_armed"] = True
        crossed = in_exit_track_roi and session["exit_armed"] and not session["exit_crossed"] and session["frames"] >= EXIT_MIN_TRACK_FRAMES and center_y <= EXIT_CROSS_Y
        if crossed:
            session["exit_crossed"] = True
            _queue_entry_if_ready(session)
            _queue_exit_if_needed(session, "crossed_exit_line", now)
            print(f"[EXIT-VEHICLE] track={track_id} color={session['color']} confidence={session['color_conf']:.2f} frames={session['frames']}", flush=True)
    if detected_message:
        print(detected_message, flush=True)


def _retire_missing_sessions(now):
    with sessions_lock:
        timeout = max(EXIT_AFTER_SEC, VEHICLE_TRACK_GAP_SEC)
        stale_ids = [
            track_id
            for track_id, session in vehicle_sessions.items()
            if now - session["last_seen"] > timeout
            and not (
                session["ocr_jobs_pending"] > 0
                and now - session["last_seen"] <= timeout + OCR_DRAIN_GRACE_SEC
            )
        ]
        for track_id in stale_ids:
            session = vehicle_sessions[track_id]
            if (
                not session["plate"]
                and session["provisional_plate"]
                and session["provisional_conf"] >= SINGLE_READ_PROMOTION_MIN_CONF
            ):
                
                session["plate"] = session["provisional_plate"]
                session["province"] = session["provisional_province"]
                session["plate_conf"] = session["provisional_conf"]
                session["plate_hits"] = max(session["plate_hits"], 1)
                session["provisional_logged"] = True
                print(
                    f"[SINGLE-READ] track={track_id} plate={session['plate']} "
                    f"province={session['province']} conf={session['plate_conf']:.2f} "
                    "promoted without a second confirming read",
                    flush=True,
                )
                _queue_entry_if_ready(session)
                _mark_detected_ready(session, now)
            if not session["detected_logged"] and session["detected_ready_at"] is not None:
                
                session["detected_logged"] = True
                print(_build_detected_message(session, track_id), flush=True)
            elif (
                not session["detected_logged"]
                and not session["provisional_logged"]
                and session["provisional_plate"]
            ):
                
                session["provisional_logged"] = True
                print(
                    f"[PROVISIONAL] track={track_id} "
                    f"plate={session['provisional_plate']} "
                    f"province={session['provisional_province']} "
                    f"conf={session['provisional_conf']:.2f} "
                    f"color={session['color']} color_conf={session['color_conf']:.2f}",
                    flush=True,
                )
            
            _queue_exit_if_needed(session, "track_disappeared", session["last_seen"])
            del vehicle_sessions[track_id]
        for old_track_id in list(session_aliases):
            if _current_session_id(old_track_id) not in vehicle_sessions:
                del session_aliases[old_track_id]


def _crop_native(native_frame, x1, y1, x2, y2):
    """Cut a box given in FRAME_W x FRAME_H coordinates out of the full-resolution frame."""
    native_h, native_w = native_frame.shape[:2]
    scale_x, scale_y = native_w / FRAME_W, native_h / FRAME_H
    return native_frame[
        int(y1 * scale_y):int(math.ceil(y2 * scale_y)),
        int(x1 * scale_x):int(math.ceil(x2 * scale_x)),
    ]


def _open_capture(source=None):
    cap = cv2.VideoCapture(CAMERA_INDEX if source is None else source, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _redact_credentials(url):
    """Hide user:password in a stream URL before it is printed or shown."""
    return re.sub(r"(://[^/:@\s]+):[^@/\s]*@", r"\1:***@", str(url))


def _reset_run_state():
    """Start every run from a clean slate: a second run from the desktop app
    must not inherit the previous run's vehicles, queued jobs or track IDs."""
    with sessions_lock:
        vehicle_sessions.clear()
        session_aliases.clear()
    for pending in (ocr_queue, attributes_queue, backend_queue):
        while True:
            try:
                pending.get_nowait()
            except queue.Empty:
                break
    reset_vehicle_tracker()


def run_live(source=None, on_frame=None, should_stop=None):
    """Run detection on ``source`` (default: the configured camera).

    With no arguments this is the original OpenCV-window loop.  The desktop app
    (app.py) instead passes ``on_frame`` -- called with each annotated frame in
    place of the window -- and ``should_stop`` -- polled every frame.  A video
    file ends the run when it finishes; a live stream reconnects."""
    global stop_flag
    source = CAMERA_INDEX if source is None else source
    use_window = on_frame is None
    is_file = os.path.isfile(str(source))

    def stopping():
        return stop_flag or (should_stop is not None and should_stop())

    cap = _open_capture(source)
    if not cap.isOpened():
        print(f"Cannot open camera: {_redact_credentials(source)}", flush=True)
        return
    stop_flag = False
    _reset_run_state()
    if use_window:
        cv2.namedWindow("Gas Station LPR", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Gas Station LPR", int(FRAME_W * DISPLAY_SCALE), int(FRAME_H * DISPLAY_SCALE))
    workers = [
        threading.Thread(target=worker, daemon=True)
        for worker in (ocr_worker, attributes_worker, backend_worker)
    ]
    for worker in workers:
        worker.start()
    frame_count, fps_count, fps, last_fps_at, last_plate_box = 0, 0, 0.0, time.time(), None
    
    frame_interval = 0.0
    next_frame_due = time.time()
    if is_file:
        native_fps = cap.get(cv2.CAP_PROP_FPS)
        if not native_fps or native_fps <= 0:
            native_fps = 25.0        
        frame_interval = 1.0 / native_fps
    hit_eof = False
    print(
        "Live detection started." + (" Press 'q' to quit | 's' to screenshot" if use_window else ""),
        flush=True,
    )

    while not stopping():
        ret, frame = cap.read()
        if not ret:
            if is_file:
                print("End of video file.", flush=True)
                hit_eof = True
                break
            print("Lost camera feed, attempting to reconnect...", flush=True)
            cap.release()
            attempt = 0
            while not stopping():
                attempt += 1
                time.sleep(CAMERA_RECONNECT_DELAY_SEC)
                cap = _open_capture(source)
                if cap.isOpened():
                    print(f"Reconnected after {attempt} attempt(s).", flush=True)
                    break
                print(f"Reconnect attempt {attempt} failed, retrying...", flush=True)
            if stopping():
                break
            continue
        
        native_frame = frame
        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        frame_count, fps_count, now = frame_count + 1, fps_count + 1, time.time()
        if now - last_fps_at >= 1:
            fps, fps_count, last_fps_at = fps_count / (now - last_fps_at), 0, now

        vehicles, box, box_conf = [], None, 0.0
        if frame_count % YOLO_EVERY_N == 0:
            vehicles = find_vehicle_tracks(frame, min_conf=YOLO_VEHICLE_MIN_CONF)
            vehicles = [vehicle for vehicle in vehicles if _is_in_station_driveway(vehicle)]
            x1, y1, x2, y2 = DETECTION_ROI
            plate_candidates = find_plate_yolo_candidates(frame[y1:y2, x1:x2])
            
            for candidate_box, candidate_conf in plate_candidates:
                candidate_box = (
                    candidate_box[0] + x1,
                    candidate_box[1] + y1,
                    candidate_box[2],
                    candidate_box[3],
                )
                if _plate_vehicle_match(candidate_box, vehicles):
                    box, box_conf = candidate_box, candidate_conf
                    break
        
        last_plate_box = None
        if box:
            x, y, w, h = box
            roi_area = max(1, (DETECTION_ROI[2] - DETECTION_ROI[0]) * (DETECTION_ROI[3] - DETECTION_ROI[1]))
            vehicle = _plate_vehicle_match(box, vehicles)
            valid = vehicle and w >= MIN_PLATE_BOX_W and h >= MIN_PLATE_BOX_H and w * h >= max(MIN_PLATE_AREA_PIXELS, roi_area * MIN_PLATE_AREA_RATIO)
            if valid:
                track_id, session = vehicle["id"], _get_session(vehicle["id"], now)
                pad_x, pad_y = max(2, int(w * 0.10)), max(2, int(h * 0.16))
                crop = _crop_native(
                    native_frame,
                    max(0, x - pad_x), max(0, y - pad_y),
                    min(FRAME_W, x + w + pad_x), min(FRAME_H, y + h + pad_y),
                )
                with sessions_lock:
                    session["plate_box"] = box
                    session["tracker"].offer(frame[y:y + h, x:x + w], crop, box_conf)
                    if (
                        session["tracker"].ready()
                        and session["ocr_jobs_submitted"] < OCR_MAX_JOBS_PER_TRACK
                    ):
                        best_crop = session["tracker"].best_crop
                        if best_crop is not None and best_crop.size:
                            try:
                                ocr_queue.put_nowait({"track_id": track_id, "crop": best_crop.copy()})
                                session["ocr_jobs_pending"] += 1
                                session["ocr_jobs_submitted"] += 1
                                session["tracker"].reset()
                            except queue.Full:
                                pass
                last_plate_box = box

        
        for vehicle in vehicles:
            _update_vehicle_session(vehicle, frame, now)
        _retire_missing_sessions(now)

        if DRAW_DETECTION_ROIS:
            x1, y1, x2, y2 = DETECTION_ROI
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 160, 0), 1)
            x1, y1, x2, y2 = VEHICLE_ENTRY_ROI
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
        with sessions_lock:
            display_sessions = [
                session for session in vehicle_sessions.values()
                if now - session["last_seen"] <= TRACK_DISPLAY_MAX_AGE_SEC
            ]
        for session in display_sessions:
            if session["box"]:
                x, y, w, h = session["box"]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
                put_label(frame, f"#{session['id']} {session['plate'] or 'reading'} | {session['color']}", (x, max(18, y - 7)))
        if last_plate_box:
            x, y, w, h = last_plate_box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, f"FPS:{fps:.1f}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        if is_file:
            next_frame_due += frame_interval
            delay = next_frame_due - time.time()
            if delay > 0:
                time.sleep(delay)
            else:
                next_frame_due = time.time()   
        if on_frame is not None:
            on_frame(frame)
            continue
        cv2.imshow("Gas Station LPR", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            stop_flag = True
            break
        if key == ord("s"):
            filename = f"screenshot_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved {filename}", flush=True)
    
    if hit_eof and _pending_work_remaining():
        print("Finishing in-progress detections...", flush=True)
        deadline = time.time() + FILE_EOF_DRAIN_TIMEOUT_SEC
        while _pending_work_remaining() and time.time() < deadline and not stopping():
            time.sleep(0.2)
    
    stop_flag = True
    cap.release()
    for worker in workers:
        worker.join(timeout=10)
    if use_window:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    run_live()
