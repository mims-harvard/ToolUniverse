"""Regression guard for Feature-R13A-1 (docs-only): CTD_get_chemical_diseases's
description promised "direct evidence type (therapeutic, marker/mechanism)"
that the RENCI Automat CTD mirror never actually provides for chemical-disease
edges -- confirmed via raw curl to automat.renci.org/ctd that the edge
properties for a real chemical-disease pair are exactly
{agent_type, knowledge_level, primary_knowledge_source, publications}, with no
predicate/qualified_predicate key at all (unlike the sibling chemical-gene
interaction edges, which do carry one). This is a genuine upstream data gap,
not a code bug, so the fix is a description caveat rather than a code change.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = Path(__file__).parent.parent.parent / "src/tooluniverse/data/ctd_tools.json"


def test_chemical_diseases_description_no_longer_promises_evidence_type():
    configs = json.loads(CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "CTD_get_chemical_diseases")
    description = config["description"]
    assert "including direct evidence type" not in description
    assert "predicate" in description.lower()
