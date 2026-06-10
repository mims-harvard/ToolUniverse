"""Taxonomy / biodiversity depth tools: parse + error-path coverage (mocked HTTP).

Covers eight new tools that close confirmed capability gaps in the
taxonomy-biodiversity cluster. All network calls are mocked; these tests never
touch the live APIs.

WoRMS (WoRMSRESTTool, AphiaID-keyed enrichment):
  * ``WoRMS_get_classification`` — nested ranked-lineage classification tree.
  * ``WoRMS_get_vernaculars``    — multilingual common names.
  * ``WoRMS_get_distribution``   — MarineRegions MRGID localities.
  * ``WoRMS_get_synonyms``       — unaccepted names -> valid AphiaID.

iDigBio (iDigBioSearchTool, mode dispatch):
  * ``iDigBio_summary_facets``   — total count + facet breakdowns.
  * ``iDigBio_search_media``     — specimen image/media records.

GBIF (BaseRESTTool, config-driven):
  * ``GBIF_match_name``          — single best backbone name match.
  * ``GBIF_occurrence_stats``    — occurrence count + facets.
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src",
    "tooluniverse",
    "data",
)


def _load_config(filename: str, tool_name: str) -> dict:
    """Load a single tool config block by name from a data JSON file."""
    with open(os.path.join(_DATA_DIR, filename)) as fh:
        for cfg in json.load(fh):
            if cfg.get("name") == tool_name:
                return cfg
    raise AssertionError(f"{tool_name} not found in {filename}")


def _fake_response(payload, status_code: int = 200, text: str = None):
    """Build a MagicMock standing in for a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(payload) if text is None else text
    resp.json.return_value = payload
    resp.headers = {"content-type": "application/json"}
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# WoRMS — WoRMSRESTTool AphiaID enrichment operations
# ---------------------------------------------------------------------------

_WORMS_CLASSIFICATION = {
    "AphiaID": 1,
    "rank": "Superdomain",
    "scientificname": "Biota",
    "child": {
        "AphiaID": 2,
        "rank": "Kingdom",
        "scientificname": "Animalia",
        "child": {
            "AphiaID": 127160,
            "rank": "Species",
            "scientificname": "Solea solea",
            "child": None,
        },
    },
}

_WORMS_VERNACULARS = [
    {"vernacular": "common sole", "language_code": "eng", "language": "English"},
    {"vernacular": "gewone tong", "language_code": "nld", "language": "Dutch"},
]

_WORMS_DISTRIBUTION = [
    {
        "locality": "Baltic sea",
        "locationID": "http://marineregions.org/mrgid/2401",
        "recordStatus": "valid",
        "establishmentMeans": None,
    },
    {
        "locality": "Black Sea",
        "locationID": "http://marineregions.org/mrgid/3319",
        "recordStatus": "valid",
        "establishmentMeans": None,
    },
]

_WORMS_SYNONYMS = [
    {
        "AphiaID": 163034,
        "scientificname": "Pleuronectes solea",
        "status": "unaccepted",
        "valid_AphiaID": 127160,
        "valid_name": "Solea solea",
        "rank": "Species",
    },
]


def _worms_tool(tool_name: str):
    from tooluniverse.worms_tool import WoRMSRESTTool

    return WoRMSRESTTool(_load_config("worms_tools.json", tool_name))


class TestWoRMSEnrichment(unittest.TestCase):
    def test_classification_parses_nested_tree(self):
        """Classification returns the recursive Biota->Kingdom->...->Species tree."""
        tool = _worms_tool("WoRMS_get_classification")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response(_WORMS_CLASSIFICATION)
            result = tool.run({"AphiaID": 127160})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["scientificname"], "Biota")
        self.assertEqual(result["data"]["child"]["rank"], "Kingdom")
        self.assertEqual(result["AphiaID"], 127160)
        # AphiaID is substituted into the WoRMS classification URL.
        self.assertIn("AphiaClassificationByAphiaID/127160", get.call_args[0][0])

    def test_vernaculars_parses_language_codes(self):
        """Vernaculars returns common names with language codes and a count."""
        tool = _worms_tool("WoRMS_get_vernaculars")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response(_WORMS_VERNACULARS)
            result = tool.run({"AphiaID": 127160})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["data"][0]["language"], "English")

    def test_distribution_parses_localities(self):
        """Distribution returns localities with MarineRegions MRGID locationIDs."""
        tool = _worms_tool("WoRMS_get_distribution")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response(_WORMS_DISTRIBUTION)
            result = tool.run({"AphiaID": 127160})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["locality"], "Baltic sea")
        self.assertIn("mrgid/2401", result["data"][0]["locationID"])

    def test_synonyms_parses_valid_aphia_mapping(self):
        """Synonyms map unaccepted names to the valid AphiaID with status."""
        tool = _worms_tool("WoRMS_get_synonyms")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response(_WORMS_SYNONYMS)
            result = tool.run({"AphiaID": 127160})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["valid_AphiaID"], 127160)
        self.assertEqual(result["data"][0]["status"], "unaccepted")

    def test_missing_aphia_id_is_error_not_exception(self):
        """A missing AphiaID yields an error envelope, never a raised exception."""
        tool = _worms_tool("WoRMS_get_classification")
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("AphiaID", result["error"])

    def test_non_integer_aphia_id_is_error(self):
        """A non-integer AphiaID is rejected with an error envelope."""
        tool = _worms_tool("WoRMS_get_vernaculars")
        result = tool.run({"AphiaID": "not-a-number"})
        self.assertEqual(result["status"], "error")

    def test_empty_204_response_is_success_empty(self):
        """A 204 (no records) for an enrichment resource is a clean empty success."""
        tool = _worms_tool("WoRMS_get_vernaculars")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response([], status_code=204, text="")
            result = tool.run({"AphiaID": 999999})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"], [])

    def test_network_error_returns_error_envelope(self):
        """A transport exception is caught and returned as an error envelope."""
        tool = _worms_tool("WoRMS_get_distribution")
        with patch("requests.Session.get", side_effect=Exception("boom")):
            result = tool.run({"AphiaID": 127160})
        self.assertEqual(result["status"], "error")
        self.assertIn("WoRMS", result["error"])

    def test_legacy_search_by_name_still_dispatches(self):
        """Default (no operation) config still does the AphiaRecordsByName search."""
        tool = _worms_tool("WoRMS_search_species")
        with patch("requests.Session.get") as get:
            get.return_value = _fake_response([{"AphiaID": 127160}])
            result = tool.run({"query": "Solea solea"})
        self.assertEqual(result["status"], "success")
        self.assertIn("AphiaRecordsByName", get.call_args[0][0])


