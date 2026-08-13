import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import cv2
import queue
import threading
import time
from datetime import datetime

from backend import send_detection, send_exit
from config import (
    CAMERA_INDEX,
    COOLDOWN_SEC,
    DEBUG_OCR,
    DISPLAY_SCALE,
    EXIT_AFTER_SEC,
    FRAME_H,
    FRAME_W,
    MIN_PLATE_BOX_H,
    MIN_PLATE_BOX_W,
    OCR_MIN_CONF,
    PROVINCE_ALLOWLIST,
    THAI_ALLOWLIST,
    YOLO_EVERY_N,
)
from detector import find_plate_yolo
from plate_filter import is_plausible_plate_text, normalize_plate_text
from ocr import ocr_best
from province_parser import match_province
from stabilizer import PlateStabilizer
from tracker import BurstTracker
from utils import upscale


ocr_queue = queue.Queue(maxsize=1)
backend_queue = queue.Queue(maxsize=10)
result_lock = threading.Lock()
live_result = {"text": "", "province": "", "conf": 0.0, "updated": 0, "last_seen": 0, "visit_id": None}
plate_stabilizer = PlateStabilizer(window_size=5, required_hits=2, stale_seconds=8, similarity_threshold=0.85)
province_stabilizer = PlateStabilizer(window_size=5, required_hits=2, stale_seconds=8, similarity_threshold=1.0)
entry_sent_for_presence = False
stop_flag = False


def backend_worker():
    while not stop_flag:
        try:
            job = backend_queue.get(timeout=1)
        except queue.Empty:
            continue
        if job["type"] == "entry":
            data = send_detection(job["plate"], job["conf"])
            if data:
                with result_lock:
                    live_result["visit_id"] = data.get("visit_id")
                tag = "NEW" if data.get("is_new_visit") else "seen again"
                print(f" [{tag}] {job['plate']}  visit_id={data.get('visit_id')}")
        elif job["type"] == "exit":
            if send_exit(job["plate"]):
                print(f" Exit: {job['plate']}")


def ocr_worker():
    global entry_sent_for_presence

    while not stop_flag:
        try:
            crop = ocr_queue.get(timeout=1)
        except queue.Empty:
            continue

        ph = crop.shape[0]
        split = int(ph * 0.62)

        main_text, conf = ocr_best(crop[0:split, :], THAI_ALLOWLIST)
        prov_raw, prov_conf = ocr_best(crop[split:, :], PROVINCE_ALLOWLIST)

        main_text = normalize_plate_text(main_text)
        province = match_province(prov_raw)

        now = time.time()

        stable_province = ""
        province_hit = None
        if province:
            province_hit = province_stabilizer.offer(province, prov_conf, province, now)
            if province_hit:
                stable_province = province_hit["text"]

        if main_text and conf > OCR_MIN_CONF and is_plausible_plate_text(main_text):
            stable = plate_stabilizer.offer(
                main_text,
                conf,
                stable_province or province,
                now
            )

            if stable:
                with result_lock:
                    same = stable["text"] == live_result["text"]
                    cooled = now - live_result["updated"] > COOLDOWN_SEC
                    should_send = (not entry_sent_for_presence) or (not same and cooled)

                    live_result.update({
                        "text": stable["text"],
                        "province": stable["province"],
                        "conf": stable["conf"],
                        "updated": now,
                    })

                print(
                    f" {stable['text']} | {stable['province']} "
                    f"(conf:{stable['conf']:.2f}, hits:{stable['hits']})"
                )

                if should_send:
                    try:
                        backend_queue.put_nowait({
                            "type": "entry",
                            "plate": stable["text"],
                            "conf": stable["conf"],
                        })
                        entry_sent_for_presence = True
                    except queue.Full:
                        pass
            else:
                print(f" Candidate {main_text} | {province}  (conf:{conf:.2f})")
        else:
            print(f"Low confidence read discarded (conf:{conf:.2f})")


