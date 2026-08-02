"""Exhaustive live evaluation across continuous VSD catalog adapters."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence

from tooluniverse.execute_function import ToolUniverse
from tooluniverse.vsd_continuous_scanner import (
    load_latest_continuous_scan,
    run_scheduled_apis_guru_scan,
    run_scheduled_smartapi_scan,
    validate_continuous_scan_cycle,
)

HERE = Path(__file__).resolve().parent
ARTIFACT_DIRECTORY = HERE / "artifacts"
JSON_ARTIFACT = ARTIFACT_DIRECTORY / "continuous_catalog_expansion_study.json"
MARKDOWN_ARTIFACT = ARTIFACT_DIRECTORY / "continuous_catalog_expansion_study.md"
CATALOG_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "apis_guru": run_scheduled_apis_guru_scan,
    "smartapi": run_scheduled_smartapi_scan,
}
SCIENTIFIC_TERMS = frozenset(
    {
        "bio",
        "cancer",
        "cell",
        "chemical",
        "clinical",
        "disease",
        "drug",
        "gene",
        "genome",
        "genomic",
        "health",
        "medical",
        "molecular",
        "ontology",
        "phenotype",
        "protein",
        "trial",
        "variant",
    }
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _history(state_directory: Path) -> list[dict[str, Any]]:
    cycles: dict[str, dict[str, Any]] = {}
    for path in state_directory.glob("cycle-*.json"):
        cycle = validate_continuous_scan_cycle(
            json.loads(path.read_text(encoding="utf-8"))
        )
        cycles[cycle["cycle_id"]] = cycle
    if not cycles:
        return []
    children: dict[str | None, list[str]] = {}
    for cycle in cycles.values():
        children.setdefault(cycle["previous_cycle_id"], []).append(cycle["cycle_id"])
    roots = children.get(None, [])
    if len(roots) != 1:
        raise ValueError("Catalog history must contain one hash-linked root")
    ordered: list[dict[str, Any]] = []
    cycle_id: str | None = roots[0]
    while cycle_id is not None:
        cycle = cycles[cycle_id]
        ordered.append(cycle)
        next_ids = children.get(cycle_id, [])
        if len(next_ids) > 1:
            raise ValueError("Catalog history contains a fork")
        cycle_id = next_ids[0] if next_ids else None
    if len(ordered) != len(cycles):
        raise ValueError("Catalog history contains an unlinked cycle")
    return ordered


def _is_complete(cycle: dict[str, Any] | None) -> bool:
    if cycle is None:
        return False
    return (
        len(cycle["state"]["inspected_record_ids"])
        >= cycle["directory"]["compatible_record_count"]
    )


def _discard_contract_snapshots(state_directory: Path) -> tuple[int, int]:
    root = state_directory.resolve()
    snapshot_directory = (root / "contracts").resolve()
    if snapshot_directory.parent != root or not snapshot_directory.exists():
        return 0, 0
    removed = 0
    removed_bytes = 0
    for path in snapshot_directory.glob("*.openapi.json"):
        if not path.is_file() or path.is_symlink():
            continue
        removed_bytes += path.stat().st_size
        path.unlink()
        removed += 1
    return removed, removed_bytes


def run_catalog_to_completion(
    tooluniverse: ToolUniverse,
    catalog_id: str,
    state_directory: Path,
    *,
    max_contracts: int,
    draftable_tool_target: int,
    timeout_seconds: float,
    max_cycles: int,
) -> list[dict[str, Any]]:
    runner = CATALOG_RUNNERS[catalog_id]
    state_directory.mkdir(parents=True, exist_ok=True)
    _discard_contract_snapshots(state_directory)
    latest = load_latest_continuous_scan(state_directory)
    completed_cycles = 0
    while not _is_complete(latest):
        if completed_cycles >= max_cycles:
            raise RuntimeError(
                f"{catalog_id} did not complete within {max_cycles} cycles"
            )
        result = runner(
            tooluniverse,
            state_directory,
            max_contracts=max_contracts,
            draftable_tool_target=draftable_tool_target,
            timeout_seconds=timeout_seconds,
        )
        latest = result["cycle"]
        removed_snapshots, removed_bytes = _discard_contract_snapshots(state_directory)
        completed_cycles += 1
        print(
            json.dumps(
                {
                    "catalog": catalog_id,
                    "cycle_id": latest["cycle_id"],
                    "processed": len(latest["state"]["inspected_record_ids"]),
                    "compatible": latest["directory"]["compatible_record_count"],
                    "contracts": latest["metrics"]["inspected_contract_count"],
                    "operations": latest["metrics"]["operation_candidate_count"],
                    "draft_ready": latest["metrics"]["draftable_tool_count"],
                    "failures": latest["metrics"]["failed_contract_count"],
                    "discarded_snapshot_count": removed_snapshots,
                    "discarded_snapshot_bytes": removed_bytes,
                },
                sort_keys=True,
            ),
            flush=True,
        )
    return _history(state_directory)


def _scientific_score(record: dict[str, Any], operation: dict[str, Any]) -> int:
    text = " ".join(
        [
            record.get("title", ""),
            record.get("provider_name", ""),
            " ".join(record.get("categories", [])),
            operation.get("api_title", ""),
            operation.get("operation_id", ""),
            operation.get("path", ""),
        ]
    ).casefold()
    return sum(term in text for term in SCIENTIFIC_TERMS)


def build_portfolio(catalog_cycles: dict[str, Sequence[Any]]) -> dict[str, Any]:
    checked = {
        catalog_id: [validate_continuous_scan_cycle(item) for item in cycles]
        for catalog_id, cycles in catalog_cycles.items()
    }
    if set(checked) != set(CATALOG_RUNNERS) or any(
        not value for value in checked.values()
    ):
        raise ValueError(
            "Expansion study requires complete evidence from both catalogs"
        )

    all_operations: list[dict[str, Any]] = []
    all_contracts: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []
    config_hashes: set[str] = set()
    operation_hashes: set[str] = set()
    contract_hashes: set[str] = set()
    hosts: set[str] = set()
    blockers: Counter[str] = Counter()
    scientific_candidates: list[tuple[int, dict[str, Any]]] = []
    catalog_summaries: list[dict[str, Any]] = []

    for catalog_id in sorted(checked):
        cycles = checked[catalog_id]
        latest = cycles[-1]
        records = {item["record_id"]: item for item in latest["directory"]["records"]}
        operations = [item for cycle in cycles for item in cycle["operations"]]
        contracts = [item for cycle in cycles for item in cycle["contracts"]]
        failures = [item for cycle in cycles for item in cycle["failures"]]
        blockers.update(
            blocker
            for operation in operations
            for blocker in operation.get("blockers", [])
        )
        catalog_config_hashes = {
            operation["preview"]["config_sha256"]
            for operation in operations
            if operation.get("preview")
        }
        catalog_operation_hashes = {
            operation["candidate_sha256"]
            for operation in operations
            if len(operation.get("candidate_sha256", "")) == 64
        }
        catalog_contract_hashes = {contract["content_sha256"] for contract in contracts}
        for operation in operations:
            preview = operation.get("preview")
            if preview:
                config_hashes.add(preview["config_sha256"])
                if operation.get("host"):
                    hosts.add(operation["host"])
                record = records.get(operation["record_id"], {})
                score = _scientific_score(record, operation)
                if score:
                    scientific_candidates.append(
                        (
                            score,
                            {
                                "catalog_id": catalog_id,
                                "record_id": operation["record_id"],
                                "title": operation["api_title"],
                                "categories": record.get("categories", []),
                                "specification_url": record.get(
                                    "specification_url", ""
                                ),
                                "content_sha256": operation["content_sha256"],
                                "candidate_id": operation["candidate_id"],
                                "candidate_sha256": operation["candidate_sha256"],
                                "operation_id": operation["operation_id"],
                                "method": operation["method"],
                                "host": operation["host"],
                                "path": operation["path"],
                                "registry_coverage": operation["registry_coverage"],
                                "existing_tools": operation["existing_tools"],
                                "preview_tool_name": preview["tool_name"],
                                "preview_config_sha256": preview["config_sha256"],
                                "scientific_term_matches": score,
                                "approval_state": operation["approval_state"],
                                "execution_allowed": operation["execution_allowed"],
                            },
                        )
                    )
        operation_hashes.update(catalog_operation_hashes)
        contract_hashes.update(catalog_contract_hashes)
        all_operations.extend(operations)
        all_contracts.extend(contracts)
        all_failures.extend(failures)
        summaries = [
            {
                "cycle_id": cycle["cycle_id"],
                "previous_cycle_id": cycle["previous_cycle_id"],
                "scanned_at": cycle["scanned_at"],
                "attempted_record_count": len(cycle["attempted_record_ids"]),
                "processed_record_count": len(cycle["state"]["inspected_record_ids"]),
                "metrics": cycle["metrics"],
            }
            for cycle in cycles
        ]
        attempted_record_count = sum(
            len(cycle["attempted_record_ids"]) for cycle in cycles
        )
        processed_record_count = len(latest["state"]["inspected_record_ids"])
        catalog_summaries.append(
            {
                "catalog_id": catalog_id,
                "catalog_endpoint": latest["directory"]["catalog_endpoint"],
                "catalog_record_count": latest["directory"]["record_count"],
                "compatible_record_count": latest["directory"][
                    "compatible_record_count"
                ],
                "unsupported_record_count": latest["directory"][
                    "unsupported_record_count"
                ],
                "attempted_record_count": attempted_record_count,
                "processed_record_count": processed_record_count,
                "redundant_attempt_count": attempted_record_count
                - processed_record_count,
                "cycle_count": len(cycles),
                "successful_contract_count": len(contracts),
                "failed_contract_count": len(failures),
                "unique_contract_count": len(catalog_contract_hashes),
                "unique_operation_count": len(catalog_operation_hashes),
                "unique_draft_ready_count": len(catalog_config_hashes),
                "cycles": summaries,
            }
        )

    unique_scientific: dict[str, tuple[int, dict[str, Any]]] = {}
    for score, candidate in scientific_candidates:
        key = candidate["preview_config_sha256"]
        existing = unique_scientific.get(key)
        if existing is None or score > existing[0]:
            unique_scientific[key] = (score, candidate)
    scientific_inventory = [
        candidate
        for _, candidate in sorted(
            unique_scientific.values(),
            key=lambda item: (
                -item[0],
                item[1]["title"].casefold(),
                item[1]["operation_id"].casefold(),
                item[1]["preview_config_sha256"],
            ),
        )
    ]
    combined = {
        "catalog_count": len(catalog_summaries),
        "catalog_record_count": sum(
            item["catalog_record_count"] for item in catalog_summaries
        ),
        "compatible_record_count": sum(
            item["compatible_record_count"] for item in catalog_summaries
        ),
        "processed_record_count": sum(
            item["processed_record_count"] for item in catalog_summaries
        ),
        "attempted_record_count": sum(
            item["attempted_record_count"] for item in catalog_summaries
        ),
        "redundant_attempt_count": sum(
            item["redundant_attempt_count"] for item in catalog_summaries
        ),
        "cycle_count": sum(item["cycle_count"] for item in catalog_summaries),
        "successful_contract_attempt_count": len(all_contracts),
        "failed_contract_count": len(all_failures),
        "unique_contract_count": len(contract_hashes),
        "cross_catalog_or_cycle_contract_duplicates": len(all_contracts)
        - len(contract_hashes),
        "unique_operation_count": len(operation_hashes),
        "unique_draft_ready_count": len(config_hashes),
        "draft_ready_host_count": len(hosts),
        "blocked_operation_count": sum(
            bool(operation.get("blockers")) for operation in all_operations
        ),
        "scientific_draft_ready_count": len(unique_scientific),
        "contract_set_sha256": _digest(sorted(contract_hashes)),
        "operation_set_sha256": _digest(sorted(operation_hashes)),
        "draft_ready_set_sha256": _digest(sorted(config_hashes)),
        "blocker_counts": dict(
            sorted(blockers.items(), key=lambda item: (-item[1], item[0]))
        ),
    }
    assertions = {
        "both_catalogs_completed": all(
            item["processed_record_count"] == item["compatible_record_count"]
            for item in catalog_summaries
        ),
        "more_than_seventeen_hundred_contract_records_were_eligible": combined[
            "compatible_record_count"
        ]
        >= 1_700,
        "at_least_ten_thousand_unique_operations_were_inventoried": combined[
            "unique_operation_count"
        ]
        >= 10_000,
        "at_least_two_thousand_unique_candidates_were_draft_ready": combined[
            "unique_draft_ready_count"
        ]
        >= 2_000,
        "scientific_candidates_were_found_without_provider_specific_scanner_logic": combined[
            "scientific_draft_ready_count"
        ]
        >= 20,
        "failures_were_isolated": combined["failed_contract_count"]
        < combined["processed_record_count"],
        "every_attempt_has_a_contract_or_failure_record": combined[
            "attempted_record_count"
        ]
        == combined["successful_contract_attempt_count"]
        + combined["failed_contract_count"],
        "all_candidate_summaries_remained_inert": all(
            operation["approval_state"] == "unreviewed_operation_candidate"
            and operation["execution_allowed"] is False
            for operation in all_operations
        ),
        "no_cycle_enabled_execution_or_publication": all(
            cycle["execution_allowed"] is False
            and cycle["automatic_publication"] is False
            for cycles in checked.values()
            for cycle in cycles
        ),
        "catalog_histories_are_hash_linked": all(
            current["previous_cycle_id"] == previous["cycle_id"]
            for cycles in checked.values()
            for previous, current in zip(cycles, cycles[1:])
        ),
    }
    latest_registry = next(iter(checked.values()))[-1]["registry"]
    body = {
        "format": "vsd_continuous_catalog_expansion_study_v1",
        "version": 1,
        "evaluation_mode": "live_network",
        "generated_at": max(cycles[-1]["scanned_at"] for cycles in checked.values()),
        "objective": (
            "Measure exhaustive candidate generation across a general OpenAPI "
            "directory and a biomedical API registry while preserving VSD's inert "
            "review boundary and exact ToolUniverse registry audit."
        ),
        "method": (
            "Each catalog was scanned through linked, bounded cycles until every "
            "compatible record had been attempted. Contracts, operations, and draft "
            "configuration hashes were deduplicated before aggregation. Scientific "
            "samples were selected only by generic vocabulary matching over catalog "
            "metadata; scanner logic contains no provider-specific scientific cases. "
            "The recorded run also preserves redundant attempts from partially filled "
            "final cycles so execution efficiency can be audited separately from "
            "deduplicated scientific results."
        ),
        "real_registry": latest_registry,
        "catalogs": catalog_summaries,
        "combined_results": combined,
        "scientific_candidate_inventory": scientific_inventory,
        "scientific_candidate_samples": scientific_inventory[:100],
        "assertions": assertions,
        "boundary": (
            "The exhaustive scanner fetched catalog pages and contract documents but "
            "did not call provider operations. Draft-ready candidates remain unverified, "
            "unapproved, unpublished, unloaded, and non-executable."
        ),
    }
    return {**body, "portfolio_sha256": _digest(body)}


def validate_portfolio(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format") != (
        "vsd_continuous_catalog_expansion_study_v1"
    ):
        raise ValueError("Continuous catalog expansion artifact is invalid")
    body = {key: item for key, item in value.items() if key != "portfolio_sha256"}
    if value.get("portfolio_sha256") != _digest(body):
        raise ValueError("Continuous catalog expansion digest does not match")
    assertions = value.get("assertions")
    if not isinstance(assertions, dict) or not all(
        result is True for result in assertions.values()
    ):
        raise ValueError("Continuous catalog expansion assertions did not pass")
    return json.loads(json.dumps(value))


def render_markdown(value: Any) -> str:
    portfolio = validate_portfolio(value)
    results = portfolio["combined_results"]
    lines = [
        "# Exhaustive Continuous Catalog Expansion Study",
        "",
        "## Objective",
        "",
        portfolio["objective"],
        "",
        "## Method",
        "",
        portfolio["method"],
        "",
        "## Catalog populations",
        "",
        "| Catalog | Records | Compatible | Processed | Cycles | Successful contracts | Failures | Draft-ready |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for catalog in portfolio["catalogs"]:
        lines.append(
            f"| `{catalog['catalog_id']}` | {catalog['catalog_record_count']:,} | "
            f"{catalog['compatible_record_count']:,} | "
            f"{catalog['processed_record_count']:,} | {catalog['cycle_count']:,} | "
            f"{catalog['successful_contract_count']:,} | "
            f"{catalog['failed_contract_count']:,} | "
            f"{catalog['unique_draft_ready_count']:,} |"
        )
    lines.extend(
        [
            "",
            "## Aggregate results",
            "",
            "| Measure | Result |",
            "| --- | ---: |",
            f"| Catalog records | {results['catalog_record_count']:,} |",
            f"| Compatible records processed | {results['processed_record_count']:,} |",
            f"| Contract attempts | {results['attempted_record_count']:,} |",
            f"| Redundant attempts in recorded run | {results['redundant_attempt_count']:,} |",
            f"| Unique contracts inspected | {results['unique_contract_count']:,} |",
            f"| Unique operations inventoried | {results['unique_operation_count']:,} |",
            f"| Unique draft-ready candidates | {results['unique_draft_ready_count']:,} |",
            f"| Draft-ready provider hosts | {results['draft_ready_host_count']:,} |",
            f"| Scientific draft-ready candidates | {results['scientific_draft_ready_count']:,} |",
            f"| Blocked operations | {results['blocked_operation_count']:,} |",
            f"| Isolated contract failures | {results['failed_contract_count']:,} |",
            "",
            "Draft-ready means the static contract and existing VSD configuration "
            "generator accepted the operation. It does not mean that the upstream "
            "operation returned a scientifically valid response.",
            f"The recorded run made {results['redundant_attempt_count']:,} redundant "
            "attempts while filling the final bounded batches. Unique contract, "
            "operation, and configuration hashes exclude those repetitions; the "
            "scanner selection logic now stops a partial final cycle instead of "
            "rotating processed records into it.",
            "",
            "## Scientific candidates for downstream qualification",
            "",
            "| Catalog | API | Operation | Request | Term matches |",
            "| --- | --- | --- | --- | ---: |",
        ]
    )
    for sample in portfolio["scientific_candidate_samples"][:30]:
        lines.append(
            f"| `{sample['catalog_id']}` | {sample['title']} | "
            f"`{sample['operation_id']}` | "
            f"`{sample['method']} {sample['host']}{sample['path']}` | "
            f"{sample['scientific_term_matches']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The study separates scale from validity. Exhaustive scanning measures "
                "how many exact operations can enter a governed review queue; selected "
                "scientific candidates must still pass representative live verification, "
                "explicit approval, fresh-runtime loading, and lifecycle monitoring."
            ),
            "",
            "## Boundary",
            "",
            portfolio["boundary"],
            "",
            f"Portfolio SHA-256: `{portfolio['portfolio_sha256']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    portfolio: Any,
    *,
    json_path: Path = JSON_ARTIFACT,
    markdown_path: Path = MARKDOWN_ARTIFACT,
) -> tuple[Path, Path]:
    checked = validate_portfolio(portfolio)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(checked, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(checked), encoding="utf-8")
    return json_path, markdown_path


def run_live_study(
    state_directory: Path,
    *,
    max_contracts: int = 75,
    draftable_tool_target: int = 1_500,
    timeout_seconds: float = 30,
    max_cycles: int = 40,
) -> dict[str, Any]:
    tooluniverse = ToolUniverse()
    try:
        cycles = {
            catalog_id: run_catalog_to_completion(
                tooluniverse,
                catalog_id,
                state_directory / catalog_id,
                max_contracts=max_contracts,
                draftable_tool_target=draftable_tool_target,
                timeout_seconds=timeout_seconds,
                max_cycles=max_cycles,
            )
            for catalog_id in CATALOG_RUNNERS
        }
    finally:
        tooluniverse.close()
    return build_portfolio(cycles)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exhaust both live continuous VSD catalog adapters."
    )
    parser.add_argument("--state-directory", type=Path, required=True)
    parser.add_argument("--max-contracts", type=int, default=75)
    parser.add_argument("--draftable-tool-target", type=int, default=1_500)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--max-cycles", type=int, default=40)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    portfolio = run_live_study(
        arguments.state_directory,
        max_contracts=arguments.max_contracts,
        draftable_tool_target=arguments.draftable_tool_target,
        timeout_seconds=arguments.timeout,
        max_cycles=arguments.max_cycles,
    )
    json_path, markdown_path = write_artifacts(portfolio)
    print(
        json.dumps(
            {
                "json_artifact": str(json_path),
                "markdown_artifact": str(markdown_path),
                "portfolio_sha256": portfolio["portfolio_sha256"],
                "combined_results": portfolio["combined_results"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
