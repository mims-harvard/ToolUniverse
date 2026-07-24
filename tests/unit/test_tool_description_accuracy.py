"""Regression guards for tool description-vs-actual accuracy fixes.

- gProfiler_enrichment's `gene_list` is a comma-separated STRING, but its prose
  description used to show a JSON-array example (['TP53', ...]), leading users
  to pass a list and hit "Expected string, got list".
- HPA_get_protein_interactions_by_gene is non-functional (HPA dropped the ppi
  column) yet advertised a working-sounding capability; its description must now
  flag the deprecation.
"""
import glob
import json

import pytest


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


@pytest.mark.unit
def test_gprofiler_description_matches_comma_string_schema():
    tool = _load("gProfiler_enrichment")
    desc = tool["description"]
    gene_list = tool["parameter"]["properties"]["gene_list"]
    # Schema is a plain string parameter...
    assert gene_list["type"] == "string"
    # ...so the description must not show a JSON-array example that would error.
    assert "['TP53'" not in desc and "[\"TP53\"" not in desc
    assert "comma-separated" in desc.lower()


@pytest.mark.unit
def test_hpa_ppi_description_flags_deprecation():
    tool = _load("HPA_get_protein_interactions_by_gene")
    desc = tool["description"].lower()
    assert "deprecated" in desc or "no longer" in desc
    # Points users at a working alternative.
    assert "string_get_interactions" in desc or "ebiproteins_get_interactions" in desc
