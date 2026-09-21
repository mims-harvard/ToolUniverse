"""The documented annotation_type values must be the ones Europe PMC accepts."""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/europepmc_annotations_tools.json"
)

# Verified against annotationsByArticleIds across four articles. The value
# 'Genes & Proteins' was documented for a long time and always returned zero
# annotations; Europe PMC spells it 'Gene_Proteins'.
VERIFIED_TYPES = {
    "Chemicals",
    "Diseases",
    "Organisms",
    "Gene_Proteins",
    "Gene Ontology",
    "Accession Numbers",
    "Experimental Methods",
    "Gene Disease Relationship",
    "Resources",
    "Sequence",
    "Cell Line",
}


def _annotation_type_enums():
    tools = json.loads(CONFIG.read_text())
    for tool in tools:
        props = (tool.get("parameter", {}) or {}).get("properties", {}) or {}
        if "annotation_type" in props:
            yield tool["name"], props["annotation_type"]


def test_annotation_type_is_constrained_to_verified_values():
    found = list(_annotation_type_enums())
    assert found, "expected at least one tool exposing annotation_type"
    for name, schema in found:
        values = {v for v in schema.get("enum", []) if v is not None}
        assert values, f"{name} must constrain annotation_type to an enum"
        assert values == VERIFIED_TYPES, f"{name} exposes unverified values"


def test_the_dead_value_is_gone():
    """'Genes & Proteins' silently returned nothing; it must not be advertised."""
    raw = CONFIG.read_text()
    assert "Genes & Proteins" not in raw
    assert "Gene_Proteins" in raw
