import torch
import cv2
import numpy as np
from ultralytics import YOLO

from config import CONF_THRESHOLD, ENABLE_PLATE_FALLBACK, MODEL_PATH


device = "cuda" if torch.cuda.is_available() else "cpu"
plate_model = YOLO(MODEL_PATH)
plate_model.to(device)


def _red_plate_fallback(frame):
    """Fallback for red- or low-contrast Thai plates when YOLO misses them."""
    h, w = frame.shape[:2]
    if h == 0 or w == 0:
        return None, 0.0

    roi = frame[max(0, int(h * 0.2)):h, max(0, int(w * 0.12)):w]
    if roi.size == 0:
        return None, 0.0

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    red1 = cv2.inRange(hsv, (0, 40, 50), (15, 255, 255))
    red2 = cv2.inRange(hsv, (165, 40, 50), (180, 255, 255))
    white = cv2.inRange(hsv, (0, 0, 180), (180, 60, 255))
    mask = cv2.bitwise_or(red1, red2)
    mask = cv2.bitwise_or(mask, white)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best = None
    best_area = 0
    for contour in contours:
        x, y, ww, hh = cv2.boundingRect(contour)
        area = ww * hh
        if area < max(200, w * h * 0.0006):
            continue
        aspect = ww / max(hh, 1)
        if aspect < 1.8 or aspect > 9.0:
            continue
        if area > best_area:
            best_area = area
            best = (x, y, ww, hh)

    if best is None:
        return None, 0.0

    x, y, ww, hh = best
    return (x, y, ww, hh), 0.35


def find_plate_yolo_candidates(frame):
    """Return plate candidates ordered from highest to lowest confidence."""
    results = plate_model(frame, conf=CONF_THRESHOLD, iou=0.45, verbose=False)[0]
    candidates = []
    h, w = frame.shape[:2]

    for box in results.boxes:
        conf = float(box.conf[0])
        if conf <= 0:
            continue
        x1, y1, x2, y2 = map(float, box.xyxy[0])
        plate_w = x2 - x1
        plate_h = y2 - y1
        area = plate_w * plate_h

        if plate_w <= 0 or plate_h <= 0:
            continue
        # Do not discard valid distant plates before the live pipeline has a
        # chance to combine several frames.  The final absolute/relative gate
        # is applied in main.py and is deliberately lower for this camera.
        if area < max(350, w * h * 0.001):
            continue
        if plate_w / max(plate_h, 1) > 8 or plate_w / max(plate_h, 1) < 1.5:
            continue

        candidates.append((conf, area, int(x1), int(y1), int(x2), int(y2)))

    if not candidates and ENABLE_PLATE_FALLBACK:
        fallback_box, fallback_conf = _red_plate_fallback(frame)
        if fallback_box is None:
            return []
        return [(fallback_box, fallback_conf)]

    candidates.sort(key=lambda value: (value[0], value[1]), reverse=True)
    return [
        ((x1, y1, x2 - x1, y2 - y1), conf)
        for conf, area, x1, y1, x2, y2 in candidates
    ]


def find_plate_yolo(frame):
    """Return the highest-confidence plate candidate for legacy callers."""
    candidates = find_plate_yolo_candidates(frame)
    return candidates[0] if candidates else (None, 0.0)
