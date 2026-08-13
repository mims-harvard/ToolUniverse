"""Two LOINC operations asked the index for things it does not implement.

Fix Round 49. Both were reproduced through the CLI and the mechanism of each
was established against the live clinicaltables API and its documentation on
2026-08-13.

1. ``LOINC_search_forms`` sent ``sf=CLASS`` and then kept only rows whose
   ``CLASS`` contained "survey"/"panel"/"form". Neither half could ever hold.
   ``sf`` selects which fields are searched and the API documents the choices
   as "text, COMPONENT, CONSUMER_NAME, RELATEDNAMES2, METHOD_TYP, SHORTNAME,
   LONG_COMMON_NAME, SURVEY_QUEST_TEXT, LOINC_NUM" -- CLASS is not among them,
   so the search matched nothing::

       search?terms=PHQ-9&sf=CLASS -> [0,[],null,[]]
       search?terms=PHQ-9          -> 58 hits

   and CLASS is separately empty for every code in this index (Fix Round 48),
   so the post-filter would have discarded every row even had rows arrived.
   Every shipped test_example returned ``count: 0`` reported as success. The
   documented way to restrict to instruments is ``type``, and ``form`` is the
   value that works: ``terms=PHQ-9&type=form`` returns the two real PHQ-9
   panels.

2. ``LOINC_get_answer_list`` sent ``type=answer``. That is not one of the
   implemented values, and unrecognised values are dropped rather than
   rejected, so the call degraded into an ordinary keyword search whose rows
   were presented as "answer-type codes". Totals were identical for
   ``type=answer`` and for an invented ``type=zzzgarbage`` on every term tried
   (PHQ-9 58/58, potassium 145/145, hemoglobin 526/526), and the index holds no
   answer codes at all (``terms=LA6568-5`` -> ``[0,[],null,[]]``). Answer lists
   are published through ``ef=AnswerLists``, which really does carry them:
   ``terms=883-9&ef=AnswerLists`` returns list LL2419-1 with Group A / B / O /
   AB.
"""

import pytest

from tooluniverse.loinc_tool import LOINCTool

pytestmark = pytest.mark.unit


def _tool(api_response):
    """A LOINCTool whose only upstream call returns `api_response`.

    The params it was called with are recorded on `tool.sent`, so a test can
    assert both what went out and what came back without touching the network.
    """
    tool = LOINCTool.__new__(LOINCTool)
    tool.sent = {}

    def fake_request(endpoint, params):
        tool.sent.update(params)
        return api_response

    tool._make_request = fake_request
    return tool


# The shape the live API returns for `terms=PHQ-9&type=form`, with the empty
# CLASS/STATUS this index really sends back for every code.
_FORMS_RESPONSE = [
    2,
    ["44249-1", "89206-7"],
    None,
    [
        ["44249-1", "PHQ-9 quick depression assessment panel [Reported.PHQ]", "", ""],
        ["89206-7", "Patient Health Questionnaire-9: Modified for Teens", "", ""],
    ],
]


def test_forms_search_does_not_filter_on_a_field_this_index_cannot_search():
    tool = _tool(_FORMS_RESPONSE)
    tool._search_forms({"terms": "PHQ-9"})
    assert tool.sent.get("sf") is None, (
        "sf=CLASS matches nothing: CLASS is not a searchable field of this index"
    )


def test_forms_search_restricts_to_instruments_with_the_value_that_works():
    tool = _tool(_FORMS_RESPONSE)
    tool._search_forms({"terms": "PHQ-9"})
    # Not merely "some type": `panel` is documented but inert upstream, and any
    # unrecognised value is silently ignored, which is how the old `answer`
    # value went unnoticed. Pin the one value proven to restrict the result set.
    assert tool.sent.get("type") == "form"


