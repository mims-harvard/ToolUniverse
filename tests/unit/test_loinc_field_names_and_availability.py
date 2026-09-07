"""LOINC must ask the index for names it uses, and disclose what it cannot answer.

Fix Round 48, both reproduced through the CLI and confirmed against the live
clinicaltables API on 2026-08-13.

1. The details call requested `SHORT_NAME`, which the loinc_items/v3 index does
   not recognise, so it answered "" for every code:

       search?terms=2823-3&df=SHORT_NAME -> [1,["2823-3"],null,[[""]]]
       search?terms=2823-3&df=SHORTNAME  -> [1,["2823-3"],null,[["Potassium SerPl-sCnc"]]]

2. Seven further fields are genuinely absent from this index -- SYSTEM,
   SCALE_TYP, METHOD_TYP, CLASS, STATUS, TIME_ASPCT, COMMON_TEST_RANK all
   return "" when probed one at a time -- yet were emitted as empty strings
   with nothing marking them unavailable. LOINC 2823-3 is serum potassium, and
   SYSTEM is the field that distinguishes it from urine potassium, so a rule
   author selecting a code saw a blank exactly where the discriminating value
   belongs.
"""

import inspect
import re

import pytest

from tooluniverse.loinc_tool import LOINCTool

pytestmark = pytest.mark.unit


def _requested_fields(method):
    """Field names the method puts in its `fields = [...]` request list."""
    # Comments are stripped first: the explanatory comment inside the field
    # list quotes raw API responses containing brackets, which would otherwise
    # terminate the match early.
    source = "\n".join(
        re.sub(r"#.*$", "", line) for line in inspect.getsource(method).splitlines()
    )
    block = re.search(r"fields = \[(.*?)\]", source, re.S)
    assert block, f"no `fields = [...]` list found in {method.__name__}"
    return set(re.findall(r'"([A-Z_]+)"', block.group(1)))


def test_shortname_is_requested_under_the_name_the_index_uses():
    """`SHORT_NAME` is not a field of this index; `SHORTNAME` is."""
    fields = _requested_fields(LOINCTool._get_code_details)
    assert "SHORTNAME" in fields
    assert "SHORT_NAME" not in fields


def test_absent_fields_are_disclosed_when_requested():
    disclosure = LOINCTool._unavailable_fields_disclosure(
        ["LOINC_NUM", "COMPONENT", "SYSTEM", "SCALE_TYP"]
    )
    assert disclosure["fields_unavailable"] == ["SYSTEM", "SCALE_TYP"]
    note = disclosure["fields_unavailable_note"]
    # The note must say the emptiness is uninformative, not merely list fields.
    assert "carries no information" in note
    assert "SYSTEM" in note


def test_no_disclosure_when_every_requested_field_is_available():
    """Control: fields this index does publish must not be flagged."""
    assert (
        LOINCTool._unavailable_fields_disclosure(
            ["LOINC_NUM", "LONG_COMMON_NAME", "SHORTNAME", "COMPONENT", "PROPERTY"]
        )
        == {}
    )


def test_the_disclosure_actually_reaches_every_operations_response():
    """Exercise the wiring, not just the helper.

    The first version of these tests called `_unavailable_fields_disclosure`
    directly and inspected source text, so deleting the lines that attach the
    disclosure to a response left every assertion green -- the only
    user-visible part of the fix was untested.
    """
    tool = LOINCTool.__new__(LOINCTool)
    captured = {}

    def fake_request(endpoint, params):
        captured["df"] = params["df"]
        # One row, one value per requested field.
        n = len(params["df"].split(","))
        return [1, ["2823-3"], None, [[""] * n]]

    tool._make_request = fake_request

    for operation, args in (
        ("_search_loinc_items", {"terms": "potassium"}),
        ("_get_answer_list", {"loinc_code": "2823-3"}),
        ("_search_forms", {"terms": "PHQ-9"}),
    ):
        result = getattr(tool, operation)(args)
        requested = set(captured["df"].split(","))
        absent = requested & set(LOINCTool._FIELDS_ABSENT_FROM_V3_INDEX)
        assert absent, f"{operation} no longer requests any absent field"
        assert "fields_unavailable" in result, (
            f"{operation} returned blanks for {sorted(absent)} with no note"
        )
        assert set(result["fields_unavailable"]) == absent

    # And the details operation, which returns the row rather than the envelope.
    details = tool._get_code_details({"loinc_code": "2823-3"})
    assert "fields_unavailable" in details


def test_every_field_named_absent_is_actually_requested_somewhere():
    """The absent-list must describe real requests, not be true by construction.

    A list naming fields the tool never asks for would make the disclosure
    vacuous while still passing the assertions above.
    """
    requested = _requested_fields(LOINCTool._get_code_details) | _requested_fields(
        LOINCTool._search_loinc_items
    )
    for field in LOINCTool._FIELDS_ABSENT_FROM_V3_INDEX:
        assert field in requested, f"{field} is declared absent but never requested"
