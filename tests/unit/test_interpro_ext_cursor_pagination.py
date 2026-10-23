from typing import Any

from tooluniverse.interpro_ext_tool import InterProExtTool


class _Response:
    status_code = 200
    content = b"{}"  # non-empty body: InterPro answers no matches with HTTP 204

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "count": 40,
            "next": "https://example.test/?cursor=new&page_size=3",
            "results": [{"metadata": {"accession": "P1", "source_organism": {}}}],
        }


def test_proteins_by_domain_forwards_and_returns_cursor(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response()

    monkeypatch.setattr("tooluniverse.interpro_ext_tool.requests.get", fake_get)
    tool = InterProExtTool({"fields": {"endpoint": "proteins_by_domain"}})

    result = tool.run({"domain_id": "IPR011615", "cursor": "old"})

    assert captured["params"]["cursor"] == "old"
    assert result["data"]["total_proteins"] == 40
    assert result["data"]["returned"] == 1
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "new"
