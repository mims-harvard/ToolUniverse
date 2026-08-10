"""Regression guard: CTD_get_chemical_diseases's description must describe
the evidence its *current* backend actually provides.

Originally the RENCI Automat mirror's chemical-disease edges carried no
predicate/qualified_predicate at all, so the description needed a caveat
that "direct evidence type" wasn't available. That mirror has since been
decommissioned; the tool now queries mydisease.info's cached CTD data,
which DOES carry a real evidence type (`direct_evidence`: "marker/mechanism"
or "therapeutic", mapped into `qualified_predicate`). The description should
reflect this current, better backend rather than the old RENCI-specific
caveat.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = Path(__file__).parent.parent.parent / "src/tooluniverse/data/ctd_tools.json"


def test_chemical_diseases_description_mentions_evidence_type():
    configs = json.loads(CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "CTD_get_chemical_diseases")
    description = config["description"]
    assert "evidence type" in description.lower()
    assert "marker/mechanism" in description
    assert "therapeutic" in description


def test_chemical_diseases_description_does_not_reference_decommissioned_backend_as_current():
    configs = json.loads(CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "CTD_get_chemical_diseases")
    description = config["description"]
    assert "mydisease.info" in description
