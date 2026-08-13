import re


_ALLOWED_RE = re.compile(r"^[ก-๙0-9]+$")


def normalize_plate_text(text):
    if not text:
        return ""
    return re.sub(r"[\s\-_.|]+", "", text.strip())


def is_plausible_plate_text(text):
    if not text:
        return False
    if not _ALLOWED_RE.match(text):
        return False
    thai_count = sum(1 for char in text if "ก" <= char <= "๛")
    digit_count = sum(1 for char in text if char.isdigit())
    if len(text) < 4:
        return False
    return thai_count >= 1 and digit_count >= 2
