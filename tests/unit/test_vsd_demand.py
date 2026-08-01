from __future__ import annotations

import copy
import json
import multiprocessing
from pathlib import Path

import pytest

from tooluniverse.vsd_coverage import resolve_capability
from tooluniverse.vsd_demand import (
    VSDDemandError,
    export_proposals,
    observe_capability_demand,
    rank_demands,
    record_coverage_observation,
    record_plan_demands,
    remove_demand,
    validate_proposal_export,
)
from tooluniverse.vsd_planning import plan_workflow
from tooluniverse.tool_registry import get_config_registry, get_tool_registry

pytestmark = pytest.mark.unit

MISSING_REQUEST = {
    "description": "quantum microscope calibration waveform optimizer",
    "required_inputs": ["sample_id"],
    "output_fields": ["calibration_score"],
}
MISSING_SUMMARY = "Quantitative microscopy calibration for research workflows"


class _Registry:
    tool_files = {}

    def __init__(self, tools=()):
        self.all_tools = list(tools)
        self.all_tool_dict = {tool["name"]: tool for tool in self.all_tools}


def _existing_tool() -> dict:
    return {
        "name": "ExistingRegistryRecords",
        "type": "VSDDynamicRESTTool",
        "category": "special_tools",
        "description": "Retrieve reviewed disease registry records by disease.",
        "parameter": {
            "type": "object",
            "properties": {"disease": {"type": "string"}},
            "required": ["disease"],
        },
        "return_schema": {
            "type": "object",
            "properties": {"registry_id": {"type": "string"}},
        },
        "vsd_operation": {
            "method": "GET",
            "endpoint": "https://registry.example.org/v1/diseases",
        },
        "vsd_capability": {"operation_id": "registry.search_diseases"},
    }


def _exact_request() -> dict:
    return {
        "description": "retrieve disease registry records",
        "operation_id": "registry.search_diseases",
        "required_inputs": ["disease"],
        "output_fields": ["registry_id"],
    }


def _missing_coverage() -> dict:
    return resolve_capability(_Registry(), MISSING_REQUEST)


def _record_missing(
    workspace: Path,
    *,
    event_id: str | None = None,
    observed_at: str = "2026-08-01T12:00:00+00:00",
) -> dict:
    return record_coverage_observation(
        MISSING_REQUEST,
        _missing_coverage(),
        public_summary=MISSING_SUMMARY,
        source="scheduled_scan",
        event_id=event_id,
        observed_at=observed_at,
        workspace=workspace,
    )


def _concurrent_record_worker(workspace: str, event_id: str, results) -> None:
    try:
        result = _record_missing(Path(workspace), event_id=event_id)
        results.put((result["data"]["recorded"], None))
    except Exception as exc:  # pragma: no cover - asserted in parent process
        results.put((False, repr(exc)))
        raise


def test_demand_mutation_and_export_are_not_agent_facing_tools():
    prohibited = {"VSDRecordDemand", "VSDRankDemands", "VSDExportProposals"}
    assert prohibited.isdisjoint(get_tool_registry())
    assert prohibited.isdisjoint(get_config_registry())


def test_private_ledger_omits_raw_query_and_event_ids_and_deduplicates(tmp_path):
    first = _record_missing(tmp_path, event_id="cron-run-001")
    duplicate = _record_missing(tmp_path, event_id="cron-run-001")
    ledger_text = (tmp_path / "demand_ledger.json").read_text(encoding="utf-8")

    assert first["data"]["recorded"] is True
    assert duplicate["data"]["recorded"] is False
    assert duplicate["data"]["deduplicated"] is True
    assert first["data"]["demand"]["total_observations"] == 1
    assert "quantum microscope calibration waveform optimizer" not in ledger_text
    assert "cron-run-001" not in ledger_text
    assert MISSING_SUMMARY in ledger_text
    assert str(tmp_path) not in json.dumps(first)


