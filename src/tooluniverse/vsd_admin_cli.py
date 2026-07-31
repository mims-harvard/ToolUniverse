"""Explicit administration CLI for the mutable VSD source catalog."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from .vsd_tool import (
    VSDDiscoverSources,
    VSDListSources,
    VSDQuerySource,
    VSDRegisterSource,
    VSDRemoveSource,
)


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError("value must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-admin",
        description=(
            "Manage additional VSD JSON sources explicitly. These administrative "
            "operations are not loaded as agent-facing ToolUniverse tools."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    discover = commands.add_parser("discover", help="list packaged reviewed sources")
    discover.add_argument("--query", default="")

    register = commands.add_parser("register", help="probe and register a JSON source")
    register.add_argument("source_id")
    register.add_argument("endpoint")
    register.add_argument("--name")
    register.add_argument("--description")
    register.add_argument("--default-params", type=_json_object, default={})
    register.add_argument("--replace", action="store_true")

    commands.add_parser("list", help="list locally registered sources")

    query = commands.add_parser("query", help="query one locally registered source")
    query.add_argument("source_id")
    query.add_argument("--params", type=_json_object, default={})

    remove = commands.add_parser("remove", help="remove a locally registered source")
    remove.add_argument("source_id")
    return parser


def _execute(namespace: argparse.Namespace) -> dict[str, Any]:
    if namespace.command == "discover":
        return VSDDiscoverSources({}).run({"query": namespace.query})
    if namespace.command == "register":
        arguments = {
            "source_id": namespace.source_id,
            "endpoint": namespace.endpoint,
            "default_params": namespace.default_params,
            "replace": namespace.replace,
        }
        if namespace.name is not None:
            arguments["name"] = namespace.name
        if namespace.description is not None:
            arguments["description"] = namespace.description
        return VSDRegisterSource({}).run(arguments)
    if namespace.command == "list":
        return VSDListSources({}).run({})
    if namespace.command == "query":
        return VSDQuerySource({}).run(
            {"source_id": namespace.source_id, "params": namespace.params}
        )
    if namespace.command == "remove":
        return VSDRemoveSource({}).run({"source_id": namespace.source_id})
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
