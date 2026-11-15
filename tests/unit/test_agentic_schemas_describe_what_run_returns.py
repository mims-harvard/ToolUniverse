"""Every AgenticTool's return_schema must describe what AgenticTool.run returns.

`run` does not hand back the model's answer. With `configs.return_metadata` at
its default of true it wraps the answer in ``{"success", "result", "metadata"}``
-- or, on any failure, ``{"success", "error", "error_type", "metadata"}``. Only
the five tools that set ``return_metadata: false`` return the answer itself.

Fifty schemas disagreed with that, in two different ways, and the distinction
matters because only one of them is a false statement:

* 12 schemas REJECTED every return their tool can produce. Five declared
  ``{"type": ["string", "null"]}``, two declared ``"string"``, and five declared
  an object with ``required`` properties -- none of which an envelope satisfies.
* 33 carried the generated placeholder
  ``{"type": "object", "description": "Output of the tool execution.",
  "properties": {}}``. That one is not false, it is VACUOUS: an object with no
  required properties accepts the envelope and equally accepts anything else,
  so it could never have failed and never said anything. It still told a reader
  to expect the payload directly.

The trap underneath all of it: ``configs.return_json`` does not make ``result``
a parsed object. It asks the API for JSON *mode*; ``infer`` is typed
``-> Optional[str]`` and hands the JSON back as text. 23 of the 33 declared
``"type": "object"`` on the opposite assumption, while the project's own
consumers -- compose_scripts/tool_discover.py, tool_description_optimizer.py --
take ``obj["result"]``, check ``isinstance(str)`` and ``json.loads`` it. The
code was right and the declarations were wrong.

So no declaration here narrows ``result`` past what the client guarantees: a
string, or null once ``infer``'s retries are spent. The structure a prompt asks
the model for is carried in ``contentSchema``, which JSON Schema treats as an
annotation and never asserts, or described in prose. A schema that asserted the
prompt's requested keys would be claiming the model complied, which nothing
here measured.

The payloads come from tests/fixtures/agentic_return_envelope.json, derived
from agentic_tool.py, llm_clients.py and utils.py rather than measured: an
AgenticTool is skipped at load time when no LLM API key is present, so no call
could be made. The derivation is exhaustive where a live pass would have been a
lower bound -- ``run`` has six returns and the fixture covers all six.
"""

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"
FIXTURE = json.loads(
    (REPO / "tests" / "fixtures" / "agentic_return_envelope.json").read_text()
)

PLACEHOLDER = {
    "type": "object",
    "description": "Output of the tool execution.",
    "properties": {},
}


def _agentic_tools():
    """Read the shipped configs directly, not ToolUniverse.all_tool_dict.

    An AgenticTool is skipped at load time without an API key, so the loader
    would hand back an empty set here and every test below would pass on
    nothing.
    """
    out = []
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(entries, list):
            continue
        for tool in entries:
            if isinstance(tool, dict) and tool.get("type") == "AgenticTool":
                out.append((path.name, tool))
    return out


TOOLS = _agentic_tools()
WRAPPED = [t for t in TOOLS if (t[1].get("configs") or {}).get("return_metadata", True)]
BARE = [
    t for t in TOOLS if not (t[1].get("configs") or {}).get("return_metadata", True)
]


def _ids(rows):
    return [f"{tool['name']}" for _, tool in rows]


def _cases(group, reachable=True):
    key = "reachable" if reachable else "unreachable"
    return FIXTURE[key][group]


def _branch_documents(schema):
    """Each oneOf branch as a standalone document, so `$ref` still resolves."""
    documents = []
    for branch in schema["oneOf"]:
        document = dict(branch)
        if "$defs" in schema:
            document["$defs"] = schema["$defs"]
        documents.append(document)
    return documents


def test_the_family_is_not_empty_and_splits_the_way_the_docstring_says():
    assert len(TOOLS) >= 50, f"found only {len(TOOLS)} AgenticTool configs"
    assert BARE, (
        "no return_metadata: false tool found; the bare-return cases below would be vacuous"
    )
    assert WRAPPED, "no default-return_metadata tool found"


@pytest.mark.parametrize("named", TOOLS, ids=_ids(TOOLS))
def test_no_agentic_tool_ships_the_generated_placeholder(named):
    """`{"type": "object", "properties": {}}` cannot fail, so it says nothing."""
    _, tool = named
    assert tool.get("return_schema") != PLACEHOLDER, (
        f"{tool['name']} still carries the generated placeholder return_schema. "
        "An object with no required properties accepts every return the tool can "
        "make and every return it cannot, so it can never fail a check."
    )


