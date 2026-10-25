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


def provider_module_source(module: str) -> tuple[Path, str]:
    """A reviewed provider's entry module, as text, without importing it.

    Importing one would pull in a model stack this environment does not have, and the
    questions below are about what the file says, not about what it does.
    """
    path = (
        Path(__file__).resolve().parents[2] / "src" / (module.replace(".", "/") + ".py")
    )
    return path, path.read_text(encoding="utf-8")


def test_a_provider_entry_point_serves_the_port_the_catalog_waits_on():
    """The failure this catches is silent on both sides.

    `register_mcp_tool` reads the server's address from `mcp_config`; the tool config
    beside it is handed to the tool and never read as server configuration. Three
    providers -- proteinmpnn, borzoi_calico and enformer_deepmind -- declared
    `server_name`, `host`, `port` and `transport` in the tool config, so they bound the
    default port 8000 while `tu remote run` and the provider pool polled the reviewed
    port and timed out with nothing to name. Verified by starting proteinmpnn's module,
    which bound 8000 for 8049, and again after the fix, which bound 8049 and matched the
    reviewed contract.

    A literal port must be the reviewed one; a computed one (evo2 reads an environment
    variable) is left to the provider, since the point here is that the key is where the
    registry looks at all.
    """
    import ast

    wrong_dict, wrong_port, positional = [], [], []
    for deployment in REMOTE_DEPLOYMENTS:
        path, source = provider_module_source(deployment.module)
        tree = ast.parse(source, filename=str(path))
        # Five providers keep their server configuration in a module-level `_MCP`, so a
        # name has to be followed to the dict it was assigned before anything can be
        # said about it.
        module_dicts = {
            node.targets[0].id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Dict)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = node.func.id if isinstance(node.func, ast.Name) else None
            if called == "start_mcp_server" and node.args:
                # `start_mcp_server(__file__)` passes a path as the port, which the
                # registry reports as "no tools registered for port <path>" and then
                # serves nothing at all.
                positional.append(deployment.slug)
            if called != "register_mcp_tool":
                continue
            keywords = {kw.arg: kw.value for kw in node.keywords}
            server = keywords.get("mcp_config")
            if isinstance(server, ast.Name):
                server = module_dicts.get(server.id)
            if not isinstance(server, ast.Dict):
                wrong_dict.append(deployment.slug)
                continue
            ports = [
                value
                for key, value in zip(server.keys, server.values)
                if isinstance(key, ast.Constant) and key.value == "port"
            ]
            if not ports:
                wrong_dict.append(deployment.slug)
            elif (
                isinstance(ports[0], ast.Constant) and ports[0].value != deployment.port
            ):
                wrong_port.append(
                    f"{deployment.slug}: {ports[0].value} != {deployment.port}"
                )

    assert positional == [], (
        f"start_mcp_server was given a port it cannot use: {positional}"
    )
    assert wrong_dict == [], (
        f"no mcp_config port, so these serve port 8000: {wrong_dict}"
    )
    assert wrong_port == [], f"serving a port the catalog does not call: {wrong_port}"


def test_ports_are_unique():
    """No two deployments may claim the same port.

    Every provider in the table binds its port on this one host, so two
    claiming the same number means whichever starts second cannot bind and the
    failure arrives as a start timeout naming no cause. Nothing checked this
    until two sessions, bringing up two providers in parallel against the same
    table, both took the next number they saw free and both wrote 8058 -- one
    in a commit, one in an uncommitted working tree, so no diff and no review
    put the two side by side. A count assertion cannot catch it (the counts
    stay right) and neither can `runtime == skills` (both halves agree on the
    wrong thing). This is the cheapest possible check and it is overdue.
    """
    ports = [item.port for item in REMOTE_DEPLOYMENTS]
    clashes = {p: [i.slug for i in REMOTE_DEPLOYMENTS if i.port == p] for p in ports if ports.count(p) > 1}
    assert not clashes, f"two deployments claim one port: {clashes}"
    # the same table reached through the setup-skill side, which is the copy a
    # second session is as likely to edit
    skill_ports = [item.port for item in DEPLOYMENTS]
    skill_clashes = {p: [i.slug for i in DEPLOYMENTS if i.port == p] for p in skill_ports if skill_ports.count(p) > 1}
    assert not skill_clashes, f"two setup skills claim one port: {skill_clashes}"


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
    assert len(runtime) == 59
    assert sum(len(item.operations) for item in REMOTE_DEPLOYMENTS) == 77
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
    # USPTO_API_KEY belongs to uspto-downloader, not to boltz. This assertion used to read
    # the other way round, because a provider inherited the whole environment and so could
    # see any credential that happened to be in the owner's shell. A provider now sees a
    # credential only when its own deployment declares it.
    assert "USPTO_API_KEY" not in environment


def test_a_provider_sees_a_credential_only_when_it_declares_it(monkeypatch):
    monkeypatch.setenv("USPTO_API_KEY", "provider-secret")

    declaring = child_environment(
        "/provider/bin/python", REMOTE_BY_SLUG["uspto-downloader"]
    )
    unrelated = child_environment("/provider/bin/python", REMOTE_BY_SLUG["boltz"])

    assert declaring["USPTO_API_KEY"] == "provider-secret"
    assert "USPTO_API_KEY" not in unrelated


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


def test_environment_check_does_not_report_unknown_probe_values_as_failed(
    monkeypatch,
):
    deployment = RemoteDeployment("test", "example.provider", 1234, ("operation",))
    completed = subprocess.CompletedProcess(
        [sys.executable], 1, "not-json\n", "private provider details"
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed)

    result = check_environment(deployment, python=sys.executable)

    assert result["ok"] is False
    assert result["python_supported_3_12"] is None
    assert result["provider"]["module_available"] is None
    assert "private provider details" not in json.dumps(result)


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
