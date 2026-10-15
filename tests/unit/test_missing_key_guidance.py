"""A gated tool must name a route to its keys that actually works.

``required_api_keys`` holds two kinds of name. A provider credential can be
passed per request; a server URL or a local data path is deployment
configuration that ``ToolUniverse._get_api_key`` reads from the process
environment on purpose. Both used to produce the same "provide them as request
credentials" sentence, which is false for the second kind -- and an OAuth
client id was treated as the second kind, so the ICD-11 tools could not be
unlocked per request at all.
"""

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.credentials import is_credential_name
from tooluniverse.execute_function import describe_missing_keys

pytestmark = pytest.mark.unit


ICD_TOOLS = ("ICD11_search_diseases", "ICD11_get_entity", "ICD11_browse_hierarchy")


@pytest.fixture
def tu(monkeypatch):
    """A ToolUniverse with no ICD or MCP configuration in the environment."""
    for name in (
        "ICD_CLIENT_ID",
        "ICD_CLIENT_SECRET",
        "ESM_MCP_SERVER_HOST",
        "USPTO_MCP_SERVER_HOST",
    ):
        monkeypatch.delenv(name, raising=False)
    engine = ToolUniverse()
    engine.load_tools()
    return engine


def _error(result):
    assert isinstance(result, dict) and result.get("status") == "error", result
    return result["error"], (result.get("error_details") or {}).get("next_steps") or []


# --- an OAuth client id is a credential --------------------------------------


def test_an_oauth_client_id_is_a_credential_name():
    """It is half of a pair with a secret, not deployment configuration."""
    assert is_credential_name("ICD_CLIENT_ID")
    assert is_credential_name("ICD_CLIENT_SECRET")


@pytest.mark.parametrize("name", ICD_TOOLS)
def test_passing_both_icd_credentials_gets_past_the_gate(name, tu, monkeypatch):
    """The regression: both supplied as the error says, and still refused.

    ICD_CLIENT_ID resolved from the process environment while the secret
    resolved from the request, so the pair could never be completed.
    """
    captured = {}

    class _Resp:
        status_code = 200

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"access_token": "tok", "expires_in": 3600}

    def fake_post(url, data=None, timeout=None):
        captured["data"] = data
        return _Resp()

    class _Search(_Resp):
        @staticmethod
        def json():
            return {"destinationEntities": []}

    def fake_get(url, headers=None, params=None, timeout=None):
        captured["authorization"] = (headers or {}).get("Authorization")
        return _Search()

    monkeypatch.setattr("tooluniverse.icd_tool.requests.post", fake_post)
    monkeypatch.setattr("tooluniverse.icd_tool.requests.get", fake_get)

    tu.run_one_function(
        {"name": name, "arguments": {"query": "asthma", "entity_id": "1"}},
        credentials={
            "ICD_CLIENT_ID": "request-id",
            "ICD_CLIENT_SECRET": "request-secret",
        },
    )
    # Reaching the token request at all means the gate let the call through,
    # and both halves came from the request rather than the environment.
    assert captured["data"]["client_id"] == "request-id"
    assert captured["data"]["client_secret"] == "request-secret"
    assert captured["authorization"] == "Bearer tok"


def test_a_half_supplied_pair_still_names_the_missing_half(tu):
    result = tu.run_one_function(
        {"name": "ICD11_search_diseases", "arguments": {"query": "asthma"}},
        credentials={"ICD_CLIENT_SECRET": "only-the-secret"},
    )
    message, _ = _error(result)
    assert "ICD_CLIENT_ID" in message
    assert "ICD_CLIENT_SECRET" not in message


# --- the wording, per kind of name -------------------------------------------


def test_credentials_keep_the_request_route():
    how, steps = describe_missing_keys(["OPENAI_API_KEY"], "run_one_function")
    assert "request credentials" in how
    assert any("credentials={...}" in step for step in steps)


def test_deployment_configuration_is_not_offered_as_a_credential():
    how, steps = describe_missing_keys(["ESM_MCP_SERVER_HOST"], "run_one_function")
    assert "ESM_MCP_SERVER_HOST" in how
    assert "environment" in how
    assert "cannot be passed as a request credential" in how
    assert not any("credentials={...}" in step for step in steps)
    assert steps == [
        "Set ESM_MCP_SERVER_HOST in the environment of the process serving these tools"
    ]


def test_a_mixture_says_which_name_goes_where():
    how, steps = describe_missing_keys(
        ["SOME_API_KEY", "SOME_SERVER_URL"], "run_one_function"
    )
    assert "SOME_API_KEY" in how and "SOME_SERVER_URL" in how
    assert "cannot be passed per request" in how
    assert len(steps) == 2
    assert "SOME_API_KEY" in steps[0] and "credentials={...}" in steps[0]
    assert "SOME_SERVER_URL" in steps[1] and "credentials={...}" not in steps[1]


