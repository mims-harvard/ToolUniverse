from typing import Any

import pytest

from tooluniverse.interpro_domain_arch_tool import InterProDomainArchTool


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
            "structures_for_domain",
            {"pfam_accession": "PF00069", "cursor": "old"},
            {
                "count": 5393,
                "next": "https://example.test/?cursor=new&page_size=20",
                "results": [{"metadata": {"accession": "1abc"}}],
            },
            "structures",
        ),
        (
            "protein_domain_architecture",
            {"accession": "P04637", "cursor": "old"},
            {
                "count": 60,
                "next": "https://example.test/?cursor=new&page_size=50",
                "results": [
                    {
                        "metadata": {"accession": "PF1", "name": "One"},
                        "proteins": [],
                    }
                ],
            },
            "domains",
        ),
    ],
)
def test_interpro_endpoints_forward_cursor(
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

    monkeypatch.setattr("tooluniverse.interpro_domain_arch_tool.requests.get", fake_get)
    tool = InterProDomainArchTool({"fields": {"endpoint": endpoint}})

    result = tool.run(arguments)

    assert result["status"] == "success"
    assert captured["params"]["cursor"] == "old"
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "new"
    assert collection in result["data"]


def test_clan_member_total_and_offset_are_not_conflated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = [
        {"accession": accession, "name": accession}
        for accession in ["PF4", "PF1", "PF3", "PF2", "PF5"]
    ]
    payload = {
        "metadata": {
            "name": "Clan",
            "relationships": {"nodes": nodes},
        }
    }
    monkeypatch.setattr(
        "tooluniverse.interpro_domain_arch_tool.requests.get",
        lambda *args, **kwargs: _Response(payload),
    )
    tool = InterProDomainArchTool({"fields": {"endpoint": "clan_members"}})

    result = tool.run(
        {"clan_accession": "CL0016", "member_offset": 2, "max_results": 2}
    )

    assert result["data"]["member_count"] == 5
    assert result["data"]["returned"] == 2
    assert result["data"]["members_truncated"] is True
    assert result["data"]["next_member_offset"] == 4
    assert [member["accession"] for member in result["data"]["members"]] == [
        "PF3",
        "PF4",
    ]

