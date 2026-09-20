"""scripts/check_skill_tool_calls.py flags wrong tool calls in skill markdown."""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SPEC = importlib.util.spec_from_file_location(
    "check_skill_tool_calls",
    Path(__file__).parent.parent.parent / "scripts" / "check_skill_tool_calls.py",
)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)

SCHEMAS = {
    "Foo_search": ({"query", "limit"}, {"query"}),
    "Foo_get": ({"foo_id"}, {"foo_id"}),
    "Foo_list": ({"page"}, set()),
}


def _md(code):
    return "text\n\n```python\n" + code + "\n```\n"


def _check(code):
    return checker.check_markdown(_md(code), SCHEMAS)


def test_valid_call_passes():
    assert _check('tu.tools.Foo_search(query="x", limit=3)') == []


def test_unknown_argument_is_reported():
    (problem,) = _check('tu.tools.Foo_search(query="x", size=3)')
    assert "Foo_search" in problem and "'size'" in problem


def test_missing_required_argument_is_reported():
    (problem,) = _check("tu.tools.Foo_get()")
    assert "missing_required=['foo_id']" in problem


def test_nonexistent_tool_is_reported_only_for_a_known_prefix():
    assert _check("tu.tools.Foo_delete(x=1)") == ["Foo_delete: no such tool"]
    assert _check("tu.tools.Zzz_delete(x=1)") == []  # prefix not shared by 2+ tools


def test_wrapper_options_are_not_tool_arguments():
    assert _check('tu.tools.Foo_search(query="x", use_cache=True)') == []


def test_splat_arguments_skip_the_required_check():
    assert _check("tu.tools.Foo_get(**params)") == []


def test_positional_calls_are_skipped():
    assert _check('tu.tools.Foo_search("x")') == []


def test_wrong_usage_examples_are_suppressed():
    assert _check("# WRONG - rejected\ntu.tools.Foo_search(query='x', size=3)") == []
    assert _check("# ❌ bad\ntu.tools.Foo_search(query='x', size=3)") == []
    assert _check("tu.tools.Foo_search(query='x', size=3)  # noqa: skill-call") == []
    assert _check("# noqa: skill-call\ntu.tools.Foo_search(query='x', size=3)") == []


def test_cli_json_form_is_checked():
    (problem,) = _check("""tu run Foo_search '{"query": "x", "bogus": 1}'""")
    assert "'bogus'" in problem


def test_dict_form_is_checked():
    (problem,) = _check("tu.run({'name': 'Foo_get', 'arguments': {'foo': 'x'}})")
    assert "'foo'" in problem and "missing_required=['foo_id']" in problem


def test_calls_outside_code_fences_are_ignored():
    assert checker.check_markdown("prose tools.Foo_get() and more", SCHEMAS) == []


def test_real_schemas_load():
    schemas = checker.load_schemas()
    assert len(schemas) > 2000
    props, required = schemas["ChEMBL_search_activities"]
    assert "target_chembl_id" in props and "target_chembl_id__exact" not in props


def test_nonexistent_tool_is_reported_in_cli_and_dict_forms_too():
    assert _check("""tu run Foo_delete '{"x": 1}'""") == ["Foo_delete: no such tool"]
    assert _check("tu.run({'name': 'Foo_delete', 'arguments': {'x': 1}})") == [
        "Foo_delete: no such tool"
    ]
    assert _check("tu.run({'name': 'Alice_smith', 'arguments': {'x': 1}})") == []
