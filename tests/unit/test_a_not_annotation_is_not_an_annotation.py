"""GO's NOT annotations, and the three keys this wrapper read that GO never sends.

`GOAPI_get_genes_by_function` answers "which genes have this function". The GO
API's association records carry `negated: true` with `qualifier: ["not"]` on an
annotation that says the opposite: the gene was examined and curated as *not*
having the term. Those rows went through the same branch as every other, so the
gene came back in the list of genes with the function.

Measured live on 2026-11-07, GO:0006915 (apoptotic process), first 400
associations: one is negated -- MGI:1341836 Trpv2, qualifier ["not"], evidence
ECO:0000314 (direct assay). It was returned as a gene with the apoptotic
process.

The same handlers read `evidence_type`, `evidence_label` and `reference`. The
API sends `evidence`, `evidence_types` and `publications`; it has no key of
any of those three names, so every annotation ever served by either tool
carried `evidence_type: null, evidence_label: null, references: []`. The
evidence code is what separates a curated experiment from an electronic guess,
and it was the one thing a GO annotation must not lose.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.go_api_tool import GOAPITool, _evidence, _is_negated, _references

pytestmark = pytest.mark.unit

# One positive and one negated association over two genes, shaped as
# api.geneontology.org answers them.
_POSITIVE = {
    "subject": {
        "id": "MGI:1915147",
        "label": "Aen",
        "taxon": {"id": "NCBITaxon:10090", "label": "Mus musculus"},
    },
    "object": {"id": "GO:0006915", "label": "apoptotic process", "category": [None]},
    "negated": False,
    "qualifier": None,
    "evidence": "ECO:0000314",
    "evidence_types": [
        {"id": "ECO:0000314", "label": "direct assay evidence used in manual assertion"}
    ],
    "provided_by": ["MGI"],
    "publications": [{"id": "PMID:17272269"}],
}
_NEGATED = {
    "subject": {
        "id": "MGI:1341836",
        "label": "Trpv2",
        "taxon": {"id": "NCBITaxon:10090", "label": "Mus musculus"},
    },
    "object": {"id": "GO:0006915", "label": "apoptotic process", "category": [None]},
    "negated": True,
    "qualifier": ["not"],
    "evidence": "ECO:0000314",
    "evidence_types": [
        {"id": "ECO:0000314", "label": "direct assay evidence used in manual assertion"}
    ],
    "provided_by": ["MGI"],
    "publications": [{"id": "PMID:20660725"}],
}


def test_a_negated_association_is_recognised_by_either_field():
    assert _is_negated(_NEGATED) is True
    assert _is_negated(_POSITIVE) is False
    # Either field alone is enough: GO has sent each without the other.
    assert _is_negated({"qualifier": ["NOT"]}) is True
    assert _is_negated({"negated": True}) is True
    assert _is_negated({}) is False


def test_the_evidence_code_comes_from_the_keys_the_api_sends():
    read = _evidence(_POSITIVE)
    assert read["evidence_type"] == "ECO:0000314"
    assert read["evidence_label"] == (
        "direct assay evidence used in manual assertion"
    )
    assert read["evidence_codes"] == ["ECO:0000314"]
    # The keys the wrapper used to read are absent from the payload, so
    # reading them returned None for every annotation.
    assert "evidence_type" not in _POSITIVE
    assert "evidence_label" not in _POSITIVE
    assert "reference" not in _POSITIVE
    assert _references(_POSITIVE) == ["PMID:17272269"]


def _tool(endpoint):
    return GOAPITool(
        {
            "name": "GOAPI_test",
            "type": "GOAPITool",
            "fields": {"endpoint": endpoint},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.text = json.dumps(body)
    resp.json.return_value = body
    resp.raise_for_status.return_value = None
    return resp


def test_a_gene_curated_against_the_function_is_not_listed_as_having_it():
    payload = {"associations": [_POSITIVE, _NEGATED]}
    with patch(
        "tooluniverse.go_api_tool.requests.get", return_value=_response(payload)
    ):
        out = _tool("search_annotations").run(
            {"go_id": "GO:0006915", "rows": 10, "max_associations_scanned": 100}
        )

    genes = {gene["gene_id"] for gene in out["data"]}
    assert "MGI:1915147" in genes
    assert "MGI:1341836" not in genes, "a NOT annotation put the gene in the list"
    meta = out["metadata"]
    assert meta["negated_associations_scanned"] == 1
    assert meta["genes_excluded_as_negated_only"] == 1
    assert "NOT annotations" in meta["negated_note"]


def test_a_listed_gene_keeps_the_not_annotation_it_also_has():
    """Excluding the row is not the same as hiding it: a gene with both a
    positive and a NOT annotation for the same term is a real curation
    conflict, and the caller should see it rather than a silent omission."""
    both = dict(_NEGATED, subject=_POSITIVE["subject"])
    payload = {"associations": [_POSITIVE, both]}
    with patch(
        "tooluniverse.go_api_tool.requests.get", return_value=_response(payload)
    ):
        out = _tool("search_annotations").run(
            {"go_id": "GO:0006915", "rows": 10, "max_associations_scanned": 100}
        )

    gene = out["data"][0]
    assert gene["gene_id"] == "MGI:1915147"
    assert gene["associations_returned"] == 1
    assert [row["negated"] for row in gene["negated_associations"]] == [True]
    assert out["metadata"]["genes_excluded_as_negated_only"] == 0


def test_a_gene_annotation_row_carries_its_evidence_and_its_references():
    payload = {"associations": [_POSITIVE]}
    with patch(
        "tooluniverse.go_api_tool.requests.get", return_value=_response(payload)
    ):
        out = _tool("gene_functions").run({"gene_id": "MGI:1915147", "rows": 5})

    row = out["data"][0]
    assert row["evidence_type"] == "ECO:0000314"
    assert row["evidence_label"].startswith("direct assay evidence")
    assert row["references"] == ["PMID:17272269"]
    assert row["negated"] is False
    # GO sends `category: [null]`; a null is not a domain.
    assert row["category"] is None
    assert row["categories"] == []
