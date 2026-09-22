"""Xenbase_get_gene returned every field null.

The Alliance gene endpoint nests the record under ``gene`` with ``displayText``-wrapped
labels (``geneSymbol``, ``geneFullName``, ``geneSynonyms``) and moved locations,
cross-references and the SO type. The tool read the top-level flat keys, so
XB-GENE-484286 (tp53) came back with ``gene_id``, ``symbol`` and ``name`` all None.
The record below is trimmed from the live response.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.xenbase_tool import XenbaseTool

pytestmark = pytest.mark.unit

PAYLOAD = {
    "category": "gene_summary",
    "gene": {
        "primaryExternalId": "Xenbase:XB-GENE-484286",
        "geneSymbol": {"formatText": "tp53", "displayText": "tp53"},
        "geneFullName": {"displayText": "tumor protein p53"},
        "geneSynonyms": [{"displayText": "p53"}, {"displayText": "Trp248"}],
        "geneType": {"curie": "SO:0000704", "name": "gene"},
        "dataProvider": {"abbreviation": "XB"},
        "taxon": {
            "curie": "NCBITaxon:8364",
            "name": "Xenopus tropicalis",
            "species": {
                "displayName": "XBXT",
                "genomeAssembly": {"primaryExternalId": "XT10.0"},
            },
        },
        "geneGenomicLocationAssociations": [
            {
                "start": 153630573,
                "end": 153641544,
                "strand": "+",
                "geneGenomicLocationAssociationObject": {"name": "Chr3"},
            }
        ],
        "crossReferences": [
            {
                "referencedCurie": "Xenbase:XB-GENEPAGE-484285",
                "resourceDescriptorPage": {
                    "name": "gene",
                    "urlTemplate": "https://www.xenbase.org/entry/[%s]",
                },
            },
            {"referencedCurie": "ENSEMBL:ENSXETG00000025055"},
            {"referencedCurie": "NCBI_Gene:431679"},
        ],
    },
}


def _get(payload, status=200):
    response = MagicMock(status_code=status)
    response.json.return_value = payload
    tool = XenbaseTool(
        {"name": "Xenbase_get_gene", "fields": {"endpoint_type": "get_gene"}}
    )
    with patch("tooluniverse.xenbase_tool.requests.get", return_value=response) as get:
        result = tool.run({"gene_id": "XB-GENE-484286"})
    return result, get


def test_nested_record_fills_the_identity_fields():
    result, get = _get(PAYLOAD)
    data = result["data"]
    assert result["status"] == "success"
    assert (data["gene_id"], data["symbol"], data["name"]) == (
        "Xenbase:XB-GENE-484286",
        "tp53",
        "tumor protein p53",
    )
    assert data["synonyms"] == ["p53", "Trp248"]
    assert data["so_term"] == "gene"
    assert get.call_args.args[0].endswith("/gene/Xenbase:XB-GENE-484286")


def test_species_location_and_links_are_derived_from_the_nested_fields():
    data = _get(PAYLOAD)[0]["data"]
    assert data["species"] == {
        "name": "Xenopus tropicalis",
        "short_name": "XBXT",
        "taxon_id": "NCBITaxon:8364",
        "data_provider": "XB",
    }
    assert data["genomic_location"] == {
        "chromosome": "Chr3",
        "start": 153630573,
        "end": 153641544,
        "strand": "+",
        "assembly": "XT10.0",
    }
    assert data["xenbase_url"] == "https://www.xenbase.org/entry/XB-GENEPAGE-484285"
    assert data["cross_references"] == {
        "ENSEMBL": ["ENSXETG00000025055"],
        "NCBI_Gene": ["431679"],
    }


def test_unknown_gene_is_reported_as_not_found_for_400_and_404():
    for status in (400, 404):
        result, _ = _get({"errors": ["No gene found with ID: x"]}, status=status)
        assert result["status"] == "error"
        assert result["error"].startswith("Gene not found")
