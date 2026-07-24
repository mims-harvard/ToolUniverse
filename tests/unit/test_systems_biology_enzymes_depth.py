"""Systems-biology / enzymes depth tools: parse + error-path coverage (mocked HTTP).

Covers five new tools that close confirmed Reactome-Analysis and BioModels
capability gaps. All network calls are mocked; these tests never touch the
live APIs.

Reactome Analysis Service (reused ``ReactomeAnalysisTool``, endpoint dispatch):

* ``ReactomeAnalysis_expression_analysis`` (endpoint=expression_analysis) -
  quantitative EXPRESSION analysis; tab-delimited 'GENE\\tVALUE' rows mapped
  per pathway (summary.type=EXPRESSION, per-pathway entities.exp values).
* ``ReactomeAnalysis_species_comparison_v2`` (endpoint=species_comparison_v2)
  - true cross-species comparison via /species/{source}/{target}
  (summary.type=SPECIES_COMPARISON).
* ``ReactomeAnalysis_pathway_found_entities`` (endpoint=found_entities) -
  per-pathway found-entities drill-down (which submitted ids matched + mapsTo).
* ``ReactomeAnalysis_not_found_identifiers`` (endpoint=not_found_identifiers)
  - explicit list of unmapped submitted identifiers for a token.

BioModels (reused ``BioModelsRESTTool``, config-only):

* ``BioModels_list_all_model_ids`` - full registry of model identifiers.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename, tool_name):
    """Load a single tool config block by name from a data JSON file."""
    with open(os.path.join(_DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    for cfg in configs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


def _reactome_tool(tool_name):
    from tooluniverse.reactome_analysis_tool import ReactomeAnalysisTool

    return ReactomeAnalysisTool(_load_config("reactome_analysis_tools.json", tool_name))


def _biomodels_tool(tool_name):
    from tooluniverse.biomodels_tool import BioModelsRESTTool

    return BioModelsRESTTool(_load_config("biomodels_tools.json", tool_name))


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    resp.headers = {"Content-Type": "application/json"}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# ReactomeAnalysis_expression_analysis
# ---------------------------------------------------------------------------

_EXPRESSION_FAKE = {
    "summary": {
        "token": "TOKEN_EXP",
        "type": "EXPRESSION",
        "projection": False,
    },
    "expression": {"columnNames": ["FC"], "min": -1.8, "max": 3.1},
    "identifiersNotFound": 0,
    "pathwaysFound": 12,
    "pathways": [
        {
            "stId": "R-HSA-2559586",
            "name": "Regulation of TP53 Expression",
            "species": {"name": "Homo sapiens"},
            "inDisease": False,
            "llp": True,
            "entities": {
                "found": 1,
                "total": 5,
                "ratio": 0.0004,
                "pValue": 0.01,
                "fdr": 0.05,
                "exp": [-1.8],
            },
            "reactions": {"found": 2, "total": 10},
        }
    ],
}


class TestExpressionAnalysis(unittest.TestCase):
    def test_parses_expression_overlay(self):
        """Expression matrix parses into per-pathway exp overlay + column metadata."""
        tool = _reactome_tool("ReactomeAnalysis_expression_analysis")
        with patch("tooluniverse.reactome_analysis_tool.requests.post") as post:
            post.return_value = _mock_response(_EXPRESSION_FAKE)
            result = tool.run({"identifiers": "PTEN\t2.5\nTP53\t-1.8\nEGFR\t3.1"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["analysis_type"], "EXPRESSION")
        self.assertEqual(data["expression_column_names"], ["FC"])
        self.assertEqual(data["expression_min"], -1.8)
        self.assertEqual(data["expression_max"], 3.1)
        self.assertEqual(data["pathways"][0]["entities_exp"], [-1.8])
        # POST body must carry the tab-delimited expression matrix.
        self.assertIn("\t", post.call_args.kwargs["data"])

    def test_missing_identifiers_returns_error(self):
        """Missing identifiers yields a status=error, never raises."""
        tool = _reactome_tool("ReactomeAnalysis_expression_analysis")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("identifiers", result["error"])

    def test_http_failure_does_not_raise(self):
        """An HTTP failure is caught and returned as status=error."""
        tool = _reactome_tool("ReactomeAnalysis_expression_analysis")
        with patch("tooluniverse.reactome_analysis_tool.requests.post") as post:
            resp = MagicMock()
            resp.raise_for_status.side_effect = Exception("boom")
            post.return_value = resp
            result = tool.run({"identifiers": "PTEN\t2.5"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# ReactomeAnalysis_species_comparison_v2
# ---------------------------------------------------------------------------

_SPECIES_FAKE = {
    "summary": {"token": "TOKEN_SP", "type": "SPECIES_COMPARISON", "projection": True},
    "identifiersNotFound": 510,
    "pathwaysFound": 2709,
    "pathways": [
        {
            "stId": "R-HSA-597592",
            "name": "Post-translational protein modification",
            "species": {"name": "Homo sapiens"},
            "entities": {"found": 100, "total": 200, "pValue": 0.0, "fdr": 0.0},
            "reactions": {"found": 50, "total": 80},
        }
    ],
}


class TestSpeciesComparisonV2(unittest.TestCase):
    def test_parses_species_comparison(self):
        """Species comparison parses type + counts and hits /species endpoint."""
        tool = _reactome_tool("ReactomeAnalysis_species_comparison_v2")
        with patch("tooluniverse.reactome_analysis_tool.requests.get") as get:
            get.return_value = _mock_response(_SPECIES_FAKE)
            result = tool.run({"species": 48892, "page_size": 3})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["analysis_type"], "SPECIES_COMPARISON")
        self.assertEqual(data["pathways_found"], 2709)
        self.assertEqual(data["identifiers_not_found"], 510)
        # The real /species/{source}/{target} endpoint must be hit.
        called_url = get.call_args.args[0]
        self.assertIn("/species/homoSapiens/48892", called_url)

    def test_missing_species_returns_error(self):
        """Missing species yields a status=error, never raises."""
        tool = _reactome_tool("ReactomeAnalysis_species_comparison_v2")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("species", result["error"])


# ---------------------------------------------------------------------------
# ReactomeAnalysis_pathway_found_entities
# ---------------------------------------------------------------------------

_FOUND_FAKE = {
    "found": 3,
    "totalEntitiesCount": 5,
    "resources": [{"resource": "TOTAL"}],
    "identifiers": [
        {
            "id": "BRCA1",
            "exp": [],
            "mapsTo": [
                {"resource": "UNIPROT", "ids": ["P38398"]},
                {"resource": "ENSEMBL", "ids": ["ENST00000357654", "ENSG00000012048"]},
            ],
        },
        {
            "id": "TP53",
            "exp": [],
            "mapsTo": [{"resource": "UNIPROT", "ids": ["P04637"]}],
        },
    ],
}


class TestPathwayFoundEntities(unittest.TestCase):
    def test_parses_found_entities_with_mapsto(self):
        """Found-entities parse with their UniProt/ENSEMBL mapsTo cross-refs."""
        tool = _reactome_tool("ReactomeAnalysis_pathway_found_entities")
        with patch("tooluniverse.reactome_analysis_tool.requests.get") as get:
            get.return_value = _mock_response(_FOUND_FAKE)
            result = tool.run({"token": "TOKEN_X", "pathway": "R-HSA-3700989"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["pathway"], "R-HSA-3700989")
        self.assertEqual(data["found"], 3)
        first = data["identifiers"][0]
        self.assertEqual(first["id"], "BRCA1")
        resources = {m["resource"]: m["ids"] for m in first["mapsTo"]}
        self.assertEqual(resources["UNIPROT"], ["P38398"])
        self.assertIn("ENSG00000012048", resources["ENSEMBL"])
        called_url = get.call_args.args[0]
        self.assertIn("/found/entities/R-HSA-3700989", called_url)

    def test_missing_token_returns_error(self):
        """Missing token yields a status=error, never raises."""
        tool = _reactome_tool("ReactomeAnalysis_pathway_found_entities")
        result = tool.run({"pathway": "R-HSA-3700989"})
        self.assertEqual(result["status"], "error")
        self.assertIn("token", result["error"])

    def test_missing_pathway_returns_error(self):
        """Missing pathway yields a status=error, never raises."""
        tool = _reactome_tool("ReactomeAnalysis_pathway_found_entities")
        result = tool.run({"token": "TOKEN_X"})
        self.assertEqual(result["status"], "error")
        self.assertIn("pathway", result["error"])


# ---------------------------------------------------------------------------
# ReactomeAnalysis_not_found_identifiers
# ---------------------------------------------------------------------------

_NOT_FOUND_FAKE = [
    {"id": "NOTAGENE123", "exp": []},
    {"id": "XYZZYFAKE", "exp": []},
]


class TestNotFoundIdentifiers(unittest.TestCase):
    def test_parses_unmapped_identifiers(self):
        """Unmapped identifier list and count parse correctly."""
        tool = _reactome_tool("ReactomeAnalysis_not_found_identifiers")
        with patch("tooluniverse.reactome_analysis_tool.requests.get") as get:
            get.return_value = _mock_response(_NOT_FOUND_FAKE)
            result = tool.run({"token": "TOKEN_X"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["not_found_count"], 2)
        self.assertEqual(data["not_found"], ["NOTAGENE123", "XYZZYFAKE"])

    def test_empty_list_when_all_mapped(self):
        """An all-mapped run returns an empty not_found list with count 0."""
        tool = _reactome_tool("ReactomeAnalysis_not_found_identifiers")
        with patch("tooluniverse.reactome_analysis_tool.requests.get") as get:
            get.return_value = _mock_response([])
            result = tool.run({"token": "TOKEN_X"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["not_found_count"], 0)
        self.assertEqual(result["data"]["not_found"], [])

    def test_missing_token_returns_error(self):
        """Missing token yields a status=error, never raises."""
        tool = _reactome_tool("ReactomeAnalysis_not_found_identifiers")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("token", result["error"])


# ---------------------------------------------------------------------------
# BioModels_list_all_model_ids
# ---------------------------------------------------------------------------

_BIOMODELS_FAKE = {
    "hits": 3190,
    "models": ["BIOMD0000000001", "BIOMD0000000002", "BIOMD0000000003"],
}


class TestBioModelsListAll(unittest.TestCase):
    def test_parses_full_registry(self):
        """Full registry parses hits count + model id list and targets identifiers endpoint."""
        tool = _biomodels_tool("BioModels_list_all_model_ids")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _mock_response(_BIOMODELS_FAKE)
            result = tool.run({})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["hits"], 3190)
        self.assertEqual(len(result["data"]["models"]), 3)
        self.assertEqual(result["data"]["models"][0], "BIOMD0000000001")
        # Endpoint must target the full identifiers registry.
        called_url = req.call_args.args[2]
        self.assertIn("/biomodels/model/identifiers", called_url)

    def test_http_error_does_not_raise(self):
        """A non-2xx response is returned as status=error, never raises."""
        tool = _biomodels_tool("BioModels_list_all_model_ids")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            err_resp = MagicMock()
            err_resp.status_code = 500
            err_resp.text = "Internal Server Error"
            req.return_value = err_resp
            result = tool.run({})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
