"""A drug-name lookup must never answer with a different drug's label section.

Defect this covers
------------------
``FDA_get_boxed_warning_info_by_drug_name {"drug_name": "Albuminex"}`` returned
BEIZRAY / DOCETAXEL's boxed warning -- "TOXIC DEATHS, HEPATOTOXICITY,
NEUTROPENIA, HYPERSENSITIVITY REACTIONS" -- under the name of Albuminex, a
plasma-derived human albumin. A clinician asking about an albumin product was
served a taxane chemotherapy agent's boxed warning.

Mechanism, measured live on api.fda.gov/drug/label.json (2026-08-11)::

    spl_product_data_elements:"ALBUMINEX"                     ->   3 labels
      AND _exists_:boxed_warning                              ->   1  BEIZRAY
    openfda.brand_name:"ALBUMINEX"                            ->   2  genuine
      AND _exists_:boxed_warning                              ->   0  <- the truth
    openfda.brand_name:"ALBUMINEX"
      AND _exists_:warnings_and_cautions                      ->   2

``drug_name`` is OR'd across ``openfda.brand_name``, ``openfda.generic_name`` and
``spl_product_data_elements`` on all 77 ``FDA_*_by_drug_name`` tools. The third
field is the raw product/ingredient blob and is there on purpose -- see
``test_fda_label_name_match_completeness.py``, which pins it because openFDA
leaves the resolved ``openfda`` block empty on many SPL records and those records
are otherwise unreachable by name. But the blob also lists EXCIPIENTS: BEIZRAY
co-packages Albuminex as a diluent, so it matched. AND-ing ``_exists_:
boxed_warning`` then deleted both genuine Albuminex labels (correctly
boxed-warning-free) and left only the wrong drug's.

The fix is a discriminator on the record's OWN resolved identity, not on which
field matched: a record is dropped only when it carries a resolved openFDA name
block AND none of ``brand_name`` / ``generic_name`` / ``substance_name`` contains
the queried name. Records with an empty ``openfda`` block are always kept -- that
is exactly the denosumab recall case the sibling suite pins, where there is no
resolved identity to contradict the blob match.

All tests here mock the HTTP layer -- no network. See ``_no_network``.
"""

import copy
import json
import pathlib
import re
import sys
import types
import urllib.parse
from functools import cache
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from tooluniverse import openfda_tool
from tooluniverse.openfda_tool import (
    FDADrugLabelTool,
    _drop_excipient_matches,
    _excipient_guard_term,
)

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    pathlib.Path(openfda_tool.__file__).parent / "data" / "fda_drug_labeling_tools.json"
)

BOXED_TOOL = "FDA_get_boxed_warning_info_by_drug_name"
WARNINGS_TOOL = "FDA_get_warnings_and_cautions_by_drug_name"

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


