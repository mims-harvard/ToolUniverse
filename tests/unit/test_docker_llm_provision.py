from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse.remote.docker_llm import client, provision

pytestmark = pytest.mark.unit

IMAGE = "registry.example/reviewed-llm@sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def _profile() -> dict:
    return {
        "version": 1,
        "profile_name": "reviewed-llm",
        "service_id": "reviewed-llm-service",
        "image": IMAGE,
        "container_port": 8000,
        "health_path": "/health",
        "inference_path": "/v1/chat/completions",
        "model": "reviewed-model",
        "tool": {
            "name": "ReviewedDockerEvidenceTool",
            "description": "Run bounded evidence prompts in the reviewed local container.",
            "max_prompt_chars": 5000,
            "max_tokens_cap": 1000,
            "default_temperature": 0.0,
        },
        "resources": {
            "cpus": 1.5,
            "memory_mb": 512,
            "pids_limit": 96,
            "tmpfs_mb": 64,
        },
        "timeouts": {"health_seconds": 10, "inference_seconds": 15},
    }


def _write_profile(tmp_path: Path, profile_data: dict | None = None) -> Path:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile_data or _profile()), encoding="utf-8")
    return path


def _container_record(
    profile_data: dict,
    digest: str,
    *,
    name: str = "tooluniverse-reviewed-llm",
    port: int = 19090,
    running: bool = True,
    labels: dict | None = None,
) -> dict:
    resources = profile_data["resources"]
    return {
        "Name": f"/{name}",
        "Image": IMAGE_ID,
        "Config": {
            "Image": profile_data["image"],
            "Labels": labels
            or {
                provision._MANAGED_LABEL: "true",
                provision._PROFILE_LABEL: digest,
                provision._SERVICE_LABEL: profile_data["service_id"],
            },
        },
        "State": {"Running": running},
        "HostConfig": {
            "PortBindings": {
                f"{profile_data['container_port']}/tcp": [
                    {"HostIp": "127.0.0.1", "HostPort": str(port)}
                ]
            },
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "Privileged": False,
            "NetworkMode": "default",
            "PidMode": "",
            "IpcMode": "private",
            "Binds": None,
            "PidsLimit": resources["pids_limit"],
            "Memory": resources["memory_mb"] * 1024 * 1024,
            "NanoCpus": int(resources["cpus"] * 1_000_000_000),
        },
    }


class FakeDocker:
    def __init__(self, profile_data: dict, digest: str, *, existing=None):
        self.profile = profile_data
        self.digest = digest
        self.record = existing
        self.commands: list[list[str]] = []

    def __call__(self, arguments, *, check=True, timeout=60):
        args = list(arguments)
        self.commands.append(args)
        stdout = ""
        stderr = ""
        returncode = 0
        if args == ["context", "show"]:
            stdout = "default\n"
        elif args == ["context", "inspect", "default"]:
            stdout = json.dumps(
                [{"Endpoints": {"docker": {"Host": "unix:///var/run/docker.sock"}}}]
            )
        elif args[:2] == ["version", "--format"]:
            stdout = "27.5.1\n"
        elif args[:3] == ["image", "inspect", "--format"]:
            stdout = IMAGE_ID + "\n"
        elif args[:2] == ["container", "inspect"]:
            if self.record is None:
                returncode, stderr = 1, "Error: No such object"
            else:
                stdout = json.dumps([self.record])
        elif args[0] == "run":
            self.record = _container_record(self.profile, self.digest)
            stdout = "container-id\n"
        elif args[:2] == ["container", "start"]:
            self.record["State"]["Running"] = True
        elif args[:2] == ["container", "stop"]:
            self.record["State"]["Running"] = False
        elif args[:3] == ["container", "rm", "--force"]:
            self.record = None
        else:
            raise AssertionError(f"Unexpected Docker command: {args}")
        result = subprocess.CompletedProcess(
            ["docker", *args], returncode, stdout, stderr
        )
        if check and returncode:
            raise provision.DockerProvisionError("fake Docker failure")
        return result


@pytest.fixture
def approved_image(monkeypatch):
    monkeypatch.setenv("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES", IMAGE)


