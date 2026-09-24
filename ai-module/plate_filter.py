import re


def normalize_plate_text(text):
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"[^0-9ก-ฮ]", "", text)
    return text


def is_plausible_plate_text(text):
    text = normalize_plate_text(text)
    if not text:
        return False

    
    if re.fullmatch(r"(?:[ก-ฮ]{1,5}\d{2,4}|\d[ก-ฮ]{1,3}\d{2,4})", text):
        return True

    return False


def plates_roughly_agree(first, second):
    """
    Determine if two plate readings are roughly the same, accounting for
    minor OCR errors and variations in how the two engines interpret the image.
    """
    first, second = normalize_plate_text(first), normalize_plate_text(second)
    if not first or not second:
        return False
    if first == second:
        return True

    digits_a = "".join(char for char in first if char.isdigit())
    digits_b = "".join(char for char in second if char.isdigit())
    if len(digits_a) < 3 or len(digits_b) < 3:
        return False

    if len(digits_a) == len(digits_b):
        
        return sum(a == b for a, b in zip(digits_a, digits_b)) >= len(digits_a) - 1
    if abs(len(digits_a) - len(digits_b)) == 1:
        
        shorter, longer = sorted((digits_a, digits_b), key=len)
        return longer.startswith(shorter) or longer.endswith(shorter)
    return False
