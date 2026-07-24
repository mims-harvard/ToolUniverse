"""Drug-safety / clinical depth tools: parse + error-path coverage (mocked HTTP).

Covers six new tools that close confirmed terminology / drug-product capability
gaps, all reusing existing tool classes (no new @register_tool class):

* ``NCIThesaurus_get_concept_maps`` (NCIThesaurusTool, endpoint=get_maps) —
  cross-vocabulary maps (MedDRA / SNOMED / GDC / ICD) for an NCIt concept.
* ``NCIThesaurus_get_parents`` (NCIThesaurusTool, endpoint=get_parents) —
  upward NCIt hierarchy (broader categories / drug-class superconcepts).
* ``RxNorm_get_ndc_status_history`` (RxNormExtendedTool, op=get_ndc_status_history)
  — NDC status + RxCUI remapping timeline (ndcstatus).
* ``RxNorm_get_ndc_properties`` (RxNormExtendedTool, op=get_ndc_properties) —
  NDC pill/package metadata (imprint, color, labeler, SPL setid).
* ``DailyMed_get_spl_media`` (GetSPLBySetIDTool, resource=media) — SPL drug-label
  image list.
* ``DailyMed_get_spl_history`` (GetSPLBySetIDTool, resource=history) — SPL version
  history.

All network calls are mocked; these tests never touch the live APIs.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

pytestmark = pytest.mark.unit


def _json_response(payload, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# NCIThesaurus_get_concept_maps  (NCIThesaurusTool, endpoint=get_maps)
# ---------------------------------------------------------------------------


def _maps_tool():
    from tooluniverse.nci_thesaurus_tool import NCIThesaurusTool

    return NCIThesaurusTool({"fields": {"endpoint": "get_maps"}})


_MAPS_FAKE = {
    "code": "C4872",
    "name": "Breast Carcinoma",
    "maps": [
        {
            "type": "Has Synonym",
            "targetName": "Breast cancer",
            "targetTermType": "LLT",
            "targetCode": "10006187",
            "targetTerminology": "MedDRA",
            "targetTerminologyVersion": "18.1",
        },
        {
            "type": "Has Synonym",
            "targetName": "Breast Cancer",
            "targetTermType": "PT",
            "targetCode": "relationship_primary_diagnosis",
            "targetTerminology": "GDC",
        },
    ],
}


class TestNCIThesaurusGetMaps(unittest.TestCase):
    def test_parses_cross_vocabulary_maps(self):
        tool = _maps_tool()
        with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
            get.return_value = _json_response(_MAPS_FAKE)
            result = tool.run({"code": "C4872"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["code"], "C4872")
        self.assertEqual(data["name"], "Breast Carcinoma")
        self.assertEqual(len(data["maps"]), 2)
        meddra = data["maps"][0]
        self.assertEqual(meddra["target_code"], "10006187")
        self.assertEqual(meddra["target_terminology"], "MedDRA")
        self.assertEqual(meddra["target_term_type"], "LLT")
        # include=maps endpoint was requested.
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["include"], "maps")
        # Distinct target terminologies are summarized + sorted.
        self.assertEqual(result["metadata"]["target_terminologies"], ["GDC", "MedDRA"])
        self.assertEqual(result["metadata"]["total_maps"], 2)

    def test_missing_code_is_error(self):
        """Missing code yields an error, not an exception."""
        tool = _maps_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")
        self.assertIn("code", result["error"])

    def test_http_failure_returns_error_not_raise(self):
        """A connection error is caught and returned as status error."""
        import requests

        tool = _maps_tool()
        with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("boom")
            result = tool.run({"code": "C4872"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# NCIThesaurus_get_parents  (NCIThesaurusTool, endpoint=get_parents)
# ---------------------------------------------------------------------------


def _parents_tool():
    from tooluniverse.nci_thesaurus_tool import NCIThesaurusTool

    return NCIThesaurusTool({"fields": {"endpoint": "get_parents"}})


_PARENTS_FAKE = [
    {"code": "C155711", "name": "Anti-HER2 Monoclonal Antibody", "leaf": False}
]


class TestNCIThesaurusGetParents(unittest.TestCase):
    def test_parses_parents(self):
        tool = _parents_tool()
        with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
            get.return_value = _json_response(_PARENTS_FAKE)
            result = tool.run({"code": "C1647"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["code"], "C155711")
        self.assertEqual(result["data"][0]["name"], "Anti-HER2 Monoclonal Antibody")
        self.assertEqual(result["metadata"]["child_code"], "C1647")
        self.assertEqual(result["metadata"]["total_parents"], 1)
        # The /parents endpoint was hit.
        args, _ = get.call_args
        self.assertTrue(args[0].endswith("/concept/ncit/C1647/parents"))

    def test_missing_code_is_error(self):
        """Missing code yields an error, not an exception."""
        tool = _parents_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_timeout_returns_error_not_raise(self):
        """A timeout is caught and returned as status error."""
        import requests

        tool = _parents_tool()
        with patch("tooluniverse.nci_thesaurus_tool.requests.get") as get:
            get.side_effect = requests.exceptions.Timeout("slow")
            result = tool.run({"code": "C1647"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# RxNorm_get_ndc_status_history  (RxNormExtendedTool, op=get_ndc_status_history)
# ---------------------------------------------------------------------------


def _ndc_status_tool():
    from tooluniverse.rxnorm_extended_tool import RxNormExtendedTool

    return RxNormExtendedTool({"fields": {"operation": "get_ndc_status_history"}})


_NDC_STATUS_FAKE = {
    "ndcStatus": {
        "ndc11": "00093005801",
        "status": "ACTIVE",
        "active": "YES",
        "rxcui": "835603",
        "conceptName": "tramadol hydrochloride 50 MG Oral Tablet",
        "conceptStatus": "ACTIVE",
        "sourceList": {"sourceName": ["GS", "RXNORM"]},
        "ndcHistory": [
            {
                "activeRxcui": "835603",
                "originalRxcui": "835603",
                "startDate": "200906",
                "endDate": "202606",
            },
            {
                "activeRxcui": "835603",
                "originalRxcui": "313442",
                "startDate": "200706",
                "endDate": "200905",
            },
        ],
    }
}


class TestRxNormNdcStatusHistory(unittest.TestCase):
    def test_parses_status_and_history(self):
        tool = _ndc_status_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.return_value = _json_response(_NDC_STATUS_FAKE)
            result = tool.run({"ndc": "00093-0058-01"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertTrue(data["found"])
        self.assertEqual(data["status"], "ACTIVE")
        self.assertEqual(data["rxcui"], "835603")
        self.assertEqual(len(data["ndc_history"]), 2)
        # Remapping timeline preserved.
        self.assertEqual(data["ndc_history"][1]["original_rxcui"], "313442")
        self.assertEqual(data["ndc_history"][1]["start_date"], "200706")
        self.assertEqual(result["metadata"]["total_history_periods"], 2)

    def test_unknown_ndc_returns_found_false(self):
        """Unknown NDC returns success with found=False."""
        tool = _ndc_status_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.return_value = _json_response({"ndcStatus": {}})
            result = tool.run({"ndc": "99999-9999-99"})
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["data"]["found"])

    def test_missing_ndc_is_error(self):
        """Missing ndc yields an error."""
        tool = _ndc_status_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_request_exception_returns_error(self):
        """A network error is caught and returned as status error."""
        import requests

        tool = _ndc_status_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("net")
            result = tool.run({"ndc": "00093-0058-01"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# RxNorm_get_ndc_properties  (RxNormExtendedTool, op=get_ndc_properties)
# ---------------------------------------------------------------------------


def _ndc_props_tool():
    from tooluniverse.rxnorm_extended_tool import RxNormExtendedTool

    return RxNormExtendedTool({"fields": {"operation": "get_ndc_properties"}})


_NDC_PROPS_FAKE = {
    "ndcPropertyList": {
        "ndcProperty": [
            {
                "ndcItem": "00781150610",
                "ndc9": "0781-1506",
                "ndc10": "0781-1506-10",
                "rxcui": "197381",
                "splSetIdItem": "b900115a-faac-4244-94bc-c1ef2f88aa38",
                "packagingList": {"packaging": ["1000 TABLET in 1 BOTTLE (0781-1506-10)"]},
                "propertyConceptList": {
                    "propertyConcept": [
                        {"propName": "ANDA", "propValue": "ANDA073025"},
                        {"propName": "COLORTEXT", "propValue": "WHITE"},
                        {"propName": "IMPRINT_CODE", "propValue": "GG263"},
                        {"propName": "LABELER", "propValue": "Sandoz Inc"},
                        {"propName": "MARKETING_CATEGORY", "propValue": "ANDA"},
                        {"propName": "SHAPE", "propValue": "C48348"},
                    ]
                },
            }
        ]
    }
}


class TestRxNormNdcProperties(unittest.TestCase):
    def test_parses_pill_and_package_metadata(self):
        tool = _ndc_props_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.return_value = _json_response(_NDC_PROPS_FAKE)
            result = tool.run({"ndc": "0781-1506-10"})

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["data"]["found"])
        prod = result["data"]["products"][0]
        self.assertEqual(prod["rxcui"], "197381")
        self.assertEqual(prod["imprint_code"], "GG263")
        self.assertEqual(prod["color"], "WHITE")
        self.assertEqual(prod["labeler"], "Sandoz Inc")
        self.assertEqual(prod["anda"], "ANDA073025")
        self.assertEqual(prod["spl_set_id"], "b900115a-faac-4244-94bc-c1ef2f88aa38")
        self.assertEqual(prod["packaging"], ["1000 TABLET in 1 BOTTLE (0781-1506-10)"])
        # ndcproperties uses the `id` query param.
        _, kwargs = get.call_args
        self.assertEqual(kwargs["params"]["id"], "0781-1506-10")

    def test_empty_property_list_returns_found_false(self):
        """Empty property list returns success with found=False."""
        tool = _ndc_props_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.return_value = _json_response({"ndcPropertyList": {"ndcProperty": []}})
            result = tool.run({"ndc": "0000-0000-00"})
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["data"]["found"])

    def test_missing_ndc_is_error(self):
        """Missing ndc yields an error."""
        tool = _ndc_props_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_request_exception_returns_error(self):
        """A network error is caught and returned as status error."""
        import requests

        tool = _ndc_props_tool()
        with patch("tooluniverse.rxnorm_extended_tool.requests.get") as get:
            get.side_effect = requests.exceptions.ConnectionError("net")
            result = tool.run({"ndc": "0781-1506-10"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# DailyMed_get_spl_media  (GetSPLBySetIDTool, resource=media)
# ---------------------------------------------------------------------------


def _media_tool():
    from tooluniverse.dailymed_tool import GetSPLBySetIDTool

    return GetSPLBySetIDTool({"fields": {"resource": "media"}})


_MEDIA_FAKE = {
    "data": {
        "spl_version": 2,
        "title": "IBUPROFEN CAPSULE [AUROHEALTH LLC]",
        "setid": "43c94480-78d1-4a23-91d4-1d49fea72cb7",
        "media": [
            {
                "mime_type": "image/jpeg",
                "name": "ibuprofen-fig1.jpg",
                "url": "https://dailymed.nlm.nih.gov/dailymed/image.cfm?setid=43c94480-78d1-4a23-91d4-1d49fea72cb7&name=ibuprofen-fig1.jpg",
            }
        ],
    },
    "metadata": {"total_elements": 1},
}


class TestDailyMedSPLMedia(unittest.TestCase):
    def test_parses_media_list(self):
        """Media items are parsed with mime type, name and URL."""
        tool = _media_tool()
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.return_value = _json_response(_MEDIA_FAKE)
            result = tool.run({"setid": "43c94480-78d1-4a23-91d4-1d49fea72cb7"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["setid"], "43c94480-78d1-4a23-91d4-1d49fea72cb7")
        self.assertEqual(len(data["media"]), 1)
        self.assertEqual(data["media"][0]["mime_type"], "image/jpeg")
        self.assertEqual(data["media"][0]["name"], "ibuprofen-fig1.jpg")
        self.assertTrue(data["media"][0]["url"].startswith("https://"))
        # The media.json sub-resource URL was requested.
        args, _ = get.call_args
        self.assertTrue(args[0].endswith("/media.json"))

    def test_missing_setid_is_error(self):
        """Missing setid yields an error."""
        tool = _media_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_404_returns_error(self):
        """HTTP 404 is returned as status error."""
        tool = _media_tool()
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.return_value = _json_response({}, status_code=404)
            result = tool.run({"setid": "deadbeef"})
        self.assertEqual(result["status"], "error")

    def test_network_exception_returns_error(self):
        """A network exception is caught and returned as status error."""
        tool = _media_tool()
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.side_effect = Exception("net down")
            result = tool.run({"setid": "43c94480-78d1-4a23-91d4-1d49fea72cb7"})
        self.assertEqual(result["status"], "error")


# ---------------------------------------------------------------------------
# DailyMed_get_spl_history  (GetSPLBySetIDTool, resource=history)
# ---------------------------------------------------------------------------


def _history_tool():
    from tooluniverse.dailymed_tool import GetSPLBySetIDTool

    return GetSPLBySetIDTool({"fields": {"resource": "history"}})


_HISTORY_FAKE = {
    "data": {
        "spl": {
            "title": "IBUPROFEN CAPSULE [AUROHEALTH LLC]",
            "setid": "43c94480-78d1-4a23-91d4-1d49fea72cb7",
        },
        "history": [
            {"spl_version": 2, "published_date": "Jun 09, 2026"},
            {"spl_version": 1, "published_date": "Jul 22, 2022"},
        ],
    },
    "metadata": {"total_elements": 2},
}


class TestDailyMedSPLHistory(unittest.TestCase):
    def test_parses_version_history(self):
        """SPL version history entries are parsed."""
        tool = _history_tool()
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.return_value = _json_response(_HISTORY_FAKE)
            result = tool.run({"setid": "43c94480-78d1-4a23-91d4-1d49fea72cb7"})

        self.assertEqual(result["status"], "success")
        data = result["data"]
        self.assertEqual(data["setid"], "43c94480-78d1-4a23-91d4-1d49fea72cb7")
        self.assertEqual(len(data["history"]), 2)
        self.assertEqual(data["history"][0]["spl_version"], 2)
        self.assertEqual(data["history"][1]["published_date"], "Jul 22, 2022")
        # The history.json sub-resource URL was requested.
        args, _ = get.call_args
        self.assertTrue(args[0].endswith("/history.json"))

    def test_missing_setid_is_error(self):
        """Missing setid yields an error."""
        tool = _history_tool()
        result = tool.run({})
        self.assertEqual(result["status"], "error")

    def test_404_returns_error(self):
        """HTTP 404 is returned as status error."""
        tool = _history_tool()
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.return_value = _json_response({}, status_code=404)
            result = tool.run({"setid": "deadbeef"})
        self.assertEqual(result["status"], "error")

    def test_full_spl_path_unaffected_without_resource(self):
        """Without a resource field, the class still returns full SPL XML."""
        from tooluniverse.dailymed_tool import GetSPLBySetIDTool

        tool = GetSPLBySetIDTool({})
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<document/>"
        with patch("tooluniverse.dailymed_tool.requests.get") as get:
            get.return_value = resp
            result = tool.run({"setid": "abc", "format": "xml"})
        self.assertEqual(result["status"], "success")
        self.assertIn("xml", result)


if __name__ == "__main__":
    unittest.main()