def test_forms_that_the_index_returns_survive_to_the_caller():
    """The bite: rows whose CLASS is empty must not be discarded.

    CLASS is empty for every code here, so the old post-filter deleted the
    entire result set. Asserting only on the outgoing params would leave that
    half of the defect free to come back.
    """
    tool = _tool(_FORMS_RESPONSE)
    result = tool._search_forms({"terms": "PHQ-9"})
    assert result["count"] == 2
    assert [row["code"] for row in result["results"]] == ["44249-1", "89206-7"]
    assert result["total_count"] == 2
    assert "note" not in result, "a successful search must not be annotated as empty"


def test_a_genuinely_empty_form_search_says_which_kind_of_empty_it_is():
    tool = _tool([0, [], None, []])
    result = tool._search_forms({"terms": "no such instrument"})
    assert result["count"] == 0
    assert "LOINC_search_tests" in result["note"], (
        "an honest zero must point the caller at the operation that can answer"
    )


# `terms=883-9&ef=AnswerLists,datatype` as the live API returns it: the `ef`
# values arrive in slot 2 keyed by field, one entry per row, NOT inline with
# the `df` row data in slot 3.
_ANSWER_RESPONSE = [
    2,
    ["883-9", "11502-2"],
    {
        "AnswerLists": [
            [
                {
                    "AnswerListId": "LL2419-1",
                    "AnswerListName": "ABO group",
                    "answers": [
                        {
                            "AnswerStringID": "LA19710-5",
                            "DisplayText": "Group A",
                            "SequenceNo": 1,
                            "Score": None,
                        }
                    ],
                }
            ],
            None,
        ],
        "datatype": ["CNE", "ST"],
    },
    [
        ["883-9", "ABO group [Type] in Blood", "ABO group", ""],
        ["11502-2", "Laboratory report", "Laboratory report", ""],
    ],
]


def test_answer_list_lookup_stops_sending_a_type_the_api_does_not_implement():
    tool = _tool(_ANSWER_RESPONSE)
    tool._get_answer_list({"loinc_code": "883-9"})
    assert tool.sent.get("type") is None, (
        "type=answer is not implemented upstream and was silently dropped, "
        "turning this operation into a plain keyword search"
    )


def test_answer_list_lookup_requests_the_field_that_carries_answer_lists():
    tool = _tool(_ANSWER_RESPONSE)
    tool._get_answer_list({"loinc_code": "883-9"})
    assert set(tool.sent.get("ef", "").split(",")) == {"AnswerLists", "datatype"}


def test_answer_lists_reach_the_caller_and_stay_on_their_own_row():
    """The bite: `ef` values are row-parallel in slot 2, not inline in slot 3.

    Reading them from the wrong slot yields no answer lists at all; reading
    them without preserving row order silently attributes one code's
    permissible values to another, which no count would reveal.
    """
    tool = _tool(_ANSWER_RESPONSE)
    result = tool._get_answer_list({"loinc_code": "ABO"})

    by_code = {row["code"]: row for row in result["results"]}
    assert by_code["883-9"]["datatype"] == "CNE"
    abo_list = by_code["883-9"]["AnswerLists"][0]
    assert abo_list["AnswerListId"] == "LL2419-1"
    assert [answer["DisplayText"] for answer in abo_list["answers"]] == ["Group A"]
    # The free-text code in the same response must keep its own (absent) list.
    assert by_code["11502-2"]["AnswerLists"] is None
    assert by_code["11502-2"]["datatype"] == "ST"


def test_matched_codes_without_an_answer_list_are_not_counted_as_answer_lists():
    tool = _tool(_ANSWER_RESPONSE)
    result = tool._get_answer_list({"loinc_code": "ABO"})
    assert result["count"] == 2, "two codes matched"
    assert result["answer_lists_found"] == 1, "but only one publishes an answer list"
    assert "note" not in result


def test_a_code_that_publishes_no_answer_list_says_so_rather_than_implying_one():
    """11502-2 is a shipped example and is free text: an honest empty answer."""
    response = [
        1,
        ["11502-2"],
        {"AnswerLists": [None], "datatype": ["ST"]},
        [["11502-2", "Laboratory report", "Laboratory report", ""]],
    ]
    result = _tool(response)._get_answer_list({"loinc_code": "11502-2"})
    assert result["answer_lists_found"] == 0
    assert "datatype" in result["note"]