# ---------------------------------------------------------------------------
# iDigBio — iDigBioSearchTool summary + media modes
# ---------------------------------------------------------------------------

_IDIGBIO_COUNT = {"itemCount": 2771}
_IDIGBIO_TOP = {
    "country": {
        "united states": {"itemCount": 4095},
        "mexico": {"itemCount": 264},
    },
    "itemCount": 5798,
}
_IDIGBIO_MEDIA = {
    "itemCount": 171,
    "items": [
        {
            "uuid": "baf0318e-b07f-4859-b46e-1579042ca381",
            "data": {
                "dcterms:type": "StillImage",
                "dcterms:format": "image/jpeg",
                "ac:providerManagedID": "urn:uuid:3f64f854",
                "dc:creator": "Rose Arnold",
                "xmpRights:Owner": "UWSP-Mammals",
                "xmpRights:UsageTerms": "CC BY-NC-SA",
                "ac:accessURI": "https://media01.example/img.jpg",
            },
        }
    ],
}


def _idigbio_tool(tool_name: str):
    from tooluniverse.idigbio_tool import iDigBioSearchTool

    return iDigBioSearchTool(_load_config("idigbio_tools.json", tool_name))


class TestiDigBioSummary(unittest.TestCase):
    def test_summary_with_top_fields_returns_count_and_facets(self):
        """With top_fields set, both the count and top-facet endpoints are queried."""
        tool = _idigbio_tool("iDigBio_summary_facets")
        with patch("tooluniverse.idigbio_tool.requests.get") as get:
            # First call -> count endpoint, second -> top endpoint.
            get.side_effect = [
                _fake_response(_IDIGBIO_COUNT),
                _fake_response(_IDIGBIO_TOP),
            ]
            result = tool.run({"genus": "puma", "top_fields": "country", "count": 5})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["itemCount"], 2771)
        self.assertIn("country", result["data"]["facets"])
        self.assertEqual(
            result["data"]["facets"]["country"]["united states"]["itemCount"], 4095
        )
        self.assertEqual(get.call_count, 2)

    def test_summary_count_only_when_no_top_fields(self):
        """Without top_fields only the count endpoint is hit; facets stay empty."""
        tool = _idigbio_tool("iDigBio_summary_facets")
        with patch("tooluniverse.idigbio_tool.requests.get") as get:
            get.return_value = _fake_response(_IDIGBIO_COUNT)
            result = tool.run({"scientificname": "puma concolor"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["itemCount"], 2771)
        self.assertEqual(result["data"]["facets"], {})
        # Only the count endpoint is hit when no top_fields requested.
        self.assertEqual(get.call_count, 1)

    def test_summary_requires_a_query_field(self):
        """An empty query yields an error envelope."""
        tool = _idigbio_tool("iDigBio_summary_facets")
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_summary_network_error_is_error_envelope(self):
        """A request exception on the count call surfaces as an error envelope."""
        tool = _idigbio_tool("iDigBio_summary_facets")
        import requests as _requests

        with patch(
            "tooluniverse.idigbio_tool.requests.get",
            side_effect=_requests.exceptions.RequestException("down"),
        ):
            result = tool.run({"genus": "puma"})
        self.assertEqual(result["status"], "error")


class TestiDigBioMedia(unittest.TestCase):
    def test_media_parses_image_record_fields(self):
        """Media records expose type, creator, usage terms, and access URI."""
        tool = _idigbio_tool("iDigBio_search_media")
        with patch("tooluniverse.idigbio_tool.requests.get") as get:
            get.return_value = _fake_response(_IDIGBIO_MEDIA)
            result = tool.run({"scientificname": "puma concolor", "limit": 2})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["metadata"]["total_available"], 171)
        rec = result["data"][0]
        self.assertEqual(rec["type"], "StillImage")
        self.assertEqual(rec["usage_terms"], "CC BY-NC-SA")
        self.assertEqual(rec["creator"], "Rose Arnold")
        self.assertEqual(rec["access_uri"], "https://media01.example/img.jpg")

    def test_media_requires_a_query_field(self):
        """An empty media query yields an error envelope."""
        tool = _idigbio_tool("iDigBio_search_media")
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_media_timeout_is_error_envelope(self):
        """A timeout on the media call surfaces as an error envelope."""
        tool = _idigbio_tool("iDigBio_search_media")
        import requests as _requests

        with patch(
            "tooluniverse.idigbio_tool.requests.get",
            side_effect=_requests.exceptions.Timeout(),
        ):
            result = tool.run({"genus": "Quercus"})
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"])


