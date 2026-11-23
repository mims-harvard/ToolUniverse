"""The seven MCPAutoLoaderTool loaders that declared no input and no output.

`MCPAutoLoaderTool.run` reads exactly one required key, `operation`, and raises
`ValueError("Unsupported operation: None")` without it. Seven loaders shipped a
`parameter` block with no properties at all, so:

  * the agent was never told that `operation` exists;
  * `build_tools.py` generated an SDK wrapper that hard-coded ``"arguments": {}``
    and documented "No parameters", which cannot make a successful call;
  * `test_examples` was ``[{}]`` -- a value `tu info` prints as the usage example
    and `tu test` executes.

Six of the seven also carried the placeholder return_schema, which accepts every
payload in the fixture, reachable or not, and so could never fail.

These tests read the shipped JSON rather than `all_tool_dict`: every one of these
loaders needs a ``*_MCP_SERVER_HOST`` to load, so in a keyless environment the
loader hands back an empty set and every assertion below would pass on nothing.
"""

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
WRAPPERS = REPO / "src" / "tooluniverse" / "tools"
SOURCE = REPO / "src" / "tooluniverse" / "mcp_client_tool.py"
FIXTURE = json.loads(
    (REPO / "tests" / "fixtures" / "mcp_loader_contract.json").read_text(
        encoding="utf-8"
    )
)

PLACEHOLDER = {
    "type": "object",
    "description": "Output of the tool execution.",
    "properties": {},
}
OPERATIONS = ["discover", "generate_configs", "call_tool"]
TARGETS = FIXTURE["loaders"]
WRAPPERED = FIXTURE["wrappers_on_disk"]


