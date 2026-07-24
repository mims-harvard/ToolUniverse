"""Unit test for HPO term-id normalization.

Regression: HPO_get_term (and get_associated_*/hierarchy) normalized a term id
with `if not term_id.startswith("HP:"): term_id = f"HP:{term_id}"`. For the
underscore CURIE `HP_0001250` -- exactly what OpenTargets emits for phenotype
HPO ids (phenotypeHPO.id) -- that produced `HP:HP_0001250` and a 404, breaking
the OpenTargets-phenotype -> HPO_get_term chain a clinician follows.
"""
import pytest

from tooluniverse.hpo_tool import _normalize_hpo_id


@pytest.mark.unit
def test_underscore_curie_is_normalized_to_colon():
    assert _normalize_hpo_id("HP_0001250") == "HP:0001250"


@pytest.mark.unit
def test_colon_curie_is_unchanged():
    assert _normalize_hpo_id("HP:0001250") == "HP:0001250"


@pytest.mark.unit
def test_bare_digits_get_prefix():
    assert _normalize_hpo_id("0001250") == "HP:0001250"


@pytest.mark.unit
def test_lowercase_and_whitespace_are_canonicalized():
    assert _normalize_hpo_id("  hp_0001250 ") == "HP:0001250"
    assert _normalize_hpo_id("hp:0001250") == "HP:0001250"
