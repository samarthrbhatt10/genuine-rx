"""
Unit tests for matching_engine.normalizer.

No database, no network.
"""
from decimal import Decimal

import pytest

from matching_engine.normalizer import normalize_salt_name, strength_to_mg


class TestNormalizeSaltName:
    def test_strips_hydrochloride(self):
        assert normalize_salt_name("Metformin Hydrochloride") == "metformin"

    def test_strips_hcl(self):
        assert normalize_salt_name("Metformin HCl") == "metformin"

    def test_strips_calcium(self):
        assert normalize_salt_name("Atorvastatin Calcium") == "atorvastatin"

    def test_lowercases(self):
        assert normalize_salt_name("PARACETAMOL") == "paracetamol"

    def test_strips_punctuation(self):
        assert normalize_salt_name("Paracetamol-500") == "paracetamol 500"

    def test_collapses_whitespace(self):
        assert normalize_salt_name("  Metformin   HCl  ") == "metformin"

    def test_preserves_non_noise_words(self):
        # "tab" is not a noise suffix — it should survive
        result = normalize_salt_name("Paracetamol Tab")
        assert "paracetamol" in result
        assert "tab" in result

    def test_empty_string(self):
        assert normalize_salt_name("") == ""


class TestStrengthToMg:
    def test_mg_passthrough(self):
        assert strength_to_mg(500, "mg") == Decimal("500")

    def test_g_to_mg(self):
        assert strength_to_mg(0.5, "g") == Decimal("500")

    def test_mcg_to_mg(self):
        assert strength_to_mg(10, "mcg") == Decimal("0.010")

    def test_ug_alias(self):
        assert strength_to_mg(10, "ug") == Decimal("0.010")

    def test_unicode_mu_alias(self):
        assert strength_to_mg(10, "µg") == Decimal("0.010")

    def test_iu_passthrough(self):
        assert strength_to_mg(400, "iu") == Decimal("400")

    def test_string_value_input(self):
        assert strength_to_mg("250", "mg") == Decimal("250")

    def test_decimal_value_input(self):
        assert strength_to_mg(Decimal("0.25"), "g") == Decimal("250")

    def test_unknown_unit_raises(self):
        with pytest.raises(ValueError, match="Unknown strength unit"):
            strength_to_mg(10, "ml")

    def test_case_insensitive_unit(self):
        assert strength_to_mg(500, "MG") == Decimal("500")
        assert strength_to_mg(0.5, "G") == Decimal("500")
