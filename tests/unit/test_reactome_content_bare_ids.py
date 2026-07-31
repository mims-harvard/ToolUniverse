"""Regression guard for Fix-R18B-1: Reactome's containedEvents endpoint mixes
full event dicts with plain integer DB IDs for some sub-pathways -- confirmed
live for R-HSA-2219528 ("PI3K/AKT Signaling in Cancer"), where 2 of its 3
real sub-pathways came back as bare ints and were silently skipped, both
dropping them from the hierarchy and making total_events disagree with
pathway_count + reaction_count. Bare IDs are now batch-resolved via
Reactome's /data/query/ids endpoint instead of discarded.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.reactome_content_tool import ReactomeContentTool

pytestmark = pytest.mark.unit


def _tool():
    return ReactomeContentTool(
        {"name": "ReactomeContent_get_contained_events", "fields": {}}
    )


def _resp(json_body, ok=True):
    r = MagicMock()
    r.ok = ok
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


def test_bare_int_ids_are_resolved_not_dropped():
    tool = _tool()
    contained_events = [
        {
            "stId": "R-HSA-5674404",
            "displayName": "PTEN Loss of Function in Cancer",
            "schemaClass": "Pathway",
            "isInDisease": True,
        },
        5674400,
        2219530,
    ] + [
        {
            "stId": f"R-HSA-{i}",
            "displayName": f"Reaction {i}",
            "schemaClass": "Reaction",
            "isInDisease": False,
        }
        for i in range(21)
    ]
    ids_response = [
        {
            "dbId": 5674400,
            "stId": "R-HSA-5674400",
            "displayName": "Constitutive Signaling by AKT1 E17K in Cancer",
            "schemaClass": "Pathway",
            "isInDisease": True,
        },
        {
            "dbId": 2219530,
            "stId": "R-HSA-2219530",
            "displayName": "Constitutive Signaling by Aberrant PI3K in Cancer",
            "schemaClass": "Pathway",
            "isInDisease": True,
        },
    ]

    def fake_get(url, **kwargs):
        return _resp(contained_events)

    def fake_post(url, **kwargs):
        return _resp(ids_response)

    with patch("tooluniverse.reactome_content_tool.requests.get", side_effect=fake_get), \
         patch("tooluniverse.reactome_content_tool.requests.post", side_effect=fake_post):
        result = tool._get_contained_events({"identifier": "R-HSA-2219528"})

    data = result["data"]
    assert data["total_events"] == 24
    assert data["pathway_count"] == 3
    assert data["reaction_count"] == 21
    assert data["pathway_count"] + data["reaction_count"] == data["total_events"]
    stids = {p["stId"] for p in data["pathways"]}
    assert stids == {"R-HSA-5674404", "R-HSA-5674400", "R-HSA-2219530"}


def test_no_extra_request_when_all_events_are_dicts():
    tool = _tool()
    contained_events = [
        {
            "stId": "R-HSA-1",
            "displayName": "Reaction 1",
            "schemaClass": "Reaction",
            "isInDisease": False,
        }
    ]

    def fake_get(url, **kwargs):
        return _resp(contained_events)

    with patch("tooluniverse.reactome_content_tool.requests.get", side_effect=fake_get), \
         patch("tooluniverse.reactome_content_tool.requests.post") as mock_post:
        result = tool._get_contained_events({"identifier": "R-HSA-1"})

    mock_post.assert_not_called()
    assert result["data"]["total_events"] == 1
    assert result["data"]["reaction_count"] == 1


def test_unresolvable_bare_id_is_dropped_gracefully():
    tool = _tool()
    contained_events = [999999999]

    def fake_get(url, **kwargs):
        return _resp(contained_events)

    def fake_post(url, **kwargs):
        return _resp([])

    with patch("tooluniverse.reactome_content_tool.requests.get", side_effect=fake_get), \
         patch("tooluniverse.reactome_content_tool.requests.post", side_effect=fake_post):
        result = tool._get_contained_events({"identifier": "R-HSA-X"})

    data = result["data"]
    assert data["total_events"] == 1
    assert data["pathway_count"] == 0
    assert data["reaction_count"] == 0
