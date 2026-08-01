from __future__ import annotations

import json
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


def test_rejects_mutating_or_embedded_credentials():
    """Mutating methods and embedded credential values never reach the network."""
    config = _search_config()
    config["vsd_operation"]["method"] = "POST"
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="read-only"):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)

    config = _search_config()
    config["vsd_operation"]["auth"] = {
        "type": "api_key",
        "value": "must-not-be-embedded",
    }
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="auth"):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)


@pytest.mark.parametrize(
    "auth, message",
    [
        (
            {
                "type": "api_key_header_env",
                "env_var": "AWS_SECRET_ACCESS_KEY",
                "header": "X-API-Key",
            },
            "TOOLUNIVERSE_VSD_",
        ),
        (
            {
                "type": "api_key_header_env",
                "env_var": "TOOLUNIVERSE_VSD_TEST_KEY",
                "header": "Authorization",
            },
            "prohibited",
        ),
        (
            {
                "type": "bearer_env",
                "env_var": "TOOLUNIVERSE_VSD_TEST_KEY",
                "value": "embedded-secret-value",
            },
            "unsupported fields",
        ),
        (
            {
                "type": "api_key_query_env",
                "env_var": "TOOLUNIVERSE_VSD_TEST_KEY",
            },
            "supports only",
        ),
    ],
)
def test_rejects_unsafe_credential_references(auth, message):
    config = _search_config()
    config["vsd_operation"]["auth"] = auth
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match=message):
        vsd_dynamic_rest.VSDDynamicRESTTool(config)


def test_api_key_header_is_read_at_runtime_and_never_returned(monkeypatch):
    config = _search_config()
    config["vsd_operation"]["auth"] = {
        "type": "api_key_header_env",
        "env_var": "TOOLUNIVERSE_VSD_TRIALS_API_KEY",
        "header": "X-API-Key",
    }
    secret = "runtime-api-key-value"
    monkeypatch.setenv("TOOLUNIVERSE_VSD_TRIALS_API_KEY", secret)
    captured = {}

    def fake_get(url, params, *, timeout, headers):
        captured.update(url=url, params=params, timeout=timeout, headers=headers)
        return {"studies": []}, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 15,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    result = vsd_dynamic_rest.VSDDynamicRESTTool(config).run({"condition": "ALS"})
    serialized = json.dumps(result, sort_keys=True)

    assert captured["headers"] == {"X-API-Key": secret}
    assert secret not in serialized
    assert "X-API-Key" not in serialized
    assert "TOOLUNIVERSE_VSD_TRIALS_API_KEY" not in serialized
    assert result["data"]["provenance"]["authentication"] == {
        "type": "api_key_header_env",
        "credential_source": "environment",
    }


def test_bearer_token_rotates_without_changing_reviewed_contract(monkeypatch):
    config = _search_config()
    config["vsd_operation"]["auth"] = {
        "type": "bearer_env",
        "env_var": "TOOLUNIVERSE_VSD_TRIALS_BEARER",
    }
    headers_seen = []

    def fake_get(url, params, *, timeout, headers):
        headers_seen.append(headers)
        return {"studies": []}, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 15,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    tool = vsd_dynamic_rest.VSDDynamicRESTTool(config)
    digest = tool._operation_digest
    monkeypatch.setenv("TOOLUNIVERSE_VSD_TRIALS_BEARER", "first-bearer-token")
    tool.run({"condition": "ALS"})
    monkeypatch.setenv("TOOLUNIVERSE_VSD_TRIALS_BEARER", "second-bearer-token")
    tool.run({"condition": "ALS"})

    assert headers_seen == [
        {"Authorization": "Bearer first-bearer-token"},
        {"Authorization": "Bearer second-bearer-token"},
    ]
    assert tool._operation_digest == digest


def test_missing_invalid_or_reflected_credentials_fail_closed(monkeypatch):
    config = _search_config()
    config["vsd_operation"]["auth"] = {
        "type": "bearer_env",
        "env_var": "TOOLUNIVERSE_VSD_TRIALS_BEARER",
    }
    calls = []

    def fake_get(url, params, *, timeout, headers):
        calls.append(headers)
        secret = headers["Authorization"].removeprefix("Bearer ")
        return {"studies": [], "echo": secret}, {
            "status_code": 200,
            "content_type": "application/json",
            "response_bytes": 50,
            "redirects": 0,
        }

    monkeypatch.setattr(vsd_dynamic_rest, "_safe_get_json", fake_get)
    tool = vsd_dynamic_rest.VSDDynamicRESTTool(config)
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="not set"):
        tool.run({"condition": "ALS"})
    assert calls == []

    monkeypatch.setenv("TOOLUNIVERSE_VSD_TRIALS_BEARER", "bad token spaces")
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="bearer token"):
        tool.run({"condition": "ALS"})
    assert calls == []

    monkeypatch.setenv("TOOLUNIVERSE_VSD_TRIALS_BEARER", "reflected-token-value")
    with pytest.raises(vsd_dynamic_rest.VSDDynamicRESTError, match="reflected"):
        tool.run({"condition": "ALS"})
    assert len(calls) == 1


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
