"""Depth tools for the environment-toxicology cluster.

Covers two new tools that reuse existing tool classes (no new registration):

* ``EPA_get_tri_facility_chemical_releases`` — reuses ``EPATRIFacilitiesTool``
  in config-driven lookup mode to return the per-chemical, per-year TRI
  reporting forms a single facility filed (tri_reporting_form table).
* ``AOPWiki_get_key_event`` — reuses ``AOPWikiDetailTool`` with
  ``settings.endpoint_kind == "event"`` to return one Key Event's
  ontology-annotated event_components (/events/{id}.json).

Both parse paths and error paths are mocked so the suite needs no network.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# EPA_get_tri_facility_chemical_releases (EPATRIFacilitiesTool, lookup mode)
# --------------------------------------------------------------------------- #
def _epa_tool():
    from tooluniverse.epa_envirofacts_tool import EPATRIFacilitiesTool

    return EPATRIFacilitiesTool(
        {
            "name": "EPA_get_tri_facility_chemical_releases",
            "type": "EPATRIFacilitiesTool",
            "fields": {
                "timeout": 30,
                "table": "tri_reporting_form",
                "lookup_column": "tri_facility_id",
                "lookup_param": "tri_facility_id",
                "row_kind": "reporting_form",
            },
        }
    )


_EPA_ROWS = [
    {
        "tri_facility_id": "15902CCKRN75BRI",
        "tri_chem_id": "N982",
        "cas_chem_name": "Zinc compounds",
        "reporting_year": "2000",
        "form_type_ind": "L",
        "max_amount_of_chem": "04",
        "one_time_release_qty": 0,
        "production_ratio": 1.25,
        "federal_fac_ind": "0",
        "trade_secret_ind": "0",
        "doc_ctrl_num": "1300140000011",
    },
    {
        "tri_facility_id": "15902CCKRN75BRI",
        "tri_chem_id": "0007439921",
        "cas_chem_name": "Lead",
        "reporting_year": "2001",
        "form_type_ind": "L",
        "max_amount_of_chem": "02",
        "one_time_release_qty": 5,
        "production_ratio": 0.92,
        "federal_fac_ind": "0",
        "trade_secret_ind": "0",
        "doc_ctrl_num": "1301150516944",
    },
]


class TestEPATriReportingForm(unittest.TestCase):
    @patch("tooluniverse.epa_envirofacts_tool.requests.get")
    def test_parse_reporting_forms(self, mock_get):
        """Reporting forms parse with chemical/year fields, not facility fields."""
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = _EPA_ROWS
        mock_get.return_value = resp

        out = _epa_tool().run({"tri_facility_id": "15902CCKRN75BRI", "limit": 3})

        self.assertEqual(out["status"], "success")
        self.assertEqual(out["metadata"]["table"], "tri_reporting_form")
        self.assertEqual(len(out["data"]), 2)

        first = out["data"][0]
        self.assertEqual(first["tri_chem_id"], "N982")
        self.assertEqual(first["chemical_name"], "Zinc compounds")
        self.assertEqual(first["reporting_year"], "2000")
        self.assertEqual(first["max_amount_code"], "04")
        # facility-row keys must NOT leak into reporting-form summaries
        self.assertNotIn("facility_name", first)

        # the request hit the tri_reporting_form table, keyed by facility id
        url = mock_get.call_args[0][0]
        self.assertIn("tri_reporting_form", url)
        self.assertIn("tri_facility_id/15902CCKRN75BRI", url)

    def test_missing_facility_id_returns_error(self):
        """A missing facility id yields a status=error envelope, no raise."""
        out = _epa_tool().run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("tri_facility_id", out["error"])

    @patch("tooluniverse.epa_envirofacts_tool.requests.get")
    def test_request_failure_returns_error_no_raise(self, mock_get):
        """A transport failure is caught and returned as status=error."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("boom")
        out = _epa_tool().run({"tri_facility_id": "15902CCKRN75BRI"})
        self.assertEqual(out["status"], "error")
        self.assertIn("failed", out["error"].lower())

    @patch("tooluniverse.epa_envirofacts_tool.requests.get")
    def test_facility_search_mode_unaffected(self, mock_get):
        """The default state/city search config must keep working."""
        from tooluniverse.epa_envirofacts_tool import EPATRIFacilitiesTool

        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = [
            {
                "tri_facility_id": "X1",
                "facility_name": "ACME",
                "city_name": "SACRAMENTO",
                "state_abbr": "CA",
            }
        ]
        mock_get.return_value = resp

        tool = EPATRIFacilitiesTool(
            {
                "name": "EPA_search_tri_facilities",
                "type": "EPATRIFacilitiesTool",
                "fields": {"timeout": 30},
            }
        )
        out = tool.run({"state": "CA", "city": "Sacramento", "limit": 1})
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["data"][0]["facility_name"], "ACME")
        self.assertEqual(out["metadata"]["table"], "tri_facility")


