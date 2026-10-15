"""OmniPath must accept list gene input and refuse a meaningless limit."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.omnipath_tool import OmniPathTool

pytestmark = pytest.mark.unit

CONFIG = Path(__file__).resolve().parents[2] / "src/tooluniverse/data/omnipath_tools.json"


def _tools():
    data = json.loads(CONFIG.read_text())
    return data if isinstance(data, list) else data["tools"]


def test_limit_cannot_be_zero_or_negative():
    """limit=0 returned [] with status success, reading as a real negative."""
    checked = 0
    for tool in _tools():
        limit = (tool["parameter"]["properties"] or {}).get("limit")
        if limit is None:
            continue
        checked += 1
        assert limit.get("minimum") == 1, tool["name"]
    assert checked, "expected tools exposing limit"


def test_gene_parameters_accept_a_list():
    """The sibling interactome tool takes a list; agents carry the habit over."""
    for tool in _tools():
        props = tool["parameter"]["properties"] or {}
        for key in ("partners", "sources", "targets", "proteins", "enzymes"):
            if key in props:
                assert "array" in props[key]["type"], f"{tool['name']}.{key}"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["EGFR"], "EGFR"),
        (["EGFR", "TGFA"], "EGFR,TGFA"),
        (("EGFR", " TGFA "), "EGFR,TGFA"),
        ("EGFR", "EGFR"),
    ],
)
def test_list_partners_are_joined_for_the_api(value, expected):
    tool = OmniPathTool(
        {"name": "lr", "fields": {"endpoint": "ligand_receptor"}}
    )
    captured = {}

    def fake_request(path, params):
        captured.update(params)
        return []

    with patch.object(tool, "_make_request", side_effect=fake_request):
        tool.run({"partners": value, "limit": 5})

    assert captured["partners"] == expected


def test_an_empty_list_does_not_become_an_empty_filter():
    tool = OmniPathTool({"name": "lr", "fields": {"endpoint": "ligand_receptor"}})
    with patch.object(tool, "_make_request", return_value=[]) as request:
        result = tool.run({"partners": []})
    # No usable filter remains, so the tool must say so rather than query.
    assert result["status"] == "error"
    request.assert_not_called()
