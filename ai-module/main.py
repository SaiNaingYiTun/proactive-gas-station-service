import os

# TCP blocks and waits for retransmission on any lost packet -- fine on a
# solid link, but per-stage timing measurements showed camera reads (not any
# AI processing) causing every FPS dip, up to several seconds each.  UDP
# just drops/corrupts the affected frame instead of blocking -- an
# occasional glitchy frame is a much better failure mode here than freezing
# the app, especially since the pipeline already discards low-confidence/
# implausible reads regardless.  Revert to "rtsp_transport;tcp" if corrupted
# frames prove more disruptive than the stalls were.
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"

import cv2
import queue
import threading
import time
import uuid
from datetime import datetime

from backend import send_detection, send_exit
from color_classification import estimate_vehicle_color_with_confidence
from config import (
    CAMERA_INDEX, COLOR_MIN_CONF, COLOR_MODEL_MIN_INTERVAL_SEC, COLOR_REQUIRED_HITS, DEBUG_COLOR, DEBUG_OCR_SAVE_INPUTS,
    DEBUG_OCR_VERBOSE, DETECTION_ROI, DISPLAY_SCALE, DRAW_DETECTION_ROIS,
    CAMERA_RECONNECT_DELAY_SEC, DETECTED_GRACE_SEC, ENABLE_MAKE_MODEL, EXIT_AFTER_SEC, EXIT_ARM_Y, EXIT_CROSS_Y,
    EXIT_MIN_TRACK_FRAMES, EXIT_TRACK_ROI, FRAME_H, FRAME_W,
    MAKE_MODEL_MIN_CONF, MAKE_MODEL_MIN_INTERVAL_SEC, MIN_PLATE_AREA_PIXELS, MIN_PLATE_AREA_RATIO,
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
from plate_filter import is_plausible_plate_text, normalize_plate_text
from province_parser import match_province
from stabilizer import PlateStabilizer
from thai_plate_recognizer import recognize_thai_plate
from tracker import BurstTracker
from utils import normalize_plate_crop
from vehicle_detector import find_vehicle_tracks


# Every OCR job carries the owning ByteTrack ID, preventing cross-car updates.
ocr_queue = queue.Queue(maxsize=8)
# Colour and make/model both used to run as direct GPU calls inside the main
# video-loop thread, gated only by a throttle interval + "OCR not busy right
# now" check.  Whenever that interval elapsed for one or more currently
# visible vehicles, the main loop blocked on those calls before it could
# read the next camera frame -- a periodic FPS dip independent of which
# model was loaded, since it was a threading issue, not a model-quality
# one.  Both now run on their own background thread instead, exactly like
# OCR already does.
attributes_queue = queue.Queue(maxsize=16)
backend_queue = queue.Queue(maxsize=16)
sessions_lock = threading.Lock()
vehicle_sessions = {}
# Maps replaced ByteTrack IDs to the current session key. OCR runs in another
# thread, so its job can still refer to an ID that ByteTrack just replaced.
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
        "box": None, "plate_box": None, "last_seen": now, "frames": 0,
        "exit_armed": False, "exit_crossed": False,
        "entry_sent": False, "exit_sent": False,
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

        # A tracker ID can change while the same large vehicle is partially
        # occluded or its box changes shape.  Reuse the old logical session so
        # it cannot produce duplicate OCR, entry, or exit events.
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
                # Keep queued OCR jobs for the old ID connected to this
                # session after its ByteTrack ID is replaced.
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
    """An entry is sent once colour is confident. Plate is intentionally not
    required here -- this camera's entry view usually doesn't show it at
    all, so the backend instead matches this entry to its eventual exit by
    colour/make. Skip a session that is already armed to exit: a vehicle
    re-tracked under a new ID while actually leaving would otherwise also
    pass the colour check and be logged as a second, bogus entry for a
    vehicle that is already inside."""
    if (
        session["entry_sent"]
        or session["color_conf"] < COLOR_MIN_CONF
        or session["exit_armed"]
    ):
        return
    try:
        backend_queue.put_nowait({
            "type": "entry", "event_id": str(uuid.uuid4()), "track_id": session["id"],
            "plate": session["plate"], "conf": session["plate_conf"],
            "color": session["color"], "make": session["make"],
        })
        session["entry_sent"] = True
    except queue.Full:
        pass


def _queue_exit_if_needed(session, reason):
    """An exit is sent once this session has a plate, regardless of whether
    this same session ever sent its own entry. A vehicle that entered
    off-camera-view of the plate (see _queue_entry_if_ready) and is only
    re-tracked once it reaches the exit corridor never has entry_sent=True
    locally -- the backend still matches it to its real, earlier entry by
    colour/make, so this session does not need to have "seen" that entry
    itself."""
    if session["exit_sent"] or not session["plate"]:
        return
    try:
        backend_queue.put_nowait({
            "type": "exit", "event_id": str(uuid.uuid4()), "track_id": session["id"],
            "plate": session["plate"], "color": session["color"], "make": session["make"],
            "reason": reason,
        })
        session["exit_sent"] = True
    except queue.Full:
        pass


def _has_pending_ocr_work():
    """Return whether any queued or running OCR job still needs the GPU."""
    with sessions_lock:
        return any(session["ocr_jobs_pending"] > 0 for session in vehicle_sessions.values())


def _build_detected_message(session, track_id):
    return (
        f"[DETECTED] track={track_id} plate={session['plate']} "
        f"province={session['province']} conf={session['plate_conf']:.2f} "
        f"hits={session['plate_hits']} color={session['color']} "
        f"color_conf={session['color_conf']:.2f} make={session['make']} "
        f"mm_conf={session['mm_conf']:.2f}"
    )


def _mark_detected_ready(session, now):
    """Record the moment plate+colour both first became available.

    The [DETECTED] print itself is deferred (see _detected_message_if_ready)
    rather than fired here, so a make/model result that resolves moments
    later on its own throttled schedule has a bounded chance to land in the
    same summary line instead of that line always showing "unknown".  This
    never delays the backend entry event -- _queue_entry_if_ready already
    fires independently of this bookkeeping.
    """
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
    if session["color_counts"][best] < COLOR_REQUIRED_HITS:
        return None
    session["color"] = best
    session["color_conf"] = session["color_scores"][best] / session["color_counts"][best]
    _queue_entry_if_ready(session)
    message = None
    if not session["color_logged"]:
        session["color_logged"] = True
        message = (
            f"[COLOR] track={track_id} color={best} "
            f"color_conf={session['color_conf']:.2f} "
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
    if session["make_logged"]:
        return None
    session["make_logged"] = True
    return f"[MAKE] track={track_id} make={session['make']} mm_conf={session['mm_conf']:.2f} hits={result['hits']}"


def attributes_worker():
    """Run colour and make/model inference off the main video-loop thread.

    Both used to run as direct synchronous GPU calls inside
    _update_vehicle_session; this drains a queue of {type, track_id, crop}
    jobs instead, so the main loop only ever has to enqueue (cheap) rather
    than wait for a classifier forward pass before it can read the next
    frame.
    """
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
            response = send_detection(job["event_id"], job["plate"], job["conf"], job["color"], job["make"])
            if response:
                tag = "NEW" if response.get("is_new_visit") else "seen again"
                print(f"[{tag}] track={job['track_id']} plate={job['plate'] or '<none yet>'} color={job['color']}", flush=True)
        elif job["type"] == "exit" and send_exit(job["event_id"], job["plate"], job["color"], job["make"]):
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
            if DEBUG_OCR_SAVE_INPUTS:
                os.makedirs("./debug_crops", exist_ok=True)
                cv2.imwrite(f"./debug_crops/ocr_input_{track_id}_{time.time():.0f}.jpg", crop)
            split = int(crop.shape[0] * PLATE_LINE_SPLIT_RATIO)
            if split <= 0 or split >= crop.shape[0]:
                continue
            trained_result = recognize_thai_plate(crop)
            plate, conf = trained_result["plate"], trained_result["confidence"]
            province_raw, province_conf = (
                trained_result["province_code"],
                trained_result["province_confidence"],
            )
            province_from_model = bool(province_raw)
            primary_plate, primary_conf = plate, conf
            if not plate or conf < OCR_MIN_CONF:
                plate, conf = ocr_best(crop[:split, :], PLATE_NUMBER_ALLOWLIST)
                primary_plate, primary_conf = plate, conf
            if not plate or conf < OCR_MIN_CONF:
                alternate = normalize_plate_crop(crop[:split, :], target_w=1400)
                if alternate is not None:
                    alternate_plate, alternate_conf = ocr_best(
                        alternate,
                        PLATE_NUMBER_ALLOWLIST,
                        threshold=0.20,
                    )
                    # Never let a noisy fallback replace a plate that already
                    # has a valid registration shape.  Use it only when it is
                    # valid and improves on the primary OCR result.
                    if is_plausible_plate_text(alternate_plate) and (
                        not is_plausible_plate_text(primary_plate)
                        or alternate_conf > primary_conf
                    ):
                        plate, conf = alternate_plate, alternate_conf
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

        plate = normalize_plate_text(plate)
        # Province codes come from the trained model and are review hints, not
        # an automatic final decision.  EasyOCR text still uses fuzzy matching.
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
            if not (plate and conf >= OCR_MIN_CONF and is_plausible_plate_text(plate)):
                if DEBUG_OCR_VERBOSE:
                    print(f"[OCR] track={track_id} rejected text={plate!r} conf={conf:.2f}", flush=True)
                continue
            if (
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
        session["box"], session["last_seen"], session["frames"] = vehicle["box"], now, session["frames"] + 1
        session_frame_count = session["frames"]

    crop = frame[max(0, vy):min(frame.shape[0], vy + vh), max(0, vx):min(frame.shape[1], vx + vw)]
    if crop.size == 0:
        return
    # Colour and make/model are auxiliary metadata, handled identically:
    # each is enqueued for the background attributes_worker thread rather
    # than run inline here, so a classifier forward pass can never block
    # this frame's read of the next camera frame -- only cheap bookkeeping
    # (throttle/stability checks, an enqueue) happens in this thread. Never
    # queue while an OCR job is active elsewhere (that GPU time stays
    # reserved for plate/OCR), no more than once per interval, and never a
    # second job for the same vehicle while one is already in flight. This
    # no longer waits for this vehicle's entire first OCR attempt to finish
    # first -- a fast vehicle can leave before that attempt (tracker
    # collection + queueing + the OCR thread itself) ever completes, and
    # previously meant colour, make, and therefore the backend entry event
    # never ran at all.
    # _has_pending_ocr_work() takes sessions_lock itself, so it must be
    # called before entering the lock below -- threading.Lock is not
    # reentrant, and nesting this call inside an already-held lock would
    # deadlock the main video-loop thread the first time a colour/make job
    # became eligible to enqueue.
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
        # Checked every frame this vehicle is visible, regardless of whether
        # colour or make/model changed just now -- this is what lets the
        # deferred [DETECTED] print fire either as soon as make resolves or
        # once DETECTED_GRACE_SEC has elapsed, whichever comes first.
        detected_message = _detected_message_if_ready(session, track_id, now)
        if in_exit_track_roi and center_y >= EXIT_ARM_Y:
            session["exit_armed"] = True
        crossed = in_exit_track_roi and session["exit_armed"] and not session["exit_crossed"] and session["frames"] >= EXIT_MIN_TRACK_FRAMES and center_y <= EXIT_CROSS_Y
        if crossed:
            session["exit_crossed"] = True
            _queue_entry_if_ready(session)
            _queue_exit_if_needed(session, "crossed_exit_line")
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
                # This vehicle is leaving before the stabilizer collected its
                # normal second confirming read -- typically a fast-moving
                # car. Without this, it would leave with zero backend record
                # at all: _queue_entry_if_ready only ever fires on a
                # confirmed session["plate"]. Only promote a lone read this
                # well above OCR_MIN_CONF, since it never gets the usual
                # protection of a second agreeing read.
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
                # Plate+colour were ready but the vehicle is leaving before
                # DETECTED_GRACE_SEC elapsed or make/model resolved -- this
                # is the last chance to print, so do it now with whatever
                # make value (possibly still "unknown") is available.
                session["detected_logged"] = True
                print(_build_detected_message(session, track_id), flush=True)
            elif (
                not session["detected_logged"]
                and not session["provisional_logged"]
                and session["provisional_plate"]
            ):
                # No longer gated on having exhausted every OCR attempt --
                # a fast vehicle can retire long before OCR_MAX_JOBS_PER_TRACK
                # jobs ever get submitted, and previously left with no trace
                # at all in that case.
                session["provisional_logged"] = True
                print(
                    f"[PROVISIONAL] track={track_id} "
                    f"plate={session['provisional_plate']} "
                    f"province={session['provisional_province']} "
                    f"conf={session['provisional_conf']:.2f} "
                    f"color={session['color']} color_conf={session['color_conf']:.2f}",
                    flush=True,
                )
            _queue_exit_if_needed(session, "track_disappeared")
            del vehicle_sessions[track_id]
        for old_track_id in list(session_aliases):
            if _current_session_id(old_track_id) not in vehicle_sessions:
                del session_aliases[old_track_id]


def _open_capture():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def run_live():
    global stop_flag
    cap = _open_capture()
    if not cap.isOpened():
        print(f"Cannot open camera: {CAMERA_INDEX}")
        return
    cv2.namedWindow("Gas Station LPR", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gas Station LPR", int(FRAME_W * DISPLAY_SCALE), int(FRAME_H * DISPLAY_SCALE))
    threading.Thread(target=ocr_worker, daemon=True).start()
    threading.Thread(target=attributes_worker, daemon=True).start()
    threading.Thread(target=backend_worker, daemon=True).start()
    frame_count, fps_count, fps, last_fps_at, last_plate_box = 0, 0, 0.0, time.time(), None
    print("Live detection started. Press 'q' to quit | 's' to screenshot", flush=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Lost camera feed, attempting to reconnect...", flush=True)
            cap.release()
            attempt = 0
            while not stop_flag:
                attempt += 1
                time.sleep(CAMERA_RECONNECT_DELAY_SEC)
                cap = _open_capture()
                if cap.isOpened():
                    print(f"Reconnected after {attempt} attempt(s).", flush=True)
                    break
                print(f"Reconnect attempt {attempt} failed, retrying...", flush=True)
            if stop_flag:
                break
            continue
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
            # A road marking can occasionally have a higher plate-model score
            # than the real registration.  Only use a candidate that belongs
            # to one of the tracked vehicles in this frame.
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
        # Reset every frame rather than only on a new valid detection -- otherwise
        # the green box drawn below keeps showing wherever the last valid plate
        # was, even after that vehicle has left or the plate is no longer found,
        # which looks like a wrong/stale detection on the current vehicle.
        last_plate_box = None
        if box:
            x, y, w, h = box
            roi_area = max(1, (DETECTION_ROI[2] - DETECTION_ROI[0]) * (DETECTION_ROI[3] - DETECTION_ROI[1]))
            vehicle = _plate_vehicle_match(box, vehicles)
            valid = vehicle and w >= MIN_PLATE_BOX_W and h >= MIN_PLATE_BOX_H and w * h >= max(MIN_PLATE_AREA_PIXELS, roi_area * MIN_PLATE_AREA_RATIO)
            if valid:
                track_id, session = vehicle["id"], _get_session(vehicle["id"], now)
                pad_x, pad_y = max(2, int(w * 0.10)), max(2, int(h * 0.16))
                crop = frame[max(0, y - pad_y):min(FRAME_H, y + h + pad_y), max(0, x - pad_x):min(FRAME_W, x + w + pad_x)]
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

        # Submit plate/OCR work before any secondary vehicle attributes.  A
        # colour inference can therefore never delay this frame's plate job.
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
                cv2.putText(frame, f"#{session['id']} {session['plate'] or 'reading'} | {session['color']}", (x, max(18, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        if last_plate_box:
            x, y, w, h = last_plate_box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, f"FPS:{fps:.1f}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.imshow("Gas Station LPR", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            stop_flag = True
            break
        if key == ord("s"):
            filename = f"screenshot_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Saved {filename}", flush=True)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    run_live()
