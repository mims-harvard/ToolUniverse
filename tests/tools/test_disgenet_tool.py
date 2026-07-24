"""
Unit tests for DisGeNET tool.

Covers the DisGeNET v1 contract: /{gda,vda}/summary query-parameter endpoints,
raw (non-Bearer) Authorization header, `payload` response parsing, and
disease-name input validation.
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock


def _summary(payload):
    """Build a mock DisGeNET v1 /summary response."""
    resp = MagicMock()
    resp.json.return_value = {"status": "OK", "payload": payload, "warnings": []}
    resp.raise_for_status = MagicMock()
    return resp


class TestDisGeNETToolDirect:
    """Test DisGeNET tool directly (Level 1)."""

    @pytest.fixture
    def tool_config(self):
        with open("src/tooluniverse/data/disgenet_tools.json") as f:
            tools = json.load(f)
            return next(t for t in tools if t["name"] == "DisGeNET_search_gene")

    @pytest.fixture
    def tool(self, tool_config):
        with patch.dict(os.environ, {"DISGENET_API_KEY": "test_key"}):
            from tooluniverse.disgenet_tool import DisGeNETTool
            return DisGeNETTool(tool_config)

    def test_missing_api_key(self, tool_config):
        with patch.dict(os.environ, {"DISGENET_API_KEY": ""}, clear=False):
            from tooluniverse.disgenet_tool import DisGeNETTool
            tool = DisGeNETTool(tool_config)
            result = tool.run({"operation": "search_gene", "gene": "BRCA1"})
            assert result["status"] == "error"
            assert "API key" in result["error"]

    def test_search_gene_missing_param(self, tool):
        result = tool.run({"operation": "search_gene"})
        assert result["status"] == "error"
        assert "gene" in result["error"].lower()

    def test_unknown_operation(self, tool):
        result = tool.run({"operation": "unknown"})
        assert result["status"] == "error"
        assert "unknown" in result["error"].lower()

    def test_auth_header_has_no_bearer_prefix(self, tool):
        """DisGeNET v1 expects the raw key, NOT 'Bearer <key>'."""
        headers = tool._get_headers()
        assert headers["Authorization"] == "test_key"
        assert "Bearer" not in headers["Authorization"]

    def test_disease_name_is_rejected_with_guidance(self, tool):
        """A free-text disease name must be rejected up front (not silently empty)."""
        result = tool.run({"operation": "get_disease_genes", "disease": "achromatopsia"})
        assert result["status"] == "error"
        assert "CUI" in result["error"]

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_gene_disease_success_parses_payload(self, mock_get, tool):
        mock_get.return_value = _summary([
            {"symbolOfGene": "BRCA1", "geneNcbiID": 672,
             "diseaseName": "Breast cancer", "diseaseUMLSCUI": "C0006142",
             "score": 0.8, "numPMIDs": 12, "ei": 1.0},
        ])
        result = tool.run({"operation": "get_gda", "gene": "BRCA1"})
        assert result["status"] == "success"
        assoc = result["data"]["associations"]
        assert len(assoc) == 1
        assert assoc[0]["gene_symbol"] == "BRCA1"
        assert assoc[0]["disease_name"] == "Breast cancer"
        # endpoint must be the /gda/summary query-param form
        called_url = mock_get.call_args[0][0]
        assert called_url.endswith("/gda/summary")
        assert mock_get.call_args.kwargs["params"]["gene_symbol"] == "BRCA1"

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_disease_genes_extracts_unique_genes(self, mock_get, tool):
        mock_get.return_value = _summary([
            {"symbolOfGene": "CNGA3", "geneNcbiID": 1261, "score": 0.7, "numPMIDs": 5},
            {"symbolOfGene": "CNGB3", "geneNcbiID": 54714, "score": 0.6, "numPMIDs": 3},
            {"symbolOfGene": "CNGA3", "geneNcbiID": 1261, "score": 0.7, "numPMIDs": 5},
        ])
        result = tool.run({"operation": "get_disease_genes", "disease": "C0152200"})
        assert result["status"] == "success"
        syms = [g["symbol"] for g in result["data"]["genes"]]
        assert syms == ["CNGA3", "CNGB3"]  # de-duplicated
        # CUI normalized to UMLS_ prefix in the request
        assert mock_get.call_args.kwargs["params"]["disease"] == "UMLS_C0152200"

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_variant_disease_by_rsid(self, mock_get, tool):
        mock_get.return_value = _summary([
            {"variantStrID": "rs121913529", "diseaseName": "Noonan syndrome",
             "diseaseUMLSCUI": "C0028326", "score": 0.9, "numPMIDs": 7},
        ])
        result = tool.run({"operation": "get_vda", "variant": "rs121913529"})
        assert result["status"] == "success"
        assert result["data"]["associations"][0]["variant"] == "rs121913529"
        assert mock_get.call_args[0][0].endswith("/vda/summary")

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_min_score_filter(self, mock_get, tool):
        mock_get.return_value = _summary([
            {"symbolOfGene": "A", "score": 0.9}, {"symbolOfGene": "B", "score": 0.1},
        ])
        result = tool.run({"operation": "get_gda", "gene": "TP53", "min_score": 0.5})
        assert result["data"]["count"] == 1
        assert result["data"]["associations"][0]["gene_symbol"] == "A"

    @patch("tooluniverse.disgenet_tool.requests.get")
    def test_http_error_returns_error_dict(self, mock_get, tool):
        import requests
        resp = MagicMock()
        resp.status_code = 403
        err = requests.exceptions.HTTPError(response=resp)
        resp.raise_for_status.side_effect = err
        mock_get.return_value = resp
        result = tool.run({"operation": "get_gda", "gene": "BRCA1"})
        assert result["status"] == "error"


class TestDisGeNETToolInterface:
    """Test DisGeNET tool via ToolUniverse interface (Level 2)."""

    @pytest.fixture
    def tu(self):
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()
        return tu

    def test_tools_registered(self, tu):
        import os
        if not os.environ.get("DISGENET_API_KEY"):
            pytest.skip("DISGENET_API_KEY not set")
        assert hasattr(tu.tools, "DisGeNET_search_gene")
        assert hasattr(tu.tools, "DisGeNET_search_disease")
        assert hasattr(tu.tools, "DisGeNET_get_gda")
        assert hasattr(tu.tools, "DisGeNET_get_vda")
        assert hasattr(tu.tools, "DisGeNET_get_disease_genes")
