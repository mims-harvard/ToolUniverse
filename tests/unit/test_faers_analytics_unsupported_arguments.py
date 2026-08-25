"""FAERS analytics: a filter this family cannot apply must not be dropped.

Regression for Fix Round 48. Every operation in faers_analytics_tool read the
two or three arguments it needed straight out of `arguments` and never looked
at the rest, so any other key was accepted, ignored, and the UNRESTRICTED
result returned as `status: success`.

Measured live 2026-08-13, byte-identical with and without the filters:

    FAERS_calculate_disproportionality
      {"drug_name": "warfarin", "adverse_event": "Haemorrhage"}
        -> a_drug_and_event = 4313
      ... plus {"patientagegroup": "6", "concomitant_drug": "aspirin"}
        -> a_drug_and_event = 4313

    FAERS_filter_serious_events
      {"drug_name": "warfarin", "seriousness_type": "death"}
        -> total_serious_events = 17327
      ... plus {"patientsex": "1", "occurcountry": "US"}
        -> total_serious_events = 17327

So a whole-database signal was handed to a caller who had asked for an
age-stratified or interaction-adjusted one, and was told it succeeded.

The spellings are not caller inventions: this tool family's own sibling
configs teach them. `patientagegroup` appears 60 times in
fda_drug_adverse_event_tools.json, whose descriptions read "all other filters
(patientsex, patientagegroup, occurcountry, serious, seriousnessdeath) are
optional".
"""

import json
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "faers_analytics_tools.json"
)

# Every operation in the family, with an undeclared record filter a caller
# could plausibly reach for and the arguments that operation legitimately
# needs. The guard lives in run(), so all six share one implementation --
# they are enumerated anyway so a future operation added without the guard
# fails here rather than shipping the defect again.
OPERATIONS = [
    ("FAERS_calculate_disproportionality", {"drug_name": "x", "adverse_event": "y"}),
    ("FAERS_stratify_by_demographics", {"drug_name": "x", "stratify_by": "age"}),
    ("FAERS_filter_serious_events", {"drug_name": "x", "seriousness_type": "death"}),
    ("FAERS_compare_drugs", {"drug1": "x", "drug2": "y", "adverse_event": "z"}),
    ("FAERS_analyze_temporal_trends", {"drug_name": "x", "adverse_event": "y"}),
    ("FAERS_rollup_meddra_hierarchy", {"drug_name": "x"}),
]


@lru_cache(maxsize=None)
def _configs():
    """Cached -- this file is re-read once per parametrised case otherwise."""
    with open(DATA_FILE) as f:
        return {t["name"]: t for t in json.load(f)}


def _make_tool(name):
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    return FAERSAnalyticsTool(_configs()[name])


def _no_network():
    """Any openFDA request at all fails the test that installs this.

    The point of the guard is that it refuses BEFORE spending a request; a
    version that ran the query and then complained would still have paid for
    the wrong answer.
    """

    def explode(*args, **kwargs):
        raise AssertionError("openFDA was contacted despite an unsupported argument")

    return patch("tooluniverse.faers_analytics_tool.request_with_retry", explode)


@pytest.mark.parametrize("tool_name,valid_args", OPERATIONS)
def test_unsupported_filter_is_refused_before_any_request(tool_name, valid_args):
    tool = _make_tool(tool_name)
    with _no_network():
        result = tool.run(dict(valid_args, patientagegroup="6"))

    assert result["status"] == "error", (
        f"{tool_name} accepted patientagegroup and answered anyway: {result}"
    )
    assert "patientagegroup" in result["error"]


def test_error_names_the_tool_that_can_stratify():
    """A record filter has a real home in this family; the error must say so."""
    tool = _make_tool("FAERS_calculate_disproportionality")
    with _no_network():
        result = tool.run(
            {
                "drug_name": "warfarin",
                "adverse_event": "Haemorrhage",
                "patientagegroup": "6",
                "concomitant_drug": "aspirin",
            }
        )

    assert result["status"] == "error"
    # Both rejected arguments are named -- reporting only the first would let a
    # caller fix one and be surprised by the other.
    assert "patientagegroup" in result["error"]
    assert "concomitant_drug" in result["error"]
    assert "FAERS_stratify_by_demographics" in result["error"]


