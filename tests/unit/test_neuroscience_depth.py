"""Neuroscience depth tools: parse + error-path coverage (mocked HTTP).

Covers four new tools that close confirmed neuroscience capability gaps by
reusing existing tool classes (no new @register_tool class):

* ``AllenBrain_get_structure_expression_values`` (AllenBrainTool,
  query_type="structure_unionize") — quantified per-structure expression
  values (StructureUnionize) for one Allen Mouse Brain ISH SectionDataSet:
  expression_energy, expression_density, sum_expressing_pixels.
* ``NeuroMorpho_search_literature`` (NeuroMorphoTool, endpoint_type=
  "literature", query_mode="search") — source-publication records searchable
  by brainRegion / cellType / tracingSystem / species.
* ``NeuroMorpho_get_persistence_vector`` (NeuroMorphoTool, endpoint_type=
  "pvec") — 100-coefficient TMD shape signature with scaling factor.
* ``NeuroVault_list_atlases`` (BaseRESTTool) — labeled anatomical atlas maps
  (label image + label-description file) listable from NeuroVault.

All network calls are mocked; these tests never touch the live APIs.
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename, tool_name):
    """Load the real JSON tool config for a tool by name."""
    with open(os.path.join(_DATA_DIR, filename)) as fh:
        configs = json.load(fh)
    for cfg in configs:
        if cfg["name"] == tool_name:
            return cfg
    raise KeyError(f"{tool_name} not found in {filename}")


def _mock_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    resp.text = json.dumps(payload)
    resp.headers = {"content-type": "application/json"}
    return resp


# ---------------------------------------------------------------------------
# AllenBrain_get_structure_expression_values  (StructureUnionize)
# ---------------------------------------------------------------------------

_ALLEN_SU_FAKE = {
    "success": True,
    "id": 0,
    "start_row": 0,
    "num_rows": 2,
    "total_rows": 2406,
    "msg": [
        {
            "expression_density": 0.103382,
            "expression_energy": 19.0584,
            "id": 453852509,
            "section_data_set_id": 75457539,
            "structure_id": 112892315,
            "sum_expressing_pixels": 7230.32,
            "sum_expressing_pixel_intensity": 1332910.0,
            "structure": {
                "id": 112892315,
                "acronym": "DR-lw",
                "name": "lateral wings of the dorsal raphe nucleus",
            },
        }
    ],
}


def _allen_tool():
    from tooluniverse.allen_brain_tool import AllenBrainTool

    cfg = _load_config(
        "allen_brain_tools.json", "AllenBrain_get_structure_expression_values"
    )
    return AllenBrainTool(cfg)


class TestAllenStructureExpressionValues(unittest.TestCase):
    def test_parses_numeric_expression_values(self):
        """Per-structure expression energy/density/pixels parse correctly."""
        tool = _allen_tool()
        with patch("tooluniverse.allen_brain_tool.requests.get") as get:
            get.return_value = _mock_response(_ALLEN_SU_FAKE)
            result = tool.run({"section_data_set_id": 75457539, "num_rows": 3})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_results"], 2406)
        self.assertEqual(result["metadata"]["section_data_set_id"], 75457539)
        row = result["data"][0]
        self.assertAlmostEqual(row["expression_energy"], 19.0584)
        self.assertAlmostEqual(row["expression_density"], 0.103382)
        self.assertAlmostEqual(row["sum_expressing_pixels"], 7230.32)
        self.assertEqual(row["structure_id"], 112892315)
        self.assertEqual(
            row["structure"]["name"], "lateral wings of the dorsal raphe nucleus"
        )

    def test_missing_section_data_set_id_returns_error(self):
        """Missing required id yields a status=error envelope, no raise."""
        tool = _allen_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("section_data_set_id", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """A connection error is caught and returned as status=error."""
        import requests

        tool = _allen_tool()
        with patch("tooluniverse.allen_brain_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            result = tool.run({"section_data_set_id": 75457539})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# NeuroMorpho_search_literature
# ---------------------------------------------------------------------------

_NM_LIT_SEARCH_FAKE = {
    "_embedded": {
        "publicationResources": [
            {
                "article_id": "56e9c8a1e4b0355017b2fb12",
                "doi": "10.1084/jem.20151776",
                "pmid": "27432938",
                "journal": "J Exp Med",
                "title": "Increased expression of AT-1/SLC33A1 causes ...",
                "species": ["mouse"],
                "brainRegion": ["hippocampus"],
            }
        ]
    },
    "page": {"size": 2, "totalElements": 128, "totalPages": 64, "number": 0},
}


def _nm_search_lit_tool():
    from tooluniverse.neuromorpho_tool import NeuroMorphoTool

    cfg = _load_config("neuromorpho_tools.json", "NeuroMorpho_search_literature")
    return NeuroMorphoTool(cfg)


class TestNeuroMorphoSearchLiterature(unittest.TestCase):
    def test_parses_literature_records(self):
        """Literature search parses records and builds the q param."""
        tool = _nm_search_lit_tool()
        with patch("tooluniverse.neuromorpho_tool.requests.get") as get:
            get.return_value = _mock_response(_NM_LIT_SEARCH_FAKE)
            result = tool.run(
                {"query_field": "brainRegion", "query_value": "hippocampus", "size": 2}
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_results"], 128)
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["doi"], "10.1084/jem.20151776")
        # Verify the q param was constructed from field:value.
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["q"], "brainRegion:hippocampus")

    def test_missing_query_value_returns_error(self):
        """Missing query_value yields status=error, no raise."""
        tool = _nm_search_lit_tool()
        result = tool.run({"query_field": "brainRegion"})
        self.assertEqual(result["status"], "error")
        self.assertIn("query_value", result["error"])


# ---------------------------------------------------------------------------
# NeuroMorpho_get_literature (single article by id)
# ---------------------------------------------------------------------------

_NM_LIT_ID_FAKE = {
    "article_id": "56e9c892e4b0355017b2fa0f",
    "doi": "10.1023/A:1005260824715",
    "journal": "Neurophysiology",
    "species": ["frog"],
    "brainRegion": ["Motor cortex"],
}


def _nm_get_lit_tool():
    from tooluniverse.neuromorpho_tool import NeuroMorphoTool

    cfg = _load_config("neuromorpho_tools.json", "NeuroMorpho_get_literature")
    return NeuroMorphoTool(cfg)


class TestNeuroMorphoGetLiterature(unittest.TestCase):
    def test_parses_single_article(self):
        """A single literature record parses by article_id."""
        tool = _nm_get_lit_tool()
        with patch("tooluniverse.neuromorpho_tool.requests.get") as get:
            get.return_value = _mock_response(_NM_LIT_ID_FAKE)
            result = tool.run({"article_id": "56e9c892e4b0355017b2fa0f"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["doi"], "10.1023/A:1005260824715")
        self.assertEqual(result["data"]["species"], ["frog"])

    def test_missing_article_id_returns_error(self):
        """Missing article_id yields status=error, no raise."""
        tool = _nm_get_lit_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("article_id", result["error"])


# ---------------------------------------------------------------------------
# NeuroMorpho_get_persistence_vector
# ---------------------------------------------------------------------------

_NM_PVEC_FAKE = {
    "neuron_id": 1,
    "scaling_factor": 244.928,
    "distance": 0.0,
    "coefficients": [3276.79, 3356.89, 3432.29] + [0.0] * 97,
}


def _nm_pvec_tool():
    from tooluniverse.neuromorpho_tool import NeuroMorphoTool

    cfg = _load_config("neuromorpho_tools.json", "NeuroMorpho_get_persistence_vector")
    return NeuroMorphoTool(cfg)


class TestNeuroMorphoPersistenceVector(unittest.TestCase):
    def test_parses_persistence_vector(self):
        """100-coefficient TMD vector + scaling factor parse correctly."""
        tool = _nm_pvec_tool()
        with patch("tooluniverse.neuromorpho_tool.requests.get") as get:
            get.return_value = _mock_response(_NM_PVEC_FAKE)
            result = tool.run({"neuron_id": 1})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["neuron_id"], 1)
        self.assertAlmostEqual(result["data"]["scaling_factor"], 244.928)
        self.assertEqual(result["metadata"]["num_coefficients"], 100)
        self.assertEqual(result["data"]["coefficients"][:3], [3276.79, 3356.89, 3432.29])

    def test_missing_neuron_id_returns_error(self):
        """Missing neuron_id yields status=error, no raise."""
        tool = _nm_pvec_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("neuron_id", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """A timeout is caught and returned as status=error."""
        import requests

        tool = _nm_pvec_tool()
        with patch("tooluniverse.neuromorpho_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout("slow")
            result = tool.run({"neuron_id": 1})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# NeuroVault_list_atlases  (BaseRESTTool, config-driven)
# ---------------------------------------------------------------------------

_NV_ATLAS_FAKE = {
    "count": 18,
    "next": None,
    "previous": None,
    "results": [
        {
            "id": 14228,
            "name": "Thalamus maxprob thr25 2mm",
            "file": "http://neurovault.org/media/images/1056/Thalamus-maxprob-thr25-2mm.nii.gz",
            "label_description_file": "http://neurovault.org/media/images/1056/Thalamus-maxprob-thr25-2mm.xml",
            "collection": "http://neurovault.org/collections/1056/",
            "collection_id": 1056,
        }
    ],
}


def _nv_list_atlases_tool():
    from tooluniverse.base_rest_tool import BaseRESTTool

    cfg = _load_config("neurovault_tools.json", "NeuroVault_list_atlases")
    return BaseRESTTool(cfg)


class TestNeuroVaultListAtlases(unittest.TestCase):
    def test_parses_atlas_list(self):
        """Atlas list parses count + label image / label-description URLs."""
        tool = _nv_list_atlases_tool()
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _mock_response(_NV_ATLAS_FAKE)
            result = tool.run({"limit": 5})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["count"], 18)
        atlas = data["results"][0]
        self.assertEqual(atlas["name"], "Thalamus maxprob thr25 2mm")
        self.assertTrue(atlas["file"].endswith("Thalamus-maxprob-thr25-2mm.nii.gz"))
        self.assertTrue(
            atlas["label_description_file"].endswith("Thalamus-maxprob-thr25-2mm.xml")
        )

    def test_http_error_returns_error_not_raise(self):
        """A 500 status is mapped to status=error, no raise."""
        tool = _nv_list_atlases_tool()
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _mock_response({"detail": "boom"}, status_code=500)
            result = tool.run({"limit": 5})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# NeuroVault_get_atlas  (BaseRESTTool, config-driven, by id)
# ---------------------------------------------------------------------------

_NV_ATLAS_ONE_FAKE = {
    "id": 14228,
    "name": "Thalamus maxprob thr25 2mm",
    "file": "http://neurovault.org/media/images/1056/Thalamus-maxprob-thr25-2mm.nii.gz",
    "label_description_file": "http://neurovault.org/media/images/1056/Thalamus-maxprob-thr25-2mm.xml",
    "collection": "http://neurovault.org/collections/1056/",
    "collection_id": 1056,
}


def _nv_get_atlas_tool():
    from tooluniverse.base_rest_tool import BaseRESTTool

    cfg = _load_config("neurovault_tools.json", "NeuroVault_get_atlas")
    return BaseRESTTool(cfg)


class TestNeuroVaultGetAtlas(unittest.TestCase):
    def test_parses_single_atlas_and_substitutes_id(self):
        """Single atlas parses and {atlas_id} is substituted into the URL."""
        tool = _nv_get_atlas_tool()
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _mock_response(_NV_ATLAS_ONE_FAKE)
            result = tool.run({"atlas_id": 14228})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["name"], "Thalamus maxprob thr25 2mm")
        # URL path parameter {atlas_id} should be substituted.
        _, kwargs = req.call_args
        called_url = req.call_args[0][2]
        self.assertIn("14228", called_url)

    def test_http_error_returns_error_not_raise(self):
        """A 404 status is mapped to status=error, no raise."""
        tool = _nv_get_atlas_tool()
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _mock_response({"detail": "not found"}, status_code=404)
            result = tool.run({"atlas_id": 999999999})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
