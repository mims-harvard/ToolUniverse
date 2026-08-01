from __future__ import annotations

from copy import deepcopy

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import vsd_dynamic_rest

pytestmark = pytest.mark.unit


def _search_config() -> dict:
    return {
        "name": "ReviewedTrialSearch",
        "type": "VSDDynamicRESTTool",
        "description": "Search a reviewed public clinical-trial endpoint.",
        "category": "special_tools",
        "cacheable": False,
        "parameter": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "minLength": 2, "maxLength": 100},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["condition"],
            "additionalProperties": False,
        },
        "vsd_operation": {
            "version": 1,
            "method": "GET",
            "endpoint": "https://clinicaltrials.gov/api/v2/studies",
            "path_arguments": {},
            "query_arguments": {
                "condition": "query.cond",
                "page_size": "pageSize",
            },
            "fixed_query": {"format": "json", "countTotal": "true"},
            "timeout_seconds": 20,
            "auth": {"type": "none"},
            "response_schema": {
                "type": "object",
                "properties": {"studies": {"type": "array"}},
                "required": ["studies"],
            },
        },
    }


def test_rejects_mutating_or_authenticated_operations():
    """Mutating methods and embedded credentials never reach the network."""
    config = _search_config()
    config["vsd_operation"]["method"] = "POST"
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="read-only"):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)

    config = _search_config()
    config["vsd_operation"]["auth"] = {
        "type": "api_key",
        "value": "must-not-be-embedded",
    }
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="credentials"):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)


def test_rejects_external_schema_references():
    """Provider-controlled schemas cannot trigger a second network fetch."""
    config = _search_config()
    config["vsd_operation"]["response_schema"] = {
        "$ref": "https://example.com/provider-schema.json"
    }
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="external"):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda c: c["parameter"].update(additionalProperties=True), "additional"),
        (
            lambda c: c["vsd_operation"]["query_arguments"].update(
                missing="query.term"
            ),
            "not declared",
        ),
        (
            lambda c: c["vsd_operation"]["fixed_query"].update(api_key="secret"),
            "Credential-like",
        ),
        (
            lambda c: c["vsd_operation"].update(
                endpoint="https://clinicaltrials.gov/api/v2/studies?x=1"
            ),
            "query",
        ),
    ],
)
def test_rejects_ambiguous_or_unsafe_contracts(mutation, message):
    """Malformed mappings, endpoints, and fixed parameters fail closed."""
    config = _search_config()
    mutation(config)
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match=message):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)


def test_validates_arguments_and_provider_schema(monkeypatch):
    """Both request arguments and provider data follow reviewed schemas."""
    tool = vsd_dynamic_rest.VSDDynamicRESTTool(_search_config())
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="reviewed schema"):
        tool.run({"condition": "ALS", "page_size": 100})

    monkeypatch.setattr(
        vsd_dynamic_rest,
        "_safe_get_json",
        lambda *args, **kwargs: (
            {"unexpected": []},
            {
                "status_code": 200,
                "content_type": "application/json",
                "response_bytes": 17,
                "redirects": 0,
            },
        ),
    )
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="Provider response"):
        tool.run({"condition": "ALS", "page_size": 5})


def test_path_values_are_encoded_and_every_argument_reaches_request(monkeypatch):
    """Path data cannot escape its placeholder and query mappings are exact."""
    config = _search_config()
    config["name"] = "ReviewedTrialDetails"
    config["parameter"] = {
        "type": "object",
        "properties": {"nct_id": {"type": "string"}},
        "required": ["nct_id"],
        "additionalProperties": False,
    }
    config["vsd_operation"].update(
        endpoint="https://clinicaltrials.gov/api/v2/studies/{nctId}",
        path_arguments={"nct_id": "nctId"},
        query_arguments={},
        fixed_query={"format": "json"},
        response_schema={"type": "object"},
    )
    request = {}

    def fake_get(url, params, *, timeout):
        request.update(url=url, params=params, timeout=timeout)
        return {}, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 2,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    result = vsd_dynamic_rest.VSDDynamicRESTTool(config).run({"nct_id": "NCT/123"})

    assert request["url"].endswith("/NCT%2F123")
    assert request["params"] == {"format": "json"}
    assert result["data"]["provenance"]["method"] == "GET"
    assert len(result["data"]["provenance"]["operation_sha256"]) == 64


def test_register_and_execute_through_real_tooluniverse(monkeypatch):
    """One reviewed runtime tool executes through ToolUniverse end to end."""
    requests = []

    def fake_get(url, params, *, timeout):
        requests.append((url, params, timeout))
        return {"studies": [{"protocolSection": {}}], "totalCount": 1}, {
            "status_code": 200,
            "content_type": "application/json; charset=utf-8",
            "response_bytes": 59,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    tooluniverse = ToolUniverse()
    try:
        name = vsd_dynamic_rest.register_reviewed_rest_tool(
            tooluniverse, deepcopy(_search_config())
        )
        result = tooluniverse.run_one_function(
            {
                "name": name,
                "arguments": {
                    "condition": "amyotrophic lateral sclerosis",
                    "page_size": 5,
                },
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()

    assert result["status"] == "success"
    assert result["data"]["result"]["totalCount"] == 1
    assert requests[0][1]["query.cond"] == "amyotrophic lateral sclerosis"


def test_digest_changes_when_reviewed_contract_changes():
    """Any reviewed-contract change invalidates its stable digest."""
    first = _search_config()
    second = deepcopy(first)
    second["vsd_operation"]["fixed_query"]["countTotal"] = "false"
    assert vsd_dynamic_rest.operation_digest(
        first
    ) != vsd_dynamic_rest.operation_digest(second)
