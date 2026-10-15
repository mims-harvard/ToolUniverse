"""DailyMed cannot filter its drug-class list, so ToolUniverse does it.

`/drugclasses.json` accepts only `page` and `pagesize`. A name filter makes it
answer HTTP 500 with `{"data": [], "metadata": {}}` -- measured for
`drug_class_name`, `class_name` and `code` -- while `drug_name` and `name` are
accepted and ignored, the response still carrying all 1210 classes. The generic
REST tool passed `drug_class_name` straight through, so all three of this tool's
shipped examples returned that 500: they were 3 of the 6 failures the weekly
health check reported for clinical_guidelines.

These tests stub the HTTP layer. The point is the filtering and paging logic,
and the catalogue is 13 upstream pages, which is not something to fetch in a
unit test.
"""

import pytest

from tooluniverse.dailymed_drug_classes_tool import DailyMedDrugClassesTool

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "DailyMed_search_drug_classes",
    "type": "DailyMedDrugClassesTool",
    "fields": {
        "endpoint": "https://dailymed.nlm.nih.gov/dailymed/services/v2/drugclasses.json"
    },
    "parameter": {
        "type": "object",
        "properties": {
            "drug_class_name": {"type": "string"},
            "page": {"type": "integer"},
            "pagesize": {"type": "integer"},
        },
        "required": ["drug_class_name"],
    },
}

# Three pages, so paging is actually exercised rather than assumed.
_PAGES = {
    1: ["Aminoglycoside Antibacterial", "Adenosine Receptor Agonist"],
    2: ["Cytomegalovirus pUL97 Kinase Inhibitor", "Tyrosine Kinase Inhibitor"],
    3: ["Serotonin Receptor Antagonist", "Thiazide Diuretic"],
}


class _Response:
    status_code = 200

    def __init__(self, page):
        self._page = page

    def json(self):
        return {
            "data": [
                {"code": f"N{self._page}{i}", "name": n, "type": "EPC"}
                for i, n in enumerate(_PAGES[self._page])
            ],
            "metadata": {"total_pages": len(_PAGES), "total_elements": 6},
        }


def _tool(monkeypatch, calls=None):
    tool = DailyMedDrugClassesTool(CONFIG)

    def fake_request(session, method, url, params=None, **kwargs):
        if calls is not None:
            calls.append(params["page"])
        return _Response(params["page"])

    monkeypatch.setattr(
        "tooluniverse.dailymed_drug_classes_tool.request_with_retry", fake_request
    )
    return tool


def test_the_filter_matches_across_every_upstream_page(monkeypatch):
    calls = []
    result = _tool(monkeypatch, calls).run({"drug_class_name": "kinase"})

    assert result["status"] == "success"
    assert [r["name"] for r in result["data"]] == [
        "Cytomegalovirus pUL97 Kinase Inhibitor",
        "Tyrosine Kinase Inhibitor",
    ], "a match on page 2 is only found if every page is read"
    assert calls == [1, 2, 3], "all pages must be read before filtering"
    assert result["metadata"]["total_matches"] == 2
    assert result["metadata"]["classes_searched"] == 6


def test_the_match_is_case_insensitive_and_a_substring(monkeypatch):
    result = _tool(monkeypatch).run({"drug_class_name": "RECEPTOR"})

    assert [r["name"] for r in result["data"]] == [
        "Adenosine Receptor Agonist",
        "Serotonin Receptor Antagonist",
    ]


def test_paging_applies_to_the_matches_not_to_the_upstream_pages(monkeypatch):
    """`pagesize` has to mean matches, or a filtered search cannot be paged."""
    first = _tool(monkeypatch).run({"drug_class_name": "receptor", "pagesize": 1})
    second = _tool(monkeypatch).run(
        {"drug_class_name": "receptor", "pagesize": 1, "page": 2}
    )

    assert [r["name"] for r in first["data"]] == ["Adenosine Receptor Agonist"]
    assert [r["name"] for r in second["data"]] == ["Serotonin Receptor Antagonist"]
    assert first["metadata"]["total_matches"] == 2, (
        "the total must count every match, not just the page returned"
    )


def test_no_match_is_a_success_with_an_empty_list(monkeypatch):
    """Nothing matching is an answer, not a failure."""
    result = _tool(monkeypatch).run({"drug_class_name": "zzzznotaclass"})

    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_matches"] == 0


def test_the_metadata_says_who_did_the_filtering(monkeypatch):
    """A caller must be able to tell the filter was not applied upstream."""
    result = _tool(monkeypatch).run({"drug_class_name": "kinase"})

    assert "ToolUniverse" in result["metadata"]["filtered_by"]
    assert result["metadata"]["upstream_pages_read"] == 3


def test_an_upstream_error_is_reported_not_silently_emptied(monkeypatch):
    tool = DailyMedDrugClassesTool(CONFIG)

    class _Broken:
        status_code = 500

        def json(self):  # pragma: no cover - never reached
            raise AssertionError("a 500 must not be parsed")

    monkeypatch.setattr(
        "tooluniverse.dailymed_drug_classes_tool.request_with_retry",
        lambda *a, **k: _Broken(),
    )
    result = tool.run({"drug_class_name": "kinase"})

    assert result["status"] == "error"
    assert "500" in result["error"]
