"""Unit test: ChEBI ontology tools accept the 'CHEBI:' CURIE form.

Regression: ChEBI_get_ontology_parents / _children required a bare integer and
rejected 'CHEBI:16113' -- but ChEBI_search and ChEBI_get_compound emit the
prefixed accession (chebi_accession = 'CHEBI:16113'), so chaining
search -> ontology broke with "'CHEBI:16113' is not of type 'integer'". The
param now accepts integer or string and the tool strips the prefix.
"""
import glob
import json

import pytest

from tooluniverse.chebi_tool import _normalize_chebi_id


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
def test_normalize_strips_curie_prefix():
    assert _normalize_chebi_id("CHEBI:16113") == "16113"
    assert _normalize_chebi_id("chebi:16113") == "16113"
    assert _normalize_chebi_id("  CHEBI:16113 ") == "16113"


@pytest.mark.unit
def test_normalize_leaves_bare_id_untouched():
    assert _normalize_chebi_id(16113) == 16113
    assert _normalize_chebi_id("16113") == "16113"


@pytest.mark.unit
@pytest.mark.parametrize(
    "name", ["ChEBI_get_ontology_parents", "ChEBI_get_ontology_children"]
)
def test_ontology_configs_accept_string_and_integer(name):
    prop = _load(name)["parameter"]["properties"]["chebi_id"]
    assert set(prop["type"]) == {"integer", "string"}