def test_profile_rejects_unallowlisted_images_and_unknown_docker_controls(
    tmp_path, monkeypatch
):
    path = _write_profile(tmp_path)
    monkeypatch.delenv("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES", raising=False)
    with pytest.raises(provision.DockerProvisionError, match="must list"):
        provision.load_profile(path)

    monkeypatch.setenv("TOOLUNIVERSE_DOCKER_ALLOWED_IMAGES", IMAGE)
    unsafe = _profile()
    unsafe["volumes"] = ["/:/host"]
    path = _write_profile(tmp_path, unsafe)
    with pytest.raises(provision.DockerProvisionError, match="fields"):
        provision.load_profile(path)


def test_plan_has_fixed_loopback_and_no_arbitrary_docker_escape(
    tmp_path, approved_image
):
    plan = provision.plan_container(_write_profile(tmp_path), host_port=19090)
    command = plan["docker_argv"]
    assert command[:3] == ["docker", "run", "--detach"]
    assert "127.0.0.1:19090:8000" in command
    assert [
        command[index + 1]
        for index, item in enumerate(command[:-1])
        if item == "--cap-drop"
    ] == ["ALL"]
    assert "--read-only" in command
    assert "no-new-privileges:true" in command
    assert "--pull" in command and "never" in command
    assert "--volume" not in command and "-v" not in command
    assert "--privileged" not in command
    assert "--network" not in command
    assert command[-1] == IMAGE


def test_provision_inspects_security_before_publishing_client(
    tmp_path, monkeypatch, approved_image
):
    profile_path = _write_profile(tmp_path)
    profile_data, digest = provision.load_profile(profile_path)
    fake = FakeDocker(profile_data, digest)
    monkeypatch.setattr(provision, "_run_docker", fake)
    monkeypatch.setattr(provision, "_port_is_available", lambda port: True)
    monkeypatch.setattr(
        provision,
        "_wait_for_health",
        lambda profile_data, port: {
            "status": "ok",
            "service_id": profile_data["service_id"],
            "model": profile_data["model"],
        },
    )

    result = provision.provision_container(
        profile_path, host_port=19090, workspace=tmp_path / "workspace"
    )

    assert result["security"]["read_only_rootfs"] is True
    assert result["security"]["bind_mounts"] == 0
    assert result["security"]["host_binding"] == "127.0.0.1:19090"
    assert result["image"] == IMAGE
    assert result["image_id"] == IMAGE_ID
    assert len(result["record_sha256"]) == 64
    assert Path(result["record_path"]).exists()


def test_health_failure_removes_only_new_managed_container(
    tmp_path, monkeypatch, approved_image
):
    profile_path = _write_profile(tmp_path)
    profile_data, digest = provision.load_profile(profile_path)
    fake = FakeDocker(profile_data, digest)
    monkeypatch.setattr(provision, "_run_docker", fake)
    monkeypatch.setattr(provision, "_port_is_available", lambda port: True)

    def fail_health(*args):
        raise provision.DockerProvisionError("health identity failed")

    monkeypatch.setattr(provision, "_wait_for_health", fail_health)
    with pytest.raises(provision.DockerProvisionError, match="health"):
        provision.provision_container(profile_path, host_port=19090)
    assert ["container", "rm", "--force", "tooluniverse-reviewed-llm"] in fake.commands
    assert fake.record is None


def test_mismatched_existing_container_is_never_started_or_removed(
    tmp_path, monkeypatch, approved_image
):
    profile_path = _write_profile(tmp_path)
    profile_data, digest = provision.load_profile(profile_path)
    existing = _container_record(
        profile_data,
        digest,
        running=False,
        labels={provision._MANAGED_LABEL: "false"},
    )
    fake = FakeDocker(profile_data, digest, existing=existing)
    monkeypatch.setattr(provision, "_run_docker", fake)
    with pytest.raises(provision.DockerProvisionError, match="not managed"):
        provision.provision_container(profile_path, host_port=19090)
    assert not any(
        command[:2] in (["container", "start"], ["container", "rm"])
        for command in fake.commands
    )
    assert fake.record is existing


def test_stop_and_remove_require_exact_profile_and_confirmation(
    tmp_path, monkeypatch, approved_image
):
    profile_path = _write_profile(tmp_path)
    profile_data, digest = provision.load_profile(profile_path)
    fake = FakeDocker(
        profile_data, digest, existing=_container_record(profile_data, digest)
    )
    monkeypatch.setattr(provision, "_run_docker", fake)
    stopped = provision.stop_container(profile_path, host_port=19090)
    assert stopped == {
        "container_name": "tooluniverse-reviewed-llm",
        "stopped": True,
        "was_running": True,
    }
    with pytest.raises(provision.DockerProvisionError, match="confirmation"):
        provision.remove_container(profile_path, host_port=19090)
    removed = provision.remove_container(
        profile_path, host_port=19090, workspace=tmp_path, confirm=True
    )
    assert removed["removed"] is True
    assert fake.record is None


