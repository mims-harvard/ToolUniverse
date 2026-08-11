"""A Lucene range must reach openFDA unquoted, from every query-building path.

Regression for Fix-R33. `openfda_adv_tool` spelled the "quote a value that
contains spaces" rule out separately in each query builder, and the paths
drifted: the range exemption was added to the multi-field branches only. Every
date parameter in these configs (`receivedate`) maps to a SINGLE field, so it
took the single-field branch, was seen as "a string with spaces" and was quoted.
openFDA then matched the range as a literal term and the query returned nothing.

Verified live before the fix, using verbatim the syntax the tool's own parameter
documentation gives:
  FAERS_count_reactions_by_drug_event
    {"medicinalproduct": "ASPIRIN", "receivedate": "[20141001 TO 20141231]"}
    -> {"results": [], "result_count": 0, "truncated": false}
  https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:%22ASPIRIN%22
      +AND+receivedate:%5B20141001+TO+20141231%5D&count=patient.reaction.reactionmeddrapt.exact
    -> [{"term": "DYSPNOEA", "count": 448}, ...]
An empty list flagged `truncated: false` reads as "no adverse events in this
quarter", which was false.

The fix routes every builder through the single `_render_clause` helper, so the
rule cannot be respelled per call site again. These tests pin the rendered URL
for each of the four classes -- all against mocked HTTP, no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.openfda_adv_tool import (  # noqa: E402
    FDACountAdditiveReactionsTool,
    FDADrugAdverseEventDetailTool,
    FDADrugAdverseEventTool,
    FDADrugInteractionDetailTool,
    _is_range,
    _render_clause,
    _render_field_group,
)

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"
RANGE = "[20141001 TO 20141231]"
# urllib.parse.quote is called with safe='+:"', so a double quote survives into
# the URL literally while brackets and spaces are percent-encoded. The range must
# arrive bracketed and UNQUOTED -- that is the whole point.
ENCODED_RANGE = "receivedate:%5B20141001%20TO%2020141231%5D"
QUOTED_RANGE = 'receivedate:"'


def _config(filename, name):
    configs = json.loads((DATA_DIR / filename).read_text())
    return next(c for c in configs if c["name"] == name)


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"results": [], "meta": {"results": {"total": 0}}}


def _capture(tool, arguments):
    """Run the tool with HTTP mocked and return the URL it built.

    The count tools also fetch a denominator for their coverage disclosure, and
    that request goes through `request_with_retry` rather than `requests.get`,
    so it needs its own mock or it would really call api.fda.gov. It is issued
    after the facet, so the URL under test is still the first one captured.
    """
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response()

    def fake_probe(_module, _method, url, **_kwargs):
        urls.append(url)
        return _Response()

    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_probe
        ),
    ):
        tool.run(arguments)
    assert urls, "tool made no request"
    return urls[0]


# ---- the shared helper is the single source of truth ----


def test_render_clause_leaves_a_range_unquoted_but_quotes_a_phrase():
    assert _render_clause("receivedate", RANGE) == f"receivedate:{RANGE}"
    assert (
        _render_clause("patient.reaction.reactionmeddrapt", "ACUTE KIDNEY INJURY")
        == 'patient.reaction.reactionmeddrapt:"ACUTE KIDNEY INJURY"'
    )
    assert _render_clause("serious", "1") == "serious:1"


def test_render_field_group_applies_the_same_rule_to_one_field_and_to_many():
    """The two paths must not diverge -- that divergence was the defect."""
    assert _render_field_group(["receivedate"], RANGE) == f"receivedate:{RANGE}"
    assert _render_field_group(["a", "b"], RANGE) == f"(a:{RANGE}+OR+b:{RANGE})"
    # A multi-field group stays parenthesized: Lucene binds AND tighter than OR.
    assert _render_field_group(["a", "b"], "X Y") == '(a:"X Y"+OR+b:"X Y")'


def test_is_range_accepts_lucene_brackets_and_rejects_a_plain_phrase():
    assert _is_range(RANGE)
    assert _is_range("{20141001 TO 20141231}")
    assert not _is_range("ACUTE KIDNEY INJURY")
    assert not _is_range("20141001")


# ---- every class that builds a query ----


def test_count_tool_sends_the_range_unquoted_from_the_single_field_path():
    """FAERS_count_reactions_by_drug_event: the reproduction case."""
    cfg = _config(
        "fda_drug_adverse_event_tools.json", "FAERS_count_reactions_by_drug_event"
    )
    url = _capture(
        FDADrugAdverseEventTool(cfg),
        {"medicinalproduct": "ASPIRIN", "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url
    assert QUOTED_RANGE not in url
    # The multi-field drug parameter is still OR-ed inside a parenthesized group.
    assert "%28patient.drug.medicinalproduct:ASPIRIN+OR+" in url


def test_additive_tool_sends_the_range_unquoted():
    cfg = _config(
        "fda_drug_adverse_event_tools.json", "FAERS_count_additive_adverse_reactions"
    )
    url = _capture(
        FDACountAdditiveReactionsTool(cfg),
        {"medicinalproducts": ["ASPIRIN"], "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url
    assert QUOTED_RANGE not in url


def test_detail_tool_sends_the_range_unquoted_from_the_single_field_path():
    cfg = _config(
        "fda_drug_adverse_event_detail_tools.json", "FAERS_search_adverse_event_reports"
    )
    # These configs expose no date parameter today; add one so the shared
    # single-field path is pinned before a config starts using it.
    cfg = json.loads(json.dumps(cfg))
    cfg["fields"]["search_fields"]["receivedate"] = ["receivedate"]
    url = _capture(
        FDADrugAdverseEventDetailTool(cfg),
        {"medicinalproduct": "ASPIRIN", "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url
    assert QUOTED_RANGE not in url


def test_interaction_tool_sends_the_range_unquoted():
    cfg = _config(
        "fda_drug_adverse_event_detail_tools.json",
        "FAERS_search_reports_by_drug_combination",
    )
    cfg = json.loads(json.dumps(cfg))
    cfg["fields"]["search_fields"]["receivedate"] = ["receivedate"]
    url = _capture(
        FDADrugInteractionDetailTool(cfg),
        {"medicinalproducts": ["ASPIRIN", "WARFARIN"], "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url
    assert QUOTED_RANGE not in url


@pytest.mark.parametrize(
    "tool_name",
    [
        "FAERS_count_reactions_by_drug_event",
        "FAERS_count_drugs_by_drug_event",
        "FAERS_count_country_by_drug_event",
        "FAERS_count_reportercountry_by_drug_event",
        "FAERS_count_seriousness_by_drug_event",
        "FAERS_count_outcomes_by_drug_event",
    ],
)
def test_every_count_tool_accepting_receivedate_keeps_the_range_unquoted(tool_name):
    cfg = _config("fda_drug_adverse_event_tools.json", tool_name)
    url = _capture(
        FDADrugAdverseEventTool(cfg),
        {"medicinalproduct": "ASPIRIN", "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url, tool_name


@pytest.mark.parametrize(
    "tool_name",
    [
        "FAERS_count_additive_adverse_reactions",
        "FAERS_count_additive_event_reports_by_country",
        "FAERS_count_additive_reports_by_reporter_country",
        "FAERS_count_additive_seriousness_classification",
        "FAERS_count_additive_reaction_outcomes",
    ],
)
def test_every_additive_tool_accepting_receivedate_keeps_the_range_unquoted(tool_name):
    cfg = _config("fda_drug_adverse_event_tools.json", tool_name)
    url = _capture(
        FDACountAdditiveReactionsTool(cfg),
        {"medicinalproducts": ["ASPIRIN"], "receivedate": RANGE},
    )

    assert ENCODED_RANGE in url, tool_name


def test_a_multi_word_term_is_still_quoted_from_the_single_field_path():
    """The refactor must not drop the quoting rule it consolidated.

    `manufacturer_name` maps to one field, so this exercises exactly the branch
    that the range fix changed.
    """
    cfg = _config(
        "fda_drug_adverse_event_tools.json", "FAERS_count_drugs_by_drug_event"
    )
    url = _capture(FDADrugAdverseEventTool(cfg), {"manufacturer_name": "PFIZER LABS"})

    assert 'patient.drug.openfda.manufacturer_name:"PFIZER%20LABS"' in url


def test_a_multi_word_term_is_still_quoted_from_the_multi_field_path():
    cfg = _config(
        "fda_drug_adverse_event_tools.json", "FAERS_count_reactions_by_drug_event"
    )
    url = _capture(
        FDADrugAdverseEventTool(cfg),
        {"reactionmeddraverse": "ACUTE KIDNEY INJURY"},
    )

    assert url.count('"ACUTE%20KIDNEY%20INJURY"') == 2
    assert '%28patient.reaction.reactionmeddrapt:"' in url
