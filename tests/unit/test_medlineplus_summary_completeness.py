"""Regression test for complete MedlinePlus Connect summaries."""

import pytest

from tooluniverse.medlineplus_tool import MedlinePlusRESTTool

pytestmark = pytest.mark.unit


def test_connect_formatter_keeps_full_summary_and_exact_length():
    summary = "<p>Complete clinical background and patient guidance.</p>" * 130
    payload = {
        "feed": {
            "entry": [
                {
                    "title": {"_value": "Diabetes Type 2"},
                    "summary": {"_value": summary},
                    "link": {"href": "https://medlineplus.gov/diabetestype2.html"},
                }
            ]
        }
    }
    tool = MedlinePlusRESTTool(
        {
            "name": "MedlinePlus_connect_lookup_by_code",
            "fields": {"endpoint": "https://example.test/{c}"},
            "parameter": {"properties": {"c": {"type": "string"}}},
        }
    )

    result = tool._format_response(payload, "MedlinePlus_connect_lookup_by_code")

    response = result["responses"][0]
    assert len(summary) > 500
    assert response["summary"] == summary
    assert response["summary_length"] == len(summary)
