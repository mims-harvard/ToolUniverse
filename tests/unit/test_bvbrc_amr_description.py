"""Regression guard: BVBRC_search_amr description must not imply organism filtering.

The tool has no organism/species parameter (only antibiotic / genome_id /
resistant_phenotype), but its description ended with "Example: search for
methicillin resistance in Staphylococcus aureus", implying an organism-scoped
search that silently doesn't exist. The description now states there is no
organism parameter and how to scope to an organism via genome_id.
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
def test_amr_has_no_organism_param():
    props = _load("BVBRC_search_amr")["parameter"]["properties"]
    assert "organism" not in props and "species" not in props


@pytest.mark.unit
def test_amr_description_does_not_imply_organism_search():
    desc = _load("BVBRC_search_amr")["description"]
    # No misleading organism-scoped example; explicitly says no organism param.
    assert "in Staphylococcus aureus" not in desc
    assert "no organism" in desc.lower()
    assert "genome_id" in desc