@pytest.fixture(autouse=True)
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB / 129k-line closest-name table, as the sibling suites do.

    Under the coverage instrumentation ``pytest.ini`` turns on by default,
    walking the real table costs ~118 s per test that reaches the
    closest-spelling stage and blows the 60 s ``pytest-timeout``. Nothing here
    is expected to reach that stage -- the sibling-section retry rescues the
    Albuminex query first -- but this file's subject is precisely which records
    survive the ladder, so the next test added must not have to remember.
    """
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [
        {"brand_name": "ALBUMINEX", "generic_name": "ALBUMIN HUMAN"},
        {"brand_name": "Prolia", "generic_name": "DENOSUMAB"},
    ]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


@pytest.fixture(autouse=True)
def _no_network(disable_network):
    """Fail loudly if anything in this module reaches the network.

    ``disable_network`` (tests/conftest.py) closes ``requests.Session.request``,
    the single door both ``requests.get`` and ``http_utils.request_with_retry``
    -> ``requests.request`` go through. The two extra patches are belt and
    braces for a caller that reaches past ``requests`` entirely. Autouse, so a
    test added later cannot opt out; each test re-opens only ``requests.get``,
    with a fake. ``test_the_network_guard_bites`` is the positive control that
    this is not a no-op.
    """

    def boom(*args, **kwargs):
        raise AssertionError("network access attempted in a hermetic test")

    with (
        patch("requests.request", side_effect=boom),
        patch("socket.create_connection", side_effect=boom),
    ):
        yield


def test_the_network_guard_bites():
    """Positive control: the fixture above really does close the network."""
    with pytest.raises((RuntimeError, AssertionError)):
        requests.get("https://api.fda.gov/drug/label.json?search=x")
    with pytest.raises(AssertionError):
        requests.request("GET", "https://api.fda.gov/drug/label.json")


# --------------------------------------------------------------------------
# A miniature openFDA: a fixed corpus queried through the real query strings.
#
# Unlike the sibling suite's matcher this one evaluates `_exists_:` clauses,
# because the whole defect lives in the interaction between the name OR-group
# and the `_exists_:<section>` guard: without `_exists_` the excipient match is
# harmless (it is one row among three), and with it, it is the ONLY row.
# --------------------------------------------------------------------------

_ATOM = re.compile(
    r'(?:_exists_:[\w.]+)|(?:[\w.]+:"[^"]*")|(?:[\w.]+:\([^)]*\))',
)


def _tokenize(search):
    """Split a decoded openFDA search into atoms, operators and parentheses.

    ``search_openfda`` joins clauses with the literal ``+AND+`` / ``+OR+`` it
    keeps unencoded via ``quote(safe='+')``; ``parse_qs`` then decodes ``+`` as
    a space, so by the time the fake transport sees them they read ``' AND '``
    and ``' OR '``. Operators are recognised only at a space, and quoted phrases
    are consumed whole, so a phrase containing the word "and" cannot be mistaken
    for an operator.
    """
    tokens = []
    i = 0
    while i < len(search):
        if search.startswith(" AND ", i):
            tokens.append("AND")
            i += 5
        elif search.startswith(" OR ", i):
            tokens.append("OR")
            i += 4
        elif search[i] in "()":
            tokens.append(search[i])
            i += 1
        elif search[i] == " ":
            i += 1
        else:
            m = _ATOM.match(search, i)
            assert m, f"unparsed openFDA search at {i}: {search[i:][:60]!r}"
            tokens.append(m.group(0))
            i = m.end()
    return tokens


def _field_text(record, field):
    value = record
    for key in field.split("."):
        if not isinstance(value, dict) or key not in value:
            return ""
        value = value[key]
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return " ".join(str(v) for v in value).lower()
    return ""


def _exists(record, field):
    value = record
    for key in field.split("."):
        if not isinstance(value, dict) or key not in value:
            return False
        value = value[key]
    return bool(value)


def _eval_atom(record, atom):
    if atom.startswith("_exists_:"):
        return _exists(record, atom.split(":", 1)[1])
    field, rest = atom.split(":", 1)
    if rest.startswith('"'):
        return rest[1:-1].lower() in _field_text(record, field)
    inner = rest[1:-1]
    haystack = _field_text(record, field)
    if " AND " in inner:
        return all(t.strip().lower() in haystack for t in inner.split(" AND ") if t)
    return any(t.strip().lower() in haystack for t in inner.split(" OR ") if t.strip())


def _matches(record, search):
    """Evaluate one openFDA Lucene-ish search string against one record."""
    tokens = _tokenize(search)
    pos = 0

    def parse_or():
        nonlocal pos
        value = parse_and()
        while pos < len(tokens) and tokens[pos] == "OR":
            pos += 1
            value = parse_and() or value
        return value

    def parse_and():
        nonlocal pos
        value = parse_unit()
        while pos < len(tokens) and tokens[pos] == "AND":
            pos += 1
            value = parse_unit() and value
        return value

    def parse_unit():
        nonlocal pos
        token = tokens[pos]
        if token == "(":
            pos += 1
            value = parse_or()
            assert tokens[pos] == ")"
            pos += 1
            return value
        pos += 1
        return _eval_atom(record, token)

    result = parse_or()
    assert pos == len(tokens), f"trailing tokens in {search!r}"
    return result


def _fake_get_for(corpus):
    def _fake_get(url, *args, **kwargs):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        # `parse_qs` already percent-decodes and turns the literal '+' operator
        # separators into spaces, so the string arrives as ' AND ' / ' OR '.
        search = query.get("search", [""])[0]
        hits = [r for r in corpus if _matches(r, search)]
        payload = (
            {
                "meta": {"results": {"skip": 0, "limit": 100, "total": len(hits)}},
                "results": hits,
            }
            if hits
            else NOT_FOUND
        )
        return SimpleNamespace(status_code=200 if hits else 404, json=lambda: payload)

    return _fake_get


@cache
def _configs():
    return tuple(json.loads(CONFIG_PATH.read_text()))


def _shipped_config(name):
    for cfg in _configs():
        if cfg.get("name") == name:
            return copy.deepcopy(cfg)
    raise AssertionError(f"{name} is not in {CONFIG_PATH.name}")


def _run(tool_name, drug_name, corpus):
    tool = FDADrugLabelTool(_shipped_config(tool_name))
    with patch(
        "tooluniverse.openfda_tool.requests.get", side_effect=_fake_get_for(corpus)
    ):
        return tool.run({"drug_name": drug_name, "limit": 50})


# --------------------------------------------------------------------------
# The Albuminex corpus: one excipient match carrying the wrong drug's boxed
# warning, two genuine products carrying none.
# --------------------------------------------------------------------------

DOCETAXEL_BOXED = (
    "WARNING: TOXIC DEATHS, HEPATOTOXICITY, NEUTROPENIA, HYPERSENSITIVITY "
    "REACTIONS, and FLUID RETENTION Treatment-related mortality associated "
    "with BEIZRAY is increased in patients with abnormal liver function."
)

BEIZRAY = {
    "openfda": {
        "brand_name": ["BEIZRAY"],
        "generic_name": ["DOCETAXEL"],
        "substance_name": ["DOCETAXEL ANHYDROUS"],
    },
    # Albuminex is co-packaged as the diluent, so the ingredient blob names it.
    "spl_product_data_elements": [
        "BEIZRAY docetaxel BEIZRAY Docetaxel DOCETAXEL ANHYDROUS ALCOHOL "
        "CITRIC ACID ACETATE ALBUMINEX Albumin human ALBUMIN HUMAN CAPRYLIC "
        "ACID N-ACETYL-DL-TRYPTOPHAN SODIUM SODIUM CHLORIDE SODIUM HYDROXIDE"
    ],
    "boxed_warning": [DOCETAXEL_BOXED],
    "warnings_and_cautions": [
        "5 WARNINGS AND PRECAUTIONS Acute myeloid leukemia, cutaneous "
        "reactions and neurologic reactions have been reported with docetaxel."
    ],
}

ALBUMINEX_WARNING = (
    "5 WARNINGS AND PRECAUTIONS Suspicion of allergic or anaphylactic "
    "reactions requires immediate discontinuation of the infusion. "
    "Hypervolemia may occur if the dosage and rate of infusion are not "
    "adjusted to the patient's volume status."
)


def _albuminex(strength):
    return {
        "openfda": {
            "brand_name": ["ALBUMINEX"],
            "generic_name": ["ALBUMIN HUMAN"],
            "substance_name": ["ALBUMIN HUMAN"],
        },
        "spl_product_data_elements": [
            f"ALBUMINEX {strength} Albumin Human Albumin Human Sodium Chloride "
            f"Sodium Hydroxide Caprylic Acid N-ACETYL-DL-TRYPTOPHAN SODIUM"
        ],
        # No boxed_warning key at all: that is why `_exists_:boxed_warning`
        # deleted these two and left the docetaxel product behind.
        "warnings_and_cautions": [f"{ALBUMINEX_WARNING} ALBUMINEX {strength}"],
    }


ALBUMINEX_CORPUS = [BEIZRAY, _albuminex("5%"), _albuminex("25%")]


def _blob(row):
    return " ".join(row.get("spl_product_data_elements") or [])


def _all_text(result):
    return json.dumps(result, default=str)


# --------------------------------------------------------------------------
# The defect.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("spelling", ["Albuminex", "ALBUMINEX", "albuminex"])
def test_another_drugs_boxed_warning_is_never_returned_for_albuminex(spelling):
    """The clinical harm, stated directly: no docetaxel warning under albumin."""
    result = _run(BOXED_TOOL, spelling, ALBUMINEX_CORPUS)

    text = _all_text(result)
    assert "TOXIC DEATHS" not in text
    assert "DOCETAXEL" not in text.upper()
    assert "BEIZRAY" not in text.upper()
    for row in result["results"]:
        assert row.get("boxed_warning") in (None, [], "")
        assert "ALBUMINEX" in _blob(row).upper()


def test_the_caller_is_told_the_section_is_absent_and_pointed_at_the_sibling():
    """Silence would be a smaller harm than the wrong drug; neither is the answer.

    The honest outcome is the one the sibling-section contract already
    describes: Albuminex matched 2 labels, none of them carries a boxed
    warning, and those same labels DO carry ``warnings_and_cautions``.
    """
    result = _run(BOXED_TOOL, "Albuminex", ALBUMINEX_CORPUS)

    assert result["result_count"] == 2
    assert result["meta"]["total"] == 2
    for row in result["results"]:
        assert row["openfda.brand_name"] == ["ALBUMINEX"]
        assert row["boxed_warning"] is None
        assert row["related_sections_present"] == ["warnings_and_cautions"]
        assert "anaphylactic" in " ".join(row["warnings_and_cautions"])

    note = result["section_note"]
    assert "boxed_warning" in note
    assert "warnings_and_cautions" in note
    assert "FDA_get_warnings_and_cautions_by_drug_name" in note


def test_the_excluded_excipient_match_is_reported_under_the_existing_note_key():
    """Rows removed silently would be a second, quieter way to mislead."""
    result = _run(BOXED_TOOL, "Albuminex", ALBUMINEX_CORPUS)

    assert "spl_product_data_elements" in result["note"]
    assert "Albuminex" in result["note"]
    # No new envelope key: the caveat channels are `note` / `dedup_note` /
    # `section_note`, all of which already existed.
    assert set(result) <= {
        "meta",
        "results",
        "result_count",
        "duplicates_removed",
        "note",
        "dedup_note",
        "section_note",
    }


def test_the_genuine_labels_are_still_reachable_through_their_own_section():
    """The same corpus, asked the question the labels can actually answer."""
    result = _run(WARNINGS_TOOL, "Albuminex", ALBUMINEX_CORPUS)

    assert result["result_count"] == 2
    assert "TOXIC DEATHS" not in _all_text(result)
    for row in result["results"]:
        assert "anaphylactic" in " ".join(row["warnings_and_cautions"])


def test_without_the_guard_the_wrong_drugs_boxed_warning_comes_back():
    """Pin the cause, so a revert cannot be mistaken for a refactor."""
    with patch.object(openfda_tool, "_excipient_guard_term", lambda _fields: None):
        result = _run(BOXED_TOOL, "Albuminex", ALBUMINEX_CORPUS)

    assert result["result_count"] == 1
    assert "TOXIC DEATHS" in _all_text(result)


# --------------------------------------------------------------------------
# The recall invariant the guard must not cost: unresolved records stay.
# --------------------------------------------------------------------------


def _denosumab(spl, brand=None):
    """``brand=None`` reproduces the empty ``openfda`` block (XBRYK et al.)."""
    return {
        "openfda": {"brand_name": [brand], "generic_name": ["DENOSUMAB"]}
        if brand
        else {},
        "spl_product_data_elements": [spl],
        "warnings_and_cautions": ["Osteonecrosis of the jaw has been reported."],
    }


DENOSUMAB_CORPUS = [
    _denosumab("Prolia denosumab DENOSUMAB SORBITOL", brand="Prolia"),
    _denosumab("XGEVA denosumab DENOSUMAB ACETATE", brand="XGEVA"),
    _denosumab("WYOST denosumab DENOSUMAB ACETIC ACID", brand="WYOST"),
    # The three with `openfda.brand_name: null` that only the ingredient blob
    # can reach -- exactly the records the completeness fix restored.
    _denosumab("XBRYK denosumab-dssb XBRYK DENOSUMAB HISTIDINE"),
    _denosumab("OSPOMYV denosumab DENOSUMAB HISTIDINE POLYSORBATE"),
    _denosumab("BILDYOS Denosumab ACETIC ACID SORBITOL DENOSUMAB"),
]


@pytest.mark.parametrize("spelling", ["denosumab", "DENOSUMAB"])
def test_records_with_an_unresolved_openfda_block_are_kept(spelling):
    """No resolved identity means nothing can contradict the blob match."""
    result = _run(WARNINGS_TOOL, spelling, DENOSUMAB_CORPUS)

    assert result["result_count"] == 6
    assert {_blob(r).split()[0] for r in result["results"]} == {
        "Prolia",
        "XGEVA",
        "WYOST",
        "XBRYK",
        "OSPOMYV",
        "BILDYOS",
    }
    # Nothing was dropped and nothing was broadened, so the caller must not be
    # told their query was weakened when it was not.
    assert "note" not in result


# --------------------------------------------------------------------------
# The discriminator itself, and the tools it must leave alone.
# --------------------------------------------------------------------------


def test_combination_products_survive_a_substring_identity():
    """`aspirin` is still the drug in "ACETAMINOPHEN, ASPIRIN, AND CAFFEINE"."""
    combo = {
        "openfda": {"generic_name": ["ACETAMINOPHEN, ASPIRIN, AND CAFFEINE"]},
        "spl_product_data_elements": ["Excedrin aspirin ASPIRIN CAFFEINE"],
    }
    kept, dropped = _drop_excipient_matches([combo], "aspirin")
    assert kept == [combo]
    assert dropped == 0


def test_a_multi_word_query_matches_a_punctuated_combination_name():
    """openFDA punctuates combination names the phrase search normalises away."""
    combo = {"openfda": {"generic_name": ["ACETAMINOPHEN AND CODEINE PHOSPHATE"]}}
    kept, dropped = _drop_excipient_matches([combo], "acetaminophen codeine")
    assert (kept, dropped) == ([combo], 0)


def test_a_contradicted_identity_is_dropped_and_an_absent_one_is_not():
    contradicted = {
        "openfda": {"brand_name": ["MEKINIST"], "generic_name": ["TRAMETINIB"]}
    }
    unresolved = {"openfda": {}, "spl_product_data_elements": ["polysorbate 80"]}
    no_names = {"openfda": {"spl_set_id": ["abc"]}}

    kept, dropped = _drop_excipient_matches(
        [contradicted, unresolved, no_names], "polysorbate 80"
    )
    assert kept == [unresolved, no_names]
    assert dropped == 1


def test_an_empty_query_never_drops_anything():
    rows = [{"openfda": {"brand_name": ["ANYTHING"]}}]
    assert _drop_excipient_matches(rows, "   ") == (rows, 0)


@pytest.mark.parametrize(
    "search_fields, expected",
    [
        # The 77 `FDA_*_by_drug_name` tools: the ambiguous shape, guard armed.
        (
            {
                (
                    "openfda.brand_name",
                    "openfda.generic_name",
                    "spl_product_data_elements",
                ): "Albuminex"
            },
            "Albuminex",
        ),
        # FDA_get_drug_names_by_ingredient: an ingredient lookup BY DESIGN.
        ({("spl_product_data_elements",): "albumin human"}, None),
        # The two OPENFDA_ONLY tools: no blob, nothing to discriminate.
        ({("openfda.brand_name", "openfda.generic_name"): "Prolia"}, None),
        # Non-name tools and empty values.
        ({("indications_and_usage",): "melanoma"}, None),
        ({"spl_product_data_elements": "albumin"}, None),
        (
            {
                (
                    "openfda.brand_name",
                    "openfda.generic_name",
                    "spl_product_data_elements",
                ): "   "
            },
            None,
        ),
    ],
)
def test_the_guard_is_armed_only_for_the_ambiguous_query_shape(search_fields, expected):
    assert _excipient_guard_term(search_fields) == expected


def test_every_shipped_drug_name_tool_arms_the_guard():
    """The guard has to cover the whole family, not the one tool that was reported."""
    armed = 0
    for cfg in _configs():
        fields = (cfg.get("fields") or {}).get("search_fields") or {}
        if "drug_name" not in fields:
            continue
        term = _excipient_guard_term({tuple(fields["drug_name"]): "Albuminex"})
        if "spl_product_data_elements" in fields["drug_name"]:
            assert term == "Albuminex", cfg["name"]
            armed += 1
        else:
            # FDA_get_brand_name_generic_name / FDA_get_drug_generic_name.
            assert term is None, cfg["name"]
    assert armed > 50
