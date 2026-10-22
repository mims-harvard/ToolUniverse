from typing import Any

import pytest

from tooluniverse.inaturalist_tool import INaturalistTool


class _Response:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = results

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"total_results": 10, "results": self._results}


@pytest.mark.parametrize(
    ("endpoint", "arguments", "results"),
    [
        (
            "search_taxa",
            {"query": "Panthera", "page": 2, "per_page": 3},
            [{"id": 1, "name": "Panthera"}],
        ),
        (
            "search_observations",
            {"taxon_id": 3, "page": 2, "per_page": 3},
            [{"id": 2, "taxon": {}, "geojson": {}, "photos": []}],
        ),
        (
            "species_counts",
            {"taxon_id": 3, "page": 2, "per_page": 3},
            [{"count": 4, "taxon": {"id": 3, "name": "Aves"}}],
        ),
    ],
)
def test_inaturalist_list_endpoints_forward_page_and_report_continuation(
    monkeypatch,
    endpoint: str,
    arguments: dict[str, Any],
    results: list[dict[str, Any]],
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response(results)

    monkeypatch.setattr("tooluniverse.inaturalist_tool.requests.get", fake_get)
    tool = INaturalistTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert result["status"] == "success"
    assert captured["params"]["page"] == 2
    assert captured["params"]["per_page"] == 3
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["api_result_window_limit"] == 10000
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["total_results_is_exact"] is True


def test_observations_expose_id_below_sliding_cursor(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response(
            [
                {"id": 105, "taxon": {}, "geojson": {}, "photos": []},
                {"id": 101, "taxon": {}, "geojson": {}, "photos": []},
            ]
        )

    monkeypatch.setattr("tooluniverse.inaturalist_tool.requests.get", fake_get)
    tool = INaturalistTool({"fields": {"endpoint": "search_observations"}})
    result = tool.run({"taxon_id": 48662, "per_page": 2, "page": 1, "id_below": 110})

    assert captured["params"]["order_by"] == "id"
    assert captured["params"]["order"] == "desc"
    assert captured["params"]["id_below"] == 110
    assert result["metadata"]["next_id_below"] == 101
    assert result["metadata"]["total_results_scope"] == "records_below_id_below"


def test_inaturalist_rejects_silent_coercions_and_fake_empty_filters(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "tooluniverse.inaturalist_tool.requests.get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network called")),
    )
    taxa = INaturalistTool({"fields": {"endpoint": "search_taxa"}})
    observations = INaturalistTool({"fields": {"endpoint": "search_observations"}})
    counts = INaturalistTool({"fields": {"endpoint": "species_counts"}})

    assert taxa.run({"query": "x", "page": 0})["parameter"] == "page"
    assert taxa.run({"query": "x", "per_page": 201})["parameter"] == "per_page"
    assert (
        observations.run({"taxon_id": 1, "quality_grade": "bogus"})["parameter"]
        == "quality_grade"
    )
    assert observations.run({"taxon_id": 1, "per_page": 201})["parameter"] == "per_page"
    assert (
        observations.run({"taxon_id": 1, "page": 3334, "per_page": 3})["parameter"]
        == "page"
    )
    assert (
        observations.run({"taxon_id": 1, "id_below": 100, "page": 2})["parameter"]
        == "page"
    )
    assert (
        counts.run({"taxon_id": 1, "quality_grade": "bogus"})["parameter"]
        == "quality_grade"
    )
