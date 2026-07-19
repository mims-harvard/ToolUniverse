"""Regression guard for Fix-R27E-1: jaspar_search_matrices silently
ignored unrecognized query parameters instead of rejecting them.
Confirmed live: `{"tf_name": "SP1"}` (a very natural guess, matching the
naming convention of the sibling tool UniBind_search_datasets) returned
`count: 5935` -- essentially JASPAR's entire unfiltered matrix database,
with zero indication the param was ignored -- while the documented
`{"name": "SP1"}` correctly returns 6 SP1 matrices. JASPARRESTTool
extends BaseTool, whose validate_parameters() already enforces
`additionalProperties: false` via jsonschema when the schema declares it;
the schema previously omitted that flag entirely. Fixed with a
config-only change (no Python code touched).
"""

import json
from pathlib import Path

import pytest

from tooluniverse.jaspar_tool import JASPARRESTTool

pytestmark = pytest.mark.unit

_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "tooluniverse"
    / "data"
    / "jaspar_tools.json"
)


def _load_tool_config():
    configs = json.loads(_CONFIG_PATH.read_text())
    for cfg in configs:
        if cfg["name"] == "jaspar_search_matrices":
            return cfg
    raise AssertionError("tool config not found")


def _tool():
    return JASPARRESTTool(_load_tool_config())


class TestAdditionalPropertiesEnforced:
    def test_schema_declares_additional_properties_false(self):
        cfg = _load_tool_config()
        assert cfg["parameter"]["additionalProperties"] is False

    def test_unrecognized_param_is_rejected(self):
        tool = _tool()
        error = tool.validate_parameters({"tf_name": "SP1"})
        assert error is not None
        assert "tf_name" in str(error)

    def test_documented_param_is_accepted(self):
        tool = _tool()
        error = tool.validate_parameters({"name": "SP1"})
        assert error is None

    def test_no_params_is_accepted(self):
        tool = _tool()
        error = tool.validate_parameters({})
        assert error is None
