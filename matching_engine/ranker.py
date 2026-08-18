"""
Ranker — sorts SubstituteResult lists by the fixed contract order:
  is_jan_aushadhi DESC, price ASC

The sort key is fixed per 04_API_CONTRACT.md. Do not add configurable
sort parameters here — ranking logic lives in one place only.
"""
from .types import SubstituteResult


def rank_substitutes(substitutes: list[SubstituteResult]) -> list[SubstituteResult]:
    """Return a new list sorted Jan-Aushadhi-first, then cheapest first.

    Jan Aushadhi entries always appear before branded equivalents at the
    same price tier, regardless of medicine_id or insertion order.
    """
    return sorted(
        substitutes,
        key=lambda r: (not r.is_jan_aushadhi, r.price),
    )
