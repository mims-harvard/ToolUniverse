"""Every FAERS drug-name lookup must search the SAME three openFDA fields.

Four separate tool families had each grown their own drug-name field list, so
the same question about the same drug returned three different totals depending
on which tool the caller happened to reach for -- with nothing in any response
saying the totals were not comparable. `FAERS_DRUG_NAME_FIELDS` in
`tooluniverse.openfda_adv_tool` is now the single list, and carries the measured
evidence for why it is a union (no one field is a superset: tofacitinib counts
13,075 reports under `medicinalproduct` alone against 186,783 across all three).

This file is the anti-drift device. It fails if any FAERS drug-name search
parameter -- in Python or in a JSON config -- wanders off that list again.

Hermetic: no test here makes a network call. The query builders are exercised
directly, and the tools whose clause is only observable through their request
have both `requests.get` AND `request_with_retry` stubbed -- patching
`requests.get` alone is NOT enough, since the count tools issue their
denominator probe through `request_with_retry` -> `requests.request`.
"""

import json
import sys
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.faers_analytics_tool import _drug_clause  # noqa: E402
from tooluniverse.openfda_adv_tool import (  # noqa: E402
    FAERS_DRUG_NAME_FIELDS,
    FDACountAdditiveReactionsTool,
    FDADrugInteractionDetailTool,
    faers_drug_name_clause,
)

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

CONFIG_FILES = [
    "fda_drug_adverse_event_tools.json",
    "fda_drug_adverse_event_detail_tools.json",
]

# The two spellings a FAERS config uses for "the drug the caller asked about":
# singular for the one-drug tools, plural for the list-taking ones.
DRUG_PARAMETERS = ("medicinalproduct", "medicinalproducts")


@lru_cache(maxsize=None)
def _configs(filename):
    """Parsed config file, cached -- these are 30-150 KB each and read repeatedly."""
    return tuple(json.loads((DATA_DIR / filename).read_text()))


def _config(filename, name):
    return next(c for c in _configs(filename) if c["name"] == name)


def _declared_drug_field_lists():
    """(config file, tool name, parameter, fields) for every drug-name mapping."""
    found = []
    for filename in CONFIG_FILES:
        for config in _configs(filename):
            search_fields = config.get("fields", {}).get("search_fields", {})
            for parameter in DRUG_PARAMETERS:
                if parameter in search_fields:
                    found.append(
                        (filename, config["name"], parameter, search_fields[parameter])
                    )
    return found


# Bound once: `parametrize` needs it for both argvalues and ids, and the guard
# test below reuses it rather than re-sweeping.
DECLARED = _declared_drug_field_lists()


def _drug_parameters_in_schema():
    """(config file, tool name, parameter) for every drug parameter a caller can pass."""
    found = []
    for filename in CONFIG_FILES:
        for config in _configs(filename):
            properties = config.get("parameter", {}).get("properties", {})
            for parameter in DRUG_PARAMETERS:
                if parameter in properties:
                    found.append((filename, config["name"], parameter))
    return found


# ---- 1. the JSON configs ----


def test_every_drug_parameter_a_caller_can_pass_declares_its_fields():
    """Omission has to be as loud as divergence.

    The equality check below only visits parameters that are already declared,
    so a config that simply leaves `medicinalproducts` out of `search_fields`
    would slip past it -- which is exactly what
    FAERS_search_reports_by_drug_combination used to do while its Python
    hardcoded the fields. This also guards the guard: an empty sweep would make
    every check in this section vacuous.
    """
    declared = {(f, t, p) for f, t, p, _ in DECLARED}
    undeclared = [x for x in _drug_parameters_in_schema() if x not in declared]
    assert not undeclared, f"drug parameters with no search_fields entry: {undeclared}"
    assert len(declared) >= 23, f"only found {len(declared)} drug-name mappings"


@pytest.mark.parametrize(
    "filename,tool_name,parameter,fields",
    DECLARED,
    ids=[f"{t}:{p}" for _, t, p, _ in DECLARED],
)
def test_every_config_drug_parameter_maps_to_the_canonical_union(
    filename, tool_name, parameter, fields
):
    """Exactly the canonical list -- same fields, same order, nothing extra.

    `fields.search_fields` is what a caller inspects to learn what a tool
    searches, so a config that declares fewer fields than the tool now uses is
    a lie about the tool's own behaviour, not merely a stale comment.
    """
    assert fields == FAERS_DRUG_NAME_FIELDS, (
        f"{filename}:{tool_name}.{parameter} declares {fields}, "
        f"expected {FAERS_DRUG_NAME_FIELDS}"
    )


# ---- 2. the analytics clause ----


def test_analytics_drug_clause_is_the_parenthesized_three_field_union():
    """`_drug_clause` feeds the disproportionality contingency table.

    Restricted to generic-or-brand it computed MEFLOQUINE's ROR from 156 of the
    drug's 751 reports, and returned "no reports" for YELLOW FEVER VACCINE,
    which has 111.

    Pinned as an equality rather than by membership so the assertion also
    catches a wrong field ORDER or an extra clause, and so the parentheses --
    load-bearing because this clause is AND-ed with a reaction filter and Lucene
    binds AND tighter than OR -- cannot be dropped.
    """
    expected = (
        "(" + "+OR+".join(f'{f}:"MEFLOQUINE"' for f in FAERS_DRUG_NAME_FIELDS) + ")"
    )
    assert _drug_clause("MEFLOQUINE") == expected


