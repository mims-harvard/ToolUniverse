from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from tooluniverse import vsd_continuous_scanner_cli as cli


def test_parser_exposes_bounded_run_options(tmp_path: Path):
    args = cli.build_parser().parse_args(
        [
            "--state-directory",
            str(tmp_path),
            "run",
            "--max-contracts",
            "25",
            "--draftable-tool-target",
            "300",
        ]
    )
    assert args.command == "run"
    assert args.catalog == "apis-guru"
    assert args.max_contracts == 25
    assert args.draftable_tool_target == 300


def test_status_reports_empty_state(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(cli, "load_latest_continuous_scan", lambda _path: None)
    result = cli._execute(Namespace(command="status", state_directory=tmp_path))
    assert result == {
        "status": "empty",
        "state_directory": str(tmp_path),
        "latest": None,
    }


def test_run_closes_tooluniverse_and_returns_summary(monkeypatch, tmp_path: Path):
    closed = []

    class FakeToolUniverse:
        def close(self):
            closed.append(True)

    cycle = {"cycle_id": "cycle"}
    monkeypatch.setattr(cli, "ToolUniverse", FakeToolUniverse)
    monkeypatch.setattr(
        cli,
        "run_scheduled_apis_guru_scan",
        lambda *_args, **_kwargs: {
            "cycle": cycle,
            "history_file": "history.json",
            "latest_file": "latest.json",
            "snapshot_directory": "contracts",
        },
    )
    monkeypatch.setattr(cli, "summarize_continuous_scan", lambda value: value)
    result = cli._execute(
        Namespace(
            command="run",
            catalog="apis-guru",
            state_directory=tmp_path,
            max_contracts=10,
            draftable_tool_target=30,
            timeout=5,
            max_contract_bytes=100_000,
        )
    )
    assert closed == [True]
    assert result["summary"] == cycle
    assert result["history_file"] == "history.json"
