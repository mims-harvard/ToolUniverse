"""Administrator CLI for local VSD drift assessments and lifecycle state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .vsd_lifecycle import (
    assess_openapi_drift,
    list_publication_states,
    set_publication_state,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-lifecycle",
        description=(
            "Assess local OpenAPI drift and explicitly control published VSD tools. "
            "These administrator operations are not agent-facing."
        ),
    )
    parser.add_argument("--workspace", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    assess = commands.add_parser("assess-openapi")
    assess.add_argument("tool_name")
    assess.add_argument("spec_file", type=Path)
    assess.add_argument("--server-index", type=int, default=0)

    status = commands.add_parser("status")
    status.add_argument("tool_name", nargs="?")

    for command in ("activate", "retire", "suspend"):
        transition = commands.add_parser(command)
        transition.add_argument("tool_name")
        transition.add_argument("--changed-by", required=True)
        transition.add_argument("--reason", required=True)
        transition.add_argument("--assessment-sha256")
    return parser


def _execute(namespace: argparse.Namespace) -> Any:
    workspace = namespace.workspace
    if namespace.command == "assess-openapi":
        return assess_openapi_drift(
            namespace.tool_name,
            namespace.spec_file,
            workspace=workspace,
            server_index=namespace.server_index,
        )
    if namespace.command == "status":
        return list_publication_states(namespace.tool_name, workspace=workspace)
    if namespace.command in {"activate", "retire", "suspend"}:
        state = (
            "active" if namespace.command == "activate" else namespace.command + "ed"
        )
        return set_publication_state(
            namespace.tool_name,
            state,
            changed_by=namespace.changed_by,
            reason=namespace.reason,
            assessment_sha256=namespace.assessment_sha256,
            workspace=workspace,
        )
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
