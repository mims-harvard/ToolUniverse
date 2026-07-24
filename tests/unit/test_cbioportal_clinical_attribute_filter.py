"""Round 92: cBioPortal_get_clinical_data silently ignored its clinical_attribute_id filter.

The tool declares an optional `clinical_attribute_id` param ("filter by clinical
attribute"), but run() only substituted {study_id}/{page_size} placeholders and
did a plain GET -- the value was never sent, so every call returned all clinical
attributes regardless of the requested one (confirmed live: brca_tcga returned 17
attributes unfiltered vs 1 with attributeId=CANCER_TYPE). The fix appends the
API's `attributeId` query param. These tests mock the HTTP session and assert the
URL wiring.
"""

from unittest.mock import MagicMock, patch

from tooluniverse.cbioportal_tool import CBioPortalRESTTool


def _make():
    cfg = {
        "name": "cBioPortal_get_clinical_data",
        "type": "CBioPortalRESTTool",
        "fields": {
            "endpoint": "https://www.cbioportal.org/api/studies/{study_id}/clinical-data?pageSize={page_size}&clinicalDataType=SAMPLE",
            "return_format": "JSON",
        },
        "parameter": {
            "type": "object",
            "properties": {
                "study_id": {"type": "string"},
                "page_size": {"type": "integer", "default": 50},
                "clinical_attribute_id": {"type": "string"},
            },
            "required": ["study_id"],
        },
    }
    return CBioPortalRESTTool(cfg)


def _run_capture(tool, arguments):
    captured = {}

    def fake_get(url, timeout=None):
        captured["url"] = url
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = []
        return resp

    with patch.object(tool.session, "get", side_effect=fake_get):
        tool.run(arguments)
    return captured["url"]


def test_clinical_attribute_id_is_sent_as_attributeId():
    tool = _make()
    url = _run_capture(tool, {"study_id": "brca_tcga", "page_size": 50, "clinical_attribute_id": "CANCER_TYPE"})
    assert "attributeId=CANCER_TYPE" in url


def test_clinical_attribute_id_omitted_leaves_url_unfiltered():
    tool = _make()
    url = _run_capture(tool, {"study_id": "brca_tcga", "page_size": 50})
    assert "attributeId" not in url


def test_clinical_attribute_id_is_url_encoded():
    tool = _make()
    # attribute ids are normally simple tokens, but a value with a space must not
    # break the query string.
    url = _run_capture(tool, {"study_id": "brca_tcga", "page_size": 50, "clinical_attribute_id": "A B"})
    assert "attributeId=A%20B" in url
    assert " " not in url.split("attributeId=")[1]
