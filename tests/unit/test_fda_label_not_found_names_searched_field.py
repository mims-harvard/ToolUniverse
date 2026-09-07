"""A NOT_FOUND must blame the field that was SEARCHED (Fix-R44).

Defect this covers
------------------
``_build_not_found_suggestion`` took ``requested_return_fields[0]`` to be the
label section that came up empty. That is right for the section-retrieval tools
(``return_fields: ["pharmacokinetics"]``) and wrong for the tools that return a
drug's identity. ``FDA_get_drug_names_by_boxed_warning`` searches
``boxed_warning`` and returns ``["openfda.brand_name",
"openfda.generic_name"]``, so running the tool's OWN registered example
produced, live::

    $ python -m tooluniverse.cli run FDA_get_drug_names_by_boxed_warning \\
        '{"warning_text":"The quick brown fox jumps over the lazy dog.", ...}'
    suggestion: "This label section ('openfda.brand_name') is absent from most
                 FDA labels; ... As a fallback, try searching label text fields
                 (e.g., spl_product_data_elements) and then pivot to the
                 desired section."

Both halves are wrong and both mislead:

1. ``openfda.brand_name`` was never searched and is not a label section -- it is
   an identity field present on most labels. The caller is told to go and look
   at something they did not ask about, while the real reason for the miss goes
   unmentioned.

2. The recommended fallback, ``spl_product_data_elements``, is the raw
   product/ingredient blob and matches EXCIPIENTS. Measured live 2026-08-12:
   searching it for "propylene glycol" returns 8,346 labels whose top hits are
   rabeprazole, glipizide and urea, every row carrying
   ``openfda.brand_name: null`` and ``openfda.generic_name: null`` so the
   substitution cannot be detected. The error message was pointing callers
   straight into a wrong-entity result.

The real cause of the miss is that openFDA matches a quoted string as a
CONTIGUOUS PHRASE. Measured live 2026-08-12 on ``boxed_warning``:

    "torsades de pointes"                    -> 273 labels
    "QT prolongation torsades de pointes"    ->  15 labels

Methadone's boxed warning states both concepts in different words, so it is in
the first and absent from the second -- a silent under-measure that supports the
conclusion "methadone has no QT boxed warning", the opposite of the truth.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


def _suggestion(**overrides):
    from tooluniverse.openfda_tool import _build_not_found_suggestion

    kwargs = {
        "query_text": "The quick brown fox jumps over the lazy dog.",
        "section": None,
        "section_hits": 0,
        "sections_present": [],
        "is_abbrev_like": False,
        "name_based": False,
        "searched_fields": ["boxed_warning", "indications_and_usage"],
    }
    kwargs.update(overrides)
    return _build_not_found_suggestion(**kwargs)


def test_text_search_miss_explains_phrase_matching():
    text = _suggestion()

    assert "CONTIGUOUS" in text
    assert "boxed_warning" in text
    # The section-absence story is about a section nobody asked for.
    assert "openfda.brand_name" not in text
    assert "label section" not in text


def test_text_search_miss_does_not_recommend_the_excipient_field():
    """The blob field returns a different drug's data; never suggest it blind."""
    assert "spl_product_data_elements" not in _suggestion()


def test_name_search_still_gets_spelling_advice_and_a_guarded_fallback():
    """The fix must not strip useful advice from the name-lookup tools."""
    text = _suggestion(
        query_text="notarealdrugxyz",
        section="pharmacokinetics",
        name_based=True,
        searched_fields=["openfda.brand_name", "openfda.generic_name"],
    )

    assert "checking spelling" in text
    assert "pharmacokinetics" in text
    # Still offered, but never again without the excipient warning attached.
    assert "spl_product_data_elements" in text
    assert "inactive ingredient" in text
    assert "openfda.generic_name on every row" in text


