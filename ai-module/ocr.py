import os
import time
import warnings

import cv2
import easyocr
import torch

from config import DEBUG_OCR, DEBUG_OCR_SAVE_VARIANTS, DEBUG_OCR_VERBOSE
from utils import get_plate_preprocess_variants
from plate_filter import normalize_plate_text, is_plausible_plate_text


use_gpu = torch.cuda.is_available()
reader = easyocr.Reader(["th", "en"], gpu=use_gpu)
if use_gpu:
    print("[OCR] Using GPU for EasyOCR")
else:
    print("[OCR] Using CPU for EasyOCR")


def _normalize_thai_text(text):
    return "".join(char for char in (text or "") if "\u0e00" <= char <= "\u0e7f")


def _is_thai_text(text):
    return len(_normalize_thai_text(text)) >= 2


def ocr_best(crop, allowlist, threshold=0.25, normalizer=normalize_plate_text, validator=None):
    if crop is None or crop.size == 0:
        return "", 0.0

    variants = get_plate_preprocess_variants(crop, target_w=1000)
    if not variants:
        return "", 0.0

    best_text = ""
    best_conf = 0.0
    best_score = -1.0
    best_variant = None

    for idx, processed in enumerate(variants):
        if DEBUG_OCR_SAVE_VARIANTS:
            os.makedirs("debug_crops", exist_ok=True)
            fname = f"debug_crops/{time.time():.3f}_{idx}.jpg"
            cv2.imwrite(fname, processed)

        try:
            # EasyOCR can generate a zero-height internal text box from a
            # degenerate plate crop. Convert its RuntimeWarning to a handled
            # exception, so it cannot clutter the terminal or stop OCR.
            with warnings.catch_warnings():
                warnings.simplefilter("error", RuntimeWarning)
                results = reader.readtext(
                    processed,
                    allowlist=allowlist,
                    detail=1,
                    paragraph=False,
                    text_threshold=threshold,
                    low_text=threshold,
                    link_threshold=0.25,
                    mag_ratio=2.5,
                    width_ths=1.5,
                    contrast_ths=0.1,
                    adjust_contrast=0.7,
                )
        except (cv2.error, OverflowError, RuntimeWarning, ValueError) as error:
            # EasyOCR occasionally produces an empty internal text crop for a
            # tiny/degenerate detection.  This must not terminate ocr_worker.
            if DEBUG_OCR_SAVE_VARIANTS:
                print(f"[OCR] variant {idx}: OpenCV error skipped: {error}")
            continue
        if not results:
            continue

        # EasyOCR may return the Thai prefix and digits as separate words.
        # Evaluate both each word and the left-to-right joined text.
        ordered = sorted(results, key=lambda item: min(point[0] for point in item[0]))
        candidates = [(text, float(conf)) for _, text, conf in ordered]
        if len(ordered) > 1:
            joined_text = "".join(text for _, text, _ in ordered)
            # A plate's Thai prefix and its digits are frequently separate
            # EasyOCR detections.  The minimum confidence makes the complete
            # joined reading always lose to one isolated character, so use a
            # conservative average and give valid registration shapes priority
            # below.  The raw OCR confidence is still returned to the caller.
            joined_conf = sum(float(conf) for _, _, conf in ordered) / len(ordered)
            candidates.append((joined_text, joined_conf))

        for text, value in candidates:
            clean = normalizer(text)
            if not clean or (validator is not None and not validator(clean)):
                continue

            # Prefer a complete, plausible plate over a high-confidence
            # fragment such as "5".  This only affects the selection; the
            # caller still receives the unmodified OCR confidence and applies
            # OCR_MIN_CONF before accepting the result.
            score = value + min(len(clean), 8) * 0.02
            if normalizer is normalize_plate_text and is_plausible_plate_text(clean):
                score += 2.0
            elif normalizer is normalize_plate_text and any(ch.isdigit() for ch in clean) and any("ก" <= ch <= "ฮ" for ch in clean):
                score += 0.20

            if score > best_score:
                best_text = clean
                best_conf = value
                best_score = score
                best_variant = idx

    if DEBUG_OCR_VERBOSE and best_text:
        print(f"[OCR] winner: variant {best_variant}, text={best_text}, conf={best_conf:.2f}")
    elif DEBUG_OCR_VERBOSE:
        print("[OCR] no valid text across all variants")

    return best_text, best_conf
