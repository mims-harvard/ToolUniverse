"""Regression guards for filters and lookups that were silently dropped.

Each tool below accepted an input, ignored it, and returned an unfiltered or
wrong result as a success:

* MGnify_search_genomes sent ?lineage= where /genomes filters on
  ?taxon_lineage=, so every taxonomy value returned the whole 56,782-genome
  catalogue; its genome_type filter has no upstream equivalent at all.
* NeuroMorpho_search_neurons left multi-word values unquoted, so
  brain_region="entorhinal cortex" was executed as "cortex".
* GtoPdb_search_targets rewrote gene_symbol into a targetId query parameter
  that the /targets endpoint ignores.
* HPA_get_rna_expression_by_source queried a column name HPA does not have.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gtopdb_tool import GtoPdbRESTTool
from tooluniverse.hpa_tool import HPAGetRnaExpressionBySourceTool
from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool
from tooluniverse.neuromorpho_tool import NeuroMorphoTool

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# MGnify genome search
# --------------------------------------------------------------------------


def _mgnify_tool():
    return MGnifyExpandedTool(
        {"name": "MGnify_search_genomes", "fields": {"endpoint_type": "genomes"}}
    )


def _mgnify_params(arguments):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": [], "meta": {"pagination": {"count": 0}}}
    with patch("requests.get", return_value=resp) as get:
        result = _mgnify_tool()._genome_search(arguments)
    return result, (get.call_args.kwargs.get("params") if get.call_args else None)


def test_mgnify_taxonomy_uses_taxon_lineage_not_lineage():
    _, params = _mgnify_params({"taxonomy": "Bacteroides"})
    assert params["taxon_lineage"] == "Bacteroides"
    assert "lineage" not in params


def test_mgnify_no_taxonomy_sends_no_taxon_filter():
    _, params = _mgnify_params({"page_size": 3})
    assert "taxon_lineage" not in params


def test_mgnify_genome_type_fails_closed_instead_of_returning_everything():
    result, params = _mgnify_params({"genome_type": "Isolate"})
    assert result["status"] == "error"
    assert "genome_type" in result["error"]
    assert params is None, "must not issue an unfiltered request"


def test_mgnify_page_size_is_still_capped():
    _, params = _mgnify_params({"taxonomy": "Bacteroides", "page_size": 5000})
    assert params["page_size"] == 100


# --------------------------------------------------------------------------
# NeuroMorpho query quoting
# --------------------------------------------------------------------------


def _neuromorpho_query(arguments):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"_embedded": {"neuronResources": []}, "page": {}}
    tool = NeuroMorphoTool(
        {
            "name": "NeuroMorpho_search_neurons",
            "fields": {"endpoint_type": "neuron", "query_mode": "search"},
        }
    )
    with patch("requests.get", return_value=resp) as get:
        tool.run(arguments)
    return get.call_args.kwargs["params"]


def test_neuromorpho_quotes_multi_word_query_value():
    params = _neuromorpho_query(
        {"query_field": "brain_region", "query_value": "entorhinal cortex"}
    )
    assert params["q"] == 'brain_region:"entorhinal cortex"'


def test_neuromorpho_leaves_single_word_unquoted():
    params = _neuromorpho_query({"query_field": "brain_region", "query_value": "cortex"})
    assert params["q"] == "brain_region:cortex"


def test_neuromorpho_does_not_double_quote():
    params = _neuromorpho_query(
        {"query_field": "brain_region", "query_value": '"entorhinal cortex"'}
    )
    assert params["q"] == 'brain_region:"entorhinal cortex"'


def test_neuromorpho_quotes_the_filter_query_too():
    params = _neuromorpho_query(
        {
            "query_field": "species",
            "query_value": "mouse",
            "filter_field": "cell_type",
            "filter_value": "pyramidal cell",
        }
    )
    assert params["fq"] == 'cell_type:"pyramidal cell"'


# --------------------------------------------------------------------------
# GtoPdb gene symbol routing
# --------------------------------------------------------------------------


def _gtopdb_tool(endpoint):
    return GtoPdbRESTTool(
        {"name": "GtoPdb_test", "fields": {"endpoint": endpoint, "params": {}}}
    )


def test_gtopdb_target_search_maps_gene_symbol_to_gene_symbol_query():
    url = _gtopdb_tool(
        "https://www.guidetopharmacology.org/services/targets"
    )._build_url({"gene_symbol": "CHRNA7"})
    assert url.endswith("targets?geneSymbol=CHRNA7")


def test_gtopdb_target_search_still_supports_name():
    url = _gtopdb_tool(
        "https://www.guidetopharmacology.org/services/targets"
    )._build_url({"name": "dopamine"})
    assert "name=dopamine" in url
    assert "geneSymbol" not in url


def test_gtopdb_target_search_does_not_resolve_gene_symbol_to_targetid():
    """The targetId rewrite is only meaningful for /interactions endpoints."""
    tool = _gtopdb_tool("https://www.guidetopharmacology.org/services/targets")
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []
    with patch("tooluniverse.gtopdb_tool.request_with_retry", return_value=resp) as req:
        tool.run({"gene_symbol": "CHRNA7"})
    called = [c.args[2] for c in req.call_args_list if len(c.args) > 2]
    assert not any("targetId=" in u for u in called)


# --------------------------------------------------------------------------
# HPA per-source expression columns
# --------------------------------------------------------------------------


def _hpa_tool():
    return HPAGetRnaExpressionBySourceTool({"name": "HPA_get_rna_expression_by_source"})


def test_hpa_brain_uses_per_region_column_not_rnabrm():
    tool = _hpa_tool()
    requested = []

    def fake_request(gene, columns, format_type="json"):
        requested.append(columns)
        if "brain_RNA_" in columns:
            return [{"Gene": "GFAP", "Brain RNA - thalamus [nTPM]": "14782.4"}]
        return []

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {"gene_name": "GFAP", "source_type": "brain", "source_name": "thalamus"}
        )

    assert result["data"]["expression_value"] == "14782.4"
    assert result["data"]["expression_level"] == "very high"
    assert any("brain_RNA_thalamus" in c for c in requested)
    assert not any(c.endswith("rnabrm") for c in requested)


def test_hpa_tissue_uses_per_tissue_column():
    tool = _hpa_tool()

    def fake_request(gene, columns, format_type="json"):
        if "t_RNA_liver" in columns:
            return [{"Gene": "TP53", "Tissue RNA - liver [nTPM]": "15.6"}]
        return []

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {"gene_name": "TP53", "source_type": "tissue", "source_name": "liver"}
        )
    assert result["data"]["expression_value"] == "15.6"


def test_hpa_picks_the_queried_gene_not_a_synonym_hit():
    """HPA's search matches synonyms, so search=GFAP also returns HGFAC."""
    tool = _hpa_tool()

    def fake_request(gene, columns, format_type="json"):
        return [
            {"Gene": "HGFAC", "Brain RNA - thalamus [nTPM]": "1.6"},
            {"Gene": "GFAP", "Brain RNA - thalamus [nTPM]": "14782.4"},
        ]

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {"gene_name": "GFAP", "source_type": "brain", "source_name": "thalamus"}
        )
    assert result["data"]["expression_value"] == "14782.4"


def test_hpa_falls_back_to_aggregate_column_when_no_per_source_value():
    tool = _hpa_tool()
    requested = []

    def fake_request(gene, columns, format_type="json"):
        requested.append(columns)
        if columns.endswith("rnabrm"):
            return [{"Gene": "GFAP"}]
        return [{"Gene": "GFAP"}]

    with patch.object(tool, "_make_api_request", side_effect=fake_request):
        result = tool.run(
            {"gene_name": "GFAP", "source_type": "brain", "source_name": "thalamus"}
        )
    assert result["status"] == "success"
    assert any(c.endswith("rnabrm") for c in requested)


def test_hpa_expression_level_buckets():
    categorize = HPAGetRnaExpressionBySourceTool._categorize_expression
    assert categorize("14782.4") == "very high"
    assert categorize("15.6") == "high"
    assert categorize("1.5") == "medium"
    assert categorize("0.5") == "low"
    assert categorize("0.05") == "very low"
    assert categorize("N/A") == "unknown"
    assert categorize(None) == "unknown"
