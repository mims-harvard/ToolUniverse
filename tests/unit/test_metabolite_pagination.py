from unittest.mock import MagicMock, patch

from tooluniverse.metabolite_tool import MetaboliteTool


def _response(payload, status_code=200):
    response = MagicMock(status_code=status_code)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_formula_search_reports_total_and_supports_offset():
    properties = [
        {
            "CID": index,
            "Title": f"compound-{index}",
            "MolecularFormula": "C6H12O6",
            "MolecularWeight": "180.16",
            "ConnectivitySMILES": f"smiles-{index}",
        }
        for index in range(7)
    ]
    tool = MetaboliteTool({})
    with patch(
        "tooluniverse.metabolite_tool.requests.get",
        return_value=_response({"PropertyTable": {"Properties": properties}}),
    ):
        result = tool._search(
            {"query": "C6H12O6", "search_type": "formula", "limit": 3, "offset": 3}
        )

    assert [row["pubchem_cid"] for row in result["data"]["results"]] == [3, 4, 5]
    assert result["data"]["count"] == 3
    assert result["data"]["total_count"] == 7
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["result_set_complete"] is True


def test_disease_associations_support_tail_page():
    rows = [
        {
            "DiseaseName": f"disease-{index}",
            "DiseaseID": f"MONDO:{index:07d}",
            "DirectEvidence": None,
            "PubMedIDs": [str(index)],
        }
        for index in range(5)
    ]
    tool = MetaboliteTool({})
    with patch.object(tool, "_resolve_to_cid", return_value=5793), patch.object(
        tool, "_get_properties", return_value={"Title": "Glucose"}
    ), patch.object(tool, "_get_synonyms", return_value=[]), patch.object(
        tool, "_resolve_ctd_term", return_value=("Glucose", rows)
    ):
        result = tool._get_diseases(
            {"compound_name": "glucose", "limit": 3, "offset": 3}
        )

    assert len(result["data"]["diseases"]) == 2
    assert result["data"]["disease_count"] == 5
    assert result["data"]["returned"] == 2
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None


def test_ctd_backend_fetches_all_server_pages():
    def hit(index):
        return {
            "_id": f"MONDO:{index:07d}",
            "mondo": {"label": f"disease-{index}"},
            "ctd": {
                "chemical_related_to_disease": {
                    "chemical_name": "Aspirin",
                    "pubmed": str(index),
                }
            },
        }

    responses = [
        _response({"total": 201, "hits": [hit(i) for i in range(200)]}),
        _response({"total": 201, "hits": [hit(200)]}),
    ]
    tool = MetaboliteTool({})
    with patch(
        "tooluniverse.metabolite_tool.requests.get", side_effect=responses
    ) as request:
        rows = tool._ctd_diseases("Aspirin")

    assert len(rows) == 201
    assert request.call_count == 2
    assert request.call_args_list[0].kwargs["params"]["from"] == 0
    assert request.call_args_list[1].kwargs["params"]["from"] == 200


def test_invalid_metabolite_pagination_is_explicit():
    tool = MetaboliteTool({})

    assert tool._search({"query": "x", "offset": -1}) == {
        "status": "error",
        "error": "offset must be a non-negative integer",
    }
    assert tool._get_diseases({"compound_name": "x", "limit": 0}) == {
        "status": "error",
        "error": "limit must be a positive integer",
    }
