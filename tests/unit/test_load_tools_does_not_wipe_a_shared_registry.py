"""Narrowing someone else's tool registry must say whether it replaces it.

``load_tools()`` resolves ``clear_existing`` to True when no ``include_tools``
and no ``tools_file`` are given (execute_function.py), so a call that narrows
the load -- ``categories=``, ``tool_type=``, ``include_tool_types=`` -- replaces
the registry with that subset. On a universe the caller owns that is harmless.
On a universe the caller was handed it removes every tool somebody else loaded.

Two call sites did exactly that, and both were reached from an ordinary tool
call rather than from setup:

    compose_tool.py   load_tools(tool_type=[category])  when a dependency
                      looked missing -- 2,743 tools became 14
    output_hook.py    load_tools(tools_to_load)         when hook tools were
                      auto-loaded -- 2,743 tools became 1

The second is the reason this is written as an invariant over the source rather
than as two regression tests. The first was reported from the field (#845); the
second was found by asking what else had the same shape, and nothing in the
test suite would have objected to a third.

The rule is deliberately about ownership, not about the keyword: a locally
constructed ``ToolUniverse()`` is the caller's own and may be loaded however it
likes, while ``self.tooluniverse.load_tools(...)`` is narrowing a registry that
arrived from outside. ``smcp.py`` already passes ``clear_existing`` explicitly
and documents which behaviour it means -- that is the standard here.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src" / "tooluniverse"
NARROWING = {"categories", "tool_type", "include_tool_types"}


def _narrowing_call(node: ast.Call) -> bool:
    """A call that loads a subset: a positional argument (which binds to
    ``categories``) or one of the narrowing keywords."""
    if node.args:
        return True
    for kw in node.keywords:
        if kw.arg not in NARROWING:
            continue
        # `tool_type=None` is an explicit "do not narrow", and in the AST that
        # is a Constant node rather than Python's None -- checking the node for
        # None instead of its value flags the opposite of the hazard.
        if isinstance(kw.value, ast.Constant) and kw.value.value is None:
            continue
        return True
    return False


def _offenders():
    out = []
    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute) or func.attr != "load_tools":
                continue
            # a registry reached through another object is not ours to replace;
            # `tu.load_tools()` on a local `tu = ToolUniverse()` is
            if not isinstance(func.value, ast.Attribute):
                continue
            if not _narrowing_call(node):
                continue
            if any(kw.arg == "clear_existing" for kw in node.keywords):
                continue
            out.append((path.relative_to(SRC.parent.parent), node.lineno))
    return out


def test_no_call_narrows_a_borrowed_registry_without_saying_so():
    offenders = _offenders()
    assert not offenders, (
        "these calls narrow a tool registry they did not create, without "
        "stating clear_existing, so they replace it:\n"
        + "\n".join(f"  {p}:{n}" for p, n in offenders)
    )


def test_the_rule_catches_the_shape_it_is_written_for(tmp_path):
    """A rule that matched nothing would pass for the wrong reason."""
    sample = tmp_path / "sample.py"
    sample.write_text(
        "class H:\n"
        "    def go(self, cats):\n"
        "        self.tooluniverse.load_tools(cats)\n"
        "        self.tooluniverse.load_tools(tool_type=['hpa'])\n"
        "        self.tooluniverse.load_tools(cats, clear_existing=False)\n"
        "        tu = ToolUniverse()\n"
        "        tu.load_tools(tool_type=['hpa'])\n"
    )
    tree = ast.parse(sample.read_text())
    flagged = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "load_tools"
            and isinstance(node.func.value, ast.Attribute)
            and _narrowing_call(node)
            and not any(kw.arg == "clear_existing" for kw in node.keywords)
        ):
            flagged.append(node.lineno)
    assert flagged == [3, 4], flagged


@pytest.mark.parametrize(
    "module,call_line_contains",
    [
        ("output_hook.py", "clear_existing=False"),
        ("compose_tool.py", "load_tools("),
    ],
)
def test_the_two_known_sites_are_still_covered(module, call_line_contains):
    """So a later refactor cannot quietly drop the guard at either site."""
    text = (SRC / module).read_text()
    assert "load_tools(" in text, module
    assert call_line_contains in text, module


def test_an_additive_category_load_keeps_what_was_already_there():
    """The structural rule above says the keyword is present; this says the
    keyword does what the call sites rely on.

    Two small categories rather than the whole universe, because the fault is
    in the clearing and not in the size of what gets cleared.
    """
    from tooluniverse import ToolUniverse

    universe = ToolUniverse()
    universe.load_tools(categories=["uniprot"])
    first = set(universe.all_tool_dict)
    assert first, "nothing loaded; this test would pass for the wrong reason"

    universe.load_tools(["output_summarization"], clear_existing=False)
    after_additive = set(universe.all_tool_dict)
    assert first <= after_additive, sorted(first - after_additive)[:5]
    assert len(after_additive) > len(first)

    # and the default really is the destructive one, which is why every
    # borrowed-registry call site has to say so
    universe.load_tools(["output_summarization"])
    after_default = set(universe.all_tool_dict)
    assert not (first <= after_default), (
        "load_tools() narrowing without clear_existing kept the earlier tools; "
        "if that default has changed, the rule above can be relaxed"
    )
