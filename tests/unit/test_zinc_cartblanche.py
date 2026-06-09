"""ZINC tool migrated from retired zinc15.docking.org to ZINC22 / CartBlanche22.

The old zinc15 endpoints now serve a bot-verification HTML wall (HTTP 200 +
HTML, no JSON). ZincTool now targets https://cartblanche22.docking.org:

- get_compound / get_purchasable -> GET /substance/{id}.json
- search_by_smiles -> async GET /smiles.json (multipart) -> poll
  /search/result/{task} until status == SUCCESS
- search_compounds (name) / search_by_properties -> unsupported by CartBlanche,
  return a clean {status: error, ...}

These tests mock the HTTP session so they run offline and assert the parsing
of each migrated operation.
"""

import unittest
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.zinc_tool import ZincTool

    return ZincTool({"name": "ZINC_test", "type": "ZincTool", "parameter": {}})


# Trimmed real /substance/ZINC000000000053.json (aspirin) response shape.
_SUBSTANCE_BODY = {
    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
    "mol_formula": "C9H8O4",
    "zinc_id": "ZINC000000000053",
    "rings": 1,
    "hetero_atoms": 4,
    "db": "zinc20",
    "tranche_details": {
        "heavy_atoms": 13,
        "logp": 1.31,
        "mwt": 180.159,
        "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
        "inchikey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
    },
    "catalogs": [
        {
            "catalog_name": "Nanjing Norris Pharm",
            "price": 240,
            "purchase": 1,
            "quantity": 10,
            "shipping": "6 weeks",
            "supplier_code": "NSTH-D20428",
            "unit": "mg",
            "url": None,
        },
        {
            "catalog_name": "eMolecules Building Blocks",
            "price": 240,
            "purchase": 1,
            "quantity": 10,
            "shipping": "6 weeks",
            "supplier_code": "474821",
            "unit": "mg",
            "url": "https://orderbb.emolecules.com/search/",
        },
    ],
}

# Real /search/result/{task} shapes for the async structure search.
_SEARCH_PROGRESS = {"progress": 0.0, "result": [], "status": "PROGRESS"}
_SEARCH_SUCCESS = {
    "progress": 1.0,
    "status": "SUCCESS",
    "result": {
        "hostname": "n-1-18.cluster.ucsf.bkslab.org",
        "logs": 1,
        "zinc22": [
            {
                "zinc_id": "ZINC6m0000002gSu",
                "smiles": "c1ccccc1",
                "matched_smiles": "c1ccccc1",
                "mol_formula": "C6H6",
                "db": "zinc22",
                "rings": 1,
                "hetero_atoms": 0,
                "tranche_details": {
                    "heavy_atoms": 6,
                    "logp": 1.687,
                    "mwt": 78.114,
                    "inchi": "InChI=1S/C6H6/c1-2-4-6-5-3-1/h1-6H",
                    "inchikey": "UHOVQNZJYSORNB-UHFFFAOYSA-N",
                },
                "catalogs": [
                    {"catalog_name": "Enamine_M", "supplier_code": "Z57120059"},
                    {"catalog_name": "coconut", "supplier_code": "CNP0140642.0"},
                ],
            }
        ],
        "zinc22_missing": [""],
    },
}


