"""
Tesseract OCR wrapper.
"""
import numpy as np
import pytesseract

def extract_text(img: np.ndarray) -> str:
    """Run Tesseract OCR on the pre-processed OpenCV image.
    
    Returns the extracted raw text.
    """
    # PSM 6: Assume a single uniform block of text.
    return pytesseract.image_to_string(img, config="--psm 6")
