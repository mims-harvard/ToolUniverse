"""Regression guard for Fix-R27B-1: IMPC_get_phenotypes_by_gene crashed
with "list index out of range" whenever a valid mgi_id query matched zero
records in the genotype-phenotype core -- confirmed live for Lrrk2
(MGI:1913975) and Brca1 (MGI:104537), both real, resolvable mouse genes
that simply have no significant phenotype calls in this core. Root cause:
`docs[0].get("marker_symbol", "")` was unguarded for an empty `docs` list,
unlike the very next line (`mgi_id`) which correctly guarded with
`if docs else ""`.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.impc_tool import IMPCTool

pytestmark = pytest.mark.unit


def _tool():
    return IMPCTool({"name": "impc_test", "fields": {"operation": "get_phenotypes_by_gene"}})


def _solr_resp(docs, num_found=None):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {
        "response": {
            "docs": docs,
            "numFound": num_found if num_found is not None else len(docs),
        }
    }
    return r


class TestEmptyDocsDoesNotCrash:
    def test_mgi_id_with_zero_phenotype_calls_returns_success_not_crash(self):
        tool = _tool()
        with patch(
            "tooluniverse.impc_tool.requests.get", return_value=_solr_resp([])
        ):
            result = tool.run({"mgi_id": "MGI:1913975"})

        assert result["status"] == "success"
        assert result["data"]["mgi_id"] == "MGI:1913975"
        assert result["data"]["gene_symbol"] == ""
        assert result["data"]["total_phenotype_calls"] == 0
        assert result["data"]["phenotypes"] == []

    def test_gene_symbol_query_with_zero_calls_also_does_not_crash(self):
        tool = _tool()
        with patch(
            "tooluniverse.impc_tool.requests.get", return_value=_solr_resp([])
        ):
            result = tool.run({"gene_symbol": "Lrrk2"})

        assert result["status"] == "success"
        assert result["data"]["gene_symbol"] == "Lrrk2"
        assert result["data"]["mgi_id"] == ""

    def test_non_empty_docs_still_populate_gene_symbol(self):
        tool = _tool()
        docs = [
            {
                "marker_symbol": "Trp53",
                "marker_accession_id": "MGI:98834",
                "mp_term_id": "MP:0001",
                "mp_term_name": "abnormal retina morphology",
            }
        ]
        with patch(
            "tooluniverse.impc_tool.requests.get", return_value=_solr_resp(docs)
        ):
            result = tool.run({"mgi_id": "MGI:98834"})

        assert result["status"] == "success"
        assert result["data"]["gene_symbol"] == "Trp53"
        assert result["data"]["total_phenotype_calls"] == 1
