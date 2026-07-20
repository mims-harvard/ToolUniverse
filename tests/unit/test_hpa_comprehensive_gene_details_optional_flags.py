"""Regression guard for Fix-R33A-2: HPA_get_comprehensive_gene_details_by_
ensembl_id's schema marked include_images/include_antibodies/include_expression
as required, even though their descriptions promise "defaults to true" and the
Python run() already reads them via arguments.get(..., True). Any caller who
omitted them (the natural reading of "defaults to true") hit a hard schema
validation error before the tool's own default logic ever ran -- confirmed
live for a bare {"ensembl_id": ...} call.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config():
    configs = json.loads((_DATA_DIR / "hpa_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == "HPA_get_comprehensive_gene_details_by_ensembl_id":
            return cfg
    raise AssertionError("HPA_get_comprehensive_gene_details_by_ensembl_id not found")


def test_only_ensembl_id_is_required():
    cfg = _tool_config()
    assert cfg["parameter"]["required"] == ["ensembl_id"]


def test_optional_flags_carry_a_matching_default():
    cfg = _tool_config()
    props = cfg["parameter"]["properties"]
    for name in ("include_images", "include_antibodies", "include_expression"):
        assert props[name]["default"] is True
