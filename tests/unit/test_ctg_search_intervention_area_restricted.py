"""search_clinical_trials matched an intervention against the whole study record.

Feature-27A-1: ``search_clinical_trials`` (ClinicalTrialsSearchTool) builds its
own API parameters and passed the caller's ``intervention`` straight through as
CT.gov v2's ``query.intr``. A bare ``query.intr`` value is matched by Essie
against the entire study record -- brief summaries, arm descriptions,
eligibility text -- not against the intervention-name field, so
``intervention="Luxturna"`` returned exactly one study, NCT07681778
("Safety and Tolerability of Subretinal OPGx-RDH12-1001..."), an RDH12
gene-therapy trial whose only connection to Luxturna is the phrase "using a
method similar to approved gene therapies like Luxturna" in its brief summary.
The five real voretigene neparvovec trials were all missed. The AREA
restriction that fixes this (Fix-R13B-1/Fix-R23-1) already existed in the
sibling ``ClinicalTrialsTool._run_search`` path; these tests pin that both
paths now drive off the same ``_AREA_RESTRICTED_FIELDS`` mapping and the same
``_restrict_to_area`` helper, so they cannot drift apart again.

Feature-27A-2: with the restriction in place, a brand name that no registrant
recorded in either name field returns zero with no explanation. Confirmed live
against the raw API: ``query.intr=(AREA[InterventionName]Luxturna OR
AREA[InterventionOtherName]Luxturna)`` has ``totalCount: 0``, while
``intervention="voretigene neparvovec"`` (the INN for the same product) returns
a full set. A zero result now says so, and says it separately from the
phase-gate note, which explains a different cause of zero.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.ctg_tool import (
    ClinicalTrialsSearchTool,
    ClinicalTrialsTool,
    _restrict_to_area,
)

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/clinicaltrials_gov_tools.json"
)
_PHASE_GATE = "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3 OR AREA[Phase]PHASE4)"


@pytest.fixture
def tool():
    # Use the shipped config so the test tracks the real parameter schema.
    configs = json.loads(_CONFIG.read_text())
    cfg = next(c for c in configs if c["name"] == "search_clinical_trials")
    return ClinicalTrialsSearchTool(cfg)


def _run(tool, arguments, studies=None, total=None):
    """Run the tool against a mocked HTTP layer; return (params, result)."""
    captured = {}
    studies = [] if studies is None else studies
    payload = {
        "studies": studies,
        "totalCount": len(studies) if total is None else total,
    }

    def fake_query(endpoint_url, variables):
        captured.update(variables)
        return payload

    with patch("tooluniverse.ctg_tool.execute_RESTful_query", side_effect=fake_query):
        result = tool.run(dict(arguments))
    return captured, result


def _study(nct_id="NCT00999609", title="A real trial"):
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct_id, "briefTitle": title},
            "designModule": {"phases": ["PHASE3"]},
        }
    }


def test_plain_intervention_is_area_restricted(tool):
    params, _ = _run(tool, {"intervention": "Luxturna"})

    assert params["query.intr"] == (
        "(AREA[InterventionName]Luxturna OR AREA[InterventionOtherName]Luxturna)"
    )


def test_multiword_intervention_is_restricted_and_phrase_quoted(tool):
    params, _ = _run(tool, {"intervention": "voretigene neparvovec"})

    assert params["query.intr"] == (
        '(AREA[InterventionName]"voretigene neparvovec" OR '
        'AREA[InterventionOtherName]"voretigene neparvovec")'
    )


def test_caller_supplied_essie_syntax_is_left_alone(tool):
    # Advanced callers may pass their own AREA/boolean expressions; blindly
    # re-wrapping those would break the syntax the tool documents.
    for value in (
        "AREA[InterventionName]nivolumab",
        "pembrolizumab OR nivolumab",
        '"gene therapy"',
    ):
        params, _ = _run(tool, {"intervention": value})
        assert params["query.intr"] == value, value


def test_search_tool_uses_the_same_mapping_as_run_search(tool):
    # The drift between the two code paths is what caused this, so the
    # mapping must be the shared one, not a private copy.
    assert tool._AREA_RESTRICTED_FIELDS is ClinicalTrialsTool._AREA_RESTRICTED_FIELDS
    areas = tool._AREA_RESTRICTED_FIELDS["query.intr"]
    params, _ = _run(tool, {"intervention": "Eliquis"})
    assert params["query.intr"] == _restrict_to_area("Eliquis", areas)
    # Brand names live in the synonym field, so it must be searched too.
    assert "InterventionOtherName" in params["query.intr"]


def test_phase_gate_is_not_regressed_by_the_restriction(tool):
    params, _ = _run(tool, {"condition": "diabetes", "intervention": "metformin"})

    assert params["filter.advanced"] == _PHASE_GATE
    assert params["query.cond"] == "diabetes"


def test_zero_results_explains_the_intervention_name_restriction(tool):
    _, result = _run(tool, {"intervention": "Luxturna"}, studies=[])

    assert result["status"] == "success"
    note = result["metadata"]["note"]
    assert "InterventionOtherName" in note
    assert "generic" in note.lower()
    # It must not be mistaken for the phase-gate explanation, which is a
    # different cause of zero; both apply here, so both are named.
    assert "phase-1-only" in note


def test_zero_results_without_an_intervention_only_blames_the_phase_gate(tool):
    _, result = _run(tool, {"condition": "orofacial cleft"}, studies=[])

    note = result["metadata"]["note"]
    assert "phase-1-only" in note
    assert "InterventionOtherName" not in note


def test_caller_supplied_essie_syntax_gets_no_restriction_note(tool):
    # Nothing was restricted, so the tool must not claim it was.
    _, result = _run(tool, {"intervention": "AREA[BriefSummary]Luxturna"}, studies=[])

    assert "InterventionOtherName" not in result["metadata"]["note"]


def test_nonempty_results_keep_the_existing_phase_disclosure(tool):
    _, result = _run(tool, {"intervention": "pembrolizumab"}, studies=[_study()])

    note = result["metadata"]["note"]
    assert "Results exclude phase-1-only" in note
    assert "InterventionOtherName" not in note
    assert result["data"]["studies"][0]["NCT ID"] == "NCT00999609"


def test_schema_documents_the_name_field_restriction():
    configs = json.loads(_CONFIG.read_text())
    cfg = next(c for c in configs if c["name"] == "search_clinical_trials")
    description = cfg["parameter"]["properties"]["intervention"]["description"]

    assert "InterventionOtherName" in description
    assert "INN" in description
