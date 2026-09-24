import os

import torch
from ultralytics import YOLO

from config import (
    CHARACTER_AMBIGUOUS_MARGIN, CHARACTER_GAP_MIN_CONF, CHARACTER_MODEL_MIN_CONF,
    CHARACTER_MODEL_PATH, CHARACTER_OVERLAP_RATIO, DEBUG_THAI_PLATE,
    PLATE_LINE_SPLIT_RATIO,
)
from plate_filter import is_plausible_plate_text


THAI_CHARACTER_MAP = {
    "A01": "ก", "A02": "ข", "A04": "ค", "A06": "ฆ", "A07": "ง",
    "A08": "จ", "A09": "ฉ", "A10": "ช", "A12": "ฌ", "A13": "ญ",
    "A14": "ฎ", "A16": "ฐ", "A18": "ฒ", "A19": "ณ", "A20": "ด",
    "A21": "ต", "A22": "ถ", "A23": "ท", "A24": "ธ", "A25": "น",
    "A26": "บ", "A27": "ป", "A28": "ผ", "A30": "พ", "A31": "ฟ",
    "A32": "ภ", "A33": "ม", "A34": "ย", "A35": "ร", "A36": "ล",
    "A37": "ว", "A38": "ศ", "A39": "ษ", "A40": "ส", "A41": "ห",
    "A42": "ฬ", "A43": "อ", "A44": "ฮ",
}

# Classes after A44 identify the whole province line.  Keep the source code
# as returned by the model so the reviewer can confirm its actual province.
PROVINCE_CODES = {
    "ACR", "ATG", "AYA", "BKK", "BKN", "BRM", "CBI", "CCO", "CMI",
    "CNT", "CPM", "CPN", "CRI", "CTI", "KBI", "KKN", "KPT", "KRI",
    "KSN", "LEI", "LPG", "LPN", "LRI", "MDH", "MKM", "NAN", "NBI",
    "NBP", "NKI", "NMA", "NPM", "NPT", "NRT", "NSN", "NST", "NWT",
    "NYK", "PBI", "PCT", "PKN", "PKT", "PLG", "PLK", "PNA", "PNB",
    "PRE", "PRI", "PTE", "PTN", "PYO", "RBR", "RET", "RNG", "RYG",
    "SBR", "SKA", "SKM", "SKN", "SKW", "SNI", "SNK", "SPB", "SPK",
    "SRI", "SRN", "SSK", "STI", "STN", "TAK", "TRG", "TRT", "UBN",
    "UDN", "UTI", "UTT", "YLA", "YST",
}

_model = None
_load_failed = False


def _get_model():
    """Load the local detector lazily so startup remains resilient."""
    global _model, _load_failed
    if _model is not None or _load_failed:
        return _model
    if not os.path.isfile(CHARACTER_MODEL_PATH):
        print(f"[THAI-PLATE] model not found: {CHARACTER_MODEL_PATH}", flush=True)
        _load_failed = True
        return None
    try:
        _model = YOLO(CHARACTER_MODEL_PATH)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model.to(device)
        print(f"[THAI-PLATE] Using {CHARACTER_MODEL_PATH} on {device}", flush=True)
    except Exception as error:
        print(f"[THAI-PLATE] model disabled: {error}", flush=True)
        _load_failed = True
    return _model


def _label(model, class_id):
    names = model.names
    return str(names[class_id] if isinstance(names, dict) else names[class_id])