def test_ranking_prioritizes_repeated_missing_then_partial_and_hides_satisfied(
    tmp_path,
):
    for index in range(2):
        _record_missing(tmp_path, event_id=f"missing-{index}")

    partial_request = {
        "description": "retrieve registry investigator contacts",
        "provider": "registry.example.org",
        "required_inputs": ["investigator_id"],
    }
    partial_coverage = resolve_capability(
        _Registry([_existing_tool()]), partial_request
    )
    assert partial_coverage["data"]["classification"] == "existing_partial"
    record_coverage_observation(
        partial_request,
        partial_coverage,
        public_summary="Registry investigator contact lookup for evidence review",
        workspace=tmp_path,
    )

    exact_request = _exact_request()
    exact_coverage = resolve_capability(_Registry([_existing_tool()]), exact_request)
    record_coverage_observation(
        exact_request,
        exact_coverage,
        public_summary="Reviewed disease registry lookup by disease identifier",
        workspace=tmp_path,
    )

    ranked = rank_demands(workspace=tmp_path)["data"]
    assert [item["priority_score"] for item in ranked["ranked_demands"]] == [10, 2]
    assert ranked["ranked_demands"][0]["public_summary"] == MISSING_SUMMARY
    assert ranked["total_demand_count"] == 3
    assert ranked["matching_demand_count"] == 2
    assert (
        len(
            rank_demands(workspace=tmp_path, include_satisfied=True)["data"][
                "ranked_demands"
            ]
        )
        == 3
    )


def test_export_is_explicit_sanitized_hash_bound_and_tamper_detecting(tmp_path):
    result = _record_missing(tmp_path, event_id="private-event-value")
    demand_id = result["data"]["demand"]["demand_id"]
    output = tmp_path / "review" / "proposals.json"
    exported = export_proposals(
        [demand_id],
        output,
        reviewed_by="VSD Maintainer",
        decision_note="Selected after reviewing the local unmet-demand aggregate.",
        workspace=tmp_path,
        created_at="2026-08-01T13:00:00+00:00",
    )

    validate_proposal_export(exported)
    serialized = json.dumps(exported, sort_keys=True)
    assert demand_id not in serialized
    assert "private-event-value" not in serialized
    assert "quantum microscope calibration waveform optimizer" not in serialized
    assert str(tmp_path) not in serialized
    assert exported["transmission"].startswith("none;")
    assert json.loads(output.read_text(encoding="utf-8")) == exported

    with pytest.raises(VSDDemandError, match="already exists"):
        export_proposals(
            [demand_id],
            output,
            reviewed_by="VSD Maintainer",
            decision_note="Selected after reviewing the local unmet-demand aggregate.",
            workspace=tmp_path,
        )

    tampered = copy.deepcopy(exported)
    tampered["proposals"][0]["priority_score"] = 999
    with pytest.raises(VSDDemandError, match="derived fields"):
        validate_proposal_export(tampered)


def test_export_omits_endpoint_paths_and_rejects_private_providers(tmp_path):
    request = {
        "description": "retrieve specialist assay calibration records",
        "endpoint": "https://api.example.org/private-tenant/record-12345",
    }
    result = record_coverage_observation(
        request,
        resolve_capability(_Registry(), request),
        public_summary="Specialist assay calibration records for research workflows",
        workspace=tmp_path,
    )
    exported = export_proposals(
        [result["data"]["demand"]["demand_id"]],
        tmp_path / "safe-proposal.json",
        reviewed_by="VSD Maintainer",
        decision_note="Selected after verifying the reduced public capability fields.",
        workspace=tmp_path,
    )
    serialized = json.dumps(exported, sort_keys=True)
    assert "private-tenant" not in serialized
    assert "record-12345" not in serialized
    assert "endpoint_host" not in serialized
    assert "endpoint_path" not in serialized
    assert exported["proposals"][0]["capability"]["provider"] == "api.example.org"

    private_request = {
        "description": "retrieve an internal calibration registry",
        "provider": "registry.internal",
    }
    private = record_coverage_observation(
        private_request,
        resolve_capability(_Registry(), private_request),
        public_summary="Internal calibration registry for research workflows",
        workspace=tmp_path,
    )
    with pytest.raises(VSDDemandError, match="not safe for public export"):
        export_proposals(
            [private["data"]["demand"]["demand_id"]],
            tmp_path / "unsafe-proposal.json",
            reviewed_by="VSD Maintainer",
            decision_note="Testing rejection of an internal provider identifier.",
            workspace=tmp_path,
        )


