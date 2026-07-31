from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

from tooluniverse.remote.docker_llm.provision import (
    ProvisionResult,
    provision_docker_llm,
)
from tooluniverse.compose_scripts.docker_llm_provisioner import compose


def test_provision_creates_remote_config_and_runs_docker():
    temp_home = Path(tempfile.mkdtemp())
    commands = []

    def fake_run(cmd, check, capture_output, text):
        commands.append(cmd)
        if cmd[0] == "docker" and cmd[1] == "version":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[0] == "docker" and cmd[1] == "ps":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if cmd[0] == "docker" and cmd[1] == "run":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        raise AssertionError(f"Unexpected docker command: {cmd}")

    response = mock.Mock()
    response.status_code = 200

    with mock.patch(
        "tooluniverse.remote.docker_llm.provision.Path.home", return_value=temp_home
    ):
        with mock.patch(
            "tooluniverse.remote.docker_llm.provision.subprocess.run",
            side_effect=fake_run,
        ):
            with mock.patch(
                "tooluniverse.remote.docker_llm.provision.requests.get",
                return_value=response,
            ):
                with mock.patch("tooluniverse.remote.docker_llm.provision.time.sleep"):
                    result = provision_docker_llm(
                        image="example/image:latest",
                        container_name="test-container",
                        host="127.0.0.1",
                        host_port=9100,
                        container_port=8000,
                        timeout_seconds=5,
                        poll_interval=0.01,
                    )

    assert result.container_name == "test-container"
    assert result.config_path.exists()
    stored = json.loads(result.config_path.read_text(encoding="utf-8"))
    assert isinstance(stored, list)
    assert stored[1]["name"] == "DockerLLMChat"
    assert [
        "docker",
        "run",
        "-d",
        "--name",
        "test-container",
        "-p",
        "127.0.0.1:9100:8000",
        "example/image:latest",
    ] in commands


def test_compose_returns_payload_and_refreshes_tooluniverse(tmp_path):
    config_path = tmp_path / "DockerLLMChat.json"

    def fake_provision(**kwargs):
        config_path.write_text("[]", encoding="utf-8")
        return ProvisionResult(
            container_name="compose-container",
            server_url="http://127.0.0.1:9000",
            config_path=config_path,
            tool_name="DockerLLMChat",
        )

    class DummyToolUniverse:
        def __init__(self):
            self.refreshed = False

        def load_tools(self):
            self.refreshed = True

    dummy_tu = DummyToolUniverse()

    with mock.patch(
        "tooluniverse.compose_scripts.docker_llm_provisioner.provision_docker_llm",
        side_effect=fake_provision,
    ):
        result = compose({"host_port": 9005}, dummy_tu, call_tool=None)

    assert result["ok"] is True
    assert result["container_name"] == "compose-container"
    assert dummy_tu.refreshed is True
