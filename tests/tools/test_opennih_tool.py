"""Tests for the OpenNIH MCP adapter and its static tool definitions."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from tooluniverse import ToolUniverse
from tooluniverse.opennih_tool import OpenNIHTool


CONFIG_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "opennih_tools.json"
)
GENERATED_TOOLS_DIR = CONFIG_PATH.parents[1] / "tools"


def _config(operation: str = "search_grants") -> dict:
    return {
        "name": f"OpenNIH_{operation}",
        "type": "OpenNIHTool",
        "operation": operation,
        "server_url": "https://mcp.opennih.org/mcp",
    }


def _static_config(operation: str) -> dict:
    configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return next(config for config in configs if config["operation"] == operation)


@pytest.mark.unit
def test_opennih_tool_returns_structured_content(monkeypatch):
    """The adapter should remove the MCP envelope around structured output."""
    tool = OpenNIHTool(_config())

    def fake_request(method, params):
        assert method == "tools/call"
        assert params["name"] == "search_grants"
        assert params["arguments"] == {"query": "CRISPR"}
        return {
            "structuredContent": {"meta": {"total": 1}, "results": []},
            "isError": False,
        }

    monkeypatch.setattr(tool, "_make_mcp_request", fake_request)
    assert tool.run({"query": "CRISPR"}) == {
        "status": "success",
        "data": {"meta": {"total": 1}, "results": []},
    }


@pytest.mark.unit
def test_opennih_tool_parses_text_fallback(monkeypatch):
    """Older MCP clients exposing only text blocks should remain supported."""
    tool = OpenNIHTool(_config("source_status"))

    def fake_request(_method, _params):
        return {
            "content": [{"type": "text", "text": '{"loaded": true}'}],
            "isError": False,
        }

    monkeypatch.setattr(tool, "_make_mcp_request", fake_request)
    assert tool.run({}) == {"status": "success", "data": {"loaded": True}}


@pytest.mark.unit
def test_opennih_tool_converts_mcp_errors(monkeypatch):
    """Remote MCP failures should be returned rather than raised."""
    tool = OpenNIHTool(_config("fetch"))

    def fake_request(_method, _params):
        return {
            "content": [{"type": "text", "text": "Grant not found"}],
            "isError": True,
        }

    monkeypatch.setattr(tool, "_make_mcp_request", fake_request)
    assert tool.run({"id": "1R01CA123456-01"}) == {
        "status": "error",
        "error": "Grant not found",
    }


@pytest.mark.unit
def test_opennih_tool_sends_stateless_jsonrpc_and_decodes_utf8(monkeypatch):
    """The HTTP adapter should parse OpenNIH's stateless SSE transport."""
    tool = OpenNIHTool(_config("source_status"))
    captured = {}

    class FakeResponse:
        headers = {"content-type": "text/event-stream"}
        encoding = None
        _body = (
            "event: message\n"
            'data: {"jsonrpc":"2.0","id":"request-1",'
            '"result":{"structuredContent":{"note":"snapshot — current"},'
            '"isError":false}}\n\n'
        ).encode("utf-8")

        @property
        def text(self):
            return self._body.decode(self.encoding or "latin-1")

        def raise_for_status(self):
            return None

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("tooluniverse.opennih_tool.uuid.uuid4", lambda: "request-1")
    monkeypatch.setattr("tooluniverse.opennih_tool.requests.post", fake_post)

    result = tool._make_mcp_request(
        "tools/call", {"name": "source_status", "arguments": {}}
    )
    assert result["structuredContent"]["note"] == "snapshot — current"
    assert captured["url"] == "https://mcp.opennih.org/mcp"
    assert captured["json"]["method"] == "tools/call"
    assert captured["timeout"] == (10, 30)


@pytest.mark.unit
def test_opennih_tool_parses_multiline_sse_events(monkeypatch):
    """SSE data split across multiple data fields should form one JSON message."""
    tool = OpenNIHTool(_config("source_status"))

    class FakeResponse:
        headers = {"Content-Type": "Text/Event-Stream; charset=utf-8"}
        text = (
            'data: {"jsonrpc":"2.0","id":"request-2",\n'
            'data: "result":{"structuredContent":{"loaded":true}}}\n\n'
        )
        encoding = None

        def raise_for_status(self):
            return None

    monkeypatch.setattr("tooluniverse.opennih_tool.uuid.uuid4", lambda: "request-2")
    monkeypatch.setattr(
        "tooluniverse.opennih_tool.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    assert tool._make_mcp_request("tools/call", {}) == {
        "structuredContent": {"loaded": True}
    }


