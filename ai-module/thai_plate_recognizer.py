"""Thai license-plate recognition using the trained ``character.pt`` model.

The model detects a character at a time for the registration and one province
class for the province line.  Province output is deliberately a *suggestion*:
the matching/review screen must let an operator confirm it.
"""

import os

import torch
from ultralytics import YOLO

from config import CHARACTER_MODEL_MIN_CONF, CHARACTER_MODEL_PATH, DEBUG_THAI_PLATE, PLATE_LINE_SPLIT_RATIO
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


def recognize_thai_plate(crop):
    """Return plate text plus a non-authoritative province suggestion.

    The return shape is stable even if inference cannot run:
    ``{"plate": "", "confidence": 0.0, "province_code": "", ...}``.
    """
    empty = {"plate": "", "confidence": 0.0, "province_code": "", "province_confidence": 0.0}
    model = _get_model()
    if model is None or crop is None or crop.size == 0:
        return empty
    try:
        # In debug mode retain weak detections in the log.  They are still
        # excluded from the assembled plate below, so diagnostics cannot make
        # the live recognizer less conservative.
        inference_conf = 0.01 if DEBUG_THAI_PLATE else CHARACTER_MODEL_MIN_CONF
        result = model(crop, conf=inference_conf, iou=0.45, verbose=False)[0]
    except Exception as error:
        print(f"[THAI-PLATE] inference skipped: {error}", flush=True)
        return empty

    crop_h = crop.shape[0]
    split_y = crop_h * PLATE_LINE_SPLIT_RATIO

    characters, provinces, raw_detections = [], [], []
    for box in result.boxes:
        try:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = (float(value) for value in box.xyxy[0])
        except (IndexError, TypeError, ValueError):
            continue
        label = _label(model, class_id)
        raw_detections.append((label, round(confidence, 2)))
        if confidence < CHARACTER_MODEL_MIN_CONF:
            continue
        y_center = (y1 + y2) / 2
        # A registration character detected inside the province band (or a
        # province-line detection inside the registration band) is almost
        # always the model firing on the wrong line's text.  Keep the two
        # bands separate the same way the EasyOCR fallback crop is split, so
        # a stray province letter can never be spliced into the plate text.
        if label.isdigit() or label in THAI_CHARACTER_MAP:
            if y_center >= split_y:
                continue
            characters.append((x1, y1, x2, y2, THAI_CHARACTER_MAP.get(label, label), confidence))
        elif label in PROVINCE_CODES:
            if y_center < split_y:
                continue
            provinces.append((confidence, label))

    # Registration characters are ordered horizontally.  Province classes are
    # separate whole-line detections and never contribute to the plate text.
    characters.sort(key=lambda item: item[0])
    plate = "".join(item[4] for item in characters)
    confidence = sum(item[5] for item in characters) / len(characters) if characters else 0.0
    province_confidence, province_code = max(provinces, default=(0.0, ""), key=lambda item: item[0])
    if not is_plausible_plate_text(plate):
        plate, confidence = "", 0.0

    if DEBUG_THAI_PLATE:
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
