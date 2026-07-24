"""Regression guard for Fix-R22A-1/2: SAbDab migrated to a React SPA
(sabdab.opig.stats.ox.ac.uk, "SAbDab2") that serves the same generic HTML
app shell for every route, including the old REST-style download/summary
endpoints this tool relies on. That HTML response is a plain 200 OK, so
neither tool previously distinguished it from real data:

- SAbDab_get_structure silently reported status:"success" with the HTML
  page's byte count/preview mislabeled as PDB structure content.
- SAbDab_get_structure_summary already had a "did not return tabular
  data" fallback, but its message misleadingly implied the structure just
  wasn't an antibody complex, even for the tool's own documented examples
  (confirmed live: 6w41, 3hfm both now fail this way).

Fixed by detecting HTML/non-PDB content in get_structure before claiming
success, and clarifying get_structure_summary's existing error message.
A full SAbDab2 API integration (its new antibody-centric data model,
different endpoint conventions) is a bigger-scope redesign, not attempted
here.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit

_HTML_SHELL = (
    '<!doctype html><html lang="en"><head><meta charset="UTF-8" />'
    "<title>SAbDab2</title></head><body><div id=\"root\"></div></body></html>"
)

_REAL_PDB_CONTENT = (
    "HEADER    TRANSFERASE                             21-NOV-02   1N8Z\n"
    "TITLE     CRYSTAL STRUCTURE OF EXTRACELLULAR DOMAIN OF HUMAN HER2\n"
    "REMARK   5 PAIRED_HL=A_B\n"
    "ATOM      1  N   ALA A   1      10.000  20.000  30.000  1.00  0.00           N\n"
)


def _tool():
    with open("src/tooluniverse/data/sabdab_tools.json") as f:
        cfg = json.load(f)[0]
    return SAbDabTool(cfg)


def _resp(status_code, text, content_type="text/html"):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.headers = {"Content-Type": content_type}
    r.raise_for_status = MagicMock()
    return r


class TestGetStructureHtmlDetection:
    def test_html_response_gives_clear_error_not_silent_success(self):
        tool = _tool()
        resp = _resp(200, _HTML_SHELL)

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_structure", "pdb_id": "1n8z"})

        assert result["status"] == "error"
        assert "non-PDB content" in result["error"]

    def test_real_pdb_content_still_succeeds(self):
        tool = _tool()
        resp = _resp(200, _REAL_PDB_CONTENT, content_type="text/plain")

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_structure", "pdb_id": "1n8z"})

        assert result["status"] == "success"
        assert result["data"]["pdb_id"] == "1n8z"
        assert "HEADER" in result["data"]["pdb_preview"]

    def test_404_still_reports_not_found(self):
        tool = _tool()
        resp = _resp(404, "")

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run({"operation": "get_structure", "pdb_id": "zzzz"})

        assert result["status"] == "error"
        assert "Structure not found" in result["error"]


class TestGetStructureSummaryErrorMessage:
    def test_html_response_error_does_not_blame_antigen_complex(self):
        """The message must no longer misleadingly suggest the structure
        just isn't an antibody complex, since this now fires even for the
        tool's own documented antibody examples."""
        tool = _tool()
        resp = _resp(200, _HTML_SHELL)

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run(
                {"operation": "get_structure_summary", "pdb_id": "6w41"}
            )

        assert result["status"] == "error"
        assert "may not be an antibody complex" not in result["error"]
        assert "migrated" in result["error"] or "non-tabular content" in result["error"]

    def test_real_tsv_still_parses_correctly(self):
        tool = _tool()
        tsv = (
            "pdb\tantigen_name\tantigen_type\tresolution\tmethod\n"
            "6w41\tSpike protein\tprotein\t2.50\tX-RAY DIFFRACTION\n"
        )
        resp = _resp(200, tsv, content_type="text/tab-separated-values")

        with patch("tooluniverse.sabdab_tool.requests.get", return_value=resp):
            result = tool.run(
                {"operation": "get_structure_summary", "pdb_id": "6w41"}
            )

        assert result["status"] == "success"
        assert result["data"]["antigen_name"] == "Spike protein"
        assert result["data"]["resolution"] == 2.5
