from __future__ import annotations

from typing import Any, Dict

from tooluniverse.compose_scripts.harvest_auto_registrar import compose


class FakeToolUniverse:
    def __init__(self) -> None:
        self.invocations: list[Dict[str, Any]] = []

    def run_one_function(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.invocations.append(payload)
        return {"ok": True, "payload": payload}


def test_compose_registers_and_runs_single_candidate():
    tool_universe = FakeToolUniverse()
    calls = {}

    def call_tool(name: str, payload: Dict[str, Any]):
        calls.setdefault(name, []).append(payload)
        if name == "HarvestCandidateTesterTool":
            return {"ok": True, "test": {"status": 200}}
        if name == "VerifiedSourceRegisterTool":
            assert payload["tool_name"] == "my_registered_tool"
            return {
                "registered": True,
                "name": payload["tool_name"],
                "config": {"endpoint": "https://example.com"},
            }
        raise AssertionError(f"Unexpected tool call: {name}")

    candidate = {
        "name": "Example API",
        "host": "example.com",
        "endpoint": "https://example.com/api",
    }

    result = compose(
        {
            "candidates": [candidate],
            "tool_name": "my_registered_tool",
            "auto_run": True,
            "tool_arguments": {"limit": 1},
        },
        tool_universe,
        call_tool,
    )

    assert result["ok"] is True
    assert result["registered_tool_name"] == "my_registered_tool"
    assert result["registration"]["registered"] is True
    assert tool_universe.invocations[0]["name"] == "my_registered_tool"
    assert tool_universe.invocations[0]["arguments"] == {"limit": 1}
    assert calls["HarvestCandidateTesterTool"][0]["candidate"] == candidate


def test_compose_generates_name_and_skips_failed_candidate():
    tool_universe = FakeToolUniverse()
    register_tool_names = []

    def call_tool(name: str, payload: Dict[str, Any]):
        if name == "HarvestCandidateTesterTool":
            ok = payload["candidate"]["host"] == "second.example.com"
            return {"ok": ok, "test": {"status": 200 if ok else 500}}
        if name == "VerifiedSourceRegisterTool":
            register_tool_names.append(payload["tool_name"])
            return {"registered": True, "name": payload["tool_name"], "config": {}}
        if name == "GenericHarvestTool":
            return {"ok": True, "candidates": []}
        raise AssertionError(f"Unexpected tool call: {name}")

    first = {
        "name": "Bad API",
        "host": "bad.example.com",
        "endpoint": "https://bad.example.com",
    }
    second = {
        "name": "Good API",
        "host": "second.example.com",
        "endpoint": "https://second.example.com",
    }

    result = compose(
        {
            "candidates": [first, second],
            "auto_run": False,
        },
        tool_universe,
        call_tool,
    )

    assert result["ok"] is True
    assert result["registered_tool_name"] == register_tool_names[0]
    assert register_tool_names[0].startswith("second_example_com_")
    assert result["attempts"][0]["status"] == "tester_failed"
    assert result["attempts"][1]["status"] == "registered"
    assert tool_universe.invocations == []
