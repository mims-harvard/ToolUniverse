"""GO_get_genes_for_term returned N empty objects and ignored its taxon filter.

Two defects compounded. The tool read the Biolink endpoint with
``extract_path: "associations[*].subject"``, but that API now answers with a
flat list of annotation records keyed ``bioentity_label`` / ``taxon`` and no
``subject`` key at all -- so ``assoc.get("subject", {})`` produced ``{}`` for
every row and ``rows=10`` returned ten empty dicts as a successful result. The
declared ``return_schema`` was ``array of objects with no properties``, so
nothing caught it.

Second, ``taxon`` was a *required* parameter that the endpoint silently ignored:
requesting NCBITaxon:10090 returned Homo sapiens and Caenorhabditis elegans
rows, and a nonsense taxon returned the same 50 records. The tool now queries
the GO Solr index, which honours the filter (human 1257, mouse 2034, bogus 0)
and returns real gene fields.
"""

import json
from pathlib import Path

from tooluniverse.gene_ontology_tool import (
    GeneOntologyTool,
    _drop_unfilled_query_segments,
)

_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src/tooluniverse/data/gene_ontology_tools.json"
)


def _config():
    configs = json.loads(_CONFIG.read_text())
    return next(c for c in configs if c["name"] == "GO_get_genes_for_term")


def _tool():
    return GeneOntologyTool(_config())


_SOLR_DOCS = {
    "response": {
        "numFound": 1257,
        "docs": [
            {
                "bioentity": "UniProtKB:P01375",
                "bioentity_label": "TNF",
                "bioentity_name": "Tumor necrosis factor",
                "taxon": "NCBITaxon:9606",
                "taxon_label": "Homo sapiens",
                "evidence_type": "IDA",
            },
            {
                "bioentity": "UniProtKB:P01375",
                "bioentity_label": "TNF",
                "bioentity_name": "Tumor necrosis factor",
                "taxon": "NCBITaxon:9606",
                "taxon_label": "Homo sapiens",
                "evidence_type": "IEA",
            },
            {
                "bioentity": "UniProtKB:P04637",
                "bioentity_label": "TP53",
                "bioentity_name": "Cellular tumor antigen p53",
                "taxon": "NCBITaxon:9606",
                "taxon_label": "Homo sapiens",
                "evidence_type": "TAS",
            },
        ],
    }
}


def test_genes_carry_real_fields_not_empty_objects():
    genes = _tool()._extract_data(_SOLR_DOCS, "response.docs.genes")

    assert len(genes) == 2
    assert all(g["bioentity"] for g in genes)
    assert {g["gene_symbol"] for g in genes} == {"TNF", "TP53"}
    assert all(g != {} for g in genes)


def test_annotation_rows_are_collapsed_to_distinct_genes():
    genes = _tool()._extract_data(_SOLR_DOCS, "response.docs.genes")
    tnf = next(g for g in genes if g["gene_symbol"] == "TNF")

    # Three rows, two genes; TNF's two evidence codes fold into one entry.
    assert tnf["annotation_count"] == 2
    assert sorted(tnf["evidence_types"]) == ["IDA", "IEA"]


def test_taxon_is_carried_through():
    genes = _tool()._extract_data(_SOLR_DOCS, "response.docs.genes")

    assert {g["taxon_label"] for g in genes} == {"Homo sapiens"}


def test_rows_without_a_bioentity_are_skipped():
    payload = {"response": {"docs": [{"bioentity_label": "orphan"}]}}

    assert _tool()._extract_data(payload, "response.docs.genes") == []


def test_taxon_is_no_longer_required():
    # It was required while being silently ignored by the old endpoint.
    assert _config()["parameter"]["required"] == ["id"]


def test_endpoint_filters_on_taxon_and_term_closure():
    endpoint = _config()["fields"]["endpoint"]

    assert "golr" in endpoint
    assert 'isa_partof_closure:"{id}"' in endpoint
    assert 'taxon:"{taxon}"' in endpoint


def test_return_schema_declares_the_gene_fields():
    schema = _config()["return_schema"]

    assert "oneOf" in schema
    props = schema["oneOf"][0]["items"]["properties"]
    assert "gene_symbol" in props
    assert "bioentity" in props


def test_omitted_optional_filter_is_dropped_from_the_url():
    url = _drop_unfilled_query_segments(
        'https://x/solr/select?q=*:*&fq=isa_partof_closure:"GO:0006915"'
        '&fq=taxon:"{taxon}"&rows=100'
    )

    assert "{taxon}" not in url
    assert 'isa_partof_closure:"GO:0006915"' in url
    assert "rows=100" in url


def test_url_without_placeholders_is_untouched():
    url = "https://x/solr/select?q=*:*&rows=10"

    assert _drop_unfilled_query_segments(url) == url
