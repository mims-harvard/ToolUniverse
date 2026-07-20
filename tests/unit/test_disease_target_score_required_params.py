"""Config-content regression guard for Fix-R37A-1: none of the 9
disease_target_score_tools.json tools should require "pageSize", since it
always has a working `"default": 100` that DiseaseTargetScoreTool.run()
already applies via arguments.get("pageSize", 100).
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_configs():
    return json.loads((_DATA_DIR / "disease_target_score_tools.json").read_text())


def test_no_tool_requires_page_size():
    for cfg in _tool_configs():
        required = cfg["parameter"]["required"]
        assert "pageSize" not in required, cfg["name"]


def test_efo_id_still_required_everywhere():
    for cfg in _tool_configs():
        required = cfg["parameter"]["required"]
        assert "efoId" in required, cfg["name"]


def test_generic_tool_still_requires_datasource_id():
    cfg = next(c for c in _tool_configs() if c["name"] == "disease_target_score")
    assert cfg["parameter"]["required"] == ["efoId", "datasourceId"]


def test_datasource_specific_tools_have_no_datasource_id_param():
    for cfg in _tool_configs():
        if cfg["name"] == "disease_target_score":
            continue
        assert "datasourceId" not in cfg["parameter"]["properties"], cfg["name"]
        assert cfg["parameter"]["required"] == ["efoId"], cfg["name"]
