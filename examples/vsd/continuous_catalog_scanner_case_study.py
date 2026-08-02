"""Live, two-cycle scale evaluation for the continuous VSD catalog scanner."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from tooluniverse.execute_function import ToolUniverse
from tooluniverse.vsd_continuous_scanner import (
    run_scheduled_apis_guru_scan,
    validate_continuous_scan_cycle,
)

HERE = Path(__file__).resolve().parent
ARTIFACT_DIRECTORY = HERE / "artifacts"
JSON_ARTIFACT = ARTIFACT_DIRECTORY / "continuous_catalog_scanner_portfolio.json"
MARKDOWN_ARTIFACT = ARTIFACT_DIRECTORY / "continuous_catalog_scanner_portfolio.md"
SUPPORTED_CONTRACT_FORMATS = [
    "openapi",
    "graphql",
    "asyncapi",
    "postman",
    "wsdl",
    "protobuf",
    "mcp",
]


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _combined_blockers(cycles: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for cycle in cycles:
        counts.update(cycle["blocker_counts"])
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _sample_operations(
    operations: list[dict[str, Any]], maximum: int = 30
) -> list[dict[str, Any]]:
    draftable = [item for item in operations if item["preview"] is not None]
    by_record: dict[str, list[dict[str, Any]]] = {}
    for operation in sorted(
        draftable,
        key=lambda item: (
            item["record_id"].casefold(),
            item["operation_id"].casefold(),
            item["candidate_id"],
        ),
    ):
        by_record.setdefault(operation["record_id"], []).append(operation)
    samples: list[dict[str, Any]] = []
    while by_record and len(samples) < maximum:
        for record_id in sorted(list(by_record), key=str.casefold):
            operation = by_record[record_id].pop(0)
            samples.append(
                {
                    "record_id": record_id,
                    "api_title": operation["api_title"],
                    "api_version": operation["api_version"],
                    "operation_id": operation["operation_id"],
                    "method": operation["method"],
                    "host": operation["host"],
                    "path": operation["path"],
                    "registry_coverage": operation["registry_coverage"],
                    "preview_tool_name": operation["preview"]["tool_name"],
                    "preview_config_sha256": operation["preview"]["config_sha256"],
                    "candidate_sha256": operation["candidate_sha256"],
                    "approval_state": operation["approval_state"],
                    "execution_allowed": operation["execution_allowed"],
                }
            )
            if not by_record[record_id]:
                del by_record[record_id]
            if len(samples) == maximum:
                break
    return samples


def build_portfolio(cycle_values: Sequence[Any]) -> dict[str, Any]:
    cycles = [validate_continuous_scan_cycle(value) for value in cycle_values]
    if len(cycles) < 2:
        raise ValueError("The scale portfolio requires at least two linked cycles")
    operations = [item for cycle in cycles for item in cycle["operations"]]
    draftable = [item for item in operations if item["preview"] is not None]
    config_hashes = sorted({item["preview"]["config_sha256"] for item in draftable})
    operation_hashes = sorted(
        {
            item["candidate_sha256"]
            for item in operations
            if isinstance(item.get("candidate_sha256"), str)
            and len(item["candidate_sha256"]) == 64
        }
    )
    contract_hashes = sorted(
        {
            contract["content_sha256"]
            for cycle in cycles
            for contract in cycle["contracts"]
        }
    )
    hosts = sorted({item["host"] for item in draftable if item["host"]})
    record_lookup = {
        record["record_id"]: record for record in cycles[-1]["directory"]["records"]
    }
    categories = sorted(
        {
            category
            for cycle in cycles
            for record_id in cycle["attempted_record_ids"]
            for category in record_lookup.get(record_id, {}).get("categories", [])
        },
        key=str.casefold,
    )
    total_failures = sum(len(cycle["failures"]) for cycle in cycles)
    combined = {
        "cycle_count": len(cycles),
        "unique_contract_count": len(contract_hashes),
        "operation_candidate_count": len(operation_hashes),
        "draftable_tool_count": len(config_hashes),
        "draftable_config_set_sha256": _digest(config_hashes),
        "operation_candidate_set_sha256": _digest(operation_hashes),
        "contract_set_sha256": _digest(contract_hashes),
        "draftable_host_count": len(hosts),
        "existing_host_gap_count": sum(
            item["registry_coverage"] == "existing_host_gap" for item in operations
        ),
        "new_host_candidate_count": sum(
            item["registry_coverage"] == "candidate_gap" for item in operations
        ),
        "blocked_operation_count": sum(bool(item["blockers"]) for item in operations),
        "failed_contract_count": total_failures,
        "represented_category_count": len(categories),
        "represented_categories": categories,
        "blocker_counts": _combined_blockers(cycles),
    }
    summaries = [
        {
            "cycle_id": cycle["cycle_id"],
            "cycle_sha256": cycle["cycle_sha256"],
            "previous_cycle_id": cycle["previous_cycle_id"],
            "scanned_at": cycle["scanned_at"],
            "directory_sha256": cycle["directory"]["directory_sha256"],
            "delta": {
                key: cycle["delta"][key]
                for key in ("added_count", "changed_count", "removed_count")
            },
            "metrics": cycle["metrics"],
            "attempted_record_count": len(cycle["attempted_record_ids"]),
            "successful_contract_ids": [
                contract["record_id"] for contract in cycle["contracts"]
            ],
            "failures": cycle["failures"],
        }
        for cycle in cycles
    ]
    first = cycles[0]
    latest = cycles[-1]
    assertions = {
        "complete_live_directory_exceeded_two_thousand_records": first["directory"][
            "record_count"
        ]
        > 2_000,
        "more_than_one_thousand_openapi_three_sources_were_compatible": first[
            "directory"
        ]["compatible_record_count"]
        > 1_000,
        "real_tooluniverse_registry_exceeded_two_thousand_tools": first["registry"][
            "tool_count"
        ]
        > 2_000,
        "cycles_are_hash_linked": all(
            current["previous_cycle_id"] == previous["cycle_id"]
            for previous, current in zip(cycles, cycles[1:])
        ),
        "later_cycle_inspected_new_contracts": any(
            set(current["state"]["inspected_record_ids"])
            > set(previous["state"]["inspected_record_ids"])
            for previous, current in zip(cycles, cycles[1:])
        ),
        "at_least_five_hundred_unique_operations_were_inventoried": len(
            operation_hashes
        )
        >= 500,
        "at_least_five_hundred_unique_tool_configs_were_draftable": len(config_hashes)
        >= 500,
        "draftable_configs_span_multiple_provider_hosts": len(hosts) >= 3,
        "contract_failures_were_isolated": total_failures
        < sum(len(cycle["attempted_record_ids"]) for cycle in cycles),
        "every_operation_remained_inert": all(
            item["approval_state"] == "unreviewed_operation_candidate"
            and item["execution_allowed"] is False
            for item in operations
        ),
        "no_cycle_enabled_publication": all(
            cycle["automatic_publication"] is False
            and cycle["execution_allowed"] is False
            for cycle in cycles
        ),
        "preview_hashes_are_unique_and_secret_free": len(config_hashes)
        == len(draftable)
        and all(
            "credential" not in json.dumps(item["preview"], sort_keys=True).casefold()
            for item in draftable
        ),
        "second_cycle_used_the_current_directory": latest["directory"]["record_count"]
        > 2_000,
    }
    body = {
        "format": "vsd_continuous_catalog_scale_portfolio_v1",
        "version": 1,
        "generated_at": latest["scanned_at"],
        "evaluation_mode": "live_network",
        "objective": (
            "Evaluate whether a scheduled VSD scanner can inventory a large public "
            "API directory, rotate through changing contracts, compare operations "
            "with the real ToolUniverse registry, and prepare hundreds of inert, "
            "draft-ready tool configurations without approval or execution."
        ),
        "supported_contract_inputs": SUPPORTED_CONTRACT_FORMATS,
        "live_scale_input": {
            "catalog": "APIs.guru OpenAPI Directory",
            "catalog_endpoint": first["directory"]["catalog_endpoint"],
            "catalog_record_count": first["directory"]["record_count"],
            "compatible_openapi_3_count": first["directory"]["compatible_record_count"],
            "unsupported_openapi_2_count": first["directory"][
                "unsupported_record_count"
            ],
            "catalog_payload_sha256": first["directory"]["request"]["payload_sha256"],
            "catalog_response_bytes": first["directory"]["request"]["response_bytes"],
        },
        "real_registry": latest["registry"],
        "cycles": summaries,
        "combined_results": combined,
        "draftable_samples": _sample_operations(operations),
        "assertions": assertions,
        "boundary": (
            "The scanner created no approvals and published or executed no tools. "
            "A draft-ready hash means the existing VSD generator accepted the exact "
            "read-only operation; representative verification and administrator "
            "approval are still required before publication."
        ),
    }
    return {**body, "portfolio_sha256": _digest(body)}


def validate_portfolio(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("format") != (
        "vsd_continuous_catalog_scale_portfolio_v1"
    ):
        raise ValueError("Continuous scanner portfolio is invalid")
    body = {key: item for key, item in value.items() if key != "portfolio_sha256"}
    if value.get("portfolio_sha256") != _digest(body):
        raise ValueError("Continuous scanner portfolio hash does not match")
    assertions = value.get("assertions")
    if (
        not isinstance(assertions, dict)
        or not assertions
        or not all(result is True for result in assertions.values())
    ):
        raise ValueError("Continuous scanner portfolio assertions did not pass")
    if value.get("evaluation_mode") != "live_network":
        raise ValueError("Checked scanner evidence must identify its live mode")
    return json.loads(json.dumps(value))


def render_markdown(value: Any) -> str:
    portfolio = validate_portfolio(value)
    source = portfolio["live_scale_input"]
    results = portfolio["combined_results"]
    lines = [
        "# Continuous VSD Catalog Scanner Scale Evaluation",
        "",
        "## Evaluation objective",
        "",
        portfolio["objective"],
        "",
        "## Method",
        "",
        (
            f"Two linked live cycles read the complete {source['catalog']} response, "
            "audited the current ToolUniverse registry, selected previously uninspected "
            "OpenAPI 3 contracts across catalog categories, saved content-addressed "
            "local snapshots, inspected each operation, and invoked the existing VSD "
            "configuration generator for operations that passed the static contract "
            "boundary. No provider operation was called."
        ),
        "",
        "The broader source-intelligence and contract-inspection path accepts: "
        + ", ".join(f"`{item}`" for item in portfolio["supported_contract_inputs"])
        + ". The large-scale live directory used OpenAPI because it provides a single "
        "bounded catalog containing thousands of independently maintained contracts.",
        "",
        "## Directory and registry",
        "",
        "| Measure | Result |",
        "| --- | ---: |",
        f"| Live catalog records | {source['catalog_record_count']:,} |",
        f"| Compatible OpenAPI 3 records | {source['compatible_openapi_3_count']:,} |",
        f"| Unsupported OpenAPI 2 records | {source['unsupported_openapi_2_count']:,} |",
        f"| Catalog response bytes | {source['catalog_response_bytes']:,} |",
        f"| ToolUniverse tools audited | {portfolio['real_registry']['tool_count']:,} |",
        f"| ToolUniverse source hosts audited | {portfolio['real_registry']['host_count']:,} |",
        "",
        "## Results",
        "",
        "| Measure | Result |",
        "| --- | ---: |",
        f"| Linked scan cycles | {results['cycle_count']:,} |",
        f"| Unique contracts inspected | {results['unique_contract_count']:,} |",
        f"| Unique operation candidates inventoried | {results['operation_candidate_count']:,} |",
        f"| Unique draft-ready configuration hashes | {results['draftable_tool_count']:,} |",
        f"| Provider hosts represented by draft-ready operations | {results['draftable_host_count']:,} |",
        f"| Blocked operations | {results['blocked_operation_count']:,} |",
        f"| Isolated contract failures | {results['failed_contract_count']:,} |",
        f"| Catalog categories represented | {results['represented_category_count']:,} |",
        "",
        "A draft-ready result is a configuration-generation proof, not a published "
        "tool. The scanner retained only the candidate identity and configuration hash "
        "in its review queue.",
        "",
        "## Cycle progression",
        "",
        "| Cycle | Added | Changed | Removed | Contracts | Operations | Draft-ready | Failures |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cycle in portfolio["cycles"]:
        metrics = cycle["metrics"]
        delta = cycle["delta"]
        lines.append(
            f"| `{cycle['cycle_id']}` | {delta['added_count']:,} | "
            f"{delta['changed_count']:,} | {delta['removed_count']:,} | "
            f"{metrics['inspected_contract_count']:,} | "
            f"{metrics['operation_candidate_count']:,} | "
            f"{metrics['draftable_tool_count']:,} | "
            f"{metrics['failed_contract_count']:,} |"
        )
    lines.extend(
        [
            "",
            "## Representative draft-ready operations",
            "",
            "| API | Operation | Request | Registry relationship | Preview identity |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for sample in portfolio["draftable_samples"][:20]:
        request = f"{sample['method']} {sample['host']}{sample['path']}"
        lines.append(
            f"| {sample['api_title']} | `{sample['operation_id']}` | `{request}` | "
            f"{sample['registry_coverage']} | `{sample['preview_tool_name']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The evaluation demonstrates a practical supply-side growth mechanism: "
                "an approved directory can be monitored repeatedly, unchanged sources "
                "can be rotated rather than rescanned in every cycle, broken contracts "
                "remain isolated, and hundreds of exact read operations can enter a "
                "local review queue without becoming executable. Demand ranking and "
                "workflow planning can then prioritize which candidates justify the "
                "cost of representative verification and maintenance."
            ),
            "",
            "## Limitations",
            "",
            (
                "Directory inclusion and successful static generation do not establish "
                "scientific relevance, provider reliability, or response correctness. "
                "The checked cycles intentionally stop before verification, approval, "
                "publication, and execution. OpenAPI 2 records are inventoried but not "
                "inspected because the current reviewed OpenAPI boundary accepts 3.0 "
                "and 3.1 documents."
            ),
            "",
            "## Reproduction",
            "",
            "```console",
            "PYTHONPATH=src TOOLUNIVERSE_CACHE_PERSIST=false \\",
            "  uv run python examples/vsd/continuous_catalog_scanner_case_study.py",
            "```",
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


def run_live_portfolio(
    state_directory: Path,
    *,
    cycles: int = 2,
    max_contracts: int = 80,
    draftable_tool_target: int = 350,
    timeout_seconds: float = 30,
) -> dict[str, Any]:
    tooluniverse = ToolUniverse()
    values: list[dict[str, Any]] = []
    try:
        for _ in range(cycles):
            result = run_scheduled_apis_guru_scan(
                tooluniverse,
                state_directory,
                max_contracts=max_contracts,
                draftable_tool_target=draftable_tool_target,
                timeout_seconds=timeout_seconds,
            )
            values.append(result["cycle"])
    finally:
        tooluniverse.close()
    return build_portfolio(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the live two-cycle continuous VSD scanner evaluation."
    )
    parser.add_argument("--state-directory", type=Path)
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--max-contracts", type=int, default=80)
    parser.add_argument("--draftable-tool-target", type=int, default=350)
    parser.add_argument("--timeout", type=float, default=30)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.state_directory:
        portfolio = run_live_portfolio(
            arguments.state_directory,
            cycles=arguments.cycles,
            max_contracts=arguments.max_contracts,
            draftable_tool_target=arguments.draftable_tool_target,
            timeout_seconds=arguments.timeout,
        )
    else:
        with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-scanner-") as root:
            portfolio = run_live_portfolio(
                Path(root),
                cycles=arguments.cycles,
                max_contracts=arguments.max_contracts,
                draftable_tool_target=arguments.draftable_tool_target,
                timeout_seconds=arguments.timeout,
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
