"""MyVariant_get_pathogenicity_scores must not answer "no scores" when one exists.

Regression for Fix-R33. MyVariant.info can file several records under one rsID,
and `/variant/<rsid>` answers with the highest-scoring one. For rs267606617 that
is `chrMT:m.1555A>G`, a dbSNP-only stub, while the CADD score lives on the
sibling `chrMT:g.1555A>G` -- so a tool whose entire purpose is pathogenicity
scores replied with no scores for a variant that has one.

Verified live before the fix:

    curl 'https://myvariant.info/v1/variant/rs267606617?fields=_id,cadd.phred'
      -> {"_id": "chrMT:m.1555A>G"}                       # no score
    curl 'https://myvariant.info/v1/query?q=rs267606617&fields=_id,cadd.phred'
      -> total 2: chrMT:m.1555A>G (no score)
                  chrMT:g.1555A>G  cadd.phred 9.793

The fix is additive and does not swap records: `data` still holds exactly the
record MyVariant resolved, and the siblings that do carry the data are reported
in the new top-level `sibling_variant_ids_with_requested_fields`,
`sibling_records_with_requested_fields` and `sibling_record_note` keys. The
extra request is confined to the case that motivates it -- an rsID input whose
resolved record carries none of the requested annotation fields -- so the common
path costs nothing.

The keys say "requested fields" rather than "scores" because the same
/variant/<id> handler backs MyVariant_get_variant_annotation, where the sibling
may carry ClinVar significance or gnomAD frequencies rather than a score.

All assertions run against synthetic MyVariant payloads -- no network.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.mygene_tool import MyVariantTool  # noqa: E402

pytestmark = pytest.mark.unit

SCORE_FIELDS = (
    "dbnsfp.revel.score,cadd.phred,clinvar.rcv.clinical_significance,dbsnp.rsid"
)

PATHOGENICITY_CONFIG = {
    "name": "MyVariant_get_pathogenicity_scores",
    "type": "MyVariantTool",
    "fields": {"operation": "get_variant"},
    "parameter": {"properties": {"fields": {"default": SCORE_FIELDS}}},
}

# The stub /variant/rs267606617 resolves to: an id and an rsid, nothing scorable.
STUB_RECORD = {
    "_id": "chrMT:m.1555A>G",
    "_version": 1,
    "dbsnp": {"rsid": "rs267606617"},
}
SIBLING_HIT = {
    "_id": "chrMT:g.1555A>G",
    "_score": 2.760395,
    "cadd": {"phred": 9.793},
}
SCORED_RECORD = {"_id": "chr10:g.96541616G>C", "cadd": {"phred": 22.1}}


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _run(arguments, *payloads):
    """Serve one canned payload per request; returns (result, request calls)."""
    tool = MyVariantTool(PATHOGENICITY_CONFIG)
    with patch(
        "tooluniverse.mygene_tool.requests.get",
        side_effect=[_response(p) for p in payloads],
    ) as get:
        result = tool.run(arguments)
    return result, get.call_args_list


def _with_sibling(arguments=None):
    return _run(
        arguments or {"variant_id": "rs267606617"},
        STUB_RECORD,
        {"took": 3, "total": 2, "hits": [dict(STUB_RECORD), SIBLING_HIT]},
    )


def test_scores_on_a_sibling_record_are_surfaced():
    result, _ = _with_sibling()

    assert result["sibling_variant_ids_with_requested_fields"] == ["chrMT:g.1555A>G"]
    assert result["sibling_records_with_requested_fields"] == [SIBLING_HIT]


def test_the_resolved_record_is_reported_not_replaced():
    """Swapping in the sibling would silently answer about a different record."""
    result, _ = _with_sibling()

    assert result["status"] == "success"
    assert result["data"] == STUB_RECORD


def test_note_explains_the_hazard_and_names_both_ids():
    note = _with_sibling()[0]["sibling_record_note"]

    assert "rs267606617" in note
    assert "chrMT:m.1555A>G" in note
    assert "chrMT:g.1555A>G" in note
    assert "sibling_records_with_requested_fields" in note


def test_common_path_costs_no_extra_request():
    """The resolved record already has a score, so there is nothing to cross-check."""
    result, calls = _run({"variant_id": "rs45478192"}, SCORED_RECORD)

    assert len(calls) == 1
    assert "sibling_records_with_requested_fields" not in result


def test_hgvs_input_never_triggers_the_lookup():
    """An HGVS id addresses one record; there is no sibling ambiguity to resolve."""
    result, calls = _run({"variant_id": "chrMT:m.1555A>G"}, STUB_RECORD)

    assert len(calls) == 1
    assert "sibling_records_with_requested_fields" not in result


def test_a_list_of_resolved_records_is_scanned_before_the_lookup():
    """An rsID can resolve to several records; one scored record is enough."""
    result, calls = _run({"variant_id": "rs4244285"}, [STUB_RECORD, SCORED_RECORD])

    assert len(calls) == 1
    assert "sibling_records_with_requested_fields" not in result


def test_siblings_without_scores_are_not_reported():
    """A second metadata stub is noise, not an answer."""
    other_stub = {"_id": "chrMT:g.1555A>C", "dbsnp": {"rsid": "rs267606617"}}
    result, _ = _run(
        {"variant_id": "rs267606617"},
        STUB_RECORD,
        {"took": 3, "total": 2, "hits": [dict(STUB_RECORD), other_stub]},
    )

    assert "sibling_records_with_requested_fields" not in result


def test_the_lookup_inherits_the_requested_assembly():
    _, calls = _with_sibling({"variant_id": "rs267606617", "assembly": "hg38"})

    assert calls[1].kwargs["params"]["assembly"] == "hg38"
    assert calls[1].kwargs["params"]["q"] == "rs267606617"


def test_the_lookup_omits_assembly_on_the_hg19_default():
    """Same omission rule as the primary request, because it is the same code."""
    _, calls = _with_sibling()

    assert "assembly" not in calls[1].kwargs["params"]


def test_a_failed_lookup_leaves_the_primary_answer_intact():
    """The cross-check is a bonus; failing it must not fail the answer."""
    tool = MyVariantTool(PATHOGENICITY_CONFIG)
    with patch(
        "tooluniverse.mygene_tool.requests.get",
        side_effect=[_response(STUB_RECORD), requests.ConnectionError("boom")],
    ):
        result = tool.run({"variant_id": "rs267606617"})

    assert result["status"] == "success"
    assert result["data"] == STUB_RECORD
    assert "sibling_records_with_requested_fields" not in result


def test_fields_all_still_cross_checks():
    """Asking for everything does not put CADD on the stub; the hazard is the same."""
    result, _ = _with_sibling({"variant_id": "rs267606617", "fields": "all"})

    assert result["sibling_records_with_requested_fields"] == [SIBLING_HIT]


def test_a_locator_field_in_the_request_does_not_switch_the_check_off():
    """`chrom` locates the variant; it is not the annotation the caller asked for."""
    located_stub = dict(STUB_RECORD, chrom="MT")
    result, _ = _run(
        {"variant_id": "rs267606617", "fields": "cadd.phred,dbsnp.rsid,chrom"},
        located_stub,
        {"took": 3, "total": 2, "hits": [located_stub, SIBLING_HIT]},
    )

    assert result["sibling_records_with_requested_fields"] == [SIBLING_HIT]


def test_annotation_tool_gets_the_same_cross_check():
    """The same handler backs MyVariant_get_variant_annotation; so does the hazard."""
    tool = MyVariantTool(
        {
            "name": "MyVariant_get_variant_annotation",
            "type": "MyVariantTool",
            "fields": {"operation": "get_variant"},
            "parameter": {
                "properties": {
                    "fields": {"default": "dbsnp,clinvar,cadd,gnomad_genome,dbnsfp"}
                }
            },
        }
    )
    clinvar_sibling = {
        "_id": "chrMT:g.1555A>G",
        "clinvar": {"rcv": [{"clinical_significance": "Pathogenic"}]},
    }
    with patch(
        "tooluniverse.mygene_tool.requests.get",
        side_effect=[
            _response(STUB_RECORD),
            _response({"hits": [dict(STUB_RECORD), clinvar_sibling]}),
        ],
    ):
        result = tool.run({"variant_id": "rs267606617"})

    assert result["data"] == STUB_RECORD
    assert result["sibling_records_with_requested_fields"] == [clinvar_sibling]
