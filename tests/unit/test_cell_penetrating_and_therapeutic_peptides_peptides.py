"""Offline, mocked unit tests for the IIITD peptide-resource tools.

Covers the four new tools in the cell-penetrating-and-therapeutic-peptides
area, each with a success-parse path and an error path:

- Hemolytik2SearchPeptidesTool (Hemolytik2_search_peptides)
- CancerPPD2SearchPeptidesTool (CancerPPD2_search_peptides)
- PEPlife2SearchPeptidesTool (PEPlife2_search_peptides)
- TumorHope2SearchPeptidesTool (TumorHope2_search_peptides)

The HTTP layer (requests.get) is mocked so the tests are deterministic and
run without network access.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

from tooluniverse.hemolytik2_tool import (  # noqa: E402
    Hemolytik2SearchPeptidesTool,
)
from tooluniverse.cancerppd2_tool import (  # noqa: E402
    CancerPPD2SearchPeptidesTool,
)
from tooluniverse.peplife2_tool import (  # noqa: E402
    PEPlife2SearchPeptidesTool,
)
from tooluniverse.tumorhope2_tool import (  # noqa: E402
    TumorHope2SearchPeptidesTool,
)


def _mock_response(json_value=None, status_code=200, raise_json=False, url="https://example.org"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.text = "" if json_value is not None else "<html>error</html>"
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_value
    return resp


# --- Sample payloads mirroring the live API shapes ------------------------

_HEMOLYTIK_PAYLOAD = {
    "status": 200,
    "count": 2,
    "data": [
        {
            "id": "2571",
            "pmid": "23609760",
            "year": "2013",
            "seq": "FVDLKKIANIINSIFKK",
            "name": "LK1",
            "cter": "Free",
            "nter": "Free",
            "lyn_cyc": "Linear",
            "ldmix": "L",
            "non_nat": "None",
            "length": None,
            "nature": "Anticancer",
            "activity": "LC50 =1,467 micromolar",
            "source": "Human",
            "origin": "Temporin-1CEa (Rana chensinensis)",
            "exp_str": "NA",
            "non_hem": "NA",
        },
        {
            "id": "2572",
            "seq": "FKDLKKIANIINSIFKK",
            "nature": "Anticancer",
            "source": "Human",
        },
    ],
}

_CANCERPPD_PAYLOAD = {
    "status": 200,
    "count": 1,
    "data": [
        {
            "id": "6879",
            "pmid": "34135370",
            "year": "2021",
            "seq": "FIHHIFRGIVHAGRSIGRFLTG",
            "name": "Piscidin 3",
            "length": "22",
            "lin_cyc": "Linear",
            "chiral": "L",
            "chem_mod": "Cu2+ bound",
            "cter": "Free",
            "nter": "Free",
            "cell_line": "HT-1080",
            "cancer_type": "Fibrosarcoma",
            "assay": "MTT assay",
            "test_time": "24-h",
            "tissue": "Not Available",
        }
    ],
}

_PEPLIFE_PAYLOAD = {
    "status": 200,
    "count": 1,
    "data": [
        {
            "id": "1001",
            "pmid": "20844765",
            "year": "2010",
            "seq": "RRWQWR",
            "name": "Lfc1",
            "length": None,
            "lin_cyc": "Linear",
            "chiral": "L",
            "chem_mod": "None",
            "cter": "Free",
            "nter": "Free",
            "origin": "Bovine lactoferricin",
            "nature": "Antimicrobial",
            "incubation_time": "9 hours",
            "conc": "5 uM",
            "half_life": "<30",
            "units_half": "minutes",
            "protease": "Human serum proteases",
            "assay": "RP-HPLC",
        }
    ],
}

_TUMORHOPE_PAYLOAD = {
    "status": "success",
    "message": "Data retrieved successfully",
    "count": 1,
    "results": [
        {
            "id": 2867,
            "title": "A brain tumor-homing tetra-peptide ...",
            "pmid": "32510090",
            "year": "2020",
            "source": "A33H",
            "name_source": "NA",
            "sequence": "SIWV",
            "n_term": "Fluorescein isothiocyanate (FITC)",
            "c_term": "Biotin",
            "motif": "NA",
            "target_tumor": "Brain tumor",
            "target_cell": "NA",
            "receptors_biomarker": "NA",
            "phage_display": "NA",
            "invitro": "U87MG cells, A549 cells, Huh7 cells",
        }
    ],
}

_NOT_FOUND_PAYLOAD = {"status": 404, "message": "Record Not Found"}
_TUMORHOPE_BAD_QUERY = {
    "status": "error",
    "message": "No valid search parameters provided.",
    "count": 0,
    "results": [],
}


class TestHemolytik2(unittest.TestCase):
    @patch("tooluniverse.hemolytik2_tool.requests.get")
    def test_search_success(self, mock_get):
        """Success parse path returns records and metadata."""
        mock_get.return_value = _mock_response(_HEMOLYTIK_PAYLOAD)
        tool = Hemolytik2SearchPeptidesTool({})
        result = tool.run({"dataType": "nature", "dataValue": "Anticancer"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["seq"], "FVDLKKIANIINSIFKK")
        self.assertEqual(result["metadata"]["total_count"], 2)
        self.assertEqual(result["metadata"]["data_type"], "nature")
        # Verify dataType/dataValue were sent as query params.
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["dataValue"], "Anticancer")

    @patch("tooluniverse.hemolytik2_tool.requests.get")
    def test_search_not_found(self, mock_get):
        """Not-found payload maps to an error envelope."""
        # Server may return the not-found body with HTTP 200.
        mock_get.return_value = _mock_response(_NOT_FOUND_PAYLOAD)
        tool = Hemolytik2SearchPeptidesTool({})
        result = tool.run({"dataType": "nature", "dataValue": "NOPENOPE"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Record Not Found", result["error"])

    def test_missing_value(self):
        """Missing required dataValue returns an error."""
        tool = Hemolytik2SearchPeptidesTool({})
        result = tool.run({"dataType": "nature"})
        self.assertEqual(result["status"], "error")
        self.assertIn("dataValue is required", result["error"])

    def test_invalid_data_type(self):
        """Unsupported dataType returns an error."""
        tool = Hemolytik2SearchPeptidesTool({})
        result = tool.run({"dataType": "bogus", "dataValue": "x"})
        self.assertEqual(result["status"], "error")
        self.assertIn("Invalid dataType", result["error"])


class TestCancerPPD2(unittest.TestCase):
    @patch("tooluniverse.cancerppd2_tool.requests.get")
    def test_search_success(self, mock_get):
        """Success parse path returns records and metadata."""
        mock_get.return_value = _mock_response(_CANCERPPD_PAYLOAD)
        tool = CancerPPD2SearchPeptidesTool({})
        result = tool.run({"dataType": "cancer_type", "dataValue": "Fibrosarcoma"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["seq"], "FIHHIFRGIVHAGRSIGRFLTG")
        self.assertEqual(result["data"][0]["cancer_type"], "Fibrosarcoma")
        self.assertEqual(result["metadata"]["total_count"], 1)

    @patch("tooluniverse.cancerppd2_tool.requests.get")
    def test_search_http_error(self, mock_get):
        """Non-200 HTTP status returns an error."""
        mock_get.return_value = _mock_response(None, status_code=500)
        tool = CancerPPD2SearchPeptidesTool({})
        result = tool.run({"dataType": "cancer_type", "dataValue": "Fibrosarcoma"})
        self.assertEqual(result["status"], "error")
        self.assertIn("HTTP 500", result["error"])

    def test_missing_value(self):
        """Missing required dataValue returns an error."""
        tool = CancerPPD2SearchPeptidesTool({})
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("dataValue is required", result["error"])


class TestPEPlife2(unittest.TestCase):
    @patch("tooluniverse.peplife2_tool.requests.get")
    def test_search_success(self, mock_get):
        """Success parse path returns records and metadata."""
        mock_get.return_value = _mock_response(_PEPLIFE_PAYLOAD)
        tool = PEPlife2SearchPeptidesTool({})
        result = tool.run({"dataType": "lin_cyc", "dataValue": "Linear"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["seq"], "RRWQWR")
        self.assertEqual(result["data"][0]["half_life"], "<30")
        self.assertEqual(result["data"][0]["units_half"], "minutes")
        self.assertEqual(result["metadata"]["data_value"], "Linear")

    @patch("tooluniverse.peplife2_tool.requests.get")
    def test_search_non_json(self, mock_get):
        """Non-JSON body returns an error."""
        mock_get.return_value = _mock_response(None, raise_json=True)
        tool = PEPlife2SearchPeptidesTool({})
        result = tool.run({"dataType": "lin_cyc", "dataValue": "Linear"})
        self.assertEqual(result["status"], "error")
        self.assertIn("non-JSON", result["error"])

    @patch("tooluniverse.peplife2_tool.requests.get")
    def test_request_exception(self, mock_get):
        """Network exception is caught and returned as error."""
        import requests as _rq

        mock_get.side_effect = _rq.exceptions.ConnectionError("boom")
        tool = PEPlife2SearchPeptidesTool({})
        result = tool.run({"dataType": "lin_cyc", "dataValue": "Linear"})
        self.assertEqual(result["status"], "error")
        self.assertIn("failed", result["error"])


class TestTumorHope2(unittest.TestCase):
    @patch("tooluniverse.tumorhope2_tool.requests.get")
    def test_search_success(self, mock_get):
        """Success parse path returns records and metadata."""
        mock_get.return_value = _mock_response(_TUMORHOPE_PAYLOAD)
        tool = TumorHope2SearchPeptidesTool({})
        result = tool.run({"source": "A33H"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["sequence"], "SIWV")
        self.assertEqual(result["data"][0]["target_tumor"], "Brain tumor")
        self.assertEqual(result["metadata"]["total_count"], 1)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["source"], "A33H")

    @patch("tooluniverse.tumorhope2_tool.requests.get")
    def test_search_bad_query_status_error(self, mock_get):
        """API status=error payload maps to an error envelope."""
        mock_get.return_value = _mock_response(_TUMORHOPE_BAD_QUERY)
        tool = TumorHope2SearchPeptidesTool({})
        # Filter present so request is issued, but server reports status=error.
        result = tool.run({"source": "anything"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No valid search parameters", result["error"])

    def test_no_filter(self):
        """No filter supplied returns an error."""
        tool = TumorHope2SearchPeptidesTool({})
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("At least one search filter", result["error"])


if __name__ == "__main__":
    unittest.main()
