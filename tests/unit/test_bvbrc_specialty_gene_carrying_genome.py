"""Regression guard for Fix-R58-1: BVBRC_search_specialty_genes named the
wrong species as the carrier of a resistance gene.

`sp_gene` rows carry two different organism fields. `organism` is the
organism of BV-BRC's *reference annotation source*; `genome_name` is the
genome the hit was actually found in. They routinely disagree, and the tool
selected only `organism` -- so "which species in my ICU carry blaKPC" was
answered with the reference organism.

Confirmed live against the host the tool calls
(https://www.bv-brc.org/api/sp_gene/?eq(gene,blaKPC)&limit(3)):

    genome_id 573.22436  organism "Enterobacteriaceae"
                         genome_name "Klebsiella pneumoniae strain CRK0113"
    genome_id 550.1655   organism "Klebsiella pneumoniae"
                         genome_name "Enterobacter cloacae strain 1-RC-17-04409-1"

The second row is the damaging one: the tool reported *K. pneumoniae* for an
*E. cloacae* genome, and contradicted its own adjacent `taxon_id` 550, which
is E. cloacae. The sibling BVBRC_search_amr already selects `genome_name`.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.bvbrc_tool import BVBRCTool

pytestmark = pytest.mark.unit

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "bvbrc_tools.json"
)


def _tool(name="BVBRC_search_specialty_genes"):
    """Build the tool from its shipped config, so routing matches production."""
    cfg = next(c for c in json.loads(_CONFIG.read_text()) if c["name"] == name)
    return BVBRCTool(cfg)


def _run_capturing_query(arguments, name="BVBRC_search_specialty_genes"):
    """Run the tool against a stubbed BV-BRC and return the query string sent."""
    captured = {}

    def fake_request(core, query):
        captured["core"] = core
        captured["query"] = query
        return [], None

    tool = _tool(name)
    with patch.object(tool, "_make_request_with_total", side_effect=fake_request):
        tool.run(arguments)
    return captured


def test_carrying_genome_name_is_requested():
    captured = _run_capturing_query({"gene": "blaKPC", "limit": 3})

    assert captured["core"] == "sp_gene"
    assert "genome_name" in captured["query"], (
        "genome_name is the genome carrying the resistance gene; without it "
        "the only organism field returned is BV-BRC's reference-annotation "
        "organism, which names a different species"
    )


def test_reference_organism_is_still_returned_alongside_it():
    """The fix is additive -- `organism` keeps its old place in the payload."""
    captured = _run_capturing_query({"gene": "blaKPC", "limit": 3})

    assert "organism" in captured["query"]
    assert "taxon_id" in captured["query"]


def test_select_fields_match_the_amr_sibling_convention():
    """BVBRC_search_amr already selects genome_name; the two should agree."""
    captured = _run_capturing_query({"genome_id": "550.1655"}, name="BVBRC_search_amr")

    assert "genome_name" in captured["query"]
