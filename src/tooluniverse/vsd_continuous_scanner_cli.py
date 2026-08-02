"""Administrator CLI for scheduled VSD catalog scanning."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Sequence

from .execute_function import ToolUniverse
from .vsd_continuous_scanner import (
    load_latest_continuous_scan,
    run_scheduled_apis_guru_scan,
    run_scheduled_smartapi_scan,
    summarize_continuous_scan,
)


def _default_state_directory() -> Path:
    configured = os.environ.get("TOOLUNIVERSE_VSD_SCANNER_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".tooluniverse" / "vsd" / "scanner"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tooluniverse-vsd-scan",
        description=(
            "Run a bounded catalog cycle that produces local, inert VSD operation "
            "candidates for later administrator review."
        ),
    )
    parser.add_argument(
        "--state-directory", type=Path, default=_default_state_directory()
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument(
        "--catalog", choices=["apis-guru", "smartapi"], default="apis-guru"
    )
    run.add_argument("--max-contracts", type=int, default=100)
    run.add_argument("--draftable-tool-target", type=int, default=500)
    run.add_argument("--timeout", type=float, default=20)
    run.add_argument("--max-contract-bytes", type=int, default=1_000_000)

    commands.add_parser("status")
    return parser


def _execute(namespace: argparse.Namespace) -> dict[str, Any]:
    if namespace.command == "status":
        latest = load_latest_continuous_scan(namespace.state_directory)
        return {
            "status": "empty" if latest is None else "success",
            "state_directory": str(namespace.state_directory),
            "latest": summarize_continuous_scan(latest) if latest else None,
        }
    if namespace.command == "run":
        tooluniverse = ToolUniverse()
        try:
            runner = (
                run_scheduled_smartapi_scan
                if namespace.catalog == "smartapi"
                else run_scheduled_apis_guru_scan
            )
            result = runner(
                tooluniverse,
                namespace.state_directory,
                max_contracts=namespace.max_contracts,
                draftable_tool_target=namespace.draftable_tool_target,
                timeout_seconds=namespace.timeout,
                max_contract_bytes=namespace.max_contract_bytes,
            )
        finally:
            tooluniverse.close()
        return {
            "status": "success",
            "catalog": namespace.catalog,
            "state_directory": str(namespace.state_directory),
            "history_file": result["history_file"],
            "latest_file": result["latest_file"],
            "snapshot_directory": result["snapshot_directory"],
            "summary": summarize_continuous_scan(result["cycle"]),
        }
    raise AssertionError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    result = _execute(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
