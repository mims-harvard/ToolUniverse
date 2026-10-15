"""enrichr_gene_enrichment_analysis ran out of memory on ordinary gene lists.

The gene/term graph is close to complete bipartite, and the tool did
``list(nx.all_simple_paths(...))`` between gene pairs and gene/term pairs just to keep the
best 20 or 5 by weight. The path count grows factorially with the number of genes:
3 genes took ~2 s, 5 genes ~8 s, 7 genes ran for minutes and the 9 target genes of a
documented network-pharmacology example (sorafenib) exhausted memory (the guard killed it
at 7 GB). Enumeration is now capped and ``metadata.paths_truncated`` says so.
"""

import itertools
from unittest.mock import patch

import pytest

from tooluniverse import enrichr_tool
from tooluniverse.enrichr_tool import EnrichrTool

pytestmark = pytest.mark.unit


def _tool():
    return EnrichrTool(
        {"name": "enrichr_gene_enrichment_analysis", "type": "EnrichrTool"}
    )


def _graph():
    G = enrichr_tool.nx.Graph()
    G.add_edge("A", "term1", weight=1.0)
    G.add_edge("term1", "B", weight=2.0)
    return G


def _fake_paths(count):
    def generator(G, source, target, **kwargs):
        return ([source, "term1", target] for _ in range(count))

    return generator


def test_enumeration_stops_at_the_cap_and_is_flagged():
    tool = _tool()
    with patch.object(enrichr_tool.nx, "all_simple_paths", _fake_paths(30000)):
        ranked = tool.rank_paths_by_weight(_graph(), "A", "B", max_paths=100)
    assert len(ranked) <= 100
    assert tool._paths_truncated is True


def test_a_generator_that_never_ends_still_terminates_when_capped():
    tool = _tool()

    def endless(G, source, target, **kwargs):
        return ([source, "term1", target] for _ in itertools.count())

    with patch.object(enrichr_tool.nx, "all_simple_paths", endless):
        ranked = tool.rank_paths_by_weight(_graph(), "A", "B", max_paths=50)
    assert len(ranked) == 50  # returned instead of hanging
    assert tool._paths_truncated is True


def test_without_a_cap_the_helpers_keep_their_old_behaviour():
    tool = _tool()
    with patch.object(enrichr_tool.nx, "all_simple_paths", _fake_paths(30)):
        ranked = tool.rank_paths_by_weight(_graph(), "A", "B")
    assert len(ranked) == 30 and tool._paths_truncated is False


def _run(genes, libs=("KEGG_2021_Human",), **caps):
    tool = _tool()
    for name, value in caps.items():
        setattr(tool, name, value)
    terms = [[0, f"term{i}", 0.01, 0, 0.5 + i / 10, list(genes)] for i in range(3)]
    with (
        patch.object(tool, "get_official_gene_name", side_effect=lambda g: g),
        patch.object(tool, "submit_gene_list", return_value="id"),
        patch.object(
            tool, "get_enrichment_results", side_effect=lambda _id, lib: {lib: terms}
        ),
    ):
        return tool.run({"gene_list": list(genes), "libs": list(libs)})


def test_small_input_is_not_truncated_and_reports_it():
    result = _run(["G1", "G2", "G3"])
    assert result["status"] == "success"
    assert result["metadata"]["paths_truncated"] is False
    assert result["data"]["connected_paths"]


def test_hitting_a_cap_is_reported_in_the_metadata():
    result = _run(
        ["G1", "G2", "G3", "G4"], MAX_PATHS_BETWEEN_GENES=2, MAX_PATHS_PER_TERM=2
    )
    assert result["status"] == "success"
    assert result["metadata"]["paths_truncated"] is True
    assert len(result["data"]["connected_paths"]) <= 2


def test_flag_resets_between_runs():
    tool = _tool()
    tool._paths_truncated = True
    terms = [[0, "term1", 0.01, 0, 0.5, ["G1", "G2"]]]
    with (
        patch.object(tool, "get_official_gene_name", side_effect=lambda g: g),
        patch.object(tool, "submit_gene_list", return_value="id"),
        patch.object(
            tool, "get_enrichment_results", side_effect=lambda _id, lib: {lib: terms}
        ),
    ):
        result = tool.run({"gene_list": ["G1", "G2"], "libs": ["L"]})
    assert result["metadata"]["paths_truncated"] is False
