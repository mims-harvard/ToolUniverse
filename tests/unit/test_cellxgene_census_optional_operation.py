"""Regression guard for Fix-R38A-1: CELLxGENE_get_cell_metadata,
CELLxGENE_get_gene_metadata, CELLxGENE_get_expression_data,
CELLxGENE_get_presence_matrix, CELLxGENE_get_embeddings, and
CELLxGENE_download_h5ad all wrongly required "operation" even though
each tool's `operation` property is a single-value enum matching its own
"default" (each tool instance only ever has one valid operation, e.g.
CELLxGENE_get_gene_metadata always defaults/enums to "get_var_metadata"),
and CELLxGENECensusTool.run() already reads it via
arguments.get("operation", "get_metadata") with the schema default
available as a fallback. A caller who reasonably omitted a param that
can only ever have one value hit a hard schema validation error --
confirmed live via BaseTool.validate_parameters() (the package itself,
cellxgene_census/tiledbsoma, isn't installed in this environment, but
schema validation runs before the tool's run() ever imports it).

The genuinely-required fields on two of these tools -- obs_value_filter
(no default; the Census has 50M+ cells and an unfiltered query times
out) and dataset_id (no default) -- are unaffected and still required.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The tool imports these optional heavy packages at call time; stub them so
# CELLxGENECensusTool.run() reaches its own dispatch logic under test.
sys.modules.setdefault("cellxgene_census", MagicMock())
sys.modules.setdefault("tiledbsoma", MagicMock())

from tooluniverse.cellxgene_census_tool import CELLxGENECensusTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _configs():
    return json.loads((_DATA_DIR / "cellxgene_census_tools.json").read_text())


def _tool_config(name):
    for cfg in _configs():
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in cellxgene_census_tools.json")


@pytest.mark.parametrize(
    "name",
    [
        "CELLxGENE_get_gene_metadata",
        "CELLxGENE_get_expression_data",
        "CELLxGENE_get_presence_matrix",
        "CELLxGENE_get_embeddings",
    ],
)
def test_operation_only_tools_have_no_required_params(name):
    cfg = _tool_config(name)
    assert cfg["parameter"]["required"] == []


def test_get_cell_metadata_requires_only_obs_value_filter():
    cfg = _tool_config("CELLxGENE_get_cell_metadata")
    assert cfg["parameter"]["required"] == ["obs_value_filter"]


def test_download_h5ad_requires_only_dataset_id():
    cfg = _tool_config("CELLxGENE_download_h5ad")
    assert cfg["parameter"]["required"] == ["dataset_id"]


def test_operation_omitted_passes_schema_validation():
    cfg = _tool_config("CELLxGENE_get_gene_metadata")
    tool = CELLxGENECensusTool(cfg)
    assert tool.validate_parameters({"organism": "Homo sapiens"}) is None


def test_obs_value_filter_alone_passes_cell_metadata_validation():
    cfg = _tool_config("CELLxGENE_get_cell_metadata")
    tool = CELLxGENECensusTool(cfg)
    args = {"obs_value_filter": 'tissue_general == "lung"'}
    assert tool.validate_parameters(args) is None


def test_cell_metadata_still_rejects_missing_obs_value_filter():
    cfg = _tool_config("CELLxGENE_get_cell_metadata")
    tool = CELLxGENECensusTool(cfg)
    error = tool.validate_parameters({})
    assert error is not None
    assert "obs_value_filter" in str(error)


def test_download_h5ad_still_rejects_missing_dataset_id():
    cfg = _tool_config("CELLxGENE_download_h5ad")
    tool = CELLxGENECensusTool(cfg)
    error = tool.validate_parameters({})
    assert error is not None
    assert "dataset_id" in str(error)


# Fix-R38A-1 (part 2): making "operation" schema-optional is not enough on
# its own -- run() previously fell back to a bare "get_metadata" literal
# that matches none of its own if/elif dispatch branches, so an omitted
# operation would have silently mis-routed to the "Unknown operation"
# error path even after the schema fix. The correct fallback (matching the
# pattern already used by ~27 other tool classes in this codebase) is
# self.get_schema_const_operation(), which resolves each tool's own single
# enum value from its config.
@pytest.mark.parametrize(
    "name,expected_method",
    [
        ("CELLxGENE_get_cell_metadata", "_get_obs_metadata"),
        ("CELLxGENE_get_gene_metadata", "_get_var_metadata"),
        ("CELLxGENE_get_expression_data", "_get_anndata"),
        ("CELLxGENE_get_presence_matrix", "_get_presence_matrix"),
        ("CELLxGENE_get_embeddings", "_get_embeddings"),
        ("CELLxGENE_download_h5ad", "_download_h5ad"),
    ],
)
def test_omitted_operation_dispatches_to_the_correct_method(name, expected_method):
    cfg = _tool_config(name)
    tool = CELLxGENECensusTool(cfg)

    with patch.object(
        tool, expected_method, return_value={"status": "success", "data": []}
    ) as mock_method:
        # A superset covering every tool's other required field is safe
        # here since the dispatched method itself is mocked out; the only
        # thing under test is dispatch routing when "operation" is absent.
        tool.run({"obs_value_filter": "x", "dataset_id": "y"})

    assert mock_method.called