@pytest.mark.parametrize(
    "summary",
    [
        "Contact maintainer@example.org about this missing research API",
        "Review https://private.example.org/source for this capability",
        "Research source with api_key=do-not-store-this credential",
        "Research source with Authorization Bearer private-token-value",
    ],
)
def test_sensitive_public_summaries_are_rejected(tmp_path, summary):
    with pytest.raises(VSDDemandError, match="must not contain"):
        record_coverage_observation(
            MISSING_REQUEST,
            _missing_coverage(),
            public_summary=summary,
            workspace=tmp_path,
        )
    assert not (tmp_path / "demand_ledger.json").exists()


def test_mismatched_coverage_and_tampered_ledger_fail_closed(tmp_path):
    other_request = {"description": "a different missing capability"}
    with pytest.raises(VSDDemandError, match="does not match"):
        record_coverage_observation(
            other_request,
            _missing_coverage(),
            public_summary="Different missing capability for a research workflow",
            workspace=tmp_path,
        )

    _record_missing(tmp_path)
    path = tmp_path / "demand_ledger.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    record = next(iter(ledger["records"].values()))
    record["observation_counts"]["missing"] = 500
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(VSDDemandError, match="integrity digest"):
        rank_demands(workspace=tmp_path)


def test_exact_only_demand_cannot_be_exported(tmp_path):
    request = _exact_request()
    result = observe_capability_demand(
        _Registry([_existing_tool()]),
        request,
        public_summary="Reviewed disease registry lookup by disease identifier",
        workspace=tmp_path,
    )
    with pytest.raises(VSDDemandError, match="no unmet observations"):
        export_proposals(
            [result["data"]["demand"]["demand_id"]],
            tmp_path / "proposal.json",
            reviewed_by="VSD Maintainer",
            decision_note="Reviewed the satisfied capability before export attempt.",
            workspace=tmp_path,
        )


def test_export_cannot_replace_private_ledger_files(tmp_path):
    demand_id = _record_missing(tmp_path)["data"]["demand"]["demand_id"]
    with pytest.raises(VSDDemandError, match="must not replace"):
        export_proposals(
            [demand_id],
            tmp_path / "demand_ledger.json",
            reviewed_by="VSD Maintainer",
            decision_note="Reviewed this proposal before testing protected output.",
            workspace=tmp_path,
            replace=True,
        )
    assert rank_demands(workspace=tmp_path)["data"]["total_demand_count"] == 1


def test_source_cardinality_is_bounded_without_corrupting_ledger(tmp_path):
    for index in range(20):
        record_coverage_observation(
            MISSING_REQUEST,
            _missing_coverage(),
            public_summary=MISSING_SUMMARY,
            source=f"source_{index:02d}",
            event_id=f"event-{index}",
            workspace=tmp_path,
        )
    with pytest.raises(VSDDemandError, match="20-source limit"):
        record_coverage_observation(
            MISSING_REQUEST,
            _missing_coverage(),
            public_summary=MISSING_SUMMARY,
            source="source_20",
            event_id="event-20",
            workspace=tmp_path,
        )
    demand = rank_demands(workspace=tmp_path)["data"]["ranked_demands"][0]
    assert demand["total_observations"] == 20
    assert len(demand["source_counts"]) == 20


def test_out_of_order_observations_preserve_timestamp_bounds(tmp_path):
    _record_missing(
        tmp_path,
        event_id="later",
        observed_at="2026-08-05T12:00:00+00:00",
    )
    _record_missing(
        tmp_path,
        event_id="earlier",
        observed_at="2026-08-01T12:00:00+00:00",
    )
    demand = rank_demands(workspace=tmp_path)["data"]["ranked_demands"][0]
    assert demand["first_observed_at"] == "2026-08-01T12:00:00+00:00"
    assert demand["last_observed_at"] == "2026-08-05T12:00:00+00:00"


