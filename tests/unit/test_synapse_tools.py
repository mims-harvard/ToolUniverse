"""Synapse_search_entities / Synapse_get_entity / Synapse_list_children (mocked)."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _response(payload=None, status=200, text=""):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = text
    return response


def _run(operation, arguments, responder):
    from tooluniverse.synapse_tool import SynapseTool

    tool = SynapseTool(
        {"name": f"Synapse_{operation}", "fields": {"operation": operation}}
    )
    calls = []

    def fake(session, method, url, **kwargs):
        calls.append((method, url.split("/repo/v1")[1], kwargs.get("json")))
        return responder(method, url)

    with patch("tooluniverse.synapse_tool.request_with_retry", fake):
        return tool.run(arguments), calls


def test_search_posts_words_and_node_type_and_formats_hits():
    payload = {
        "found": 835,
        "hits": [
            {
                "id": "syn76396144",
                "name": "Breast Cancer Organoid Research",
                "node_type": "project",
                "description": "x" * 500,
                "created_on": 1784705694,
                "modified_on": 1784705695,
                "created_by": "3593328",
            }
        ],
    }
    result, calls = _run(
        "search",
        {"query": "breast cancer", "node_type": "Project", "size": 500},
        lambda m, u: _response(payload, status=201),
    )
    method, path, body = calls[0]
    assert (method, path) == ("POST", "/search")
    assert body["queryTerm"] == ["breast", "cancer"]
    assert body["size"] == 100
    assert body["booleanQuery"] == [{"key": "node_type", "value": "project"}]
    row = result["data"][0]
    assert row["id"] == "syn76396144"
    assert row["created_on"].endswith("Z") and row["created_on"].startswith("2026")
    assert len(row["description"]) == 403 and row["description"].endswith("...")
    assert result["metadata"]["total_found"] == 835


def test_get_entity_flattens_annotations_and_short_type():
    def responder(method, url):
        if url.endswith("/annotations2"):
            return _response(
                {
                    "annotations": {
                        "assay": {"type": "STRING", "value": ["RNA-seq"]},
                        "tissue": {"type": "STRING", "value": ["brain", "blood"]},
                    }
                }
            )
        return _response(
            {
                "id": "syn1",
                "name": "f.vcf",
                "concreteType": "org.sagebionetworks.repo.model.FileEntity",
                "parentId": "syn0",
                "versionNumber": 1,
                "dataFileHandleId": "64701305",
            }
        )

    result, _ = _run("get_entity", {"entity_id": "syn1"}, responder)
    data = result["data"]
    assert data["type"] == "File"
    assert data["annotations"] == {"assay": "RNA-seq", "tissue": ["brain", "blood"]}
    assert data["url"] == "https://www.synapse.org/Synapse:syn1"


def test_restricted_entity_is_reported_as_not_public():
    result, _ = _run(
        "get_entity",
        {"entity_id": "syn2280093"},
        lambda m, u: _response({"reason": "You lack READ access"}, status=403),
    )
    assert result["status"] == "error"
    assert "not public" in result["error"]


def test_entity_id_is_validated():
    result, calls = _run(
        "get_entity", {"entity_id": "../etc"}, lambda m, u: _response({})
    )
    assert result["status"] == "error" and calls == []


def test_list_children_passes_paging_token_and_types():
    payload = {
        "page": [
            {
                "id": "syn22364365",
                "name": "a.vcf",
                "type": "org.sagebionetworks.repo.model.FileEntity",
                "versionNumber": 1,
            }
        ],
        "nextPageToken": "50a0",
    }
    result, calls = _run(
        "list_children",
        {
            "entity_id": "syn22364283",
            "include_types": ["file"],
            "next_page_token": "tok",
        },
        lambda m, u: _response(payload),
    )
    body = calls[0][2]
    assert body == {
        "parentId": "syn22364283",
        "includeTypes": ["file"],
        "nextPageToken": "tok",
    }
    assert result["data"][0]["type"] == "File"
    assert result["metadata"]["next_page_token"] == "50a0"
