"""
Image pre-processing for OCR: upscale, denoise, safe deskew + CLAHE contrast normalization.
"""
import cv2
import numpy as np

# Tesseract works best when text x-height is ~20-30px; phone photos of strips are often smaller.
_MIN_LONG_SIDE = 1600
_MAX_LONG_SIDE = 2800
# Deskew only corrects small tilts; larger "angles" are almost always a bad estimate.
_MAX_DESKEW_ANGLE = 20.0


def _resize_for_ocr(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    long_side = max(h, w)
    if long_side < _MIN_LONG_SIDE:
        scale = _MIN_LONG_SIDE / long_side
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if long_side > _MAX_LONG_SIDE:
        scale = _MAX_LONG_SIDE / long_side
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return img


def _estimate_skew(img: np.ndarray) -> float:
    """Return the rotation (degrees, cv2 convention) that straightens the text, or 0.0 if unsure."""
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    # Merge characters into text blobs so the rectangle follows text lines, not noise.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 3))
    blobs = cv2.dilate(thresh, kernel, iterations=1)
    contours, _ = cv2.findContours(blobs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    angles, weights = [], []
    min_area = 0.0005 * img.shape[0] * img.shape[1]
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        (_, _), (w, h), ang = cv2.minAreaRect(c)
        if w < h:  # normalise so the long side (text direction) is the width
            ang += 90.0
        # Fold into (-45, 45]
        if ang > 45:
            ang -= 90
        elif ang <= -45:
            ang += 90
        # Only near-horizontal blobs are text lines worth voting on
        if min(w, h) > 0 and max(w, h) / min(w, h) >= 2.0:
            angles.append(ang)
            weights.append(area)
    if not angles:
        return 0.0
    angle = float(np.average(angles, weights=weights))
    return angle if abs(angle) <= _MAX_DESKEW_ANGLE else 0.0


def preprocess_for_ocr(image_path: str) -> np.ndarray:
    """Read image, upscale, denoise, deskew, and apply CLAHE."""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    img = _resize_for_ocr(img)
    img = cv2.fastNlMeansDenoising(img, None, h=10, templateWindowSize=7, searchWindowSize=21)

    angle = _estimate_skew(img)
    if abs(angle) > 0.5:
        (h, w) = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        img = cv2.warpAffine(
            img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)
