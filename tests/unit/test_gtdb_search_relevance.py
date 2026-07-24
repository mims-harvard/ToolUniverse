"""Regression guard for Fix-R23D-3: GTDB_search_genomes matches against the
whole taxonomic clade, not just organism-name text -- confirmed live that
querying "Akkermansia muciniphila" returned unrelated family-mates like
"Roseibacillus sp. TMED18" ranked ahead of genomes whose own name actually
matches. Fixed by boosting exact/prefix ncbiOrgName matches to the front of
the fetched page.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtdb_tool import GTDBTool

pytestmark = pytest.mark.unit

_UNSORTED_ROWS = [
    {"accession": "GCA_002168145.2", "ncbiOrgName": "Roseibacillus sp. TMED18"},
    {"accession": "GCA_000436395.1", "ncbiOrgName": "Akkermansia muciniphila CAG:154"},
    {
        "accession": "GCA_002170085.1",
        "ncbiOrgName": "Verrucomicrobiaceae bacterium TMED137",
    },
    {"accession": "GCA_000723745.2", "ncbiOrgName": "Akkermansia muciniphila"},
]


def _tool():
    return GTDBTool({"name": "gtdb_test", "parameter": {}})


def _resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    return r


class TestSearchGenomesRelevance:
    def test_exact_name_match_ranked_first(self):
        tool = _tool()
        resp = _resp(200, {"rows": _UNSORTED_ROWS, "totalRows": 3599})

        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "search_genomes", "query": "Akkermansia muciniphila"}
            )

        assert result["status"] == "success"
        names = [r["ncbiOrgName"] for r in result["data"]["results"]]
        assert names[0] == "Akkermansia muciniphila"
        assert names[1] == "Akkermansia muciniphila CAG:154"
        assert set(names[2:]) == {
            "Roseibacillus sp. TMED18",
            "Verrucomicrobiaceae bacterium TMED137",
        }

    def test_no_relevant_match_preserves_original_order(self):
        tool = _tool()
        rows = _UNSORTED_ROWS[:2]  # neither is an exact/prefix match for this query
        resp = _resp(200, {"rows": rows, "totalRows": 2})

        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "search_genomes", "query": "Faecalibacterium prausnitzii"}
            )

        names = [r["ncbiOrgName"] for r in result["data"]["results"]]
        assert names == [r["ncbiOrgName"] for r in rows]
