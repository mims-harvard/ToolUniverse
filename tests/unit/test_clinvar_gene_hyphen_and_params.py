"""Regression guard for two round-8 ClinVar_search_variants fixes:

Fix-R8B-1: HGNC gene symbols don't contain hyphens, but informal usage
still writes them hyphenated (e.g. "BRCA-2"). ClinVar's [gene] index only
matches the canonical unhyphenated form, so a hyphenated query silently
returned 0 results.

Fix-R5D-1/R8C-1: an unrecognized parameter (e.g. "variant_name", which
doesn't exist -- only "variant_id" does) was silently dropped. When it was
the only param supplied, this produced a generic "at least one search
parameter is required" error; when other valid params were also supplied,
the query ran but silently ignored the unrecognized one with no
indication the filter had zero effect.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _patch_request():
    return patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    )


def test_hyphenated_gene_symbol_is_normalized():
    tool = _tool()
    with _patch_request() as mock_request:
        tool.run({"gene": "BRCA-2"})

    assert "BRCA2[gene]" in mock_request.call_args[0][1]["term"]
    assert "BRCA-2" not in mock_request.call_args[0][1]["term"]


def test_plain_gene_symbol_unaffected():
    tool = _tool()
    with _patch_request() as mock_request:
        tool.run({"gene": "BRCA2"})

    assert "BRCA2[gene]" in mock_request.call_args[0][1]["term"]


def test_unrecognized_param_alone_names_itself_in_error():
    tool = _tool()
    result = tool.run({"variant_name": "35delG"})

    assert result["status"] == "error"
    assert "variant_name" in result["error"]
    assert "Unrecognized parameter" in result["error"]


def test_unrecognized_param_alongside_valid_param_is_noted_not_silently_dropped():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        side_effect=[
            {
                "status": "success",
                "data": {
                    "esearchresult": {
                        "idlist": [],
                        "count": "739",
                        "querytranslation": "GJB2[gene]",
                    }
                },
            },
        ],
    ):
        result = tool.run({"gene": "GJB2", "variant_name": "35delG"})

    assert result["status"] == "success"
    assert result["data"]["ignored_parameters"] == ["variant_name"]
    assert result["data"]["total_count"] == 739


def test_all_valid_params_have_no_ignored_parameters_key():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={
            "status": "success",
            "data": {"esearchresult": {"idlist": [], "count": "1", "querytranslation": ""}},
        },
    ):
        result = tool.run({"gene": "BRCA2"})

    assert result["status"] == "success"
    assert "ignored_parameters" not in result["data"]
