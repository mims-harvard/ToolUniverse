"""
Compose script that provisions a Docker-hosted LLM and refreshes ToolUniverse.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..remote.docker_llm.provision import ProvisionError, provision_docker_llm


def compose(
    arguments: Dict[str, Any],
    tooluniverse,
    call_tool,
    stream_callback=None,
    emit_event=None,
    memory_manager=None,
) -> Dict[str, Any]:
    """Provision a Docker LLM container and register MCP configs."""

    args = dict(arguments or {})

    try:
        result = provision_docker_llm(
            image=args.get("docker_image"),
            container_name=args.get("container_name"),
            docker_cli=args.get("docker_cli", "docker"),
            host=args.get("host", "127.0.0.1"),
            host_port=int(args.get("host_port", 9000)),
            container_port=int(args.get("container_port", 8000)),
            env=args.get("env"),
            volumes=args.get("volumes"),
            extra_args=args.get("extra_args"),
            tool_name=args.get("tool_name", "DockerLLMChat"),
            tool_prefix=args.get("tool_prefix"),
            mcp_tool_name=args.get("mcp_tool_name", "docker_llm_chat"),
            health_path=args.get("health_path", "/health"),
            timeout_seconds=int(args.get("timeout_seconds", 120)),
            poll_interval=float(args.get("poll_interval", 2.0)),
            reuse_container=bool(args.get("reuse_container", True)),
            server_url=args.get("server_url"),
            description=args.get("description"),
        )
    except ProvisionError as exc:
        return {"ok": False, "error": str(exc)}

    load_error: Optional[str] = None
    if tooluniverse is not None:
        try:
            # Reload tool registry so the new MCP configs are visible immediately.
            tooluniverse.load_tools()
        except Exception as exc:  # pragma: no cover - defensive
            load_error = str(exc)

    payload = {
        "ok": True,
        "container_name": result.container_name,
        "server_url": result.server_url,
        "config_path": str(result.config_path),
        "tool_name": result.tool_name,
    }
    if load_error:
        payload["load_warning"] = load_error

    return payload


__all__ = ["compose"]
