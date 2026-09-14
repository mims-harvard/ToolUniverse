"""Compatible upstream drift keeps a tool working without widening its surface.

Refusing every changed tool turned a vendor's documentation edit into an outage
for users who cannot review a third-party schema. Accepting the live schema
would let a server add a field the agent then fills in. These cover both
halves: the tool stays up, and what the agent may send does not change.
"""

import copy

import pytest

from tooluniverse.mcp_client_tool import MCPAutoLoaderTool
from tooluniverse.mcp_contract_compat import classify, pinned_tool_from_reviewed

pytestmark = pytest.mark.unit


REVIEWED = {
    "name": "reviewed_tool",
    "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "original"}},
        "required": ["query"],
    },
    "outputSchema": {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
    },
}


def _live(**mutations):
    live = copy.deepcopy(REVIEWED)
    for path, value in mutations.items():
        if path == "add_optional":
            live["inputSchema"]["properties"][value] = {"type": "string"}
        elif path == "add_required":
            live["inputSchema"]["properties"][value] = {"type": "string"}
            live["inputSchema"]["required"] = ["query", value]
        elif path == "redescribe":
            live["inputSchema"]["properties"]["query"]["description"] = value
        elif path == "retype":
            live["inputSchema"]["properties"]["query"]["type"] = value
    return live


@pytest.mark.parametrize(
    ("label", "live", "expected"),
    [
        ("identical", _live(), True),
        ("description reworded", _live(redescribe="rewritten upstream"), True),
        ("new optional field", _live(add_optional="hint"), True),
        ("new required field", _live(add_required="objective"), False),
        ("type changed", _live(retype="number"), False),
    ],
)
def test_only_call_preserving_drift_is_tolerated(label, live, expected):
    tolerable, reasons = classify(REVIEWED, live)
    assert tolerable is expected, f"{label}: {reasons}"


def test_a_newly_required_field_is_refused_because_reviewed_calls_would_fail():
    """The real Exa incident: `objective` became required, so calls 400."""
    tolerable, reasons = classify(REVIEWED, _live(add_required="objective"))
    assert tolerable is False
    assert any("objective" in reason and "required" in reason for reason in reasons)


def test_missing_reviewed_contract_is_never_assumed_safe():
    """Without a recorded schema there is nothing to compare against."""
    tolerable, reasons = classify(None, _live(redescribe="anything"))
    assert tolerable is False
    assert reasons == ["contract changed, and no reviewed schema is recorded"]


def test_tolerated_drift_does_not_expose_the_field_the_server_added():
    """The safety property: the agent only ever sees the reviewed parameters.

    An agent fills in whatever a server advertises, so exposing the live schema
    would turn an added free-text field into an unreviewed way for data to
    leave the session.
    """
    live = _live(add_optional="context")
    assert classify(REVIEWED, live)[0] is True

    pinned = pinned_tool_from_reviewed(REVIEWED, live)

    assert "context" not in pinned["inputSchema"]["properties"]
    assert set(pinned["inputSchema"]["properties"]) == {"query"}


def test_tolerated_drift_keeps_the_live_output_schema():
    """Output is validated against what the server actually returns."""
    live = _live(add_optional="hint")
    live["outputSchema"] = {
        "type": "object",
        "properties": {"answer": {"type": "string"}, "score": {"type": "number"}},
        "required": ["answer"],
    }
    pinned = pinned_tool_from_reviewed(REVIEWED, live)
    assert "score" in pinned["outputSchema"]["properties"]


def _loader_config(**overrides):
    config = {
        "name": "probe_loader",
        "description": "probe",
        "type": "MCPAutoLoaderTool",
        "server_url": "https://example.test/mcp",
        "tool_prefix": "p_",
        "selected_tools": ["reviewed_tool"],
        "tool_contracts": [
            {
                "name": "reviewed_tool",
                "description": "Locally reviewed description.",
                "contract_sha256": MCPAutoLoaderTool._contract_sha256(REVIEWED),
            }
        ],
        "strict_tool_contracts": True,
    }
    config.update(overrides)
    return config


def test_loader_keeps_a_compatibly_drifted_tool_on_the_reviewed_schema(monkeypatch):
    """End to end: the tool stays registered, still advertising only `query`."""
    monkeypatch.setattr(
        "tooluniverse.mcp_client_tool.load_reviewed_contracts",
        lambda name: {"reviewed_tool": copy.deepcopy(REVIEWED)},
    )
    loader = MCPAutoLoaderTool(_loader_config())
    live = _live(add_optional="context", redescribe="upstream rewrote this")

    pinned = loader._verify_and_pin_contracts({"reviewed_tool": live})

    assert set(pinned) == {"reviewed_tool"}
    assert set(pinned["reviewed_tool"]["inputSchema"]["properties"]) == {"query"}
    configs = []
    loader._discovered_tools = pinned
    configs = loader.generate_proxy_tool_configs()
    assert set(configs[0]["parameter"]["properties"]) == {"query"}


def test_loader_still_refuses_a_tool_whose_reviewed_call_would_break(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.mcp_client_tool.load_reviewed_contracts",
        lambda name: {"reviewed_tool": copy.deepcopy(REVIEWED)},
    )
    loader = MCPAutoLoaderTool(_loader_config())

    with pytest.raises(ValueError, match="objective"):
        loader._verify_and_pin_contracts(
            {"reviewed_tool": _live(add_required="objective")}
        )


def test_without_a_lockfile_entry_drift_still_fails_closed(monkeypatch):
    """Pre-lockfile behaviour is preserved when nothing was recorded."""
    monkeypatch.setattr(
        "tooluniverse.mcp_client_tool.load_reviewed_contracts", lambda name: {}
    )
    loader = MCPAutoLoaderTool(_loader_config())

    with pytest.raises(ValueError, match="no reviewed schema is recorded"):
        loader._verify_and_pin_contracts(
            {"reviewed_tool": _live(redescribe="harmless rewording")}
        )
