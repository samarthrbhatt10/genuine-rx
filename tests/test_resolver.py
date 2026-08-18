"""
Unit tests for matching_engine.resolver.

Uses an in-memory salt_table fixture — no database, no network.
"""
import pytest

from matching_engine.types import SaltEntry
from matching_engine.resolver import resolve_alias


@pytest.fixture
def salt_table() -> list[SaltEntry]:
    return [
        SaltEntry(
            salt_id=1,
            canonical_name="Paracetamol",
            aliases=frozenset({"pcm", "acetaminophen", "paracetamol tab", "paracetamol 500"}),
        ),
        SaltEntry(
            salt_id=2,
            canonical_name="Metformin",
            aliases=frozenset({"metformin hcl", "metformin hydrochloride", "mf 500"}),
        ),
        SaltEntry(
            salt_id=3,
            canonical_name="Atorvastatin",
            aliases=frozenset({"atorva", "atorvastatin calcium", "atorvastatin 10"}),
        ),
    ]


class TestResolveAlias:
    def test_exact_canonical_match(self, salt_table):
        result = resolve_alias("Paracetamol", salt_table)
        assert result is not None
        assert result.salt_id == 1

    def test_case_insensitive_canonical(self, salt_table):
        result = resolve_alias("PARACETAMOL", salt_table)
        assert result is not None
        assert result.salt_id == 1

    def test_exact_alias_match(self, salt_table):
        result = resolve_alias("PCM", salt_table)
        assert result is not None
        assert result.salt_id == 1

    def test_alias_case_insensitive(self, salt_table):
        result = resolve_alias("pcm", salt_table)
        assert result is not None
        assert result.salt_id == 1

    def test_normalised_canonical_match(self, salt_table):
        # "Metformin Hydrochloride" normalises to "metformin", which matches
        result = resolve_alias("Metformin Hydrochloride", salt_table)
        assert result is not None
        assert result.salt_id == 2

    def test_normalised_alias_match(self, salt_table):
        # "Atorvastatin Calcium" is an alias stored lowercase
        result = resolve_alias("Atorvastatin Calcium", salt_table)
        assert result is not None
        assert result.salt_id == 3

    def test_unresolvable_returns_none(self, salt_table):
        result = resolve_alias("Ibuprofen", salt_table)
        assert result is None

    def test_empty_string_returns_none(self, salt_table):
        result = resolve_alias("", salt_table)
        assert result is None

    def test_whitespace_only_returns_none(self, salt_table):
        result = resolve_alias("   ", salt_table)
        assert result is None
