#!/usr/bin/env python3
"""
Provision a Docker-hosted LLM and register it with ToolUniverse.

This script wraps the helper in tooluniverse.remote.docker_llm.provision so that
non-technical users can start the container and create the necessary MCP client
configurations with a single command.
"""

from __future__ import annotations

import argparse
import sys

from tooluniverse.remote.docker_llm.provision import (
    DEFAULT_IMAGE,
    ProvisionError,
    provision_docker_llm,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Start a Docker-hosted LLM and register it with ToolUniverse."
    )
    parser.add_argument(
        "--image",
        default=DEFAULT_IMAGE,
        help=f"Docker image to run (default: {DEFAULT_IMAGE})",
    )
    parser.add_argument(
        "--container-name",
        help="Name for the Docker container. Generated automatically if omitted.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--host-port",
        type=int,
        default=9000,
        help="Host port to expose the MCP endpoint on (default: 9000).",
    )
    parser.add_argument(
        "--container-port",
        type=int,
        default=8000,
        help="Internal container port (default: 8000).",
    )
    parser.add_argument(
        "--tool-name",
        default="DockerLLMChat",
        help="Tool name to register inside ToolUniverse.",
    )
    parser.add_argument(
        "--tool-prefix",
        help="Prefix used when auto-registering tools from the MCP server.",
    )
    parser.add_argument(
        "--mcp-tool-name",
        default="docker_llm_chat",
        help="Underlying MCP tool name exposed by the container.",
    )
    parser.add_argument(
        "--health-path",
        default="/health",
        help="HTTP path used for readiness checks (default: /health).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Seconds to wait for container health (default: 120).",
    )
    parser.add_argument(
        "--no-reuse",
        action="store_true",
        help="Always recreate the container instead of reusing an existing one.",
    )
    parser.add_argument(
        "--docker-cli",
        default="docker",
        help="Docker CLI executable to invoke (default: docker).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = provision_docker_llm(
            image=args.image,
            container_name=args.container_name,
            docker_cli=args.docker_cli,
            host=args.host,
            host_port=args.host_port,
            container_port=args.container_port,
            tool_name=args.tool_name,
            tool_prefix=args.tool_prefix,
            mcp_tool_name=args.mcp_tool_name,
            health_path=args.health_path,
            timeout_seconds=args.timeout,
            reuse_container=not args.no_reuse,
        )
    except ProvisionError as exc:
        print(f"Provisioning failed: {exc}", file=sys.stderr)
        return 1

    print("Docker LLM provisioning complete.")
    print(f"  Container name : {result.container_name}")
    print(f"  MCP server URL : {result.server_url}")
    print(f"  Tool config    : {result.config_path}")
    print(
        "Add the tool by reloading ToolUniverse or invoking "
        "'DockerLLMProvisioner' from within the agent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
