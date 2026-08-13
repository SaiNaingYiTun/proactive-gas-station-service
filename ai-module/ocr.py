import os
import time

import cv2
import easyocr
import torch

from config import DEBUG_OCR
from utils import preprocess


reader = easyocr.Reader(["th", "en"], gpu=torch.cuda.is_available())


def ocr_best(crop, allowlist):
    if crop.size == 0:
        return "", 0.0
    processed = preprocess(crop)

    if DEBUG_OCR:
        os.makedirs("debug_crops", exist_ok=True)
        fname = f"debug_crops/{time.time():.3f}.jpg"
        cv2.imwrite(fname, processed)

    results = reader.readtext(
        processed,
        allowlist=allowlist,
        detail=1,
        paragraph=False,
        text_threshold=0.25,
        low_text=0.25,
        link_threshold=0.25,
        mag_ratio=2.5,
        width_ths=1.5,
        contrast_ths=0.1,
        adjust_contrast=0.7,
    )
    if not results:
        return "", 0.0
    results.sort(key=lambda r: r[0][0][0])
    text = "".join([r[1] for r in results]).strip()
    conf = sum(r[2] for r in results) / len(results)
    return text, conf
