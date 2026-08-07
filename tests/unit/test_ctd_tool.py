"""Unit tests for the CTD tool (mydisease.info backend).

The tool was originally migrated from CTD's native batchQuery.go
(CAPTCHA-blocked) to the NIH/NCATS-Translator-funded RENCI Automat mirror,
and has since been migrated again because that mirror was fully
decommissioned (its registry no longer lists a 'ctd' backend at all). It now
queries the BioThings mydisease.info API, which independently caches CTD's
chemical-disease curation under `ctd.chemical_related_to_disease` on each
disease document. These tests cover the current behaviour: chemical-name/
MeSH-ID/CAS-RN resolution to the right nested field, the chemical->disease
and disease->chemical directions, the gene<->chemical "permanently
unavailable" guard, and the envelope shape.
"""

from unittest.mock import Mock, patch

import pytest

from tooluniverse.ctd_tool import CTDTool, HEADERS


def make_ctd_tool(input_type="chem", report_type="diseases_curated"):
    """Create a CTD tool with a small deterministic config."""

    return CTDTool(
        {
            "name": "CTD_get_chemical_diseases",
            "type": "CTDTool",
            "fields": {
                "input_type": input_type,
                "report_type": report_type,
            },
        }
    )


def make_query_response(hits):
    """Mock a mydisease.info /query response."""

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = {"hits": hits}
    return response


def make_disease_response(doc):
    """Mock a mydisease.info /disease/<id> response."""

    response = Mock()
    response.status_code = 200
    response.raise_for_status.return_value = None
    response.json.return_value = doc
    return response


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_chemical_diseases_returns_normalised_edges(mock_get):
    """SmallMolecule->Disease edges should flatten into the CTD-style envelope."""

    mock_get.return_value = make_query_response(
        [
            {
                "_id": "MONDO:0000495",
                "mondo": {"label": "some disease"},
                "ctd": {
                    "chemical_related_to_disease": [
                        {
                            "chemical_name": "bisphenol A",
                            "mesh_chemical_id": "C006780",
                            "cas_registry_number": "80-05-7",
                            "direct_evidence": "marker/mechanism",
                            "pubmed": "25307304",
                        }
                    ]
                },
            }
        ]
    )

    tool = make_ctd_tool()
    result = tool.run({"input_terms": "bisphenol A"})

    assert result["status"] == "success"
    assert result["data"][0]["source_id"] == "MESH:C006780"
    assert result["data"][0]["source_name"] == "bisphenol A"
    assert result["data"][0]["target_id"] == "MONDO:0000495"
    assert result["data"][0]["target_name"] == "some disease"
    assert result["data"][0]["qualified_predicate"] == "biolink:contributes_to"
    assert result["data"][0]["primary_knowledge_source"] == "infores:ctd"
    assert result["metadata"]["backend"].startswith("mydisease.info")


@pytest.mark.unit
def test_ctd_gene_disease_returns_redirect_error():
    """Gene->disease has no live curated CTD source; must redirect callers."""

    tool = make_ctd_tool(input_type="gene", report_type="diseases_curated")
    result = tool.run({"input_terms": "BRCA1"})

    assert result["status"] == "error"
    assert "OpenTargets_get_associated_diseases" in result["suggestion"]


@pytest.mark.unit
def test_ctd_chemical_gene_returns_permanently_unavailable_error():
    """Gene<->chemical has no live free source since RENCI's decommissioning."""

    tool = make_ctd_tool(input_type="chem", report_type="genes_curated")
    result = tool.run({"input_terms": "bisphenol A"})

    assert result["status"] == "error"
    assert "decommissioned" in result["error"]
    assert "DGIdb_get_drug_gene_interactions" in result["suggestion"]


@pytest.mark.unit
def test_ctd_gene_chemicals_returns_permanently_unavailable_error():
    tool = make_ctd_tool(input_type="gene", report_type="chems_curated")
    result = tool.run({"input_terms": "TP53"})

    assert result["status"] == "error"
    assert "decommissioned" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_chemical_diseases_no_match_returns_error(mock_get):
    """If the chemical isn't found in the CTD-derived index, return a clear error."""

    mock_get.return_value = make_query_response([])

    tool = make_ctd_tool()
    result = tool.run({"input_terms": "definitely-not-a-compound"})

    assert result["status"] == "error"
    assert "definitely-not-a-compound" in result["error"]


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_disease_chemicals_resolves_by_mondo_curie(mock_get):
    """A bare MONDO CURIE should skip name resolution and fetch directly."""

    mock_get.side_effect = [
        make_disease_response({"mondo": {"label": "asthma"}}),
        make_disease_response(
            {
                "ctd": {
                    "chemical_related_to_disease": [
                        {
                            "chemical_name": "budesonide",
                            "mesh_chemical_id": "D001990",
                            "direct_evidence": "therapeutic",
                            "pubmed": "12345",
                        }
                    ]
                }
            }
        ),
    ]

    tool = make_ctd_tool(input_type="disease", report_type="chems_curated")
    result = tool.run({"input_terms": "MONDO:0004979"})

    assert result["status"] == "success"
    assert result["data"][0]["source_id"] == "MONDO:0004979"
    assert result["data"][0]["target_name"] == "budesonide"
    assert result["data"][0]["qualified_predicate"] == "biolink:treats"


@pytest.mark.unit
@patch("tooluniverse.ctd_tool.requests.get")
def test_ctd_request_asks_for_json(mock_get):
    """Requests to mydisease.info should include the canonical Accept/UA headers."""

    mock_get.return_value = make_query_response([])

    make_ctd_tool().run({"input_terms": "aspirin"})

    assert mock_get.call_args.kwargs["headers"] == HEADERS


@pytest.mark.unit
def test_ctd_missing_input_terms_returns_error():
    """Empty input_terms should fail fast, before any HTTP call."""

    tool = make_ctd_tool()
    result = tool.run({})

    assert result["status"] == "error"
    assert "input_terms" in result["error"]
