"""Explicit local administration CLI for VSD demand aggregation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .execute_function import ToolUniverse
from .vsd_demand import (
    export_proposals,
    observe_capability_demand,
    rank_demands,
    record_plan_demands,
    remove_demand,
)


def _csv(value: str) -> list[str]:
    fields = [item.strip() for item in value.split(",") if item.strip()]
    if not fields:
        raise argparse.ArgumentTypeError("Provide at least one comma-separated field")
    return fields


def _json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise argparse.ArgumentTypeError(
            "Could not read the requested JSON file"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-demand",
        description=(
            "Record and rank private local VSD demand, then explicitly export "
            "selected sanitized proposals. Nothing is transmitted automatically."
        ),
    )
    parser.add_argument("--workspace", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    record = commands.add_parser("record")
    record.add_argument("--description", required=True)
    record.add_argument("--public-summary", required=True)
    record.add_argument("--provider")
    record.add_argument("--method", default="GET")
    record.add_argument("--endpoint")
    record.add_argument("--operation-id")
    record.add_argument("--required-inputs", type=_csv)
    record.add_argument("--output-fields", type=_csv)
    record.add_argument("--source", default="manual")
    record.add_argument("--event-id")
    record.add_argument("--limit", type=int, default=5)

    record_plan = commands.add_parser("record-plan")
    record_plan.add_argument("plan_file", type=Path)
    record_plan.add_argument("summaries_file", type=Path)
    record_plan.add_argument("--source", default="workflow_plan")
    record_plan.add_argument("--run-id")
    record_plan.add_argument(
        "--include",
        type=_csv,
        default=["missing", "existing_partial"],
        help="Comma-separated missing, existing_partial, or existing_exact values.",
    )

    rank = commands.add_parser("rank")
    rank.add_argument("--minimum-observations", type=int, default=1)
    rank.add_argument("--limit", type=int, default=100)
    rank.add_argument("--include-satisfied", action="store_true")

    export = commands.add_parser("export")
    export.add_argument("output_file", type=Path)
    export.add_argument("--demand-id", action="append", required=True)
    export.add_argument("--reviewed-by", required=True)
    export.add_argument("--decision-note", required=True)
    export.add_argument("--replace", action="store_true")

    remove = commands.add_parser("remove")
    remove.add_argument("demand_id")
    remove.add_argument("--confirm", action="store_true")
    return parser


def _request(namespace: argparse.Namespace) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "description": namespace.description,
            "provider": namespace.provider,
            "method": namespace.method,
            "endpoint": namespace.endpoint,
            "operation_id": namespace.operation_id,
            "required_inputs": namespace.required_inputs,
            "output_fields": namespace.output_fields,
        }.items()
        if value is not None
    }


def _execute(namespace: argparse.Namespace) -> dict[str, Any]:
    workspace = namespace.workspace
    if namespace.command == "record":
        tooluniverse = ToolUniverse()
        try:
            return observe_capability_demand(
                tooluniverse,
                _request(namespace),
                public_summary=namespace.public_summary,
                source=namespace.source,
                event_id=namespace.event_id,
                workspace=workspace,
                limit=namespace.limit,
            )
        finally:
            tooluniverse.close()
    if namespace.command == "rank":
        return rank_demands(
            workspace=workspace,
            minimum_observations=namespace.minimum_observations,
            limit=namespace.limit,
            include_satisfied=namespace.include_satisfied,
        )
    if namespace.command == "record-plan":
        plan = _json_file(namespace.plan_file)
        summaries = _json_file(namespace.summaries_file)
        if not isinstance(summaries, dict):
            raise argparse.ArgumentTypeError("summaries file must contain an object")
        return record_plan_demands(
            plan,
            summaries,
            workspace=workspace,
            source=namespace.source,
            run_id=namespace.run_id,
            include_classifications=tuple(namespace.include),
        )
    if namespace.command == "export":
        return {
            "status": "success",
            "data": export_proposals(
                namespace.demand_id,
                namespace.output_file,
                reviewed_by=namespace.reviewed_by,
                decision_note=namespace.decision_note,
                workspace=workspace,
                replace=namespace.replace,
            ),
        }
    if namespace.command == "remove":
        return remove_demand(
            namespace.demand_id,
            workspace=workspace,
            confirm=namespace.confirm,
        )
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
