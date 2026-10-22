from typing import Any

from tooluniverse.pdbe_search_tool import PDBeSearchTool


class _Response:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "response": {
                "numFound": 10,
                "docs": [{"pdb_id": "1abc"}, {"pdb_id": "2abc"}],
            }
        }


def test_pdbe_organism_search_forwards_and_reports_start(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.pdbe_search_tool.requests.get", fake_get)
    tool = PDBeSearchTool({"fields": {"endpoint_type": "search_by_organism"}})

    result = tool.run({"organism": "Homo sapiens", "limit": 2, "start": 4})

    assert captured["params"]["rows"] == 2
    assert captured["params"]["start"] == 4
    assert result["metadata"]["start"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_start"] == 6
