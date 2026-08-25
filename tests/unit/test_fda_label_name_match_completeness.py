"""A correct drug spelling must never return fewer labels than a typo of it.

Defect this covers
------------------
``FDA_get_warnings_and_cautions_by_drug_name`` and its siblings mapped
``drug_name`` onto ``openfda.brand_name`` / ``openfda.generic_name`` only. Both
of those live in openFDA's *resolved* ``openfda`` block, which is empty on every
SPL record openFDA failed to resolve -- so those records were unreachable by
name. Measured live on 2026-08-11::

    run FDA_get_warnings_and_cautions_by_drug_name '{"drug_name":"denosumab"}' -> total 19
    run FDA_get_warnings_and_cautions_by_drug_name '{"drug_name":"denosumb"}'  -> total 25

The *misspelling* returned six MORE labels than the correct spelling, because it
fell through to the closest-spelling stage, which searches
``spl_product_data_elements`` (see Stage C in ``openfda_tool.search_openfda``).
The six extras are genuine denosumab products -- XBRYK, OSPOMYV, BILDYOS,
Bilprevda and two Denosumab-dssb records -- all of them carrying the
osteonecrosis-of-the-jaw warning, and all of them with
``openfda.brand_name: null``. The same 19-vs-25 split reproduced on
``FDA_get_adverse_reactions_by_drug_name`` and was case-insensitive.

Field choice was measured, not guessed (openFDA drug/label, 2026-08-11)::

    openfda.brand_name:"denosumab"                      ->  2
    openfda.generic_name:"denosumab"                    -> 19
    (brand OR generic)                                  -> 19
    spl_product_data_elements:"denosumab"               -> 25
    (brand OR generic OR spl_product_data_elements)     -> 25
    free text `denosumab`                               -> 29

``spl_product_data_elements`` is the per-record product/ingredient identity
string ("XBRYK denosumab-dssb ... DENOSUMAB"), i.e. an authoritative name field
carried by the record itself, so every term stays bound to a name field. The
free-text 29 is *not* used: it matches labels that merely mention the drug.

Sampled live, the extra records the third field admits are genuine products of
the drug queried, not noise -- aspirin 747 -> 2,223, metformin 389 -> 1,063 and
warfarin 73 -> 285, every sampled extra being an aspirin / metformin / warfarin
SPL with an empty ``openfda`` block.

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

from tooluniverse import openfda_tool
from tooluniverse.openfda_tool import FDADrugLabelTool

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    pathlib.Path(openfda_tool.__file__).parent / "data" / "fda_drug_labeling_tools.json"
)

# openFDA's *resolved* name fields: null on every SPL record openFDA could not
# resolve, which is what made those records unreachable by name.
RESOLVED_NAME_FIELDS = ["openfda.brand_name", "openfda.generic_name"]

# The one list every drug-name lookup must resolve to.
CANONICAL_NAME_FIELDS = RESOLVED_NAME_FIELDS + ["spl_product_data_elements"]

# The only two tools deliberately left on the resolved fields alone: their whole
# answer IS the openfda block, and the records the third field admits have an
# empty openfda block by construction, so for these two the extra rows would
# carry nothing but nulls.
OPENFDA_ONLY_TOOLS = {"FDA_get_brand_name_generic_name", "FDA_get_drug_generic_name"}

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}

_DRUG_LIST_MODULE = "tooluniverse.data.fda_drugs_with_brand_generic_names_for_tool"


@pytest.fixture(autouse=True)
def tiny_drug_list(monkeypatch):
    """Stub the 6 MB / 129k-line closest-name table, as the sibling suites do.

    The closest-spelling stage this module exercises on purpose scans every
    brand and generic name in that table. Under the coverage instrumentation
    `pytest.ini` turns on by default, walking it takes **118 seconds per test**
    and blows the 60s `pytest-timeout` -- measured here, on the two
    `test_correct_spelling_returns_a_superset_of_the_misspelling` cases, before
    this stub existed. Every other test in this file runs in under 5 ms.

    Autouse rather than opt-in (the sibling suites take it as a parameter):
    this file's whole subject is the fallback ladder, so the next test added
    here is likely to reach that stage too, and it must not have to remember.

    The two entries are the only DENOSUMAB rows in the real table, so the
    closest-spelling match for "denosumb" is unchanged by stubbing it.
    """
    stub = types.ModuleType(_DRUG_LIST_MODULE)
    stub.drug_list = [
        {"brand_name": "Prolia", "generic_name": "DENOSUMAB"},
        {"brand_name": "XGEVA", "generic_name": "DENOSUMAB"},
    ]
    monkeypatch.setitem(sys.modules, _DRUG_LIST_MODULE, stub)
    return stub


@pytest.fixture(autouse=True)
def _no_network(disable_network):
    """Fail loudly if anything in this module reaches the network.

    ``disable_network`` (tests/conftest.py) closes ``requests.Session.request``,
    which is the door ``requests.get`` and ``http_utils.request_with_retry`` ->
    ``requests.request`` both go through. The two extra patches below are belt
    and braces for a caller that reaches past requests entirely. Autouse, so a
    test added later cannot opt out; each test re-opens only ``requests.get``,
    with a fake.
    """

    def boom(*args, **kwargs):
        raise AssertionError("network access attempted in a hermetic test")

    with (
        patch("requests.request", side_effect=boom),
        patch("socket.create_connection", side_effect=boom),
    ):
        yield


# --------------------------------------------------------------------------
# A miniature openFDA: a fixed corpus queried through the real query strings.
# --------------------------------------------------------------------------


def _record(spl, brand=None):
    """One SPL label. ``brand=None`` reproduces the empty ``openfda`` block."""
    openfda = {"brand_name": [brand], "generic_name": ["DENOSUMAB"]} if brand else {}
    return {
        "openfda": openfda,
        "spl_product_data_elements": [spl],
        "warnings_and_cautions": ["Osteonecrosis of the jaw has been reported."],
        "adverse_reactions": ["Hypocalcaemia and osteonecrosis of the jaw."],
    }


# Two shapes, both taken from the live corpus: records openFDA resolved (so the
# openfda block is populated) and the ones it did not, where the block is empty
# and only spl_product_data_elements identifies the product.
CORPUS = [
    _record("Prolia denosumab DENOSUMAB DENOSUMAB SORBITOL", brand="Prolia"),
    _record("XGEVA denosumab DENOSUMAB DENOSUMAB ACETATE", brand="XGEVA"),
    _record("WYOST denosumab DENOSUMAB DENOSUMAB ACETIC ACID", brand="WYOST"),
    # The three the two-field search could not see.
    _record("XBRYK denosumab-dssb XBRYK DENOSUMAB HISTIDINE"),
    _record("OSPOMYV denosumab DENOSUMAB HISTIDINE POLYSORBATE"),
    _record("BILDYOS Denosumab ACETIC ACID SORBITOL DENOSUMAB"),
]

_PHRASE_CLAUSE = re.compile(r'([\w.]+):"([^"]*)"')
_TERMS_CLAUSE = re.compile(r"([\w.]+):\(([^)]*)\)")


def _field_text(record, field):
    """Every indexed value in ``CORPUS`` is a list of strings; join it, folded."""
    value = record
    for key in field.split("."):
        if key not in value:
            return ""
        value = value[key]
    return " ".join(str(v) for v in value).lower()


def _matches(record, search):
    """OR every ``field:"phrase"`` / ``field:(t1 AND t2)`` clause in `search`.

    ``_exists_:`` clauses are ignored because neither regex can capture one:
    openFDA takes them bare, as ``(_exists_:a OR _exists_:b)``, never bound to a
    field. That is sound here anyway -- every record in ``CORPUS`` carries the
    requested section, so the guard would be a no-op.
    """
    for field, phrase in _PHRASE_CLAUSE.findall(search):
        if phrase.lower() in _field_text(record, field):
            return True
    for field, terms in _TERMS_CLAUSE.findall(search):
        haystack = _field_text(record, field)
        wanted = [t.strip().lower() for t in terms.split(" AND ") if t.strip()]
        if wanted and all(t in haystack for t in wanted):
            return True
    return False


def _fake_get(url, *args, **kwargs):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    # `search_openfda` builds its URL with quote(safe='+'), so '+' is a literal
    # separator rather than an encoded space -- undo both here.
    search = urllib.parse.unquote(query.get("search", [""])[0]).replace("+", " ")
    hits = [r for r in CORPUS if _matches(r, search)]
    payload = (
        {
            "meta": {"results": {"skip": 0, "limit": 100, "total": len(hits)}},
            "results": hits,
        }
        if hits
        else NOT_FOUND
    )
    return SimpleNamespace(status_code=200 if hits else 404, json=lambda: payload)


@cache
def _configs():
    """Parsed config file, cached -- it is ~1 MB and read by every test here."""
    return tuple(json.loads(CONFIG_PATH.read_text()))


def _shipped_config(name):
    """A deep copy, so a test that edits the config cannot leak into the next."""
    for cfg in _configs():
        if cfg.get("name") == name:
            return copy.deepcopy(cfg)
    raise AssertionError(f"{name} is not in {CONFIG_PATH.name}")


def _run(drug_name, config=None):
    tool = FDADrugLabelTool(config or _shipped_config(WARNINGS_TOOL))
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=_fake_get):
        return tool.run({"drug_name": drug_name, "limit": 50})


WARNINGS_TOOL = "FDA_get_warnings_and_cautions_by_drug_name"


def _identities(result):
    return {tuple(r.get("spl_product_data_elements") or []) for r in result["results"]}


# --------------------------------------------------------------------------
# The defect.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool_name", [WARNINGS_TOOL, "FDA_get_adverse_reactions_by_drug_name"]
)
def test_record_with_null_openfda_brand_name_is_reachable_by_name(tool_name):
    """XBRYK has ``openfda.brand_name: null``; its SPL name field still finds it.

    ``note`` must be absent: the record has to arrive on the exact-name path,
    not be rescued by one of the broadening stages, otherwise the caller is told
    their query was weakened when it was not.
    """
    result = _run("denosumab", _shipped_config(tool_name))

    xbryk = [
        r
        for r in result["results"]
        if "XBRYK" in " ".join(r.get("spl_product_data_elements") or [])
    ]
    assert len(xbryk) == 1
    assert xbryk[0]["openfda.brand_name"] is None
    assert "note" not in result


@pytest.mark.parametrize("spelling", ["denosumab", "DENOSUMAB"])
def test_correct_spelling_returns_a_superset_of_the_misspelling(spelling):
    """The invariant, stated directly: a typo can never out-recall the truth.

    The misspelling still reaches the closest-spelling stage -- that path is not
    being removed, it is being made redundant -- so this compares two live code
    paths against one corpus rather than asserting a fixed number.
    """
    typo = _run("denosumb")
    correct = _run(spelling)

    assert "closest-spelling" in typo["note"]
    assert _identities(typo) <= _identities(correct)
    assert correct["result_count"] >= typo["result_count"]


def test_two_field_search_is_what_lost_the_records():
    """Pin the cause, so a revert cannot be mistaken for a refactor.

    Restoring the pre-fix field list reproduces the live 19-vs-25 shape on this
    corpus: the three resolved products come back and the three with an empty
    ``openfda`` block vanish.
    """
    cfg = _shipped_config(WARNINGS_TOOL)
    cfg["fields"]["search_fields"]["drug_name"] = RESOLVED_NAME_FIELDS

    before = _run("denosumab", cfg)
    after = _run("denosumab")

    assert before["result_count"] == 3
    assert after["result_count"] == 6
    assert _identities(before) < _identities(after)


# --------------------------------------------------------------------------
# The invariant across every config, so one tool cannot wander off alone.
# --------------------------------------------------------------------------


def test_every_drug_name_parameter_a_caller_can_pass_declares_its_fields():
    """Omission has to be as loud as divergence.

    The equality check below only visits tools that already declare the mapping,
    so a new label tool taking a ``drug_name`` and forgetting ``search_fields``
    would slip past it silently -- and silently search nothing by name. This
    also guards the guard: an empty sweep would make the check below vacuous.
    """
    undeclared = [
        cfg["name"]
        for cfg in _configs()
        if "drug_name" in ((cfg.get("parameter") or {}).get("properties") or {})
        and "drug_name" not in ((cfg.get("fields") or {}).get("search_fields") or {})
    ]
    assert not undeclared, (
        f"drug_name parameters with no search_fields entry: {undeclared}"
    )


def test_every_drug_name_lookup_searches_the_canonical_name_fields():
    checked = 0
    for cfg in _configs():
        fields = (cfg.get("fields") or {}).get("search_fields") or {}
        if "drug_name" not in fields:
            continue
        checked += 1
        # Equality, not "does not contain": pinned negatively, the two exempt
        # tools could drift to any other field list unnoticed.
        expected = (
            RESOLVED_NAME_FIELDS
            if cfg["name"] in OPENFDA_ONLY_TOOLS
            else CANONICAL_NAME_FIELDS
        )
        assert fields["drug_name"] == expected, cfg["name"]
    # A guard against the loop silently matching nothing after a rename.
    assert checked > 50