@pytest.mark.parametrize("named", TOOLS, ids=_ids(TOOLS))
def test_every_return_schema_is_a_union_of_the_branches_run_can_take(named):
    _, tool = named
    schema = tool.get("return_schema")
    assert isinstance(schema, dict) and isinstance(schema.get("oneOf"), list), (
        f"{tool['name']}: run() has a success branch and a failure branch, so a "
        "single-shape return_schema cannot describe both"
    )
    assert len(schema["oneOf"]) >= 2, tool["name"]


@pytest.mark.parametrize("named", WRAPPED, ids=_ids(WRAPPED))
def test_the_two_envelope_branches_discriminate_on_success(named):
    """`oneOf` is exclusive, so the branches must disagree about `success`.

    Without the `const`, an envelope would match both branches on the keys they
    share and `oneOf` would reject it outright.
    """
    _, tool = named
    branches = tool["return_schema"]["oneOf"]
    consts = [
        (branch.get("properties") or {}).get("success", {}).get("const")
        for branch in branches
    ]
    assert sorted(consts, key=str) == [False, True], (
        f"{tool['name']}: branches declare success as {consts}; the success and "
        "failure envelopes are told apart by that one field"
    )


@pytest.mark.parametrize("named", WRAPPED, ids=_ids(WRAPPED))
def test_result_is_the_text_the_client_returns_not_a_parsed_object(named):
    """`infer` is typed `-> Optional[str]`; `return_json` only asks for JSON mode."""
    _, tool = named
    success = next(
        branch
        for branch in tool["return_schema"]["oneOf"]
        if (branch.get("properties") or {}).get("success", {}).get("const") is True
    )
    declared = success["properties"]["result"].get("type")
    assert declared == ["string", "null"], (
        f"{tool['name']}: result is declared {declared!r}. The client hands back "
        "the model's text, or None once its retries are spent -- a parsed object "
        "only when the caller passes response_format, which this tool does not "
        "declare as a parameter."
    )


@pytest.mark.parametrize("named", WRAPPED, ids=_ids(WRAPPED))
def test_a_contentschema_is_an_annotation_and_never_narrows_the_string(named):
    """Carrying the prompt's requested shape must not make the string assertable."""
    _, tool = named
    success = next(
        branch
        for branch in tool["return_schema"]["oneOf"]
        if (branch.get("properties") or {}).get("success", {}).get("const") is True
    )
    result = success["properties"]["result"]
    if "contentSchema" in result:
        assert result.get("contentMediaType") == "application/json", (
            f"{tool['name']}: a contentSchema without contentMediaType describes "
            "the shape of nothing in particular"
        )
        assert "pattern" not in result and "enum" not in result, tool["name"]


@pytest.mark.parametrize("named", WRAPPED, ids=_ids(WRAPPED))
@pytest.mark.parametrize(
    "case",
    _cases("return_metadata_true"),
    ids=[
        c["branch"] + ":" + str(i) for i, c in enumerate(_cases("return_metadata_true"))
    ],
)
def test_a_wrapped_tool_accepts_every_return_run_can_make(named, case):
    _, tool = named
    schema = tool["return_schema"]
    jsonschema.validate(case["payload"], schema)
    matched = [
        index
        for index, document in enumerate(_branch_documents(schema))
        if jsonschema.Draft202012Validator(document).is_valid(case["payload"])
    ]
    assert len(matched) == 1, (
        f"{tool['name']}: {len(matched)} branches matched the {case['branch']} "
        f"payload ({matched}). `oneOf` means exactly one, so two matches reject a "
        "return the tool really makes."
    )


@pytest.mark.parametrize("named", WRAPPED, ids=_ids(WRAPPED))
@pytest.mark.parametrize(
    "case",
    _cases("return_metadata_true", reachable=False),
    ids=[str(i) for i in range(len(_cases("return_metadata_true", reachable=False)))],
)
def test_a_wrapped_tool_rejects_what_run_cannot_return(named, case):
    """Without this the suite could not tell a real declaration from a vacuous one."""
    _, tool = named
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(case["payload"], tool["return_schema"])


@pytest.mark.parametrize("named", BARE, ids=_ids(BARE))
@pytest.mark.parametrize(
    "case",
    _cases("return_metadata_false"),
    ids=[
        c["branch"] + ":" + str(i)
        for i, c in enumerate(_cases("return_metadata_false"))
    ],
)
def test_a_bare_return_tool_accepts_every_return_run_can_make(named, case):
    _, tool = named
    jsonschema.validate(case["payload"], tool["return_schema"])


@pytest.mark.parametrize("named", BARE, ids=_ids(BARE))
@pytest.mark.parametrize(
    "case",
    _cases("return_metadata_false", reachable=False),
    ids=[str(i) for i in range(len(_cases("return_metadata_false", reachable=False)))],
)
def test_a_bare_return_tool_rejects_what_run_cannot_return(named, case):
    _, tool = named
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(case["payload"], tool["return_schema"])
