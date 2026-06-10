"""Depth coverage for the plant-agriculture cluster: name->symbol resolution,
Plant Reactome pathway participants, and species pathway-tree enumeration.

Each test mocks the upstream HTTP call so it runs offline, covering both the
parse (success) path and the failure path. The tools must always return a
{status: ...} envelope and never raise.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

import requests

pytestmark = pytest.mark.unit


def _make_usda_search():
    from tooluniverse.usda_plants_tool import USDAPlantsProfileTool

    return USDAPlantsProfileTool(
        {
            "name": "USDA_plants_search_by_name",
            "type": "USDAPlantsProfileTool",
            "fields": {"timeout": 30, "action": "search"},
        }
    )


def _make_pr_tool(action):
    from tooluniverse.plant_reactome_tool import PlantReactomeTool

    return PlantReactomeTool(
        {
            "name": f"PlantReactome_{action}",
            "type": "PlantReactomeTool",
            "fields": {"action": action},
        }
    )


class TestUSDASearchByName(unittest.TestCase):
    USDA_PAYLOAD = [
        {
            "Text": "Arizona white oak",
            "Plant": {
                "Id": 70178,
                "Symbol": "QUAR",
                "ScientificName": "<i>Quercus arizonica</i> Sarg.",
                "CommonName": "Arizona white oak",
                "Rank": "Species",
            },
        },
        {
            "Text": "white oak",
            "Plant": {
                "Id": 70172,
                "Symbol": "QUAL",
                "ScientificName": "<i>Quercus alba</i> L.",
                "CommonName": "white oak",
                "Rank": "Species",
            },
        },
    ]

    def test_parse_success(self):
        """Parse the mocked upstream payload into the tool envelope."""
        tool = _make_usda_search()
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = self.USDA_PAYLOAD
            resp.raise_for_status.return_value = None
            get.return_value = resp
            out = tool.run({"searchText": "white oak"})

        self.assertEqual(out["status"], "success")
        self.assertEqual(len(out["data"]), 2)
        first = out["data"][0]
        self.assertEqual(first["symbol"], "QUAR")
        # HTML tags stripped from the scientific name
        self.assertEqual(first["scientific_name"], "Quercus arizonica Sarg.")
        self.assertEqual(first["common_name"], "Arizona white oak")
        self.assertEqual(first["rank"], "Species")
        self.assertEqual(out["metadata"]["total_results"], 2)
        self.assertEqual(out["metadata"]["query"], "white oak")

    def test_limit_truncates(self):
        """limit must cap the returned list while reporting the true total."""
        tool = _make_usda_search()
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = self.USDA_PAYLOAD
            resp.raise_for_status.return_value = None
            get.return_value = resp
            out = tool.run({"searchText": "white oak", "limit": 1})
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["metadata"]["total_results"], 2)
        self.assertEqual(out["metadata"]["returned_results"], 1)

    def test_missing_search_text(self):
        """Missing searchText returns an error envelope, not a raise."""
        tool = _make_usda_search()
        out = tool.run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("searchText", out["error"])

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_usda_search()
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            out = tool.run({"searchText": "white oak"})
        self.assertEqual(out["status"], "error")
        self.assertIn("USDA PLANTS request failed", out["error"])

    def test_timeout_path(self):
        """A timeout returns a status=error envelope."""
        tool = _make_usda_search()
        with patch("tooluniverse.usda_plants_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout()
            out = tool.run({"searchText": "white oak"})
        self.assertEqual(out["status"], "error")
        self.assertIn("timed out", out["error"])


class TestPlantReactomeParticipants(unittest.TestCase):
    PAYLOAD = [
        {
            "peDbId": 5138520,
            "displayName": "argininosuccinate lyase activity [plastid stroma]",
            "schemaClass": "CatalystActivity",
            "refEntities": [
                {
                    "identifier": "Q10MK5",
                    "schemaClass": "ReferenceGeneProduct",
                    "displayName": "UniProt:Q10MK5 LOC_OS03G19280",
                    "geneName": ["LOC_OS03G19280", "Os03g0305500"],
                    "url": "http://purl.uniprot.org/uniprot/Q10MK5",
                }
            ],
        }
    ]

    def test_parse_success(self):
        """Parse the mocked upstream payload into the tool envelope."""
        tool = _make_pr_tool("get_participants")
        with patch("tooluniverse.plant_reactome_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = self.PAYLOAD
            resp.raise_for_status.return_value = None
            get.return_value = resp
            out = tool.run({"pathway_id": "R-OSA-1119263"})

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["metadata"]["total_participants"], 1)
        ref = out["data"][0]["ref_entities"][0]
        self.assertEqual(ref["identifier"], "Q10MK5")
        self.assertEqual(ref["gene_names"], ["LOC_OS03G19280", "Os03g0305500"])
        self.assertEqual(out["metadata"]["pathway_id"], "R-OSA-1119263")

    def test_missing_pathway_id(self):
        """Missing pathway_id returns an error envelope."""
        tool = _make_pr_tool("get_participants")
        out = tool.run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("pathway_id", out["error"])

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_pr_tool("get_participants")
        with patch("tooluniverse.plant_reactome_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("down")
            out = tool.run({"pathway_id": "R-OSA-1119263"})
        self.assertEqual(out["status"], "error")
        self.assertIn("connect", out["error"].lower())


class TestPlantReactomeSpeciesTree(unittest.TestCase):
    PAYLOAD = [
        {
            "stId": "R-OSA-2894886",
            "name": "Cellular processes",
            "species": "Oryza sativa",
            "type": "TopLevelPathway",
            "diagram": True,
            "children": [
                {
                    "stId": "R-OSA-9640670",
                    "name": "Cell cycle",
                    "species": "Oryza sativa",
                    "type": "Pathway",
                }
            ],
        }
    ]

    def test_parse_success(self):
        """Parse the mocked upstream payload into the tool envelope."""
        tool = _make_pr_tool("get_species_tree")
        with patch("tooluniverse.plant_reactome_tool.requests.get") as get:
            resp = MagicMock()
            resp.json.return_value = self.PAYLOAD
            resp.raise_for_status.return_value = None
            get.return_value = resp
            out = tool.run({"tax_id": 4530})

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["metadata"]["total_top_level_pathways"], 1)
        self.assertEqual(out["metadata"]["tax_id"], "4530")
        top = out["data"][0]
        self.assertEqual(top["stId"], "R-OSA-2894886")
        self.assertEqual(top["children"][0]["stId"], "R-OSA-9640670")

    def test_missing_tax_id(self):
        """Missing tax_id returns an error envelope."""
        tool = _make_pr_tool("get_species_tree")
        out = tool.run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("tax_id", out["error"])

    def test_error_path_does_not_raise(self):
        """A network failure returns status=error, never raises."""
        tool = _make_pr_tool("get_species_tree")
        with patch("tooluniverse.plant_reactome_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout()
            out = tool.run({"tax_id": 4530})
        self.assertEqual(out["status"], "error")
        self.assertIn("timed out", out["error"])


if __name__ == "__main__":
    unittest.main()
