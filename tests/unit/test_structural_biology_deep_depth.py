"""Structural-biology-deep depth tools: parse + error-path coverage (mocked HTTP).

Covers five new tools that close confirmed structural-biology capability gaps.
All network calls are mocked; these tests never touch the live APIs.

BMRB (reused ``BaseRESTTool``, config-only via api.bmrb.io):

* ``BMRB_search_by_sequence`` (endpoint /search/fasta/{sequence}) - archive-wide
  FASTA/BLAST sequence-similarity search; flat list of hits with percent_id,
  alignment_length, e-value, bit_score.
* ``BMRB_search_chemical_shifts`` (endpoint /search/chemical_shifts) - cross-archive
  chemical-shift statistics for a comp_id/atom_id; {columns, data} table.
* ``BMRB_get_validation`` (endpoint /entry/{id}/validate) - AVS + PANAV assignment
  validation report keyed by entry id.

3D-Beacons (reused ``ThreeDBeaconsTool``, new endpoint=annotations):

* ``ThreeDBeacons_get_annotations`` - residue-level structural/functional
  annotations (DOMAIN, BINDING, etc.) with residue + region lists.

PDB-REDO (reused ``BaseRESTTool``, config-only via pdb-redo.eu):

* ``PDB_REDO_get_version_info`` (endpoint /db/{id}/versions.json) - re-refinement
  version & provenance metadata; {data, software} sections.
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


def _bmrb_tool(tool_name):
    from tooluniverse.base_rest_tool import BaseRESTTool

    return BaseRESTTool(_load_config("bmrb_tools.json", tool_name))


def _pdb_redo_tool(tool_name):
    from tooluniverse.base_rest_tool import BaseRESTTool

    return BaseRESTTool(_load_config("pdb_redo_tools.json", tool_name))


def _beacons_tool(tool_name):
    from tooluniverse.three_d_beacons_tool import ThreeDBeaconsTool

    return ThreeDBeaconsTool(_load_config("three_d_beacons_tools.json", tool_name))


def _rest_response(json_data, status_code=200, text=None):
    """Build a mock response for BaseRESTTool (request_with_retry)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = text if text is not None else json.dumps(json_data)
    resp.headers = {"content-type": "application/json"}
    return resp