def run_live():
    global stop_flag, entry_sent_for_presence

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print("Cannot open camera.")
        print(f"   URL: {CAMERA_INDEX}")
        return

    cv2.namedWindow("Gas Station LPR", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gas Station LPR", int(FRAME_W * DISPLAY_SCALE), int(FRAME_H * DISPLAY_SCALE))

    threading.Thread(target=ocr_worker, daemon=True).start()
    threading.Thread(target=backend_worker, daemon=True).start()

    tracker = BurstTracker(max_candidates=2)
    last_box = None
    frame_count = 0
    fps, fps_counter, t_fps = 0.0, 0, time.time()
    plate_present = False
    entry_sent_for_presence = False

    print("Live detection started.")
    print("   Press 'q' to quit | 's' to screenshot\n")
    if DEBUG_OCR:
        print("🐛 DEBUG_OCR enabled — crops saved to ./debug_crops/\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️  Lost camera feed.")
            break

        frame = cv2.resize(frame, (FRAME_W, FRAME_H))
        frame_count += 1
        fps_counter += 1

        if time.time() - t_fps >= 1.0:
            fps = fps_counter / (time.time() - t_fps)
            fps_counter = 0
            t_fps = time.time()

        box, box_conf = None, 0.0
        if frame_count % YOLO_EVERY_N == 0:
            box, box_conf = find_plate_yolo(frame)

        now = time.time()

        if box:
            x, y, w, h = box
            if w < MIN_PLATE_BOX_W or h < MIN_PLATE_BOX_H:
                print(f"🔎 Skipping tiny box {w}x{h} before OCR")
                last_box = box
            else:
                last_box = box
                plate_present = True
                with result_lock:
                    live_result["last_seen"] = now

                ih, iw = frame.shape[:2]
                pad = 15
                x1, y1 = max(0, x - pad), max(0, y - pad)
                x2, y2 = min(iw, x + w + pad), min(ih, y + h + pad)
                tight = frame[y : y + h, x : x + w]
                padded = frame[y1:y2, x1:x2]
                tracker.offer(tight, padded, box_conf)

                if tracker.ready() and ocr_queue.empty() and tracker.best_crop is not None:
                    try:
                        ocr_queue.put_nowait(upscale(tracker.best_crop))
                    except queue.Full:
                        pass
                    tracker.reset()

            if tracker.ready() and ocr_queue.empty() and tracker.best_crop is not None:
                try:
                    ocr_queue.put_nowait(upscale(tracker.best_crop))
                except queue.Full:
                    pass
                tracker.reset()

        else:
            with result_lock:
                last_seen = live_result["last_seen"]

            if plate_present and now - last_seen > EXIT_AFTER_SEC:
                if tracker.best_crop is not None and ocr_queue.empty():
                    try:
                        ocr_queue.put_nowait(upscale(tracker.best_crop))
                    except queue.Full:
                        pass
                tracker.reset()

                with result_lock:
                    plate_to_exit = live_result["text"]
                if plate_to_exit:
                    try:
                        backend_queue.put_nowait({"type": "exit", "plate": plate_to_exit})
                    except queue.Full:
                        pass
                plate_present = False
                entry_sent_for_presence = False
                last_box = None

        with result_lock:
            r_text = live_result["text"]
            r_province = live_result["province"]
            r_age = now - live_result["updated"]

        if last_box:
            x, y, w, h = last_box
            color = (0, 255, 0) if r_age < 5 else (130, 130, 130)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            if r_text and r_age < 8:
                cv2.putText(frame, f"{r_text} {r_province}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

        cv2.putText(frame, f"FPS:{fps:.1f}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        status = "Vehicle in frame" if last_box else "Waiting for vehicle..."
        cv2.putText(frame, status, (10, FRAME_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        cv2.imshow("Gas Station LPR", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            stop_flag = True
            break
        elif key == ord("s"):
            fname = f"screenshot_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(fname, frame)
            print(f"📸 {fname}")

    cap.release()
    cv2.destroyAllWindows()
    print("\n👋 Stopped.")


if __name__ == "__main__":
    run_live()