def test_identity_return_fields_are_not_treated_as_a_section():
    """End to end through the response handler, not just the message builder.

    Pins the call site as well as the helper: the bug was the call site passing
    an `openfda.*` return field in as `section`.
    """
    from tooluniverse.openfda_tool import FDADrugLabelTool

    tool = FDADrugLabelTool(
        {
            "name": "FDA_get_drug_names_by_boxed_warning",
            "type": "FDADrugLabel",
            "parameter": {
                "type": "object",
                "properties": {"warning_text": {"type": "string"}},
                "required": ["warning_text"],
            },
            "fields": {
                "search_fields": {"warning_text": ["boxed_warning"]},
                "return_fields": ["openfda.brand_name", "openfda.generic_name"],
            },
        }
    )

    class _NotFound:
        status_code = 404

        @staticmethod
        def json():
            return {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

    # Patched at `requests.get`, which is what this module actually calls --
    # patching `requests.request` would not intercept it, and `disable_network`
    # is not autouse, so this test's hermeticity rests on this patch alone.
    with patch("tooluniverse.openfda_tool.requests.get", return_value=_NotFound):
        result = tool.run({"warning_text": "no such phrase anywhere at all"})

    suggestion = result["suggestion"]
    assert "openfda.brand_name" not in suggestion
    assert "CONTIGUOUS" in suggestion


def _label_tool(name, search_fields, return_fields):
    from tooluniverse.openfda_tool import FDADrugLabelTool

    return FDADrugLabelTool(
        {
            "name": name,
            "type": "FDADrugLabel",
            "parameter": {
                "type": "object",
                "properties": {k: {"type": "string"} for k in search_fields},
                "required": list(search_fields),
            },
            "fields": {
                "search_fields": search_fields,
                "return_fields": return_fields,
            },
        }
    )


def _run_with_rows(tool, arguments, rows):
    class _Ok:
        status_code = 200

        @staticmethod
        def json():
            return {"meta": {"results": {"total": len(rows)}}, "results": rows}

    with patch("tooluniverse.openfda_tool.requests.get", return_value=_Ok):
        return tool.run(arguments)


def test_identity_exists_guard_is_disclosed():
    """A guard that drops real, non-duplicate labels must not be silent.

    `exists` defaults to the tool's RETURN fields, so a tool returning the
    openFDA identity block silently requires that block to be resolved. Measured
    live 2026-08-12, adverse_reactions:"keratoacanthoma" matches 4 labels
    upstream and this tool reported 2; the two dropped are not duplicates of the
    two kept BRAF inhibitors -- one is muromonab-CD3, a different drug class.
    """
    tool = _label_tool(
        "FDA_get_drug_name_by_adverse_reaction",
        {"adverse_reaction": ["adverse_reactions"]},
        ["openfda.brand_name", "openfda.generic_name"],
    )
    result = _run_with_rows(
        tool,
        {"adverse_reaction": "keratoacanthoma"},
        [{"openfda": {"brand_name": ["ZELBORAF"], "generic_name": ["VEMURAFENIB"]}}],
    )

    note = result.get("note") or ""
    assert "restricted to labels carrying" in note
    assert "openfda.brand_name" in note
    assert "AFTER that restriction" in note
    assert "not duplicates" in note


def test_section_tools_do_not_get_the_narrowing_note():
    """For a section tool the same guard is correct, so it must stay quiet.

    Warning on every call would train readers to skip the note, which is how a
    caveat stops being read on the queries that need it.
    """
    tool = _label_tool(
        "FDA_get_boxed_warning_info_by_drug_name",
        {"drug_name": ["openfda.brand_name", "openfda.generic_name"]},
        ["boxed_warning"],
    )
    result = _run_with_rows(
        tool, {"drug_name": "methadone"}, [{"boxed_warning": ["WARNING: ..."]}]
    )

    assert "restricted to labels carrying" not in (result.get("note") or "")


def test_config_documents_the_phrase_and_the_denominator():
    """The description must state what the code cannot fix.

    Phrase matching and the record-vs-drug distinction are openFDA's behaviour,
    not defects to code around, so the tool has to say so.
    """
    import json
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "fda_drug_labeling_tools.json"
    )
    config = next(
        t
        for t in json.loads(path.read_text())
        if t["name"] == "FDA_get_drug_names_by_boxed_warning"
    )

    assert "CONTIGUOUS PHRASE" in config["description"]
    assert "LABEL RECORDS, not drugs" in config["description"]
    assert (
        "CONTIGUOUSLY"
        in config["parameter"]["properties"]["warning_text"]["description"]
    )
    # The registered example matched nothing, so the tool's own documented
    # invocation only ever demonstrated its error path.
    assert config["test_examples"][0]["warning_text"] == "torsades de pointes"
