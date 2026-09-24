import os
import time

import cv2
import torch
from ultralytics import YOLO

from config import (
    BRAND_ALLOWLIST, BRAND_ALLOWLIST_MIN_RAW_CONF, BRAND_MODEL_PATH,
    DEBUG_MAKE_MODEL, DEBUG_MAKE_MODEL_SAVE_INPUTS, MAKE_MODEL_MIN_CONF,
)


_brand_model = None
_brand_model_load_failed = False


def _vehicle_body_crop(crop):
    """Remove the loose detector box edges where road and foliage appear."""
    if crop is None or crop.size == 0:
        return crop
    height, width = crop.shape[:2]
    x1, x2 = int(width * 0.08), max(int(width * 0.08) + 1, int(width * 0.96))
    y1, y2 = int(height * 0.10), max(int(height * 0.10) + 1, int(height * 0.95))
    body = crop[y1:y2, x1:x2]
    return body if body.size else crop


def _get_brand_model():
    """Load the classifier once, using CUDA when PyTorch can access it."""
    global _brand_model, _brand_model_load_failed
    if _brand_model is not None or _brand_model_load_failed:
        return _brand_model
    if not os.path.isfile(BRAND_MODEL_PATH):
        print(f"[MAKE] model not found: {BRAND_MODEL_PATH}", flush=True)
        _brand_model_load_failed = True
        return None
    try:
        _brand_model = YOLO(BRAND_MODEL_PATH)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _brand_model.to(device)
        print(f"[MAKE] Using trained model: {BRAND_MODEL_PATH} on {device}", flush=True)
    except Exception as error:
        print(f"[MAKE] model disabled: {error}", flush=True)
        _brand_model_load_failed = True
    return _brand_model


def _infer_classify(model, body):
    """brand.pt as a whole-image classifier (``model.task == 'classify'``)."""
    result = model(body, verbose=False)[0]
    names = model.names
    if result.probs is None:
        return "unknown", 0.0

    full_probs = result.probs.data
    allowed = [
        (BRAND_ALLOWLIST[str(names[i])], float(full_probs[i]))
        for i in range(len(names))
        if str(names[i]) in BRAND_ALLOWLIST
    ]
    total = sum(prob for _, prob in allowed)

    if DEBUG_MAKE_MODEL:
        top_ids = result.probs.top5
        top_confs = result.probs.top5conf.tolist()
        full_top5 = [(str(names[i]), round(float(c), 2)) for i, c in zip(top_ids, top_confs)]
        allowed_top5 = sorted(allowed, key=lambda item: item[1], reverse=True)[:5]
        winner = max(allowed, key=lambda item: item[1])[0] if total > 0 else "<none>"
        winner_conf = max(prob for _, prob in allowed) / total if total > 0 else 0.0
        print(
            f"[MAKE] full_top5={full_top5} "
            f"allowed_top5={[(name, round(prob, 2)) for name, prob in allowed_top5]} "
            f"make={winner} conf={winner_conf:.2f}",
            flush=True,
        )

    if total <= 0:
        return "unknown", 0.0
    make, raw_conf = max(allowed, key=lambda item: item[1])
    
    if raw_conf < BRAND_ALLOWLIST_MIN_RAW_CONF:
        return "unknown", 0.0
    confidence = raw_conf / total
    if confidence < MAKE_MODEL_MIN_CONF:
        return "unknown", 0.0
    return make, confidence


def _infer_detect(model, body):
    """brand.pt as a badge/logo detector (``model.task == 'detect'``)."""
    names = model.names
    inference_conf = 0.01 if DEBUG_MAKE_MODEL else MAKE_MODEL_MIN_CONF
    result = model(body, conf=inference_conf, iou=0.45, verbose=False)[0]
    best_class_id, best_confidence = None, 0.0
    raw_detections = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        label = names[class_id] if isinstance(names, dict) else names[class_id]
        raw_detections.append((str(label), round(confidence, 2)))
        if confidence >= MAKE_MODEL_MIN_CONF and confidence > best_confidence:
            best_confidence = confidence
            best_class_id = class_id
    if DEBUG_MAKE_MODEL:
        winner = names[best_class_id] if best_class_id is not None else "<none>"
        print(f"[MAKE] raw={raw_detections} make={winner} conf={best_confidence:.2f}", flush=True)
    if best_class_id is None:
        return "unknown", 0.0
    return str(names[best_class_id]).lower(), best_confidence


def infer_make_model(vehicle_crop, track_id=None):
    """Return (make, model, confidence) with a safe unknown fallback."""
    if vehicle_crop is None or vehicle_crop.size == 0:
        return "unknown", "unknown", 0.0
    model = _get_brand_model()
    if model is None:
        return "unknown", "unknown", 0.0
    try:
        
        if DEBUG_MAKE_MODEL_SAVE_INPUTS and vehicle_crop.size:
            os.makedirs("./debug_crops", exist_ok=True)
            label = track_id if track_id is not None else "na"
            cv2.imwrite(f"./debug_crops/make_input_{label}_{time.time():.0f}.jpg", vehicle_crop)
        body = _vehicle_body_crop(vehicle_crop)
        if model.task == "classify":
            make, confidence = _infer_classify(model, body)
        else:
            make, confidence = _infer_detect(model, body)
        return make, "unknown", confidence
    except Exception as error:
        
        print(f"[MAKE] inference skipped: {error}", flush=True)
        return "unknown", "unknown", 0.0