def test_the_async_entry_point_names_itself_in_its_own_steps():
    _, steps = describe_missing_keys(["OPENAI_API_KEY"], "run_one_function_async")
    assert any("run_one_function_async(credentials={...})" in step for step in steps)


def test_a_tool_gated_only_on_a_server_url_says_so(tu):
    """End to end, not just the helper."""
    message, steps = _error(tu.run_one_function({"name": "mcp_auto_loader_esm"}))
    assert "ESM_MCP_SERVER_HOST" in message
    assert "cannot be passed as a request credential" in message
    assert not any("credentials={...}" in step for step in steps)


# --- the ICD tool's own authentication message -------------------------------


def _icd_tool():
    from tooluniverse.icd_tool import ICDTool

    return ICDTool(
        {
            "name": "ICD11_search_diseases",
            "type": "ICDTool",
            "fields": {"endpoint": "/release/11/2024-01/mms/search?q={search_term}"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def test_icd_says_which_half_of_the_pair_is_missing(monkeypatch):
    monkeypatch.delenv("ICD_CLIENT_ID", raising=False)
    monkeypatch.setenv("ICD_CLIENT_SECRET", "secret")
    out = _icd_tool().run({"query": "asthma"})
    assert out["status"] == "error"
    assert "ICD_CLIENT_ID is not set" in out["error"]
    assert "ICD_CLIENT_SECRET is not set" not in out["error"]


def test_icd_does_not_tell_you_to_set_credentials_it_just_had_rejected(monkeypatch):
    """WHO answers a wrong id or secret with 400 invalid_client.

    The old message said "Set ICD_CLIENT_ID and ICD_CLIENT_SECRET environment
    variables", which is the one thing the caller had already done.
    """
    monkeypatch.setenv("ICD_CLIENT_ID", "wrong")
    monkeypatch.setenv("ICD_CLIENT_SECRET", "wrong")

    class _Rejected:
        status_code = 400

        @staticmethod
        def json():
            return {"error": "invalid_client"}

    monkeypatch.setattr(
        "tooluniverse.icd_tool.requests.post",
        lambda url, data=None, timeout=None: _Rejected(),
    )
    out = _icd_tool().run({"query": "asthma"})
    assert out["status"] == "error"
    assert "rejected" in out["error"] and "invalid_client" in out["error"]
    assert "is not set" not in out["error"]


def test_icd_reports_an_unreachable_auth_service_as_such(monkeypatch):
    monkeypatch.setenv("ICD_CLIENT_ID", "id")
    monkeypatch.setenv("ICD_CLIENT_SECRET", "secret")

    def boom(url, data=None, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr("tooluniverse.icd_tool.requests.post", boom)
    out = _icd_tool().run({"query": "asthma"})
    assert out["status"] == "error"
    assert "Could not reach the ICD authentication service" in out["error"]
    assert "connection refused" in out["error"]


# --- a service that keeps logins for its users says where to add one --------


def test_a_service_can_say_where_its_users_add_a_missing_login(monkeypatch):
    """A scientist chatting with an AI app on a hosted service cannot pass credentials={...}."""
    monkeypatch.setenv(
        "TOOLUNIVERSE_CREDENTIAL_HELP",
        "The user can add it at https://example.org/credentials?key={key}, then ask again.",
    )
    how, steps = describe_missing_keys(["OMIM_API_KEY"], "run_one_function")
    assert how == "The user can add it at https://example.org/credentials?key=OMIM_API_KEY, then ask again."
    assert steps == [how]
    assert "environment" not in how and "credentials={" not in how


def test_without_a_service_message_local_users_keep_the_python_guidance(monkeypatch):
    monkeypatch.delenv("TOOLUNIVERSE_CREDENTIAL_HELP", raising=False)
    how, steps = describe_missing_keys(["OMIM_API_KEY"], "run_one_function")
    assert how == "Provide them as request credentials or environment variables."
    assert any("credentials={" in step for step in steps)


def test_deployment_configuration_is_never_sent_to_the_service_page(monkeypatch):
    """A server host is not a user login, so the service's login page is the wrong place for it."""
    monkeypatch.setenv("TOOLUNIVERSE_CREDENTIAL_HELP", "Add it at https://example.org/credentials?key={key}.")
    how, _ = describe_missing_keys(["ESM_MCP_SERVER_HOST"], "run_one_function")
    assert "example.org" not in how


def test_a_gated_tool_on_a_service_names_the_page(monkeypatch, tu):
    monkeypatch.setenv("TOOLUNIVERSE_CREDENTIAL_HELP", "Add it at https://example.org/credentials?key={key}.")
    error, steps = _error(tu.run_one_function({"name": "ICD11_search_diseases", "arguments": {"query": "asthma"}}))
    assert "https://example.org/credentials?key=ICD_CLIENT_ID" in error
    assert steps == ["Add it at https://example.org/credentials?key=ICD_CLIENT_ID."]
