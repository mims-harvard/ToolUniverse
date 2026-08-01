from __future__ import annotations

import json

import pytest

from tooluniverse import vsd_source_intelligence_cli as cli

pytestmark = pytest.mark.unit


class _EmptyToolUniverse:
    tool_files = {}
    all_tools = []

    def close(self):
        return None


def test_catalog_and_coverage_commands_are_machine_readable(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_tool_context", _EmptyToolUniverse)
    assert cli.main(["catalog"]) == 0
    catalog = json.loads(capsys.readouterr().out)
    assert len(catalog["sources"]) == 50
    assert catalog["execution_allowed"] is False

    assert cli.main(["coverage"]) == 0
    coverage = json.loads(capsys.readouterr().out)
    assert coverage["catalog_source_count"] == 50
    assert coverage["candidate_gap_count"] == 50


def test_handoff_parser_does_not_imply_consent():
    namespace = cli.build_parser().parse_args(
        [
            "handoff",
            "handoff.json",
            "scan.json",
            "--candidate-id",
            "0" * 16,
            "--reviewed-by",
            "VSD Maintainer",
            "--decision-note",
            "Review the selected candidate before any promotion occurs.",
        ]
    )
    assert namespace.consent is False
    assert namespace.replace is False


def test_submit_parser_does_not_imply_confirmation():
    namespace = cli.build_parser().parse_args(["submit", "handoff.json"])
    assert namespace.confirm is False
