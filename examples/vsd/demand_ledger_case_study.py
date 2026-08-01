"""Exercise private VSD demand aggregation and explicit proposal export."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from tooluniverse import ToolUniverse
from tooluniverse.vsd_demand import (
    export_proposals,
    observe_capability_demand,
    rank_demands,
    record_plan_demands,
    validate_proposal_export,
)
from tooluniverse.vsd_planning import plan_workflow

HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
DEFAULT_JSON = ARTIFACTS / "demand_ledger_snapshot.json"
DEFAULT_MARKDOWN = ARTIFACTS / "demand_ledger_snapshot.md"
DEFAULT_PROPOSALS = ARTIFACTS / "demand_proposals.json"

ALS_GOAL = (
    "Build an ALS evidence workflow from rare disease genes, phenotypes, "
    "literature, clinical trials, drug labels, and quantitative microscopy"
)
ALS_CAPABILITIES = [
    {
        "step_id": "genes",
        "description": "rare disease registry genes",
        "required_inputs": ["disease"],
    },
    {
        "step_id": "phenotypes",
        "description": "rare disease registry phenotypes",
        "required_inputs": ["disease"],
    },
    {
        "step_id": "literature",
        "description": "search biomedical literature articles by disease",
        "required_inputs": ["query"],
    },
    {
        "step_id": "trials",
        "description": "search clinical trials by disease condition",
        "required_inputs": ["condition"],
        "depends_on": ["genes", "phenotypes"],
    },
    {
        "step_id": "drug_label",
        "description": "retrieve FDA drug label by set identifier",
        "provider": "FDA",
        "required_inputs": ["set_id"],
    },
    {
        "step_id": "microscopy_calibration",
        "description": "quantum microscope calibration waveform optimizer",
        "required_inputs": ["instrument_id"],
        "output_fields": ["calibration_report"],
        "depends_on": ["genes"],
    },
    {
        "step_id": "synthesis",
        "description": "synthesize ALS evidence into a reviewed research brief",
        "fulfillment": "agent",
        "depends_on": [
            "genes",
            "phenotypes",
            "literature",
            "trials",
            "drug_label",
            "microscopy_calibration",
        ],
    },
]
PUBLIC_SUMMARIES = {
    "genes": "ALS rare-disease gene retrieval for evidence workflows",
    "phenotypes": "ALS rare-disease phenotype retrieval for evidence workflows",
    "literature": "ALS biomedical literature retrieval for evidence workflows",
    "trials": "ALS clinical-trial retrieval for evidence workflows",
    "microscopy_calibration": (
        "Quantitative microscopy calibration for ALS research workflows"
    ),
}
RETINAL_REQUEST = {
    "description": (
        "calibrate adaptive optics retinal imaging phantoms with traceable "
        "wavefront uncertainty"
    ),
    "required_inputs": ["instrument_id"],
    "output_fields": ["calibration_report"],
}
RETINAL_SUMMARY = (
    "Traceable adaptive-optics retinal imaging calibration for research workflows"
)
FDA_REQUEST = {
    "description": "retrieve FDA drug label by set identifier",
    "provider": "FDA",
    "required_inputs": ["set_id"],
}
FDA_SUMMARY = "FDA drug-label retrieval by reviewed set identifier"
RAW_DESCRIPTIONS = {
    *(step["description"] for step in ALS_CAPABILITIES),
    RETINAL_REQUEST["description"],
    FDA_REQUEST["description"],
}
RUN_IDS = ("als-run-001", "als-run-002", "als-run-003")
EXPECTED_ASSERTIONS = {
    "agent_synthesis_is_not_recorded",
    "already_satisfied_demand_is_not_ranked",
    "batch_plan_identity_is_verified",
    "duplicate_run_is_deduplicated",
    "event_ids_are_not_persisted",
    "export_contains_only_selected_demands",
    "export_is_hash_bound",
    "export_is_local_only",
    "ledger_has_expected_population",
    "ledger_is_hash_bound",
    "local_paths_are_not_exposed",
    "raw_descriptions_are_not_persisted",
    "repeated_missing_demand_ranks_first",
}


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_case(workspace: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    proposal_path = workspace / "selected_proposals.json"
    tooluniverse = ToolUniverse()
    try:
        plan = plan_workflow(
            tooluniverse,
            goal=ALS_GOAL,
            capabilities=ALS_CAPABILITIES,
            limit=5,
        )
        batches = [
            record_plan_demands(
                plan,
                PUBLIC_SUMMARIES,
                workspace=workspace,
                source="scheduled_scan",
                run_id=run_id,
                observed_at=f"2026-08-0{index}T12:00:00+00:00",
            )
            for index, run_id in enumerate(RUN_IDS, start=1)
        ]
        duplicate = record_plan_demands(
            plan,
            PUBLIC_SUMMARIES,
            workspace=workspace,
            source="scheduled_scan",
            run_id=RUN_IDS[-1],
            observed_at="2026-08-03T12:00:00+00:00",
        )
        retinal = [
            observe_capability_demand(
                tooluniverse,
                RETINAL_REQUEST,
                public_summary=RETINAL_SUMMARY,
                source="scheduled_scan",
                event_id=f"retinal-run-{index:03d}",
                observed_at=f"2026-08-0{index + 3}T12:00:00+00:00",
                workspace=workspace,
            )
            for index in range(1, 3)
        ]
        satisfied = observe_capability_demand(
            tooluniverse,
            FDA_REQUEST,
            public_summary=FDA_SUMMARY,
            source="manual_review",
            event_id="fda-review-001",
            observed_at="2026-08-06T12:00:00+00:00",
            workspace=workspace,
        )
    finally:
        tooluniverse.close()

    ranking = rank_demands(workspace=workspace)["data"]
    ranked = ranking["ranked_demands"]
    selected_ids = [item["demand_id"] for item in ranked[:2]]
    proposals = export_proposals(
        selected_ids,
        proposal_path,
        reviewed_by="VSD Case Study Maintainer",
        decision_note=(
            "Selected the two highest repeated unmet capabilities after local review."
        ),
        workspace=workspace,
        created_at="2026-08-07T12:00:00+00:00",
    )
    validate_proposal_export(proposals)

    ledger_path = workspace / "demand_ledger.json"
    ledger_text = ledger_path.read_text(encoding="utf-8")
    proposal_text = proposal_path.read_text(encoding="utf-8")
    ranked_summaries = [item["public_summary"] for item in ranked]
    plan_steps = [
        {
            "step_id": step["step_id"],
            "classification": step["classification"],
            "fulfillment": step["fulfillment"],
        }
        for step in plan["data"]["steps"]
    ]
    assertions = {
        "batch_plan_identity_is_verified": (
            all(
                batch["data"]["plan_id"] == plan["data"]["plan_id"] for batch in batches
            )
            and all(batch["data"]["recorded_count"] == 5 for batch in batches)
        ),
        "duplicate_run_is_deduplicated": (
            duplicate["data"]["recorded_count"] == 0
            and duplicate["data"]["deduplicated_count"] == 5
        ),
        "ledger_has_expected_population": (
            ranking["total_demand_count"] == 7 and ranking["matching_demand_count"] == 6
        ),
        "repeated_missing_demand_ranks_first": (
            [item["priority_score"] for item in ranked[:3]] == [15, 10, 6]
            and ranked[0]["public_summary"]
            == PUBLIC_SUMMARIES["microscopy_calibration"]
            and ranked[1]["public_summary"] == RETINAL_SUMMARY
        ),
        "already_satisfied_demand_is_not_ranked": (
            satisfied["data"]["demand"]["observation_counts"]["exact"] == 1
            and FDA_SUMMARY not in ranked_summaries
        ),
        "agent_synthesis_is_not_recorded": (
            next(step for step in plan_steps if step["step_id"] == "synthesis")[
                "fulfillment"
            ]
            == "agent"
            and "synthesis" not in PUBLIC_SUMMARIES
            and "synthesize" not in ledger_text.casefold()
        ),
        "export_contains_only_selected_demands": (
            len(proposals["proposals"]) == 2
            and [item["public_summary"] for item in proposals["proposals"]]
            == ranked_summaries[:2]
            and all(demand_id not in proposal_text for demand_id in selected_ids)
        ),
        "raw_descriptions_are_not_persisted": all(
            description not in ledger_text and description not in proposal_text
            for description in RAW_DESCRIPTIONS
        ),
        "event_ids_are_not_persisted": all(
            run_id not in ledger_text and run_id not in proposal_text
            for run_id in (
                *RUN_IDS,
                "retinal-run-001",
                "retinal-run-002",
                "fda-review-001",
            )
        ),
        "local_paths_are_not_exposed": (
            str(workspace) not in ledger_text
            and str(workspace) not in proposal_text
            and str(workspace) not in json.dumps(ranking)
        ),
        "ledger_is_hash_bound": (
            len(ranking["ledger_sha256"]) == 64
            and all(batch["data"]["ledger_sha256"] for batch in [*batches, duplicate])
        ),
        "export_is_hash_bound": (
            len(proposals["export_sha256"]) == 64
            and json.loads(proposal_text)["export_sha256"] == proposals["export_sha256"]
        ),
        "export_is_local_only": proposals["transmission"].startswith("none;"),
    }
    snapshot = {
        "title": "Private ALS Capability-Demand Ledger Case Study",
        "question": (
            "Can repeated workflow gaps be counted and prioritized locally without "
            "silently reporting queries or exporting satisfied capabilities?"
        ),
        "answer": (
            "Yes. Three hash-bound ALS plans and two retinal-calibration observations "
            "produced a deterministic unmet-demand ranking; one exact FDA capability "
            "was retained locally but excluded, and only two reviewed proposals were "
            "written to a non-transmitting export."
        ),
        "plan": {
            "plan_id": plan["data"]["plan_id"],
            "plan_sha256": plan["data"]["plan_sha256"],
            "registry_sha256": plan["data"]["registry_sha256"],
            "steps": plan_steps,
        },
        "observation_summary": {
            "plan_runs_recorded": len(batches),
            "plan_step_observations_recorded": sum(
                batch["data"]["recorded_count"] for batch in batches
            ),
            "duplicate_step_observations_rejected": duplicate["data"][
                "deduplicated_count"
            ],
            "retinal_observations_recorded": sum(
                item["data"]["recorded"] for item in retinal
            ),
            "satisfied_observations_recorded": int(satisfied["data"]["recorded"]),
        },
        "ranking": ranking,
        "proposal_export": proposals,
        "privacy_boundary": (
            "The ledger is private and local; raw descriptions and event IDs are not "
            "stored. Export is an explicit reviewed file write and performs no network "
            "transmission, candidate creation, tool registration, or execution."
        ),
        "end_to_end_assertions": assertions,
    }
    snapshot["audit_sha256"] = _digest(
        {
            "plan": snapshot["plan"],
            "observation_summary": snapshot["observation_summary"],
            "ranking": snapshot["ranking"],
            "proposal_export": snapshot["proposal_export"],
            "privacy_boundary": snapshot["privacy_boundary"],
            "end_to_end_assertions": assertions,
        }
    )
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    assertions = snapshot.get("end_to_end_assertions")
    if not isinstance(assertions, dict) or set(assertions) != EXPECTED_ASSERTIONS:
        raise ValueError("Snapshot does not contain the complete assertion set")
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise ValueError(f"End-to-end assertions failed: {failed!r}")
    validate_proposal_export(snapshot.get("proposal_export"))
    expected = _digest(
        {
            "plan": snapshot["plan"],
            "observation_summary": snapshot["observation_summary"],
            "ranking": snapshot["ranking"],
            "proposal_export": snapshot["proposal_export"],
            "privacy_boundary": snapshot["privacy_boundary"],
            "end_to_end_assertions": assertions,
        }
    )
    if snapshot.get("audit_sha256") != expected:
        raise ValueError("Snapshot audit digest does not match its content")


def _markdown(snapshot: dict[str, Any]) -> str:
    ranking = snapshot["ranking"]
    proposals = snapshot["proposal_export"]["proposals"]
    lines = [
        "# Private ALS Capability-Demand Ledger Case Study",
        "",
        "## Decision Question",
        "",
        snapshot["question"],
        "",
        f"**Result:** {snapshot['answer']}",
        "",
        "## Hash-Bound Workflow Input",
        "",
        f"Plan `{snapshot['plan']['plan_id']}` was verified against its complete "
        "SHA-256 before any observations were committed. Three distinct scheduled "
        "runs recorded five unmet tool steps each; replaying the last run recorded "
        "nothing because its event hashes were already present.",
        "",
        "| Step | Fulfillment | Coverage |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        f"| `{step['step_id']}` | {step['fulfillment']} | {step['classification']} |"
        for step in snapshot["plan"]["steps"]
    )
    lines.extend(
        [
            "",
            "## Local Priority Ranking",
            "",
            "Missing observations receive five points and partial observations receive "
            "two. Exact coverage remains available in the private ledger but does not "
            "enter the unmet-demand ranking.",
            "",
            "| Rank | Reviewed public summary | Exact | Partial | Missing | Score |",
            "| ---: | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for index, item in enumerate(ranking["ranked_demands"], start=1):
        counts = item["observation_counts"]
        lines.append(
            f"| {index} | {item['public_summary']} | {counts['exact']} | "
            f"{counts['partial']} | {counts['missing']} | {item['priority_score']} |"
        )
    lines.extend(
        [
            "",
            "## Explicit Proposal Export",
            "",
            "Only the two highest reviewed demand IDs were selected. The export "
            "contains stable proposal IDs, safe structured capability fields, aggregate "
            "counts, and a review decision. It contains no local demand IDs, raw query "
            "descriptions, event IDs, or filesystem paths.",
            "",
            "| Proposal | Public summary | Next step |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| `{item['proposal_id']}` | {item['public_summary']} | "
        f"`{item['recommended_next_step']}` |"
        for item in proposals
    )
    lines.extend(
        [
            "",
            "## End-to-End Assertions",
            "",
            "| Assertion | Result |",
            "| --- | --- |",
        ]
    )
    lines.extend(
        f"| `{name}` | {'PASS' if passed else 'FAIL'} |"
        for name, passed in sorted(snapshot["end_to_end_assertions"].items())
    )
    lines.extend(
        [
            "",
            "## Privacy And Execution Boundary",
            "",
            snapshot["privacy_boundary"],
            "",
            f"**Ledger SHA-256:** `{ranking['ledger_sha256']}`",
            "",
            f"**Export SHA-256:** `{snapshot['proposal_export']['export_sha256']}`",
            "",
            f"**Case audit SHA-256:** `{snapshot['audit_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_artifacts(
    snapshot: dict[str, Any],
    json_path: Path = DEFAULT_JSON,
    markdown_path: Path = DEFAULT_MARKDOWN,
    proposals_path: Path = DEFAULT_PROPOSALS,
) -> None:
    validate_snapshot(snapshot)
    for path in (json_path, markdown_path, proposals_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(_markdown(snapshot), encoding="utf-8")
    proposals_path.write_text(
        json.dumps(
            snapshot["proposal_export"], indent=2, sort_keys=True, ensure_ascii=True
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tooluniverse-vsd-demand-") as directory:
        snapshot = run_case(Path(directory))
    write_artifacts(snapshot)
    print(json.dumps({"status": "passed", "audit_sha256": snapshot["audit_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
