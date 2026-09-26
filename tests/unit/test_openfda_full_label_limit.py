"""Whole-label results (``return_fields="ALL"``) honour the caller's limit.

``FDA_get_drug_label_info_by_field_value`` with ``field="openfda.brand_name"``,
``field_value="keppra extended"``, ``return_fields="ALL"`` and ``limit=1``
returned three complete labels (389k characters) while ``meta.limit`` said 1.
The exact query finds nothing, the fallback re-queries with a candidate page of
at least 25, and the ``"ALL"`` branch returned before the step that cuts the
results back to the caller's limit.

Everything mocks the HTTP layer -- no network.
"""

import copy
from unittest.mock import patch

from tooluniverse import openfda_tool as module
from tooluniverse.openfda_tool import FDADrugLabelFieldValueTool

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}


def _records():
    return [
        {
            "id": str(i),
            "set_id": f"set-{i}",
            "openfda": {"brand_name": ["Sample Drug"], "route": ["ORAL"]},
            "spl_product_data_elements": ["Sample Drug"],
            "warnings": ["Complete original paragraph [including brackets]."],
            "dosage_and_administration_table": ["<table><tr><td>1</td></tr></table>"],
        }
        for i in range(3)
    ]


def _search(limit, fallback, fields="ALL"):
    records = _records()
    payload = {
        "meta": {
            "results": {"skip": 0, "limit": 25 if fallback else limit, "total": 3}
        },
        "results": records,
    }
    responses = ([NOT_FOUND] if fallback else []) + [payload]
    with patch.object(
        module, "_openfda_get", side_effect=copy.deepcopy(responses)
    ) as fetch:
        result = module.search_openfda(
            {"search_fields": {"openfda.brand_name": "Sample Drug"}, "limit": limit},
            endpoint_url="https://example.invalid/drug/label.json",
            return_fields=fields,
            exists=None,
        )
    assert fetch.call_count == len(responses)
    return result, records


def test_a_fallback_returns_one_whole_label_when_one_is_asked_for():
    result, records = _search(1, fallback=True)
    assert result["results"] == records[:1]
    assert result["result_count"] == 1
    assert result["meta"]["limit"] == 1
    assert result["meta"]["total"] == 3
    assert "note" in result  # the fallback still says what it did


def test_a_fallback_returns_two_whole_labels_when_two_are_asked_for():
    result, records = _search(2, fallback=True)
    assert result["results"] == records[:2]
    assert result["result_count"] == 2


def test_the_labels_themselves_are_not_rewritten():
    result, records = _search(1, fallback=True)
    assert result["results"][0] == records[0]


def test_an_exact_answer_is_bounded_too():
    result, records = _search(1, fallback=False)
    assert result["results"] == records[:1]


def test_no_limit_keeps_every_label():
    for limit in (0, None):
        result, records = _search(limit, fallback=False)
        assert result["results"] == records


def test_projected_sections_still_honour_the_limit():
    result, _ = _search(1, fallback=True, fields=["warnings"])
    assert len(result["results"]) == 1
    assert result["result_count"] == 1


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_the_field_value_tool_honours_the_limit_for_whole_labels():
    config = {
        "name": "FDA_get_drug_label_info_by_field_value",
        "description": "field lookup",
        "type": "FDADrugLabelFieldValueTool",
        "parameter": {"type": "object", "properties": {}},
    }
    served = []

    def fake_get(url, *args, **kwargs):
        served.append(url)
        if len(served) == 1:
            return _FakeResponse(NOT_FOUND)
        return _FakeResponse(
            {
                "meta": {"results": {"skip": 0, "limit": 25, "total": 3}},
                "results": _records(),
            }
        )

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = FDADrugLabelFieldValueTool(config).run(
            {
                "field": "openfda.brand_name",
                "field_value": "keppra extended",
                "return_fields": "ALL",
                "limit": 1,
            }
        )
    assert len(served) >= 2  # the exact query missed and a fallback ran
    assert out["result_count"] == 1
    assert len(out["results"]) == 1
    assert out["meta"]["limit"] == 1
