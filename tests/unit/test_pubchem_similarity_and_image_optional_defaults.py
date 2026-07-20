"""Regression guard for Fix-R41A-1: PubChem_search_compounds_by_similarity
and PubChem_get_compound_2D_image_by_CID both wrongly required
threshold/image_size even though each has a working "default" -- confirmed
live, e.g. PubChem_get_compound_2D_image_by_CID({"cid": 2244}) previously
failed outright with a schema validation error.

PubChem_search_compounds_by_similarity needed only the schema fix: its
Python code (line ~137, `if "threshold" in arguments`) already omits the
Threshold query param entirely when the caller doesn't supply it, and
PubChem's own fastsimilarity_2d endpoint defaults to exactly the same 90%
threshold documented in the schema -- confirmed live the omitted-threshold
and explicit-threshold=0.9 results are byte-identical.

PubChem_get_compound_2D_image_by_CID needed a two-part fix -- the SAME
sub-pattern discovered in round 40 for ChEMBL_search_similarity: its
endpoint template (/compound/cid/{cid}/PNG?image_size={image_size}) has a
URL path placeholder, and PubChemRESTTool._build_url() -- like
ChEMBLRESTTool, a hand-rolled BaseTool subclass, not a BaseRESTTool one --
previously raised ValueError for ANY placeholder missing from the caller's
args, with no fallback to the property's own schema default. Fixed by
checking for a schema default before raising.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pubchem_tool import PubChemRESTTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "pubchem_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in pubchem_tools.json")


def test_search_compounds_by_similarity_requires_only_smiles():
    cfg = _tool_config("PubChem_search_compounds_by_similarity")
    assert cfg["parameter"]["required"] == ["smiles"]


def test_get_compound_2d_image_requires_only_cid():
    cfg = _tool_config("PubChem_get_compound_2D_image_by_CID")
    assert cfg["parameter"]["required"] == ["cid"]


def test_build_url_fills_missing_image_size_from_schema_default():
    cfg = _tool_config("PubChem_get_compound_2D_image_by_CID")
    tool = PubChemRESTTool(cfg)

    url = tool._build_url({"cid": 2244})

    assert "{image_size}" not in url
    assert "image_size=200x200" in url


def test_build_url_still_honors_explicit_image_size():
    cfg = _tool_config("PubChem_get_compound_2D_image_by_CID")
    tool = PubChemRESTTool(cfg)

    url = tool._build_url({"cid": 2244, "image_size": "300x300"})

    assert "image_size=300x300" in url


def test_build_url_still_raises_for_a_placeholder_with_no_default():
    tool = PubChemRESTTool(
        {
            "name": "test_tool",
            "fields": {"endpoint": "/compound/cid/{cid}/PNG"},
            "parameter": {"type": "object", "properties": {}},
        }
    )

    with pytest.raises(ValueError, match="cid"):
        tool._build_url({})


def test_get_compound_2d_image_end_to_end_with_image_size_omitted():
    cfg = _tool_config("PubChem_get_compound_2D_image_by_CID")
    tool = PubChemRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes"

    with patch("tooluniverse.pubchem_tool.requests.get", return_value=resp):
        result = tool.run({"cid": 2244})

    assert result["status"] == "success"
    assert isinstance(result["data"]["image_base64"], str)


def test_search_similarity_threshold_omitted_matches_explicit_default():
    cfg = _tool_config("PubChem_search_compounds_by_similarity")
    tool = PubChemRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"IdentifierList": {"CID": [702]}}

    with patch(
        "tooluniverse.pubchem_tool.requests.get", return_value=resp
    ) as mock_get:
        omitted_result = tool.run({"smiles": "CCO", "max_results": 5})
        omitted_url = mock_get.call_args.args[0]

    with patch(
        "tooluniverse.pubchem_tool.requests.get", return_value=resp
    ) as mock_get:
        explicit_result = tool.run(
            {"smiles": "CCO", "threshold": 0.9, "max_results": 5}
        )
        explicit_url = mock_get.call_args.args[0]

    assert omitted_result["status"] == "success"
    assert explicit_result["status"] == "success"
    assert omitted_result == explicit_result
    assert "Threshold=90" in explicit_url
    assert "Threshold" not in omitted_url
