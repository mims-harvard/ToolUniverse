"""A return_schema that is a contract on the whole return must describe errors.

``run_one_function`` does not only forward what a tool returns. On a missing
credential, a non-dict argument list, an unknown tool name, a timeout or an
unhandled exception it returns ``_create_dual_format_error(...)`` instead --
``{"status": "error", "error": str, "error_details": {...}}`` -- from ten sites
that sit *above* the tool. So that payload can come back from any tool in the
catalogue regardless of what the tool's own code does.

A ``return_schema`` is not always a contract on that payload's level, and this
is the part that makes the rule narrow rather than universal. Issue #246's
convention is that a tool returning ``{"status": "success", "data": payload}``
declares the schema of ``payload``: ``cli.py`` validates ``result["data"]``
against it, not the result. Measured on the shipped configs, 2065 of 2817
schemas are that inner contract and 752 are contracts on the whole return. For
the 2065, asking whether the schema accepts the error envelope is a category
error -- the envelope never reaches the slot the schema describes, and nothing
validates the top level of those tools at all.

Two things follow, and only the first is asserted here.

* Where the schema *is* the top-level contract and rejects the envelope, the
  schema is wrong about every failure its tool can have. 18 such schemas were.
* The top level of the other 2065 has no declared contract, while
  ``generate_tools`` annotates the wrapper's return type from the schema
  regardless -- so the generated signature describes ``data`` for a function
  that returns the envelope around it. That is a separate defect and is not
  what this file checks.

Which population a tool is in cannot be settled statically with confidence. A
class-scoped scan for ``{"status": "success", "data": ...}`` called four
enveloping tools bare (DnDsTool, NetworkProximityTool, ROCAnalysisTool and
FDALabelTool build the envelope in a module-level helper); widening it to the
module then called two bare tools enveloping (``openalex_literature_search``
and ``CMA_Guidelines_Search`` sit in modules whose helper other tools use).
Both directions were wrong on a sample of eighteen, so the membership below
rests on calling each tool and reading what came back, not on a scan.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "src/tooluniverse/data"

# Tools whose run() was called here and returned a bare payload -- a list, or a
# dict that is not the {status, data} envelope -- which their schema validated.
# That makes the schema the contract on the whole return, so it has to cover the
# error envelope too. Recorded rather than derived, for the reason in the module
# docstring. The shape each one returned:
#
#   FAERS_* (6)                {count, limit, reports, skip, status}
#   Tool_Finder_Keyword        list
#   HAL_search_archive         list
#   openalex_literature_search list
#   PMC_search_papers          list
#   CMA_Guidelines_Search      list
#   Wikidata_SPARQL_query      list
#   AdverseEvent* (3)          a bare string; these carry
#                              `configs.return_metadata: false`, which is the
#                              AgenticTool branch that returns the model's text
#                              instead of {success, result, metadata}
MEASURED_TOP_LEVEL_TOOLS = [
    "FAERS_search_adverse_event_reports",
    "FAERS_search_reports_by_drug_and_reaction",
    "FAERS_search_serious_reports_by_drug",
    "FAERS_search_reports_by_drug_and_indication",
    "FAERS_search_reports_by_drug_and_outcome",
    "FAERS_search_reports_by_drug_combination",
    "Tool_Finder_Keyword",
    "HAL_search_archive",
    "openalex_literature_search",
    "PMC_search_papers",
    "CMA_Guidelines_Search",
    "Wikidata_SPARQL_query",
    "AdverseEventPredictionQuestionGenerator",
    "AdverseEventICDMapper",
    "AdverseEventPredictionQuestionGeneratorWithContext",
]


@pytest.fixture(scope="module")
def framework_error_envelope():
    """The payload run_one_function returns when it fails before the tool runs."""
    from tooluniverse.exceptions import ToolError
    from tooluniverse.execute_function import ToolUniverse

    envelope = ToolUniverse._create_dual_format_error(
        ToolUniverse.__new__(ToolUniverse), ToolError("upstream returned HTTP 500")
    )
    # If this fails the envelope's shape changed, and the schemas written
    # against it need revisiting -- which is why it is built, not written out.
    assert set(envelope) == {"status", "error", "error_details"}, envelope
    assert envelope["status"] == "error"
    assert isinstance(envelope["error"], str)
    return envelope


@pytest.fixture(scope="module")
def schema_describes_envelope():
    """cli.py's own helper, so this file cannot drift from what cli.py does."""
    from tooluniverse.cli import _schema_describes_envelope

    return _schema_describes_envelope


def _shipped_return_schemas():
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            schema = entry.get("return_schema")
            if name and isinstance(schema, dict):
                yield path.name, name, schema


def test_there_are_schemas_to_check():
    # Guards against a glob or a parse change making everything below vacuous,
    # which is how a rule like this stops working with nothing going red.
    assert sum(1 for _ in _shipped_return_schemas()) > 2500


def test_envelope_declaring_schemas_accept_a_framework_error(
    framework_error_envelope, schema_describes_envelope
):
    """Derived and total: no list of names, so a new such schema is covered.

    A schema that declares `status` and `data` itself is describing the
    envelope, and cli.py validates the whole result against it. 327 schemas do.
    Three of them required keys only the tool's own failures carry --
    STRING_get_protein_interactions required `data`, and both
    ProteinSimilarity_search_*_local required `stage` -- so the framework's
    error matched no branch.
    """
    checked = 0
    rejecting = []
    for fname, name, schema in _shipped_return_schemas():
        if not schema_describes_envelope(schema):
            continue
        checked += 1
        if list(Draft7Validator(schema).iter_errors(framework_error_envelope)):
            rejecting.append(f"{fname}:{name}")
    assert checked > 300, f"only {checked} schemas declare the envelope; expected ~327"
    assert not rejecting, (
        f"{len(rejecting)} schemas describe the {{status, data}} envelope but "
        f"cannot validate the error envelope run_one_function returns for any "
        f"tool. Relax the error branch to require only what the framework "
        f"sends, or add a branch for it. First few: {rejecting[:10]}"
    )


