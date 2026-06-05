"""HPO phenotype->genes and phenotype->diseases tools (JAX network annotation).

These fill a real capability gap: skills needed to go from an observed HPO
phenotype to candidate genes / a disease differential, but TU only exposed the
term lookup and hierarchy. The new endpoints use
ontology.jax.org/api/network/annotation/{HP-id}, which returns the genes and
diseases linked to a phenotype.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

_ANNOTATION = {
    "genes": [
        {"id": "NCBIGene:5649", "name": "RELN"},
        {"id": "NCBIGene:6323", "name": "SCN1A"},
        {"id": "NCBIGene:9211", "name": "LGI1"},
    ],
    "diseases": [
        {
            "id": "OMIM:600512",
            "name": "Epilepsy, familial temporal lobe, 1",
            "mondoId": "MONDO:0700090",
        },
        {"id": "ORPHA:157835", "name": "Paroxysmal hemicrania", "mondoId": "MONDO:0015529"},
    ],
    "assays": [],
    "medicalActions": [],
}


def _tool(endpoint):
    from tooluniverse.hpo_tool import HPOTool

    return HPOTool({"name": "t", "type": "HPOTool", "fields": {"endpoint": endpoint}})


def _resp():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = _ANNOTATION
    return r


class TestHPOPhenotypeAnnotations(unittest.TestCase):
    def test_genes_by_phenotype(self):
        tool = _tool("get_associated_genes")
        with patch("tooluniverse.hpo_tool.requests.get", return_value=_resp()) as get:
            result = tool.run({"term_id": "HP:0001250", "limit": 2})
        # hits the network-annotation endpoint, not /hp/terms
        self.assertIn("network/annotation/HP:0001250", get.call_args.args[0])
        self.assertEqual(result["status"], "success")
        genes = result["data"]["genes"]
        self.assertEqual(len(genes), 2)  # limit respected
        self.assertEqual(genes[0], {"id": "NCBIGene:5649", "name": "RELN"})
        self.assertEqual(result["metadata"]["total"], 3)

    def test_diseases_by_phenotype_includes_mondo(self):
        tool = _tool("get_associated_diseases")
        with patch("tooluniverse.hpo_tool.requests.get", return_value=_resp()):
            result = tool.run({"term_id": "HP:0001250"})
        diseases = result["data"]["diseases"]
        self.assertEqual(diseases[0]["id"], "OMIM:600512")
        self.assertEqual(diseases[0]["mondo_id"], "MONDO:0700090")

    def test_normalizes_bare_id_and_requires_term(self):
        tool = _tool("get_associated_genes")
        with patch("tooluniverse.hpo_tool.requests.get", return_value=_resp()) as get:
            tool.run({"term_id": "0001250"})  # no HP: prefix
        self.assertIn("HP:0001250", get.call_args.args[0])
        # missing term_id -> validation error, no network call
        with patch("tooluniverse.hpo_tool.requests.get") as get2:
            result = tool.run({})
        self.assertEqual(result["status"], "error")
        get2.assert_not_called()


if __name__ == "__main__":
    unittest.main()
