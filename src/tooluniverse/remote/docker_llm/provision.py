"""
Docker-hosted LLM provisioning helpers for ToolUniverse.

These helpers start (or reuse) a Docker container that exposes an MCP-compatible
LLM service, wait for it to become healthy, and register client/auto-loader
configurations in the user's ToolUniverse remote tool directory.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import requests

DEFAULT_IMAGE = "ghcr.io/tooluniverse/docker-llm-mcp:latest"
DEFAULT_CONTAINER_BASENAME = "tooluniverse-llm"
DEFAULT_INTERNAL_PORT = 8000
DEFAULT_TOOL_NAME = "DockerLLMChat"
DEFAULT_MCP_TOOL_NAME = "docker_llm_chat"
DEFAULT_HEALTH_PATH = "/health"


class ProvisionError(RuntimeError):
    """Raised when Docker provisioning fails."""


@dataclass
class ProvisionResult:
    container_name: str
    server_url: str
    config_path: Path
    tool_name: str


def _ensure_remote_dir() -> Path:
    target = Path.home() / ".tooluniverse" / "remote_tools"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _run_docker(
    args: Sequence[str], *, docker_cli: str = "docker", check: bool = True
) -> subprocess.CompletedProcess:
    command = [docker_cli, *args]
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
    )


def _container_exists(container_name: str, docker_cli: str) -> bool:
    proc = _run_docker(
        ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        docker_cli=docker_cli,
        check=True,
    )
    return any(line.strip() == container_name for line in proc.stdout.splitlines())


def _container_running(container_name: str, docker_cli: str) -> bool:
    proc = _run_docker(
        ["ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        docker_cli=docker_cli,
        check=True,
    )
    return any(line.strip() == container_name for line in proc.stdout.splitlines())


def _start_existing(container_name: str, docker_cli: str) -> None:
    _run_docker(["start", container_name], docker_cli=docker_cli, check=True)


def _run_new_container(
    *,
    docker_cli: str,
    image: str,
    container_name: str,
    host: str,
    host_port: int,
    container_port: int,
    env: Optional[Dict[str, str]],
    volumes: Optional[List[str]],
    extra_args: Optional[List[str]],
) -> None:
    cmd: List[str] = [
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{host}:{host_port}:{container_port}",
    ]

    for key, value in (env or {}).items():
        cmd.extend(["-e", f"{key}={value}"])

    for volume in volumes or []:
        cmd.extend(["-v", volume])

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(image)
    _run_docker(cmd, docker_cli=docker_cli, check=True)


def _wait_for_health(
    url: str,
    *,
    timeout: int,
    interval: float,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=5)
            if 200 <= response.status_code < 400:
                return
        except requests.RequestException:
            pass
        time.sleep(interval)
    raise ProvisionError(f"Container health check did not succeed at {url}")


def _write_remote_config(config: List[Dict[str, object]], *, tool_name: str) -> Path:
    target_dir = _ensure_remote_dir()
    path = target_dir / f"{tool_name}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
    return path


def provision_docker_llm(
    image: str = DEFAULT_IMAGE,
    *,
    container_name: Optional[str] = None,
    docker_cli: str = "docker",
    host: str = "127.0.0.1",
    host_port: int = 9000,
    container_port: int = DEFAULT_INTERNAL_PORT,
    env: Optional[Dict[str, str]] = None,
    volumes: Optional[List[str]] = None,
    extra_args: Optional[List[str]] = None,
    tool_name: str = DEFAULT_TOOL_NAME,
    tool_prefix: Optional[str] = None,
    mcp_tool_name: str = DEFAULT_MCP_TOOL_NAME,
    health_path: str = DEFAULT_HEALTH_PATH,
    timeout_seconds: int = 120,
    poll_interval: float = 2.0,
    reuse_container: bool = True,
    server_url: Optional[str] = None,
    description: Optional[str] = None,
) -> ProvisionResult:
    """
    Ensure a Docker-hosted LLM is running and registered with ToolUniverse.
    """
    container_name = (
        container_name or f"{DEFAULT_CONTAINER_BASENAME}-{int(time.time())}"
    )
    tool_prefix = tool_prefix or (tool_name.lower() + "_")
    if not tool_prefix.endswith("_"):
        tool_prefix += "_"

    # Verify Docker availability
    try:
        _run_docker(["version"], docker_cli=docker_cli, check=True)
    except FileNotFoundError as exc:
        raise ProvisionError(
            "Docker CLI not found. Please install Docker Desktop."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise ProvisionError(f"Docker is not available: {exc.stderr.strip()}") from exc

    exists = _container_exists(container_name, docker_cli)
    running = _container_running(container_name, docker_cli) if exists else False

    if exists and not running and reuse_container:
        _start_existing(container_name, docker_cli)
        running = True

    if not exists or (exists and not running and not reuse_container):
        if exists and not reuse_container:
            _run_docker(["rm", "-f", container_name], docker_cli=docker_cli, check=True)
        _run_new_container(
            docker_cli=docker_cli,
            image=image,
            container_name=container_name,
            host=host,
            host_port=host_port,
            container_port=container_port,
            env=env,
            volumes=volumes,
            extra_args=extra_args,
        )

    base_url = server_url or f"http://{host}:{host_port}"
    health_url = base_url.rstrip("/") + health_path
    _wait_for_health(health_url, timeout=timeout_seconds, interval=poll_interval)

    config_description = (
        description
        or "Interact with a locally hosted Docker LLM via MCP-compatible interface."
    )

    remote_config = [
        {
            "name": f"{tool_prefix.rstrip('_')}_auto_loader",
            "description": f"Automatically discover tools from the Docker-hosted LLM server at {base_url}.",
            "type": "MCPAutoLoaderTool",
            "server_url": f"{base_url.rstrip('/')}/mcp",
            "tool_prefix": tool_prefix,
        },
        {
            "name": tool_name,
            "description": config_description,
            "type": "MCPClientTool",
            "server_url": base_url,
            "transport": "http",
            "mcp_tool_name": mcp_tool_name,
            "parameter": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Prompt text to send to the Docker-hosted language model.",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature for the model.",
                        "default": 0.7,
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens to generate in the response.",
                        "default": 512,
                    },
                },
                "required": ["prompt"],
                "additionalProperties": True,
            },
        },
    ]

    config_path = _write_remote_config(remote_config, tool_name=tool_name)

    return ProvisionResult(
        container_name=container_name,
        server_url=base_url.rstrip("/"),
        config_path=config_path,
        tool_name=tool_name,
    )
