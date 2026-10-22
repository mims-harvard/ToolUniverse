from typing import Any

import pytest

from tooluniverse.rcsb_search_tool import RCSBSearchTool

pytestmark = pytest.mark.unit


class _Response:
    status_code = 200
    content = b"json"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "total_count": 10,
            "result_set": [
                {"identifier": "1AAA", "score": 1.0},
                {"identifier": "2BBB", "score": 0.9},
            ],
        }


def test_rcsb_search_forwards_start_and_reports_global_continuation(monkeypatch) -> None:
    """A non-zero start must reach RCSB and rank rows by their global position."""
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.rcsb_search_tool.requests.post", fake_post)
    # _enrich_text_results returns (results, metadata_enrichment); the stub must
    # match that shape or the caller unpacks the results list itself.
    monkeypatch.setattr(
        RCSBSearchTool, "_enrich_text_results", lambda self, x: (x, None)
    )
    tool = RCSBSearchTool({})

    result = tool.run(
        {"query": "kinase", "search_type": "text", "max_results": 2, "start": 3}
    )

    assert captured["json"]["request_options"]["paginate"] == {
        "start": 3,
        "rows": 2,
    }
    assert result["status"] == "success"
    assert [row["rank"] for row in result["data"]["results"]] == [4, 5]
    assert result["data"]["total_found"] == 10
    assert result["data"]["start"] == 3
    assert result["data"]["returned"] == 2
    assert result["data"]["has_more"] is True
    assert result["data"]["next_start"] == 5
