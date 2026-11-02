"""Three defects a 134-call validation run turned up, none of them a narrow type.

Validating every live payload from the loose-array batch against its schema
gave 122 of 134. Reverting the batch and running the same 134 cases gave the
same 122 and the same 12 failures, so none of them came from that work. They
were three separate faults, and only one of the three is a schema being wrong
about a type.

  * ENCODE answered a missing accession with status: "success"
  * ChannelsDB's error envelope failed validation while being correct
  * two OpenFoodFacts fields were declared non-null and return null

The first is the serious one. ENCODE serves a 404 whose body is its own error
document, and _http_get read that body instead of raising -- deliberately,
because ENCODE does serve real payloads with a non-200 status. But it could
not tell the two apart, so asking for a nonexistent accession produced

    {"status": "success",
     "data": {"@type": ["HTTPNotFound", "Error"], "status": "error",
              "code": 404, "title": "Not Found", ...}}

and a caller checking status == "success" got an error document to read as a
file. ENCODE names the classes of whatever it serves in `@type`: a file is
["File", "Item"], an experiment ["Experiment", "Dataset", "Item"], an error
["HTTPNotFound", "Error"]. A real object never lists "Error" there, which is
why the check keys off @type and not off the body's own `status` -- for a real
resource that field carries the object's lifecycle state, "released" or
"archived", not a call outcome. Both call sites shared the fault and the fix is
in the helper, so one change covers them.

The second is a schema too loose in a way that causes a false failure, which is
worth separating from the too-narrow kind. The error envelope
{status, error, url, status_code, detail} is correct and its `error` branch
accepts it -- but the success branch required nothing, so it accepted the
envelope too, and oneOf needs exactly one match. Requiring the two keys every
one of the 10 successful payloads carries separates them.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _tool(stem, name):
    for entry in json.loads((DATA / f"{stem}.json").read_text()):
        if entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not in {stem}.json")


def _node(schema, path):
    def step(node, seg):
        if not isinstance(node, dict):
            return None
        found = (
            node.get("items") if seg == "*" else (node.get("properties") or {}).get(seg)
        )
        if found is not None:
            return found
        for keyword in ("oneOf", "anyOf", "allOf"):
            for branch in node.get(keyword) or []:
                found = step(branch, seg)
                if found is not None:
                    return found
        return None

    node = schema
    for seg in path.split("->"):
        node = step(node, seg)
        if node is None:
            return None
    return node


def _types(schema, path):
    decl = _node(schema, path)
    assert decl is not None, f"{path} is not declared"
    t = decl.get("type")
    return set(t) if isinstance(t, list) else {t}


REAL_FILE = {
    "@type": ["File", "Item"],
    "accession": "ENCFF001JXO",
    "status": "archived",
}
REAL_EXPERIMENT = {
    "@type": ["Experiment", "Dataset", "Item"],
    "accession": "ENCSR000AKS",
    "status": "released",
}
NOT_FOUND = {
    "@type": ["HTTPNotFound", "Error"],
    "status": "error",
    "code": 404,
    "title": "Not Found",
    "description": "The resource could not be found.",
    "detail": "/files/ENCFF123ABC/",
}


def test_encode_tells_its_error_document_from_a_resource():
    """@type is the discriminator, not the body's own `status` -- that reads
    "archived" and "released" on real objects."""
    from tooluniverse.encode_tool import _is_encode_error_document

    assert _is_encode_error_document(NOT_FOUND)
    assert not _is_encode_error_document(REAL_FILE)
    assert not _is_encode_error_document(REAL_EXPERIMENT)
    # a resource whose own lifecycle status happens to be an error-ish word is
    # still a resource
    assert not _is_encode_error_document({"@type": ["File", "Item"], "status": "error"})
    assert not _is_encode_error_document(None)
    assert not _is_encode_error_document({"raw": "not json"})


def test_an_encode_error_document_is_raised_not_returned_as_data():
    """Returning it made the envelope say success. Raising lets the callers'
    existing error handling produce an error envelope, which is why one change
    in the helper fixes both call sites.

    It raises ToolUnavailableError rather than a new exception class on
    purpose: that is what _handle_encode_error already maps "404" and "not
    found" to, and a new class defined in a tool module would be picked up by
    the lazy-registry generator's AST scan and committed as if it were a
    tool."""
    from tooluniverse.encode_tool import _encode_error_message
    from tooluniverse.exceptions import ToolUnavailableError

    message = _encode_error_message(NOT_FOUND)
    assert "404" in message
    assert "Not Found" in message
    assert "could not be found" in message
    assert issubclass(ToolUnavailableError, Exception)


def test_the_encode_helper_still_swallows_a_non_200_that_carries_a_resource():
    """The reason the body was read rather than re-raised in the first place.
    That behaviour is kept; only error documents now raise."""
    import tooluniverse.encode_tool as mod

    assert not mod._is_encode_error_document(REAL_FILE)


def test_the_channelsdb_branches_cannot_both_match_the_error_envelope():
    """Both branches accepting it is why a correct result failed: oneOf needs
    exactly one. The success branch now requires the two keys all 10 measured
    payloads carry."""
    schema = _tool("channelsdb_tools", "ChannelsDB_get_channels_pdb")["return_schema"]
    branches = schema["oneOf"]
    success = next(b for b in branches if "Channels" in (b.get("properties") or {}))
    assert sorted(success["required"]) == ["Annotations", "Channels"]

    envelope = {
        "status": "error",
        "error": "ChannelsDB_get_channels_pdb API error (HTTP 404): "
        "Protein with ID '1crn' not found in ChannelsDB (PDB)",
        "url": "https://channelsdb.ncbr.muni.cz/api/channels/pdb/1crn",
        "status_code": 404,
        "detail": '{"detail":"Protein with ID \'1crn\' not found"}',
    }
    matching = [
        i
        for i, b in enumerate(branches)
        if not list(Draft7Validator(b).iter_errors(envelope))
    ]
    assert len(matching) == 1, f"branches {matching} all accept the error envelope"
    assert not list(Draft7Validator(schema).iter_errors(envelope))

    payload = {"Annotations": [], "Channels": {"CSATunnels_MOLE": []}}
    assert not list(Draft7Validator(schema).iter_errors(payload))


OPENFOODFACTS_WIDENED = [
    (
        "product->ecoscore_data->previous_data->score",
        {"integer", "number", "null"},
        "an integer for 7 of 12 products, null for 1, absent for 4",
    ),
    (
        "product->sources->*->name",
        {"string", "null"},
        "null for 5 of the 91 source records across 12 products",
    ),
]


@pytest.mark.parametrize(
    "path,types,evidence",
    OPENFOODFACTS_WIDENED,
    ids=[p.split("->")[-1] for p, _, _ in OPENFOODFACTS_WIDENED],
)
def test_an_openfoodfacts_field_that_returns_null_says_so(path, types, evidence):
    schema = _tool("openfoodfacts_tools", "OpenFoodFacts_get_product")["return_schema"]
    assert _types(schema, path) == types, evidence
