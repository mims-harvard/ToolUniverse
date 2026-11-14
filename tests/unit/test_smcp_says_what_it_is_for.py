"""The MCP host must be told what this server is for.

Filed as #875. FastMCP's `instructions` is the one piece of text an MCP host
puts verbatim into the model's context when a session opens. SMCP passed only
`name`, so that text was empty:

    super().__init__(name=name or "SMCP Server", **fastmcp_kwargs)

and `grep -rn "instructions=" src/tooluniverse/` returned nothing, so no entry
point supplied one either. With deferred tools -- Claude Code lists MCP tools
by name only -- the model saw `find_tools`, `grep_tools`, `execute_tool` and
nothing saying those names lead to genes, drugs, trials or variants.

The text is derived rather than written down, so it stays true as the
catalogue grows and as a deployment's own category filters narrow it.
"""

import pytest

from tooluniverse.smcp import SMCP


@pytest.fixture(scope="module")
def server():
    return SMCP(name="probe", tool_categories=["uniprot"], compact_mode=True)


def test_the_host_is_told_something(server):
    assert server.instructions, "FastMCP instructions is what the host shows the model"
    assert len(server.instructions) > 80


def test_it_names_the_entry_points_that_exist(server):
    registered = set(server._exposed_tools)
    if getattr(server, "_find_tools_registered", False):
        registered.add("find_tools")
    named = {
        name
        for name in (
            "find_tools",
            "list_tools",
            "grep_tools",
            "get_tool_info",
            "execute_tool",
        )
        if name in server.instructions
    }
    assert named, "the instructions name no entry point at all"
    assert named <= registered, (
        f"the instructions advertise entry points this server does not register: "
        f"{sorted(named - registered)}"
    )


def test_it_names_a_subject_area_a_caller_would_search_for(server):
    assert "uniprot" in server.instructions.lower()


def test_it_does_not_offer_this_server_s_plumbing_as_a_subject(server):
    lowered = server.instructions.lower()
    for plumbing in ("compact_mode", "tool_finder"):
        assert plumbing not in lowered, (
            f"{plumbing} is this server's own machinery, not a database to search"
        )


def test_a_caller_supplied_value_is_left_alone():
    chosen = "This deployment serves one lab and nothing else."
    server = SMCP(
        name="probe",
        tooluniverse_config={},
        auto_expose_tools=False,
        search_enabled=False,
        instructions=chosen,
    )
    assert server.instructions == chosen


def test_a_server_with_nothing_loaded_still_says_what_it_is():
    server = SMCP(
        name="probe",
        tooluniverse_config={},
        auto_expose_tools=False,
        search_enabled=False,
    )
    assert server.instructions
    assert "tooluniverse" in server.instructions.lower()
