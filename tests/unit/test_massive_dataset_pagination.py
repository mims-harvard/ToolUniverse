from typing import Any

from tooluniverse.massive_tool import MassIVETool


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, Any]]:
        return [{"accession": [{"value": "MSV000000001"}]}]


def test_massive_search_forwards_one_based_page_number(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.massive_tool.requests.get", fake_get)
    tool = MassIVETool({"fields": {"operation": "search_datasets"}})

    result = tool.run({"page_size": 3, "page_number": 2})

    assert result["status"] == "success"
    assert captured["params"]["pageSize"] == 3
    assert captured["params"]["pageNumber"] == 2
    assert result["data"][0]["accessions"] == ["MSV000000001"]
    assert result["metadata"] == {
        "page_number": 2,
        "page_size": 3,
        "returned": 1,
        "has_more": False,
        "possible_more": False,
        "next_page": None,
        "results_lower_bound": 4,
        "total_results": 4,
        "total_results_is_exact": True,
    }


def test_massive_full_page_exposes_uncertain_but_recoverable_next_page(monkeypatch):
    class FullResponse(_Response):
        def json(self) -> list[dict[str, Any]]:
            return [
                {"accession": [{"value": f"MSV{i}"}]}
                for i in range(3)
            ]

    monkeypatch.setattr(
        "tooluniverse.massive_tool.requests.get", lambda *a, **k: FullResponse()
    )
    result = MassIVETool({"fields": {"operation": "search_datasets"}}).run(
        {"page_size": 3, "page_number": 2}
    )

    assert result["metadata"]["has_more"] is None
    assert result["metadata"]["possible_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["results_lower_bound"] == 6
    assert result["metadata"]["total_results"] is None
    assert "does not expose a total" in result["metadata"]["warning"]


def test_massive_rejects_values_that_used_to_be_silently_clamped(monkeypatch):
    called = False

    def fake_get(*args: Any, **kwargs: Any) -> _Response:
        nonlocal called
        called = True
        return _Response()

    monkeypatch.setattr("tooluniverse.massive_tool.requests.get", fake_get)
    tool = MassIVETool({"fields": {"operation": "search_datasets"}})

    for arguments in (
        {"page_size": 0},
        {"page_size": 101},
        {"page_size": True},
        {"page_number": 0},
        {"page_number": -1},
        {"page_number": "2"},
    ):
        result = tool.run(arguments)
        assert result["status"] == "error"

    assert called is False

