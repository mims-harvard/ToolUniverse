"""MAGICapp_list_guidelines: the whole public list is read (the API returns 15
guidelines unless paged), searched by words and language, and returned as
compact rows that name the id the other MAGICapp tools take. HTTP is faked."""

import json
from pathlib import Path

import pytest

from tooluniverse import magicapp_tool as M

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _guideline(i, name, owner="WHO", language="en", description=""):
    return {
        "guidelineId": 1000 + i,
        "publishedId": i,
        "name": name,
        "byName": "",
        "owner": owner,
        "institutionName": owner,
        "description": description,
        "language": language,
        "publishDate": "2025-01-0%d" % (i % 9 + 1),
        "publishedRecommendationCount": i,
        "shortCode": "c%d" % i,
        "contactEmail": "not returned",
    }


CATALOGUE = [
    _guideline(
        1, "Living guideline for acute stroke thrombolysis", owner="Stroke Foundation"
    ),
    _guideline(
        2, "Rehabilitation after stroke", owner="Stroke Foundation", language="en-au"
    ),
    _guideline(
        3, "WHO recommendations on postpartum haemorrhage", description="uterine atony"
    ),
    _guideline(
        4,
        "Richtlijn beroerte",
        owner="NHG",
        language="nl",
        description="stroke in general practice",
    ),
    _guideline(5, "Pregnancy care guidelines", owner="Australian Government"),
]


class _Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %d" % self.status_code)

    def json(self):
        return self.body


@pytest.fixture
def tool(monkeypatch):
    """A tool whose catalogue is CATALOGUE served in pages of 2; records the params."""
    monkeypatch.setattr(M, "PAGE_SIZE", 2)
    monkeypatch.setattr(M, "_cache", {"rows": None, "fetched": 0.0})
    calls = []

    def fake(session, method, url, params=None, timeout=None, max_attempts=None):
        calls.append(params)
        start = params["offset"]
        return _Response(CATALOGUE[start : start + params["limit"]])

    monkeypatch.setattr(M, "request_with_retry", fake)
    config = next(
        t
        for t in json.loads((DATA / "clinical_guidelines_tools.json").read_text())
        if t["name"] == "MAGICapp_list_guidelines"
    )
    instance = M.MAGICappGuidelineListTool(config)
    instance.calls = calls
    return instance


def test_the_whole_list_is_read_in_pages_and_kept(tool):
    out = tool.run({})
    assert [c["offset"] for c in tool.calls] == [
        0,
        2,
        4,
    ]  # the short third page ends it
    assert (
        out["metadata"]["public_guidelines"] == 5 and out["metadata"]["matching"] == 5
    )
    tool.run({"query": "stroke"})
    assert len(tool.calls) == 3  # served from the kept list


def test_rows_are_compact_and_name_the_published_id(tool):
    row = tool.run({"query": "haemorrhage"})["data"][0]
    assert row["publishedId"] == 3 and row["guidelineId"] == 1003
    assert row["url"] == "https://app.magicapp.org/#/guideline/c3"
    assert "contactEmail" not in row
    assert "publishedId" in tool.run({})["metadata"]["id_to_use"]


def test_every_word_matches_name_first_then_organization_or_description(tool):
    out = tool.run({"query": "stroke"})
    assert [r["publishedId"] for r in out["data"]] == [
        1,
        2,
        4,
    ]  # 4: only its description says stroke
    assert out["metadata"]["matched_by"] == "every word"
    assert [r["publishedId"] for r in tool.run({"query": "pregnan"})["data"]] == [
        5
    ]  # a word beginning
    assert tool.run({"query": "is"})["data"] == []  # not inside 'this'


def test_without_every_word_the_most_matching_come_first_and_are_flagged(tool):
    out = tool.run({"query": "stroke thrombolysis aspirin"})
    assert [r["publishedId"] for r in out["data"]][:1] == [1]
    assert (
        out["metadata"]["matched_by"] == "any word"
        and "matching_note" in out["metadata"]
    )


def test_language_limit_and_offset(tool):
    english = tool.run({"query": "stroke", "language": "en"})["data"]
    assert [r["publishedId"] for r in english] == [
        1,
        2,
    ]  # en-au counts as English, nl does not
    page = tool.run({"limit": 2, "offset": 1})
    assert [r["publishedId"] for r in page["data"]] == [2, 3]
    assert page["metadata"]["next_offset"] == 3
    assert (
        tool.run({"limit": 999})["metadata"]["returned"] == 5
    )  # capped at MAX_LIMIT, not an error
    assert tool.run({"limit": "x"})["status"] == "error"


def test_a_failed_fetch_is_an_error_and_is_not_kept(tool, monkeypatch):
    def down(*args, **kwargs):
        return _Response({"message": "unavailable"}, status=503)

    monkeypatch.setattr(M, "request_with_retry", down)
    out = tool.run({"query": "stroke"})
    assert out["status"] == "error" and "unavailable" in out["error"]
    assert M._cache["rows"] is None


def test_config_parameters_are_optional_and_registered():
    config = next(
        t
        for t in json.loads((DATA / "clinical_guidelines_tools.json").read_text())
        if t["name"] == "MAGICapp_list_guidelines"
    )
    assert config["type"] == "MAGICappGuidelineListTool"
    for name in ("query", "language", "limit", "offset"):
        assert "null" in config["parameter"]["properties"][name]["type"], name
    assert config["parameter"]["required"] == []
    assert all(example.get("query") != "TEST" for example in config["test_examples"])
    from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY

    assert STATIC_LAZY_REGISTRY["MAGICappGuidelineListTool"] == "magicapp_tool"
