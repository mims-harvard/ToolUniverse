"""Regression guard for Fix-R72A-1: ClinGen's gene-validity and dosage-
sensitivity gene filters used substring matching (`gene_upper in
symbol.upper()`) instead of exact matching, against a column that holds a
single precise HGNC symbol, not free text. Confirmed live: querying "OTC"
(ornithine transcarbamylase deficiency) also silently returned "NOTCH1" and
"NOTCH2" curations, since "OTC" is a literal substring of "NOTCH1"/"NOTCH2".
`_get_gene_validity` already used the correct exact-match pattern -- this
brings `_search_gene_validity`, `_get_dosage_sensitivity`, and
`_search_dosage_sensitivity` in line with it.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_tool import ClinGenTool

pytestmark = pytest.mark.unit

CSV_TEXT = (
    '"CLINGEN DOSAGE SENSITIVITY CURATIONS","","","","",""\n'
    '"FILE CREATED: 2026-07-21","","","","",""\n'
    '"GENE SYMBOL","HGNC ID","HAPLOINSUFFICIENCY","TRIPLOSENSITIVITY","ONLINE REPORT","DATE"\n'
    '"NOTCH1","HGNC:7881","Sufficient Evidence for Haploinsufficiency","No Evidence for Triplosensitivity","url1","date1"\n'
    '"NOTCH2","HGNC:7882","No Evidence for Haploinsufficiency","No Evidence for Triplosensitivity","url2","date2"\n'
    '"OTC","HGNC:8512","Sufficient Evidence for Haploinsufficiency","No Evidence for Triplosensitivity","url3","date3"\n'
)


def _tool(operation):
    return ClinGenTool({"name": "clingen_test", "fields": {"operation": operation}})


def _resp():
    r = MagicMock()
    r.text = CSV_TEXT
    r.raise_for_status = MagicMock()
    return r


def test_get_dosage_sensitivity_exact_matches_otc_not_notch():
    tool = _tool("get_dosage_sensitivity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "OTC"})

    assert result["status"] == "success"
    assert result["data"] == [
        {
            "GENE SYMBOL": "OTC",
            "HGNC ID": "HGNC:8512",
            "HAPLOINSUFFICIENCY": "Sufficient Evidence for Haploinsufficiency",
            "TRIPLOSENSITIVITY": "No Evidence for Triplosensitivity",
            "ONLINE REPORT": "url3",
            "DATE": "date3",
        }
    ]
    assert result["total"] == 1


def test_search_dosage_sensitivity_exact_matches_otc_not_notch():
    tool = _tool("search_dosage_sensitivity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "OTC"})

    assert result["status"] == "success"
    assert len(result["data"]) == 1
    assert result["data"][0]["GENE SYMBOL"] == "OTC"


def test_search_gene_validity_exact_matches_otc_not_notch():
    tool = _tool("search_gene_validity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "OTC"})

    assert result["status"] == "success"
    assert len(result["data"]) == 1
    assert result["data"][0]["GENE SYMBOL"] == "OTC"


def test_get_dosage_sensitivity_case_insensitive_still_matches():
    tool = _tool("get_dosage_sensitivity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "otc"})

    assert len(result["data"]) == 1
    assert result["data"][0]["GENE SYMBOL"] == "OTC"


def test_get_dosage_sensitivity_genuinely_nonexistent_gene_returns_empty():
    tool = _tool("get_dosage_sensitivity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "NOTAREALGENE12345"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["total"] == 0


def test_get_dosage_sensitivity_notch1_query_does_not_pull_in_otc():
    """The inverse check: querying the longer symbol must not match the
    shorter one it happens to contain either."""
    tool = _tool("get_dosage_sensitivity")
    with patch("tooluniverse.clingen_tool.requests.get", return_value=_resp()):
        result = tool.run({"gene": "NOTCH1"})

    assert len(result["data"]) == 1
    assert result["data"][0]["GENE SYMBOL"] == "NOTCH1"