def _json_response(body, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = str(body)
    return resp


class TestZincCartBlanche(unittest.TestCase):
    def test_get_compound_parse(self):
        tool = _tool()
        tool.session = MagicMock()
        tool.session.get.return_value = _json_response(_SUBSTANCE_BODY)

        out = tool.run({"operation": "get_compound", "zinc_id": "ZINC000000000053"})

        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["zinc_id"], "ZINC000000000053")
        self.assertEqual(data["smiles"], "CC(=O)Oc1ccccc1C(=O)O")
        self.assertEqual(data["formula"], "C9H8O4")
        self.assertEqual(data["mwt"], 180.159)
        self.assertEqual(data["logp"], 1.31)
        self.assertEqual(data["heavy_atoms"], 13)
        self.assertEqual(data["inchikey"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        self.assertEqual(data["database"], "zinc20")
        self.assertEqual(data["n_catalogs"], 2)
        # Hits the CartBlanche substance endpoint.
        called_url = tool.session.get.call_args[0][0]
        self.assertIn("cartblanche22.docking.org/substance/", called_url)

    def test_get_purchasable_catalogs_parse(self):
        tool = _tool()
        tool.session = MagicMock()
        tool.session.get.return_value = _json_response(_SUBSTANCE_BODY)

        out = tool.run({"operation": "get_purchasable", "zinc_id": "ZINC000000000053"})

        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["vendor_count"], 2)
        first = data["vendors"][0]
        self.assertEqual(first["catalog_name"], "Nanjing Norris Pharm")
        self.assertEqual(first["supplier_code"], "NSTH-D20428")
        self.assertEqual(first["price"], 240)
        self.assertEqual(first["unit"], "mg")
        self.assertTrue(first["purchasable"])

    def test_get_compound_not_found(self):
        tool = _tool()
        tool.session = MagicMock()
        tool.session.get.return_value = _json_response(
            {"error": "not found"}, status_code=404
        )

        out = tool.run({"operation": "get_compound", "zinc_id": "ZINC999999999999"})

        self.assertEqual(out["status"], "error")
        self.assertIn("not found", out["error"].lower())

    def test_search_by_smiles_parse(self):
        tool = _tool()
        tool.session = MagicMock()
        # First .get is the submit (returns a task id); subsequent .get calls
        # are result polls: one PROGRESS, then SUCCESS.
        submit_resp = _json_response({"task": "abc-123"})
        progress_resp = _json_response(_SEARCH_PROGRESS)
        success_resp = _json_response(_SEARCH_SUCCESS)
        tool.session.get.side_effect = [submit_resp, progress_resp, success_resp]

        out = tool.run(
            {
                "operation": "search_by_smiles",
                "smiles": "c1ccccc1",
                "dist": 2,
                "database": "zinc22",
                "count": 5,
            }
        )

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["count"], 1)
        hit = out["data"][0]
        self.assertEqual(hit["zinc_id"], "ZINC6m0000002gSu")
        self.assertEqual(hit["smiles"], "c1ccccc1")
        self.assertEqual(hit["matched_smiles"], "c1ccccc1")
        self.assertEqual(hit["formula"], "C6H6")
        self.assertEqual(hit["mwt"], 78.114)
        self.assertEqual(hit["database"], "zinc22")
        self.assertEqual(hit["n_catalogs"], 2)
        # The submit call uses multipart form (files=) on /smiles.json.
        submit_call = tool.session.get.call_args_list[0]
        self.assertIn("smiles.json", submit_call[0][0])
        self.assertIn("files", submit_call.kwargs)
        self.assertIn("smiles", submit_call.kwargs["files"])

    def test_search_by_smiles_failure_status(self):
        tool = _tool()
        tool.session = MagicMock()
        submit_resp = _json_response({"task": "abc-123"})
        failure_resp = _json_response(
            {"progress": 1.0, "result": [], "status": "FAILURE"}
        )
        tool.session.get.side_effect = [submit_resp, failure_resp]

        out = tool.run({"operation": "search_by_smiles", "smiles": "BAD"})

        self.assertEqual(out["status"], "error")
        self.assertIn("failed", out["error"].lower())

    def test_search_compounds_unsupported(self):
        tool = _tool()
        out = tool.run({"operation": "search_compounds", "query": "aspirin"})

        self.assertEqual(out["status"], "error")
        self.assertIn("not supported", out["error"].lower())
        self.assertIn("search_by_smiles", out["error"])

    def test_search_by_properties_unsupported(self):
        tool = _tool()
        out = tool.run({"operation": "search_by_properties", "mwt_max": 500})

        self.assertEqual(out["status"], "error")
        self.assertIn("not supported", out["error"].lower())
        self.assertIn("search_by_smiles", out["error"])

    def test_unknown_operation(self):
        tool = _tool()
        out = tool.run({"operation": "bogus"})

        self.assertEqual(out["status"], "error")
        self.assertIn("available_operations", out)

    def test_missing_operation(self):
        tool = _tool()
        out = tool.run({})

        self.assertEqual(out["status"], "error")


if __name__ == "__main__":
    unittest.main()
