"""Regression tests for LitVar2 autocomplete's non-pageable top-N semantics."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/litvar_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "LitVar_search_variants"
    )


def test_full_limit_is_explicitly_capped_and_non_pageable(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = [{"_id": f"v{i}"} for i in range(10)]
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run({"query": "BRCA1", "limit": 10})
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["pagination_supported"] is False
    assert result["metadata"]["next_offset"] is None
    assert "ignores offset" in result["metadata"]["warning"]


def test_short_response_is_complete(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = [{"_id": "only"}]
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run({"query": "rare", "limit": 10})
    assert result["metadata"]["total_results"] == 1
    assert result["metadata"]["result_set_complete"] is True


@pytest.mark.parametrize("limit", [0, 101, 1.5, True])
def test_invalid_limit_is_explicit(limit):
    result = BaseRESTTool(_config()).run({"query": "BRCA1", "limit": limit})
    assert result["status"] == "error"
    assert result["parameter"] == "limit"
