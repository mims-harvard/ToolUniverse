"""``return_all_loaded_tools`` must offer a read-only path that does not copy.

The deep copy exists so callers cannot modify the live catalogue. It also walks every
tool's parameter schema, which costs hundreds of milliseconds once the catalogue holds a
few thousand tools -- and request paths that only read the configurations were paying it
on every call. ``copy_tools=False`` is that read-only path.

These tests pin both halves of the contract: the default still isolates the caller, and
the opt-out shares the tool dictionaries while still handing back a list the caller may
safely mutate.
"""

from tooluniverse import ToolUniverse


def _engine_with_two_tools():
    tu = ToolUniverse()
    tu.all_tools = [
        {"name": "alpha", "parameter": {"properties": {"x": {"type": "string"}}}},
        {"name": "beta", "parameter": {"properties": {"y": {"type": "integer"}}}},
    ]
    return tu


def test_default_returns_an_isolated_deep_copy():
    tu = _engine_with_two_tools()
    copied = tu.return_all_loaded_tools()

    assert copied == tu.all_tools
    assert copied is not tu.all_tools
    assert copied[0] is not tu.all_tools[0]

    copied[0]["parameter"]["properties"]["x"]["type"] = "mutated"
    assert tu.all_tools[0]["parameter"]["properties"]["x"]["type"] == "string"


def test_copy_tools_false_shares_the_configurations():
    tu = _engine_with_two_tools()
    shared = tu.return_all_loaded_tools(copy_tools=False)

    assert shared == tu.all_tools
    assert all(a is b for a, b in zip(shared, tu.all_tools))


def test_copy_tools_false_still_returns_a_list_the_caller_may_mutate():
    # ToolFinderKeyword extends the returned list with the api-key-gated tools, so
    # handing back the live list itself would grow the catalogue on every search.
    tu = _engine_with_two_tools()
    shared = tu.return_all_loaded_tools(copy_tools=False)

    assert shared is not tu.all_tools
    shared.append({"name": "gated"})
    assert len(tu.all_tools) == 2
