"""
Tesseract OCR wrapper.

Medicine photos are rarely clean, so we OCR several variants of the image
(contrast-normalised, adaptive-threshold, inverted for light-on-dark strips)
with different page-segmentation modes and return all text found. The fuzzy
matcher picks the best medicine name out of it.
"""
import logging

import cv2
import numpy as np
import pytesseract

logger = logging.getLogger(__name__)

# 6 = uniform block, 11 = sparse text (finds brand names scattered on packaging)
_PSM_MODES = (6, 11)


def _variants(img: np.ndarray) -> list[np.ndarray]:
    adaptive = cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )
    return [img, adaptive, cv2.bitwise_not(img)]


def extract_text(img: np.ndarray) -> str:
    """Run Tesseract on several variants of the pre-processed image.

    Returns the extracted raw text (all passes joined by newlines).
    Raises RuntimeError if the Tesseract binary is not installed.
    """
    chunks: list[str] = []
    for variant in _variants(img):
        for psm in _PSM_MODES:
            try:
                text = pytesseract.image_to_string(variant, config=f"--oem 3 --psm {psm}")
            except (pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
                raise RuntimeError(
                    "Tesseract OCR is not installed. Install it "
                    "(macOS: `brew install tesseract`, Ubuntu: `apt install tesseract-ocr`)."
                ) from exc
            if text.strip():
                chunks.append(text)
    logger.info("OCR extracted %d chars", sum(len(c) for c in chunks))
    return "\n".join(chunks)
