"""CLI and startup-boundary tests for the scientific MCP server."""

import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tooluniverse import server_security
from tooluniverse import smcp_server
from tooluniverse.smcp import SMCP


class _FakeSMCP:
    instances = []
    run_error = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.run_calls = []
        self.__class__.instances.append(self)

    def run_simple(self, **kwargs):
        self.run_calls.append(kwargs)
        if self.__class__.run_error:
            raise self.__class__.run_error


@pytest.fixture(autouse=True)
def _clean_cli_state(monkeypatch):
    from tooluniverse import logging_config

    _FakeSMCP.instances = []
    _FakeSMCP.run_error = None
    monkeypatch.delenv(server_security.API_TOKEN_ENV, raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_STDIO_MODE", raising=False)
    monkeypatch.setattr(smcp_server, "SMCP", _FakeSMCP)
    monkeypatch.setattr(logging_config, "reconfigure_for_stdio", MagicMock())


def _invoke(monkeypatch, entrypoint, *arguments):
    monkeypatch.setattr(sys, "argv", ["tooluniverse-test", *arguments])
    entrypoint()
    assert len(_FakeSMCP.instances) == 1
    return _FakeSMCP.instances[0]


def test_main_http_defaults_are_dispatched_without_opening_listener(monkeypatch):
    server = _invoke(monkeypatch, smcp_server.run_smcp_server)

    assert server.kwargs["name"] == "ToolUniverse SMCP Server"
    assert server.kwargs["tool_categories"] is None
    assert server.kwargs["search_enabled"] is True
    assert server.kwargs["max_workers"] == 5
    assert server.run_calls == [
        {"transport": "http", "host": "127.0.0.1", "port": 7000}
    ]


def test_main_dispatches_full_scientific_server_configuration(monkeypatch, tmp_path):
    hook_path = tmp_path / "hooks.json"
    hook_path.write_text(json.dumps({"hooks": [{"type": "LoggingHook"}]}))

    server = _invoke(
        monkeypatch,
        smcp_server.run_smcp_server,
        "--transport",
        "sse",
        "--port",
        "8123",
        "--name",
        "Genomics MCP",
        "--categories",
        "uniprot",
        "opentarget",
        "--exclude-tools",
        "unsafe_tool",
        "--exclude-categories",
        "large_models",
        "--include-tools",
        "UniProt_get_entry_by_accession",
        "--tools-file",
        "selected-tools.txt",
        "--tool-config-files",
        "local:C:\\data\\tools.json",
        "--include-tool-types",
        "OpenTarget",
        "--exclude-tool-types",
        "AgenticTool",
        "--load",
        "./profile.yaml",
        "--workspace",
        "./workspace",
        "--global",
        "--no-search",
        "--max-workers",
        "9",
        "--hook-config-file",
        str(hook_path),
        "--compact-mode",
    )

    assert server.kwargs == {
        "name": "Genomics MCP",
        "profile": "./profile.yaml",
        "workspace": "./workspace",
        "use_global": True,
        "tool_categories": ["uniprot", "opentarget"],
        "exclude_tools": ["unsafe_tool"],
        "exclude_categories": ["large_models"],
        "include_tools": ["UniProt_get_entry_by_accession"],
        "tools_file": "selected-tools.txt",
        "tool_config_files": {"local": "C:\\data\\tools.json"},
        "include_tool_types": ["OpenTarget"],
        "exclude_tool_types": ["AgenticTool"],
        "search_enabled": False,
        "max_workers": 9,
        "hooks_enabled": True,
        "hook_config": {"hooks": [{"type": "LoggingHook"}]},
        "hook_type": None,
        "compact_mode": True,
    }
    assert server.run_calls == [
        {"transport": "sse", "host": "127.0.0.1", "port": 8123}
    ]


def test_stdio_entrypoint_keeps_protocol_on_stdio(monkeypatch):
    from tooluniverse import logging_config

    reconfigure = MagicMock()
    monkeypatch.setattr(logging_config, "reconfigure_for_stdio", reconfigure)

    server = _invoke(
        monkeypatch,
        smcp_server.run_stdio_server,
        "--categories",
        "uniprot",
        "--max-workers",
        "3",
        "--hooks",
        "--hook-type",
        "FileSaveHook",
    )

    assert server.kwargs["tool_categories"] == ["uniprot"]
    assert server.kwargs["max_workers"] == 3
    assert server.kwargs["hooks_enabled"] is True
    assert server.kwargs["hook_type"] == "FileSaveHook"
    assert server.run_calls == [{"transport": "stdio"}]
    assert reconfigure.call_count == 1
    assert os.environ["TOOLUNIVERSE_STDIO_MODE"] == "1"


def test_http_compatibility_entrypoint_uses_streamable_http(monkeypatch):
    server = _invoke(
        monkeypatch,
        smcp_server.run_http_server,
        "--port",
        "8088",
        "--compact-mode",
        "--load",
        "community/proteomics",
    )

    assert server.kwargs["auto_expose_tools"] is True
    assert server.kwargs["profile"] == "community/proteomics"
    assert server.kwargs["compact_mode"] is True
    assert server.run_calls == [
        {"transport": "http", "host": "127.0.0.1", "port": 8088}
    ]


@pytest.mark.parametrize("port", ["0", "-1", "65536", "not-a-port"])
@pytest.mark.parametrize(
    "entrypoint", [smcp_server.run_http_server, smcp_server.run_smcp_server]
)
def test_network_entrypoints_reject_invalid_ports(
    monkeypatch, entrypoint, port, capsys
):
    monkeypatch.setattr(sys, "argv", ["tooluniverse-test", "--port", port])

    with pytest.raises(SystemExit) as exc:
        entrypoint()

    assert exc.value.code == 2
    assert _FakeSMCP.instances == []
    assert "port" in capsys.readouterr().err


@pytest.mark.parametrize("workers", ["0", "-2", "invalid"])
@pytest.mark.parametrize(
    "entrypoint", [smcp_server.run_stdio_server, smcp_server.run_smcp_server]
)
def test_worker_entrypoints_reject_nonpositive_counts(
    monkeypatch, entrypoint, workers
):
    monkeypatch.setattr(
        sys, "argv", ["tooluniverse-test", "--max-workers", workers]
    )

    with pytest.raises(SystemExit) as exc:
        entrypoint()

    assert exc.value.code == 2
    assert _FakeSMCP.instances == []


@pytest.mark.parametrize("host", ["", "0.0.0.0", "api.internal.example"])
@pytest.mark.parametrize(
    "entrypoint", [smcp_server.run_http_server, smcp_server.run_smcp_server]
)
def test_network_entrypoints_reject_unauthenticated_remote_or_wildcard_bind(
    monkeypatch, entrypoint, host
):
    monkeypatch.setattr(sys, "argv", ["tooluniverse-test", "--host", host])

    with pytest.raises(SystemExit) as exc:
        entrypoint()

    assert exc.value.code == 1
    assert _FakeSMCP.instances == []


def test_authenticated_remote_bind_reaches_server_dispatch(monkeypatch):
    monkeypatch.setenv(server_security.API_TOKEN_ENV, "test-token")
    server = _invoke(
        monkeypatch,
        smcp_server.run_smcp_server,
        "--host",
        "0.0.0.0",
        "--port",
        "8443",
    )
    assert server.run_calls[0]["host"] == "0.0.0.0"


def test_stdio_transport_does_not_apply_network_bind_guard(monkeypatch):
    server = _invoke(
        monkeypatch,
        smcp_server.run_smcp_server,
        "--transport",
        "stdio",
        "--host",
        "",
    )
    assert server.run_calls[0]["transport"] == "stdio"


@pytest.mark.parametrize("host", ["", None])
def test_empty_hosts_are_not_classified_as_loopback(host):
    assert server_security.is_loopback_host(host) is False


def test_invalid_tool_config_spec_fails_before_server_construction(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["tooluniverse-test", "--tool-config-files", "missing-separator"],
    )

    with pytest.raises(SystemExit) as exc:
        smcp_server.run_smcp_server()

    assert exc.value.code == 1
    assert _FakeSMCP.instances == []


def test_server_start_failure_becomes_nonzero_cli_exit(monkeypatch):
    _FakeSMCP.run_error = RuntimeError("bind failed")
    monkeypatch.setattr(sys, "argv", ["tooluniverse-test"])

    with pytest.raises(SystemExit) as exc:
        smcp_server.run_smcp_server()

    assert exc.value.code == 1


@pytest.mark.parametrize("transport", ["http", "sse", "invalid"])
def test_run_simple_propagates_startup_errors_and_closes(transport):
    state = {"closed": False}

    async def close():
        state["closed"] = True

    server = SimpleNamespace(
        logger=MagicMock(),
        name="Test MCP",
        _exposed_tools=[],
        search_enabled=True,
        hooks_enabled=False,
        hook_type=None,
        hook_config=None,
        run=MagicMock(side_effect=RuntimeError("startup failed")),
        close=close,
    )

    with pytest.raises((RuntimeError, ValueError)):
        SMCP.run_simple(server, transport=transport)

    assert state["closed"] is True


def test_default_stdio_entrypoint_adds_compact_mode_once(monkeypatch):
    delegate = MagicMock()
    monkeypatch.setattr(smcp_server, "run_stdio_server", delegate)
    monkeypatch.setattr(sys, "argv", ["tooluniverse", "--verbose"])

    smcp_server.run_default_stdio_server()

    assert sys.argv.count("--compact-mode") == 1
    delegate.assert_called_once_with()
