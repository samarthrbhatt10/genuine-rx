"""
Barcode detection shortcut for OpenCV.
"""
import cv2
import numpy as np

def detect_barcode(img: np.ndarray) -> str | None:
    """Attempt to detect and decode a barcode in the image.
    
    Returns the decoded string, or None if no barcode is found.
    """
    try:
        detector = cv2.barcode.BarcodeDetector()
        retval, decoded_info, decoded_type, points = detector.detectAndDecode(img)
        if retval and decoded_info:
            # If multiple barcodes are found, return the first valid one
            for info in decoded_info:
                if info:
                    return info
    except AttributeError:
        # OpenCV might not have barcode module built-in on some distributions
        pass
    
    return None