# --------------------------------------------------------------------------- #
# AOPWiki_get_key_event (AOPWikiDetailTool, endpoint_kind == "event")
# --------------------------------------------------------------------------- #
def _aop_event_tool():
    from tooluniverse.aopwiki_tool import AOPWikiDetailTool

    return AOPWikiDetailTool(
        {
            "name": "AOPWiki_get_key_event",
            "type": "AOPWikiDetailTool",
            "settings": {
                "base_url": "https://aopwiki.org",
                "timeout": 30,
                "endpoint_kind": "event",
            },
        }
    )


_AOP_EVENT = {
    "id": 18,
    "title": "Activation, AhR",
    "short_name": "Activation, AhR",
    "biological_organization": "Molecular",
    "created_at": "2016-11-29T18:41:22.000-05:00",
    "updated_at": "2025-05-31T07:56:20.000-04:00",
    "event_components": [
        {
            "id": 101,
            "process": {
                "term": "aryl hydrocarbon receptor activity",
                "source_id": "GO:0004874",
            },
            "object": {
                "term": "aryl hydrocarbon receptor",
                "source_id": "PR:000003858",
            },
            "action": {"term": "increased", "source_id": "1"},
        }
    ],
}


class TestAOPWikiKeyEvent(unittest.TestCase):
    @patch("tooluniverse.aopwiki_tool._get_json")
    def test_parse_event_components(self, mock_json):
        """Event components surface GO/PR source_ids and biological level."""
        mock_json.return_value = _AOP_EVENT
        out = _aop_event_tool().run({"event_id": 18})

        self.assertEqual(out["status"], "success")
        data = out["data"]
        self.assertEqual(data["id"], 18)
        self.assertEqual(data["title"], "Activation, AhR")
        self.assertEqual(data["biological_organization"], "Molecular")

        comp = data["event_components"][0]
        self.assertEqual(comp["process"]["source_id"], "GO:0004874")
        self.assertEqual(comp["object"]["source_id"], "PR:000003858")
        self.assertEqual(comp["action"]["term"], "increased")

        # it queried the /events/{id}.json endpoint
        url = mock_json.call_args[0][0]
        self.assertIn("/events/18.json", url)

    def test_missing_event_id_returns_error(self):
        """A missing event id yields a status=error envelope, no raise."""
        out = _aop_event_tool().run({})
        self.assertEqual(out["status"], "error")
        self.assertIn("event_id", out["error"])

    @patch("tooluniverse.aopwiki_tool._get_json")
    def test_not_found_returns_error(self, mock_json):
        """A 404-ish payload becomes a status=error envelope."""
        mock_json.return_value = {"status": 404}
        out = _aop_event_tool().run({"event_id": 99999999})
        self.assertEqual(out["status"], "error")
        self.assertIn("not found", out["error"].lower())

    @patch("tooluniverse.aopwiki_tool._get_json")
    def test_network_error_returns_error_no_raise(self, mock_json):
        """A network exception is caught and returned as status=error."""
        mock_json.side_effect = OSError("connection reset")
        out = _aop_event_tool().run({"event_id": 18})
        self.assertEqual(out["status"], "error")
        self.assertIn("AOPWiki API error", out["error"])

    @patch("tooluniverse.aopwiki_tool._get_json")
    def test_aop_detail_mode_unaffected(self, mock_json):
        """Default whole-AOP detail config must keep working."""
        from tooluniverse.aopwiki_tool import AOPWikiDetailTool

        mock_json.return_value = {
            "id": 3,
            "title": "AOP three",
            "aop_kes": [{"event_id": 10, "event": "KE ten"}],
        }
        tool = AOPWikiDetailTool(
            {
                "name": "AOPWiki_get_aop",
                "type": "AOPWikiDetailTool",
                "settings": {"base_url": "https://aopwiki.org", "timeout": 30},
            }
        )
        out = tool.run({"aop_id": 3})
        self.assertEqual(out["status"], "success")
        self.assertEqual(out["data"]["id"], 3)
        self.assertEqual(out["data"]["key_events"][0]["event_id"], 10)
        url = mock_json.call_args[0][0]
        self.assertIn("/aops/3.json", url)


if __name__ == "__main__":
    unittest.main()
