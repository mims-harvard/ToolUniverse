"""Tests for USPTO_get_patent_assignment JSON config."""

import json
from pathlib import Path


def _load_uspto_configs():
    config_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "uspto_tools.json"
    )
    with open(config_path) as f:
        return json.load(f)


class TestAssignmentConfig:
    def test_assignment_config_exists(self):
        configs = _load_uspto_configs()
        names = [c["name"] for c in configs]
        assert "USPTO_get_patent_assignment" in names

    def test_assignment_endpoint_is_singular(self):
        configs = _load_uspto_configs()
        assignment = next(
            c for c in configs if c["name"] == "USPTO_get_patent_assignment"
        )
        assert "assignment" in assignment["api_endpoint"]
        assert "assignments" not in assignment["api_endpoint"]

    def test_assignment_requires_application_number(self):
        configs = _load_uspto_configs()
        assignment = next(
            c for c in configs if c["name"] == "USPTO_get_patent_assignment"
        )
        assert "applicationNumberText" in assignment["parameter"]["required"]

    def test_assignment_uses_correct_tool_type(self):
        configs = _load_uspto_configs()
        assignment = next(
            c for c in configs if c["name"] == "USPTO_get_patent_assignment"
        )
        assert assignment["type"] == "USPTOOpenDataPortalTool"
