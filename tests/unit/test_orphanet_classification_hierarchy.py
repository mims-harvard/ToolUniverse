"""Regression guard for Fix-R20D-2: Orphanet_get_classification's own
description promises "parent and child disease categories showing where a
disease fits in the rare disease taxonomy," but the implementation only
ever called the RDcode Classification endpoint, which returns a flat list
of named classification SYSTEMS the disease is filed under (e.g. "Orphanet
classification of rare respiratory diseases") -- membership, not a
parent/child tree.

Confirmed live via the RDcode API's own OpenAPI spec that a real hierarchy
exists on two separate endpoints: PreferentialParent and
PreferentialChildren (e.g. Cystic fibrosis's preferential parent is "Rare
respiratory disease", and that parent has 82 real preferential children).
Fixed by fetching both alongside the existing classification-systems list,
which is kept (renamed to member_of_classifications for clarity) rather
than dropped.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.orphanet_tool import OrphanetTool

pytestmark = pytest.mark.unit


def _tool():
    return OrphanetTool({"name": "orphanet_test"})


def _resp(status_code, json_body=None, is_string_body=False):
    r = MagicMock()
    r.status_code = status_code
    if is_string_body:
        r.json.return_value = json_body
    else:
        r.json.return_value = json_body or {}
    if status_code >= 400:
        import requests

        r.raise_for_status = MagicMock(
            side_effect=requests.exceptions.HTTPError(response=r)
        )
    else:
        r.raise_for_status = MagicMock()
    return r


_MEMBERSHIP = {
    "ORPHAcode": 586,
    "Preferred term": "Cystic fibrosis",
    "Classification": [
        {
            "ID of the classification": 184,
            "Name of the classification": "Orphanet classification of rare respiratory diseases",
        }
    ],
}

_PARENT = {
    "ORPHAcode": 586,
    "Preferred term": "Cystic fibrosis",
    "Preferential parent": {"ORPHAcode": 97955, "Preferred term": "Rare respiratory disease"},
}


def test_leaf_disease_has_real_parent_and_empty_children():
    tool = _tool()

    def fake_get(url, **kwargs):
        if url.endswith("/orphacode/586/Name"):
            return _resp(200, {"Preferred term": "Cystic fibrosis"})
        if url.endswith("/orphacode/586/Classification"):
            return _resp(200, _MEMBERSHIP)
        if url.endswith("/orphacode/586/PreferentialParent"):
            return _resp(200, _PARENT)
        if url.endswith("/orphacode/586/PreferentialChildren"):
            # The API returns a plain string (not JSON dict/list) for
            # "no such relation" -- confirmed live for a leaf disease.
            return _resp(
                200,
                "Clinical entity does not exist or is not a preferential parent.",
                is_string_body=True,
            )
        raise AssertionError(f"unexpected URL {url}")

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        result = tool.run({"operation": "get_classification", "orpha_code": "586"})

    assert result["status"] == "success"
    assert result["data"]["parent"]["Preferential parent"]["Preferred term"] == (
        "Rare respiratory disease"
    )
    assert result["data"]["children"] == []
    assert "member_of_classifications" in result["data"]


def test_top_level_category_has_no_parent_but_has_children():
    tool = _tool()
    children_payload = [
        {"ORPHAcode": 586, "Preferred term": "Cystic fibrosis"},
        {"ORPHAcode": 60, "Preferred term": "Alpha-1-antitrypsin deficiency"},
    ]

    def fake_get(url, **kwargs):
        if url.endswith("/orphacode/97955/Name"):
            return _resp(200, {"Preferred term": "Rare respiratory disease"})
        if url.endswith("/orphacode/97955/Classification"):
            return _resp(200, {"Classification": []})
        if url.endswith("/orphacode/97955/PreferentialParent"):
            # 404 with a plain string body for "no parent" -- confirmed
            # live for a root-level category.
            return _resp(404, "Query not found", is_string_body=True)
        if url.endswith("/orphacode/97955/PreferentialChildren"):
            return _resp(200, children_payload)
        raise AssertionError(f"unexpected URL {url}")

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        result = tool.run({"operation": "get_classification", "orpha_code": "97955"})

    assert result["status"] == "success"
    assert result["data"]["parent"] is None
    assert len(result["data"]["children"]) == 2


def test_fetch_hierarchy_relation_swallows_network_errors():
    import requests

    tool = _tool()

    def fake_get(url, **kwargs):
        raise requests.exceptions.ConnectionError("boom")

    with patch("tooluniverse.orphanet_tool.requests.get", side_effect=fake_get):
        assert tool._fetch_hierarchy_relation("586", "PreferentialParent") is None
