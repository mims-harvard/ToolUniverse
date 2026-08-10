"""Round 026: FDALabelTool must never present a shortened label section as complete.

Regression for Feature-026C-1. Every long clinical section used to be cut at a
hard-coded 2000 characters, mid-word, with nothing in the response saying so --
which silently dropped e.g. the section 12.5 Pharmacogenomics content from the
tacrolimus label while the answer still read as the complete prescribing
information.

The fix: a caller-controllable `max_section_chars` budget (generous by default
for FDA_get_drug_label, deliberately compact for the multi-record
FDA_search_drug_labels), plus a top-level `truncated` flag that is always
present and a `truncation_note` naming the cut sections and how to get them.

All tests here mock the HTTP layer -- no network.
"""

from unittest.mock import patch

from tooluniverse.fda_label_tool import DEFAULT_SECTION_CHARS, FDALabelTool


def _cfg(query_type):
    return {
        "name": f"FDA_{query_type}",
        "type": "FDALabelTool",
        "fields": {
            "endpoint": "https://api.fda.gov/drug/label.json",
            "query_type": query_type,
        },
        "parameter": {"type": "object", "properties": {}},
    }


class _Resp:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _record(brand="PROGRAF", **sections):
    return {"openfda": {"brand_name": [brand]}, "id": "spl-1", **sections}


def _run(query_type, arguments, results):
    tool = FDALabelTool(_cfg(query_type))
    payload = {"results": results}
    with patch("tooluniverse.fda_label_tool.requests.get", return_value=_Resp(payload)):
        return tool.run(arguments)


# A section longer than the FDA_get_drug_label default budget, whose tail can
# only be reached by raising max_section_chars.
_TAIL = "PHARMACOGENOMIC-TAIL-MARKER"
_LONG = ("x" * (DEFAULT_SECTION_CHARS["get"] + 500)) + _TAIL


def test_long_section_sets_top_level_truncation_flag_and_note():
    out = _run(
        "get",
        {"drug_name": "Prograf"},
        [_record(clinical_pharmacology=[_LONG])],
    )

    assert out["status"] == "success"
    assert out["truncated"] is True
    assert out["truncated_fields"] == ["clinical_pharmacology"]

    note = out["truncation_note"]
    # The note has to name the affected section, the budget applied, and the
    # argument that retrieves the rest -- a flag with no remedy is half a fix.
    assert "clinical_pharmacology" in note
    assert str(DEFAULT_SECTION_CHARS["get"]) in note
    assert "max_section_chars" in note

    # The applied budget is also echoed in metadata, and the data really is cut.
    assert out["metadata"]["max_section_chars"] == DEFAULT_SECTION_CHARS["get"]
    assert len(out["data"]["clinical_pharmacology"]) == DEFAULT_SECTION_CHARS["get"]
    assert _TAIL not in out["data"]["clinical_pharmacology"]


def test_short_sections_are_not_flagged_as_truncated():
    short = "Tacrolimus is a calcineurin inhibitor."
    out = _run(
        "get",
        {"drug_name": "Prograf"},
        [
            _record(
                clinical_pharmacology=[short], indications_and_usage=["Prophylaxis."]
            )
        ],
    )

    assert out["status"] == "success"
    # `truncated` is always present so callers can rely on the key; it must be
    # False, and the note/field list must not appear at all.
    assert out["truncated"] is False
    assert "truncation_note" not in out
    assert "truncated_fields" not in out
    assert out["data"]["clinical_pharmacology"] == short


def test_max_section_chars_zero_returns_the_section_in_full():
    out = _run(
        "get",
        {"drug_name": "Prograf", "max_section_chars": 0},
        [_record(clinical_pharmacology=[_LONG])],
    )

    assert out["truncated"] is False
    assert "truncation_note" not in out
    assert out["data"]["clinical_pharmacology"] == _LONG
    assert _TAIL in out["data"]["clinical_pharmacology"]
    assert out["metadata"]["max_section_chars"] == 0


def test_raising_max_section_chars_recovers_the_cut_content():
    args = {"drug_name": "Prograf", "max_section_chars": len(_LONG)}
    out = _run("get", args, [_record(clinical_pharmacology=[_LONG])])

    assert out["truncated"] is False
    assert _TAIL in out["data"]["clinical_pharmacology"]


def test_get_default_budget_holds_a_whole_clinical_section():
    """The default must be generous enough for a real clinical section.

    Measured against the live openFDA API, a complete Prograf
    clinical_pharmacology section is ~19,500 characters and its pharmacogenomics
    discussion starts ~6,600 characters in -- so a default that cuts at a few
    thousand characters removes it from every label that has one.
    """
    assert DEFAULT_SECTION_CHARS["get"] >= 20000

    realistic = "y" * 19517
    out = _run(
        "get",
        {"drug_name": "Prograf"},
        [_record(clinical_pharmacology=[realistic])],
    )
    assert out["truncated"] is False
    assert out["data"]["clinical_pharmacology"] == realistic


def test_search_keeps_a_compact_budget_but_discloses_it():
    """FDA_search_drug_labels returns many records, so it stays a summary view --
    it just has to say so instead of presenting cut prose as complete."""
    out = _run(
        "search",
        {"drug_name": "Prograf", "limit": 1},
        [_record(clinical_pharmacology=[_LONG], adverse_reactions=[_LONG])],
    )

    assert out["truncated"] is True
    assert out["truncated_fields"] == ["adverse_reactions", "clinical_pharmacology"]
    assert out["metadata"]["max_section_chars"] == DEFAULT_SECTION_CHARS["search"]
    assert (
        len(out["data"][0]["clinical_pharmacology"])
        == (DEFAULT_SECTION_CHARS["search"])
    )


def test_get_disclosure_describes_only_the_record_actually_returned():
    """_get_label fetches several candidates and returns the best match; the
    disclosure must not name sections belonging to the discarded candidates."""
    out = _run(
        "get",
        {"drug_name": "Prograf"},
        [
            _record(brand="OTHER BRAND", adverse_reactions=[_LONG]),
            _record(brand="PROGRAF", clinical_pharmacology=["Short and complete."]),
        ],
    )

    assert out["data"]["brand_name"] == "PROGRAF"
    assert out["truncated"] is False
    assert "truncated_fields" not in out


def test_search_by_indication_also_discloses_truncation():
    out = _run(
        "search",
        {"indication": "organ rejection", "limit": 1},
        [_record(indications_and_usage=[_LONG])],
    )

    assert out["truncated"] is True
    assert out["truncated_fields"] == ["indications_and_usage"]
    assert "max_section_chars" in out["truncation_note"]
