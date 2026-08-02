"""Promote two narrow tools from one discovered cancer-trial data source."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.vsd_promotion import (
    approve_draft,
    create_draft,
    list_promotion_state,
    load_published_tools,
    publish_draft,
    verify_draft,
)

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DISCOVERY_SNAPSHOT = ARTIFACTS / "api_discovery_snapshot.json"
DEFAULT_WORKSPACE = ARTIFACTS / "promotion_workspace"
DEFAULT_JSON = ARTIFACTS / "tool_promotion_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "tool_promotion_snapshot.md"
RETURN_FIELDS = [
    "date_opened",
    "protocol",
    "primary_site",
    "study_phase",
    "title",
    "date_closed",
    "principal_investigator",
]
DISCLAIMER = (
    "This validates software contracts and live retrieval, not trial quality, "
    "clinical relevance, or scientific conclusions."
)


def _verification_cases(field: str, values: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "arguments": {field: value},
            "expect": {
                "min_items": 1,
                "max_items": 25,
                "required_fields": ["protocol", "title", field],
                "equals": {field: value},
            },
        }
        for value in values
    ]


def _execute(tooluniverse: ToolUniverse, name: str, arguments: dict) -> dict:
    result = tooluniverse.run_one_function(
        {"name": name, "arguments": arguments}, use_cache=False
    )
    if not isinstance(result, dict) or result.get("status") != "success":
        raise RuntimeError(f"Published tool execution failed: {result!r}")
    return result["data"]


def _markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# Reviewed Tool Promotion: Cancer-Trial Case Study",
        "",
        "## Result",
        "",
        (
            "One discovery candidate produced two distinct, narrow ToolUniverse "
            "tools. Each tool passed three live provider cases, was approved against "
            "the exact verification hash, was published atomically, loaded into a "
            "fresh ToolUniverse instance, and executed again."
        ),
        "",
        f"- Provider: `{snapshot['source']['api_endpoint']}`",
        f"- Dataset: `{snapshot['source']['dataset_id']}`",
        f"- Loaded tools: {', '.join(f'`{name}`' for name in snapshot['loaded_tools'])}",
        f"- Boundary: {snapshot['interpretation_boundary']}",
        "",
        "## Promotion Evidence",
        "",
        "| Tool | Required filter | Verification cases | Rows observed | Operation hash |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for promotion in snapshot["promotions"]:
        counts = ", ".join(str(case["row_count"]) for case in promotion["cases"])
        lines.append(
            f"| `{promotion['tool_name']}` | `{promotion['filter_field']}` | "
            f"{promotion['case_count']} | {counts} | "
            f"`{promotion['operation_sha256'][:16]}...` |"
        )
    lines.extend(
        [
            "",
            "## Fresh Runtime Check",
            "",
            "| Tool | Query | Rows | Payload hash |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for check in snapshot["runtime_checks"]:
        argument = next(iter(check["arguments"].items()))
        lines.append(
            f"| `{check['tool_name']}` | `{argument[0]}={argument[1]}` | "
            f"{check['row_count']} | `{check['payload_sha256'][:16]}...` |"
        )
    lines.extend(
        [
            "",
            "## What This Proves",
            "",
            "1. Discovery metadata alone never executes and never enters the approved directory.",
            "2. Generation converts reviewed fields into bounded GET contracts with mandatory filters.",
            "3. Verification uses ToolUniverse itself and records counts, fields, timestamps, and hashes without storing entire provider responses.",
            "4. Approval and publication fail if the draft, evidence, or approval chain changes.",
            "5. Published tools are loaded only by an explicit call and cannot replace an existing tool.",
            "",
            "## Interpretation",
            "",
            DISCLAIMER,
            "",
        ]
    )
    return "\n".join(lines)


def run_case(
    *, workspace: Path, output_json: Path, output_markdown: Path
) -> dict[str, Any]:
    discovery = json.loads(DISCOVERY_SNAPSHOT.read_text(encoding="utf-8"))
    candidate = discovery["analysis"]["selected_candidate"]
    specs = [
        {
            "tool_name": "VSDGeneratedCancerTrialsBySite",
            "description": (
                "Query the reviewed Roswell Park active cancer-trial dataset by "
                "exact primary cancer site."
            ),
            "filter_field": "primary_site",
            "verification_values": [
                "Brain and Nervous System",
                "Breast",
                "Prostate",
            ],
            "runtime_value": "Breast",
        },
        {
            "tool_name": "VSDGeneratedCancerTrialsByPhase",
            "description": (
                "Query the reviewed Roswell Park active cancer-trial dataset by "
                "exact study phase."
            ),
            "filter_field": "study_phase",
            "verification_values": ["I", "II", "III"],
            "runtime_value": "III",
        },
    ]
    promotions = []
    for spec in specs:
        draft = create_draft(
            candidate,
            tool_name=spec["tool_name"],
            description=spec["description"],
            filter_fields=[spec["filter_field"]],
            return_fields=RETURN_FIELDS,
            max_records=25,
            workspace=workspace,
        )
        evidence = verify_draft(
            draft["draft_id"],
            _verification_cases(spec["filter_field"], spec["verification_values"]),
            workspace=workspace,
        )
        approval = approve_draft(
            draft["draft_id"],
            reviewed_by="SufianTA",
            decision_note=(
                "Technical approval after contract review and three live provider "
                "cases; this is not a scientific or clinical endorsement."
            ),
            workspace=workspace,
        )
        publication = publish_draft(
            draft["draft_id"], workspace=workspace, replace=True
        )
        promotions.append(
            {
                "tool_name": spec["tool_name"],
                "filter_field": spec["filter_field"],
                "draft_id": draft["draft_id"],
                "draft_sha256": draft["draft_sha256"],
                "operation_sha256": draft["operation_sha256"],
                "verification_sha256": evidence["verification_sha256"],
                "approval_sha256": approval["approval_sha256"],
                "publication_sha256": publication["publication_sha256"],
                "case_count": evidence["case_count"],
                "cases": evidence["cases"],
            }
        )

    runtime_workspace = workspace / ".runtime"
    tooluniverse = ToolUniverse(
        tool_files={}, keep_default_tools=False, workspace=str(runtime_workspace)
    )
    try:
        loaded = load_published_tools(tooluniverse, workspace=workspace)
        runtime_checks = []
        for spec in specs:
            arguments = {spec["filter_field"]: spec["runtime_value"]}
            data = _execute(tooluniverse, spec["tool_name"], arguments)
            rows = data["result"]
            if any(
                row.get(spec["filter_field"]) != spec["runtime_value"] for row in rows
            ):
                raise RuntimeError("Fresh runtime result violated its exact filter")
            runtime_checks.append(
                {
                    "tool_name": spec["tool_name"],
                    "arguments": arguments,
                    "row_count": len(rows),
                    "payload_sha256": data["provenance"]["payload_sha256"],
                    "operation_sha256": data["provenance"]["operation_sha256"],
                    "retrieved_at": data["provenance"]["retrieved_at"],
                    "sample_rows": rows[:3],
                }
            )
    finally:
        tooluniverse.close()

    snapshot = {
        "case": "one_discovered_source_to_two_reviewed_cancer_trial_tools",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "candidate_id": candidate["candidate_id"],
            "catalog_domain": candidate["catalog_domain"],
            "dataset_id": candidate["dataset_id"],
            "api_endpoint": candidate["api_endpoint"],
            "dataset_updated_at": candidate.get("updated_at"),
        },
        "promotions": promotions,
        "loaded_tools": loaded,
        "runtime_checks": runtime_checks,
        "promotion_state": list_promotion_state(workspace=workspace),
        "interpretation_boundary": DISCLAIMER,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(_markdown(snapshot), encoding="utf-8")
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    snapshot = run_case(
        workspace=args.workspace,
        output_json=args.output_json,
        output_markdown=args.output_markdown,
    )
    print(
        json.dumps(
            {
                "loaded_tools": snapshot["loaded_tools"],
                "verification_cases": sum(
                    item["case_count"] for item in snapshot["promotions"]
                ),
                "runtime_rows": [
                    item["row_count"] for item in snapshot["runtime_checks"]
                ],
                "output_json": str(args.output_json),
                "output_markdown": str(args.output_markdown),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
