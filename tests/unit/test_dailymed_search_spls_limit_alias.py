"""Regression guard for Fix-R33A-1: DailyMed_search_spls only recognized its
own "pagesize" param, so a caller guessing the far more common ToolUniverse
pagination name "limit" (used by CPIC, ClinVar, GWAS, ...) was silently
ignored -- confirmed live, {"drug_name": "isoniazid", "limit": 3} returned
all 44 matching labels instead of 3.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dailymed_tool import SearchSPLTool

pytestmark = pytest.mark.unit


def _tool():
    return SearchSPLTool({"name": "DailyMed_search_spls", "parameter": {"properties": {}}})


def _resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"data": [], "metadata": {}}
    return resp


def test_limit_alias_maps_to_pagesize():
    tool = _tool()
    with patch("tooluniverse.dailymed_tool.requests.get", return_value=_resp()) as mock_get:
        tool.run({"drug_name": "isoniazid", "limit": 3})

    params = mock_get.call_args.kwargs["params"]
    assert params["pagesize"] == 3


def test_pagesize_still_takes_precedence_over_limit():
    tool = _tool()
    with patch("tooluniverse.dailymed_tool.requests.get", return_value=_resp()) as mock_get:
        tool.run({"drug_name": "isoniazid", "pagesize": 5, "limit": 3})

    params = mock_get.call_args.kwargs["params"]
    assert params["pagesize"] == 5


def test_no_pagination_arg_defaults_to_100():
    tool = _tool()
    with patch("tooluniverse.dailymed_tool.requests.get", return_value=_resp()) as mock_get:
        tool.run({"drug_name": "isoniazid"})

    params = mock_get.call_args.kwargs["params"]
    assert params["pagesize"] == 100
