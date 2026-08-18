"""
Fuzzy matching logic for OCR text against the medicine catalog.
Uses rapidfuzz for string similarity.
"""
from dataclasses import dataclass
from rapidfuzz import fuzz, process

@dataclass
class ResolveResult:
    matched: bool
    medicine_id: int | None
    brand_name: str | None
    confidence: float
    needs_confirmation: bool
    candidates: list[dict] | None = None


def match_medicine_text(raw_text: str, catalog: dict[str, dict]) -> ResolveResult:
    """
    Match raw_text against the catalog of valid medicine names/aliases.
    
    Args:
        raw_text: The OCR extracted text or typed search string.
        catalog: A dict mapping search keys (brand names, aliases) to 
                 their canonical medicine dict:
                 {"combiflam": {"medicine_id": 4821, "brand_name": "Combiflam"}}
                 
    Returns:
        ResolveResult with the matching outcome per 04_API_CONTRACT.md
    """
    if not raw_text.strip() or not catalog:
        return ResolveResult(
            matched=False, medicine_id=None, brand_name=None,
            confidence=0.0, needs_confirmation=False
        )

    # Convert catalog keys to a list for rapidfuzz
    choices = list(catalog.keys())
    
    # Extract top 3 matches
    # process.extract returns a list of tuples: (matched_string, score, index)
    # score is out of 100.0
    matches = process.extract(
        raw_text.lower(),
        choices,
        scorer=fuzz.WRatio,
        limit=3
    )
    
    if not matches:
        return ResolveResult(
            matched=False, medicine_id=None, brand_name=None,
            confidence=0.0, needs_confirmation=False
        )
        
    best_match_str, best_score, _ = matches[0]
    best_med = catalog[best_match_str]
    confidence = round(best_score / 100.0, 2)
    
    if confidence >= 0.75:
        # High confidence -> direct match
        return ResolveResult(
            matched=True,
            medicine_id=best_med["medicine_id"],
            brand_name=best_med["brand_name"],
            confidence=confidence,
            needs_confirmation=False,
            candidates=None
        )
    else:
        # Low confidence -> needs confirmation, return top 3
        candidates = []
        seen_ids = set()
        
        for match_str, score, _ in matches:
            med = catalog[match_str]
            if med["medicine_id"] not in seen_ids:
                candidates.append({
                    "medicine_id": med["medicine_id"],
                    "brand_name": med["brand_name"],
                    "confidence": round(score / 100.0, 2)
                })
                seen_ids.add(med["medicine_id"])
                
        return ResolveResult(
            matched=True,
            medicine_id=None,
            brand_name=None,
            confidence=confidence,
            needs_confirmation=True,
            candidates=candidates
        )
