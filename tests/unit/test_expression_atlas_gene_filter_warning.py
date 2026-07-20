"""Regression guard for Fix-R20C-1/2: ExpressionAtlasTool's `gene`
parameter across get_baseline_expression, search_differential_experiments,
and search_experiments silently had no real filtering effect.

Confirmed live: querying the same species/condition with a real,
well-characterized gene (HK1, TP53) and a nonsense gene string
("NOTAREALGENEXYZ123") returned byte-identical result sets (same
total_baseline=123, same top experiments, gene_mentioned=false /
gene_specific_count=0 for both). Root cause: "gene_mentioned" tagging
relies on a literal-text match against EBI Search's atlas-experiments
description index, which almost never contains individual gene symbols in
generic baseline/differential dataset descriptions (confirmed live: 0/4561
hits for HK1, 1/4561 for TP53). The tool never fetches actual per-gene
expression values, so it structurally cannot filter by gene -- this is a
genuine upstream/architectural limitation, not something fixable with a
different query parameter (confirmed: GXA's /json/experiments endpoint's
own geneQuery param is also silently ignored server-side).

Rather than silently return the unfiltered catalog as if it were
gene-specific (the original bug), every gene-querying response now
includes an explicit `warning` field naming this limitation -- matching
the project's established "honest warning over silent wrong data" pattern
used for DepMap's ignored tissue/cancer_type filter in round 19.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.expression_atlas_tool import ExpressionAtlasTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return ExpressionAtlasTool({"name": "gxa_test", "fields": {"operation": operation}})


def _resp(json_body, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


_EXPERIMENTS = {
    "experiments": [
        {
            "experimentAccession": "E-GTEX-8",
            "rawExperimentType": "RNASEQ_MRNA_BASELINE",
            "experimentDescription": "The Genotype-Tissue Expression (GTEx) project v8",
            "species": "homo sapiens",
            "numberOfAssays": 17382,
            "lastUpdate": "2020-01-01",
        }
    ]
}


def _no_ebi_search_hits(url, params=None, **kwargs):
    if "ebisearch" in url:
        return _resp({"entries": []})
    return _resp(_EXPERIMENTS)


def test_get_baseline_gene_and_nonsense_gene_return_same_catalog_but_gene_warns():
    tool = _tool("get_baseline_expression")

    with patch(
        "tooluniverse.expression_atlas_tool.requests.get", side_effect=_no_ebi_search_hits
    ):
        real_gene = tool.run({"gene": "HK1", "species": "homo sapiens"})
        nonsense_gene = tool.run(
            {"gene": "NOTAREALGENEXYZ123", "species": "homo sapiens"}
        )

    assert real_gene["status"] == "success"
    assert real_gene["data"]["total_baseline"] == nonsense_gene["data"]["total_baseline"]
    # Fix-R24: get_baseline_expression's gene_mentioned/warning fields were
    # removed entirely (confirmed live the underlying text-match signal was
    # false for every real gene, not just a weak heuristic) in favor of a
    # top-level `note` pointing callers at the tool that actually supports
    # per-gene filtering.
    assert "warning" not in real_gene["data"]
    assert "gene_mentioned" not in str(real_gene["data"].get("baseline_experiments"))
    assert "HK1" in real_gene["note"]


def test_search_differential_gene_query_warns_but_condition_only_does_not():
    tool = _tool("search_differential_experiments")
    diff_experiments = {
        "experiments": [
            {
                "experimentAccession": "E-MTAB-1",
                "rawExperimentType": "RNASEQ_MRNA_DIFFERENTIAL",
                "experimentDescription": "cancer vs normal study",
                "species": "homo sapiens",
                "numberOfAssays": 20,
                "experimentalFactors": ["disease"],
            }
        ]
    }

    def fake_get(url, params=None, **kwargs):
        if "ebisearch" in url:
            return _resp({"entries": []})
        return _resp(diff_experiments)

    with patch(
        "tooluniverse.expression_atlas_tool.requests.get", side_effect=fake_get
    ):
        with_gene = tool.run({"gene": "HK1", "condition": "cancer"})
        condition_only = tool.run({"condition": "cancer"})

    assert "warning" in with_gene["data"]
    assert "warning" not in condition_only["data"]
    # Condition text filtering genuinely works and is unaffected.
    assert with_gene["data"]["experiment_count"] == 1
    assert condition_only["data"]["experiment_count"] == 1


def test_search_experiments_gene_only_query_warns():
    tool = _tool("search_experiments")

    with patch(
        "tooluniverse.expression_atlas_tool.requests.get", side_effect=_no_ebi_search_hits
    ):
        result = tool.run({"gene": "HK1"})

    assert result["status"] == "success"
    assert "warning" in result["data"]
    assert result["data"]["gene_specific_count"] == 0


def test_gene_experiment_ids_helper_deduplicates_three_call_sites():
    """The three operations now share one EBI Search helper instead of
    duplicating the request/parsing logic three times."""
    tool = _tool("get_baseline_expression")
    assert hasattr(tool, "_gene_experiment_ids")

    with patch(
        "tooluniverse.expression_atlas_tool.requests.get",
        return_value=_resp({"entries": [{"id": "E-GTEX-8"}]}),
    ) as mock_get:
        ids = tool._gene_experiment_ids("HK1")

    assert ids == {"E-GTEX-8"}
    mock_get.assert_called_once()
