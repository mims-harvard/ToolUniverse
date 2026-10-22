from typing import Any

import pytest

from tooluniverse.pfam_tool import PfamTool


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


@pytest.mark.parametrize(
    ("endpoint", "arguments", "payload", "collection"),
    [
        (
            "search_families",
            {"query": "kinase", "max_results": 2, "cursor": "old-family"},
            {
                "count": 9,
                "next": "https://example.test/?cursor=new-family&page_size=2",
                "results": [
                    {"metadata": {"accession": "PF1", "name": "One"}},
                    {"metadata": {"accession": "PF2", "name": "Two"}},
                ],
            },
            "families",
        ),
        (
            "get_family_proteins",
            {"pfam_accession": "PF00001", "cursor": "old-protein"},
            {
                "count": 289,
                "next": "https://example.test/?cursor=new-protein&page_size=20",
                "results": [{"metadata": {"accession": "P1"}, "entries": []}],
            },
            "proteins",
        ),
        (
            "search_clans",
            {"cursor": "old-clan"},
            {
                "count": 891,
                "next": "https://example.test/?cursor=new-clan&page_size=20",
                "results": [{"metadata": {"accession": "CL1", "name": "One"}}],
            },
            "clans",
        ),
        (
            "get_family_proteomes",
            {"pfam_accession": "PF00001", "cursor": "old-proteome"},
            {
                "count": 1890,
                "next": "https://example.test/?cursor=new-proteome&page_size=20",
                "results": [{"metadata": {"accession": "UP1", "name": "One"}}],
            },
            "proteomes",
        ),
    ],
)
def test_pfam_endpoints_forward_and_return_cursor(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    arguments: dict[str, Any],
    payload: dict[str, Any],
    collection: str,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured["url"] = url
        captured.update(kwargs)
        return _Response(payload)

    monkeypatch.setattr("tooluniverse.pfam_tool.requests.get", fake_get)
    tool = PfamTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert result["status"] == "success"
    assert captured["params"]["cursor"] == arguments["cursor"]
    assert result["data"][collection]
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"].startswith("new-")


def test_pfam_last_page_reports_no_next_cursor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tooluniverse.pfam_tool.requests.get",
        lambda *args, **kwargs: _Response({"count": 1, "next": None, "results": []}),
    )
    tool = PfamTool({"fields": {"endpoint": "search_clans"}})

    result = tool.run({})

    assert result["data"]["has_more"] is False
    assert result["data"]["next_cursor"] is None

