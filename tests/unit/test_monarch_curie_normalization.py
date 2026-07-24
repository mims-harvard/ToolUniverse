"""Unit test: Monarch entity CURIE underscore->colon normalization.

Regression: Mondo_get_disease (and other MonarchV3Tool entity lookups) built
'/entity/{disease_id}' verbatim, so the underscore CURIE OpenTargets emits
('MONDO_0004995', 'EFO_0008572', 'Orphanet_238583') 404'd -- Monarch needs the
colon form 'MONDO:0004995'. Feeding one tool's output into Mondo_get_disease
broke with a bare 404 that never revealed the delimiter was the cause.
"""
import pytest

from tooluniverse.monarch_v3_tool import _normalize_curie


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MONDO_0004995", "MONDO:0004995"),
        ("EFO_0008572", "EFO:0008572"),
        ("Orphanet_238583", "Orphanet:238583"),
        ("HP_0001250", "HP:0001250"),
        ("NCBITaxon_9606", "NCBITaxon:9606"),
    ],
)
def test_underscore_curie_normalized_to_colon(raw, expected):
    assert _normalize_curie(raw) == expected


@pytest.mark.unit
def test_colon_curie_unchanged():
    assert _normalize_curie("MONDO:0004995") == "MONDO:0004995"


@pytest.mark.unit
def test_whitespace_trimmed():
    assert _normalize_curie("  MONDO_0004995 ") == "MONDO:0004995"


@pytest.mark.unit
def test_non_curie_strings_untouched():
    # A plain search term or a symbol must not be rewritten.
    assert _normalize_curie("BRCA2") == "BRCA2"
    assert _normalize_curie("Rett syndrome") == "Rett syndrome"
    # Non-string passthrough.
    assert _normalize_curie(None) is None