@pytest.mark.unit
def test_opennih_tool_parses_json_transport(monkeypatch):
    """A conforming application/json MCP response should also be accepted."""
    tool = OpenNIHTool(_config("source_status"))

    class FakeResponse:
        headers = {"content-type": "application/json"}
        encoding = None

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": "request-3",
                "result": {"structuredContent": {"loaded": True}},
            }

    monkeypatch.setattr("tooluniverse.opennih_tool.uuid.uuid4", lambda: "request-3")
    monkeypatch.setattr(
        "tooluniverse.opennih_tool.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    assert tool._make_mcp_request("tools/call", {}) == {
        "structuredContent": {"loaded": True}
    }


@pytest.mark.unit
@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (requests.exceptions.Timeout(), "OpenNIH request timed out after 30 seconds"),
        (
            requests.exceptions.HTTPError(response=SimpleNamespace(status_code=429)),
            "OpenNIH HTTP error: 429",
        ),
        (requests.exceptions.HTTPError(), "OpenNIH HTTP error: unknown"),
    ],
)
def test_opennih_tool_normalizes_transport_errors(
    monkeypatch, exception, expected_error
):
    """Expected transport failures should produce stable tool error objects."""
    tool = OpenNIHTool(_config())

    def fail_request(_method, _params):
        raise exception

    monkeypatch.setattr(tool, "_make_mcp_request", fail_request)
    assert tool.run({"query": "CRISPR"}) == {
        "status": "error",
        "error": expected_error,
    }


@pytest.mark.unit
def test_opennih_tool_rejects_mismatched_jsonrpc_id(monkeypatch):
    """A response for a different request must never be returned to the caller."""
    tool = OpenNIHTool(_config("source_status"))

    class FakeResponse:
        headers = {"content-type": "application/json"}
        encoding = None

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": "another-request",
                "result": {"structuredContent": {"loaded": True}},
            }

    monkeypatch.setattr("tooluniverse.opennih_tool.uuid.uuid4", lambda: "request-4")
    monkeypatch.setattr(
        "tooluniverse.opennih_tool.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    with pytest.raises(
        RuntimeError, match="OpenNIH returned no matching JSON-RPC response"
    ):
        tool._make_mcp_request("tools/call", {})


@pytest.mark.unit
def test_opennih_tool_raises_jsonrpc_error_message(monkeypatch):
    """JSON-RPC protocol errors should retain the server's useful message."""
    tool = OpenNIHTool(_config("source_status"))

    class FakeResponse:
        headers = {"content-type": "application/json"}
        encoding = None

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "jsonrpc": "2.0",
                "id": "request-5",
                "error": {"code": -32602, "message": "Invalid arguments"},
            }

    monkeypatch.setattr("tooluniverse.opennih_tool.uuid.uuid4", lambda: "request-5")
    monkeypatch.setattr(
        "tooluniverse.opennih_tool.requests.post",
        lambda *_args, **_kwargs: FakeResponse(),
    )

    with pytest.raises(RuntimeError, match="^Invalid arguments$"):
        tool._make_mcp_request("tools/call", {})


@pytest.mark.unit
def test_opennih_tool_rejects_unsupported_operation(monkeypatch):
    """An unknown operation should fail locally without making a request."""
    tool = OpenNIHTool(_config("not_a_real_tool"))

    def fail_on_network(*_args, **_kwargs):
        raise AssertionError("unsupported operation attempted a network request")

    monkeypatch.setattr(tool, "_make_mcp_request", fail_on_network)
    assert tool.run({}) == {
        "status": "error",
        "error": "Unsupported OpenNIH operation: not_a_real_tool",
    }


@pytest.mark.unit
def test_search_grants_warns_about_duplicate_full_project_rows(monkeypatch):
    """Repeated parent/component rows should be visible without altering totals."""
    tool = OpenNIHTool(_config("search_grants"))
    payload = {
        "meta": {
            "total": 2,
            "unique_project_nums": 1,
            "total_funding": 2_999_932,
        },
        "results": [
            {"project_num": "1U54AG099000-01", "award_amount": 1_499_966},
            {"project_num": "1U54AG099000-01", "award_amount": 1_499_966},
        ],
    }
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {"structuredContent": payload},
    )

    result = tool.run({"project_num": "1U54AG099000-01"})

    assert result["data"]["meta"]["total_funding"] == 2_999_932
    assert result["data"]["results"] == payload["results"]
    assert result["data"]["tooluniverse_contract_warnings"] == [
        {
            "code": "duplicate_full_project_rows",
            "message": (
                "The matching slice contains repeated full project numbers, which can "
                "represent parent and component rows. meta.total_funding is a row sum "
                "and may double-count unique-award dollars."
            ),
            "project_nums_on_page": ["1U54AG099000-01"],
            "slice_total_rows": 2,
            "slice_unique_project_nums": 1,
        }
    ]


