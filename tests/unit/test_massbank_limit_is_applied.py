"""MassBank search tools ignored ``limit`` and returned every spectrum.

The MassBank records API has no page-size parameter (limit, size, page and
max_results are all ignored: 135 spectra for C9H8O4 whatever was asked), so a
documented "maximum number of spectra to return (default 10)" returned all of them.
The tools now truncate client-side and report ``total_before_limit``.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"
NAMES = ["MassBank_search_by_formula", "MassBank_search_by_compound"]


def _config(name):
    tools = json.loads((DATA / "massbank_tools.json").read_text(encoding="utf-8"))
    return next(t for t in tools if t["name"] == name)


def _run(name, arguments, n=25):
    response = MagicMock(status_code=200, text="[]")
    response.json.return_value = [{"accession": f"MSBNK-{i}"} for i in range(n)]
    response.headers = {"content-type": "application/json"}
    tool = BaseRESTTool(_config(name))
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", return_value=response
    ) as get:
        return tool.run(arguments), get


@pytest.mark.parametrize("name", NAMES)
def test_config_truncates_client_side_with_a_real_default_of_ten(name):
    config = _config(name)
    assert config["fields"]["client_side_limit"] is True
    assert config["parameter"]["properties"]["limit"]["default"] == 10


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("MassBank_search_by_formula", {"formula": "C9H8O4"}),
        ("MassBank_search_by_compound", {"compound_name": "aspirin"}),
    ],
)
def test_omitted_limit_returns_ten_and_discloses_the_total(name, arguments):
    result, get = _run(name, arguments)
    assert len(result["data"]) == 10
    assert result["total_before_limit"] == 25
    assert "limit" not in get.call_args.kwargs["params"]  # never sent upstream


def test_explicit_limit_is_honoured_and_larger_than_available_returns_all():
    result, _ = _run("MassBank_search_by_formula", {"formula": "C9H8O4", "limit": 3})
    assert len(result["data"]) == 3
    result, _ = _run("MassBank_search_by_formula", {"formula": "C9H8O4", "limit": 500})
    assert len(result["data"]) == 25
