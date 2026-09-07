"""Regression guard for Fix-R29: a binomial query to GTDB_search_genomes must
not silently degrade into a genus-wide match.

GTDB's /search/gtdb endpoint ORs the terms of a multi-word query instead of
requiring all of them. Confirmed live against https://gtdb-api.ecogenomic.org :

    search=xyzzyplop                  -> totalRows 0
    search=Mycobacterium              -> totalRows 13027
    search=Mycobacterium xyzzyplop    -> totalRows 13027 (identical rows)
    search=Mycobacterium tuberculosis -> totalRows 13381, first row
                                         "Mycobacterium leprae Br4923"

So an unmatchable term is discarded entirely and the reported total is the
union count for the broader taxon. The endpoint's documented `filterText`
parameter adds a case-insensitive literal-substring test that every returned
row must satisfy (live: search+filterText="Mycobacterium tuberculosis" ->
totalRows 7869, all M. tuberculosis; filterText="Mycobacterium xyzzyplop" -> 0),
so the tool now issues the precise lookup first and only falls back to the
loose union search with an explicit top-level disclosure.

No live network here -- the HTTP layer is mocked.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.gtdb_tool import GTDBTool

pytestmark = pytest.mark.unit


def _row(name, species):
    return {
        "gid": "GCA_TEST",
        "accession": "GCA_TEST",
        "ncbiOrgName": name,
        "ncbiTaxonomy": "d__Bacteria; g__Mycobacterium; s__" + species,
        "gtdbTaxonomy": "d__Bacteria; g__Mycobacterium; s__" + species,
        "isGtdbSpeciesRep": False,
        "isNcbiTypeMaterial": False,
    }


TB_ROWS = [
    _row("Mycobacterium tuberculosis SUMu001", "Mycobacterium tuberculosis"),
    _row("Mycobacterium tuberculosis C", "Mycobacterium tuberculosis"),
]
GENUS_ROWS = [
    _row("Mycobacterium leprae Br4923", "Mycobacterium leprae"),
] + TB_ROWS


def _tool():
    return GTDBTool({"name": "GTDB_search_genomes", "parameter": {}})


def _resp(json_body, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    return r


def _fake_gtdb(filtered_body, unfiltered_body):
    """Mimic /search/gtdb: `filterText` narrows, its absence unions the terms."""
    calls = []

    def _get(url, params=None, timeout=None):
        params = params or {}
        calls.append(params)
        if params.get("filterText"):
            return _resp(filtered_body)
        return _resp(unfiltered_body)

    return _get, calls


class TestBinomialQueryDoesNotDegradeToGenus:
    def test_precise_filter_is_applied_and_wrong_species_excluded(self):
        tool = _tool()
        get, calls = _fake_gtdb(
            {"rows": TB_ROWS, "totalRows": 7869},
            {"rows": GENUS_ROWS, "totalRows": 13381},
        )
        tool.session.get = get

        result = tool.run(
            {
                "operation": "search_genomes",
                "query": "Mycobacterium tuberculosis",
                "items_per_page": 5,
            }
        )

        assert result["status"] == "success"
        data = result["data"]

        # The precise lookup must actually be sent upstream.
        assert calls[0]["filterText"] == "Mycobacterium tuberculosis"

        # No result may be a species other than the one that was asked for.
        for row in data["results"]:
            assert "s__Mycobacterium tuberculosis" in row["gtdbTaxonomy"]
            assert "leprae" not in row["ncbiOrgName"]

        # The count must be the species count, not the genus/union count.
        assert data["match_type"] == "exact"
        assert data["total_results"] == 7869
        assert data["total_results"] != 13381
        assert "note" not in data

    def test_unmatched_binomial_falls_back_but_discloses_it(self):
        """GTDB drops the unmatchable term and returns the whole genus; the
        tool must fall back only with an explicit top-level disclosure."""
        tool = _tool()
        get, _calls = _fake_gtdb(
            {"rows": [], "totalRows": 0},
            {"rows": GENUS_ROWS, "totalRows": 13027},
        )
        tool.session.get = get

        result = tool.run(
            {"operation": "search_genomes", "query": "Mycobacterium xyzzyplop"}
        )

        data = result["data"]
        assert data["match_type"] == "broad"
        # The disclosure must be at the top level, not buried in the rows.
        assert "note" in data
        assert "NOT 'Mycobacterium xyzzyplop'" in data["note"]
        # total_results must not be passed off as the count for the query.
        assert "not for 'Mycobacterium xyzzyplop'" in data["note"]
        assert "broader" in data["total_results_scope"]
        # Results are still returned so the caller can inspect them.
        assert data["count"] == len(GENUS_ROWS)

    def test_no_match_at_all_reported_as_none(self):
        tool = _tool()
        get, _calls = _fake_gtdb(
            {"rows": [], "totalRows": 0}, {"rows": [], "totalRows": 0}
        )
        tool.session.get = get

        result = tool.run(
            {"operation": "search_genomes", "query": "Xyzzyplop notaspecies"}
        )

        data = result["data"]
        assert data["match_type"] == "none"
        assert data["total_results"] == 0
        assert data["results"] == []
        assert "no genome" in data["note"]

    def test_genus_query_still_matches_the_genus(self):
        """Control: a genus query is legitimately a genus-level match."""
        tool = _tool()
        get, calls = _fake_gtdb(
            {"rows": GENUS_ROWS, "totalRows": 13027},
            {"rows": GENUS_ROWS, "totalRows": 13027},
        )
        tool.session.get = get

        result = tool.run({"operation": "search_genomes", "query": "Mycobacterium"})

        data = result["data"]
        assert data["match_type"] == "exact"
        assert data["total_results"] == 13027
        assert "note" not in data
        assert len(calls) == 1

    def test_internal_whitespace_collapsed_for_literal_filter(self):
        """filterText is whitespace-literal upstream (a double space matches
        nothing), so the query must be normalized before it is sent."""
        tool = _tool()
        get, calls = _fake_gtdb(
            {"rows": TB_ROWS, "totalRows": 7869},
            {"rows": GENUS_ROWS, "totalRows": 13381},
        )
        tool.session.get = get

        result = tool.run(
            {"operation": "search_genomes", "query": "  Mycobacterium   tuberculosis "}
        )

        assert calls[0]["filterText"] == "Mycobacterium tuberculosis"
        assert calls[0]["search"] == "Mycobacterium tuberculosis"
        assert result["data"]["match_type"] == "exact"

    def test_page_beyond_last_does_not_trigger_broad_fallback(self):
        """An empty page of a non-empty exact match is still an exact match."""
        tool = _tool()
        get, calls = _fake_gtdb(
            {"rows": [], "totalRows": 7869},
            {"rows": GENUS_ROWS, "totalRows": 13381},
        )
        tool.session.get = get

        result = tool.run(
            {
                "operation": "search_genomes",
                "query": "Mycobacterium tuberculosis",
                "page": 99999,
            }
        )

        data = result["data"]
        assert data["match_type"] == "exact"
        assert data["results"] == []
        assert len(calls) == 1
