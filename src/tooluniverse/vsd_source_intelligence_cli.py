"""Local administrator CLI for VSD source intelligence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .execute_function import ToolUniverse
from .vsd_source_intelligence import (
    VSDSourceIntelligenceError,
    assess_catalog_coverage,
    configured_source_inventory,
    crawl_source_candidates,
    load_trusted_source_catalog,
    prepare_core_handoff,
    render_core_issue,
    snapshot_source_candidate,
    submit_core_handoff,
    validate_core_handoff,
    validate_source_scan,
    write_core_handoff,
    write_scan_report,
    write_snapshot_manifest,
)


def _json_file(path: Path) -> Any:
    try:
        if path.stat().st_size > 4_000_000:
            raise VSDSourceIntelligenceError("JSON input exceeds 4 MB")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VSDSourceIntelligenceError("Could not read JSON input") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-sources",
        description=(
            "Inspect configured source coverage, run bounded local contract discovery, "
            "and explicitly prepare or submit sanitized review handoffs."
        ),
    )
    parser.add_argument("--catalog", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("catalog")
    commands.add_parser("inventory")
    commands.add_parser("coverage")

    scan = commands.add_parser("scan")
    scan.add_argument("--seed", action="append", required=True)
    scan.add_argument("--max-pages", type=int, default=20)
    scan.add_argument("--max-depth", type=int, default=2)
    scan.add_argument("--max-page-bytes", type=int, default=500_000)
    scan.add_argument("--max-total-bytes", type=int, default=5_000_000)
    scan.add_argument("--timeout", type=float, default=15)
    scan.add_argument("--report-directory", type=Path)
    scan.add_argument("--replace", action="store_true")

    snapshot = commands.add_parser("snapshot")
    snapshot.add_argument("scan_file", type=Path)
    snapshot.add_argument("candidate_id")
    snapshot.add_argument("directory", type=Path)
    snapshot.add_argument("--timeout", type=float, default=15)
    snapshot.add_argument("--max-bytes", type=int, default=1_000_000)
    snapshot.add_argument("--manifest-file", type=Path)
    snapshot.add_argument("--replace", action="store_true")

    handoff = commands.add_parser("handoff")
    handoff.add_argument("output_file", type=Path)
    handoff.add_argument("scan_file", type=Path, nargs="+")
    handoff.add_argument("--candidate-id", action="append", required=True)
    handoff.add_argument("--snapshot", action="append", type=Path, default=[])
    handoff.add_argument("--demand-export", type=Path)
    handoff.add_argument("--reviewed-by", required=True)
    handoff.add_argument("--decision-note", required=True)
    handoff.add_argument("--consent", action="store_true")
    handoff.add_argument("--replace", action="store_true")

    render = commands.add_parser("render")
    render.add_argument("handoff_file", type=Path)

    submit = commands.add_parser("submit")
    submit.add_argument("handoff_file", type=Path)
    submit.add_argument("--confirm", action="store_true")
    return parser


def _tool_context() -> ToolUniverse:
    return ToolUniverse()


def _execute(namespace: argparse.Namespace) -> dict[str, Any]:
    catalog = load_trusted_source_catalog(namespace.catalog)
    if namespace.command == "catalog":
        return catalog
    if namespace.command in {"inventory", "coverage", "scan"}:
        tooluniverse = _tool_context()
        try:
            inventory = configured_source_inventory(tooluniverse)
        finally:
            tooluniverse.close()
        if namespace.command == "inventory":
            return inventory
        if namespace.command == "coverage":
            return assess_catalog_coverage(catalog, inventory)
        report = crawl_source_candidates(
            namespace.seed,
            catalog=catalog,
            inventory=inventory,
            max_pages=namespace.max_pages,
            max_depth=namespace.max_depth,
            max_page_bytes=namespace.max_page_bytes,
            max_total_bytes=namespace.max_total_bytes,
            timeout_seconds=namespace.timeout,
        )
        if namespace.report_directory:
            output = write_scan_report(
                report, namespace.report_directory, replace=namespace.replace
            )
            return {**report, "report_file": str(output)}
        return report
    if namespace.command == "snapshot":
        scan = validate_source_scan(_json_file(namespace.scan_file))
        manifest = snapshot_source_candidate(
            scan,
            namespace.candidate_id,
            namespace.directory,
            timeout_seconds=namespace.timeout,
            max_bytes=namespace.max_bytes,
        )
        if namespace.manifest_file:
            output = write_snapshot_manifest(
                manifest, namespace.manifest_file, replace=namespace.replace
            )
            return {
                "status": "success",
                "data": manifest,
                "manifest_file": str(output),
            }
        return manifest
    if namespace.command == "handoff":
        scans = [validate_source_scan(_json_file(path)) for path in namespace.scan_file]
        snapshots = [_json_file(path) for path in namespace.snapshot]
        demand_export = (
            _json_file(namespace.demand_export) if namespace.demand_export else None
        )
        value = prepare_core_handoff(
            scans,
            namespace.candidate_id,
            reviewed_by=namespace.reviewed_by,
            decision_note=namespace.decision_note,
            consent=namespace.consent,
            demand_export=demand_export,
            snapshots=snapshots,
        )
        output = write_core_handoff(
            value, namespace.output_file, replace=namespace.replace
        )
        return {"status": "success", "data": value, "output_file": str(output)}
    if namespace.command == "render":
        title, body = render_core_issue(
            validate_core_handoff(_json_file(namespace.handoff_file))
        )
        return {"title": title, "body": body, "submitted": False}
    if namespace.command == "submit":
        return submit_core_handoff(
            validate_core_handoff(_json_file(namespace.handoff_file)),
            confirm=namespace.confirm,
        )
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
