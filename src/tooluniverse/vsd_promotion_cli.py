"""Explicit administration CLI for the VSD tool-promotion pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .vsd_openapi import inspect_openapi_document, select_openapi_candidate
from .vsd_promotion import (
    approve_draft,
    create_draft,
    create_openapi_draft,
    list_promotion_state,
    publish_draft,
    verify_draft,
)


def _json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise argparse.ArgumentTypeError(f"Could not read JSON from {path}") from exc


def _csv(value: str) -> list[str]:
    fields = [item.strip() for item in value.split(",") if item.strip()]
    if not fields:
        raise argparse.ArgumentTypeError("Provide at least one comma-separated field")
    return fields


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-promote",
        description=(
            "Generate, verify, approve, and publish read-only VSD tools. "
            "These administrator operations are not agent-facing."
        ),
    )
    parser.add_argument("--workspace", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    draft = commands.add_parser("draft-socrata")
    draft.add_argument("candidate_file", type=Path)
    draft.add_argument("--tool-name", required=True)
    draft.add_argument("--description", required=True)
    draft.add_argument("--filter-fields", required=True, type=_csv)
    draft.add_argument("--return-fields", required=True, type=_csv)
    draft.add_argument("--max-records", type=int, default=25)

    inspect_openapi = commands.add_parser("inspect-openapi")
    inspect_openapi.add_argument("spec_file", type=Path)
    inspect_openapi.add_argument("--server-index", type=int, default=0)

    draft_openapi = commands.add_parser("draft-openapi")
    draft_openapi.add_argument("candidate_file", type=Path)
    draft_openapi.add_argument("--candidate-id")
    draft_openapi.add_argument("--tool-name", required=True)
    draft_openapi.add_argument("--description", required=True)
    draft_openapi.add_argument("--include-parameters", type=_csv)
    draft_openapi.add_argument("--fixed-query-file", type=Path)
    draft_openapi.add_argument("--timeout-seconds", type=float, default=20)
    draft_openapi.add_argument("--credential-env")

    verify = commands.add_parser("verify")
    verify.add_argument("draft_id")
    verify.add_argument("cases_file", type=Path)

    approve = commands.add_parser("approve")
    approve.add_argument("draft_id")
    approve.add_argument("--reviewed-by", required=True)
    approve.add_argument("--decision-note", required=True)

    publish = commands.add_parser("publish")
    publish.add_argument("draft_id")
    publish.add_argument("--replace", action="store_true")

    commands.add_parser("list")
    return parser


def _execute(namespace: argparse.Namespace) -> Any:
    workspace = namespace.workspace
    if namespace.command == "draft-socrata":
        candidate = _json_file(namespace.candidate_file)
        if isinstance(candidate, dict) and "selected_candidate" in candidate:
            candidate = candidate["selected_candidate"]
        elif (
            isinstance(candidate, dict)
            and isinstance(candidate.get("analysis"), dict)
            and "selected_candidate" in candidate["analysis"]
        ):
            candidate = candidate["analysis"]["selected_candidate"]
        return create_draft(
            candidate,
            tool_name=namespace.tool_name,
            description=namespace.description,
            filter_fields=namespace.filter_fields,
            return_fields=namespace.return_fields,
            max_records=namespace.max_records,
            workspace=workspace,
        )
    if namespace.command == "inspect-openapi":
        return inspect_openapi_document(
            namespace.spec_file, server_index=namespace.server_index
        )
    if namespace.command == "draft-openapi":
        report = _json_file(namespace.candidate_file)
        candidate = select_openapi_candidate(report, namespace.candidate_id)
        fixed_query = (
            _json_file(namespace.fixed_query_file)
            if namespace.fixed_query_file is not None
            else None
        )
        if fixed_query is not None and not isinstance(fixed_query, dict):
            raise argparse.ArgumentTypeError("fixed query file must contain an object")
        return create_openapi_draft(
            candidate,
            tool_name=namespace.tool_name,
            description=namespace.description,
            include_parameters=namespace.include_parameters,
            fixed_query=fixed_query,
            timeout_seconds=namespace.timeout_seconds,
            credential_env=namespace.credential_env,
            workspace=workspace,
        )
    if namespace.command == "verify":
        return verify_draft(
            namespace.draft_id,
            _json_file(namespace.cases_file),
            workspace=workspace,
        )
    if namespace.command == "approve":
        return approve_draft(
            namespace.draft_id,
            reviewed_by=namespace.reviewed_by,
            decision_note=namespace.decision_note,
            workspace=workspace,
        )
    if namespace.command == "publish":
        return publish_draft(
            namespace.draft_id,
            replace=namespace.replace,
            workspace=workspace,
        )
    if namespace.command == "list":
        return list_promotion_state(workspace=workspace)
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
