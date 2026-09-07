"""Regression guard for Fix-R58-4: guideline searches reported a page of rows
as if it were the whole corpus.

Five of the six guideline backends that publish a match count parsed it and
threw it away with a bare expression statement -- `data.get("hitCount", 0)`,
`int(total.text) ...`, `data.get("meta", {})` -- while NICE and WHO IRIS
never read theirs at all. Every one of these tools then returned a bare
list, so there was nowhere to put the figure even once read.

Totals confirmed live against the hosts the tools call:

    NICE      q=infection            -> resultCount 1057 (15 rows served)
    TRIP      criteria=vancomycin    -> <total>12638</total>, <count>20</count>
    EuropePMC guideline query        -> hitCount 9972+
    OpenAlex  works?search=...       -> meta.count 18266
    WHO IRIS  query=tuberculosis     -> page.totalElements 28435
    PubMed    therapeutic plasma exchange -> esearch count 94

Note TRIP's `<count>` is the size of the page it chose to send, not a match
count: limit=3 answered `<count>20</count>`. Publishing that as the total
would be the very defect being fixed, so only `<total>` is used.

The six now share the {status, data, metadata} envelope already used by
PubMed_Guidelines_Search and by EuropePMC_search_articles elsewhere in the
repo. The remaining guideline searches (GIN, CMA, SIGN x2, CTFPHC x2) keep
their bare-list contract deliberately: their sources publish no match count,
so an envelope could only report `total == len(results)`.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.unified_guideline_tools import _guideline_envelope

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "unified_guideline_tools.json"
)

ENVELOPED = [
    "NICE_Clinical_Guidelines_Search",
    "PubMed_Guidelines_Search",
    "EuropePMC_Guidelines_Search",
    "TRIP_Database_Guidelines_Search",
    "WHO_Guidelines_Search",
    "OpenAlex_Guidelines_Search",
]

BARE_LIST = [
    "GIN_Guidelines_Search",
    "CMA_Guidelines_Search",
    "SIGN_search_guidelines",
    "SIGN_list_guidelines",
    "CTFPHC_list_guidelines",
    "CTFPHC_search_guidelines",
]


def _configs():
    return {c["name"]: c for c in json.loads(_CONFIG.read_text())}


def test_every_search_tool_is_classified():
    """A new guideline search must be put in one list or the other.

    Both lists are hand-maintained, so without this a 13th search tool added
    to the config lands in neither and is silently unguarded.
    """
    searches = {
        name
        for name in _configs()
        if "Search" in name or "search" in name or "list" in name
    }

    assert searches == set(ENVELOPED) | set(BARE_LIST)


@pytest.mark.parametrize("name", ENVELOPED)
def test_declared_schema_admits_the_envelope_actually_returned(name):
    """PubMed's round-57 envelope validated against neither oneOf branch."""
    from jsonschema import validate

    sample = {
        "status": "success",
        "data": [{"title": "A guideline", "url": "https://example.org/g"}],
        "metadata": {
            "total": 1057,
            "retrieved": 15,
            "returned": 1,
            "truncated": True,
            "source": "NICE",
        },
    }
    validate(sample, _configs()[name]["return_schema"])


@pytest.mark.parametrize("name", ENVELOPED)
def test_error_branch_survives_the_conversion(name):
    """Each tool still returns an error object on failure."""
    from jsonschema import validate

    validate({"error": "boom"}, _configs()[name]["return_schema"])


@pytest.mark.parametrize("name", BARE_LIST)
def test_countless_sources_keep_their_bare_list(name):
    """Deliberate: these have no upstream total to report.

    Wrapping them would mean publishing `total == len(results)`, which is the
    page-size-as-total defect this change removes elsewhere.
    """
    schema = _configs()[name]["return_schema"]
    branches = schema.get("oneOf", [schema])
    assert any(b.get("type") == "array" for b in branches), (
        f"{name} was converted to an envelope but has no match count to put in it"
    )


def test_upstream_total_and_truncation_are_reported():
    env = _guideline_envelope([{"t": 1}], total=1057, retrieved=15, source="NICE")

    assert env["status"] == "success"
    assert env["data"] == [{"t": 1}]
    meta = env["metadata"]
    assert meta["total"] == 1057
    assert meta["retrieved"] == 15
    assert meta["returned"] == 1
    assert meta["truncated"] is True
    assert meta["source"] == "NICE"
    # A bare `truncated: true` states the fact and withholds the remedy, so
    # every sibling discloser in the repo pairs the flag with a sentence.
    assert "1057" in meta["truncation_note"]
    assert "Raise `limit`" in meta["truncation_note"]


def test_client_side_filtering_is_not_mistaken_for_upstream_truncation():
    """returned < retrieved means this tool dropped rows, not that the source
    had fewer -- only total > retrieved is upstream truncation."""
    env = _guideline_envelope([{"t": 1}], total=3, retrieved=3, source="Europe PMC")

    assert env["metadata"]["returned"] == 1
    assert env["metadata"]["retrieved"] == 3
    assert env["metadata"]["truncated"] is False
    assert "truncation_note" not in env["metadata"]


def test_absent_total_is_null_not_the_page_size():
    """A WHO topic page is a curated list and publishes no match count."""
    env = _guideline_envelope([{"t": 1}, {"t": 2}], total=None, retrieved=2)

    assert env["metadata"]["total"] is None
    assert env["metadata"]["truncated"] is False
    assert env["metadata"]["returned"] == 2


def test_retrieved_defaults_to_the_rows_given():
    env = _guideline_envelope([{"t": 1}, {"t": 2}], total=9)

    assert env["metadata"]["retrieved"] == 2
    assert env["metadata"]["truncated"] is True


def test_source_is_omitted_when_not_supplied():
    env = _guideline_envelope([], total=0)

    assert "source" not in env["metadata"]