@pytest.mark.unit
def test_search_grants_warns_when_duplicates_fall_outside_returned_page(monkeypatch):
    """Full-slice metadata should protect a one-row page from a false-safe result."""
    tool = OpenNIHTool(_config("search_grants"))
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {
            "structuredContent": {
                "meta": {"total": 7, "unique_project_nums": 1},
                "results": [{"project_num": "1U54AG099000-01"}],
            }
        },
    )

    result = tool.run({"project_num": "1U54AG099000-01", "limit": 1})
    warning = result["data"]["tooluniverse_contract_warnings"][0]

    assert warning["code"] == "duplicate_full_project_rows"
    assert "project_nums_on_page" not in warning
    assert warning["slice_total_rows"] == 7
    assert warning["slice_unique_project_nums"] == 1


@pytest.mark.unit
def test_pi_profile_warns_about_missing_publications_rows_and_collaborators(
    monkeypatch,
):
    """PI profiles should expose all known semantic traps as stable warnings."""
    tool = OpenNIHTool(_config("get_pi_profile"))
    payload = {
        "profile": {"total_funding": 4_680_010, "grant_count": 4},
        "grants": [
            {"project_num": "1U54AG099000-01", "amount": 1_499_966},
            {"project_num": "1U54AG099000-01", "amount": 1_499_966},
        ],
        "collaborators": [{"name": "Example PI", "shared_grants": 1}],
    }
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {"structuredContent": payload},
    )

    result = tool.run({"profile_id": "1891769"})
    warning_codes = {
        warning["code"] for warning in result["data"]["tooluniverse_contract_warnings"]
    }

    assert result["data"]["profile"] == payload["profile"]
    assert warning_codes == {
        "publications_not_exposed",
        "profile_row_counts_not_awards",
        "shared_award_not_direct_collaboration",
    }


@pytest.mark.unit
def test_pi_profile_missing_publications_is_not_zero_publications(monkeypatch):
    """Even a simple profile should warn when the publication field is absent."""
    tool = OpenNIHTool(_config("get_pi_profile"))
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {
            "structuredContent": {"profile": {}, "grants": [], "collaborators": []}
        },
    )

    result = tool.run({"profile_id": "6569262"})

    assert [
        warning["code"] for warning in result["data"]["tooluniverse_contract_warnings"]
    ] == ["publications_not_exposed", "profile_row_counts_not_awards"]


@pytest.mark.unit
def test_pi_profile_warns_that_collaborators_ignore_year_window(monkeypatch):
    """A windowed PI response must not imply collaborators share that window."""
    tool = OpenNIHTool(_config("get_pi_profile"))
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {
            "structuredContent": {
                "profile": {"grant_count": 0, "total_funding": None},
                "grants": [],
                "collaborators": [{"profile_id": "2", "shared_grants": 1}],
                "meta": {"fiscal_year_start": 2100, "fiscal_year_end": 2100},
            }
        },
    )

    result = tool.run(
        {"profile_id": "1891769", "fiscal_year_start": 2100, "fiscal_year_end": 2100}
    )
    warnings = {
        warning["code"]: warning
        for warning in result["data"]["tooluniverse_contract_warnings"]
    }

    assert warnings["collaborators_not_year_filtered"] == {
        "code": "collaborators_not_year_filtered",
        "message": (
            "The fiscal-year window filters grants and profile totals, but not "
            "collaborators. Collaborator rows can come from shared awards outside "
            "the requested window."
        ),
        "requested_fiscal_year_start": 2100,
        "requested_fiscal_year_end": 2100,
    }


@pytest.mark.unit
def test_contract_warning_codes_are_not_duplicated(monkeypatch):
    """Server-provided warnings should not be repeated by the local adapter."""
    tool = OpenNIHTool(_config("get_pi_profile"))
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {
            "structuredContent": {
                "profile": {},
                "grants": [],
                "collaborators": [],
                "publications": [],
                "tooluniverse_contract_warnings": [
                    {"code": "profile_row_counts_not_awards", "message": "server"}
                ],
            }
        },
    )

    result = tool.run({"profile_id": "1"})
    warnings = result["data"]["tooluniverse_contract_warnings"]

    assert warnings == [{"code": "profile_row_counts_not_awards", "message": "server"}]


