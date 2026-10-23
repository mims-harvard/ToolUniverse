from unittest.mock import Mock, patch

import pytest

from tooluniverse.mesh_tool import MeSHTool


def _tool(endpoint):
    return MeSHTool({"name": "mesh", "fields": {"endpoint": endpoint}})


def _response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


@pytest.mark.parametrize(
    ("endpoint", "arguments"),
    [
        ("search_descriptors", {"query": ""}),
        ("search_descriptors", {"query": "cancer", "limit": True}),
        ("search_descriptors", {"query": "cancer", "limit": 51}),
        ("search_terms", {"query": "cancer", "match": "startswith"}),
        ("search_terms", {"query": "cancer", "offset": 50}),
        ("get_descriptor", {"descriptor_id": "D9369"}),
        ("get_descriptor", {"descriptor_id": "D009369", "format": "json"}),
    ],
)
def test_invalid_inputs_are_rejected_before_network(endpoint, arguments):
    with patch("tooluniverse.mesh_tool.requests.get") as get:
        result = _tool(endpoint).run(arguments)

    assert result["status"] == "error"
    get.assert_not_called()


def test_descriptor_search_reports_complete_results_only_below_limit():
    payload = [
        {
            "resource": "http://id.nlm.nih.gov/mesh/D009369",
            "label": "Neoplasms",
        }
    ]
    with patch(
        "tooluniverse.mesh_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("search_descriptors").run(
            {"query": "neoplasm", "match": "startsWith", "limit": 10}
        )

    assert result["status"] == "success"
    assert result["data"][0]["descriptor_id"] == "D009369"
    assert result["metadata"] == {
        "source": "NLM MeSH",
        "query": "neoplasm",
        "match_type": "startsWith",
        "returned": 1,
        "requested_limit": 10,
        "total_results": 1,
        "total_results_known": True,
        "possibly_truncated": False,
        "result_set_complete": True,
        "pagination_supported": False,
        "warning": None,
    }
    assert get.call_args.kwargs["params"]["match"] == "startsWith"
    assert "offset" not in get.call_args.kwargs["params"]


def test_term_search_exposes_unknown_total_when_limit_is_reached():
    payload = [
        {
            "resource": f"http://id.nlm.nih.gov/mesh/T{i:06d}",
            "label": f"Cancer term {i}",
        }
        for i in range(50)
    ]
    with patch("tooluniverse.mesh_tool.requests.get", return_value=_response(payload)):
        result = _tool("search_terms").run(
            {"query": "cancer", "match": "startsWith", "limit": 50}
        )

    metadata = result["metadata"]
    assert metadata["returned"] == 50
    assert metadata["total_results"] is None
    assert metadata["total_results_known"] is False
    assert metadata["possibly_truncated"] is True
    assert metadata["result_set_complete"] is False
    assert metadata["pagination_supported"] is False
    assert "no total or offset" in metadata["warning"]


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("search_descriptors", {"resource": "not-a-list"}),
        ("search_terms", [{"resource": "http://id.nlm.nih.gov/mesh/T000001"}]),
    ],
)
def test_search_rejects_malformed_source_records(endpoint, payload):
    with patch("tooluniverse.mesh_tool.requests.get", return_value=_response(payload)):
        result = _tool(endpoint).run({"query": "cancer"})

    assert result["status"] == "error"
    assert "malformed" in result["error"]


def test_search_rejects_result_that_violates_requested_match_mode():
    payload = [
        {
            "resource": "http://id.nlm.nih.gov/mesh/D009369",
            "label": "Neoplasms",
        }
    ]
    with patch("tooluniverse.mesh_tool.requests.get", return_value=_response(payload)):
        result = _tool("search_descriptors").run({"query": "cancer", "match": "exact"})

    assert result["status"] == "error"
    assert result["returned_label"] == "Neoplasms"


def test_descriptor_preserves_complete_record_and_verifies_identity():
    payload = {
        "@context": "http://id.nlm.nih.gov/mesh/context.json",
        "@id": "http://id.nlm.nih.gov/mesh/D009369",
        "@type": "http://id.nlm.nih.gov/mesh/vocab#TopicalDescriptor",
        "identifier": "D009369",
        "label": {"@language": "en", "@value": "Neoplasms"},
        "annotation": {"@value": "Cancer terminology note"},
        "historyNote": {"@value": "1963-2026"},
        "publicMeSHNote": {"@value": "Public note"},
        "treeNumber": ["http://id.nlm.nih.gov/mesh/C04"],
        "allowableQualifier": ["http://id.nlm.nih.gov/mesh/Q000188"],
        "concept": ["http://id.nlm.nih.gov/mesh/M0018326"],
        "preferredConcept": "http://id.nlm.nih.gov/mesh/M0018326",
        "preferredTerm": "http://id.nlm.nih.gov/mesh/T027926",
        "customFutureField": {"kept": True},
    }
    with patch("tooluniverse.mesh_tool.requests.get", return_value=_response(payload)):
        result = _tool("get_descriptor").run({"descriptor_id": " d009369 "})

    assert result["status"] == "success"
    assert result["data"]["descriptor_id"] == "D009369"
    assert result["data"]["tree_numbers"] == ["C04"]
    assert result["data"]["history_note"] == "1963-2026"
    assert result["data"]["allowable_qualifiers"] == payload["allowableQualifier"]
    assert result["data"]["record"] == payload
    assert result["data"]["record"]["customFutureField"] == {"kept": True}
    assert result["metadata"]["returned_identifier_verified"] is True
    assert result["metadata"]["source_record_complete"] is True


def test_descriptor_rejects_returned_identifier_mismatch():
    with patch(
        "tooluniverse.mesh_tool.requests.get",
        return_value=_response({"identifier": "D003920"}),
    ):
        result = _tool("get_descriptor").run({"descriptor_id": "D009369"})

    assert result["status"] == "error"
    assert result["requested_descriptor_id"] == "D009369"
    assert result["returned_descriptor_id"] == "D003920"


def test_descriptor_accepts_new_nine_digit_identifier_format():
    payload = {"identifier": "D000072656", "label": {"@value": "Cancer Survivors"}}
    with patch(
        "tooluniverse.mesh_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = _tool("get_descriptor").run({"descriptor_id": "d000072656"})

    assert result["status"] == "success"
    assert result["data"]["descriptor_id"] == "D000072656"
    assert get.call_args.args[0].endswith("/D000072656.json")
