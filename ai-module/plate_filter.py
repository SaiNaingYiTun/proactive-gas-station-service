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

    # Thai private-vehicle plates normally use Thai letters followed by digits.
    # Some registrations use a leading digit followed by Thai letters and the
    # serial digits (for example "4กข9517"), so accept that form as well.
    # Reject a number-only fragment (for example "921"): it is often read
    # from a building, timestamp, or incomplete plate and must not be sent to
    # the backend as a registration number.
    # A two-character result such as "ว3" is almost always an OCR fragment,
    # not a usable registration.  Require at least two digits and a minimum
    # of three total characters before it can reach the stabilizer/backend.
    if re.fullmatch(r"(?:[ก-ฮ]{1,5}\d{2,4}|\d[ก-ฮ]{1,3}\d{2,4})", text):
        return True

    return False
