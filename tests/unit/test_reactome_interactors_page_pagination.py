from typing import Any

from tooluniverse.reactome_interactors_tool import ReactomeInteractorsTool


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


def test_interactor_details_forward_page_and_report_next_page(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        if url.endswith("/summary"):
            return _Response({"entities": [{"count": 10}]})
        captured.update(kwargs)
        return _Response(
            {"entities": [{"acc": "P04637", "interactors": [{"acc": "P1"}]}]}
        )

    monkeypatch.setattr("tooluniverse.reactome_interactors_tool.requests.get", fake_get)
    tool = ReactomeInteractorsTool({"fields": {"endpoint": "interactors"}})

    result = tool.run({"accession": "P04637", "page_size": 3, "page": 2})

    assert captured["params"] == {"page": 2, "pageSize": 3}
    assert result["status"] == "success"
    assert result["data"]["total_interactors"] == 10
    assert result["data"]["page"] == 2
    assert result["data"]["has_more"] is True
    assert result["data"]["next_page"] == 3


def test_interactor_details_rejects_coerced_page_controls(monkeypatch) -> None:
    def unexpected_get(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("invalid paging must not reach Reactome")

    monkeypatch.setattr("tooluniverse.reactome_interactors_tool.requests.get", unexpected_get)
    tool = ReactomeInteractorsTool({"fields": {"endpoint": "interactors"}})
    for pagination in (
        {"page_size": "2"},
        {"page_size": 0},
        {"page_size": False},
        {"page": "2"},
        {"page": 0},
    ):
        result = tool.run({"accession": "P04637", **pagination})
        assert result["status"] == "error", pagination


def test_entity_search_discloses_that_rows_are_per_group(monkeypatch) -> None:
    payload = {
        "numberOfMatches": 7,
        "numberOfGroups": 2,
        "results": [
            {
                "typeName": "Protein",
                "entriesCount": 4,
                "entries": [{"stId": "P1", "name": "P1"}, {"stId": "P2", "name": "P2"}],
            },
            {
                "typeName": "Pathway",
                "entriesCount": 3,
                "entries": [{"stId": "R1", "name": "R1"}, {"stId": "R2", "name": "R2"}],
            },
        ],
    }

    def fake_get(*args: Any, **kwargs: Any) -> _Response:
        return _Response(payload)

    monkeypatch.setattr("tooluniverse.reactome_interactors_tool.requests.get", fake_get)
    tool = ReactomeInteractorsTool({"fields": {"endpoint": "search_entity"}})
    result = tool.run({"query": "TP53", "limit": 2, "offset": 0})

    assert len(result["data"]) == 4
    assert result["metadata"]["returned"] == 4
    assert result["metadata"]["rows_per_group"] == 2
    assert result["metadata"]["limit_scope"] == "per_result_group"
    assert result["metadata"]["next_offset"] == 2


def test_entity_search_rejects_coerced_or_clamped_pagination(monkeypatch) -> None:
    def unexpected_get(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("invalid paging must not reach Reactome")

    monkeypatch.setattr("tooluniverse.reactome_interactors_tool.requests.get", unexpected_get)
    tool = ReactomeInteractorsTool({"fields": {"endpoint": "search_entity"}})
    for pagination in (
        {"limit": "2"},
        {"limit": 0},
        {"limit": 1001},
        {"offset": "2"},
        {"offset": -1},
        {"offset": False},
    ):
        result = tool.run({"query": "TP53", **pagination})
        assert result["status"] == "error", pagination
