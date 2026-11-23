"""Eleven tools shipped a generated placeholder `return_schema`.

    {"type": "object", "description": "Output of the tool execution.",
     "properties": {}}

That is not a false statement, it is a VACUOUS one: an object with no required
properties accepts whatever the tool returns and equally accepts anything else,
so no check could ever have failed on it and it told a reader nothing. Three of
the eleven do not even return an object -- the two embedding tool finders and
the LLM one answer a list -- so for those it was false as well.

The shapes here are derived from each tool's own source, which is exhaustive
rather than a lower bound: these classes have a small, enumerable set of
returns. `get_webpage_text_from_url` is the one that could also be run here,
and the fixture marks its measured row.

One trap worth recording. `ToolFinderEmbedding.find_tools` documents its return
as "Tool prompts as a formatted string". It is not a string:
`prepare_tool_prompts` returns a list of tool configs cut to
name/description/parameter/required. A schema written from that docstring would
have declared the wrong root type, which is why these were read from the code.

The payloads come from tests/fixtures/placeholder_return_shapes.json.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
FIXTURE = json.loads(
    (REPO / "tests" / "fixtures" / "placeholder_return_shapes.json").read_text()
)

PLACEHOLDER = {
    "type": "object",
    "description": "Output of the tool execution.",
    "properties": {},
}


def _configs():
    """Read the shipped configs, not ToolUniverse.all_tool_dict.

    Several of these tools are gated on an extra or an API key and would be
    absent from a loaded instance, so the loader would hand back a short set
    and the parametrised tests below would silently cover fewer tools.
    """
    found = {}
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(entries, list):
            continue
        for tool in entries:
            if isinstance(tool, dict) and tool.get("name") in FIXTURE["tools"]:
                found[tool["name"]] = tool
    return found


CONFIGS = _configs()
NAMES = sorted(FIXTURE["tools"])


def _cases(kind):
    out = []
    for name in NAMES:
        for index, case in enumerate(FIXTURE["tools"][name][kind]):
            out.append((name, index, case))
    return out


REACHABLE = _cases("reachable")
UNREACHABLE = _cases("unreachable")


def _ids(rows):
    return [
        f"{name}-{kind}{index}"
        for name, index, kind in [(n, i, c.get("branch", "x")) for n, i, c in rows]
    ]


def _branch_documents(schema):
    documents = []
    for branch in schema["oneOf"]:
        document = dict(branch)
        if "$defs" in schema:
            document["$defs"] = schema["$defs"]
        documents.append(document)
    return documents


def test_the_fixture_and_the_configs_cover_the_same_eleven_tools():
    assert len(NAMES) == 11, NAMES
    missing = sorted(set(NAMES) - set(CONFIGS))
    assert not missing, f"named in the fixture but in no shipped config: {missing}"


@pytest.mark.parametrize("name", NAMES)
def test_no_tool_here_still_ships_the_generated_placeholder(name):
    """An object with no required properties cannot fail, so it says nothing."""
    assert CONFIGS[name].get("return_schema") != PLACEHOLDER, (
        f"{name} still carries the generated placeholder return_schema"
    )


@pytest.mark.parametrize("name", NAMES)
def test_every_schema_is_a_union_because_every_tool_has_a_failure_return(name):
    schema = CONFIGS[name]["return_schema"]
    assert isinstance(schema.get("oneOf"), list) and len(schema["oneOf"]) >= 2, (
        f"{name}: run() has at least a success and a failure return, so a "
        "single-shape return_schema cannot describe both"
    )


@pytest.mark.parametrize("name,index,case", REACHABLE, ids=_ids(REACHABLE))
def test_a_reachable_return_validates_against_exactly_one_branch(name, index, case):
    schema = CONFIGS[name]["return_schema"]
    jsonschema.validate(case["payload"], schema)
    matched = [
        position
        for position, document in enumerate(_branch_documents(schema))
        if jsonschema.Draft202012Validator(document).is_valid(case["payload"])
    ]
    assert len(matched) == 1, (
        f"{name}: {len(matched)} branches matched the {case.get('branch')} "
        f"payload ({matched}). `oneOf` means exactly one, so two matches reject "
        "a return the tool really makes."
    )


@pytest.mark.parametrize("name,index,case", UNREACHABLE, ids=_ids(UNREACHABLE))
def test_a_return_the_tool_cannot_make_is_rejected(name, index, case):
    """Without this the suite could not tell a real declaration from a vacuous one."""
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(case["payload"], CONFIGS[name]["return_schema"])


@pytest.mark.parametrize("name", [n for n in NAMES if n.startswith("embedding_")])
def test_an_embedding_error_carries_no_status_which_is_what_separates_it(name):
    """These handlers return a bare {"error": ...}; the success branch is the
    only one with `status`, and that is the whole discriminator."""
    branches = CONFIGS[name]["return_schema"]["oneOf"]
    success = [b for b in branches if "status" in (b.get("properties") or {})]
    failure = [b for b in branches if "error" in (b.get("required") or [])]
    assert len(success) == 1 and len(failure) == 1, name
    assert success[0]["properties"]["status"].get("const") == "success", name
    assert "status" not in (failure[0].get("properties") or {}), name


@pytest.mark.parametrize("name", ["Tool_RAG", "Tool_Finder", "Tool_Finder_LLM"])
def test_a_finder_answers_an_array_not_an_object(name):
    """`prepare_tool_prompts` returns a list, whatever find_tools' docstring says."""
    branches = CONFIGS[name]["return_schema"]["oneOf"]
    assert any(b.get("type") == "array" for b in branches), (
        f"{name}: no array branch, but find_tools returns "
        "prepare_tool_prompts(...), which is a list of trimmed tool configs"
    )
