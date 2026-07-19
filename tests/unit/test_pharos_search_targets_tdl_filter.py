"""Regression guard for Fix-R20E-2: Pharos_search_targets' `tdl` parameter
was declared in the tool's schema and accepted by the code, but never
actually used -- the GraphQL query sent only `filter: {term: $term}`,
completely ignoring tdl. Confirmed live: `tdl:"Tdark"` and `tdl:"Tclin"`
returned byte-identical count/results for the same query.

Root cause (confirmed via GraphQL introspection against
pharos-api.ncats.io): Pharos' `IFilter` input type has no direct `tdl`
scalar field at all -- TDL filtering must go through its generic `facets`
list (`facet: "Target Development Level", values: [...]`). Fixed by
building that facets argument whenever `tdl` is provided.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.pharos_tool import PharosTool

pytestmark = pytest.mark.unit


def _tool():
    return PharosTool({"name": "pharos_test", "fields": {"operation": "search_targets"}})


def _graphql_resp(targets_payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = {"data": {"targets": targets_payload}}
    return r


def test_tdl_filter_sent_as_facets_not_dropped():
    tool = _tool()
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["variables"] = json.get("variables")
        return _graphql_resp({"count": 1, "targets": [{"sym": "KNDC1", "tdl": "Tdark"}]})

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = tool.run({"query": "kinase", "tdl": "Tdark", "top": 5})

    assert result["status"] == "success"
    facets = captured["variables"]["facets"]
    assert facets == [{"facet": "Target Development Level", "values": ["Tdark"]}]


def test_no_tdl_sends_no_facets():
    tool = _tool()
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["variables"] = json.get("variables")
        return _graphql_resp({"count": 2, "targets": []})

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = tool.run({"query": "kinase", "top": 5})

    assert result["status"] == "success"
    assert captured["variables"]["facets"] is None


def test_different_tdl_values_produce_different_facet_filters():
    tool = _tool()
    seen_facets = []

    def fake_post(url, json=None, **kwargs):
        seen_facets.append(json.get("variables")["facets"])
        return _graphql_resp({"count": 1, "targets": []})

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        tool.run({"query": "kinase", "tdl": "Tdark", "top": 5})
        tool.run({"query": "kinase", "tdl": "Tclin", "top": 5})

    assert seen_facets[0] != seen_facets[1]
    assert seen_facets[0] == [{"facet": "Target Development Level", "values": ["Tdark"]}]
    assert seen_facets[1] == [{"facet": "Target Development Level", "values": ["Tclin"]}]


def test_tdl_summary_returns_real_counts_from_facets():
    """Regression guard for Fix-R20E-3: get_tdl_summary previously
    returned only static TDL labels/descriptions plus a note telling the
    caller to look elsewhere -- confirmed live it now runs a minimal
    top:1 targets query whose facets field carries the real whole-proteome
    TDL breakdown."""
    tool = PharosTool({"name": "pharos_test", "fields": {"operation": "get_tdl_summary"}})

    def fake_post(url, json=None, **kwargs):
        return _graphql_resp_full(
            {
                "dbVersion": "pharos319",
                "targets": {
                    "facets": [
                        {
                            "facet": "Target Development Level",
                            "values": [
                                {"name": "Tbio", "value": 12303},
                                {"name": "Tdark", "value": 5501},
                                {"name": "Tchem", "value": 1904},
                                {"name": "Tclin", "value": 704},
                            ],
                        }
                    ]
                },
            }
        )

    with patch("tooluniverse.pharos_tool.requests.post", side_effect=fake_post):
        result = tool.run({})

    assert result["status"] == "success"
    assert result["data"]["counts"] == {
        "Tclin": 704,
        "Tchem": 1904,
        "Tbio": 12303,
        "Tdark": 5501,
    }
    assert result["data"]["total_targets"] == 20412
    assert result["data"]["db_version"] == "pharos319"


def _graphql_resp_full(data):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = {"data": data}
    return r