def test_the_analytics_clause_and_the_raw_search_tool_share_one_renderer():
    """Same helper, differing only in the joiner the transport forces."""
    assert _drug_clause("MEFLOQUINE") == faers_drug_name_clause("MEFLOQUINE")
    assert faers_drug_name_clause("MEFLOQUINE", joiner=" OR ") == _drug_clause(
        "MEFLOQUINE"
    ).replace("+OR+", " OR ")


# ---- 3. the interaction tool's AND semantics ----


class _Response:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"results": [], "meta": {"results": {"total": 0}}}


def _capture_url(tool, arguments):
    """Run `tool` with EVERY network path stubbed and return the URL it built.

    Both stubs are required: these tools issue their main request through
    `requests.get` and their denominator probe through `request_with_retry` ->
    `requests.request`, so patching only the former lets the probe escape to
    api.fda.gov.
    """
    urls = []

    def fake_get(url, **_kwargs):
        urls.append(url)
        return _Response()

    def fake_retry(*_args, **_kwargs):
        # The denominator probe's URL is never asserted on; this stub exists
        # only so the probe cannot reach api.fda.gov.
        return _Response()

    with (
        patch("tooluniverse.openfda_adv_tool.requests.get", side_effect=fake_get),
        patch(
            "tooluniverse.openfda_adv_tool.request_with_retry", side_effect=fake_retry
        ),
    ):
        tool.run(arguments)
    assert urls, "tool made no request"
    return urls[0]


def test_interaction_tool_keeps_each_drug_group_parenthesized_under_the_and():
    """Co-occurrence: the AND asks whether BOTH drugs are on the SAME report.

    Lucene binds AND tighter than OR, so dropping the parentheses would parse
    `a:X OR b:X AND a:Y OR b:Y` as `a:X OR (b:X AND a:Y) OR b:Y` -- an "either
    drug" query wearing an interaction query's name, returning far MORE reports
    rather than an obvious error.
    """
    tool = FDADrugInteractionDetailTool(
        _config(
            "fda_drug_adverse_event_detail_tools.json",
            "FAERS_search_reports_by_drug_combination",
        )
    )
    url = _capture_url(tool, {"medicinalproducts": ["WARFARIN", "ASPIRIN"]})

    for drug in ("WARFARIN", "ASPIRIN"):
        group = (
            "%28"
            + "+OR+".join(f'{field}:"{drug}"' for field in FAERS_DRUG_NAME_FIELDS)
            + "%29"
        )
        assert group in url, f"{drug} group not parenthesized in {url}"
    assert "%29+AND+%28" in url, f"drug groups not AND-ed in {url}"


def test_additive_tool_or_s_the_per_drug_groups_rather_than_and_ing_them():
    """The mirror case: `medicinalproducts` on a COUNT tool is a union.

    Same three-field group per drug, but joined with OR -- pinned here so a
    future edit cannot swap the two tools' semantics while both still "search
    all three fields".
    """
    tool = FDACountAdditiveReactionsTool(
        _config(
            "fda_drug_adverse_event_tools.json",
            "FAERS_count_additive_adverse_reactions",
        )
    )
    url = _capture_url(tool, {"medicinalproducts": ["WARFARIN", "ASPIRIN"]})

    assert "%29+OR+%28" in url, f"drug groups not OR-ed in {url}"
    assert "+AND+" not in url.split("&count=")[0], f"unexpected AND in {url}"


# ---- 4. the raw openFDA search tool ----


def test_openfda_search_drug_events_uses_the_same_union():
    """`OpenFDA_search_drug_events` builds its Lucene query in Python.

    It sends the query as a `requests` `params` value, so its operators are
    spelled " OR "/" AND " with spaces rather than "+OR+"/"+AND+" -- a literal
    "+" there would be percent-encoded to %2B and reach openFDA as a plus sign.
    The FIELDS must still be the canonical three.
    """
    from tooluniverse.openfda_tool import OpenFDADrugEventsTool

    config = next(
        c
        for c in _configs("openfda_tools.json")
        if c.get("type") == "OpenFDADrugEventsTool"
    )

    captured = {}

    def fake_request(_session, _method, _url, **kwargs):
        captured.update(kwargs.get("params") or {})
        raise RuntimeError("request intercepted")

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry", side_effect=fake_request
    ):
        OpenFDADrugEventsTool(config).run(
            {"drug_name": "SEROQUEL", "reaction": "Haemorrhage"}
        )

    search = captured["search"]
    for field in FAERS_DRUG_NAME_FIELDS:
        assert f'{field}:"SEROQUEL"' in search, f"{field} missing from {search}"
    assert search.startswith("("), search
    assert ") AND patient.reaction.reactionmeddrapt:" in search, search
