"""Compound-bioactivity-screening depth tools: parse + error-path coverage (mocked HTTP).

Covers three new tools that close confirmed capability gaps for the
compound-bioactivity-screening cluster. All three reuse existing registered
tool classes (no new @register_tool class), dispatched by the ``operation`` field.

* ``PharmacoDB_get_drug_targets`` (PharmacoDBTool / get_drug_targets) — drug-target
  relationships in three directions: gene->targets (single_gene_target),
  compound->targets (single_compound_target), and the full paginated drug-target
  table (all_compound_targets).
* ``PharmacoDB_get_molecular_profiling`` (PharmacoDBTool / get_molecular_profiling)
  — per-cell-line molecular profiling inventory (which omics layers exist per dataset).
* ``SYNERGxDB_get_biomarker_association`` (SYNERGxDBTool / get_biomarker_association)
  — per-cell-line gene expression (FPKM) vs drug-combination synergy scores.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pharmacodb_tool():
    from tooluniverse.pharmacodb_tool import PharmacoDBTool

    return PharmacoDBTool({"name": "PharmacoDBTool", "parameter": {}})


def _synergxdb_tool():
    from tooluniverse.synergxdb_tool import SYNERGxDBTool

    return SYNERGxDBTool({"name": "SYNERGxDBTool", "parameter": {}})


def _mock_post(json_payload, status_code=200):
    """Build a MagicMock requests.Response-like object for requests.post."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_payload
    resp.text = ""
    return resp


# ---------------------------------------------------------------------------
# PharmacoDB_get_drug_targets
# ---------------------------------------------------------------------------


