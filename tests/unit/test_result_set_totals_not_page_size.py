"""Regression tests: reported totals must describe the result set, not the page.

Three search tools computed their "total" field from the list they had already
truncated to ``limit``, so the number they reported was simply the page size:

* ``TCDB_search_family`` reported ``total_matches: 100`` for a query with 165
  matches, and ``total_matches: 5`` for the same query at ``limit=5``.
* ``TCDB_search_by_substrate`` did the same (126 true matches for "glucose").
* ``IGSR_search_populations`` reported ``total: 3`` at ``limit=3`` although the
  Elasticsearch response carried the true hit count of 212.

Both TCDB searches also capped ``limit`` at 100 with no offset, so the rest of
the result set was unreachable.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.igsr_tool import IGSRTool
from tooluniverse.tcdb_tool import TCDBTool


# --------------------------------------------------------------------------
# TCDB
# --------------------------------------------------------------------------

FAMILY_CONFIG = {
    "type": "TCDBTool",
    "name": "TCDB_search_family",
    "description": "Search TCDB families",
    "parameter": {"type": "object", "properties": {}},
    "fields": {"operation": "search_family"},
}

SUBSTRATE_CONFIG = {
    "type": "TCDBTool",
    "name": "TCDB_search_by_substrate",
    "description": "Search TCDB by substrate",
    "parameter": {"type": "object", "properties": {}},
    "fields": {"operation": "search_by_substrate"},
}

# 165 families under the "1.A" prefix, mirroring the live TCDB numbers.
FAMILIES = {f"1.A.{i}": f"Channel family {i}" for i in range(1, 166)}
FAMILIES.update({f"2.A.{i}": f"Porter family {i}" for i in range(1, 31)})


def _family_tool():
    tool = TCDBTool(dict(FAMILY_CONFIG))
    tool._get_families = lambda: FAMILIES
    tool._get_acc2tcid = lambda: {"P00001": ["1.A.1.1.1"]}
    return tool


def _substrate_tool(n_matches=126):
    tool = TCDBTool(dict(SUBSTRATE_CONFIG))
    entries = [
        {"tc_number": f"2.A.1.{i}", "substrates": [{"name": "D-glucose"}]}
        for i in range(n_matches)
    ]
    entries += [
        {"tc_number": f"3.A.1.{i}", "substrates": [{"name": "sodium"}]}
        for i in range(40)
    ]
    tool._get_substrates = lambda: entries
    tool._get_families = lambda: {}
    tool._family_for_tc = lambda tc, fams: "family"
    return tool


@pytest.mark.parametrize("limit", [5, 20, 100])
def test_family_total_is_independent_of_limit(limit):
    result = _family_tool().run({"family_id": "1.A", "limit": limit})
    data = result["data"]
    assert data["total_matches"] == 165, "total must count all matches, not the page"
    assert data["returned"] == limit
    assert len(data["families"]) == limit
    assert data["has_more"] is True


@pytest.mark.parametrize("limit", [5, 100])
def test_substrate_total_is_independent_of_limit(limit):
    result = _substrate_tool().run({"substrate_name": "glucose", "limit": limit})
    data = result["data"]
    assert data["total_matches"] == 126
    assert data["returned"] == limit
    assert data["has_more"] is True


def test_family_offset_reaches_results_beyond_the_limit_cap():
    """`limit` is capped at 100; `offset` must make the tail reachable."""
    result = _family_tool().run({"family_id": "1.A", "offset": 160, "limit": 100})
    data = result["data"]
    assert data["total_matches"] == 165
    assert data["returned"] == 5
    assert data["has_more"] is False
    # The page is the tail of the (lexicographically) sorted match list.
    expected_tail = sorted(f for f in FAMILIES if f.startswith("1.A"))[160:]
    assert [f["family_id"] for f in data["families"]] == expected_tail


def test_family_offset_pages_are_disjoint():
    first = _family_tool().run({"family_id": "1.A", "limit": 50, "offset": 0})
    second = _family_tool().run({"family_id": "1.A", "limit": 50, "offset": 50})
    ids_a = {f["family_id"] for f in first["data"]["families"]}
    ids_b = {f["family_id"] for f in second["data"]["families"]}
    assert len(ids_a) == 50 and len(ids_b) == 50
    assert not ids_a & ids_b


def test_substrate_offset_reaches_the_tail():
    result = _substrate_tool().run(
        {"substrate_name": "glucose", "offset": 120, "limit": 100}
    )
    data = result["data"]
    assert data["total_matches"] == 126
    assert data["returned"] == 6
    assert data["has_more"] is False


def test_family_name_filter_total_is_also_untruncated():
    result = _family_tool().run({"family_name": "Porter", "limit": 5})
    assert result["data"]["total_matches"] == 30
    assert result["data"]["returned"] == 5


def test_family_requires_a_query():
    result = _family_tool().run({})
    assert result["status"] == "error"


def test_substrate_requires_a_query():
    result = _substrate_tool().run({})
    assert result["status"] == "error"


def test_family_empty_result_set_has_no_more():
    result = _family_tool().run({"family_id": "9.Z", "limit": 10})
    data = result["data"]
    assert data["total_matches"] == 0
    assert data["returned"] == 0
    assert data["has_more"] is False


# --------------------------------------------------------------------------
# IGSR
# --------------------------------------------------------------------------

POPULATION_CONFIG = {
    "type": "IGSRTool",
    "name": "IGSR_search_populations",
    "description": "Search IGSR populations",
    "parameter": {
        "type": "object",
        "properties": {"operation": {"default": "search_populations"}},
    },
}


def _population_hits(n, superpop="EUR"):
    return [
        {
            "_source": {
                "code": f"POP{i}",
                "name": f"Population {i}",
                "description": "",
                "samples": {"count": 100},
                "superpopulation": {"code": superpop, "name": superpop},
            }
        }
        for i in range(n)
    ]


def _igsr_tool(hits, total):
    tool = IGSRTool(dict(POPULATION_CONFIG))
    tool._es_search = lambda index, body: {
        "hits": {"total": total, "hits": hits[: body.get("size", 10)]}
    }
    return tool


@pytest.mark.parametrize("limit", [3, 25, 100])
def test_population_total_comes_from_elasticsearch_not_the_page(limit):
    tool = _igsr_tool(_population_hits(300), total=212)
    result = tool.run({"limit": limit})
    data = result["data"]
    assert data["total"] == 212, "total must be the ES hit count, not the page size"
    assert data["returned"] == min(limit, 212)


def test_population_total_handles_elasticsearch7_total_object():
    tool = _igsr_tool(_population_hits(300), total={"value": 212, "relation": "eq"})
    result = tool.run({"limit": 3})
    assert result["data"]["total"] == 212


def test_population_superpopulation_total_counts_filtered_matches():
    """The superpopulation filter runs client-side, so the ES count is wrong there."""
    hits = _population_hits(5, superpop="EUR") + _population_hits(20, superpop="AFR")
    tool = _igsr_tool(hits, total=212)
    result = tool.run({"superpopulation": "EUR", "limit": 3})
    data = result["data"]
    assert data["total"] == 5, "must count EUR matches, not all 212 populations"
    assert data["returned"] == 3


def test_population_superpopulation_total_stable_across_limits():
    hits = _population_hits(5, superpop="EUR") + _population_hits(20, superpop="AFR")
    totals = {
        limit: _igsr_tool(hits, total=212).run(
            {"superpopulation": "EUR", "limit": limit}
        )["data"]["total"]
        for limit in (1, 3, 100)
    }
    assert set(totals.values()) == {5}


def test_population_returned_never_exceeds_available():
    tool = _igsr_tool(_population_hits(4), total=4)
    result = tool.run({"limit": 100})
    assert result["data"]["total"] == 4
    assert result["data"]["returned"] == 4


def test_samples_and_collections_totals_survive_total_object_form():
    """The shared helper must not regress the siblings that were already correct."""
    for operation, key in (
        ("search_samples", "samples"),
        ("list_data_collections", "collections"),
    ):
        config = dict(POPULATION_CONFIG)
        config["parameter"] = {
            "type": "object",
            "properties": {"operation": {"default": operation}},
        }
        tool = IGSRTool(config)
        tool._es_search = lambda index, body: {
            "hits": {
                "total": {"value": 3202, "relation": "eq"},
                "hits": [{"_source": {}} for _ in range(2)],
            }
        }
        result = tool.run({"limit": 2})
        assert result["data"]["total"] == 3202
        assert result["data"]["returned"] == 2
        assert len(result["data"][key]) == 2


def test_igsr_unknown_operation_is_an_error():
    tool = IGSRTool(dict(POPULATION_CONFIG))
    result = tool.run({"operation": "not_a_real_operation"})
    assert result["status"] == "error"


def test_igsr_es_failure_surfaces_as_error():
    tool = IGSRTool(dict(POPULATION_CONFIG))

    def boom(index, body):
        raise RuntimeError("es down")

    tool._es_search = boom
    result = tool.run({"limit": 5})
    assert result["status"] == "error"


def test_tcdb_config_declares_offset_and_new_schema_fields():
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "tcdb_tools.json"
    )
    tools = {t["name"]: t for t in json.loads(path.read_text())}
    for name in ("TCDB_search_family", "TCDB_search_by_substrate"):
        props = tools[name]["parameter"]["properties"]
        assert "offset" in props, f"{name} must document offset"
        schema = json.dumps(tools[name]["return_schema"])
        assert "has_more" in schema and "returned" in schema


def test_igsr_config_documents_total_semantics():
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "igsr_tools.json"
    )
    tools = {t["name"]: t for t in json.loads(path.read_text())}
    schema = json.dumps(tools["IGSR_search_populations"]["return_schema"])
    assert "returned" in schema
    assert "independent of the `limit`" in schema


def test_igsr_es_search_is_untouched_by_helper():
    """_total_hits must be a pure read of the response, not a request."""
    assert IGSRTool._total_hits({"hits": {"total": 7}}) == 7
    assert IGSRTool._total_hits({"hits": {"total": {"value": 7}}}) == 7
    assert IGSRTool._total_hits({}) == 0
    assert IGSRTool._total_hits({"hits": {}}) == 0


def test_tcdb_get_transporter_operation_unaffected():
    """Only the two search operations changed; lookup must still route normally."""
    config = dict(FAMILY_CONFIG)
    config["fields"] = {"operation": "get_transporter"}
    tool = TCDBTool(config)
    result = tool.run({})
    # No accession supplied -> a clean error, not a crash.
    assert result["status"] == "error"
    assert isinstance(result.get("error"), str)


def test_magicmock_not_leaking_into_results():
    """Guard against mocks silently standing in for real data in these tests."""
    result = _family_tool().run({"family_id": "1.A", "limit": 2})
    assert not isinstance(result["data"]["total_matches"], MagicMock)
