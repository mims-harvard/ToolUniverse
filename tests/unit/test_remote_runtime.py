import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

from scripts.remote_validation.setup_skill_preflight import DEPLOYMENTS
from tooluniverse.remote_runtime import (
    REMOTE_BY_SLUG,
    REMOTE_DEPLOYMENTS,
    RemoteDeployment,
    _provider_probe_code,
    _check_provider_credentials,
    check_environment,
    child_environment,
    ensure_provider,
    resolve_python,
    start_provider,
)


def test_catalog_matches_setup_skills_and_covers_all_operations():
    runtime = {
        item.slug: (
            item.port,
            item.operations,
            item.required_env,
            item.path_env,
            item.required_commands,
        )
        for item in REMOTE_DEPLOYMENTS
    }
    skills = {
        item.slug: (
            item.port,
            item.operations,
            item.required_env,
            item.path_env,
            item.required_commands,
        )
        for item in DEPLOYMENTS
    }
    assert runtime == skills
    assert len(runtime) == 30
    assert sum(len(item.operations) for item in REMOTE_DEPLOYMENTS) == 41
    assert {
        item.slug: item.relay_workers
        for item in REMOTE_DEPLOYMENTS
        if item.relay_workers != 1
    } == {"expert-feedback": 2}


def test_catalog_modules_match_all_setup_skill_entrypoints():
    repository = Path(__file__).resolve().parents[2]
    documented = {}
    for deployment in REMOTE_DEPLOYMENTS:
        path = (
            repository / "skills" / f"setup-{deployment.slug}-remote-tool" / "SKILL.md"
        )
        match = re.search(
            r"^python -m (tooluniverse\.remote\.\S+)",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        assert match is not None
        documented[deployment.slug] = match.group(1)

    assert documented == {
        deployment.slug: deployment.module for deployment in REMOTE_DEPLOYMENTS
    }


def test_resolve_python_preserves_virtualenv_symlink(tmp_path):
    python = tmp_path / "provider-python"
    python.symlink_to(sys.executable)

    assert resolve_python(str(python)) == str(python.absolute())
    assert Path(resolve_python(str(python))).is_symlink()


def test_resolve_python_uses_conventional_provider_environment(tmp_path, monkeypatch):
    deployment = REMOTE_BY_SLUG["boltz"]
    python = tmp_path / ".venvs" / deployment.slug / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    monkeypatch.chdir(tmp_path)

    assert resolve_python(None, deployment) == str(python.absolute())


def test_resolve_python_uses_validated_live_environment_fallback(tmp_path, monkeypatch):
    deployment = REMOTE_BY_SLUG["boltz"]
    python = tmp_path / ".venvs" / f"{deployment.slug}-live" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(sys.executable)
    monkeypatch.chdir(tmp_path)

    assert resolve_python(None, deployment) == str(python.absolute())


def test_provider_probe_is_valid_python_for_gpu_and_cpu_deployments():
    compile(_provider_probe_code(REMOTE_BY_SLUG["boltz"]), "<gpu-probe>", "exec")
    compile(_provider_probe_code(REMOTE_BY_SLUG["mofa"]), "<cpu-probe>", "exec")


def test_child_environment_prepends_provider_bin_without_losing_existing_path(
    monkeypatch,
):
    monkeypatch.setenv("PATH", "/existing/bin")
    monkeypatch.setenv("TOOLUNIVERSE_SERVICE_KEY", "relay-secret")
    monkeypatch.setenv("USPTO_API_KEY", "provider-secret")
    deployment = REMOTE_BY_SLUG["boltz"]

    environment = child_environment("/provider/bin/python", deployment)

    assert environment["PATH"] == "/provider/bin" + os.pathsep + "/existing/bin"
    assert environment["TOOLUNIVERSE_MCP_HOST"] == "127.0.0.1"
    assert environment["TOOLUNIVERSE_MCP_PORT"] == "8080"
    assert "TOOLUNIVERSE_SERVICE_KEY" not in environment
    assert environment["USPTO_API_KEY"] == "provider-secret"


def test_environment_check_parses_final_json_line_and_never_discloses_secret(
    monkeypatch,
):
    secret = "must-never-appear-in-report"
    deployment = RemoteDeployment(
        "test",
        "example.provider",
        1234,
        ("operation",),
        required_env=("PROVIDER_SECRET",),
    )
    provider = {
        "python_version": [3, 12, 3],
        "module_available": True,
        "commands": {},
    }
    completed = subprocess.CompletedProcess(
        [sys.executable], 0, "provider notice\n" + json.dumps(provider) + "\n", ""
    )
    monkeypatch.setenv("PROVIDER_SECRET", secret)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    result = check_environment(deployment, python=sys.executable)

    assert result["ok"] is True
    assert result["provider_environment"] == [{"name": "PROVIDER_SECRET", "set": True}]
    assert secret not in json.dumps(result)
    assert result["secret_values_disclosed"] is False


def test_uspto_preflight_rejects_provider_key_before_launch_without_disclosing_it(
    monkeypatch,
):
    secret = "must-never-appear-in-report"
    deployment = REMOTE_BY_SLUG["uspto-downloader"]
    monkeypatch.setenv("USPTO_API_KEY", secret)
    monkeypatch.setattr(
        "tooluniverse.remote_runtime._uspto_credential_status",
        lambda *_args, **_kwargs: 403,
    )

    result = _check_provider_credentials(deployment, timeout=2)

    assert result == {
        "name": "USPTO_API_KEY",
        "checked": True,
        "ready": False,
        "http_status": 403,
        "detail": "USPTO rejected the key; renew or activate it before launch",
    }
    assert secret not in json.dumps(result)


def test_uspto_preflight_accepts_verified_provider_key_without_disclosing_it(
    monkeypatch,
):
    secret = "must-never-appear-in-report"
    deployment = REMOTE_BY_SLUG["uspto-downloader"]
    monkeypatch.setenv("USPTO_API_KEY", secret)
    monkeypatch.setattr(
        "tooluniverse.remote_runtime._uspto_credential_status",
        lambda *_args, **_kwargs: 200,
    )

    result = _check_provider_credentials(deployment, timeout=2)

    assert result["ready"] is True
    assert result["http_status"] == 200
    assert secret not in json.dumps(result)


def test_ensure_provider_reuses_only_an_exact_existing_endpoint(monkeypatch):
    deployment = REMOTE_BY_SLUG["boltz"]
    exact = {
        "ok": True,
        "reachable": True,
        "endpoint": deployment.endpoint,
        "discovered_operations": ["boltz2_docking"],
    }
    start = Mock()
    monkeypatch.setattr(
        "tooluniverse.remote_runtime.discover_endpoint", lambda *args, **kwargs: exact
    )
    monkeypatch.setattr("tooluniverse.remote_runtime.start_provider", start)

    managed, ready = ensure_provider(
        deployment,
        python=sys.executable,
        log_dir="logs",
        startup_timeout=1,
    )

    assert managed is None
    assert ready == exact
    start.assert_not_called()


def test_start_provider_uses_reviewed_module_and_dedicated_process_group(
    tmp_path, monkeypatch
):
    process = Mock()
    popen = Mock(return_value=process)
    monkeypatch.setattr(subprocess, "Popen", popen)
    deployment = REMOTE_BY_SLUG["expert-feedback"]

    managed = start_provider(
        deployment,
        python=sys.executable,
        log_dir=tmp_path,
    )
    try:
        command = popen.call_args.args[0]
        options = popen.call_args.kwargs
        assert command == [
            sys.executable,
            "-m",
            deployment.module,
            "--start-server",
        ]
        assert options["start_new_session"] is True
        assert "shell" not in options
    finally:
        managed.log_handle.close()
