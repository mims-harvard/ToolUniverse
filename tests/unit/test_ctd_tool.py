"""Unit tests for the CTD tool (RENCI Automat backend).

The tool was migrated from CTD's native batchQuery.go (CAPTCHA-blocked in
2026) to the NIH/NCATS-Translator-funded mirror at automat.renci.org/ctd/.
These tests cover the new behaviour: cypher-resolution of free-text inputs
to a graph CURIE, the typed-edge fetch, the gene→disease unsupported-path
guard, and the envelope shape.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctd_tool import RENCI_HEADERS, CTDTool


def make_ctd_tool(input_type="chem", report_type="genes_curated"):
    """Create a CTD tool with a small deterministic config."""

    return CTDTool(
        {
            "name": "CTD_get_chemical_gene_interactions",
            "type": "CTDTool",
            "fields": {
                "input_type": input_type,
                "report_type": report_type,
            },
        }
    )


def make_cypher_response(curie):
    """Mock the /cypher endpoint response for term resolution."""

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [{"data": [{"row": [curie]}]}],
        "errors": [],
    }
    return response


def make_edge_response(edges):
    """Mock the /<source>/<target>/<curie> response."""

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = edges
    return response


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.post")
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_chemical_gene_returns_normalised_edges(mock_get, mock_post):
    """SmallMolecule->Gene edges should flatten into the legacy CTD-style envelope."""

    mock_post.return_value = make_cypher_response("CHEBI:15365")
    mock_get.return_value = make_edge_response(
        [
            [
                {"id": "CHEBI:15365", "name": "aspirin"},
                {
                    "predicate": "biolink:affects",
                    "qualified_predicate": "biolink:causes",
                    "object_direction_qualifier": "decreased",
                    "knowledge_level": "knowledge_assertion",
                    "agent_type": "manual_agent",
                    "primary_knowledge_source": "infores:ctd",
                },
                {"id": "NCBIGene:7076", "name": "TIMP1"},
            ]
        ]
    )

    tool = make_ctd_tool()
    result = tool.run({"input_terms": "aspirin"})

    assert result["status"] == "success"
    assert result["data"][0]["source_id"] == "CHEBI:15365"
    assert result["data"][0]["target_id"] == "NCBIGene:7076"
    assert result["data"][0]["primary_knowledge_source"] == "infores:ctd"
    assert result["metadata"]["backend"] == "RENCI Automat CTD"
    assert result["metadata"]["canonical_curie"] == "CHEBI:15365"
    assert result["metadata"]["total_results"] == 1


@pytest.mark.unit
def test_ctd_gene_disease_returns_redirect_error():
    """Gene->disease isn't in the RENCI snapshot; must redirect callers."""

    tool = make_ctd_tool(input_type="gene", report_type="diseases_curated")
    result = tool.run({"input_terms": "BRCA1"})

    assert result["status"] == "error"
    assert "RENCI CTD mirror" in result["error"]
    assert "chemical-centric" in result["error"]
    assert "OpenTargets_get_associated_diseases" in result["suggestion"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.post")
def test_ctd_unresolvable_input_returns_error(mock_post):
    """If cypher can't find the term, return a clear not-found error."""

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": [{"data": []}], "errors": []}
    mock_post.return_value = response

    tool = make_ctd_tool()
    result = tool.run({"input_terms": "definitely-not-a-compound"})

    assert result["status"] == "error"
    assert "definitely-not-a-compound" in result["error"]
    assert "not found" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.post")
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_request_asks_for_json(mock_get, mock_post):
    """Edge-fetch requests should include the canonical Accept/UA headers."""

    mock_post.return_value = make_cypher_response("CHEBI:15365")
    mock_get.return_value = make_edge_response([])

    make_ctd_tool().run({"input_terms": "aspirin"})

    assert mock_get.call_args.kwargs["headers"] == RENCI_HEADERS


@pytest.mark.unit
def test_ctd_missing_input_terms_returns_error():
    """Empty input_terms should fail fast, before any HTTP call."""

    tool = make_ctd_tool()
    result = tool.run({})

    assert result["status"] == "error"
    assert "input_terms" in result["error"]
