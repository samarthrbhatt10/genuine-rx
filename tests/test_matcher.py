"""
Unit tests for matching_engine.matcher (find_substitutes).

Covers the three DoD cases from 06_FEATURES.md Module B:
  - single-salt match
  - multi-salt combination match
  - zero-match case

Plus: alias resolution, caution flag, ranking, order-independence,
and unresolvable salt error.

No database, no network — pure in-memory fixture.
"""
from decimal import Decimal

import pytest

from matching_engine import find_substitutes
from matching_engine.types import (
    MedicineEntry,
    PriceEntry,
    SaltEntry,
    SaltRequirement,
)


# --------------------------------------------------------------------------- #
# Shared test fixture
# --------------------------------------------------------------------------- #

@pytest.fixture
def salt_table() -> list[SaltEntry]:
    return [
        SaltEntry(
            salt_id=1,
            canonical_name="Paracetamol",
            aliases=frozenset({"pcm", "acetaminophen", "paracetamol tab"}),
        ),
        SaltEntry(
            salt_id=2,
            canonical_name="Metformin",
            aliases=frozenset({"metformin hcl", "metformin hydrochloride", "mf 500"}),
        ),
        SaltEntry(
            salt_id=3,
            canonical_name="Atorvastatin",
            aliases=frozenset({"atorva", "atorvastatin calcium"}),
        ),
        SaltEntry(
            salt_id=4,
            canonical_name="Glibenclamide",
            aliases=frozenset({"glyburide", "glibenclamide 5"}),
        ),
    ]


# helper
def _s(salt_id: int, mg: str) -> SaltRequirement:
    return SaltRequirement(salt_id=salt_id, strength_mg=Decimal(mg))


@pytest.fixture
def medicine_table() -> list[MedicineEntry]:
    paracetamol_500 = frozenset({_s(1, "500")})
    metformin_500 = frozenset({_s(2, "500")})
    atorvastatin_10 = frozenset({_s(3, "10")})
    combo = frozenset({_s(2, "500"), _s(4, "5")})   # Metformin 500 + Glibenclamide 5

    return [
        # Paracetamol 500 mg family
        MedicineEntry(1, "Crocin",                     "tablet", "GSK Pharma",  False, paracetamol_500),
        MedicineEntry(2, "Calpol",                     "tablet", "GSK Pharma",  False, paracetamol_500),
        MedicineEntry(3, "Metacin",                    "tablet", "Pfizer",      False, paracetamol_500),
        MedicineEntry(4, "Paracetamol (Jan Aushadhi)", "tablet", "PMBI",        True,  paracetamol_500),

        # Metformin 500 mg (single-salt)
        MedicineEntry(5, "Glycomet",                   "tablet", "USV",         False, metformin_500),
        MedicineEntry(6, "Metformin (Jan Aushadhi)",   "tablet", "PMBI",        True,  metformin_500),

        # Atorvastatin 10 mg (on caution list)
        MedicineEntry(7, "Atorva",                     "tablet", "Zydus",       False, atorvastatin_10),

        # Combination: Metformin 500 + Glibenclamide 5
        MedicineEntry(8, "Glucovance",                 "tablet", "Merck",       False, combo),
        MedicineEntry(9, "Metanorm-G (Jan Aushadhi)",  "tablet", "PMBI",        True,  combo),
    ]


@pytest.fixture
def price_table() -> list[PriceEntry]:
    return [
        PriceEntry(1, "primary_pharmacy",  Decimal("30.00")),
        PriceEntry(2, "primary_pharmacy",  Decimal("29.00")),
        PriceEntry(3, "primary_pharmacy",  Decimal("18.50")),
        PriceEntry(4, "jan_aushadhi_pdf",  Decimal("3.50")),
        PriceEntry(5, "primary_pharmacy",  Decimal("40.00")),
        PriceEntry(6, "jan_aushadhi_pdf",  Decimal("5.50")),
        PriceEntry(7, "primary_pharmacy",  Decimal("55.00")),
        PriceEntry(8, "primary_pharmacy",  Decimal("75.00")),
        PriceEntry(9, "jan_aushadhi_pdf",  Decimal("12.00")),
    ]


@pytest.fixture
def caution_salt_ids() -> dict[int, str]:
    # Atorvastatin (salt_id=3) is on the caution list
    return {3: "Statin — check for drug-drug interactions before switching brand"}


# --------------------------------------------------------------------------- #
# DoD case 1: single-salt match
# --------------------------------------------------------------------------- #

