"""Regression guard for Feature-R15B-1: gnomad_get_gene_constraints and
gnomad_get_constraint have near-identical names and both live under
gnomAD-constraint-sounding categories, but only gnomad_get_constraint
returns the full panel (pLI + LOEUF + missense Z-score + synonymous
Z-score) -- confirmed live that gnomad_get_gene_constraints omits mis_z,
syn_z, and LOEUF entirely. A researcher grepping "gnomad" + "constraint"
and picking the more generic-sounding name would silently get an
incomplete answer. gnomad_get_gene_constraints' description now says so
and points to the sibling tool.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG_PATH = Path(__file__).parent.parent.parent / "src/tooluniverse/data/gnomad_tools.json"


def test_gene_constraints_description_notes_missing_fields_and_alternative():
    configs = json.loads(CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "gnomad_get_gene_constraints")
    description = config["description"]
    assert "LOEUF" in description
    assert "gnomad_get_constraint" in description
