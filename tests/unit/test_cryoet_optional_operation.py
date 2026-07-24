"""Regression guard for Fix-R39A-1: all 7 CryoET_* tools
(list_datasets, get_dataset, list_runs, list_tomograms, list_annotations,
list_tiltseries, list_depositions) wrongly required "operation" even
though each tool's operation property is a single-value enum matching
its own "default" -- confirmed live, e.g.
CryoET_list_datasets({"organism_name": "Homo sapiens", "limit": 3})
previously failed outright with a schema validation error.

This one needed a two-part fix (same class as round 38's CELLxGENE
Census fix): removing "operation" from required alone was not enough,
because CryoETTool.run()'s existing Python fallback was
arguments.get("operation", "") -- an empty string matching none of its
own if/elif dispatch branches. Fixed by switching to
self.get_schema_const_operation(), the established codebase helper for
resolving a tool's own single enum/const operation value.

The genuinely-required fields on 4 of these tools -- dataset_id (no
default; CryoET_get_dataset/list_runs) and run_id (no default;
CryoET_list_tomograms/list_annotations) -- are unaffected and still
required.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.cryoet_tool import CryoETTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _configs():
    return json.loads((_DATA_DIR / "cryoet_tools.json").read_text())


def _tool_config(name):
    for cfg in _configs():
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in cryoet_tools.json")


@pytest.mark.parametrize(
    "name,expected_required",
    [
        ("CryoET_list_datasets", []),
        ("CryoET_get_dataset", ["dataset_id"]),
        ("CryoET_list_runs", ["dataset_id"]),
        ("CryoET_list_tomograms", ["run_id"]),
        ("CryoET_list_annotations", ["run_id"]),
        ("CryoET_list_tiltseries", []),
        ("CryoET_list_depositions", []),
    ],
)
def test_operation_no_longer_required(name, expected_required):
    cfg = _tool_config(name)
    assert cfg["parameter"]["required"] == expected_required


def test_operation_omitted_passes_schema_validation():
    cfg = _tool_config("CryoET_list_datasets")
    tool = CryoETTool(cfg)
    assert tool.validate_parameters({"organism_name": "Homo sapiens"}) is None


def test_dataset_id_still_rejected_when_missing():
    cfg = _tool_config("CryoET_get_dataset")
    tool = CryoETTool(cfg)
    error = tool.validate_parameters({})
    assert error is not None
    assert "dataset_id" in str(error)


@pytest.mark.parametrize(
    "name,expected_method,args",
    [
        ("CryoET_list_datasets", "_list_datasets", {}),
        ("CryoET_get_dataset", "_get_dataset", {"dataset_id": 10463}),
        ("CryoET_list_runs", "_list_runs", {"dataset_id": 10463}),
        ("CryoET_list_tomograms", "_list_tomograms", {"run_id": 3430}),
        ("CryoET_list_annotations", "_list_annotations", {"run_id": 3430}),
        ("CryoET_list_tiltseries", "_list_tiltseries", {}),
        ("CryoET_list_depositions", "_list_depositions", {}),
    ],
)
def test_omitted_operation_dispatches_to_the_correct_method(
    name, expected_method, args
):
    cfg = _tool_config(name)
    tool = CryoETTool(cfg)

    with patch.object(
        tool, expected_method, return_value={"status": "success", "data": {}}
    ) as mock_method:
        tool.run(args)

    assert mock_method.called
