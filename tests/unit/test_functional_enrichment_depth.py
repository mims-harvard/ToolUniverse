"""Depth tests for functional-enrichment coverage tools.

Covers a new tool that reuses an existing tool class (no new registration):

* ``Enrichr_gene_to_genesets`` (EnrichrExtTool, operation
  ``gene_to_genesets``) — reverse gene-to-geneset membership. Given ONE gene
  symbol, it queries Enrichr's ``genemap`` endpoint and returns every
  term/gene-set name containing that gene, broken down across all ~243
  Enrichr libraries. This is the inverse of forward enrichment.

All HTTP is mocked so the suite is offline/deterministic; live verification
is done separately via the CLI.
"""

import json
import os

import pytest

from tooluniverse.enrichr_ext_tool import EnrichrExtTool

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_tool_config(filename, tool_name):
    with open(os.path.join(DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    matches = [c for c in configs if c.get("name") == tool_name]
    assert matches, f"{tool_name} not found in {filename}"
    return matches[0]


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, raise_json=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("No JSON object could be decoded")
        return self._payload

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            import requests

            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


# Sample genemap payload mirroring the real Enrichr /genemap?json=true shape:
# {"gene": {library_name: [term_name, ...], ...}, "descriptions": [...]}
_GENEMAP_PAYLOAD = {
    "gene": {
        "KEGG_2021_Human": [
            "Acute myeloid leukemia",
            "JAK-STAT signaling pathway",
            "Th17 cell differentiation",
        ],
        "GO_Biological_Process_2023": [
            "positive regulation of transcription (GO:0045944)",
            "cellular response to cytokine stimulus (GO:0071345)",
        ],
        "GeneSigDB": ["18081427-TableS8"],
        "_not_a_list": "should be skipped",
    },
    "descriptions": [
        {"name": "KEGG_2021_Human", "description": "KEGG pathway library."},
    ],
    "categories": [{"name": "Pathways"}],
}


def _make_tool():
    cfg = _load_tool_config("enrichr_ext_tools.json", "Enrichr_gene_to_genesets")
    return EnrichrExtTool(cfg)


@pytest.mark.unit
def test_gene_to_genesets_parses_membership(monkeypatch):
    """Parse genemap into per-library term lists with correct counts."""
    tool = _make_tool()
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params or {}
        return _FakeResponse(200, _GENEMAP_PAYLOAD)

    monkeypatch.setattr("tooluniverse.enrichr_ext_tool.requests.get", fake_get)

    result = tool.run({"gene": "STAT3"})

    assert result["status"] == "success"
    assert captured["url"].endswith("/genemap")
    assert captured["params"]["gene"] == "STAT3"
    assert captured["params"]["json"] == "true"
    # setup not requested by default
    assert "setup" not in captured["params"]

    data = result["data"]
    assert data["gene"] == "STAT3"
    # 3 list-valued libraries; the non-list "_not_a_list" entry is skipped
    assert data["num_libraries"] == 3
    assert data["total_gene_sets"] == 3 + 2 + 1
    assert "KEGG_2021_Human" in data["libraries"]
    assert data["libraries"]["GeneSigDB"] == ["18081427-TableS8"]
    # metadata not included unless requested
    assert "descriptions" not in data
    assert "categories" not in data


@pytest.mark.unit
def test_gene_to_genesets_caps_terms_and_includes_metadata(monkeypatch):
    """max_terms_per_library caps lists; include_metadata forwards setup=true."""
    tool = _make_tool()
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["params"] = params or {}
        return _FakeResponse(200, _GENEMAP_PAYLOAD)

    monkeypatch.setattr("tooluniverse.enrichr_ext_tool.requests.get", fake_get)

    result = tool.run(
        {"gene": "STAT3", "include_metadata": True, "max_terms_per_library": 1}
    )

    assert result["status"] == "success"
    # setup=true forwarded when metadata requested
    assert captured["params"].get("setup") == "true"

    data = result["data"]
    # each library capped at 1 term, but total_gene_sets reflects full counts
    assert data["libraries"]["KEGG_2021_Human"] == ["Acute myeloid leukemia"]
    assert all(len(v) <= 1 for v in data["libraries"].values())
    assert data["total_gene_sets"] == 6
    # metadata present
    assert data["descriptions"] == _GENEMAP_PAYLOAD["descriptions"]
    assert data["categories"] == _GENEMAP_PAYLOAD["categories"]


@pytest.mark.unit
def test_gene_to_genesets_missing_gene_returns_error():
    """Blank or absent gene yields a status=error result, never raises."""
    tool = _make_tool()

    result = tool.run({"gene": "   "})
    assert result["status"] == "error"
    assert "gene is required" in result["error"]

    result2 = tool.run({})
    assert result2["status"] == "error"
    assert "gene is required" in result2["error"]


@pytest.mark.unit
def test_gene_to_genesets_http_error_returns_error(monkeypatch):
    """Network failure yields a status=error result, never raises."""
    tool = _make_tool()

    def fake_get(url, params=None, timeout=None):
        import requests

        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr("tooluniverse.enrichr_ext_tool.requests.get", fake_get)

    result = tool.run({"gene": "STAT3"})
    assert result["status"] == "error"
    assert "Request failed" in result["error"]


@pytest.mark.unit
def test_gene_to_genesets_malformed_payload_returns_error(monkeypatch):
    """A payload missing the gene dict yields a status=error result."""
    tool = _make_tool()

    # Response with no "gene" dict (e.g., unexpected shape)
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(200, {"unexpected": True})

    monkeypatch.setattr("tooluniverse.enrichr_ext_tool.requests.get", fake_get)

    result = tool.run({"gene": "STAT3"})
    assert result["status"] == "error"
    assert "No gene-set membership" in result["error"]


@pytest.mark.unit
def test_gene_to_genesets_bad_json_returns_error(monkeypatch):
    """Non-JSON body yields a status=error result, never raises."""
    tool = _make_tool()

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(200, raise_json=True)

    monkeypatch.setattr("tooluniverse.enrichr_ext_tool.requests.get", fake_get)

    result = tool.run({"gene": "STAT3"})
    assert result["status"] == "error"
    assert "parse" in result["error"].lower()