@pytest.mark.unit
def test_fetch_warns_when_canonical_row_has_components(monkeypatch):
    """A canonical fetch row must not masquerade as a deduplicated award total."""
    tool = OpenNIHTool(_config("fetch"))
    monkeypatch.setattr(
        tool,
        "_make_mcp_request",
        lambda *_args, **_kwargs: {
            "structuredContent": {
                "metadata": {"award_amount": 1_499_966, "matching_rows": 7},
            }
        },
    )

    result = tool.run({"id": "1U54AG099000-01"})

    assert result["data"]["metadata"]["award_amount"] == 1_499_966
    assert result["data"]["tooluniverse_contract_warnings"] == [
        {
            "code": "canonical_fetch_has_components",
            "message": (
                "fetch returned one canonical row from multiple matching rows. Its amount "
                "is not a sum or deduplicated total for all components."
            ),
            "matching_rows": 7,
        }
    ]


@pytest.mark.unit
def test_opennih_config_defines_all_supported_operations():
    """Static definitions should cover every supported server operation."""
    configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    operations = {config["operation"] for config in configs}

    assert operations == OpenNIHTool.SUPPORTED_OPERATIONS
    assert len(configs) == len(operations) == 14
    for config in configs:
        assert config["name"] == f"OpenNIH_{config['operation']}"
        assert len(config["name"]) <= 55
        assert config["type"] == "OpenNIHTool"
        assert config["server_url"] == "https://mcp.opennih.org/mcp"
        assert config["test_examples"]
        assert "oneOf" in config["return_schema"]
        assert config["parameter"]["additionalProperties"] is False

    descriptions = {config["operation"]: config["description"] for config in configs}
    assert "row sum" in descriptions["search_grants"][:160]
    assert "Publications are not returned" in descriptions["get_pi_profile"][:80]
    assert "not a component sum" in descriptions["fetch"][:160]


@pytest.mark.unit
def test_opennih_rejects_unknown_parameters_before_network(monkeypatch):
    """Misspelled filters must fail instead of silently widening a query."""
    tool = OpenNIHTool(_static_config("search_grants"))

    def fail_on_network(*_args, **_kwargs):
        raise AssertionError("invalid arguments attempted a network request")

    monkeypatch.setattr(tool, "_make_mcp_request", fail_on_network)
    result = tool.run(
        {"query": "CRISPR", "fiscal_yaer_start": 2025, "limit": 1}
    )

    assert result["status"] == "error"
    assert "Additional properties are not allowed" in result["error"]
    assert "fiscal_yaer_start" in result["error"]


@pytest.mark.unit
def test_opennih_rejects_reverse_year_window_before_network(monkeypatch):
    """Cross-field year ordering should be checked locally for every endpoint."""
    tool = OpenNIHTool(_static_config("funding_trend"))

    def fail_on_network(*_args, **_kwargs):
        raise AssertionError("invalid year window attempted a network request")

    monkeypatch.setattr(tool, "_make_mcp_request", fail_on_network)
    result = tool.run({"fiscal_year_start": 2025, "fiscal_year_end": 2020})

    assert result == {
        "status": "error",
        "error": (
            "Parameter validation failed: fiscal_year_start must be less than or "
            "equal to fiscal_year_end"
        ),
    }


@pytest.mark.unit
def test_generated_opennih_wrapper_docs_include_contract_caveats():
    """Generated direct-import docs must not lag behind the source config."""
    expected_caveats = {
        "OpenNIH_search_grants.py": "total_funding is a row sum",
        "OpenNIH_get_pi_profile.py": "Publications are not returned",
        "OpenNIH_fetch.py": "metadata.matching_rows is greater than one",
    }

    for filename, caveat in expected_caveats.items():
        wrapper = (GENERATED_TOOLS_DIR / filename).read_text(encoding="utf-8")
        assert caveat in wrapper[:1000], filename


@pytest.mark.unit
def test_opennih_tools_register_without_network(monkeypatch):
    """Loading the OpenNIH category should register tools without MCP discovery."""

    def fail_on_network(*_args, **_kwargs):
        raise AssertionError("OpenNIH category load attempted a network request")

    monkeypatch.setattr(OpenNIHTool, "_make_mcp_request", fail_on_network)
    tu = ToolUniverse()
    tu.load_tools(tool_type=["opennih"])

    assert set(tu.all_tool_dict) == {
        f"OpenNIH_{operation}" for operation in OpenNIHTool.SUPPORTED_OPERATIONS
    }
    assert hasattr(tu.tools, "OpenNIH_search_grants")
