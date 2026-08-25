"""Regression guard for Fix-R18B-2: ReactomeInteractorsTool sent
page=-1 (a Reactome-specific "ignore pagination, return everything"
signal), so the tool's own documented page_size parameter had zero effect
-- confirmed live that page=-1&pageSize=10 returned all 153 interactors for
P31749, while page=1&pageSize=10 correctly returned 10.

Feature-23C-2: page_size was additionally clamped to 100, and
total_interactors was read from the /details response's `count` field --
which reports how many records that page returned, not the size of the
full result set. So a page_size=300 request came back with
total_interactors=100 and no indication anything had been dropped
(live-verified for P04637: pageSize=100 -> count=100, pageSize=300 ->
count=249). The clamp is gone and the true total now comes from the
dedicated /summary endpoint, so these tests assert against two calls.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.reactome_interactors_tool import ReactomeInteractorsTool

pytestmark = pytest.mark.unit


def _tool():
    return ReactomeInteractorsTool(
        {"name": "ReactomeInteractors_get_protein_interactors", "fields": {}}
    )


def _fake_reactome(total, returned, acc="P31749"):
    """Mock Reactome's two endpoints: /summary gives the true total,
    /details gives one page. Records the params each one was called with."""
    captured = {}

    def fake_get(url, params=None, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if url.endswith("/summary"):
            captured["summary_params"] = params
            resp.json.return_value = {
                "resource": "static",
                "entities": [{"acc": acc, "count": total}],
            }
        else:
            captured["details_params"] = params
            resp.json.return_value = {
                "resource": "IntAct",
                "entities": [
                    {
                        "acc": acc,
                        # `count` here is the page's own size, which is exactly
                        # why it must not be reported as a total.
                        "count": returned,
                        "interactors": [
                            {
                                "acc": f"P{i}",
                                "alias": None,
                                "score": 0.5,
                                "evidences": [],
                            }
                            for i in range(returned)
                        ],
                    }
                ],
            }
        return resp

    return fake_get, captured


def test_page_size_is_honored_via_correct_page_param():
    tool = _tool()
    fake_get, captured = _fake_reactome(total=10, returned=10)

    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get", side_effect=fake_get
    ):
        result = tool._get_interactors({"accession": "P31749", "page_size": 10})

    assert captured["details_params"]["page"] == 1
    assert captured["details_params"]["pageSize"] == 10
    assert len(result["data"]["interactors"]) == 10


def test_page_size_above_100_is_not_clamped():
    tool = _tool()
    fake_get, captured = _fake_reactome(total=249, returned=249, acc="P04637")

    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get", side_effect=fake_get
    ):
        result = tool._get_interactors({"accession": "P04637", "page_size": 300})

    assert captured["details_params"]["pageSize"] == 300
    assert result["data"]["total_interactors"] == 249
    assert result["data"]["returned_interactors"] == 249
    assert result["data"]["truncated"] is False


def test_truncated_page_reports_true_total_and_flags_truncation():
    tool = _tool()
    fake_get, _ = _fake_reactome(total=249, returned=20, acc="P04637")

    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get", side_effect=fake_get
    ):
        result = tool._get_interactors({"accession": "P04637"})

    data = result["data"]
    # The /details page reported count=20; the total must come from /summary.
    assert data["total_interactors"] == 249
    assert data["returned_interactors"] == 20
    assert data["truncated"] is True
    assert data["total_is_exact"] is True
    assert "249" in data["note"]


def test_unavailable_summary_does_not_pass_page_count_off_as_total():
    tool = _tool()

    def fake_get(url, params=None, **kwargs):
        resp = MagicMock()
        if url.endswith("/summary"):
            raise requests.exceptions.ConnectionError("summary down")
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "resource": "IntAct",
            "entities": [
                {
                    "acc": "P31749",
                    "count": 20,
                    "interactors": [
                        {"acc": f"P{i}", "alias": None, "score": 0.5, "evidences": []}
                        for i in range(20)
                    ],
                }
            ],
        }
        return resp

    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get", side_effect=fake_get
    ):
        result = tool._get_interactors({"accession": "P31749"})

    data = result["data"]
    assert data["total_is_exact"] is False
    assert data["returned_interactors"] == 20
    assert "incomplete" in data["note"]
