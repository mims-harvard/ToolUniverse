"""Structure-prediction-modeling depth tools: parse + error-path coverage (mocked HTTP).

Covers three confirmed capability gaps in the SWISS-MODEL Repository tools.
Each tool REUSES the existing registered ``SwissModelTool`` class (no new
@register_tool, no registration changes) — only the ``fields.endpoint_type``
dispatch field differs:

* ``SwissModel_download_pdb`` (endpoint_type=download_pdb) — fetches the actual
  3D atomic coordinates (ATOM/HETATM records) as PDB text, with optional
  sort/provider/template/range selectors. The pre-existing SwissModel tools
  return only JSON metadata + a coordinates URL string they never fetch.
* ``SwissModel_get_models_batch`` (endpoint_type=get_models_batch) — batch
  lookup of up to 250 UniProt accessions in one call via the comma-separated
  ``/uniprot/{identifiers}.json`` path (top-level ``resultset`` array).
* ``SwissModel_get_models`` (endpoint_type=get_models) — extended with
  range/provider/template query-string filters.

All network calls are mocked; these tests never touch the live API.
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


def _load_config(json_file: str, tool_name: str) -> dict:
    with open(os.path.join(_DATA_DIR, json_file)) as f:
        configs = json.load(f)
    for cfg in configs:
        if cfg.get("name") == tool_name:
            return cfg
    raise AssertionError(f"{tool_name} not found in {json_file}")


def _swissmodel_tool(tool_name: str):
    from tooluniverse.swissmodel_tool import SwissModelTool

    return SwissModelTool(_load_config("swissmodel_tools.json", tool_name))


# ---------------------------------------------------------------------------
# SwissModel_download_pdb
# ---------------------------------------------------------------------------

_PDB_FAKE = (
    "TITLE     SWISS-MODEL SERVER (https://swissmodel.expasy.org)\n"
    "TITLE    2 Untitled Project\n"
    "REMARK   1 MODEL\n"
    "ATOM      1  N   LYS A  19     223.948 191.306 174.848  1.00 14.87           N\n"
    "ATOM      2  CA  LYS A  19     223.198 191.371 173.597  1.00 14.87           C\n"
    "ATOM      3  C   LYS A  19     221.869 190.626 173.647  1.00 14.87           C\n"
    "HETATM    4  ZN  ZN  A 201     220.000 190.000 173.000  1.00 10.00          ZN\n"
    "END\n"
)


class TestSwissModelDownloadPdb(unittest.TestCase):
    def test_parse_pdb_coordinates(self):
        """ATOM/HETATM records are counted and returned as raw PDB text."""
        tool = _swissmodel_tool("SwissModel_download_pdb")
        mock_resp = MagicMock()
        mock_resp.text = _PDB_FAKE
        mock_resp.headers = {"Content-Type": "text/plain; charset=ASCII"}
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp):
            result = tool.run({"uniprot_id": "P04637", "provider": "swissmodel"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["format"], "pdb")
        # 3 ATOM + 1 HETATM
        self.assertEqual(data["atom_count"], 4)
        self.assertIn("ATOM      1  N   LYS A  19", data["pdb_content"])
        self.assertTrue(data["size_bytes"] > 0)
        # Filter echoed back so the agent knows the scope
        self.assertEqual(data["filters_applied"], {"provider": "swissmodel"})
        self.assertEqual(result["metadata"]["endpoint"], "download_pdb")

    def test_filters_forwarded_as_query_params(self):
        """sort/provider/template/range are forwarded as request params."""
        tool = _swissmodel_tool("SwissModel_download_pdb")
        mock_resp = MagicMock()
        mock_resp.text = _PDB_FAKE
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp
        ) as mget:
            tool.run(
                {
                    "uniprot_id": "P00533",
                    "sort": "seqid",
                    "provider": "pdb",
                    "template": "2j6m.1.A",
                    "range": "94-312",
                }
            )
        _, kwargs = mget.call_args
        self.assertEqual(
            kwargs["params"],
            {
                "sort": "seqid",
                "provider": "pdb",
                "template": "2j6m.1.A",
                "range": "94-312",
            },
        )

    def test_empty_coordinates_is_error(self):
        """A response with no ATOM/HETATM records returns status=error."""
        tool = _swissmodel_tool("SwissModel_download_pdb")
        mock_resp = MagicMock()
        mock_resp.text = "TITLE     nothing here\nEND\n"
        mock_resp.headers = {"Content-Type": "text/plain"}
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp):
            result = tool.run({"uniprot_id": "P04637", "provider": "pdb"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No atomic coordinates", result["error"])

    def test_missing_id_is_error(self):
        """A call with no uniprot_id returns status=error."""
        tool = _swissmodel_tool("SwissModel_download_pdb")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("uniprot_id", result["error"])

    def test_error_path_never_raises(self):
        """A network failure is caught and returned as a status=error envelope."""
        tool = _swissmodel_tool("SwissModel_download_pdb")
        with patch(
            "tooluniverse.swissmodel_tool.requests.get",
            side_effect=RuntimeError("boom network"),
        ):
            result = tool.run({"uniprot_id": "P04637"})
        self.assertEqual(result["status"], "error")
        self.assertIn("boom network", result["error"])


# ---------------------------------------------------------------------------
# SwissModel_get_models_batch
# ---------------------------------------------------------------------------

_BATCH_FAKE = {
    "api_version": "2.0",
    "query": {"identifiers": "P04637,P00533,P38398"},
    "resultset": [
        {
            "crc64": "AD5C149FD8106131",
            "sequence_length": 393,
            "uniprot_entries": [{"ac": "P04637", "id": "P53_HUMAN"}],
            "structures": [
                {
                    "template": "2j6m.1.A",
                    "method": "Homology",
                    "coverage": 0.86,
                    "from": 12,
                    "to": 351,
                    "provider": "SWISSMODEL",
                    "coordinates": "https://swissmodel.expasy.org/repository/uniprot/P04637.pdb?range=12-351",
                    "qmean": {"qmean4_global_score": 0.7, "qmean_z_score": -1.1},
                }
            ],
        },
        {
            "crc64": "BBBB",
            "sequence_length": 1210,
            "uniprot_entries": [{"ac": "P00533", "id": "EGFR_HUMAN"}],
            "structures": [
                {"template": "3w2s.1.A", "method": "PDB", "provider": "PDB"},
                {"template": "5x2f.1.A", "method": "PDB", "provider": "PDB"},
            ],
        },
        {
            "crc64": "CCCC",
            "sequence_length": 1863,
            "uniprot_entries": [{"ac": "P38398", "id": "BRCA1_HUMAN"}],
            "structures": [],
        },
    ],
}


class TestSwissModelGetModelsBatch(unittest.TestCase):
    def test_parse_resultset(self):
        """Each resultset entry is flattened with its accession and model count."""
        tool = _swissmodel_tool("SwissModel_get_models_batch")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _BATCH_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch("tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp):
            result = tool.run(
                {"uniprot_ids": ["P04637", "P00533", "P38398"]}
            )

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["requested_count"], 3)
        self.assertEqual(data["returned_count"], 3)
        by_ac = {r["uniprot_ids"][0]: r for r in data["results"]}
        self.assertEqual(by_ac["P04637"]["model_count"], 1)
        self.assertEqual(by_ac["P00533"]["model_count"], 2)
        self.assertEqual(by_ac["P38398"]["model_count"], 0)
        # Flattened model keeps template + coordinates URL
        m = by_ac["P04637"]["models"][0]
        self.assertEqual(m["template"], "2j6m.1.A")
        self.assertEqual(m["provider"], "SWISSMODEL")
        self.assertIn("P04637.pdb", m["coordinates_url"])
        self.assertEqual(m["qmean_global"], 0.7)

    def test_comma_string_accepted(self):
        """A comma-separated string is split into the joined identifiers path."""
        tool = _swissmodel_tool("SwissModel_get_models_batch")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _BATCH_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp
        ) as mget:
            result = tool.run({"uniprot_ids": "P04637, P00533, P38398"})
        self.assertEqual(result["status"], "success")
        called_url = mget.call_args[0][0]
        self.assertIn("P04637,P00533,P38398.json", called_url)

    def test_empty_ids_is_error(self):
        """An empty accession list returns status=error."""
        tool = _swissmodel_tool("SwissModel_get_models_batch")
        result = tool.run({"uniprot_ids": []})
        self.assertEqual(result["status"], "error")
        self.assertIn("uniprot_ids", result["error"])

    def test_too_many_ids_is_error(self):
        """More than 250 accessions returns status=error (batch limit)."""
        tool = _swissmodel_tool("SwissModel_get_models_batch")
        result = tool.run({"uniprot_ids": [f"P{i:05d}" for i in range(251)]})
        self.assertEqual(result["status"], "error")
        self.assertIn("250", result["error"])

    def test_error_path_never_raises(self):
        """A network failure is caught and returned as a status=error envelope."""
        tool = _swissmodel_tool("SwissModel_get_models_batch")
        with patch(
            "tooluniverse.swissmodel_tool.requests.get",
            side_effect=RuntimeError("batch boom"),
        ):
            result = tool.run({"uniprot_ids": ["P04637"]})
        self.assertEqual(result["status"], "error")
        self.assertIn("batch boom", result["error"])


# ---------------------------------------------------------------------------
# SwissModel_get_models  (range / provider / template filters)
# ---------------------------------------------------------------------------

_MODELS_FAKE = {
    "api_version": "2.0",
    "query": {"ac": "P04637", "from": 94, "to": 312, "identifiers": "P04637"},
    "result": {
        "crc64": "AD5C149FD8106131",
        "sequence_length": 393,
        "structures": [
            {
                "template": "2j6m.1.A",
                "method": "Homology",
                "coverage": 0.55,
                "from": 94,
                "to": 312,
                "provider": "SWISSMODEL",
                "coordinates": "https://swissmodel.expasy.org/repository/uniprot/P04637.pdb",
                "qmean": {"qmean4_global_score": 0.68, "qmean_z_score": -1.3},
            }
        ],
    },
}


class TestSwissModelGetModelsFilters(unittest.TestCase):
    def test_range_filter_forwarded_and_echoed(self):
        """range/provider/template are sent as params and echoed in filters_applied."""
        tool = _swissmodel_tool("SwissModel_get_models")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _MODELS_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp
        ) as mget:
            result = tool.run(
                {"uniprot_id": "P04637", "range": "94-312", "provider": "swissmodel"}
            )

        self.assertEqual(result["status"], "success")
        _, kwargs = mget.call_args
        self.assertEqual(
            kwargs["params"], {"range": "94-312", "provider": "swissmodel"}
        )
        data = result["data"]
        self.assertEqual(data["model_count"], 1)
        self.assertEqual(
            data["filters_applied"], {"range": "94-312", "provider": "swissmodel"}
        )
        # Coordinates URL now surfaced in the flattened model
        self.assertIn("P04637.pdb", data["models"][0]["coordinates_url"])

    def test_no_filters_sends_no_params(self):
        """An unfiltered call passes params=None (no query string)."""
        tool = _swissmodel_tool("SwissModel_get_models")
        mock_resp = MagicMock()
        mock_resp.json.return_value = _MODELS_FAKE
        mock_resp.raise_for_status.return_value = None

        with patch(
            "tooluniverse.swissmodel_tool.requests.get", return_value=mock_resp
        ) as mget:
            result = tool.run({"uniprot_id": "P04637"})
        self.assertEqual(result["status"], "success")
        self.assertNotIn("filters_applied", result["data"])
        _, kwargs = mget.call_args
        self.assertIsNone(kwargs["params"])

    def test_missing_id_is_error(self):
        """A call with no uniprot_id returns status=error."""
        tool = _swissmodel_tool("SwissModel_get_models")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("uniprot_id", result["error"])

    def test_error_path_never_raises(self):
        """A network failure is caught and returned as a status=error envelope."""
        tool = _swissmodel_tool("SwissModel_get_models")
        with patch(
            "tooluniverse.swissmodel_tool.requests.get",
            side_effect=RuntimeError("models boom"),
        ):
            result = tool.run({"uniprot_id": "P04637", "range": "94-312"})
        self.assertEqual(result["status"], "error")
        self.assertIn("models boom", result["error"])


if __name__ == "__main__":
    unittest.main()
