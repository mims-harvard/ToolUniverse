from unittest.mock import MagicMock, patch

from tooluniverse.bioportal_tool import BioPortalTool


def _tool(endpoint):
    return BioPortalTool(
        {
            "name": f"BioPortal_{endpoint}",
            "type": "BioPortalTool",
            "fields": {"endpoint": endpoint},
        }
    )


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def test_search_forwards_page_and_exposes_continuation():
    payload = {
        "collection": [{"prefLabel": "Recurrent Melanoma", "@id": "x"}],
        "totalCount": 1060,
        "page": 2,
        "pageCount": 354,
    }
    with patch(
        "tooluniverse.bioportal_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("search").run(
            {"query": "melanoma", "ontologies": "NCIT", "page_size": 3, "page": 2}
        )

    assert get.call_args.kwargs["params"]["page"] == 2
    assert result["metadata"]["source"] == "BioPortal (NCBO)"
    assert result["metadata"]["total_count"] == 1060
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["page_size"] == 3
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["page_count"] == 354
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["query"] == "melanoma"


def test_hierarchy_forwards_page_and_exposes_continuation():
    payload = {
        "collection": [{"prefLabel": "sensory system disease", "@id": "y"}],
        "totalCount": 197,
        "page": 2,
        "pageCount": 66,
    }
    with patch(
        "tooluniverse.bioportal_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("get_hierarchy").run(
            {
                "ontology": "DOID",
                "concept_id": "http://purl.obolibrary.org/obo/DOID_4",
                "page_size": 3,
                "page": 2,
            }
        )

    assert get.call_args.kwargs["params"]["page"] == 2
    assert result["metadata"]["total_count"] == 197
    assert result["metadata"]["page"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3


def test_search_preserves_all_synonyms():
    synonyms = [f"synonym-{index}" for index in range(18)]
    payload = {
        "collection": [
            {"prefLabel": "Malignant Neoplasms", "@id": "x", "synonym": synonyms}
        ],
        "totalCount": 1,
        "page": 1,
        "pageCount": 1,
    }
    with patch(
        "tooluniverse.bioportal_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("search").run({"query": "cancer"})

    assert result["data"][0]["synonyms"] == synonyms
    assert result["data"][0]["synonym_count"] == 18


def test_hierarchy_preserves_all_synonyms():
    synonyms = [f"synonym-{index}" for index in range(8)]
    payload = [{"prefLabel": "child", "@id": "y", "synonym": synonyms}]
    with patch(
        "tooluniverse.bioportal_tool.requests.get", return_value=_response(payload)
    ):
        result = _tool("get_hierarchy").run({"ontology": "TEST", "concept_id": "id"})

    assert result["data"][0]["synonyms"] == synonyms
    assert result["data"][0]["synonym_count"] == 8


def test_search_and_hierarchy_reject_coerced_or_clamped_controls():
    invalid_search = (
        {"page_size": "2"},
        {"page_size": 0},
        {"page_size": 51},
        {"page": "2"},
        {"page": 0},
        {"exact_match": "false"},
    )
    invalid_hierarchy = (
        {"page_size": "2"},
        {"page_size": 101},
        {"page": False},
        {"direction": "descendants"},
    )
    with patch("tooluniverse.bioportal_tool.requests.get") as get:
        for invalid in invalid_search:
            result = _tool("search").run({"query": "melanoma", **invalid})
            assert result["status"] == "error", invalid
        for invalid in invalid_hierarchy:
            result = _tool("get_hierarchy").run(
                {"ontology": "DOID", "concept_id": "id", **invalid}
            )
            assert result["status"] == "error", invalid
    get.assert_not_called()
