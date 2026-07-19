"""Regression guard for Fix-R24E-1/24C-1: ExpressionAtlas_get_baseline's
per-gene "gene_mentioned"/"gene_specific_count" fields were computed by
full-text-searching EBI Search's experiment *description* field for the
gene symbol. Confirmed live (independently, by two different queries) this
essentially never matches -- descriptions are one-line study summaries
that don't contain bare gene symbols -- so gene_mentioned was false for
every real gene tested, including well-known housekeeping genes, while
status stayed "success". Also confirmed live that GXA's own /json/experiments
endpoint silently ignores a geneQuery filter (identical result count with
or without it), so there is no cheap correct way to filter server-side
either. Fixed by dropping the broken fields and being explicit that this
call lists species-level baseline experiments, not gene-filtered ones.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.expression_atlas_tool import ExpressionAtlasTool

pytestmark = pytest.mark.unit

_ALL_EXPERIMENTS = {
    "experiments": [
        {
            "experimentAccession": "E-GTEX-8",
            "rawExperimentType": "RNASEQ_MRNA_BASELINE",
            "experimentDescription": "The Genotype-Tissue Expression (GTEx) project v8",
            "species": "Homo sapiens",
            "numberOfAssays": 17350,
            "lastUpdate": "20-12-2024",
        },
        {
            "experimentAccession": "E-MTAB-5214",
            "rawExperimentType": "RNASEQ_MRNA_BASELINE",
            "experimentDescription": "Baseline RNA-seq of 53 human tissues",
            "species": "Homo sapiens",
            "numberOfAssays": 927,
            "lastUpdate": "01-01-2023",
        },
        {
            "experimentAccession": "E-MTAB-1234",
            "rawExperimentType": "RNASEQ_MRNA_DIFFERENTIAL",
            "experimentDescription": "Differential experiment, should be excluded",
            "species": "Homo sapiens",
            "numberOfAssays": 10,
            "lastUpdate": "01-01-2023",
        },
    ]
}


def _tool():
    return ExpressionAtlasTool(
        {"name": "expr_atlas_test", "fields": {"operation": "get_baseline_expression"}}
    )


def _resp(json_body):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


class TestBaselineListingIsHonest:
    def test_no_gene_mentioned_field_and_note_present(self):
        tool = _tool()
        resp = _resp(_ALL_EXPERIMENTS)

        with patch(
            "tooluniverse.expression_atlas_tool.requests.get", return_value=resp
        ):
            result = tool.run({"gene": "INS", "species": "homo sapiens"})

        assert result["status"] == "success"
        assert "gene_specific_count" not in result["data"]
        for exp in result["data"]["baseline_experiments"]:
            assert "gene_mentioned" not in exp
        assert "GxA_get_experiment_expression" in result["note"]

    def test_only_baseline_experiments_returned_for_species(self):
        tool = _tool()
        resp = _resp(_ALL_EXPERIMENTS)

        with patch(
            "tooluniverse.expression_atlas_tool.requests.get", return_value=resp
        ):
            result = tool.run({"gene": "INS", "species": "homo sapiens"})

        accessions = {
            e["experiment_accession"] for e in result["data"]["baseline_experiments"]
        }
        assert accessions == {"E-GTEX-8", "E-MTAB-5214"}
        assert result["data"]["total_baseline"] == 2

    def test_sorted_by_assay_count_descending(self):
        tool = _tool()
        resp = _resp(_ALL_EXPERIMENTS)

        with patch(
            "tooluniverse.expression_atlas_tool.requests.get", return_value=resp
        ):
            result = tool.run({"gene": "INS", "species": "homo sapiens"})

        accessions = [
            e["experiment_accession"] for e in result["data"]["baseline_experiments"]
        ]
        assert accessions == ["E-GTEX-8", "E-MTAB-5214"]

    def test_only_one_http_call_made_no_ebi_search_call(self):
        """The old implementation made a second HTTP call to EBI Search's
        atlas-experiments index; that call is gone now that gene_mentioned
        isn't computed."""
        tool = _tool()
        resp = _resp(_ALL_EXPERIMENTS)

        with patch(
            "tooluniverse.expression_atlas_tool.requests.get", return_value=resp
        ) as mock_get:
            tool.run({"gene": "INS", "species": "homo sapiens"})

        assert mock_get.call_count == 1
