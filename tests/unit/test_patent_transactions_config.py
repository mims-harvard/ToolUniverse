"""Tests for USPTO_get_patent_transactions JSON config."""

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


class TestTransactionsConfig:
    def test_transactions_config_exists(self):
        configs = _load_uspto_configs()
        names = [c["name"] for c in configs]
        assert "USPTO_get_patent_transactions" in names

    def test_transactions_endpoint_path(self):
        configs = _load_uspto_configs()
        tool = next(c for c in configs if c["name"] == "USPTO_get_patent_transactions")
        assert (
            tool["api_endpoint"]
            == "patent/applications/{applicationNumberText}/transactions"
        )

    def test_transactions_requires_application_number(self):
        configs = _load_uspto_configs()
        tool = next(c for c in configs if c["name"] == "USPTO_get_patent_transactions")
        assert "applicationNumberText" in tool["parameter"]["required"]

    def test_transactions_return_fields_include_events(self):
        configs = _load_uspto_configs()
        tool = next(c for c in configs if c["name"] == "USPTO_get_patent_transactions")
        rf = tool.get("return_fields", [])
        assert "eventDataBag/eventCode" in rf
        assert "eventDataBag/eventDescriptionText" in rf
        assert "eventDataBag/eventDate" in rf
