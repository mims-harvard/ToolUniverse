from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import vsd_tool

pytestmark = pytest.mark.unit


SOURCE_TOOL_NAMES = (
    "VSDDiscoverSources",
    "VSDWHOHypertensionIndicator",
    "VSDCDCPlacesCoronaryHeartDisease",
    "VSDOpenFDALabelBySetId",
    "VSDEnsemblServiceStatus",
)
ADMIN_TOOL_NAMES = (
    "VSDRegisterSource",
    "VSDListSources",
    "VSDQuerySource",
    "VSDRemoveSource",
)


def _loaded_vsd() -> ToolUniverse:
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(
        include_tools=[*SOURCE_TOOL_NAMES, *ADMIN_TOOL_NAMES], quiet=True
    )
    return tooluniverse


def test_default_surface_contains_only_read_only_source_specific_tools():
    """Mutable administration and generic proxy tools are not agent-facing."""
    tooluniverse = _loaded_vsd()
    try:
        loaded = {tool["name"] for tool in tooluniverse.all_tools}
        assert loaded == set(SOURCE_TOOL_NAMES)
        assert loaded.isdisjoint(ADMIN_TOOL_NAMES)

        for name in SOURCE_TOOL_NAMES:
            config = tooluniverse.all_tool_dict[name]
            assert config["cacheable"] is True
            assert config["mcp_annotations"] == {
                "readOnlyHint": True,
                "destructiveHint": False,
            }
            assert config["return_schema"] != {}
    finally:
        tooluniverse.close()


def test_source_contracts_are_fixed_and_typed():
    """Reviewed providers expose constrained inputs and normalized outputs."""
    tooluniverse = _loaded_vsd()
    try:
        cdc = tooluniverse.all_tool_dict["VSDCDCPlacesCoronaryHeartDisease"]
        assert cdc["parameter"]["required"] == ["state_abbr", "county_name"]
        assert cdc["parameter"]["properties"]["limit"]["maximum"] == 500
        assert (
            cdc["return_schema"]["properties"]["tracts"]["items"][
                "additionalProperties"
            ]
            is False
        )

        fda = tooluniverse.all_tool_dict["VSDOpenFDALabelBySetId"]
        assert fda["parameter"]["required"] == ["set_id"]
        assert fda["parameter"]["properties"]["set_id"]["format"] == "uuid"

        discovery = tooluniverse.run_one_function(
            {"name": "VSDDiscoverSources", "arguments": {"query": "CDC"}}
        )
        source = discovery["data"]["sources"][0]
        assert source["tool_name"] == "VSDCDCPlacesCoronaryHeartDisease"
        assert source["review_scope"].endswith("not scientific endorsement.")
    finally:
        tooluniverse.close()


def test_tooluniverse_executes_typed_who_adapter(monkeypatch):
    """The documented ToolUniverse call path returns normalized WHO data."""
    monkeypatch.setattr(
        vsd_tool,
        "_safe_get_json",
        lambda endpoint, params: (
            {
                "value": [
                    {
                        "IndicatorCode": "NCD_HYP_DIAGNOSIS_C",
                        "IndicatorName": "Hypertension diagnosis coverage (%)",
                        "Language": "EN",
                    }
                ]
            },
            {
                "url": endpoint,
                "status_code": 200,
                "content_type": "application/json",
                "response_bytes": 100,
                "peer_ip": "93.184.216.34",
                "redirects": 0,
            },
        ),
    )
    tooluniverse = ToolUniverse()
    tooluniverse.load_tools(include_tools=["VSDWHOHypertensionIndicator"], quiet=True)
    try:
        result = tooluniverse.run_one_function(
            {"name": "VSDWHOHypertensionIndicator", "arguments": {}}
        )
        assert result["data"]["indicator"]["indicator_code"] == ("NCD_HYP_DIAGNOSIS_C")
        assert result["data"]["provenance"]["provider"] == (
            "WHO Global Health Observatory"
        )
    finally:
        tooluniverse.close()


def test_generated_wrappers_and_metadata_match_source_surface():
    """Generated SDK wrappers expose source contracts and omit admin commands."""
    tools_path = Path(__file__).parents[2] / "src" / "tooluniverse" / "tools"
    wrapper = ast.parse(
        (tools_path / "VSDCDCPlacesCoronaryHeartDisease.py").read_text(encoding="utf-8")
    )
    function = next(
        node
        for node in wrapper.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "VSDCDCPlacesCoronaryHeartDisease"
    )
    positional = [argument.arg for argument in function.args.args]
    assert positional[:3] == ["state_abbr", "county_name", "limit"]

    metadata = json.loads(
        (tools_path / ".tool_metadata.json").read_text(encoding="utf-8")
    )
    for name in SOURCE_TOOL_NAMES:
        assert re.fullmatch(r"[0-9a-f]{32}", metadata[name])
    for name in ADMIN_TOOL_NAMES:
        assert name not in metadata
