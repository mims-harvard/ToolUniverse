"""Regression guard for Fix-R39A-3: both hca_search_projects and
hca_get_file_manifest wrongly required "action" even though each tool's
action property is a single-value enum matching its own "default" --
confirmed live, e.g. hca_get_file_manifest({"project_id": "..."})
previously failed outright with a schema validation error.

Two-part fix, same class as round 38's CELLxGENE Census fix and this
round's CryoET/FourDN fixes: removing "action" from required alone was
not enough. Unlike those other tools (which use the "operation" property
name and BaseTool.get_schema_const_operation()), HCATool.run() previously
had NO fallback at all for "action" (arguments.get("action")), so an
omitted action fell straight through to "Unknown action: None". Since
get_schema_const_operation() is hardcoded to the "operation" property
name, this tool needed an inline equivalent lookup against its own
"action" property's schema default instead.

project_id (get_file_manifest) has no default and is unaffected -- still
required.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.hca_tool import HCATool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _configs():
    return json.loads((_DATA_DIR / "hca_tools.json").read_text())


def _tool_config(name):
    for cfg in _configs():
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in hca_tools.json")


def test_search_projects_has_no_required_params():
    cfg = _tool_config("hca_search_projects")
    assert cfg["parameter"]["required"] == []


def test_get_file_manifest_requires_only_project_id():
    cfg = _tool_config("hca_get_file_manifest")
    assert cfg["parameter"]["required"] == ["project_id"]


def test_omitted_action_dispatches_to_search_projects():
    cfg = _tool_config("hca_search_projects")
    tool = HCATool(cfg)

    with patch.object(
        tool, "search_projects", return_value={"total_hits": 0, "projects": []}
    ) as mock_method:
        tool.run({"organ": "heart"})

    assert mock_method.called


def test_omitted_action_dispatches_to_get_file_manifest():
    cfg = _tool_config("hca_get_file_manifest")
    tool = HCATool(cfg)

    with patch.object(
        tool, "get_file_manifest", return_value={"total_files": 0, "files": []}
    ) as mock_method:
        tool.run({"project_id": "abc123"})

    assert mock_method.called


def test_get_file_manifest_still_requires_project_id():
    cfg = _tool_config("hca_get_file_manifest")
    tool = HCATool(cfg)

    with pytest.raises(ValueError, match="project_id"):
        tool.run({})
