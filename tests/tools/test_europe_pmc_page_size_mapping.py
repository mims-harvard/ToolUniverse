#!/usr/bin/env python3
"""
Unit tests for EuropePMC REST page_size -> pageSize mapping.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.europe_pmc_tool import EuropePMCRESTTool


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, url="https://example.test"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.url = url
        self.text = ""

    def json(self):
        return self._payload


@pytest.mark.unit
def test_page_size_is_mapped_to_pageSize(monkeypatch):
    tool = EuropePMCRESTTool(
        {
            "name": "EuropePMC_get_citations",
            "fields": {
                "endpoint": "https://www.ebi.ac.uk/europepmc/webservices/rest/{source}/{article_id}/citations"
            },
        }
    )

    captured = {}

    def fake_request_with_retry(session, method, url, *, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = dict(params or {})
        return _FakeResponse(status_code=200, payload={"ok": True}, url=url)

    monkeypatch.setattr(
        "tooluniverse.europe_pmc_tool.request_with_retry", fake_request_with_retry
    )

    result = tool.run(
        {"source": "MED", "article_id": "25428363", "page_size": 10, "page": 1}
    )

    assert result["status"] == "success"
    assert "pageSize" in captured["params"]
    assert captured["params"]["pageSize"] == 10
    assert "page_size" not in captured["params"]
