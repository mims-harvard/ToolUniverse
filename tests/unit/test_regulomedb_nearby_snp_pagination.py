from typing import Any

from tooluniverse.regulomedb_tool import RegulomeDBRESTTool


class _Response:
    status_code = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


def _tool() -> RegulomeDBRESTTool:
    return RegulomeDBRESTTool(
        {
            "fields": {
                "endpoint": ("https://regulomedb.test/?regions={rsid}&genome=GRCh38")
            }
        }
    )


def test_regulomedb_nearby_snps_are_pageable(monkeypatch) -> None:
    payload = {
        "variants": [{"rsids": ["rs1"]}],
        "nearby_snps": [{"rsid": f"rs{i}"} for i in range(11)],
        "@graph": [],
    }
    tool = _tool()
    monkeypatch.setattr(tool.session, "get", lambda *args, **kwargs: _Response(payload))

    first = tool.run({"rsid": "rs1", "nearby_snp_limit": 3})
    last = tool.run({"rsid": "rs1", "nearby_snp_offset": 10, "nearby_snp_limit": 3})

    assert [row["rsid"] for row in first["data"]["nearby_snps"]] == [
        "rs0",
        "rs1",
        "rs2",
    ]
    assert first["data"]["nearby_snps_total"] == 11
    assert first["data"]["nearby_snps_returned"] == 3
    assert first["data"]["nearby_snps_truncated"] is True
    assert first["data"]["next_nearby_snp_offset"] == 3

    assert [row["rsid"] for row in last["data"]["nearby_snps"]] == ["rs10"]
    assert last["data"]["nearby_snps_returned"] == 1
    assert last["data"]["nearby_snps_truncated"] is False
    assert last["data"]["next_nearby_snp_offset"] is None
