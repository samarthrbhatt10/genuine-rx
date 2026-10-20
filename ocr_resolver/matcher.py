"""
Fuzzy matching logic for OCR text against the medicine catalog.
Uses rapidfuzz for string similarity.
"""
import re
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


def _candidate_phrases(raw_text: str) -> list[str]:
    """
    Break noisy OCR output into short phrases worth matching: each line, each
    word, and each pair/triple of adjacent words (for names like "combiflam plus").
    Matching the whole blob at once lets packaging noise drown out the brand name.
    """
    phrases: list[str] = []
    for line in raw_text.lower().splitlines():
        words = [w for w in re.findall(r"[a-z0-9]{2,}", line)]
        if not words:
            continue
        phrases.append(" ".join(words))
        phrases.extend(words)
        for n in (2, 3):
            phrases.extend(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))
    # de-duplicate, keep order
    return list(dict.fromkeys(phrases)) or [raw_text.lower().strip()]


def _best_matches(raw_text: str, choices: list[str]) -> list[tuple[str, float]]:
    """Best score per catalog key across all phrases; top 3 by score."""
    best: dict[str, float] = {}
    for phrase in _candidate_phrases(raw_text):
        # Short fragments only count if the whole word closely matches (avoid 'cin' -> 'crocin')
        for key, score, _ in process.extract(phrase, choices, scorer=fuzz.ratio, limit=5):
            if score > best.get(key, 0.0):
                best[key] = score
    return sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:3]


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
    matches = [(k, sc, None) for k, sc in _best_matches(raw_text, choices)]
    
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