def test_declared_aliases_are_not_rejected():
    """Control: `drug`/`reaction` are declared aliases and must still route.

    Guards this shape of fix against its own obvious failure mode -- rejecting
    the alias spellings run() normalises, which would break every caller using
    the documented short names.
    """
    tool = _make_tool("FAERS_calculate_disproportionality")
    assert (
        tool._unsupported_arguments({"drug": "warfarin", "reaction": "Haemorrhage"})
        is None
    )


def test_compare_drugs_list_alias_is_not_rejected():
    tool = _make_tool("FAERS_compare_drugs")
    assert (
        tool._unsupported_arguments(
            {"drugs": ["heparin", "bivalirudin"], "adverse_event": "Thrombocytopenia"}
        )
        is None
    )


def test_none_valued_unknown_argument_is_ignored():
    """Passing an explicit null must stay equivalent to omitting the key."""
    tool = _make_tool("FAERS_calculate_disproportionality")
    assert (
        tool._unsupported_arguments(
            {
                "drug_name": "warfarin",
                "adverse_event": "Haemorrhage",
                "patientsex": None,
            }
        )
        is None
    )


def test_known_arguments_stays_in_sync_with_the_shipped_configs():
    """`_KNOWN_ARGUMENTS` must be exactly what the six configs declare.

    It is a hand-maintained copy of data that lives in JSON, so without this it
    rots in both directions: a name dropped from it starts being refused for
    every tool, and a name left in it after a config removes it keeps being
    accepted and ignored -- the defect this module was fixed for.
    """
    from tooluniverse.faers_analytics_tool import _KNOWN_ARGUMENTS

    declared = set()
    for config in _configs().values():
        declared.update(config["parameter"]["properties"])

    assert _KNOWN_ARGUMENTS == declared, (
        f"only in _KNOWN_ARGUMENTS: {sorted(_KNOWN_ARGUMENTS - declared)}; "
        f"only in configs: {sorted(declared - _KNOWN_ARGUMENTS)}"
    )


def test_partial_schema_still_accepts_the_module_vocabulary():
    """Regression on this fix's own first version.

    The guard originally treated `parameter.properties` as a complete
    allow-list. tests/unit/test_faers_rollup_pt_truncation.py builds this tool
    from a stub declaring only `operation` and `drug_name`, so a valid
    `stratify_by="country"` was refused and that test failed -- a working call
    broken in order to police a schema that was merely incomplete.
    """
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    partial = FAERSAnalyticsTool(
        {
            "name": "FAERS_stratify_by_demographics",
            "parameter": {
                "type": "object",
                "properties": {
                    "operation": {"const": "stratify_by_demographics"},
                    "drug_name": {"type": "string"},
                },
            },
        }
    )
    assert (
        partial._unsupported_arguments(
            {"drug_name": "HYDROMORPHONE", "stratify_by": "country"}
        )
        is None
    )
    # ... while a record filter is still refused through the same stub.
    refused = partial._unsupported_arguments(
        {"drug_name": "HYDROMORPHONE", "occurcountry": "US"}
    )
    assert refused is not None and "occurcountry" in refused["error"]


def test_schema_less_stub_still_refuses_a_record_filter():
    """`{"parameter": {}}` is used by sibling tests and must stay usable."""
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    tool = FAERSAnalyticsTool(
        {"name": "FAERS_stratify_by_demographics", "parameter": {}, "fields": {}}
    )
    assert (
        tool._unsupported_arguments({"drug": "ondansetron", "stratify_by": "age"})
        is None
    )
    assert tool._unsupported_arguments({"drug": "x", "patientsex": "1"}) is not None
