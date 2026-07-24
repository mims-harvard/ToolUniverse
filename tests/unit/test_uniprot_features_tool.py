"""UniProt_get_features_by_accession returns all sequence features.

Fills the audit gap where skills wanted protein sequence features (domains,
sites, PTMs) but TU only exposed variant- and PTM-specific extracts. The new
tool uses extract_path 'features' on the UniProtKB entry.
"""

import json
import os

import pytest

pytestmark = pytest.mark.unit

_CFG = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "data", "uniprot_tools.json"
)


def _tool(name):
    for t in json.load(open(_CFG)):
        if t.get("name") == name:
            return t
    raise AssertionError(f"{name} not in uniprot_tools.json")


def test_features_tool_config():
    t = _tool("UniProt_get_features_by_accession")
    assert t["type"] == "UniProtRESTTool"
    # all features (not a type-filtered subset)
    assert t["fields"]["extract_path"] == "features"
    assert "{accession}" in t["fields"]["endpoint"]
    assert t["test_examples"][0]["accession"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
