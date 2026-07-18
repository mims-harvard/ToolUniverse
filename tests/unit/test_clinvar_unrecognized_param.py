"""Regression guard for Fix-R5D-1: ClinVar_search_variants used to silently
drop any caller-supplied parameter that didn't match a recognized name or
alias (e.g. "gene_name" instead of "gene"/"gene_symbol"), producing a
generic "at least one search parameter is required" error with no hint the
parameter itself was misnamed.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def test_unrecognized_param_names_itself_in_error():
    tool = _tool()
    result = tool.run({"gene_name": "BRCA1"})

    assert result["status"] == "error"
    assert "gene_name" in result["error"]
    assert "Unrecognized parameter" in result["error"]


def test_truly_empty_args_keeps_original_generic_error():
    tool = _tool()
    result = tool.run({})

    assert result["status"] == "error"
    assert result["error"] == "At least one search parameter is required"


def test_recognized_gene_param_still_dispatches_request():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"gene": "BRCA1"})

    assert result["status"] == "success"
    mock_request.assert_called_once()
    assert "BRCA1[gene]" in mock_request.call_args[0][1]["term"]


def test_gene_symbol_alias_still_works():
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        result = tool.run({"gene_symbol": "BRCA1"})

    assert result["status"] == "success"
    assert "BRCA1[gene]" in mock_request.call_args[0][1]["term"]
