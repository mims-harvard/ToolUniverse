from typing import Any

from tooluniverse.immport_tool import ImmPortTool


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "hits": {
                "total": {"value": 10},
                "hits": [
                    {"_source": {"study_accession": "SDY1"}},
                    {"_source": {"study_accession": "SDY2"}},
                ],
            }
        }


def test_immport_forwards_and_reports_from_record(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.immport_tool.requests.get", fake_get)
    tool = ImmPortTool({"fields": {"operation": "search_studies"}})

    result = tool.run({"query": "influenza", "limit": 2, "from_record": 4})

    assert captured["params"]["pageSize"] == 2
    assert captured["params"]["fromRecord"] == 4
    assert result["metadata"]["raw_returned"] == 2
    assert result["metadata"]["from_record"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_from_record"] == 6