def _beacons_response(json_data, status_code=200):
    """Build a mock response for ThreeDBeaconsTool (requests.get + raise_for_status)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    resp.headers = {"content-type": "application/json"}
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# BMRB_search_by_sequence
# ---------------------------------------------------------------------------


class TestBMRBSearchBySequence(unittest.TestCase):
    UBQ = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"

    HITS = [
        {
            "entry_id": "51143",
            "entity_id": "5",
            "entry_title": "H3 tail in 193-bp nucleosome",
            "percent_id": 100.0,
            "alignment_length": 76,
            "mismatches": 0,
            "gap_openings": 0,
            "q.start": 1,
            "q.end": 76,
            "s.start": 1,
            "s.end": 76,
            "e-value": 1.57e-30,
            "bit_score": 125.6,
        },
        {
            "entry_id": "6470",
            "entity_id": "1",
            "entry_title": "Rotational Diffusion Anisotropy of Human Ubiquitin",
            "percent_id": 100.0,
            "alignment_length": 76,
            "e-value": 1.57e-30,
            "bit_score": 125.6,
        },
    ]

    def test_parse_sequence_hits(self):
        """Flat hit list parses; sequence is a path param and type is a query param."""
        tool = _bmrb_tool("BMRB_search_by_sequence")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response(self.HITS),
        ) as mock_req:
            result = tool.run({"sequence": self.UBQ, "type": "polymer"})

        # The sequence is a path parameter; "type" must go through as a query param.
        called_url = mock_req.call_args[0][2]
        self.assertIn("/search/fasta/", called_url)
        self.assertIn(self.UBQ, called_url)
        sent_params = mock_req.call_args[1]["params"]
        self.assertEqual(sent_params.get("type"), "polymer")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        first = result["data"][0]
        self.assertEqual(first["entry_id"], "51143")
        self.assertEqual(first["percent_id"], 100.0)
        self.assertEqual(first["e-value"], 1.57e-30)
        self.assertEqual(first["bit_score"], 125.6)

    def test_error_path_http_500(self):
        """HTTP 500 yields an error envelope, never raises."""
        tool = _bmrb_tool("BMRB_search_by_sequence")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response({}, status_code=500, text="boom"),
        ):
            result = tool.run({"sequence": self.UBQ})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 500)


# ---------------------------------------------------------------------------
# BMRB_search_chemical_shifts
# ---------------------------------------------------------------------------


class TestBMRBSearchChemicalShifts(unittest.TestCase):
    PAYLOAD = {
        "columns": [
            "Atom_chem_shift.Entry_ID",
            "Atom_chem_shift.Entity_ID",
            "Atom_chem_shift.Entity_assembly_ID",
            "Atom_chem_shift.Comp_index_ID",
            "Atom_chem_shift.Comp_ID",
            "Atom_chem_shift.Atom_ID",
            "Atom_chem_shift.Atom_type",
            "Atom_chem_shift.Val",
        ],
        "data": [
            ["10004", 1, 1, 40, "HIS", "CA", "C", 55.462],
            ["10005", 1, 1, 12, "HIS", "CA", "C", 56.1],
        ],
    }

    def test_parse_shift_table(self):
        """columns/data table parses and query params are forwarded."""
        tool = _bmrb_tool("BMRB_search_chemical_shifts")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response(self.PAYLOAD),
        ) as mock_req:
            result = tool.run({"comp_id": "HIS", "atom_id": "CA"})

        sent_params = mock_req.call_args[1]["params"]
        self.assertEqual(sent_params.get("comp_id"), "HIS")
        self.assertEqual(sent_params.get("atom_id"), "CA")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["columns"][4], "Atom_chem_shift.Comp_ID")
        self.assertEqual(len(result["data"]["data"]), 2)
        self.assertEqual(result["data"]["data"][0][7], 55.462)

    def test_optional_shift_range_forwarded(self):
        """shift_low/shift_high are passed through as query params."""
        tool = _bmrb_tool("BMRB_search_chemical_shifts")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response(self.PAYLOAD),
        ) as mock_req:
            tool.run(
                {
                    "comp_id": "HIS",
                    "atom_id": "CA",
                    "shift_low": 54.0,
                    "shift_high": 57.0,
                }
            )
        sent_params = mock_req.call_args[1]["params"]
        self.assertEqual(sent_params.get("shift_low"), 54.0)
        self.assertEqual(sent_params.get("shift_high"), 57.0)

    def test_error_path_http_404(self):
        """HTTP 404 yields an error envelope, never raises."""
        tool = _bmrb_tool("BMRB_search_chemical_shifts")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response({}, status_code=404, text="not found"),
        ):
            result = tool.run({"comp_id": "ZZZ", "atom_id": "CA"})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 404)


# ---------------------------------------------------------------------------
# BMRB_get_validation
# ---------------------------------------------------------------------------


class TestBMRBGetValidation(unittest.TestCase):
    PAYLOAD = {
        "15000": {
            "avs": {
                "category": "AVS_analysis",
                "tags": ["Assembly_ID", "Comp_ID"],
                "data": [["1", "1", "1", "7", "ARG", "Anomalous", "Consistent"]],
            },
            "panav": {
                "0": {
                    "offsets": {"CO": -3.42, "CA": -0.19},
                    "deviants": [],
                    "suspicious": [],
                }
            },
        }
    }

    def test_parse_validation_categories(self):
        """AVS + PANAV categories parse under the entry-id key."""
        tool = _bmrb_tool("BMRB_get_validation")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response(self.PAYLOAD),
        ) as mock_req:
            result = tool.run({"entry_id": "15000"})

        called_url = mock_req.call_args[0][2]
        self.assertTrue(called_url.endswith("/entry/15000/validate"))

        self.assertEqual(result["status"], "success")
        entry = result["data"]["15000"]
        self.assertEqual(sorted(entry.keys()), ["avs", "panav"])
        self.assertEqual(entry["avs"]["category"], "AVS_analysis")
        self.assertIn("CA", entry["panav"]["0"]["offsets"])

    def test_error_path_http_500(self):
        """HTTP 500 yields an error envelope, never raises."""
        tool = _bmrb_tool("BMRB_get_validation")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response({}, status_code=500, text="server error"),
        ):
            result = tool.run({"entry_id": "999999"})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 500)


# ---------------------------------------------------------------------------
# ThreeDBeacons_get_annotations
# ---------------------------------------------------------------------------


class TestThreeDBeaconsAnnotations(unittest.TestCase):
    PAYLOAD = {
        "accession": "P38398",
        "id": "P38398",
        "sequence": "MDLSALRVE",
        "annotation": [
            {
                "type": "DOMAIN",
                "description": "BRCA1-associated (IPR031099)",
                "source_name": "InterPro",
                "evidence": "COMPUTATIONAL/PREDICTED",
                "residues": [7, 8, 9],
                "regions": [{"start": 7, "end": 99}],
            }
        ],
    }

    def test_parse_annotations(self):
        """DOMAIN annotation parses with residues and regions."""
        tool = _beacons_tool("ThreeDBeacons_get_annotations")
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get",
            return_value=_beacons_response(self.PAYLOAD),
        ) as mock_get:
            result = tool.run({"accession": "P38398", "type": "DOMAIN"})

        called_url = mock_get.call_args[0][0]
        self.assertIn("/annotations/P38398.json", called_url)
        sent_params = mock_get.call_args[1]["params"]
        self.assertEqual(sent_params.get("type"), "DOMAIN")

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["accession"], "P38398")
        self.assertEqual(data["annotation_count"], 1)
        ann = data["annotations"][0]
        self.assertEqual(ann["type"], "DOMAIN")
        self.assertEqual(ann["description"], "BRCA1-associated (IPR031099)")
        self.assertEqual(ann["source_name"], "InterPro")
        self.assertEqual(ann["regions"], [{"start": 7, "end": 99}])

    def test_list_payload_is_flattened(self):
        """A list-wrapped annotation record is flattened correctly."""
        # The API may wrap annotation records in a list; both shapes must parse.
        tool = _beacons_tool("ThreeDBeacons_get_annotations")
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get",
            return_value=_beacons_response([self.PAYLOAD]),
        ):
            result = tool.run({"accession": "P38398", "type": "DOMAIN"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["annotation_count"], 1)

    def test_invalid_type_rejected_without_network(self):
        """An invalid type is rejected before any HTTP call."""
        tool = _beacons_tool("ThreeDBeacons_get_annotations")
        with patch("tooluniverse.three_d_beacons_tool.requests.get") as mock_get:
            result = tool.run({"accession": "P38398", "type": "NOTREAL"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid annotation type", result["error"])
        mock_get.assert_not_called()

    def test_error_path_404(self):
        """A 404 / HTTP error yields an error envelope, never raises."""
        import requests as _requests

        tool = _beacons_tool("ThreeDBeacons_get_annotations")
        err_resp = MagicMock()
        err_resp.status_code = 404
        http_err = _requests.exceptions.HTTPError(response=err_resp)
        with patch(
            "tooluniverse.three_d_beacons_tool.requests.get",
            side_effect=http_err,
        ):
            result = tool.run({"accession": "NONEXISTENT"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# PDB_REDO_get_version_info
# ---------------------------------------------------------------------------


class TestPDBRedoVersionInfo(unittest.TestCase):
    PAYLOAD = {
        "data": {
            "PDBID": "1cbs",
            "coordinates_revision_major_mmCIF": "1",
            "coordinates_revision_minor_mmCIF": "3",
            "coordinates_edited": False,
            "reflections_revision": "1_1",
            "reflections_edited": False,
            "foldit_used": False,
            "foldit_id": None,
            "foldit_player": None,
        },
        "software": {
            "pdb-redo": {"version": "8.21", "used": True},
            "WHAT_CHECK": {"version": "15.0", "used": True},
        },
    }

    def test_parse_version_info(self):
        """data + software provenance sections parse correctly."""
        tool = _pdb_redo_tool("PDB_REDO_get_version_info")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response(self.PAYLOAD),
        ) as mock_req:
            result = tool.run({"pdb_id": "1cbs"})

        called_url = mock_req.call_args[0][2]
        self.assertTrue(called_url.endswith("/db/1cbs/versions.json"))

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(sorted(data.keys()), ["data", "software"])
        self.assertEqual(data["software"]["pdb-redo"]["version"], "8.21")
        self.assertEqual(data["data"]["coordinates_revision_major_mmCIF"], "1")
        self.assertEqual(data["data"]["coordinates_revision_minor_mmCIF"], "3")
        self.assertFalse(data["data"]["foldit_used"])

    def test_error_path_404(self):
        """A 404 / HTTP error yields an error envelope, never raises."""
        tool = _pdb_redo_tool("PDB_REDO_get_version_info")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_rest_response({}, status_code=404, text="not found"),
        ):
            result = tool.run({"pdb_id": "zzzz"})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
