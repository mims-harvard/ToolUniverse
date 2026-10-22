from typing import Any

import pytest

from tooluniverse.interpro_entry_tool import InterProEntryTool
from tooluniverse.interpro_member_db_tool import InterProMemberDBTool


class _Response:
    status_code = 200

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
            "list_member_entries",
            {"member_database": "pfam", "cursor": "old"},
            {
                "count": 30134,
                "next": "https://example.test/?cursor=new&page_size=20",
                "results": [{"metadata": {"accession": "PF00001"}}],
            },
            "entries",
        ),
        (
            "get_structures_for_entry",
            {"interpro_id": "IPR000719", "cursor": "old"},
            {
                "count": 8135,
                "next": "https://example.test/?cursor=new&page_size=20",
                "results": [{"metadata": {"accession": "1abc"}}],
            },
            "structures",
        ),
    ],
)
def test_member_database_endpoints_forward_cursor(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    arguments: dict[str, Any],
    payload: dict[str, Any],
    collection: str,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response(payload)

    monkeypatch.setattr("tooluniverse.interpro_member_db_tool.requests.get", fake_get)
    tool = InterProMemberDBTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert captured["params"]["cursor"] == "old"
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "new"
    assert result["data"][collection]


@pytest.mark.parametrize(
    ("endpoint", "arguments"),
    [
        ("entries_for_protein", {"accession": "P04637", "cursor": "old"}),
        ("search_entries", {"query": "kinase", "cursor": "old"}),
    ],
)
def test_entry_endpoints_forward_cursor(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    arguments: dict[str, Any],
) -> None:
    captured: dict[str, Any] = {}
    payload = {
        "count": 2,
        "next": "https://example.test/?cursor=new&page_size=20",
        "results": [{"metadata": {"accession": "IPR1", "name": "One"}}],
    }

    def fake_get(url: str, **kwargs: Any) -> _Response:
        captured.update(kwargs)
        return _Response(payload)

    monkeypatch.setattr("tooluniverse.interpro_entry_tool.requests.get", fake_get)
    tool = InterProEntryTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert captured["params"]["cursor"] == "old"
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "new"
    assert result["data"]["truncated"] is True


@pytest.mark.parametrize(
    ("endpoint", "base", "invalid"),
    [
        ("entries_for_protein", {"accession": "P04637"}, {"page_size": "2"}),
        ("entries_for_protein", {"accession": "P04637"}, {"page_size": 0}),
        ("entries_for_protein", {"accession": "P04637"}, {"page_size": 201}),
        ("search_entries", {"query": "kinase"}, {"page_size": False}),
        ("search_entries", {"query": "kinase"}, {"page_size": 51}),
        ("search_entries", {"query": "kinase"}, {"cursor": 123}),
        ("search_entries", {"query": "kinase"}, {"entry_type": "garbage"}),
    ],
)
def test_entry_endpoints_reject_coerced_or_invalid_controls(
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    base: dict[str, Any],
    invalid: dict[str, Any],
) -> None:
    def unexpected_get(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("invalid controls must not reach InterPro")

    monkeypatch.setattr("tooluniverse.interpro_entry_tool.requests.get", unexpected_get)
    result = InterProEntryTool({"fields": {"endpoint": endpoint}}).run(
        {**base, **invalid}
    )
    assert result["status"] == "error"
