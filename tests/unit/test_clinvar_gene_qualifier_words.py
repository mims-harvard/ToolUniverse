"""Regression guard for Fix-R10D-1: ClinVar's [gene] index only matches a
bare HGNC symbol, but a natural clinical phrasing like "NF2 gene" (used
verbatim in real research questions) silently returned 0 results, since
the literal trailing word "gene" became part of the queried string
(confirmed live and via raw NCBI E-utils curl: "Nf2 gene[gene]" -> 0
hits, "NF2[gene]" -> 2612 hits). A trailing/leading "gene"/"protein"
qualifier word is now stripped before querying.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinvar_tool import ClinVarSearchVariants

pytestmark = pytest.mark.unit


def _tool():
    return ClinVarSearchVariants({"name": "ClinVar_search_variants"})


def _term_for(gene_value):
    tool = _tool()
    with patch.object(
        ClinVarSearchVariants,
        "_make_request",
        return_value={"status": "success", "data": {}},
    ) as mock_request:
        tool.run({"gene": gene_value})
    return mock_request.call_args[0][1]["term"]


def test_trailing_gene_qualifier_is_stripped():
    assert _term_for("Nf2 gene") == "Nf2[gene]"


def test_leading_gene_qualifier_is_stripped():
    assert _term_for("gene NF2") == "NF2[gene]"


def test_trailing_protein_qualifier_is_stripped():
    assert _term_for("NF2 protein") == "NF2[gene]"


def test_plain_symbol_unaffected():
    assert _term_for("NF2") == "NF2[gene]"
