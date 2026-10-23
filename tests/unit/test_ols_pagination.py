from typing import Any

import pytest

from tooluniverse.ols_tool import OLSTool


def _term(index: int) -> dict[str, Any]:
    return {
        "iri": f"http://purl.obolibrary.org/obo/GO_{index:07d}",
        "label": f"term {index}",
        "ontology_name": "go",
        "short_form": f"GO:{index:07d}",
    }


def test_search_terms_forwards_start_and_reports_continuation(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(self, path: str, params=None):
        captured["path"] = path
        captured["params"] = params
        return {
            "response": {
                "docs": [_term(4), _term(5)],
                "numFound": 10,
                "start": 3,
            }
        }

    monkeypatch.setattr(OLSTool, "_get_json", fake_get)
    tool = OLSTool({"fields": {"operation": "search_terms"}})

    result = tool.run(
        {"operation": "search_terms", "query": "cancer", "rows": 2, "start": 3}
    )

    assert captured == {
        "path": "/api/search",
        "params": {
            "q": "cancer",
            "rows": 2,
            "start": 3,
            "exact": False,
            "obsoletes": False,
        },
    }
    assert result["start"] == 3
    assert result["total_items"] == 10
    assert result["has_more"] is True
    assert result["next_start"] == 5


@pytest.mark.parametrize(
    ("operation", "endpoint"),
    [
        ("get_term_children", "children"),
        ("get_term_ancestors", "ancestors"),
    ],
)
def test_hierarchy_operations_forward_page_and_report_continuation(
    monkeypatch, operation: str, endpoint: str
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(self, path: str, params=None):
        captured["path"] = path
        captured["params"] = params
        return {
            "elements": [_term(4), _term(5)],
            "page": 1,
            "numElements": 2,
            "totalPages": 4,
            "totalElements": 8,
        }

    monkeypatch.setattr(OLSTool, "_get_json", fake_get)
    tool = OLSTool({"fields": {"operation": operation}})

    result = tool.run(
        {"operation": operation, "term_id": "GO:0008150", "size": 2, "page": 1}
    )

    assert captured["path"].endswith(f"/{endpoint}")
    assert captured["params"] == {
        "page": 1,
        "size": 2,
        "includeObsoleteEntities": False,
    }
    assert result["total_items"] == 8
    assert result["pagination"] == {
        "page": 1,
        "size": 2,
        "total_pages": 4,
        "total_items": 8,
        "has_more": True,
        "next_page": 2,
    }


def test_empty_hierarchy_page_preserves_upstream_total() -> None:
    tool = OLSTool({"fields": {"operation": "get_term_children"}})

    result = tool._format_term_collection(
        {
            "elements": [],
            "page": {
                "number": 3,
                "size": 2,
                "totalPages": 4,
                "totalElements": 7,
            },
        },
        2,
    )

    assert result["terms"] == []
    assert result["total_items"] == 7
    assert result["pagination"]["has_more"] is False
    assert result["pagination"]["next_page"] is None