# ---------------------------------------------------------------------------
# GBIF — BaseRESTTool config-driven match + occurrence-stats
# ---------------------------------------------------------------------------

_GBIF_MATCH = {
    "usageKey": 2435099,
    "scientificName": "Puma concolor (Linnaeus, 1771)",
    "canonicalName": "Puma concolor",
    "rank": "SPECIES",
    "status": "ACCEPTED",
    "confidence": 99,
    "matchType": "EXACT",
    "kingdom": "Animalia",
    "speciesKey": 2435099,
    "familyKey": 9703,
}

_GBIF_STATS = {
    "offset": 0,
    "limit": 0,
    "count": 29340,
    "results": [],
    "facets": [
        {
            "field": "COUNTRY",
            "counts": [
                {"name": "US", "count": 11380},
                {"name": "AR", "count": 3368},
            ],
        }
    ],
}


def _gbif_tool(tool_name: str):
    from tooluniverse.base_rest_tool import BaseRESTTool

    return BaseRESTTool(_load_config("gbif_ext_tools.json", tool_name))


class TestGBIFMatchName(unittest.TestCase):
    def test_match_returns_usage_key_and_confidence(self):
        """Match returns usageKey, matchType, confidence and sends name as a query."""
        tool = _gbif_tool("GBIF_match_name")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _fake_response(_GBIF_MATCH)
            result = tool.run({"name": "Puma concolor"})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["usageKey"], 2435099)
        self.assertEqual(result["data"]["matchType"], "EXACT")
        self.assertEqual(result["data"]["confidence"], 99)
        # name is sent as a query param (not a path param).
        self.assertEqual(req.call_args.kwargs["params"].get("name"), "Puma concolor")

    def test_match_http_error_is_error_envelope(self):
        """A non-2xx status surfaces as an error envelope with status_code."""
        tool = _gbif_tool("GBIF_match_name")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _fake_response({}, status_code=500, text="server error")
            result = tool.run({"name": "Puma concolor"})
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["status_code"], 500)

    def test_match_exception_is_error_envelope(self):
        """A transport exception is caught and returned as an error envelope."""
        tool = _gbif_tool("GBIF_match_name")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            side_effect=Exception("network down"),
        ):
            result = tool.run({"name": "Puma concolor"})
        self.assertEqual(result["status"], "error")


class TestGBIFOccurrenceStats(unittest.TestCase):
    def test_stats_returns_count_and_facets(self):
        """Stats forward limit=0 and the facet, and return count plus facets."""
        tool = _gbif_tool("GBIF_occurrence_stats")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _fake_response(_GBIF_STATS)
            result = tool.run({"taxonKey": 2435099, "facet": "country", "facetLimit": 5})
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["count"], 29340)
        self.assertEqual(result["data"]["facets"][0]["field"], "COUNTRY")
        params = req.call_args.kwargs["params"]
        # limit=0 (count-only) and the facet are forwarded to GBIF.
        self.assertEqual(params.get("limit"), 0)
        self.assertEqual(params.get("facet"), "country")
        self.assertEqual(params.get("taxonKey"), 2435099)

    def test_stats_facet_defaults_to_country(self):
        """When facet/facetLimit are omitted the schema defaults are applied."""
        tool = _gbif_tool("GBIF_occurrence_stats")
        with patch("tooluniverse.base_rest_tool.request_with_retry") as req:
            req.return_value = _fake_response(_GBIF_STATS)
            tool.run({"taxonKey": 2435099})
        params = req.call_args.kwargs["params"]
        self.assertEqual(params.get("facet"), "country")
        self.assertEqual(params.get("facetLimit"), 10)

    def test_stats_exception_is_error_envelope(self):
        """A transport exception is caught and returned as an error envelope."""
        tool = _gbif_tool("GBIF_occurrence_stats")
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            side_effect=Exception("boom"),
        ):
            result = tool.run({"taxonKey": 2435099})
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
