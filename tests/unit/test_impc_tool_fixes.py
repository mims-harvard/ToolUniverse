"""Regression guard for two Fix-R23A bugs in IMPCTool.

Fix-R23A-1 (search relevance): IMPC_search_genes's Solr query had no
exact-match boost, so a real gene symbol could rank well outside the
default rows=20 window -- confirmed live that querying "App" put the exact
match 12th, behind unrelated genes like Hydin/Nfrkb/Ikbke. Fixed by boosting
an exact marker_symbol match to the front of Solr's own relevance ranking.

Fix-R23A-2 (gene summary has_phenotype_data): IMPC_get_gene_summary derives
has_phenotype_data purely from the 'gene' Solr core's own summary fields
(imits_phenotype_complete, mp_id), which are inconsistently populated --
confirmed live that App (MGI:88059) has none of them set in the 'gene' core
despite having 9 real significant phenotype calls in the separate
'genotype-phenotype' core (used by the sibling get_phenotypes_by_gene
tool). Fixed by cross-checking that core before deciding has_phenotype_data.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.impc_tool import IMPCTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return IMPCTool({"name": "impc_test", "fields": {"operation": operation}})


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


class TestSearchGenesExactMatchBoost:
    def test_query_boosts_exact_marker_symbol_match(self):
        tool = _tool("search_genes")
        resp = _solr_resp([{"mgi_accession_id": "MGI:88059", "marker_symbol": "App"}])

        with patch(
            "tooluniverse.impc_tool.requests.get", return_value=resp
        ) as mock_get:
            tool.run({"query": "App"})

        query_param = mock_get.call_args.kwargs["params"]["q"]
        assert 'marker_symbol:"App"^100' in query_param


class TestGeneSummaryPhenotypeCrossCheck:
    def test_falls_back_to_genotype_phenotype_core_when_gene_core_empty(self):
        tool = _tool("get_gene_summary")
        gene_resp = _solr_resp(
            [{"mgi_accession_id": "MGI:88059", "marker_symbol": "App"}]
        )
        gp_resp = _solr_resp([], num_found=9)

        with patch(
            "tooluniverse.impc_tool.requests.get",
            side_effect=[gene_resp, gp_resp],
        ):
            result = tool.run({"gene_symbol": "App"})

        assert result["status"] == "success"
        assert result["data"]["has_phenotype_data"] is True

    def test_no_genotype_phenotype_hits_and_no_gene_core_fields_is_false(self):
        tool = _tool("get_gene_summary")
        gene_resp = _solr_resp(
            [{"mgi_accession_id": "MGI:99999", "marker_symbol": "Xyz"}]
        )
        gp_resp = _solr_resp([], num_found=0)

        with patch(
            "tooluniverse.impc_tool.requests.get",
            side_effect=[gene_resp, gp_resp],
        ):
            result = tool.run({"gene_symbol": "Xyz"})

        assert result["status"] == "success"
        assert result["data"]["has_phenotype_data"] is False

    def test_gene_core_fields_alone_still_count(self):
        tool = _tool("get_gene_summary")
        gene_resp = _solr_resp(
            [
                {
                    "mgi_accession_id": "MGI:12345",
                    "marker_symbol": "Trp53",
                    "imits_phenotype_complete": "1",
                }
            ]
        )
        gp_resp = _solr_resp([], num_found=0)

        with patch(
            "tooluniverse.impc_tool.requests.get",
            side_effect=[gene_resp, gp_resp],
        ):
            result = tool.run({"gene_symbol": "Trp53"})

        assert result["data"]["has_phenotype_data"] is True
