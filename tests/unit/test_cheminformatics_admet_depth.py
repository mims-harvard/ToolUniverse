"""Cheminformatics / ADMET depth tools (mocked HTTP, no live calls).

Covers four new tools that reuse existing tool classes (no new @register_tool
class, no registration changes):

  - PubChemBioAssay_get_concise_activity_table
        (PubChemBioAssayTool, endpoint=concise_activity_table)
  - UniChem_connectivity_search
        (UniChemTool, endpoint_type=connectivity_search)
  - PubChemTox_get_ecotoxicity_values
        (PubChemToxTool, endpoint=ecotoxicity_values)
  - PubChemTox_get_human_toxicity_values
        (PubChemToxTool, endpoint=human_toxicity_values)

Each tool gets a parse (success) test and an error-path test.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit


def _json_resp(status_code, body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.url = "https://example.test/url"
    r.raise_for_status = MagicMock()
    return r


# --------------------------------------------------------------------------- #
# PubChemBioAssay_get_concise_activity_table
# --------------------------------------------------------------------------- #
class TestBioAssayConciseTable(unittest.TestCase):
    def _tool(self):
        from tooluniverse.pubchem_bioassay_tool import PubChemBioAssayTool

        return PubChemBioAssayTool(
            {
                "name": "PubChemBioAssay_get_concise_activity_table",
                "type": "PubChemBioAssayTool",
                "fields": {"endpoint": "concise_activity_table"},
            }
        )

    _BODY = {
        "Table": {
            "Columns": {
                "Column": [
                    "AID",
                    "SID",
                    "CID",
                    "Activity Outcome",
                    "Target Accession",
                    "Target GeneID",
                    "Activity Value [uM]",
                    "Activity Name",
                ]
            },
            "Row": [
                {
                    "Cell": [
                        "504832",
                        "842131",
                        "6602565",
                        "Active",
                        "ACC1",
                        "12345",
                        "6.5733",
                        "Potency",
                    ]
                },
                {
                    "Cell": [
                        "504832",
                        "842132",
                        "6602566",
                        "Inactive",
                        "ACC1",
                        "12345",
                        "",
                        "Potency",
                    ]
                },
                {
                    "Cell": [
                        "504832",
                        "842133",
                        "6602567",
                        "Inactive",
                        "ACC1",
                        "12345",
                        "",
                        "Potency",
                    ]
                },
            ],
        }
    }

    def test_parse_rows_and_total(self):
        """Concise table maps columns->cells and reports total/returned rows."""
        with patch(
            "tooluniverse.pubchem_bioassay_tool.requests.get",
            return_value=_json_resp(200, self._BODY),
        ):
            out = self._tool().run({"aid": 504832, "max_rows": 2})
        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["total_rows"], 3)
        self.assertEqual(data["returned_rows"], 2)
        self.assertEqual(len(data["rows"]), 2)
        self.assertIn("Activity Value [uM]", data["columns"])
        row0 = data["rows"][0]
        self.assertEqual(row0["SID"], "842131")
        self.assertEqual(row0["CID"], "6602565")
        self.assertEqual(row0["Activity Outcome"], "Active")
        self.assertEqual(row0["Activity Value [uM]"], "6.5733")
        self.assertTrue(out["metadata"]["truncated"])

    def test_missing_aid_error(self):
        """Missing aid returns a structured error, never raises."""
        out = self._tool().run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("aid", out["error"].lower())

    def test_empty_table_error(self):
        """An empty concise table yields a structured error."""
        with patch(
            "tooluniverse.pubchem_bioassay_tool.requests.get",
            return_value=_json_resp(200, {"Table": {}}),
        ):
            out = self._tool().run({"aid": 99999999})
        self.assertEqual(out["status"], "error")

    def test_http_error_path(self):
        """HTTP errors are caught and returned as status=error."""
        resp = _json_resp(404, {})
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404", response=MagicMock(status_code=404)
        )
        with patch(
            "tooluniverse.pubchem_bioassay_tool.requests.get", return_value=resp
        ):
            out = self._tool().run({"aid": 1259393})
        self.assertEqual(out["status"], "error")


# --------------------------------------------------------------------------- #
# UniChem_connectivity_search
# --------------------------------------------------------------------------- #
class TestUniChemConnectivitySearch(unittest.TestCase):
    def _tool(self):
        from tooluniverse.unichem_tool import UniChemTool

        return UniChemTool(
            {
                "name": "UniChem_connectivity_search",
                "type": "UniChemTool",
                "fields": {"endpoint_type": "connectivity_search"},
            }
        )

    _BODY = {
        "response": "Success",
        "searchedCompound": {
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "standardInchiKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "uci": 161671,
        },
        "totalCompounds": 15,
        "totalSources": 1044,
        "sources": [
            {
                "id": 1,
                "shortName": "chembl",
                "longName": "ChEMBL",
                "compoundId": "CHEMBL25",
                "typeOfSearch": "match",
                "url": "https://www.ebi.ac.uk/chembldb/compound/inspect/CHEMBL25",
                "comparison": {
                    "charge": True,
                    "connectivity": True,
                    "formula": True,
                    "isotope": True,
                    "protonation": True,
                    "stereoDbond": True,
                    "HAtoms": True,
                },
            },
            {
                "id": 22,
                "shortName": "pubchem",
                "longName": "PubChem",
                "compoundId": "2244",
                "typeOfSearch": "match",
                "url": None,
                "comparison": {
                    "charge": True,
                    "connectivity": True,
                    "formula": True,
                    "isotope": True,
                    "protonation": True,
                    "stereoDbond": True,
                    "HAtoms": True,
                },
            },
        ],
    }

    def test_parse_matches_and_comparison(self):
        """Connectivity search exposes per-match comparison flags + totals."""
        with patch(
            "tooluniverse.unichem_tool.requests.post",
            return_value=_json_resp(200, self._BODY),
        ):
            out = self._tool().run(
                {"compound": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "type": "inchikey"}
            )
        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["response"], "Success")
        self.assertEqual(data["total_compounds"], 15)
        self.assertEqual(data["total_sources"], 1044)
        self.assertEqual(data["match_count"], 2)
        self.assertEqual(
            data["searched_compound"]["inchikey"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        )
        m0 = data["matches"][0]
        self.assertEqual(m0["source_name"], "chembl")
        self.assertEqual(m0["compound_id"], "CHEMBL25")
        self.assertIn("charge", m0["comparison"])
        self.assertIn("stereoDbond", m0["comparison"])

    def test_missing_compound_error(self):
        """Missing compound returns a structured error, never raises."""
        out = self._tool().run({"type": "inchikey"})
        self.assertEqual(out["status"], "error")
        self.assertIn("compound", out["error"].lower())

    def test_connection_error_path(self):
        """Network failure is caught and returned as status=error."""
        with patch(
            "tooluniverse.unichem_tool.requests.post",
            side_effect=requests.exceptions.ConnectionError("down"),
        ):
            out = self._tool().run(
                {"compound": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "type": "inchikey"}
            )
        self.assertEqual(out["status"], "error")


# --------------------------------------------------------------------------- #
# Shared PUG View body builder for PubChemTox tests
# --------------------------------------------------------------------------- #
def _pugview_body(heading, values):
    return {
        "Record": {
            "RecordTitle": "Benzene",
            "Section": [
                {
                    "TOCHeading": "Ecological Information",
                    "Section": [
                        {
                            "TOCHeading": heading,
                            "Information": [
                                {"Value": {"StringWithMarkup": [{"String": v}]}}
                                for v in values
                            ],
                        }
                    ],
                }
            ],
        }
    }


# --------------------------------------------------------------------------- #
# PubChemTox_get_ecotoxicity_values
# --------------------------------------------------------------------------- #
class TestEcotoxicityValues(unittest.TestCase):
    def _tool(self):
        from tooluniverse.pubchem_tox_tool import PubChemToxTool

        return PubChemToxTool(
            {
                "name": "PubChemTox_get_ecotoxicity_values",
                "type": "PubChemToxTool",
                "fields": {"endpoint": "ecotoxicity_values"},
            }
        )

    def test_parse_ecotoxicity_values(self):
        """Ecotoxicity LC50 strings are extracted from the heading."""
        body = _pugview_body(
            "Ecotoxicity Values",
            [
                "LC50; Species: Palaemonetes pugio (grass shrimp); Concentration: 27 ppm for 96 hr",
                "LC50; Species: Cancer magister (crab larvae) stage 1; Concentration: 108 ppm for 96 hr",
            ],
        )
        with patch(
            "tooluniverse.pubchem_tox_tool.requests.get",
            return_value=_json_resp(200, body),
        ):
            out = self._tool().run({"cid": 241})
        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["cid"], 241)
        self.assertEqual(data["ecotoxicity_values_count"], 2)
        self.assertTrue(any("grass shrimp" in v for v in data["ecotoxicity_values"]))

    def test_no_id_error(self):
        """Neither cid nor compound_name yields a structured error."""
        out = self._tool().run({})
        self.assertEqual(out["status"], "error")

    def test_http_404_error_path(self):
        """404 (heading absent) returns a structured error, never raises."""
        resp = _json_resp(404, {})
        http_err = requests.exceptions.HTTPError("404")
        http_err.response = MagicMock(status_code=404)
        resp.raise_for_status.side_effect = http_err
        with patch("tooluniverse.pubchem_tox_tool.requests.get", return_value=resp):
            out = self._tool().run({"cid": 241})
        self.assertEqual(out["status"], "error")


# --------------------------------------------------------------------------- #
# PubChemTox_get_human_toxicity_values
# --------------------------------------------------------------------------- #
class TestHumanToxicityValues(unittest.TestCase):
    def _tool(self):
        from tooluniverse.pubchem_tox_tool import PubChemToxTool

        return PubChemToxTool(
            {
                "name": "PubChemTox_get_human_toxicity_values",
                "type": "PubChemToxTool",
                "fields": {"endpoint": "human_toxicity_values"},
            }
        )

    def test_parse_human_toxicity_values(self):
        """Human lethal-dose / IDLH strings are extracted from the heading."""
        body = _pugview_body(
            "Human Toxicity Values",
            [
                "Estimated oral doses from 9-30 g have proved fatal.",
                "Immediately dangerous to life and health = 500 ppm",
            ],
        )
        with patch(
            "tooluniverse.pubchem_tox_tool.requests.get",
            return_value=_json_resp(200, body),
        ):
            out = self._tool().run({"cid": 241})
        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["human_toxicity_values_count"], 2)
        self.assertTrue(
            any("Immediately dangerous" in v for v in data["human_toxicity_values"])
        )

    def test_no_id_error(self):
        """Neither cid nor compound_name yields a structured error."""
        out = self._tool().run({})
        self.assertEqual(out["status"], "error")

    def test_connection_error_path(self):
        """Network failure is caught and returned as status=error."""
        with patch(
            "tooluniverse.pubchem_tox_tool.requests.get",
            side_effect=requests.exceptions.ConnectionError("down"),
        ):
            out = self._tool().run({"cid": 241})
        self.assertEqual(out["status"], "error")


if __name__ == "__main__":
    unittest.main()
