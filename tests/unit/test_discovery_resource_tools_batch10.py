"""Unit tests for discovery-round batch 10 (Open Genes). Network mocked."""

from unittest.mock import MagicMock, patch

from tooluniverse.open_genes_tool import OpenGenesGeneTool, OpenGenesSearchTool


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _cfg(name, typ):
    return {"name": name, "type": typ, "parameter": {"type": "object", "properties": {}}}


_GENE = {
    "symbol": "FOXO3", "name": "forkhead box O3", "ncbiId": 2309, "uniprot": "FOXO3_HUMAN",
    "ensembl": "ENSG00000118689", "expressionChange": 1,
    "confidenceLevel": {"id": 1, "name": "highest"},
    "agingMechanisms": [{"id": 1, "name": "transcriptional alterations"},
                        {"id": 2, "name": "stem cell exhaustion"}],
    "functionalClusters": [{"id": 1, "name": "insulin sensitivity"}],
    "diseaseCategories": [{"id": 1, "name": "cancer"}],
    "proteinDescriptionOpenGenes": "A transcription factor...",
    "researches": {"increaseLifespan": [1, 2, 3], "geneAssociatedWithLongevityEffects": list(range(58)),
                   "geneAssociatedWithProgeriaSyndromes": []},
}


def test_get_gene_requires_symbol():
    out = OpenGenesGeneTool(_cfg("OpenGenes_get_gene", "OpenGenesGeneTool")).run({})
    assert out["status"] == "error"
    assert "symbol" in out["error"]


def test_get_gene_curates_mechanisms_and_evidence():
    with patch("tooluniverse.open_genes_tool.requests.get", return_value=_resp(200, _GENE)):
        out = OpenGenesGeneTool(_cfg("OpenGenes_get_gene", "OpenGenesGeneTool")).run({"symbol": "FOXO3"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["symbol"] == "FOXO3"
    assert d["aging_mechanisms"] == ["transcriptional alterations", "stem cell exhaustion"]
    assert d["functional_clusters"] == ["insulin sensitivity"]
    assert d["confidence_level"] == "highest"
    # researches lists collapsed to counts
    assert d["evidence_counts"]["geneAssociatedWithLongevityEffects"] == 58
    assert d["evidence_counts"]["increaseLifespan"] == 3
    assert d["evidence_counts"]["geneAssociatedWithProgeriaSyndromes"] == 0


def test_get_gene_unknown_symbol_returns_empty_success():
    # Open Genes returns a non-gene-object (string error page) for unknown symbols.
    with patch("tooluniverse.open_genes_tool.requests.get", return_value=_resp(200, "Page not found")):
        out = OpenGenesGeneTool(_cfg("OpenGenes_get_gene", "OpenGenesGeneTool")).run({"symbol": "NOTAGENE"})
    assert out["status"] == "success"
    assert out["data"] == {}
    assert "not in Open Genes" in out["metadata"]["note"]


def test_search_curates_and_reports_total():
    body = {"options": {"total": 2405}, "items": [
        {"symbol": "GHR", "name": "growth hormone receptor",
         "agingMechanisms": [{"name": "INS/IGF-1 pathway dysregulation"}],
         "confidenceLevel": {"name": "highest"}}]}
    with patch("tooluniverse.open_genes_tool.requests.get", return_value=_resp(200, body)):
        out = OpenGenesSearchTool(_cfg("OpenGenes_search_genes", "OpenGenesSearchTool")).run({"limit": 5})
    assert out["status"] == "success"
    assert out["metadata"]["total_aging_genes"] == 2405
    assert out["data"][0]["symbol"] == "GHR"
    assert out["data"][0]["aging_mechanisms"] == ["INS/IGF-1 pathway dysregulation"]


def test_search_clamps_pagination():
    captured = {}

    def fake_get(url, params=None, **kw):
        captured["params"] = params
        return _resp(200, {"options": {}, "items": []})

    with patch("tooluniverse.open_genes_tool.requests.get", side_effect=fake_get):
        OpenGenesSearchTool(_cfg("OpenGenes_search_genes", "OpenGenesSearchTool")).run({"limit": 9999, "page": 0})
    assert captured["params"]["pageSize"] == 100  # clamped to max
    assert captured["params"]["page"] == 1  # clamped to min
