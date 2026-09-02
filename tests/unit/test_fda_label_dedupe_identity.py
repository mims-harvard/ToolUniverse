"""Offline regression tests for the FDA drug-label dedupe / count reconciliation.

Defect this covers
------------------
``search_openfda`` deduplicates the records it fetched before returning them,
but the fallback dedupe key was::

    set_id or id or (brand_name + "|" + generic_name)

The drug-label tools request neither ``set_id`` nor ``id`` in their return-field
set, and a large share of SPL records carry an *empty* ``openfda`` block, so
every such record hashed to the single key ``"|"``. Four genuinely distinct
amifostine labels -- including the branded Ethyol one, the one a clinician
actually wants -- collapsed into one row, while ``meta.total`` still reported
the upstream count of 4. The returned list and the number describing it
disagreed, and real content was silently destroyed.

Three properties are pinned here:

1. distinct labels with an empty ``openfda`` block survive deduplication;
2. byte-identical labels still collapse into one;
3. ``result_count`` equals ``len(results)`` and ``duplicates_removed``
   reconciles the returned list with the upstream ``meta.total``.

Plus the identity fallback: ``spl_product_data_elements`` is returned so the
caller can tell which product a row describes when ``openfda.brand_name`` and
``openfda.generic_name`` are both null -- which is exactly what the tool's own
fallback note instructs the caller to check.

Everything mocks the HTTP layer -- no network.
"""

from unittest.mock import patch

from tooluniverse.openfda_tool import FDADrugLabelTool

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

