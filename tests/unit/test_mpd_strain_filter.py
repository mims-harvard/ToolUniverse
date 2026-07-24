"""Regression guard for Fix-R42A-1: MPD_get_phenotype_data silently ignored
its own "strain" parameter -- confirmed live, every call returned the exact
same generic ENCODE experiment list regardless of what strain was passed.

The tool's own JSON config already documented an intended fix
(fields.endpoint templated `{strain}` into ENCODE's
`biosample_ontology.term_name` filter), but mpd_tool.py's run() never used
that template at all -- it hardcoded a different URL with no strain filter.
Confirmed live that the documented template itself was also broken:
biosample_ontology.term_name is a tissue/cell-type ontology field, not a
strain field, so it always returns zero results for real mouse strain names.
ENCODE's free-text `searchTerm` parameter, by contrast, was confirmed live to
surface strain-relevant experiments (292 hits for "C57BL/6J", 3 for
"BALB/c", correctly 0 for a strain ENCODE has no data on).

Fixed by querying with searchTerm=<strain> and being explicit in the
response that phenotype_category isn't applied (ENCODE has no such concept)
and that this is not curated MPD phenotype data.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.mpd_tool import MPDRESTTool

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config():
    configs = json.loads((_DATA_DIR / "mpd_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == "MPD_get_phenotype_data":
            return cfg
    raise AssertionError("MPD_get_phenotype_data not found in mpd_tools.json")


def test_strain_not_required():
    cfg = _tool_config()
    assert cfg["parameter"]["required"] == []


def test_run_uses_search_term_not_biosample_ontology():
    cfg = _tool_config()
    tool = MPDRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"total": 292, "@graph": []}

    with patch.object(tool.session, "get", return_value=resp) as mock_get:
        result = tool.run({"strain": "C57BL/6J", "limit": 3})
        called_url = mock_get.call_args.args[0]

    assert result["status"] == "success"
    assert "searchTerm=C57BL" in called_url
    assert "biosample_ontology.term_name" not in called_url


def test_run_handles_strain_with_slash():
    cfg = _tool_config()
    tool = MPDRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"total": 3, "@graph": []}

    with patch.object(tool.session, "get", return_value=resp) as mock_get:
        result = tool.run({"strain": "BALB/c", "limit": 2})
        called_url = mock_get.call_args.args[0]

    # quote()'s default safe="/" leaves the slash unescaped -- confirmed live
    # this is exactly what ENCODE expects (searchTerm=BALB/c and
    # searchTerm=C57BL/6J both returned correct, strain-relevant results).
    assert "searchTerm=BALB/c" in called_url
    assert result["status"] == "success"


def test_run_defaults_strain_when_omitted():
    cfg = _tool_config()
    tool = MPDRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"total": 292, "@graph": []}

    with patch.object(tool.session, "get", return_value=resp):
        result = tool.run({"limit": 2})

    assert result["query_info"]["strain"] == "C57BL/6J"


def test_response_discloses_data_source_limitation():
    cfg = _tool_config()
    tool = MPDRESTTool(cfg)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"total": 0, "@graph": []}

    with patch.object(tool.session, "get", return_value=resp):
        result = tool.run({"strain": "DBA/2J"})

    note = result["query_info"]["note"]
    assert "phenotype_category" in note
    assert "not applied" in note
