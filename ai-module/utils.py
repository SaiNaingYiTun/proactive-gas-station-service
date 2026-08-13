import cv2
from config import UPSCALE_TARGET_W


def upscale(crop, target_w=UPSCALE_TARGET_W):
    h, w = crop.shape[:2]
    if w > 0 and w < target_w:
        crop = cv2.resize(crop, None, fx=target_w / w, fy=target_w / w, interpolation=cv2.INTER_CUBIC)
    return crop


def preprocess(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    return gray


def sharpness_score(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()
