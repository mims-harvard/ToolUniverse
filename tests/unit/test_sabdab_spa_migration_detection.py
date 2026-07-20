"""Regression guard for Fix-R17D-2 and Fix-R17D-3: SAbDab migrated to a new
frontend ("SAbDab2", a React SPA), and its old download/summary URLs now
return an HTTP-200 SPA HTML shell instead of the real PDB/TSV data
(confirmed live: the new domain's /api/pdb/{id}/ route 307-redirects to an
internal-only "sabdab-backend:8000" hostname, not publicly resolvable).
Before this fix, SAbDab_get_structure reported the HTML as a successful PDB
download, and SAbDab_get_structure_summary blamed the HTML on the
structure "may not be an antibody complex" -- both misleading. Both now
detect the SPA shell and report the real, upstream cause honestly.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit

SPA_HTML = (
    '<!doctype html>\n<html lang="en"><head><title>SAbDab2</title></head>'
    "<body><div id=\"root\"></div></body></html>"
)


class _FakeResponse:
    def __init__(self, text, status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        pass


def _tool():
    return SAbDabTool({"name": "SAbDab_get_structure"})


def test_get_structure_detects_spa_html(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        "tooluniverse.sabdab_tool.requests.get",
        lambda *a, **k: _FakeResponse(SPA_HTML),
    )

    result = tool._get_structure({"pdb_id": "5jxe"})

    assert result["status"] == "error"
    assert "non-PDB content" in result["error"]


def test_get_structure_still_parses_real_pdb_content(monkeypatch):
    tool = _tool()
    real_pdb = "REMARK   5 PAIRED_HL=A_B\nATOM      1  N   ALA A   1\n"
    monkeypatch.setattr(
        "tooluniverse.sabdab_tool.requests.get",
        lambda *a, **k: _FakeResponse(real_pdb),
    )

    result = tool._get_structure({"pdb_id": "5jxe"})

    assert result["status"] == "success"
    assert result["data"]["pdb_id"] == "5jxe"


def test_get_structure_summary_detects_spa_html(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        "tooluniverse.sabdab_tool.requests.get",
        lambda *a, **k: _FakeResponse(SPA_HTML, headers={"Content-Type": "text/html"}),
    )

    result = tool._get_structure_summary({"pdb_id": "5jxe"})

    assert result["status"] == "error"
    assert "migrated" in result["error"]


def test_get_structure_summary_non_html_non_tabular_keeps_original_message(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        "tooluniverse.sabdab_tool.requests.get",
        lambda *a, **k: _FakeResponse("not tabular and not html either"),
    )

    result = tool._get_structure_summary({"pdb_id": "5jxe"})

    assert result["status"] == "error"
    assert "may not be an antibody complex" in result["error"]
