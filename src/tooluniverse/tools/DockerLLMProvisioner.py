"""
DockerLLMProvisioner

Compose wrapper that provisions a Docker-hosted LLM MCP server and registers
its ToolUniverse configurations.
"""

from typing import Any, Dict, Optional, Callable
from ._shared_client import get_shared_client


def DockerLLMProvisioner(
    *,
    docker_image: Optional[str] = None,
    container_name: Optional[str] = None,
    docker_cli: str = "docker",
    host: str = "127.0.0.1",
    host_port: int = 9000,
    container_port: int = 8000,
    env: Optional[Dict[str, str]] = None,
    volumes: Optional[list[str]] = None,
    extra_args: Optional[list[str]] = None,
    tool_name: str = "DockerLLMChat",
    tool_prefix: Optional[str] = None,
    mcp_tool_name: str = "docker_llm_chat",
    health_path: str = "/health",
    timeout_seconds: int = 120,
    poll_interval: float = 2.0,
    reuse_container: bool = True,
    server_url: Optional[str] = None,
    description: Optional[str] = None,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Provision a Docker-hosted LLM and register MCP configs with ToolUniverse.
    """

    arguments: Dict[str, Any] = {
        "docker_image": docker_image,
        "container_name": container_name,
        "docker_cli": docker_cli,
        "host": host,
        "host_port": host_port,
        "container_port": container_port,
        "env": env,
        "volumes": volumes,
        "extra_args": extra_args,
        "tool_name": tool_name,
        "tool_prefix": tool_prefix,
        "mcp_tool_name": mcp_tool_name,
        "health_path": health_path,
        "timeout_seconds": timeout_seconds,
        "poll_interval": poll_interval,
        "reuse_container": reuse_container,
        "server_url": server_url,
        "description": description,
    }

    return get_shared_client().run_one_function(
        {"name": "DockerLLMProvisioner", "arguments": arguments},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DockerLLMProvisioner"]
