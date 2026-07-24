"""Regression guard for Fix-R40A-1: ChEMBL_search_similar_molecules and
ChEMBL_search_similarity both wrongly required similarity_threshold/
max_results (resp. threshold) even though each has a working "default" --
confirmed live, e.g. ChEMBL_search_similarity({"smiles": "CCO"}) previously
failed outright with a schema validation error.

ChEMBL_search_similar_molecules needed only the schema fix (chem_tool.py's
_search_similar_molecules already reads its args via
arguments.get("similarity_threshold", 80) / arguments.get("max_results", 20)).

ChEMBL_search_similarity needed a two-part fix, a NEW sub-pattern (not the
operation/action routing field from rounds 38-39): its endpoint template
(/similarity/{smiles}/{threshold}.json) has a URL PATH placeholder, and
ChEMBLRESTTool._build_url() only substituted placeholders explicitly present
in the caller's args -- unlike BaseRESTTool's _build_url(), it had no
fallback to schema defaults for unfilled placeholders. Confirmed live: with
only the schema fix, the caller passed validation but the request went out
with a literal "{threshold}" left in the URL, producing a 404. Fixed by
adding the same schema-default-filling loop BaseRESTTool already has.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.chem_tool import ChEMBLRESTTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "chembl_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in chembl_tools.json")


def test_search_similar_molecules_requires_only_query():
    cfg = _tool_config("ChEMBL_search_similar_molecules")
    assert cfg["parameter"]["required"] == ["query"]


def test_search_similarity_requires_only_smiles():
    cfg = _tool_config("ChEMBL_search_similarity")
    assert cfg["parameter"]["required"] == ["smiles"]


def test_build_url_fills_missing_path_placeholder_from_schema_default():
    cfg = _tool_config("ChEMBL_search_similarity")
    tool = ChEMBLRESTTool(cfg)

    url = tool._build_url({"smiles": "CCO"})

    assert "{threshold}" not in url
    assert url.endswith("/similarity/CCO/80.json")


def test_build_url_still_honors_explicit_threshold():
    cfg = _tool_config("ChEMBL_search_similarity")
    tool = ChEMBLRESTTool(cfg)

    url = tool._build_url({"smiles": "CCO", "threshold": 95})

    assert url.endswith("/similarity/CCO/95.json")


def test_search_similarity_end_to_end_with_threshold_omitted():
    cfg = _tool_config("ChEMBL_search_similarity")
    tool = ChEMBLRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"molecules": []}
    resp.raise_for_status = MagicMock()

    with patch(
        "tooluniverse.chem_tool.request_with_retry", return_value=resp
    ) as mock_request:
        result = tool.run({"smiles": "CCO"})

    assert result["status"] == "success"
    called_url = mock_request.call_args.args[2]
    assert "{threshold}" not in called_url
    assert called_url.endswith("/similarity/CCO/80.json")