def _every_loader():
    found = {}
    for path in sorted(DATA.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for tool in data:
            if isinstance(tool, dict) and tool.get("type") == "MCPAutoLoaderTool":
                found[tool["name"]] = tool
    return found


LOADERS = _every_loader()
ALL_NAMES = sorted(LOADERS)


def test_the_fixture_still_describes_the_repo():
    """A loader added later must not slip past these tests unnoticed."""
    assert LOADERS, "no MCPAutoLoaderTool found at all -- the scan is broken"
    missing = [n for n in TARGETS if n not in LOADERS]
    assert not missing, f"fixture names loaders that no longer exist: {missing}"


@pytest.mark.parametrize("name", ALL_NAMES)
def test_declares_operation_with_the_three_run_handles(name):
    param = LOADERS[name].get("parameter") or {}
    props = param.get("properties") or {}
    assert "operation" in props, (
        f"{name} does not declare `operation`, the one key run() requires; "
        "an agent reading this config cannot call the tool at all"
    )
    assert props["operation"].get("enum") == OPERATIONS, (
        f"{name} declares operation enum {props['operation'].get('enum')!r}, "
        f"but run() branches on exactly {OPERATIONS!r}"
    )
    assert "operation" in (param.get("required") or []), (
        f"{name} leaves `operation` optional, yet run() raises "
        "ValueError('Unsupported operation: None') without it"
    )


@pytest.mark.parametrize("name", ALL_NAMES)
def test_declares_the_two_keys_call_tool_reads(name):
    props = (LOADERS[name].get("parameter") or {}).get("properties") or {}
    for key in ("tool_name", "tool_arguments"):
        assert key in props, f"{name} does not declare `{key}`, which run() reads"
    required = (LOADERS[name].get("parameter") or {}).get("required") or []
    assert "tool_name" not in required, (
        f"{name} marks tool_name globally required, but run() only needs it when "
        "operation is call_tool"
    )


@pytest.mark.parametrize("name", ALL_NAMES)
def test_parameter_block_is_a_valid_schema(name):
    Draft202012Validator.check_schema(LOADERS[name].get("parameter") or {})


@pytest.mark.parametrize("name", ALL_NAMES)
def test_examples_validate_against_their_own_parameter_schema(name):
    """The invariant that makes `[{}]` impossible to ship again."""
    tool = LOADERS[name]
    examples = tool.get("test_examples")
    if not examples:
        pytest.skip(f"{name} ships no test_examples")
    validator = Draft202012Validator(tool.get("parameter") or {})
    for i, example in enumerate(examples):
        errors = sorted(validator.iter_errors(example), key=str)
        assert not errors, (
            f"{name} test_examples[{i}] = {example!r} does not satisfy the tool's "
            f"own parameter schema: {errors[0].message}. `tu info` prints this as "
            f"the usage example and `tu test` runs it."
        )


@pytest.mark.parametrize("name", TARGETS)
def test_return_schema_is_not_the_placeholder(name):
    schema = LOADERS[name].get("return_schema")
    assert schema != PLACEHOLDER, (
        f"{name} still declares the placeholder, which accepts every payload in "
        "tests/fixtures/mcp_loader_contract.json and so can never fail"
    )
    assert schema, f"{name} declares no return_schema at all"
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("name", TARGETS)
def test_return_schema_is_a_union_over_the_three_operations(name):
    schema = LOADERS[name]["return_schema"]
    assert "oneOf" in schema, (
        f"{name} does not declare a union, but run() has three unrelated success shapes"
    )
    assert len(schema["oneOf"]) == 3, (
        f"{name} declares {len(schema['oneOf'])} branches for run()'s three operations"
    )


@pytest.mark.parametrize("name", TARGETS)
@pytest.mark.parametrize("case", sorted(FIXTURE["reachable"]))
def test_accepts_what_run_really_returns(name, case):
    entry = FIXTURE["reachable"][case]
    errors = sorted(
        Draft202012Validator(LOADERS[name]["return_schema"]).iter_errors(
            entry["payload"]
        ),
        key=str,
    )
    assert not errors, (
        f"{name} rejects a return run() really produces ({case}: {entry['why']}): "
        f"{errors[0].message}"
    )


@pytest.mark.parametrize("name", TARGETS)
@pytest.mark.parametrize("case", sorted(FIXTURE["unreachable"]))
def test_rejects_what_run_cannot_return(name, case):
    entry = FIXTURE["unreachable"][case]
    validator = Draft202012Validator(LOADERS[name]["return_schema"])
    assert not validator.is_valid(entry["payload"]), (
        f"{name} accepts a payload run() cannot produce ({case}: {entry['why']}). "
        "A declaration that accepts everything cannot catch anything."
    )


@pytest.mark.parametrize("name", TARGETS)
@pytest.mark.parametrize("case", sorted(FIXTURE["reachable"]))
def test_exactly_one_branch_matches_each_real_return(name, case):
    """oneOf is exclusive, so the branches have to discriminate."""
    payload = FIXTURE["reachable"][case]["payload"]
    schema = LOADERS[name]["return_schema"]
    defs = {"$defs": schema.get("$defs", {})}
    hits = [
        i
        for i, branch in enumerate(schema["oneOf"])
        if Draft202012Validator({**branch, **defs}).is_valid(payload)
    ]
    assert len(hits) == 1, (
        f"{name}: {case} matches branches {hits} -- a real return must match "
        "exactly one, or oneOf rejects it"
    )


@pytest.mark.parametrize("name", WRAPPERED)
def test_the_generated_wrapper_can_make_a_successful_call(name):
    """The wrapper used to hard-code an argument dict run() always rejects."""
    source = (WRAPPERS / f"{name}.py").read_text(encoding="utf-8")
    assert '"arguments": {}' not in source, (
        f"{name}'s wrapper still sends a hard-coded empty argument dict, so every "
        "call through the SDK raises ValueError('Unsupported operation: None')"
    )
    assert re.search(r"^    operation: str,$", source, re.M), (
        f"{name}'s wrapper does not take `operation` as a required parameter"
    )
    assert '"operation": operation,' in source, (
        f"{name}'s wrapper does not forward `operation` to run()"
    )
    assert "No parameters" not in source, (
        f"{name}'s wrapper still documents 'No parameters'"
    )


def test_the_declared_enum_matches_the_branches_in_the_source():
    """Anchor the enum to run(), not to a docstring."""
    source = SOURCE.read_text(encoding="utf-8")
    body = source[source.index("class MCPAutoLoaderTool") :]
    run = body[body.index("def run(self, arguments)") :]
    run = run[: run.index("def __del__")]
    in_source = re.findall(r'operation == "([a-z_]+)"', run)
    assert sorted(in_source) == sorted(OPERATIONS), (
        f"run() branches on {in_source!r} but these tests assert {OPERATIONS!r}; "
        "the code moved and the declarations have to follow"
    )
