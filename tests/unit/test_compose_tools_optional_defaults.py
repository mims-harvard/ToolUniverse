"""Regression guard: DrugSafetyAnalyzer's `serious_events_only` and
BiomarkerDiscoveryWorkflow's `sample_type` were wrongly marked `required`
in compose_tools.json even though each has a working `default` and their
composition functions already handle the omitted case via
`arguments.get(x, default)` -- confirmed live, both tools previously
failed schema validation when the param was omitted despite being fully
answerable without it.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.compose_scripts.drug_safety_analyzer import (
    compose as drug_safety_compose,
)
from tooluniverse.compose_scripts.biomarker_discovery import (
    compose as biomarker_compose,
)

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "compose_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found in compose_tools.json")


def test_drug_safety_analyzer_requires_only_drug_name_and_patient_sex():
    cfg = _tool_config("DrugSafetyAnalyzer")
    assert cfg["parameter"]["required"] == ["drug_name", "patient_sex"]


def test_biomarker_discovery_workflow_requires_only_disease_condition():
    cfg = _tool_config("BiomarkerDiscoveryWorkflow")
    assert cfg["parameter"]["required"] == ["disease_condition"]


def test_drug_safety_compose_defaults_serious_events_only_to_false():
    calls = []

    def fake_call_tool(name, args):
        calls.append((name, args))
        return {"result": []}

    result = drug_safety_compose(
        {"drug_name": "aspirin", "patient_sex": "Female"},
        tooluniverse=None,
        call_tool=fake_call_tool,
    )

    assert result["analysis_parameters"]["serious_events_only"] is False
    faers_call = next(c for c in calls if c[0] == "FAERS_count_reactions_by_drug_event")
    assert "serious" not in faers_call[1]


def test_drug_safety_compose_honors_explicit_serious_events_only():
    calls = []

    def fake_call_tool(name, args):
        calls.append((name, args))
        return {"result": []}

    result = drug_safety_compose(
        {"drug_name": "aspirin", "patient_sex": "Female", "serious_events_only": True},
        tooluniverse=None,
        call_tool=fake_call_tool,
    )

    assert result["analysis_parameters"]["serious_events_only"] is True
    faers_call = next(c for c in calls if c[0] == "FAERS_count_reactions_by_drug_event")
    assert faers_call[1]["serious"] == "Yes"


def test_biomarker_compose_defaults_sample_type_to_blood():
    def fake_call_tool(name, args):
        return {"result": []}

    result = biomarker_compose(
        {"disease_condition": "diabetes"},
        tooluniverse=None,
        call_tool=fake_call_tool,
    )

    assert result["sample_type"] == "blood"
