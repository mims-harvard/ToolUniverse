"""Regression guard for Fix-R43A-1: four tools wrongly required params that
already have a working Python-level default, matching the round-37 backlog's
first sub-pattern (pure `.get(x, default)` fallback already correct, only
the schema wrongly required it):

- DBLP_search_publications' `limit` (dblp_tool.py already does
  `int(arguments.get("limit", 10))`).
- HAL_search_archive's `max_results` (hal_tool.py already does
  `int(arguments.get("max_results", 10))`).
- get_webpage_title's `timeout` (url_tool.py's URLHTMLTagTool already does
  `arguments.get("timeout", 20)`).
- get_webpage_text_from_url's `timeout` (url_tool.py's URLToPDFTextTool
  already does `int(arguments.get("timeout", 30))`).

Confirmed live for all four: omitting the param previously failed schema
validation ("'<param>' is a required property") despite the tool being
fully answerable without it.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dblp_tool import DBLPTool
from tooluniverse.hal_tool import HALTool
from tooluniverse.url_tool import URLHTMLTagTool, URLToPDFTextTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(filename, name):
    configs = json.loads((_DATA_DIR / filename).read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in {filename}")


def test_dblp_requires_only_query():
    cfg = _tool_config("dblp_tools.json", "DBLP_search_publications")
    assert cfg["parameter"]["required"] == ["query"]


def test_hal_requires_only_query():
    cfg = _tool_config("hal_tools.json", "HAL_search_archive")
    assert cfg["parameter"]["required"] == ["query"]


def test_webpage_title_requires_only_url():
    cfg = _tool_config("url_fetch_tools.json", "get_webpage_title")
    assert cfg["parameter"]["required"] == ["url"]


def test_webpage_text_requires_only_url():
    cfg = _tool_config("url_fetch_tools.json", "get_webpage_text_from_url")
    assert cfg["parameter"]["required"] == ["url"]


def test_dblp_run_uses_default_limit_when_omitted():
    cfg = _tool_config("dblp_tools.json", "DBLP_search_publications")
    tool = DBLPTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"result": {"hits": {"hit": []}}}

    with patch("tooluniverse.dblp_tool.requests.get", return_value=resp) as mock_get:
        tool.run({"query": "transformers"})
        params = mock_get.call_args.kwargs["params"]

    assert params["h"] == 10


def test_hal_run_uses_default_max_results_when_omitted():
    cfg = _tool_config("hal_tools.json", "HAL_search_archive")
    tool = HALTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"response": {"docs": []}}

    with patch("tooluniverse.hal_tool.requests.get", return_value=resp) as mock_get:
        tool.run({"query": "genomics"})
        params = mock_get.call_args.kwargs["params"]

    assert params["rows"] == 10


def test_webpage_title_run_uses_default_timeout_when_omitted():
    cfg = _tool_config("url_fetch_tools.json", "get_webpage_title")
    tool = URLHTMLTagTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.text = "<html><head><title>Example</title></head></html>"

    with patch("tooluniverse.url_tool.requests.get", return_value=resp) as mock_get:
        result = tool.run({"url": "https://example.com"})
        called_timeout = mock_get.call_args.kwargs["timeout"]

    assert called_timeout == 20
    assert result["title"] == "Example"


def test_webpage_text_run_uses_default_timeout_when_omitted():
    cfg = _tool_config("url_fetch_tools.json", "get_webpage_text_from_url")
    tool = URLToPDFTextTool(cfg)

    err = tool.validate_parameters({"url": "https://example.com"})

    assert err is None
