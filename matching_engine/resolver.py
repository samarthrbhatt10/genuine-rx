"""
Alias resolver — maps a raw salt name (from OCR or user input) to a
canonical SaltEntry from the in-memory salt table.

Resolution is deterministic and tiered (no fuzzy scores, no LLM):
  1. Exact match on canonical_name      (case-insensitive)
  2. Exact match on any alias           (case-insensitive)
  3. Normalised match on canonical_name (noise-stripped)
  4. Normalised match on any alias      (noise-stripped)

Returns None on failure — caller decides whether to raise or flag.
Never silently falls back to a wrong salt.
"""
from .normalizer import normalize_salt_name
from .types import SaltEntry


def resolve_alias(raw_name: str, salt_table: list[SaltEntry]) -> SaltEntry | None:
    """Find the canonical SaltEntry for *raw_name*.

    Args:
        raw_name:    The name as it came from OCR, user input, or a
                     structured data source.  May be an alias, misspelling,
                     or abbreviation.
        salt_table:  All SaltEntry rows loaded from the `salts` table.
                     Aliases must already be stored in lowercase.

    Returns:
        The matching SaltEntry, or None if no match is found at any tier.
    """
    raw_lower = raw_name.strip().lower()
    raw_norm = normalize_salt_name(raw_name)

    # Tier 1: exact canonical name (case-insensitive)
    for entry in salt_table:
        if entry.canonical_name.lower() == raw_lower:
            return entry

    # Tier 2: exact alias (aliases stored lowercase)
    for entry in salt_table:
        if raw_lower in entry.aliases:
            return entry

    # Tier 3: normalised canonical name
    for entry in salt_table:
        if normalize_salt_name(entry.canonical_name) == raw_norm:
            return entry

    # Tier 4: normalised alias
    for entry in salt_table:
        for alias in entry.aliases:
            if normalize_salt_name(alias) == raw_norm:
                return entry

    return None
