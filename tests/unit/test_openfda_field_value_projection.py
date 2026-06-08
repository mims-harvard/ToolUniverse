"""Regression guard for Feature-ClinPharm-001.

FDA_get_drug_label_info_by_field_value must treat return_fields as a PROJECTION,
not an _exists_ match filter — otherwise requesting a field the matched record
lacks (e.g. boxed_warning) returns a DIFFERENT drug. The fix passes exists=None.
"""

from unittest.mock import patch

from tooluniverse.openfda_tool import FDADrugLabelFieldValueTool


def _tool():
    return FDADrugLabelFieldValueTool(
        {"name": "FDA_get_drug_label_info_by_field_value", "type": "FDADrugLabelFieldValueTool",
         "fields": {}, "parameter": {"type": "object", "properties": {}}},
    )


def test_field_value_passes_exists_none_not_return_fields():
    captured = {}

    def fake_search(arguments, **kw):
        captured.update(kw)
        return {"status": "success", "results": []}

    with patch("tooluniverse.openfda_tool.search_openfda", side_effect=fake_search):
        _tool().run({
            "field": "openfda.generic_name",
            "field_value": "IMATINIB MESYLATE",
            "return_fields": ["boxed_warning"],
        })
    # The projection field must NOT become an _exists_ filter.
    assert captured["exists"] is None
    assert captured["return_fields"] == ["boxed_warning"]