def test_remove_requires_confirmation_and_preserves_integrity(tmp_path):
    demand_id = _record_missing(tmp_path)["data"]["demand"]["demand_id"]
    with pytest.raises(VSDDemandError, match="confirm=True"):
        remove_demand(demand_id, workspace=tmp_path)
    removed = remove_demand(demand_id, workspace=tmp_path, confirm=True)
    assert removed["data"]["removed"] is True
    assert rank_demands(workspace=tmp_path)["data"]["total_demand_count"] == 0


def test_hash_bound_workflow_plan_is_recorded_atomically_and_deduplicated(tmp_path):
    plan = plan_workflow(
        _Registry([_existing_tool()]),
        goal="Build a registry and quantitative microscopy evidence workflow",
        capabilities=[
            {
                "step_id": "registry",
                "description": "retrieve disease registry records",
                "operation_id": "registry.search_diseases",
            },
            {
                "step_id": "calibration",
                **MISSING_REQUEST,
                "depends_on": ["registry"],
            },
            {
                "step_id": "synthesis",
                "description": "synthesize the reviewed evidence package",
                "fulfillment": "agent",
                "depends_on": ["registry", "calibration"],
            },
        ],
    )
    summaries = {"calibration": MISSING_SUMMARY}

    first = record_plan_demands(plan, summaries, workspace=tmp_path)
    duplicate = record_plan_demands(plan, summaries, workspace=tmp_path)
    second_run = record_plan_demands(
        plan, summaries, workspace=tmp_path, run_id="scheduled-run-002"
    )

    assert first["data"]["selected_step_count"] == 1
    assert first["data"]["recorded_count"] == 1
    assert duplicate["data"]["deduplicated_count"] == 1
    assert second_run["data"]["recorded_count"] == 1
    ranked = rank_demands(workspace=tmp_path)["data"]["ranked_demands"]
    assert ranked[0]["observation_counts"]["missing"] == 2
    ledger_text = (tmp_path / "demand_ledger.json").read_text(encoding="utf-8")
    assert MISSING_REQUEST["description"] not in ledger_text
    assert "scheduled-run-002" not in ledger_text


def test_plan_batch_fails_before_writing_when_summary_is_missing_or_hash_is_tampered(
    tmp_path,
):
    plan = plan_workflow(
        _Registry([_existing_tool()]),
        goal="Build a registry investigator and calibration workflow",
        capabilities=[
            {
                "step_id": "contacts",
                "description": "retrieve registry investigator contacts",
                "provider": "registry.example.org",
                "required_inputs": ["investigator_id"],
            },
            {"step_id": "calibration", **MISSING_REQUEST},
        ],
    )
    with pytest.raises(VSDDemandError, match="required for steps"):
        record_plan_demands(
            plan,
            {"calibration": MISSING_SUMMARY},
            workspace=tmp_path,
        )
    assert not (tmp_path / "demand_ledger.json").exists()

    tampered = copy.deepcopy(plan)
    tampered["data"]["steps"][0]["classification"] = "missing"
    with pytest.raises(VSDDemandError, match="Plan identity"):
        record_plan_demands(
            tampered,
            {
                "contacts": "Registry investigator contacts for evidence review",
                "calibration": MISSING_SUMMARY,
            },
            workspace=tmp_path,
        )
    assert not (tmp_path / "demand_ledger.json").exists()


def test_concurrent_process_observations_do_not_lose_counts(tmp_path):
    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    processes = [
        context.Process(
            target=_concurrent_record_worker,
            args=(str(tmp_path), f"worker-{index}", results),
        )
        for index in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)

    outcomes = [results.get(timeout=2) for _ in processes]
    assert outcomes == [(True, None), (True, None)]
    assert [process.exitcode for process in processes] == [0, 0]
    demand = rank_demands(workspace=tmp_path)["data"]["ranked_demands"][0]
    assert demand["total_observations"] == 2
    assert demand["observation_counts"]["missing"] == 2