def test_docker_subprocess_environment_drops_remote_daemon_controls(monkeypatch):
    monkeypatch.setenv("DOCKER_HOST", "tcp://untrusted.example:2375")
    monkeypatch.setenv("DOCKER_CONTEXT", "remote")
    monkeypatch.setenv("DOCKER_TLS_VERIFY", "1")
    environment = provision._docker_environment()
    assert "PATH" in environment
    assert not {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY"} & set(environment)


def test_docker_check_rejects_remote_saved_context(monkeypatch):
    def fake_docker(arguments, *, check=True, timeout=60):
        if list(arguments) == ["context", "show"]:
            output = "remote-production\n"
        elif list(arguments) == ["context", "inspect", "remote-production"]:
            output = json.dumps(
                [{"Endpoints": {"docker": {"Host": "ssh://admin@example.com"}}}]
            )
        else:
            raise AssertionError("Version must not run for a remote context")
        return subprocess.CompletedProcess(["docker", *arguments], 0, output, "")

    monkeypatch.setattr(provision, "_run_docker", fake_docker)
    with pytest.raises(provision.DockerProvisionError, match="local socket"):
        provision._check_docker()


class FakeResponse:
    def __init__(self, payload: dict, *, status=200, redirect=False, size_header=None):
        self.body = json.dumps(payload).encode()
        self.status_code = status
        self.is_redirect = redirect
        self.is_permanent_redirect = False
        self.headers = {
            "Content-Type": "application/json",
            "Content-Length": str(
                size_header if size_header is not None else len(self.body)
            ),
        }
        self.closed = False

    def iter_content(self, chunk_size):
        yield self.body

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response, health_response=None):
        self.response = response
        self.health_response = health_response or FakeResponse(
            {
                "status": "ok",
                "service_id": "reviewed-llm-service",
                "model": "reviewed-model",
            }
        )
        self.trust_env = True
        self.request = None
        self.health_request = None
        self.closed = False

    def get(self, url, **kwargs):
        self.health_request = (url, kwargs, self.trust_env)
        return self.health_response

    def post(self, url, **kwargs):
        self.request = (url, kwargs, self.trust_env)
        return self.response

    def close(self):
        self.closed = True


