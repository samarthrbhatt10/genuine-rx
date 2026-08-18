"""
Full OCR Resolver Pipeline.
Combines barcode detection, image pre-processing, OCR, and fuzzy matching.
"""
import cv2

from .barcode import detect_barcode
from .image_prep import preprocess_for_ocr
from .ocr import extract_text
from .matcher import match_medicine_text, ResolveResult

def resolve_prescription_image(
    image_path: str,
    catalog: dict[str, dict],
    barcode_catalog: dict[str, int] = None
) -> ResolveResult:
    """
    Process an image and return the best matched medicine.
    
    Pipeline:
      1. Barcode detection shortcut. If a barcode is found and exists in 
         the barcode_catalog, return an exact, high-confidence match immediately.
      2. If no barcode, run OpenCV pre-processing (deskew + CLAHE).
      3. Run Tesseract OCR on the processed image.
      4. Fuzzy match the extracted text against the medicine catalog.
    
    Args:
        image_path: Path to the prescription or medicine strip image.
        catalog: Dict for fuzzy matching text -> medicine dict.
        barcode_catalog: Dict mapping barcode strings to medicine_ids.
        
    Returns:
        ResolveResult per the API contract.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
        
    # 1. Barcode Shortcut (Delight feature)
    if barcode_catalog is not None:
        barcode_str = detect_barcode(img)
        if barcode_str and barcode_str in barcode_catalog:
            med_id = barcode_catalog[barcode_str]
            # Find the brand_name from the main catalog for this id
            brand_name = None
            for key, med in catalog.items():
                if med["medicine_id"] == med_id:
                    brand_name = med["brand_name"]
                    break
            
            if brand_name:
                return ResolveResult(
                    matched=True,
                    medicine_id=med_id,
                    brand_name=brand_name,
                    confidence=1.0,
                    needs_confirmation=False
                )

    # 2. Image Pre-processing
    processed_img = preprocess_for_ocr(image_path)
    
    # 3. OCR
    extracted_text = extract_text(processed_img)
    
    # 4. Match
    return match_medicine_text(extracted_text, catalog)
