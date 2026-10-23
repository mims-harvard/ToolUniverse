from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.lovd_tool import LOVDTool


pytestmark = pytest.mark.unit


def _tool(operation):
    return LOVDTool({"fields": {"operation": operation}})


def _response(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    return response


def _variant(dbid="TP53_010464", dna="NM_000546.5:c.*2609C>A"):
    return {
        "symbol": "TP53",
        "Variant/DBID": dbid,
        "Variant/DNA": [dna],
    }


@pytest.mark.parametrize(
    "operation,arguments,error",
    [
        ("get_gene", {"gene_symbol": 1}, "gene_symbol"),
        ("get_variants", {"gene_symbol": "TP53", "limit": 10}, "Unrecognized"),
        ("search_variants", {"gene_symbol": "TP53"}, "exactly one"),
        (
            "search_variants",
            {
                "gene_symbol": "TP53",
                "variant_dbid": "TP53_010464",
                "dna_notation": "c.*2609C>A",
            },
            "exactly one",
        ),
        (
            "search_variants",
            {"gene_symbol": "TP53", "variant_dbid": 1},
            "variant_dbid",
        ),
    ],
)
def test_invalid_or_conflicting_controls_are_rejected_before_network(
    operation, arguments, error
):
    with patch("tooluniverse.lovd_tool.requests.get") as get:
        result = _tool(operation).run(arguments)
    assert result["status"] == "error"
    assert error in result["error"]
    get.assert_not_called()


def test_gene_response_symbol_is_verified():
    with patch.object(
        LOVDTool,
        "_make_request",
        return_value=_response({"symbol": "TP53", "hgnc_id": 11998}),
    ):
        result = _tool("get_gene").run({"gene_symbol": "tp53"})
    assert result["data"]["hgnc_id"] == 11998
    assert result["metadata"]["returned_symbol_verified"] is True
    assert result["metadata"]["source_record_complete"] is True


def test_gene_response_mismatch_is_an_error():
    with patch.object(
        LOVDTool,
        "_make_request",
        return_value=_response({"symbol": "BRCA1"}),
    ):
        result = _tool("get_gene").run({"gene_symbol": "TP53"})
    assert result["status"] == "error"
    assert result["returned_symbol"] == "BRCA1"


def test_full_variant_response_has_explicit_unpaginated_completeness():
    variants = [_variant(), _variant(dbid="TP53_010424", dna="NM_000546.5:c.1A>G")]
    with patch.object(LOVDTool, "_make_request", return_value=_response(variants)):
        result = _tool("get_variants").run({"gene_symbol": "TP53"})
    assert result["metadata"]["returned"] == 2
    assert result["metadata"]["result_set_complete"] is True
    assert "unpaginated" in result["metadata"]["completeness_basis"]


def test_variant_for_different_gene_is_rejected():
    variant = _variant()
    variant["symbol"] = "BRCA1"
    with patch.object(LOVDTool, "_make_request", return_value=_response([variant])):
        result = _tool("get_variants").run({"gene_symbol": "TP53"})
    assert result["status"] == "error"
    assert "different gene" in result["error"]


def test_filter_404_empty_array_is_no_match_not_missing_gene():
    with patch.object(
        LOVDTool, "_make_request", return_value=_response([], status=404)
    ):
        result = _tool("search_variants").run(
            {"gene_symbol": "TP53", "variant_dbid": "NOT_REAL"}
        )
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["matches"] == 0
    assert result["metadata"]["filter_verified"] is True


def test_dbid_filter_is_checked_against_every_record():
    with patch.object(
        LOVDTool, "_make_request", return_value=_response([_variant(dbid="OTHER")])
    ):
        result = _tool("search_variants").run(
            {"gene_symbol": "TP53", "variant_dbid": "TP53_010464"}
        )
    assert result["status"] == "error"
    assert result["mismatches"] == ["OTHER"]


def test_dna_filter_accepts_refseq_prefixed_exact_notation():
    with patch.object(LOVDTool, "_make_request", return_value=_response([_variant()])):
        result = _tool("search_variants").run(
            {"gene_symbol": "TP53", "dna_notation": "c.*2609C>A"}
        )
    assert result["status"] == "success"
    assert result["metadata"]["matches"] == 1
    assert result["metadata"]["filter_verified"] is True


def test_non_json_response_is_structured_error_not_exception():
    response = _response(None)
    response.json.side_effect = ValueError("bad json")
    with patch.object(LOVDTool, "_make_request", return_value=response):
        result = _tool("get_gene").run({"gene_symbol": "TP53"})
    assert result["status"] == "error"
    assert "invalid JSON" in result["error"]