def test_published_client_executes_through_real_tooluniverse(
    tmp_path, monkeypatch, approved_image
):
    profile_path = _write_profile(tmp_path)
    profile_data, digest = provision.load_profile(profile_path)
    profile_data["tool"]["default_temperature"] = 0.65
    profile_path = _write_profile(tmp_path, profile_data)
    profile_data, digest = provision.load_profile(profile_path)
    fake_docker = FakeDocker(profile_data, digest)
    monkeypatch.setattr(provision, "_run_docker", fake_docker)
    monkeypatch.setattr(provision, "_port_is_available", lambda port: True)
    monkeypatch.setattr(
        provision,
        "_wait_for_health",
        lambda profile_data, port: {
            "status": "ok",
            "service_id": profile_data["service_id"],
            "model": profile_data["model"],
        },
    )
    workspace = tmp_path / "workspace"
    provision.provision_container(profile_path, host_port=19090, workspace=workspace)
    response = FakeResponse(
        {
            "model": "reviewed-model",
            "choices": [
                {"message": {"role": "assistant", "content": "bounded synthesis"}}
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }
    )
    session = FakeSession(response)
    monkeypatch.setattr(client.requests, "Session", lambda: session)
    tooluniverse = ToolUniverse(
        tool_files={}, keep_default_tools=False, workspace=str(tmp_path / "runtime")
    )
    try:
        assert (
            provision.load_provisioned_tool(
                tooluniverse, "ReviewedDockerEvidenceTool", workspace=workspace
            )
            == "ReviewedDockerEvidenceTool"
        )
        result = tooluniverse.run_one_function(
            {
                "name": "ReviewedDockerEvidenceTool",
                "arguments": {"prompt": "Synthesize records A, B, and C."},
            },
            use_cache=False,
        )
    finally:
        tooluniverse.close()
    assert result["status"] == "success"
    assert result["data"]["response"] == "bounded synthesis"
    assert result["data"]["provenance"]["image_id"] == IMAGE_ID
    assert session.request[0] == "http://127.0.0.1:19090/v1/chat/completions"
    assert session.request[1]["json"]["temperature"] == 0.65
    assert session.request[1]["allow_redirects"] is False
    assert session.request[2] is False
    assert session.health_request[0] == "http://127.0.0.1:19090/health"
    assert session.health_request[1]["allow_redirects"] is False
    assert session.health_request[2] is False
    assert response.closed and session.health_response.closed and session.closed


def test_client_rechecks_live_service_identity_before_inference(monkeypatch):
    profile_data = _profile()
    config = provision._client_config(profile_data, "c" * 64, IMAGE_ID, 19090)
    inference = FakeResponse(
        {"choices": [{"message": {"content": "must not be reached"}}]}
    )
    wrong_health = FakeResponse(
        {
            "status": "ok",
            "service_id": "unrelated-loopback-service",
            "model": "reviewed-model",
        }
    )
    session = FakeSession(inference, health_response=wrong_health)
    monkeypatch.setattr(client.requests, "Session", lambda: session)

    with pytest.raises(client.DockerLLMClientError, match="identity"):
        client.DockerLLMClientTool(config).run({"prompt": "test prompt"})

    assert session.request is None
    assert wrong_health.closed and session.closed


def test_client_rejects_unknown_arguments(monkeypatch):
    config = provision._client_config(_profile(), "c" * 64, IMAGE_ID, 19090)
    session = FakeSession(
        FakeResponse({"choices": [{"message": {"content": "unused"}}]})
    )
    monkeypatch.setattr(client.requests, "Session", lambda: session)

    with pytest.raises(client.DockerLLMClientError, match="unknown fields"):
        client.DockerLLMClientTool(config).run(
            {"prompt": "test prompt", "endpoint": "http://example.com"}
        )

    assert session.health_request is None and session.request is None


def test_client_rejects_redirects_oversize_and_non_loopback(monkeypatch):
    profile_data = _profile()
    config = provision._client_config(profile_data, "c" * 64, IMAGE_ID, 19090)
    external = deepcopy(config)
    external["docker_llm"]["endpoint"] = "http://example.com/v1/chat/completions"
    with pytest.raises(client.DockerLLMClientError, match="loopback"):
        client.DockerLLMClientTool(external)

    for response, message in (
        (
            FakeResponse({"choices": [{"message": {"content": "x"}}]}, redirect=True),
            "redirect",
        ),
        (
            FakeResponse(
                {"choices": [{"message": {"content": "x"}}]}, size_header=1_000_001
            ),
            "1 MB",
        ),
    ):
        monkeypatch.setattr(client.requests, "Session", lambda: FakeSession(response))
        with pytest.raises(client.DockerLLMClientError, match=message):
            client.DockerLLMClientTool(config).run({"prompt": "test prompt"})


def test_tampered_client_record_is_not_loaded(tmp_path, approved_image):
    profile_data = _profile()
    config = provision._client_config(profile_data, "d" * 64, IMAGE_ID, 19090)
    record_body = {
        "version": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
        "profile_name": "reviewed-llm",
        "profile_sha256": "d" * 64,
        "image": IMAGE,
        "image_id": IMAGE_ID,
        "docker_server_version": "27.5.1",
        "docker_context": "default",
        "container_name": "tooluniverse-reviewed-llm",
        "host_port": 19090,
        "security": {"read_only_rootfs": True},
        "health": {
            "status": "ok",
            "service_id": "reviewed-llm-service",
            "model": "reviewed-model",
        },
        "tool_config": config,
    }
    record = {**record_body, "record_sha256": provision._canonical_digest(record_body)}
    path = tmp_path / "approved" / "ReviewedDockerEvidenceTool.json"
    path.parent.mkdir()
    path.write_text(json.dumps(record), encoding="utf-8")
    record["unexpected_change"] = True
    path.write_text(json.dumps(record), encoding="utf-8")
    tooluniverse = ToolUniverse()
    try:
        with pytest.raises(provision.DockerProvisionError, match="contract|digest"):
            provision.load_provisioned_tool(
                tooluniverse, "ReviewedDockerEvidenceTool", workspace=tmp_path
            )
        assert "ReviewedDockerEvidenceTool" not in tooluniverse.all_tool_dict
    finally:
        tooluniverse.close()
