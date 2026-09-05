import os

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from config import COLOR_MODEL_MIN_CONF, COLOR_MODEL_PATH


_color_model = None
_color_model_load_failed = False
_COLOR_ALIASES = {"grey": "gray"}


def _vehicle_body_crop(crop):
    """Remove the loose detector box edges where road and foliage appear."""
    if crop is None or crop.size == 0:
        return crop
    height, width = crop.shape[:2]
    x1, x2 = int(width * 0.12), max(int(width * 0.12) + 1, int(width * 0.94))
    y1, y2 = int(height * 0.18), max(int(height * 0.18) + 1, int(height * 0.90))
    body = crop[y1:y2, x1:x2]
    return body if body.size else crop


def _get_color_model():
    """Load the classifier once, using CUDA when PyTorch can access it."""
    global _color_model, _color_model_load_failed
    if _color_model is not None or _color_model_load_failed:
        return _color_model
    if not os.path.isfile(COLOR_MODEL_PATH):
        _color_model_load_failed = True
        return None
    try:
        _color_model = YOLO(COLOR_MODEL_PATH)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _color_model.to(device)
        print(f"[COLOR] Using trained model: {COLOR_MODEL_PATH} on {device}", flush=True)
    except Exception as error:
        print(f"[COLOR] model disabled: {error}", flush=True)
        _color_model_load_failed = True
    return _color_model


def _estimate_model_color(crop):
    model = _get_color_model()
    if model is None or crop is None or crop.size == 0:
        return "unknown", 0.0
    try:
        result = model(crop, verbose=False)[0]
        if result.probs is None:
            return "unknown", 0.0
        class_id = int(result.probs.top1)
        confidence = float(result.probs.top1conf.item())
        name = model.names[class_id] if isinstance(model.names, dict) else model.names[class_id]
        color = _COLOR_ALIASES.get(str(name).lower(), str(name).lower())
        if confidence < COLOR_MODEL_MIN_CONF:
            return "unknown", 0.0
        return color, confidence
    except Exception as error:
        # The HSV fallback below still permits the LPR pipeline to run if a
        # model/runtime error occurs on one frame.
        print(f"[COLOR] model inference skipped: {error}", flush=True)
        return "unknown", 0.0


def estimate_vehicle_color(crop):
    if crop is None or crop.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    mean_h = float(np.mean(h))
    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))
    std_v = float(np.std(v))
    median_v = float(np.median(v))

    # Focus on brighter body panels rather than dark windows, tyres, and the
    # road. This distinguishes the black sedan from the white SUV in the exit
    # camera footage, where a plain whole-crop hue average is misleading.
    bright_mask = v >= 140
    bright_ratio = float(np.mean(bright_mask))
    bright_saturation = float(np.median(s[bright_mask])) if np.any(bright_mask) else 255.0

    if bright_ratio >= 0.25 and bright_saturation < 26:
        return "white"

    if median_v < 85 and bright_ratio < 0.22:
        return "black"

    # Bright, low-saturation image -> white/silver/gray, but only when contrast is decent.
    if mean_s < 18 and mean_v > 165 and std_v > 18:
        return "white"

    if mean_s < 28 and mean_v > 120 and std_v > 15:
        return "silver"

    if mean_s < 30 and mean_v > 90 and std_v > 12:
        return "gray"

    # Saturated hues.
    if 0 <= mean_h < 15 or 165 <= mean_h <= 180:
        return "red"
    if 15 <= mean_h < 25:
        return "orange"
    if 25 <= mean_h < 40:
        return "yellow"
    if 40 <= mean_h < 75:
        return "green"
    if 75 <= mean_h < 115:
        return "blue"
    if 115 <= mean_h < 150:
        return "purple"
    if 150 <= mean_h < 165:
        return "pink"

    # If the crop is still pale after hue checks, classify as gray rather than random noise.
    if mean_s < 38 and mean_v > 70:
        return "gray"

    return "unknown"


def _estimate_hsv_color_with_confidence(crop):
    if crop is None or crop.size == 0:
        return "unknown", 0.0

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    # Thai taxis commonly have both yellow and green body panels.  Testing
    # only the average hue turns this into an arbitrary single colour.  Use
    # the central body region so roadside foliage does not supply the green.
    height, width = h.shape
    body_h = slice(int(height * 0.18), max(int(height * 0.18) + 1, int(height * 0.88)))
    body_w = slice(int(width * 0.08), max(int(width * 0.08) + 1, int(width * 0.92)))
    body_hue, body_sat, body_value = h[body_h, body_w], s[body_h, body_w], v[body_h, body_w]
    body_mask = (body_sat >= 70) & (body_value >= 90)
    if np.any(body_mask):
        yellow_ratio = float(np.mean((body_hue >= 25) & (body_hue < 40) & body_mask))
        green_ratio = float(np.mean((body_hue >= 40) & (body_hue < 75) & body_mask))
        if yellow_ratio >= 0.06 and green_ratio >= 0.06 and yellow_ratio + green_ratio >= 0.18:
            return "yellow-green", 0.65

    # A monochrome/IR camera has no colour information.  Calling a grayscale
    # image "white" or "gray" is misleading, so report it as unavailable.
    b, g, r = cv2.split(crop)
    chroma = np.maximum.reduce((
        np.abs(b.astype(np.int16) - g.astype(np.int16)),
        np.abs(g.astype(np.int16) - r.astype(np.int16)),
        np.abs(r.astype(np.int16) - b.astype(np.int16)),
    ))
    if float(np.percentile(chroma, 95)) < 5.0:
        return "unknown", 0.0

    mean_h = float(np.mean(h))
    mean_s = float(np.mean(s))
    mean_v = float(np.mean(v))
    std_v = float(np.std(v))

    color = estimate_vehicle_color(crop)
    if color == "unknown":
        return color, 0.0

    if color == "yellow-green":
        # Both saturated taxi body colours must be visibly present, rather
        # than the result being an average of two unrelated background hues.
        return color, 0.65

    saturation_score = min(1.0, mean_s / 120.0)
    brightness_score = min(1.0, mean_v / 180.0)
    contrast_score = min(1.0, std_v / 60.0)

    confidence = 0.45 * saturation_score + 0.35 * brightness_score + 0.20 * contrast_score

    # More strict rejection for low-contrast or washed-out vehicles.
    if mean_s < 18 or mean_v < 25 or std_v < 12:
        confidence *= 0.55

    # Neutral colors need better contrast to be trusted.
    if color in {"white", "silver", "gray"} and (mean_s < 28 or std_v < 18):
        confidence *= 0.8

    # Black should be a little more conservative when the image is too bright.
    if color == "black" and mean_v > 120:
        confidence *= 0.75

    # A large, low-saturation bright-panel region is a strong white signal,
    # even though the complete crop also includes dark glass and road.
    bright_mask = v >= 140
    if color == "white" and np.any(bright_mask):
        bright_ratio = float(np.mean(bright_mask))
        bright_saturation = float(np.median(s[bright_mask]))
        if bright_ratio >= 0.25 and bright_saturation < 26:
            confidence = max(confidence, 0.45)

    if confidence < 0.30:
        return "unknown", 0.0

    return color, float(max(0.0, min(1.0, confidence)))


def estimate_vehicle_color_with_confidence(crop):
    """Use the trained colour classifier; use HSV only as a fallback."""
    # Vehicle detector boxes often contain foliage/road around the body.  Use
    # the inner body for both methods so background green cannot dominate.
    body = _vehicle_body_crop(crop)
    color, confidence = _estimate_model_color(body)
    if color != "unknown":
        return color, confidence
    return _estimate_hsv_color_with_confidence(body)