def test_extra_fields_are_only_attached_when_the_operation_asked_for_them():
    """Control: the plain test search must not sprout `ef` keys."""
    tool = _tool(_FORMS_RESPONSE)
    result = tool._search_loinc_items({"terms": "PHQ-9"})
    assert tool.sent.get("ef") is None
    assert all("AnswerLists" not in row for row in result["results"])


# --------------------------------------------------------------------------- #
# The unavailable-fields disclosure must not contradict the rows it sits on.
#
# Fix-R48 derived its list of absent fields by probing a single code, 2823-3,
# and generalised "" to "empty for every code". METHOD_TYP is not: measured
# over 570 rows drawn from 19 unrelated search terms it is populated in 260
# (45.6%), with real values "PhenX", "ISE", "LC/MS/MS" and "Confirm". So a
# search for creatinine returned two rows reading METHOD_TYP "PhenX" directly
# above a note asserting METHOD_TYP is "returned empty for every code" -- and
# METHOD_TYP is what separates a presumptive immunoassay screen from a
# confirmatory LC/MS/MS quantitation, so the note was telling callers to
# disregard the discriminating value. Three personas hit it independently.
# --------------------------------------------------------------------------- #


def test_a_populated_field_is_never_declared_unavailable():
    """The bite: the claim is checked against the rows, not just asserted."""
    disclosure = LOINCTool._unavailable_fields_disclosure(
        ["LOINC_NUM", "SYSTEM", "METHOD_TYP"],
        [{"LOINC_NUM": "62807-3", "SYSTEM": "", "METHOD_TYP": "PhenX"}],
    )
    assert "METHOD_TYP" not in disclosure["fields_unavailable"]
    assert "METHOD_TYP" not in disclosure["fields_unavailable_note"]
    # SYSTEM really is empty in that row and really is absent from the index.
    assert disclosure["fields_unavailable"] == ["SYSTEM"]


def test_method_typ_is_no_longer_claimed_absent_at_all():
    """It is not an index-wide absence, so the static list must not say so."""
    assert "METHOD_TYP" not in LOINCTool._FIELDS_ABSENT_FROM_V3_INDEX


def test_the_disclosure_still_fires_for_fields_that_really_are_absent():
    """Control: removing one wrong entry must not disarm the other six."""
    disclosure = LOINCTool._unavailable_fields_disclosure(
        ["LOINC_NUM", "SYSTEM", "CLASS"],
        [{"LOINC_NUM": "2823-3", "SYSTEM": "", "CLASS": ""}],
    )
    assert disclosure["fields_unavailable"] == ["SYSTEM", "CLASS"]
    assert "carries no information" in disclosure["fields_unavailable_note"]


def test_a_zero_result_response_carries_no_per_code_field_note():
    """It would describe the fields of no codes at all."""
    result = _tool([0, [], None, []])._search_loinc_items({"terms": "LC/MS/MS"})
    assert result["count"] == 0
    assert "fields_unavailable" not in result
    assert "fields_unavailable_note" not in result


def test_every_field_still_named_absent_is_empty_in_practice():
    """Guards the static list against a second over-generalisation.

    Each entry is a claim about the whole index. This pins the measurement
    that justifies it, so adding an entry means producing rows that support it.
    """
    measured_nonempty_rate = {
        "SYSTEM": 0.0,
        "SCALE_TYP": 0.0,
        "CLASS": 0.0,
        "STATUS": 0.0,
        "TIME_ASPCT": 0.0,
        "COMMON_TEST_RANK": 0.0,
        # Removed from the list this round; kept here as the counter-example.
        "METHOD_TYP": 0.456,
    }
    for field in LOINCTool._FIELDS_ABSENT_FROM_V3_INDEX:
        assert measured_nonempty_rate.get(field) == 0.0, (
            f"{field} is declared absent from the index but was measured "
            f"populated in {measured_nonempty_rate.get(field)} of sampled rows"
        )
