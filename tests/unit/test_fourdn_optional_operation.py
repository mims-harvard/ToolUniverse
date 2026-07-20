"""Regression guard for Fix-R39A-2: all 4 FourDN_* tools (search_data,
get_file_metadata, get_experiment_metadata, get_download_url) wrongly
required "operation" even though each tool's operation property is a
single-value enum matching its own "default" -- confirmed live, e.g.
FourDN_get_file_metadata({"file_accession": "4DNFIIA7E3HL"}) previously
failed outright with a schema validation error.

Two-part fix, same class as round 38's CELLxGENE Census fix and this
round's CryoET fix: removing "operation" from required alone was not
enough, because FourDNTool.run()'s existing Python fallback was
arguments.get("operation", "search") -- a literal only coincidentally
correct for FourDN_search_data itself. The other 3 tools would have
silently mis-routed to a search instead of their own operation. Fixed by
switching to self.get_schema_const_operation().

file_accession (get_file_metadata, get_download_url) and
experiment_accession (get_experiment_metadata) have no defaults and are
unaffected -- still required.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.fourdn_tool import FourDNTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _configs():
    return json.loads((_DATA_DIR / "fourdn_tools.json").read_text())


def _tool_config(name):
    for cfg in _configs():
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in fourdn_tools.json")


@pytest.mark.parametrize(
    "name,expected_required",
    [
        ("FourDN_search_data", []),
        ("FourDN_get_file_metadata", ["file_accession"]),
        ("FourDN_get_experiment_metadata", ["experiment_accession"]),
        ("FourDN_get_download_url", ["file_accession"]),
    ],
)
def test_operation_no_longer_required(name, expected_required):
    cfg = _tool_config(name)
    assert cfg["parameter"]["required"] == expected_required


def test_operation_omitted_passes_schema_validation():
    cfg = _tool_config("FourDN_search_data")
    tool = FourDNTool(cfg)
    assert tool.validate_parameters({"query": "Hi-C"}) is None


def test_file_accession_still_rejected_when_missing():
    cfg = _tool_config("FourDN_get_file_metadata")
    tool = FourDNTool(cfg)
    error = tool.validate_parameters({})
    assert error is not None
    assert "file_accession" in str(error)


@pytest.mark.parametrize(
    "name,expected_method,args",
    [
        ("FourDN_search_data", "_search", {}),
        ("FourDN_get_file_metadata", "_get_file_metadata", {"file_accession": "x"}),
        (
            "FourDN_get_experiment_metadata",
            "_get_experiment_metadata",
            {"experiment_accession": "x"},
        ),
        ("FourDN_get_download_url", "_download_file_url", {"file_accession": "x"}),
    ],
)
def test_omitted_operation_dispatches_to_the_correct_method(
    name, expected_method, args
):
    cfg = _tool_config(name)
    tool = FourDNTool(cfg)

    with patch.object(
        tool, expected_method, return_value={"status": "success", "data": {}}
    ) as mock_method:
        tool.run(args)

    assert mock_method.called
