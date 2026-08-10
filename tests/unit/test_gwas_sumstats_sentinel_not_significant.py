"""Regression guard: GWASSumStats_get_region_associations reported the GWAS
Catalog missing-value sentinel (-99) as a genome-wide-significant hit.

Confirmed live against
chr2:179000000-179600000 with p_upper=5e-8: the upstream API itself returns
rows whose ``p_value`` is ``-99.0`` (and whose ``odds_ratio`` is also
``-99.0``), because the server-side threshold test ``-99 <= 5e-8`` is
numerically true. The tool then re-sorted ascending by p-value, which lifted
every ``-99`` row *above* the two genuinely significant variants
(rs10174774 p=5.31e-24, rs10170520 p=5.71e-23), so a size=10 query answered
with 8 sentinels on top and the real hits at the bottom.

Note the upstream ``code`` field cannot be used as the discriminator: it is
the harmonisation code, and code 10 ("forward strand, alleles already in the
correct orientation") is a *success* code that the sentinel rows happen to
carry, while the two real hits carry code 14 ("invalid for harmonisation",
their alleles are null). The payloads below mirror that real shape.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gwas_sumstats_tool import GWASSumStatsTool

pytestmark = pytest.mark.unit


REGION_ARGS = {
    "chromosome": 2,
    "bp_lower": 179000000,
    "bp_upper": 179600000,
    "p_upper": 5e-8,
    "size": 5,
}


def _tool():
    return GWASSumStatsTool(
        {
            "name": "gwas_sumstats_test",
            "fields": {"endpoint_type": "get_region_associations"},
        }
    )


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body or {}
    return r


def _real_hit(variant_id, position, p_value):
    """Mirrors a GCST001255 row: real p-value, no alleles, harmonisation code 14."""
    return {
        "variant_id": variant_id,
        "chromosome": 2,
        "base_pair_location": position,
        "p_value": p_value,
        "beta": None,
        "odds_ratio": None,
        "effect_allele": None,
        "other_allele": None,
        "effect_allele_frequency": None,
        "code": 14,
        "study_accession": "GCST001255",
        "trait": ["EFO_0001359"],
        "ci_lower": None,
        "ci_upper": None,
    }


def _sentinel_row(variant_id, position, eaf):
    """Mirrors a GCST004415 row: -99 sentinel p-value/OR, harmonisation code 10."""
    return {
        "variant_id": variant_id,
        "chromosome": 2,
        "base_pair_location": position,
        "p_value": -99.0,
        "beta": None,
        "odds_ratio": -99.0,
        "effect_allele": "C",
        "other_allele": "T",
        "effect_allele_frequency": eaf,
        "code": 10,
        "study_accession": "GCST004415",
        "trait": ["EFO_0001075"],
        "ci_lower": None,
        "ci_upper": None,
    }


def _payload(rows):
    return {"_embedded": {"associations": {str(i): r for i, r in enumerate(rows)}}}


MIXED_PAYLOAD = _payload(
    [
        _real_hit("rs10170520", 179229886, 5.708e-23),
        _real_hit("rs10174774", 179231834, 5.3109999999999995e-24),
        _sentinel_row("rs571763084", 179002622, 1.414e-05),
        _sentinel_row("rs181634435", 179003529, 0.0006703999999999999),
        _sentinel_row("rs531141128", 179004593, 0.0006997),
    ]
)

CLEAN_PAYLOAD = _payload(
    [
        _real_hit("rs10170520", 179229886, 5.708e-23),
        _real_hit("rs10174774", 179231834, 5.3109999999999995e-24),
    ]
)


def _run(payload, args=None):
    tool = _tool()
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get",
        return_value=_resp(200, payload),
    ):
        return tool.run(dict(args if args is not None else REGION_ARGS))


def test_sentinel_rows_do_not_satisfy_p_upper():
    result = _run(MIXED_PAYLOAD)

    assert result["status"] == "success"
    returned = result["data"]
    assert [row["p_value"] for row in returned] == pytest.approx(
        [5.3109999999999995e-24, 5.708e-23]
    )
    # No -99 sentinel survived the genome-wide-significance filter.
    assert all(row["p_value"] > 0 for row in returned)
    assert not any(row["variant_id"].startswith("rs5717") for row in returned)


def test_real_hits_are_returned_most_significant_first():
    returned = _run(MIXED_PAYLOAD)["data"]

    ids = [row["variant_id"] for row in returned]
    assert ids == ["rs10174774", "rs10170520"]
    assert returned[0]["p_value"] == pytest.approx(5.3109999999999995e-24)


def test_excluded_sentinel_count_is_disclosed():
    metadata = _run(MIXED_PAYLOAD)["metadata"]

    assert metadata["sentinel_rows_excluded"] == 3
    assert metadata["num_associations"] == 2
    assert "-99" in metadata["sentinel_note"]


def test_rows_expose_code_and_reported_flag():
    returned = _run(MIXED_PAYLOAD)["data"]

    for row in returned:
        assert row["p_value_reported"] is True
        assert row["code"] == 14  # upstream harmonisation code is passed through


def test_sentinels_kept_but_flagged_and_sorted_last_when_no_threshold():
    """Without a p_upper threshold the caller asked for the whole region, so
    sentinel rows are retained -- but flagged, and never above a real hit."""
    args = dict(REGION_ARGS, p_upper=None)
    result = _run(MIXED_PAYLOAD, args)

    returned = result["data"]
    assert len(returned) == 5
    assert result["metadata"]["sentinel_rows_excluded"] == 0
    assert [row["p_value_reported"] for row in returned] == [
        True,
        True,
        False,
        False,
        False,
    ]
    assert [row["variant_id"] for row in returned[:2]] == [
        "rs10174774",
        "rs10170520",
    ]


def test_all_valid_response_is_unchanged_apart_from_added_keys():
    result = _run(CLEAN_PAYLOAD)

    assert result["status"] == "success"
    assert result["metadata"]["sentinel_rows_excluded"] == 0
    assert "sentinel_note" not in result["metadata"]
    assert result["metadata"]["num_associations"] == 2

    returned = result["data"]
    assert [row["variant_id"] for row in returned] == ["rs10174774", "rs10170520"]
    assert set(returned[0]) == {
        "variant_id",
        "chromosome",
        "position",
        "p_value",
        "p_value_reported",
        "code",
        "beta",
        "odds_ratio",
        "effect_allele",
        "other_allele",
        "effect_allele_frequency",
        "study_accession",
        "trait",
        "ci_lower",
        "ci_upper",
    }
    assert returned[0]["position"] == 179231834
    assert returned[0]["study_accession"] == "GCST001255"
    assert returned[0]["trait"] == ["EFO_0001359"]