def _resolve_overlapping_characters(boxes):
    """Collapse duplicate detections that cover the same physical character.
    """
    remaining = sorted(boxes, key=lambda item: item[5], reverse=True)
    resolved, dropped_ambiguous = [], []
    while remaining:
        best = remaining.pop(0)
        bx1, by1, bx2, by2 = best[:4]
        best_area = max(1.0, (bx2 - bx1) * (by2 - by1))
        group, still_remaining = [best], []
        for other in remaining:
            ox1, oy1, ox2, oy2 = other[:4]
            left, top = max(bx1, ox1), max(by1, oy1)
            right, bottom = min(bx2, ox2), min(by2, oy2)
            intersection = max(0, right - left) * max(0, bottom - top)
            other_area = max(1.0, (ox2 - ox1) * (oy2 - oy1))
            if intersection / min(best_area, other_area) >= CHARACTER_OVERLAP_RATIO:
                group.append(other)
            else:
                still_remaining.append(other)
        remaining = still_remaining
        if len(group) == 1 or group[0][5] - group[1][5] >= CHARACTER_AMBIGUOUS_MARGIN:
            resolved.append(group[0])
        else:
            dropped_ambiguous.append(group)
    return resolved, dropped_ambiguous


def _has_internal_gap(characters, weak_positions):
    """Detect a likely-missed character sitting between two accepted ones.
    """
    for left, right in zip(characters, characters[1:]):
        gap_left, gap_right = left[2], right[0]
        if gap_right <= gap_left:
            continue
        for wx1, wx2 in weak_positions:
            if gap_left < (wx1 + wx2) / 2 < gap_right:
                return True
    return False


def recognize_thai_plate(crop):
    """Return plate text plus a non-authoritative province suggestion.
    """
    empty = {"plate": "", "confidence": 0.0, "province_code": "", "province_confidence": 0.0}
    model = _get_model()
    if model is None or crop is None or crop.size == 0:
        return empty
    try:
        
        inference_conf = 0.01 if DEBUG_THAI_PLATE else CHARACTER_MODEL_MIN_CONF
        result = model(crop, conf=inference_conf, iou=0.45, verbose=False)[0]
    except Exception as error:
        print(f"[THAI-PLATE] inference skipped: {error}", flush=True)
        return empty

    crop_h = crop.shape[0]
    split_y = crop_h * PLATE_LINE_SPLIT_RATIO

    characters, provinces, raw_detections, weak_positions = [], [], [], []
    for box in result.boxes:
        try:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
        except (IndexError, TypeError, ValueError):
            continue
        label = _label(model, class_id)
        raw_detections.append((label, round(confidence, 2)))
        is_char_class = label.isdigit() or label in THAI_CHARACTER_MAP
        if confidence < CHARACTER_MODEL_MIN_CONF:
            if is_char_class and confidence >= CHARACTER_GAP_MIN_CONF:
                weak_positions.append((x1, x2))
            continue
        y_center = (y1 + y2) / 2
        
        if is_char_class:
            if y_center >= split_y:
                continue
            characters.append((x1, y1, x2, y2, THAI_CHARACTER_MAP.get(label, label), confidence))
        elif label in PROVINCE_CODES:
            if y_center < split_y:
                continue
            provinces.append((confidence, label))

    characters, dropped_ambiguous = _resolve_overlapping_characters(characters)

    characters.sort(key=lambda item: item[0])
    plate = "".join(item[4] for item in characters)
    confidence = sum(item[5] for item in characters) / len(characters) if characters else 0.0
    province_confidence, province_code = max(provinces, default=(0.0, ""), key=lambda item: item[0])
    incomplete = _has_internal_gap(characters, weak_positions)
    if not is_plausible_plate_text(plate) or incomplete:
        plate, confidence = "", 0.0

    if DEBUG_THAI_PLATE:
        if dropped_ambiguous:
            ambiguous_str = [
                [(item[4], round(item[5], 2)) for item in group]
                for group in dropped_ambiguous
            ]
            print(f"[THAI-PLATE] ambiguous positions dropped: {ambiguous_str}", flush=True)
        if incomplete:
            print(f"[THAI-PLATE] discarded as incomplete: a weak detection sits between accepted characters", flush=True)
        print(
            f"[THAI-PLATE] raw={raw_detections} plate={plate or '<invalid>'} "
            f"conf={confidence:.2f} province={province_code or '<none>'}",
            flush=True,
        )

    return {
        "plate": plate,
        "confidence": confidence,
        "province_code": province_code,
        "province_confidence": province_confidence,
    }
