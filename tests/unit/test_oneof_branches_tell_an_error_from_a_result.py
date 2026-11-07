"""No return_schema's oneOf may accept an error envelope on two branches.

oneOf requires EXACTLY one branch to match. 581 schemas paired a success branch
that required nothing -- so it accepted any object -- with an error branch that
required `error`. An error envelope satisfied both, so oneOf rejected it, and a
correct result failed its own schema. Measured live before the fix on four
tools picked for having nothing else to do with this work:

    Alliance_get_gene            result=error  branches matched=[0, 1]
    AlphaFill_get_transplants    result=error  branches matched=[0, 1]
    MobiDB_get_protein           result=error  branches matched=[0, 1]
    OmicsDI_get_dataset          result=error  branches matched=[0, 1]

It only bites when the upstream call fails, which is why 581 of them went
unnoticed: every success payload validated fine.

The fix is `"not": {"required": ["error"]}` on the success branch, which says
what that branch was always for -- a result that is not an error. It cannot
turn a passing result into a failing one, because the only objects it newly
rejects are ones carrying an `error` key, and those matched both branches
before and so failed anyway.

`anyOf` would have been the wrong fix, and is worth naming because it is the
obvious one. The success branch accepts any object, so under `anyOf` every
result would match it and the schema could never fail at all -- trading a false
failure for no checking whatsoever.

This test is written as an invariant over every tool rather than a list of the
581, so a schema added later cannot reintroduce it.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

# Error envelopes the tools in this repo actually produce: `error` alone, and
# with the status/url/status_code/detail keys the REST helpers add.
ENVELOPES = [
    {"status": "error", "error": "upstream said no"},
    {"status": "error", "error": "upstream said no", "url": "http://x"},
    {
        "status": "error",
        "error": "upstream said no",
        "url": "http://x",
        "status_code": 404,
        "detail": "{}",
    },
    {"error": "upstream said no"},
]


def _schemas():
    for path in sorted(DATA.glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            schema = entry.get("return_schema")
            if isinstance(schema, dict) and isinstance(schema.get("oneOf"), list):
                if len(schema["oneOf"]) > 1:
                    yield path.name, entry["name"], schema


def _matching(branches, instance):
    return [
        i
        for i, branch in enumerate(branches)
        if not list(Draft7Validator(branch).iter_errors(instance))
    ]


ALL = list(_schemas())


def test_there_are_schemas_to_check():
    """Guard against the walk silently finding nothing and the rest of this
    file passing for the wrong reason."""
    assert len(ALL) > 500, len(ALL)


def test_no_oneof_accepts_an_error_envelope_on_two_branches():
    """The invariant. A schema here means a tool whose error result cannot
    validate, however correct it is."""
    offenders = []
    for filename, tool, schema in ALL:
        for envelope in ENVELOPES:
            hits = _matching(schema["oneOf"], envelope)
            if len(hits) > 1:
                offenders.append((filename, tool, sorted(envelope), hits))
                break
    assert not offenders, "%d schemas cannot tell an error from a result: %s" % (
        len(offenders),
        offenders[:5],
    )


def test_every_schema_this_fixed_still_validates_an_error_result():
    """The other half: making the branches exclusive must not leave an error
    result matching nothing.

    Restricted to the schemas carrying the marker this change added, because it
    is not a repo-wide invariant. 34 other schemas match none of these
    envelopes: their oneOf is one success shape against another, so an error
    envelope was never described here. That question has since been measured --
    each of the 34 was called until it failed and the payload it really sends
    recorded -- and is asserted in
    test_oneof_accepts_the_failure_the_tool_reports.py, where 30 needed an
    error branch and 4 already accepted the shape they emit.

    Among the fixed ones an envelope matching no branch is still acceptable
    where that schema's error branch requires keys the envelope lacks: Crossref
    and ROR require `status` alongside `error`, confirmed live, so the bare
    {"error": ...} probe is a shape they never emit. At least one envelope has
    to land."""
    fixed = [
        (filename, tool, schema)
        for filename, tool, schema in ALL
        if any(b.get("not") == {"required": ["error"]} for b in schema["oneOf"])
    ]
    assert len(fixed) > 500, len(fixed)
    unreachable = [
        (f, t)
        for f, t, schema in fixed
        if not any(len(_matching(schema["oneOf"], e)) == 1 for e in ENVELOPES)
    ]
    assert not unreachable, (
        "%d of the fixed schemas no envelope validates against: %s"
        % (
            len(unreachable),
            unreachable[:5],
        )
    )


SPOT_CHECKS = [
    ("alliance_genome_tools", "Alliance_get_gene"),
    ("mobidb_tools", "MobiDB_get_protein"),
    ("crossref_tools", "Crossref_get_member"),
    ("kegg_ext_tools", "KEGG_get_compound"),
    ("edger_limma_tools", "RNAseq_edger_limma_de"),
    ("iucn_tools", "IUCN_get_conservation_status"),
    ("consensus_tools", "Consensus_search_papers"),
]


@pytest.mark.parametrize("stem,tool", SPOT_CHECKS, ids=[t for _, t in SPOT_CHECKS])
def test_the_success_branch_says_it_is_not_an_error(stem, tool):
    """Named cases across the three forms the edit had to take: files a JSON
    dump reproduces, files it does not, and the two tools whose branches are
    written inline on one line."""
    entries = json.loads((DATA / f"{stem}.json").read_text())
    schema = next(e for e in entries if e.get("name") == tool)["return_schema"]
    branches = schema["oneOf"]
    success = [b for b in branches if "error" not in (b.get("required") or [])]
    assert success, tool
    for branch in success:
        guard = branch.get("not")
        # A branch that also admits null carries the guard scoped to objects.
        # `required` applies only to objects, so for a null the unscoped guard
        # is vacuously satisfied and `not` then rejects the very null the
        # branch allows -- four schemas hit that. Scoping changes nothing for
        # an error envelope, which is an object carrying `error` either way,
        # so the invariant above still holds for both shapes.
        declared = branch.get("type")
        nullable = declared == "null" or (
            isinstance(declared, list) and "null" in declared
        )
        expected = (
            {"type": "object", "required": ["error"]}
            if nullable
            else {"required": ["error"]}
        )
        assert guard == expected, (tool, guard)
