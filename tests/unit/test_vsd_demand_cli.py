from __future__ import annotations

import json

import pytest

from tooluniverse import vsd_demand_cli
from tooluniverse.vsd_planning import plan_workflow

pytestmark = pytest.mark.unit


class _EmptyToolUniverse:
    tool_files = {}

    def __init__(self):
        self.all_tools = []
        self.all_tool_dict = {}

    def close(self):
        pass


def test_cli_completes_private_record_rank_export_remove_lifecycle(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(vsd_demand_cli, "ToolUniverse", _EmptyToolUniverse)
    workspace = tmp_path / "demand"
    base = ["--workspace", str(workspace)]
    assert (
        vsd_demand_cli.main(
            base
            + [
                "record",
                "--description",
                "quantum microscope calibration waveform optimizer",
                "--public-summary",
                "Quantitative microscopy calibration for research workflows",
                "--required-inputs",
                "sample_id",
                "--output-fields",
                "calibration_score",
                "--source",
                "scheduled_scan",
                "--event-id",
                "scan-001",
            ]
        )
        == 0
    )
    recorded = json.loads(capsys.readouterr().out)
    demand_id = recorded["data"]["demand"]["demand_id"]

    assert vsd_demand_cli.main(base + ["rank"]) == 0
    ranked = json.loads(capsys.readouterr().out)
    assert ranked["data"]["ranked_demands"][0]["demand_id"] == demand_id

    output = tmp_path / "selected-proposals.json"
    assert (
        vsd_demand_cli.main(
            base
            + [
                "export",
                str(output),
                "--demand-id",
                demand_id,
                "--reviewed-by",
                "VSD Maintainer",
                "--decision-note",
                "Selected after reviewing the local unmet-demand aggregate.",
            ]
        )
        == 0
    )
    exported = json.loads(capsys.readouterr().out)
    assert exported["data"]["transmission"].startswith("none;")
    assert output.exists()

    assert vsd_demand_cli.main(base + ["remove", demand_id, "--confirm"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["data"]["removed"] is True
    assert vsd_demand_cli.main(base + ["rank"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["total_demand_count"] == 0


def test_cli_records_complete_hash_bound_plan_batch(tmp_path, capsys):
    plan = plan_workflow(
        _EmptyToolUniverse(),
        goal="Build a quantitative microscopy calibration workflow",
        capabilities=[
            {
                "step_id": "calibration",
                "description": "quantum microscope calibration waveform optimizer",
            }
        ],
    )
    plan_file = tmp_path / "plan.json"
    summaries_file = tmp_path / "summaries.json"
    plan_file.write_text(json.dumps(plan), encoding="utf-8")
    summaries_file.write_text(
        json.dumps(
            {
                "calibration": (
                    "Quantitative microscopy calibration for research workflows"
                )
            }
        ),
        encoding="utf-8",
    )
    base = ["--workspace", str(tmp_path / "demand")]

    assert (
        vsd_demand_cli.main(
            base
            + [
                "record-plan",
                str(plan_file),
                str(summaries_file),
                "--source",
                "scheduled_scan",
                "--run-id",
                "batch-001",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["data"]["selected_step_count"] == 1
    assert result["data"]["recorded_count"] == 1