class TestPharmacoDBGetDrugTargets(unittest.TestCase):
    def test_gene_direction_parses_targets(self):
        """gene_name -> single_gene_target returns gene_id + targets list."""
        tool = _pharmacodb_tool()
        payload = {
            "data": {
                "single_gene_target": {
                    "gene_id": 8931,
                    "gene_name": "ENSG00000146648",
                    "targets": [
                        {"target_id": 67, "target_name": "Epidermal growth factor receptor erbB1"},
                        {"target_id": 1226, "target_name": "Epidermal growth factor receptor"},
                    ],
                }
            }
        }
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run({"operation": "get_drug_targets", "gene_name": "EGFR"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["direction"], "single_gene_target")
        self.assertEqual(data["gene_id"], 8931)
        self.assertEqual(data["num_targets"], 2)
        self.assertEqual(data["targets"][0]["target_id"], 67)

    def test_compound_direction_parses_targets(self):
        """compound_name -> single_compound_target returns compound_id + targets."""
        tool = _pharmacodb_tool()
        payload = {
            "data": {
                "single_compound_target": {
                    "compound_id": 49658,
                    "compound_name": "Paclitaxel",
                    "targets": [
                        {"target_id": 2, "target_name": "Cytochrome P450 2C9"},
                        {"target_id": 899, "target_name": "Tubulin beta-3 chain"},
                    ],
                }
            }
        }
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run(
                {"operation": "get_drug_targets", "compound_name": "paclitaxel"}
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["direction"], "single_compound_target")
        self.assertEqual(data["compound_id"], 49658)
        self.assertEqual(data["num_targets"], 2)

    def test_full_table_client_side_pagination(self):
        """No gene/compound -> all_compound_targets, paginated client-side."""
        tool = _pharmacodb_tool()
        rows = [
            {"compound_id": 18, "compound_name": "acid A",
             "targets": [{"target_id": 1, "target_name": "Cytochrome P450 2C19"}]},
            {"compound_id": 32, "compound_name": "acid B",
             "targets": [{"target_id": 2, "target_name": "Cytochrome P450 2C9"}]},
            {"compound_id": 38, "compound_name": "acid C",
             "targets": [{"target_id": 4, "target_name": "ERAB protein"}]},
        ]
        payload = {"data": {"all_compound_targets": rows}}
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run({"operation": "get_drug_targets", "per_page": 2, "page": 1})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["direction"], "all_compound_targets")
        self.assertEqual(data["num_returned"], 2)
        self.assertEqual(data["total_available"], 3)
        self.assertEqual(data["compound_targets"][0]["compound_id"], 18)
        # Page 2 returns the remaining row.
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            page2 = tool.run({"operation": "get_drug_targets", "per_page": 2, "page": 2})
        self.assertEqual(page2["data"]["num_returned"], 1)
        self.assertEqual(page2["data"]["compound_targets"][0]["compound_id"], 38)

    def test_gene_not_found_returns_error(self):
        """Null single_gene_target -> structured error (no exception)."""
        tool = _pharmacodb_tool()
        payload = {"data": {"single_gene_target": None}}
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run(
                {"operation": "get_drug_targets", "gene_name": "NOTAGENE"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("gene", result["error"].lower())

    def test_http_error_returns_error_not_raise(self):
        """Non-200 HTTP -> error envelope, never raises."""
        tool = _pharmacodb_tool()
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post({}, status_code=500)
            result = tool.run({"operation": "get_drug_targets", "gene_name": "EGFR"})
        self.assertEqual(result["status"], "error")
        self.assertIn("500", result["error"])


# ---------------------------------------------------------------------------
# PharmacoDB_get_molecular_profiling
# ---------------------------------------------------------------------------


class TestPharmacoDBGetMolecularProfiling(unittest.TestCase):
    def test_parses_profiling_inventory(self):
        """cell_line_name -> list of {dataset, mDataType, num_prof} records."""
        tool = _pharmacodb_tool()
        payload = {
            "data": {
                "molecular_profiling": [
                    {"cell_line": {"id": 273, "name": "MCF-7"},
                     "dataset": {"id": 1, "name": "CCLE"},
                     "mDataType": "Kallisto_0.46.1.rnaseq", "num_prof": 1},
                    {"cell_line": {"id": 273, "name": "MCF-7"},
                     "dataset": {"id": 1, "name": "CCLE"},
                     "mDataType": "mutation", "num_prof": 1},
                ]
            }
        }
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run(
                {"operation": "get_molecular_profiling", "cell_line_name": "MCF-7"}
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["num_records"], 2)
        self.assertEqual(data["profiling"][0]["mDataType"], "Kallisto_0.46.1.rnaseq")
        self.assertEqual(data["profiling"][1]["dataset"]["name"], "CCLE")

    def test_missing_cell_line_returns_error(self):
        """No cell line input -> structured error before any network call."""
        tool = _pharmacodb_tool()
        result = tool.run({"operation": "get_molecular_profiling"})
        self.assertEqual(result["status"], "error")
        self.assertIn("cell_line", result["error"].lower())

    def test_empty_profiling_returns_error(self):
        """Empty molecular_profiling list -> structured error."""
        tool = _pharmacodb_tool()
        payload = {"data": {"molecular_profiling": []}}
        with patch("tooluniverse.pharmacodb_tool.requests.post") as post:
            post.return_value = _mock_post(payload)
            result = tool.run(
                {"operation": "get_molecular_profiling", "cell_line_name": "NOPE"}
            )
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# SYNERGxDB_get_biomarker_association
# ---------------------------------------------------------------------------


class TestSYNERGxDBGetBiomarkerAssociation(unittest.TestCase):
    def test_parses_fpkm_vs_synergy_rows(self):
        """gene -> per-cell-line FPKM + bliss/loewe/hsa/zip rows."""
        tool = _synergxdb_tool()
        rows = [
            {"fpkm": 0, "cellName": "451Lu", "bliss": -0.9768,
             "loewe": -0.1676, "hsa": -0.1885, "zip": None},
            {"fpkm": 0, "cellName": "A2058", "bliss": -1.365,
             "loewe": -0.259, "hsa": -0.628, "zip": -0.498},
        ]
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = rows
        with patch.object(tool.session, "get", return_value=resp) as get:
            result = tool.run(
                {"operation": "get_biomarker_association", "gene": "EGFR"}
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["gene"], "EGFR")
        self.assertEqual(result["data"][1]["cellName"], "A2058")
        # gene was forwarded as a query param.
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["gene"], "EGFR")

    def test_unknown_gene_returns_empty_with_message(self):
        """Object response {message:...} -> empty success list + message."""
        tool = _synergxdb_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"message": "No data found for a given set of parameters"}
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "get_biomarker_association", "gene": "NOTAGENE123"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["data"], [])
        self.assertIn("No biomarker association", result["message"])

    def test_missing_gene_returns_error(self):
        """No gene -> structured error before any network call."""
        tool = _synergxdb_tool()
        result = tool.run({"operation": "get_biomarker_association"})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene", result["error"].lower())

    def test_gene_name_alias(self):
        """gene_name alias is accepted in place of gene."""
        tool = _synergxdb_tool()
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [{"fpkm": 1, "cellName": "NCI-H460",
                                   "bliss": -0.97, "loewe": -0.19,
                                   "hsa": -0.24, "zip": -0.3}]
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "get_biomarker_association", "gene_name": "BRAF"}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["gene"], "BRAF")

    def test_server_error_returns_error_not_raise(self):
        """HTTP 500 -> error envelope, never raises."""
        tool = _synergxdb_tool()
        resp = MagicMock()
        resp.status_code = 500
        resp.json.return_value = {}
        resp.text = "Internal Server Error"
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"operation": "get_biomarker_association", "gene": "EGFR"}
            )
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
