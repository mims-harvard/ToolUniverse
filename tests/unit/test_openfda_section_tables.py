"""A requested label section comes back with its tables.

openFDA stores a section's tables in a separate field, ``<section>_table``.
Asking ``FDA_get_dosage_and_storage_information_by_drug_name`` for levetiracetam
returned the ``dosage_and_administration`` prose, which points at "Table 1" for
the renal dose adjustment, but not ``dosage_and_administration_table``, which
holds the doses. The tables of the requested sections are now copied from the
same record, HTML intact and never keyword-trimmed.

Everything mocks the HTTP layer -- no network.
"""

import copy
from unittest.mock import patch

from tooluniverse.openfda_tool import FDADrugLabelTool, extract_nested_fields

TABLE = [
    '<table><caption>Table 1</caption><tr><th rowspan="2">CLcr (mL/min)</th>'
    "<th>Dose</th></tr><tr><td>30-50</td><td>250-750 mg every 12 hours</td></tr>"
    "<tfoot><tr><td>* after dialysis</td></tr></tfoot></table>"
]


def _label(**extra):
    record = {
        "openfda": {"brand_name": ["KEPPRA"], "generic_name": ["LEVETIRACETAM"]},
        "dosage_and_administration": [
            "Take with or without food. Adjust the dose in renal impairment (see Table 1)."
        ],
        "dosage_and_administration_table": copy.deepcopy(TABLE),
        "adverse_reactions_table": ["<table>unrelated section</table>"],
    }
    record.update(extra)
    return record


def test_the_requested_section_s_table_comes_with_it_unchanged():
    record = _label()
    before = copy.deepcopy(record)
    fields = ["dosage_and_administration"]
    out = extract_nested_fields([record], fields)
    assert out == [
        {
            "dosage_and_administration": record["dosage_and_administration"],
            "dosage_and_administration_table": TABLE,
        }
    ]
    # a copy: the caller cannot edit the raw record through the result
    out[0]["dosage_and_administration_table"].append("changed")
    assert record == before
    assert fields == ["dosage_and_administration"]


def test_tables_of_sections_not_requested_are_not_added():
    out = extract_nested_fields([_label()], ["dosage_and_administration"])
    assert "adverse_reactions_table" not in out[0]


def test_a_table_is_never_borrowed_from_another_record():
    records = [_label(), {"dosage_and_administration": ["Another label."]}]
    out = extract_nested_fields(records, ["dosage_and_administration"])
    assert out[1] == {"dosage_and_administration": ["Another label."]}


def test_keyword_trimming_cuts_prose_but_never_a_table():
    out = extract_nested_fields([_label()], ["dosage_and_administration"], ["renal"])
    prose = str(out[0]["dosage_and_administration"])
    assert "renal impairment" in prose
    assert "with or without food" not in prose
    assert out[0]["dosage_and_administration_table"] == TABLE
    # asking for the table field itself is not trimmed either
    direct = extract_nested_fields(
        [_label()], ["dosage_and_administration_table"], ["renal"]
    )
    assert direct[0]["dosage_and_administration_table"] == TABLE


def test_a_table_alone_counts_as_the_section_being_present():
    out = extract_nested_fields([{"dose_table": ["data"]}], ["dose"])
    assert out == [{"dose": None, "dose_table": ["data"]}]


def test_dotted_fields_never_look_for_a_table():
    record = {"openfda": {"brand_name": ["X"]}, "openfda.brand_name_table": ["no"]}
    out = extract_nested_fields([record], ["openfda.brand_name"])
    assert out == [{"openfda.brand_name": ["X"]}]


def test_identity_fields_still_cannot_resurrect_an_empty_record():
    assert (
        extract_nested_fields([{"id": "one"}], ["dose"], identity_fields=["id"]) == []
    )


def test_sibling_sections_behave_as_before():
    record = {
        "openfda": {"brand_name": ["X"]},
        "warnings": ["related"],
        "id": "one",
    }
    out = extract_nested_fields(
        [record],
        ["openfda.brand_name", "precautions"],
        identity_fields=["id"],
        sibling_sections={"precautions": ["warnings"]},
    )
    assert out[0]["related_sections_present"] == ["warnings"]
    assert out[0]["id"] == "one"
    assert out[0]["precautions"] is None


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_the_label_tool_returns_the_table():
    config = {
        "name": "FDA_get_dosage_and_storage_information_by_drug_name",
        "description": "dose",
        "type": "FDADrugLabel",
        "parameter": {
            "type": "object",
            "properties": {"drug_name": {"type": "string"}},
            "required": ["drug_name"],
        },
        "fields": {
            "search_fields": {
                "drug_name": ["openfda.brand_name", "openfda.generic_name"]
            },
            "return_fields": ["dosage_and_administration", "how_supplied"],
        },
    }
    payload = {
        "meta": {"results": {"skip": 0, "limit": 1, "total": 1}},
        "results": [_label()],
    }
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        out = FDADrugLabelTool(config).run({"drug_name": "levetiracetam", "limit": 1})
    assert out["results"][0]["dosage_and_administration_table"] == TABLE
    assert "adverse_reactions_table" not in out["results"][0]
