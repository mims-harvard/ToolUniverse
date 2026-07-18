"""Regression guard for two docs-only fixes in round 14.

Feature-R14B-1: CATH_get_superfamily's description unconditionally promised
a classification name/description. Confirmed via raw curl to cathdb.info
that classification_name/classification_description are genuinely null in
CATH's own API for some superfamilies (e.g. 1.10.530.10, the lysozyme-like
fold) -- a real upstream curation gap, not a ToolUniverse extraction bug
(the same code correctly returns the name for other superfamilies, e.g.
2.40.50.140).

Feature-R14C-1: biostudies_search's description didn't warn that common
biomedical phrases are frequently dominated by 'S-EPMC*' literature hits
(EuropePMC-collection entries) rather than actual datasets -- confirmed live
that the top 5 hits for "breast cancer transcriptomics" were literature, not
datasets.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

CATH_CONFIG_PATH = Path(__file__).parent.parent.parent / "src/tooluniverse/data/cath_tools.json"
BIOSTUDIES_CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/biostudies_tools.json"
)


def test_cath_superfamily_description_notes_possible_null_classification():
    configs = json.loads(CATH_CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "CATH_get_superfamily")
    description = config["description"]
    assert "null" in description
    assert "1.10.530.10" in description


def test_biostudies_search_description_warns_about_literature_dominance():
    configs = json.loads(BIOSTUDIES_CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "biostudies_search")
    description = config["description"]
    assert "S-EPMC" in description
    assert "biostudies_search_by_collection" in description
