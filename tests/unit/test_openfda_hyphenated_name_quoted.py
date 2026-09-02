"""Fix-54B-1: a hyphenated drug name was sent to openFDA unquoted.

`_render_clause` quoted a value only when it contained a SPACE. A hyphen is a
Lucene operator, so a single-token hyphenated name was reparsed into its parts
and the query silently became a union of DIFFERENT drugs -- while the response
went on to report, in prose, how many reports "named" the product.

`faers_drug_name_clause` in the same module had always quoted, and its
docstring gave this exact case as the reason ("the hyphen in CO-TRIMOXAZOLE
... would be reparsed rather than matched"). So the two paths disagreed on the
one input each was written about, and a third comment called the divergence
deliberate. The fix removed the divergence: `faers_drug_name_clause` now calls
`_render_clause` rather than restating the rule, so its docstring no longer
carries that sentence.

Measured against api.fda.gov on 2026-08-13, same field:value, unquoted vs
quoted total::

    patient.drug.medicinalproduct:sumatriptan-naproxen   124792  vs      13
    patient.drug.medicinalproduct:CO-TRIMOXAZOLE          24806  vs    1416

and end to end, before the fix::

    FAERS_count_reactions_by_drug_event(medicinalproduct="sumatriptan-naproxen")
      total_reports_matching_query  219048
      = sumatriptan (51,295) OR naproxen (172,094) over the three name fields,
        for a combination product with 1,438 reports under its real brand name
      and the response asserted "only 124,792 of them named
      'sumatriptan-naproxen' as the product" -- no report does, 124,792 times.

    FAERS_count_reactions_by_drug_event(medicinalproduct="MANNITOL-SULFATE")
      total_reports_matching_query  852859   (MANNITOL 6,370 OR SULFATE 847,806)
      for a substance that does not exist. After the fix: 0.

    FAERS_count_reactions_by_drug_event(medicinalproduct="CIGUATOXIN-ANTITOXIN-XYZ")
      total_reports_matching_query  141, with
      reports_matched_by_name_resolution_only 0 -- i.e. the tool affirmed that
      141 reports named an invented product. After the fix: 0.

Two personas found this independently in the same round.

The cost of widening the quoting rule was measured over every other value
shape these builders send; see `_render_clause`'s docstring. Quoted and
unquoted returned identical totals for all of them, so no query changes except
the ones that were wrong. These tests build query strings only -- no request.
"""

import pytest

from tooluniverse.openfda_adv_tool import (
    FAERS_DRUG_NAME_FIELDS,
    _render_clause,
    _render_field_group,
    faers_drug_name_clause,
)

pytestmark = pytest.mark.unit

FIELD = "patient.drug.medicinalproduct"


@pytest.mark.parametrize(
    "name", ["CO-TRIMOXAZOLE", "sumatriptan-naproxen", "MANNITOL-SULFATE"]
)
def test_a_hyphenated_name_is_quoted(name):
    """Unquoted, Lucene splits on the hyphen and answers about other drugs."""
    assert _render_clause(FIELD, name) == f'{FIELD}:"{name}"'


def test_the_drug_name_clause_quotes_a_hyphenated_name():
    """The divergence a comment used to call deliberate on both sides.

    `faers_drug_name_clause` now calls `_render_clause` instead of restating
    the quoting rule, so comparing the two renderers to each other would be
    true by construction. The rendered string is pinned instead: this fails if
    the shared rule stops quoting, which is the regression that matters.
    """
    expected = (
        "(" + "+OR+".join(f'{f}:"CO-TRIMOXAZOLE"' for f in FAERS_DRUG_NAME_FIELDS) + ")"
    )
    assert faers_drug_name_clause("CO-TRIMOXAZOLE") == expected
    assert _render_field_group(FAERS_DRUG_NAME_FIELDS, "CO-TRIMOXAZOLE") == expected


def test_a_single_date_is_quoted_without_changing_the_answer():
    """`receivedate` accepts a single date as well as a range; only the range
    is exempt from quoting, so the single-date form is now quoted.

    Measured against api.fda.gov, because a quoted RANGE returns HTTP 404 and
    a silently-empty date filter is exactly the failure the carve-out exists to
    prevent: receivedate:20141001 and receivedate:"20141001" both return 2,415,
    and receiptdate likewise returns 2,375 either way.
    """
    assert _render_clause("receivedate", "20141001") == 'receivedate:"20141001"'


def test_a_lucene_range_is_still_not_quoted():
    """The one carve-out, and it is load-bearing.

    Measured: receivedate:[20141001 TO 20141231] returns 197,676 unquoted and
    HTTP 404 NOT_FOUND quoted.
    """
    rng = "[20141001 TO 20141231]"
    assert _render_clause("receivedate", rng) == f"receivedate:{rng}"


def test_a_multi_word_value_is_still_quoted():
    """The case the old space-based rule got right; it must not regress."""
    assert (
        _render_clause("patient.reaction.reactionmeddrapt", "ACUTE KIDNEY INJURY")
        == 'patient.reaction.reactionmeddrapt:"ACUTE KIDNEY INJURY"'
    )


def test_a_coded_value_is_quoted_without_changing_the_answer():
    """Quoting a HUMAN_TO_FDA_MAP code is a no-op upstream.

    Measured: serious:1 and serious:"1" both return 11,882,961; the same held
    for patientsex, agegroup, route 048, reactionoutcome, qualification,
    drugcharacterization, fulfillexpeditecriteria, occurcountry and a numeric
    patientonsetage. Pinned so a range stays the only exemption among STRING
    values -- non-strings are covered separately, just below.
    """
    assert _render_clause("serious", "1") == 'serious:"1"'


def test_a_non_string_value_is_not_quoted():
    """Only strings are quoted; an int must not become a phrase."""
    assert _render_clause("patient.patientonsetage", 50) == (
        "patient.patientonsetage:50"
    )
