"""``load_tools(categories=...)`` returns only the requested categories.

Built-in tools that also register a config with ``@register_tool(config=...)``
(GTEx, WikiPathways, IUPred3, ...) were appended after the category filter, so
``load_tools(categories=["opennih"])`` returned GTEx tools whenever gtex_tool
had been imported earlier in the process. Decorator configs from user modules
have no JSON category and must still load.
"""

import ast
import json
from pathlib import Path

import pytest

from tooluniverse import ToolUniverse
from tooluniverse import tool_registry
from tooluniverse.base_tool import BaseTool
from tooluniverse.execute_function import default_tool_files

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "tooluniverse"


@pytest.fixture
def gtex_imported():
    import tooluniverse.gtex_tool  # noqa: F401  (registers decorator configs)

    assert "GTExExpressionTool" in tool_registry.get_config_registry()


def _names(tu):
    return set(tu.all_tool_dict)


def _built_in_json_names():
    names = set()
    for path in default_tool_files.values():
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, list):
            names.update(t.get("name") for t in data if isinstance(t, dict))
    return names


def test_category_filter_excludes_decorator_configs_of_other_categories(gtex_imported):
    tu = ToolUniverse()
    tu.load_tools(categories=["opennih"])

    # Only built-in tools are checked: decorator tools registered in-process by
    # user code (or other tests) have no category and load regardless.
    other_built_in = (_built_in_json_names() & _names(tu)) - {
        name for name in _names(tu) if name.startswith("OpenNIH_")
    }
    assert any(name.startswith("OpenNIH_") for name in _names(tu))
    assert not other_built_in, sorted(other_built_in)


def test_requested_category_still_loads_its_decorator_registered_tools(gtex_imported):
    tu = ToolUniverse()
    tu.load_tools(categories=["gtex"])

    assert {"GTEx_get_expression_summary", "GTEx_query_eqtl"} <= _names(tu)


def test_exclude_categories_is_not_undone_by_decorator_configs(gtex_imported):
    tu = ToolUniverse()
    tu.load_tools(categories=["opennih", "gtex"], exclude_categories=["gtex"])

    assert not any(name.startswith("GTEx_") for name in _names(tu))


def test_user_decorator_config_still_loads_under_a_category_filter():
    name = "ZZTestUserDecoratorTool"

    @tool_registry.register_tool(
        name,
        config={
            "name": "zz_user_decorator_tool",
            "description": "test tool",
            "parameter": {"type": "object", "properties": {}},
        },
    )
    class _UserTool(BaseTool):
        def run(self, arguments):
            return {"status": "success"}

    try:
        tu = ToolUniverse()
        tu.load_tools(categories=["opennih"])
        assert "zz_user_decorator_tool" in _names(tu)
    finally:
        tool_registry._tool_registry.pop(name, None)
        tool_registry._config_registry.pop(name, None)


def _decorator_config_names():
    names = set()
    for path in SRC.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "@register_tool" not in text or "config=" not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if not (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "register_tool"
            ):
                continue
            for kw in node.keywords:
                if kw.arg == "config" and isinstance(kw.value, ast.Dict):
                    for key, value in zip(kw.value.keys, kw.value.values):
                        if (
                            isinstance(key, ast.Constant)
                            and key.value == "name"
                            and isinstance(value, ast.Constant)
                        ):
                            names.add(value.value)
    return names


def test_every_built_in_decorator_config_has_a_json_category():
    """A filtered load skips built-in decorator configs in favour of their JSON
    entry, so a built-in decorator tool without one could never be loaded by
    category."""
    json_names = _built_in_json_names()
    decorator_names = _decorator_config_names()
    assert decorator_names
    assert decorator_names <= json_names, sorted(decorator_names - json_names)