class TestSingleSaltMatch:
    def test_returns_all_brands(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 4
        brand_names = {r.brand_name for r in results}
        assert "Crocin" in brand_names
        assert "Calpol" in brand_names
        assert "Metacin" in brand_names
        assert "Paracetamol (Jan Aushadhi)" in brand_names

    def test_jan_aushadhi_ranked_first(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert results[0].is_jan_aushadhi is True
        assert results[0].brand_name == "Paracetamol (Jan Aushadhi)"

    def test_branded_sorted_price_asc_after_jan_aushadhi(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        branded = [r for r in results if not r.is_jan_aushadhi]
        prices = [r.price for r in branded]
        assert prices == sorted(prices)

    def test_jan_aushadhi_has_highest_savings_pct(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        jan = next(r for r in results if r.is_jan_aushadhi)
        # Jan Aushadhi at Rs 3.50 vs most expensive at Rs 30.00
        assert jan.savings_pct is not None
        assert jan.savings_pct == pytest.approx(88.33, abs=0.1)

    def test_most_expensive_has_zero_savings(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        most_expensive = max(results, key=lambda r: r.price)
        assert most_expensive.savings_pct == pytest.approx(0.0)

    def test_no_caution_flag_for_paracetamol(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert all(not r.caution_flag for r in results)


# --------------------------------------------------------------------------- #
# DoD case 2: multi-salt combination match
# --------------------------------------------------------------------------- #

class TestMultiSaltCombinationMatch:
    def test_returns_both_combo_brands(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Metformin", Decimal("500")), ("Glibenclamide", Decimal("5"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 2
        brand_names = {r.brand_name for r in results}
        assert "Glucovance" in brand_names
        assert "Metanorm-G (Jan Aushadhi)" in brand_names

    def test_combo_order_independent(self, salt_table, medicine_table, price_table, caution_salt_ids):
        """Reversed salt order must produce the same results."""
        fwd = find_substitutes(
            [("Metformin", Decimal("500")), ("Glibenclamide", Decimal("5"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        rev = find_substitutes(
            [("Glibenclamide", Decimal("5")), ("Metformin", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert {r.medicine_id for r in fwd} == {r.medicine_id for r in rev}

    def test_combo_jan_aushadhi_first(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Metformin", Decimal("500")), ("Glibenclamide", Decimal("5"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert results[0].is_jan_aushadhi is True

    def test_combo_does_not_match_single_salt(self, salt_table, medicine_table, price_table, caution_salt_ids):
        """Metformin 500 alone must NOT match the combo medicine."""
        results = find_substitutes(
            [("Metformin", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        combo_ids = {8, 9}
        assert not any(r.medicine_id in combo_ids for r in results)


# --------------------------------------------------------------------------- #
# DoD case 3: zero-match
# --------------------------------------------------------------------------- #

class TestZeroMatch:
    def test_wrong_strength_returns_empty(self, salt_table, medicine_table, price_table, caution_salt_ids):
        # Paracetamol 250 mg — not in fixture
        results = find_substitutes(
            [("Paracetamol", Decimal("250"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert results == []

    def test_unpriced_medicine_excluded(self, salt_table, medicine_table, caution_salt_ids):
        # Empty price table — nothing has a price yet
        results = find_substitutes(
            [("Paracetamol", Decimal("500"))],
            salt_table, medicine_table, price_table=[], caution_salt_ids=caution_salt_ids,
        )
        assert results == []


# --------------------------------------------------------------------------- #
# Alias resolution
# --------------------------------------------------------------------------- #

class TestAliasResolution:
    def test_pcm_resolves_to_paracetamol(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("PCM", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 4

    def test_metformin_hcl_resolves(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Metformin HCl", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 2  # Glycomet + Jan Aushadhi

    def test_unresolvable_salt_raises_value_error(self, salt_table, medicine_table, price_table, caution_salt_ids):
        with pytest.raises(ValueError, match="Cannot resolve salt name"):
            find_substitutes(
                [("Ibuprofen", Decimal("400"))],
                salt_table, medicine_table, price_table, caution_salt_ids,
            )

    def test_normalised_alias_metformin_hydrochloride(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Metformin Hydrochloride", Decimal("500"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 2


# --------------------------------------------------------------------------- #
# Caution list
# --------------------------------------------------------------------------- #

class TestCautionList:
    def test_caution_flag_set_for_atorvastatin(self, salt_table, medicine_table, price_table, caution_salt_ids):
        results = find_substitutes(
            [("Atorvastatin", Decimal("10"))],
            salt_table, medicine_table, price_table, caution_salt_ids,
        )
        assert len(results) == 1
        assert results[0].caution_flag is True
        assert results[0].caution_reason is not None
        assert "statin" in results[0].caution_reason.lower()

    def test_no_caution_without_caution_list(self, salt_table, medicine_table, price_table):
        results = find_substitutes(
            [("Atorvastatin", Decimal("10"))],
            salt_table, medicine_table, price_table,
            caution_salt_ids={},  # empty caution list
        )
        assert len(results) == 1
        assert results[0].caution_flag is False
        assert results[0].caution_reason is None
