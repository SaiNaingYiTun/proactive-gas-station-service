import cv2
import numpy as np

from config import UPSCALE_TARGET_W


def upscale(crop, target_w=UPSCALE_TARGET_W):
    h, w = crop.shape[:2]
    if w > 0 and w < target_w:
        crop = cv2.resize(crop, None, fx=target_w / w, fy=target_w / w, interpolation=cv2.INTER_CUBIC)
    return crop


def resize_to_target(gray, target_w):
    h, w = gray.shape[:2]
    if w > 0 and w < target_w:
        scale = target_w / w
        scale = min(scale, 4.0)
        new_w = int(w * scale)
        gray = cv2.resize(gray, (new_w, max(1, int(h * scale))), interpolation=cv2.INTER_CUBIC)
    return gray


def prepare_grayscale_variant(crop, target_w=1000):
    if crop is None or crop.size == 0:
        return None

    if len(crop.shape) == 3:
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        gray = crop.copy()

    gray = resize_to_target(gray, target_w)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    return gray


def prepare_clahe_variant(crop, target_w=1000):
    gray = prepare_grayscale_variant(crop, target_w=target_w)
    if gray is None:
        return None

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, kernel)
    return gray


def prepare_otsu_variant(crop, target_w=1000):
    gray = prepare_grayscale_variant(crop, target_w=target_w)
    if gray is None:
        return None

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if thresh.mean() > 200:
        thresh = cv2.bitwise_not(thresh)
    return thresh


def get_plate_preprocess_variants(crop, target_w=1000):
    variants = []
    gray = prepare_grayscale_variant(crop, target_w=target_w)
    if gray is not None:
        variants.append(gray)

    clahe = prepare_clahe_variant(crop, target_w=target_w)
    if clahe is not None:
        variants.append(clahe)

    otsu = prepare_otsu_variant(crop, target_w=target_w)
    if otsu is not None:
        variants.append(otsu)

    return variants


def normalize_plate_crop(crop, target_w=1000):

    return prepare_clahe_variant(crop, target_w=target_w)


def preprocess(crop):
    return normalize_plate_crop(crop, target_w=1000)


def sharpness_score(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()



_THAI_FONT_CANDIDATES = (
    "C:/Windows/Fonts/tahomabd.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/LeelawUI.ttf",
    "/usr/share/fonts/truetype/tlwg/Loma-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
)
_thai_font = None
_thai_font_searched = False


def _get_thai_font(size=15):
    global _thai_font, _thai_font_searched
    if not _thai_font_searched:
        _thai_font_searched = True
        try:
            from PIL import ImageFont
        except ImportError:
            return None
        for path in _THAI_FONT_CANDIDATES:
            try:
                _thai_font = ImageFont.truetype(path, size)
                break
            except OSError:
                continue
    return _thai_font


def put_label(frame, text, org, color=(0, 255, 255)):
    font = None if text.isascii() else _get_thai_font()
    if font is None:
        cv2.putText(frame, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return

    from PIL import Image, ImageDraw

    left, top, right, bottom = font.getbbox(text, anchor="ls")
    x0, y0 = max(0, org[0] + left - 2), max(0, org[1] + top - 2)
    x1, y1 = min(frame.shape[1], org[0] + right + 2), min(frame.shape[0], org[1] + bottom + 2)
    if x1 <= x0 or y1 <= y0:
        return
    patch = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
    ImageDraw.Draw(patch).text(
        (org[0] - x0, org[1] - y0), text, font=font, fill=(color[2], color[1], color[0]), anchor="ls",
    )
    frame[y0:y1, x0:x1] = cv2.cvtColor(np.asarray(patch), cv2.COLOR_RGB2BGR)
