"""Unit test for Alliance_get_gene's nested-schema parsing.

Regression for Feature-007L-01: the Alliance of Genome Resources API
moved the gene record under a top-level "gene" key and wrapped labels as
{formatText, displayText}. The tool parsed the old flat schema, so every
field came back null while still reporting status="success" (a silent
failure that makes a real gene look nonexistent).
"""
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.alliance_genome_tool import AllianceGenomeTool


def _make_tool():
    return AllianceGenomeTool(
        {
            "name": "Alliance_get_gene",
            "type": "AllianceGenomeTool",
            "fields": {"endpoint_type": "gene_detail"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


# Minimal stand-in for the current Alliance /gene/{id} response shape.
_NESTED_RESPONSE = {
    "category": "gene",
    "gene": {
        "primaryExternalId": "HGNC:11998",
        "geneSymbol": {"formatText": "TP53", "displayText": "TP53"},
        "geneFullName": {"formatText": "tumor protein p53", "displayText": "tumor protein p53"},
        "taxon": {
            "curie": "NCBITaxon:9606",
            "name": "Homo sapiens",
            "species": {"displayName": "HUMAN", "abbreviation": "Hsa"},
        },
        "geneType": {"name": "protein_coding_gene"},
        "geneSynonyms": [
            {"displayText": "LFS1"},
            {"displayText": "TRP53"},
        ],
        "geneGenomicLocationAssociations": [{"start": 7661779, "end": 7687550}],
        "crossReferences": [
            {"referencedCurie": "RGD:70502", "displayName": "RGD"},
        ],
    },
}


@pytest.mark.unit
def test_get_gene_detail_parses_nested_schema():
    tool = _make_tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = _NESTED_RESPONSE

    with patch(
        "tooluniverse.alliance_genome_tool.requests.get", return_value=resp
    ):
        result = tool.run({"gene_id": "HGNC:11998"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["symbol"] == "TP53"
    assert data["name"] == "tumor protein p53"
    assert data["species"]["name"] == "Homo sapiens"
    assert data["species"]["taxon_id"] == "NCBITaxon:9606"
    assert data["so_term"] == "protein_coding_gene"
    assert "LFS1" in data["synonyms"]
    assert data["genomic_location"]["start"] == 7661779
    assert data["cross_references"][0]["name"] == "RGD"


def _make_search_tool():
    return AllianceGenomeTool(
        {
            "name": "Alliance_search_genes",
            "type": "AllianceGenomeTool",
            "fields": {"endpoint_type": "search_genes"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
def test_search_genes_filters_category_and_uses_curie():
    """Feature-008: autocomplete no longer honours category=gene and ids moved
    to `curie`; keep gene hits client-side and read the curie."""
    tool = _make_search_tool()
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "results": [
            {"symbol": "TP53", "name": "TP53", "curie": "HGNC:11998",
             "category": "gene_search_result"},
            {"symbol": "should-drop", "curie": "DOID:1", "name": "x",
             "category": "disease_search_result"},
            {"symbol": "tp53", "name": "tp53", "curie": "ZFIN:ZDB-GENE-1",
             "category": "gene_search_result"},
        ]
    }
    with patch(
        "tooluniverse.alliance_genome_tool.requests.get", return_value=resp
    ) as mock_get:
        result = tool.run({"query": "TP53"})

    # category=gene must NOT be sent (it now returns zero results upstream)
    assert "category" not in mock_get.call_args.kwargs.get("params", {})
    data = result["data"]
    assert len(data) == 2  # disease hit filtered out
    assert data[0]["symbol"] == "TP53"
    assert data[0]["gene_id"] == "HGNC:11998"


@pytest.mark.unit
def test_gene_phenotypes_unwraps_gene_symbol():
    """Feature-008: phenotype subject.geneSymbol is now a {displayText} object."""
    tool = AllianceGenomeTool(
        {
            "name": "Alliance_get_gene_phenotypes",
            "type": "AllianceGenomeTool",
            "fields": {"endpoint_type": "gene_phenotypes"},
            "parameter": {"type": "object", "properties": {}},
        }
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "total": 1,
        "results": [
            {
                "phenotypeStatement": "Abnormal bleeding",
                "subject": {
                    "primaryExternalId": "HGNC:11998",
                    "geneSymbol": {"formatText": "TP53", "displayText": "TP53"},
                },
            }
        ],
    }
    with patch(
        "tooluniverse.alliance_genome_tool.requests.get", return_value=resp
    ):
        result = tool.run({"gene_id": "HGNC:11998"})

    pheno = result["data"][0]
    assert pheno["gene_symbol"] == "TP53"
    assert pheno["gene_id"] == "HGNC:11998"
    assert pheno["phenotype_statement"] == "Abnormal bleeding"
