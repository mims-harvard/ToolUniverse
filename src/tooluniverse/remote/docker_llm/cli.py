"""Administrator CLI for reviewed Docker LLM lifecycle operations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .provision import (
    DockerProvisionError,
    plan_container,
    provision_container,
    remove_container,
    status_container,
    stop_container,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-docker-llm-admin",
        description=(
            "Manage one reviewed, allowlisted Docker LLM profile. "
            "This lifecycle interface is not a ToolUniverse agent tool."
        ),
    )
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--host-port", type=int, default=9000)
    parser.add_argument("--container-name")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan")
    commands.add_parser("start")
    commands.add_parser("status")
    commands.add_parser("stop")
    remove = commands.add_parser("remove")
    remove.add_argument("--yes", action="store_true")
    return parser


def _execute(namespace: argparse.Namespace):
    common = {
        "host_port": namespace.host_port,
        "container_name": namespace.container_name,
    }
    if namespace.command == "plan":
        return plan_container(namespace.profile, **common)
    if namespace.command == "start":
        return provision_container(
            namespace.profile, workspace=namespace.workspace, **common
        )
    if namespace.command == "status":
        return status_container(namespace.profile, **common)
    if namespace.command == "stop":
        return stop_container(namespace.profile, **common)
    if namespace.command == "remove":
        return remove_container(
            namespace.profile,
            workspace=namespace.workspace,
            confirm=namespace.yes,
            **common,
        )
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        result = _execute(build_parser().parse_args(argv))
    except DockerProvisionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps({"ok": True, "result": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
