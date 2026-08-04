import sys
from types import ModuleType
from unittest.mock import patch

import pytest

from tooluniverse import http_api_server_cli as cli
from tooluniverse import server_security


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_server_environment(monkeypatch):
    monkeypatch.delenv("TOOLUNIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("TOOLUNIVERSE_THREAD_POOL_SIZE", raising=False)


def _fake_server_module():
    module = ModuleType("tooluniverse.http_api_server")
    module.app = object()
    return module


def test_default_run_uses_loopback_single_worker_and_thread_pool(monkeypatch):
    server_module = _fake_server_module()
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api"])

    with (
        patch.dict(sys.modules, {"tooluniverse.http_api_server": server_module}),
        patch("uvicorn.run") as run,
    ):
        cli.run_http_api_server()

    run.assert_called_once_with(
        server_module.app,
        host="127.0.0.1",
        port=8080,
        workers=1,
        reload=False,
        log_level="info",
    )
    assert cli.os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"] == "20"


def test_multiple_workers_use_import_string_and_require_remote_token(monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_API_TOKEN", "secret")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "tooluniverse-http-api",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--workers",
            "3",
            "--thread-pool-size",
            "8",
            "--log-level",
            "warning",
        ],
    )

    with patch("uvicorn.run") as run:
        cli.run_http_api_server()

    run.assert_called_once_with(
        "tooluniverse.http_api_server:app",
        host="0.0.0.0",
        port=9000,
        workers=3,
        log_level="warning",
    )
    assert cli.os.environ["TOOLUNIVERSE_THREAD_POOL_SIZE"] == "8"


def test_reload_uses_app_object_and_one_worker(monkeypatch):
    server_module = _fake_server_module()
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api", "--reload"])

    with (
        patch.dict(sys.modules, {"tooluniverse.http_api_server": server_module}),
        patch("uvicorn.run") as run,
    ):
        cli.run_http_api_server()

    assert run.call_args.kwargs["reload"] is True
    assert run.call_args.kwargs["workers"] == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["--port", "0"],
        ["--port", "65536"],
        ["--port", "not-a-number"],
        ["--workers", "0"],
        ["--workers", "-1"],
        ["--thread-pool-size", "0"],
        ["--thread-pool-size", "-1"],
    ],
)
def test_invalid_numeric_arguments_exit_before_server_start(monkeypatch, arguments):
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api", *arguments])

    with patch("uvicorn.run") as run, pytest.raises(SystemExit) as exc_info:
        cli.run_http_api_server()

    assert exc_info.value.code == 2
    run.assert_not_called()
    assert "TOOLUNIVERSE_THREAD_POOL_SIZE" not in cli.os.environ


def test_reload_and_multiple_workers_are_rejected(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["tooluniverse-http-api", "--reload", "--workers", "2"],
    )

    with patch("uvicorn.run") as run, pytest.raises(SystemExit) as exc_info:
        cli.run_http_api_server()

    assert exc_info.value.code == 2
    run.assert_not_called()
    assert "TOOLUNIVERSE_THREAD_POOL_SIZE" not in cli.os.environ


@pytest.mark.parametrize("host", ["0.0.0.0", "", "   ", None])
def test_unknown_or_wildcard_hosts_are_not_loopback(host):
    assert server_security.is_loopback_host(host) is False


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_literal_loopback_hosts_remain_allowed(host):
    assert server_security.is_loopback_host(host) is True


@pytest.mark.parametrize("host", ["0.0.0.0", ""])
def test_remote_or_empty_bind_without_token_fails_before_mutation(
    monkeypatch, capsys, host
):
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api", "--host", host])

    with patch("uvicorn.run") as run, pytest.raises(SystemExit) as exc_info:
        cli.run_http_api_server()

    assert exc_info.value.code == 1
    assert "Refusing to bind" in capsys.readouterr().err
    run.assert_not_called()
    assert "TOOLUNIVERSE_THREAD_POOL_SIZE" not in cli.os.environ


def test_server_startup_error_returns_failure(monkeypatch, capsys):
    server_module = _fake_server_module()
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api"])

    with (
        patch.dict(sys.modules, {"tooluniverse.http_api_server": server_module}),
        patch("uvicorn.run", side_effect=RuntimeError("address in use")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.run_http_api_server()

    assert exc_info.value.code == 1
    assert "address in use" in capsys.readouterr().out


def test_keyboard_interrupt_returns_successful_shutdown(monkeypatch, capsys):
    server_module = _fake_server_module()
    monkeypatch.setattr(sys, "argv", ["tooluniverse-http-api"])

    with (
        patch.dict(sys.modules, {"tooluniverse.http_api_server": server_module}),
        patch("uvicorn.run", side_effect=KeyboardInterrupt),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.run_http_api_server()

    assert exc_info.value.code == 0
    assert "Server stopped by user" in capsys.readouterr().out