@pytest.mark.parametrize("name", MEASURED_TOP_LEVEL_TOOLS)
def test_measured_top_level_schemas_accept_a_framework_error(
    name, framework_error_envelope
):
    schemas = {n: s for _, n, s in _shipped_return_schemas()}
    assert name in schemas, f"{name} lost its return_schema"
    errors = [
        e.message
        for e in Draft7Validator(schemas[name]).iter_errors(framework_error_envelope)
    ]
    assert not errors, (
        f"{name}'s schema is the contract on its whole return and cannot "
        f"validate the framework error envelope: {errors[0]}"
    )


def test_exactly_one_oneof_branch_accepts_the_envelope(framework_error_envelope):
    """oneOf means exactly one, so a second match is as broken as none.

    A success branch that is an open object -- no `required`, no
    `additionalProperties: false` -- accepts the envelope as well, both branches
    match, and the schema rejects the very payload the error branch was added
    for. 583 schemas were fixed for that; the fix puts
    `"not": {"required": ["error"]}` on such a branch.
    """
    ambiguous = []
    for fname, name, schema in _shipped_return_schemas():
        branches = schema.get("oneOf")
        if not isinstance(branches, list):
            continue
        hits = [
            i
            for i, branch in enumerate(branches)
            if not list(Draft7Validator(branch).iter_errors(framework_error_envelope))
        ]
        if len(hits) > 1:
            ambiguous.append(f"{fname}:{name} matches branches {hits}")
    assert not ambiguous, (
        f"{len(ambiguous)} schemas match the error envelope in more than one "
        f'branch; the success branch needs "not": {{"required": ["error"]}}. '
        f"First few: {ambiguous[:10]}"
    )


def test_string_interactions_partial_failure_matches_exactly_one_branch():
    """The envelope is not the only payload that can match two branches.

    STRING_get_protein_interactions returns {status, data, metadata, error} when
    none of the submitted identifiers mapped (string_tool.py, the
    `if not returned_indices` path): a real page of records alongside an error
    string. That satisfies its success branch *and* the error branch, so oneOf
    would reject it -- hence `"not": {"required": ["error"]}` on the success
    branch.

    test_exactly_one_oneof_branch_accepts_the_envelope cannot catch this. It
    probes with the framework envelope, which has no `data` and so fails that
    success branch whether the guard is present or not; removing the guard
    leaves it green. This payload is what distinguishes them, and it has to be
    written out because nothing generic can synthesise a valid instance of an
    arbitrary success branch.
    """
    schema = next(
        s
        for _, name, s in _shipped_return_schemas()
        if name == "STRING_get_protein_interactions"
    )
    partial_failure = {
        "status": "error",
        "data": [{"stringId_A": "9606.ENSP00000269305", "score": "0.9"}],
        "metadata": {"unmapped_count": 1, "unmapped_identifiers": ["NOTAGENE"]},
        "error": "STRING could not map any of the 1 submitted identifier(s): NOTAGENE.",
    }
    branches = schema["oneOf"]
    hits = [
        i
        for i, branch in enumerate(branches)
        if not list(Draft7Validator(branch).iter_errors(partial_failure))
    ]
    assert hits == [1], (
        "a partly-failed STRING page must match the error branch only; "
        f'matched {hits}. The success branch needs "not": {{"required": ["error"]}}.'
    )
    assert not list(Draft7Validator(schema).iter_errors(partial_failure))


@pytest.mark.parametrize(
    "schema, fault",
    [
        (
            {"type": "array", "items": {"type": "object"}},
            "an array cannot be an object",
        ),
        ({"type": "string"}, "a string cannot be an object"),
        (
            {
                "type": "object",
                "properties": {"reports": {"type": "array"}},
                "required": ["reports"],
            },
            "requires a key the envelope does not carry",
        ),
        (
            {
                "type": "object",
                "properties": {
                    "status": {"const": "error"},
                    "error": {"type": "string"},
                    "stage": {"type": "string"},
                },
                "required": ["status", "error", "stage"],
            },
            "an error branch requiring a key only the tool's own failures carry",
        ),
    ],
)
def test_the_rule_rejects_the_shapes_it_was_written_for(
    schema, fault, framework_error_envelope
):
    """Without this, a rule that silently stopped matching would still pass.

    These are the four shapes the 18 fixed schemas actually had.
    """
    assert list(Draft7Validator(schema).iter_errors(framework_error_envelope)), fault


def test_an_open_success_branch_is_caught_as_ambiguous(framework_error_envelope):
    """The ambiguity the naive fix introduces, proved separately from the sweep."""
    naive = {
        "oneOf": [
            {"type": "object"},
            {
                "type": "object",
                "properties": {"error": {"type": "string"}},
                "required": ["error"],
            },
        ]
    }
    hits = [
        i
        for i, b in enumerate(naive["oneOf"])
        if not list(Draft7Validator(b).iter_errors(framework_error_envelope))
    ]
    assert hits == [0, 1], (
        "an open success branch must match the envelope too, which is what "
        "makes the guard necessary"
    )
