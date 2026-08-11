"""A multi-word drug name must reach openFDA percent-encoded exactly ONCE.

Regression for Fix-R36. The two builders that take a `medicinalproducts` LIST
percent-encoded each name themselves before the finished query went through the
one encode that every openFDA query gets, so the name was encoded twice.

What that did upstream, established live against api.fda.gov rather than by
reasoning about ``quote()``:

  the space in "SODIUM CHLORIDE" became %2520; openFDA decoded that once, so
  Lucene received the literal term ``SODIUM%20CHLORIDE``, whose analyzer split
  it on the non-word ``%`` and left the field bound to the first token alone.
  The query silently widened from one product to every product whose name
  merely CONTAINS "SODIUM" -- sodium bicarbonate, sodium valproate, docusate
  sodium, and so on.

  search=patient.drug.medicinalproduct:%22SODIUM%20CHLORIDE%22&count=serious
    -> 74,079 serious + 16,715 non-serious =  90,794
  search=patient.drug.medicinalproduct:SODIUM%2520CHLORIDE&count=serious
    -> 605,620 serious + 173,560 non-serious = 779,180
  search=patient.drug.medicinalproduct:SODIUM&count=serious
    -> 779,180   <- identical, confirming the query collapsed to the first token

An 8.6x over-count, and the same shape on the detail path: the pair
("SODIUM CHLORIDE", "ASPIRIN") totalled 9,043 reports correctly encoded and
84,200 double-encoded.

This is the dangerous direction for a pharmacovigilance count. The output was
not empty and not obviously malformed -- it was RICHER than the truth, so
nothing looked broken, and any disproportionality ratio built on it was
inflated in the direction that manufactures a safety signal.

The fix routes drug names through the same `_render_clause` helper as every
other value, so the name is Lucene-quoted once and percent-encoded once. These
tests pin the rendered URL for both classes, against mocked HTTP, no network.
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
    FDADrugInteractionDetailTool,
)

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

# quote() is called with safe='+:"', so the Lucene double quotes survive into the
# URL literally and the space becomes %20. A SECOND encode is what turned this
# into %2520, and it is exactly what must never reappear.
ENCODED_ONCE = 'patient.drug.medicinalproduct:"SODIUM%20CHLORIDE"'
DOUBLE_ENCODED = "%2520"


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
    """Run the tool with HTTP mocked and return the URL it built."""
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response()

    with patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get):
        tool.run(arguments)
    assert urls, "tool made no request"
    return urls[0]


@pytest.mark.parametrize(
    "tool_name",
    [
        "FAERS_count_additive_adverse_reactions",
        "FAERS_count_additive_event_reports_by_country",
        "FAERS_count_additive_reports_by_reporter_country",
        "FAERS_count_additive_seriousness_classification",
        "FAERS_count_additive_reaction_outcomes",
        "FAERS_count_additive_administration_routes",
    ],
)
def test_additive_count_tools_encode_a_multi_word_drug_name_once(tool_name):
    cfg = _config("fda_drug_adverse_event_tools.json", tool_name)
    url = _capture(
        FDACountAdditiveReactionsTool(cfg),
        {"medicinalproducts": ["SODIUM CHLORIDE"]},
    )

    assert ENCODED_ONCE in url, tool_name
    assert DOUBLE_ENCODED not in url, tool_name


def test_combination_detail_tool_encodes_a_multi_word_drug_name_once():
    cfg = _config(
        "fda_drug_adverse_event_detail_tools.json",
        "FAERS_search_reports_by_drug_combination",
    )
    url = _capture(
        FDADrugInteractionDetailTool(cfg),
        {"medicinalproducts": ["SODIUM CHLORIDE", "ASPIRIN"]},
    )

    assert ENCODED_ONCE in url
    assert DOUBLE_ENCODED not in url
    # The second name is single-token, so it must arrive bare -- quoting is only
    # applied where Lucene would otherwise split the term.
    assert "patient.drug.medicinalproduct:ASPIRIN" in url


def test_every_name_in_a_list_is_quoted_not_just_the_first():
    """The OR clause is built per name; a later name must not be left raw."""
    cfg = _config(
        "fda_drug_adverse_event_tools.json", "FAERS_count_additive_adverse_reactions"
    )
    url = _capture(
        FDACountAdditiveReactionsTool(cfg),
        {"medicinalproducts": ["ASPIRIN", "SODIUM CHLORIDE", "FOLIC ACID"]},
    )

    assert ENCODED_ONCE in url
    assert 'patient.drug.medicinalproduct:"FOLIC%20ACID"' in url
    assert DOUBLE_ENCODED not in url


def test_a_single_word_drug_name_is_unchanged_by_the_fix():
    """Single-token names never hit the defect; they must stay byte-identical.

    Verified live: ASPIRIN counts 435,388 serious + 182,287 non-serious both
    before and after the fix, matching the API called directly.
    """
    cfg = _config(
        "fda_drug_adverse_event_tools.json",
        "FAERS_count_additive_seriousness_classification",
    )
    url = _capture(
        FDACountAdditiveReactionsTool(cfg), {"medicinalproducts": ["ASPIRIN"]}
    )

    assert "patient.drug.medicinalproduct:ASPIRIN" in url
    assert '"' not in url.split("search=")[1].split("&")[0]
