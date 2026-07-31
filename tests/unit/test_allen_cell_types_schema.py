"""Regression guard for Feature-R14A-2: AllenCellTypes_search_specimens
silently ignored an unrecognized `gene` parameter (this tool has no
gene-expression filter -- it wraps electrophysiology/morphology specimen
search, not transcriptomics) and returned unrelated specimens as if the
request had been fully satisfied, with nothing indicating the key was
dropped. AllenCellTypesSpecimensTool is a BaseTool subclass whose run()
only ever reads species/structure/limit, so adding `additionalProperties:
false` is safe and makes the rejection explicit instead of silent.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.allen_cell_types_tool import AllenCellTypesSpecimensTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src/tooluniverse/data/allen_cell_types_tools.json"
)


def _tool_config():
    configs = json.loads(CONFIG_PATH.read_text())
    return next(c for c in configs if c["name"] == "AllenCellTypes_search_specimens")


def test_schema_rejects_additional_properties():
    config = _tool_config()
    assert config["parameter"]["additionalProperties"] is False


def test_unrecognized_gene_param_is_rejected_by_validation():
    config = _tool_config()
    tool = AllenCellTypesSpecimensTool(config)

    error = tool.validate_parameters(
        {"species": "Mus musculus", "gene": "Bdnf", "limit": 5}
    )

    assert error is not None


def test_declared_params_still_validate_cleanly():
    config = _tool_config()
    tool = AllenCellTypesSpecimensTool(config)

    error = tool.validate_parameters({"species": "Mus musculus", "limit": 5})

    assert error is None
