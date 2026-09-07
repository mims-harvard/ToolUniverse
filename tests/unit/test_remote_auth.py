import json
import stat
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tooluniverse import cli

KEY_A = "tu-sk-" + "a" * 60
KEY_B = "tu-sk-" + "b" * 60


def _auth_file(tmp_path, monkeypatch):
    path = tmp_path / "config" / "remote-auth.json"
    monkeypatch.setenv("TOOLUNIVERSE_REMOTE_AUTH_FILE", str(path))
    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY", raising=False)
    return path


def test_stored_remote_login_round_trip_is_private(tmp_path, monkeypatch):
    path = _auth_file(tmp_path, monkeypatch)

    written = cli._write_stored_remote_key(KEY_A)

    assert written == path
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert cli._read_stored_remote_key() == KEY_A


def test_environment_key_takes_precedence_over_stored_login(tmp_path, monkeypatch):
    _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_B)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY_A)

    assert cli._resolve_private_connection_key() == KEY_A


def test_share_preflight_recognizes_stored_login(tmp_path, monkeypatch):
    _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_A)

    assert cli._private_connection_key_available() is True


def test_share_preflight_rejects_malformed_environment_key(tmp_path, monkeypatch):
    _auth_file(tmp_path, monkeypatch)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", "not-a-key")

    with pytest.raises(SystemExit, match="invalid format"):
        cli._private_connection_key_available()


def test_stored_remote_login_rejects_group_readable_file(tmp_path, monkeypatch):
    path = _auth_file(tmp_path, monkeypatch)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"version": 1, "service_key": KEY_A}))
    path.chmod(0o640)

    with pytest.raises(ValueError, match="permissions must be 0600"):
        cli._read_stored_remote_key()


def test_remote_login_imports_protected_env_and_never_prints_key(
    tmp_path, monkeypatch, capsys
):
    auth_path = _auth_file(tmp_path, monkeypatch)
    source = tmp_path / "service.env"
    source.write_text(f"TOOLUNIVERSE_SERVICE_KEY='{KEY_A}'\n")
    source.chmod(0o600)
    calls = []
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda service, path, api_key="", payload=None: calls.append(
            (service, path, api_key, payload)
        )
        or {},
    )

    cli.cmd_remote_login(
        SimpleNamespace(env_file=str(source), service="https://example.test")
    )

    output = capsys.readouterr()
    assert calls == [("https://example.test", "/remote-servers/preflight", KEY_A, {})]
    assert KEY_A not in output.out
    assert KEY_A not in output.err
    assert cli._read_stored_remote_key() == KEY_A
    assert stat.S_IMODE(auth_path.stat().st_mode) == 0o600


def test_remote_login_does_not_store_an_unverified_key(tmp_path, monkeypatch):
    auth_path = _auth_file(tmp_path, monkeypatch)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY_A)
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("HTTP 401")),
    )

    with pytest.raises(SystemExit) as raised:
        cli.cmd_remote_login(
            SimpleNamespace(env_file=None, service="https://example.test")
        )

    assert raised.value.code == 2
    assert not auth_path.exists()


def test_device_login_polls_then_validates_without_printing_the_key(
    monkeypatch, capsys
):
    calls = []
    responses = iter(
        [
            {
                "device_code": "d" * 64,
                "user_code": "BCDF-GHJK",
                "verification_uri_complete": "https://connect.example/activate?user_code=BCDF-GHJK",
                "expires_in": 600,
                "interval": 1,
            },
            cli._PlatformHTTPError(
                "waiting", status=400, error_code="authorization_pending"
            ),
            {"access_token": KEY_A, "purpose": "relay"},
            {"ok": True, "credential_type": "relay", "least_privilege": True},
        ]
    )

    def platform_request(service, path, api_key="", payload=None):
        calls.append((service, path, api_key, payload))
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(cli, "_platform_request", platform_request)
    monkeypatch.setattr("time.sleep", lambda _: None)

    assert (
        cli._device_authorization_login("https://api.example", no_browser=True) == KEY_A
    )
    output = capsys.readouterr()
    assert "BCDF-GHJK" in output.out
    assert "https://connect.example/activate" in output.out
    assert KEY_A not in output.out
    assert KEY_A not in output.err
    assert [call[1] for call in calls] == [
        "/auth/device/start",
        "/auth/device/token",
        "/auth/device/token",
        "/remote-servers/preflight",
    ]


def test_device_login_rejects_invalid_platform_authorization_url(monkeypatch):
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda *args, **kwargs: {
            "device_code": "d" * 64,
            "user_code": "BCDF-GHJK",
            "verification_uri_complete": "javascript:alert(1)",
            "expires_in": 600,
            "interval": 5,
        },
    )

    with pytest.raises(RuntimeError, match="invalid device authorization response"):
        cli._device_authorization_login("https://api.example", no_browser=True)


