"""proteins_api_search accession routing fix (Fix-T3A-008).

A UniProt accession passed as `query` (e.g. 'P05067', the tool's own
documented example) used to always be misrouted to the `gene=` parameter by
the Feature-81B-007 short-string heuristic, silently returning zero results
even though the tool's description explicitly promises accession support.
The tool now recognizes the canonical UniProt accession format first.
"""

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.proteins_api_tool import ProteinsAPIRESTTool

    return ProteinsAPIRESTTool(
        {"name": "proteins_api_search", "type": "ProteinsAPIRESTTool", "fields": {}}
    )


@pytest.mark.parametrize(
    "accession", ["P05067", "P62593", "Q9Y6K9", "A0A075B6H7", "p05067"]
)
def test_uniprot_accession_routes_to_accession_param(accession):
    tool = _make_tool()
    params = tool._build_params({"query": accession})
    assert params.get("accession") == accession.strip().upper()
    assert "gene" not in params
    assert "protein" not in params
    # Accession lookups must not force the human taxid default.
    assert "taxid" not in params


@pytest.mark.parametrize("gene_name", ["BRCA1", "CYP2D6", "TP53"])
def test_short_gene_name_still_routes_to_gene_param(gene_name):
    """Regression guard for Feature-81B-007: non-accession short strings
    (gene symbols) must keep routing to gene=, not accession=."""
    tool = _make_tool()
    params = tool._build_params({"query": gene_name})
    assert params.get("gene") == gene_name
    assert "accession" not in params


def test_long_query_still_routes_to_protein_param():
    tool = _make_tool()
    params = tool._build_params({"query": "amyloid precursor protein"})
    assert params.get("protein") == "amyloid precursor protein"
    assert "accession" not in params
    assert "gene" not in params
