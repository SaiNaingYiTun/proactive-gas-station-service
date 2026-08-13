from config import THAI_PROVINCES
from difflib import SequenceMatcher


def match_province(ocr_text):
    if not ocr_text or len(ocr_text) < 3:
        return ""
    ocr_text = ocr_text.strip()
    best_match=""
    best_score = 0.0
    for province in THAI_PROVINCES:
        score = SequenceMatcher(None, ocr_text, province).ratio()
        if score > best_score:
            best_score= score
            best_match = province
    return best_match if best_score >= 0.45 else ""