def test_device_login_surfaces_browser_denial_without_a_secret(monkeypatch, capsys):
    responses = iter(
        [
            {
                "device_code": "d" * 64,
                "user_code": "BCDF-GHJK",
                "verification_uri_complete": "https://connect.example/activate?user_code=BCDF-GHJK",
                "expires_in": 600,
                "interval": 1,
            },
            cli._PlatformHTTPError("denied", status=400, error_code="access_denied"),
        ]
    )

    def platform_request(*args, **kwargs):
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(cli, "_platform_request", platform_request)
    monkeypatch.setattr("time.sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="browser authorization was denied"):
        cli._device_authorization_login("https://api.example", no_browser=True)
    assert KEY_A not in capsys.readouterr().out


def test_device_login_replaces_one_expired_request(monkeypatch, capsys):
    attempts = []

    def authorize_attempt(*_args, **_kwargs):
        attempts.append(True)
        if len(attempts) == 1:
            raise cli._DeviceAuthorizationExpired("expired")
        return KEY_A

    monkeypatch.setattr(cli, "_device_authorization_attempt", authorize_attempt)

    assert cli._device_authorization_login(
        "https://api.example", no_browser=True
    ) == KEY_A
    assert len(attempts) == 2
    assert "fresh link automatically" in capsys.readouterr().out


def test_device_login_stops_after_two_expired_requests(monkeypatch):
    monkeypatch.setattr(
        cli,
        "_device_authorization_attempt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            cli._DeviceAuthorizationExpired("expired")
        ),
    )

    with pytest.raises(RuntimeError, match="expired twice"):
        cli._device_authorization_login("https://api.example", no_browser=True)


def test_failed_remote_login_preserves_previous_verified_key(tmp_path, monkeypatch):
    _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_B)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY_A)
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("HTTP 401")),
    )

    with pytest.raises(SystemExit):
        cli.cmd_remote_login(
            SimpleNamespace(env_file=None, service="https://example.test")
        )

    monkeypatch.delenv("TOOLUNIVERSE_SERVICE_KEY")
    assert cli._read_stored_remote_key() == KEY_B


def test_remote_share_missing_key_stops_before_provider_checks(
    tmp_path, monkeypatch, capsys
):
    _auth_file(tmp_path, monkeypatch)
    environment_check = Mock()
    monkeypatch.setattr(
        "tooluniverse.remote_runtime.check_environment", environment_check
    )

    with pytest.raises(SystemExit) as raised:
        cli.cmd_remote_run(SimpleNamespace(implementation="boltz", share=True))

    assert raised.value.code == 2
    environment_check.assert_not_called()
    assert "tu remote login" in capsys.readouterr().err


def test_remote_share_rejects_malformed_key_before_provider_checks(
    tmp_path, monkeypatch, capsys
):
    _auth_file(tmp_path, monkeypatch)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", "not-a-key")
    environment_check = Mock()
    monkeypatch.setattr(
        "tooluniverse.remote_runtime.check_environment", environment_check
    )

    with pytest.raises(SystemExit) as raised:
        cli.cmd_remote_run(SimpleNamespace(implementation="boltz", share=True))

    assert raised.value.code == 2
    environment_check.assert_not_called()
    output = capsys.readouterr()
    assert "invalid format" in output.err
    assert "not-a-key" not in output.err


def test_remote_share_rejects_revoked_key_before_provider_start(
    tmp_path, monkeypatch, capsys
):
    _auth_file(tmp_path, monkeypatch)
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", KEY_A)
    monkeypatch.setattr(
        "tooluniverse.remote_runtime.check_environment",
        lambda *args, **kwargs: {"ok": True, "implementation": "boltz"},
    )
    provider_start = Mock()
    monkeypatch.setattr("tooluniverse.remote_runtime.ensure_provider", provider_start)
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("HTTP 401")),
    )
    args = SimpleNamespace(
        implementation="boltz",
        share=True,
        python=None,
        allow_cpu=False,
        timeout=30,
        service="https://example.test",
    )

    with pytest.raises(SystemExit) as raised:
        cli.cmd_remote_run(args)

    assert raised.value.code == 2
    provider_start.assert_not_called()
    output = capsys.readouterr()
    assert "failed before provider startup" in output.err
    assert "tu remote login" in output.err
    assert KEY_A not in output.out
    assert KEY_A not in output.err


def test_remote_logout_removes_only_stored_login(tmp_path, monkeypatch):
    auth_path = _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_A)

    cli.cmd_remote_logout(SimpleNamespace())

    assert not auth_path.exists()


def test_remote_logout_can_revoke_before_removing_local_login(
    tmp_path, monkeypatch, capsys
):
    auth_path = _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_A)
    calls = []
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda service, path, **kwargs: calls.append((service, path, kwargs))
        or {"ok": True, "revoked": True},
    )

    cli.cmd_remote_logout(
        SimpleNamespace(revoke=True, service="https://api.example")
    )

    assert not auth_path.exists()
    assert calls == [
        (
            "https://api.example",
            "/remote-servers/connection-key",
            {"api_key": KEY_A, "method": "DELETE"},
        )
    ]
    assert KEY_A not in capsys.readouterr().out


def test_remote_logout_preserves_local_login_when_revocation_fails(
    tmp_path, monkeypatch
):
    auth_path = _auth_file(tmp_path, monkeypatch)
    cli._write_stored_remote_key(KEY_A)
    monkeypatch.setattr(
        cli,
        "_platform_request",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("HTTP 503")),
    )

    with pytest.raises(SystemExit):
        cli.cmd_remote_logout(
            SimpleNamespace(revoke=True, service="https://api.example")
        )

    assert auth_path.exists()


def test_remote_share_alias_sets_share_without_requiring_flag(monkeypatch):
    captured = []
    monkeypatch.setattr(cli, "cmd_remote_run", lambda args: captured.append(args))
    monkeypatch.setattr(sys, "argv", ["tu", "remote", "share", "mofa"])

    cli.main()

    assert len(captured) == 1
    assert captured[0].implementation == "mofa"
    assert captured[0].share is True
