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


def plates_roughly_agree(first, second):
    """Whether two independent plate reads are close enough to call the same
    physical plate, tolerant of the kind of noise each engine adds on its own
    (character.pt drops a character it isn't confident on; EasyOCR often
    prepends/appends a stray digit or misses a letter) -- but NOT tolerant of
    a genuinely different serial number.

    This exists because the two engines almost never produce the exact same
    string even when both correctly read the plate (one may include the
    leading digit the other dropped, EasyOCR may tack on an extra trailing
    digit), so exact equality is too strict to ever recognise agreement, but
    two DIFFERENT digits at the same position (a real misread, e.g. "4838"
    vs "4939") must never be waved through as "close enough".
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
        # Same digit count: require them to be near-identical, not just
        # "mostly similar" -- SequenceMatcher's ratio can still score two
        # digit strings that disagree at one position as a decent match
        # purely because most of the other digits line up too, which would
        # again wave through exactly the single-wrong-digit case this exists
        # to catch. Position-by-position agreement is unambiguous.
        return sum(a == b for a, b in zip(digits_a, digits_b)) >= len(digits_a) - 1
    if abs(len(digits_a) - len(digits_b)) == 1:
        # One engine dropped or added a single digit at one end -- the same
        # tolerance PlateStabilizer already gives a repeated read of the
        # SAME engine across frames (see its own docstring), extended here
        # to a same-attempt read from the OTHER engine.
        shorter, longer = sorted((digits_a, digits_b), key=len)
        return longer.startswith(shorter) or longer.endswith(shorter)
    return False