WARNINGS_TOOL_CONFIG = {
    "name": "FDA_get_warnings_by_drug_name",
    "description": "Retrieve warning information based on the drug name.",
    "type": "FDADrugLabel",
    "parameter": {
        "type": "object",
        "properties": {"drug_name": {"type": "string"}},
        "required": ["drug_name"],
    },
    "fields": {
        "search_fields": {"drug_name": ["openfda.brand_name", "openfda.generic_name"]},
        "return_fields": ["warnings", "boxed_warning"],
    },
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def json(self):
        return self._payload


def _label(warnings_text, spl_text):
    """An SPL record with an EMPTY openfda block, as amifostine's really are."""
    return {
        "set_id": None,
        "openfda": {},
        "warnings": [warnings_text],
        "spl_product_data_elements": [spl_text],
    }


def _run(records, upstream_total, arguments=None):
    """Drive the tool so the broad-text fallback stage serves ``records``.

    The exact-name query and the term-based stage return NOT_FOUND, which is
    what pushes ``search_openfda`` onto the label-text stage -- the same path
    the live 'amifostine' query takes. Only that path runs the dedupe.
    """
    payload = {
        "meta": {"results": {"skip": 0, "limit": 100, "total": upstream_total}},
        "results": records,
    }

    def fake_get(url, *args, **kwargs):
        if "spl_product_data_elements" in url:
            return _FakeResponse(payload)
        return _FakeResponse(NOT_FOUND)

    tool = FDADrugLabelTool(WARNINGS_TOOL_CONFIG)
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        return tool.run(arguments or {"drug_name": "amifostine", "limit": 10})


def test_distinct_labels_with_empty_openfda_are_not_collapsed():
    """Two different labels, both with no openfda names, must both survive.

    Under the old `brand|generic` key both hashed to "|" and one was destroyed.
    """
    result = _run(
        [
            _label("Amifostine can cause severe hypotension.", "amifostine amifostine"),
            _label("Ethyol may cause cutaneous reactions.", "Ethyol amifostine"),
        ],
        upstream_total=2,
    )

    assert len(result["results"]) == 2
    assert result["duplicates_removed"] == 0
    warnings = {tuple(r["warnings"]) for r in result["results"]}
    assert warnings == {
        ("Amifostine can cause severe hypotension.",),
        ("Ethyol may cause cutaneous reactions.",),
    }


def test_byte_identical_labels_are_collapsed():
    """Genuinely duplicated records must still collapse to a single row."""
    duplicate = _label("Identical warning text.", "amifostine amifostine")
    result = _run([dict(duplicate), dict(duplicate)], upstream_total=2)

    assert len(result["results"]) == 1
    assert result["duplicates_removed"] == 1


def test_result_count_matches_returned_list_and_reconciles_meta_total():
    """`result_count` describes `results`; `meta.total` keeps its old meaning.

    The amifostine shape: four upstream records, two of them byte-identical,
    so three distinct labels survive and one is dropped as a duplicate.
    """
    duplicate_text = "Duplicated warning text."
    result = _run(
        [
            _label("First distinct warning.", "amifostine amifostine"),
            _label("Ethyol distinct warning.", "Ethyol amifostine"),
            _label(duplicate_text, "amifostine amifostine"),
            _label(duplicate_text, "amifostine amifostine"),
        ],
        upstream_total=4,
    )

    assert len(result["results"]) == 3
    assert result["result_count"] == len(result["results"])
    assert result["duplicates_removed"] == 1
    # meta.total is left exactly as openFDA reported it -- pre-deduplication.
    assert result["meta"]["total"] == 4
    # ...and the two numbers are now reconcilable rather than contradictory.
    assert result["result_count"] + result["duplicates_removed"] == 4


def test_dedup_note_discloses_pre_dedupe_total_and_page_overlap():
    result = _run(
        [
            _label("First distinct warning.", "amifostine amifostine"),
            _label("Second distinct warning.", "Ethyol amifostine"),
        ],
        upstream_total=9,
    )

    note = result["dedup_note"]
    assert "upstream" in note
    # Requirement (c): pages are deduplicated independently and may overlap.
    assert "skip" in note and "overlap" in note


def test_identity_field_present_when_openfda_names_are_null():
    """The fallback note says to check openfda.brand_name / generic_name.

    Those are null on these records, so the check is impossible without an
    identity fallback. `spl_product_data_elements` supplies it.
    """
    result = _run(
        [
            _label("Ethyol may cause cutaneous reactions.", "Ethyol amifostine"),
        ],
        upstream_total=1,
    )

    row = result["results"][0]
    assert row["openfda.brand_name"] is None
    assert row["openfda.generic_name"] is None
    assert row["spl_product_data_elements"] == ["Ethyol amifostine"]


def test_identity_field_never_resurrects_an_empty_record():
    """A record with no requested content is still dropped.

    `spl_product_data_elements` is attached AFTER the "did we extract anything?"
    test, so adding it can never make an otherwise-empty record appear.
    """
    empty = {
        "openfda": {},
        "warnings": [],
        "boxed_warning": [],
        "spl_product_data_elements": ["Some product name"],
    }
    result = _run([empty, _label("Real warning.", "amifostine")], upstream_total=2)

    assert len(result["results"]) == 1
    assert result["result_count"] == 1
    assert result["results"][0]["warnings"] == ["Real warning."]


def test_result_count_present_on_the_non_dedupe_path():
    """Exact-name hits never run the dedupe, but must still be reconcilable."""
    payload = {
        "meta": {"results": {"skip": 0, "limit": 100, "total": 2}},
        "results": [
            {
                "openfda": {"brand_name": ["ERBITUX"], "generic_name": ["CETUXIMAB"]},
                "warnings": ["Warning one."],
                "spl_product_data_elements": ["ERBITUX cetuximab"],
            },
            {
                "openfda": {"brand_name": ["ERBITUX"], "generic_name": ["CETUXIMAB"]},
                "warnings": ["Warning one."],
                "spl_product_data_elements": ["ERBITUX cetuximab"],
            },
        ],
    }
    tool = FDADrugLabelTool(WARNINGS_TOOL_CONFIG)
    with patch(
        "tooluniverse.openfda_tool.requests.get",
        return_value=_FakeResponse(payload),
    ):
        result = tool.run({"drug_name": "cetuximab"})

    # No fallback fired, so nothing is deduplicated and the list is untouched.
    assert len(result["results"]) == 2
    assert result["result_count"] == 2
    assert result["duplicates_removed"] == 0
    assert "dedup_note" not in result
    assert result["meta"]["total"] == 2
