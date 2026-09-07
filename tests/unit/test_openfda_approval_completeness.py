"""Drugs@FDA approvals must be complete in what they list and in what they find.

Two defects, both silent, both measured live 2026-08-11 against
https://api.fda.gov/drug/drugsfda.json.

1. TRUNCATION NEXT TO A COUNT THAT IMPLIED COMPLETENESS.
   `_extract_approval_summary` returned `sorted(strengths)[:5]`. NDA215256
   (Wegovy) has 12 products carrying 7 distinct strengths, and the summary
   printed `product_count: 12` beside a 5-item list with no truncation flag.
   `sorted()` is lexicographic on these strings, so the cut was not arbitrary:
   it removed `7.2MG/0.75ML (7.2MG/0.75ML)` and `9.6MG/3ML (3.2MG/ML)` -- the
   two HIGHEST Wegovy doses. `brand_name[:3]` / `generic_name[:3]` cut the same
   way.

2. NAME SEARCH THAT ONLY LOOKED AT THE RESOLVED `openfda.*` FIELDS.
   The name clause was `(openfda.brand_name:"X" OR openfda.generic_name:"X")`.
   The `openfda` block is derived from FDA's SPL resolution and is EMPTY for
   NDA215256 (Wegovy) and NDA209637 (Ozempic injection), while their
   `products.brand_name` is populated and searchable:

     openfda.brand_name:"WEGOVY"    -> total 0
     products.brand_name:"WEGOVY"   -> total 2  (NDA215256, NDA218316)
     openfda.brand_name:"OZEMPIC"   -> total 1  (NDA213051)
     products.brand_name:"OZEMPIC"  -> total 2  (NDA213051, NDA209637)

   So `drug_name="Wegovy"` reported "No FDA drug approvals found", and
   `drug_name="Ozempic"` did something worse than fail: it returned exactly one
   application, NDA213051 (the ORAL tablet, original approval 2019-09-20),
   while the Ozempic INJECTION the caller meant is NDA209637, approved
   2017-12-05. A confident answer with the wrong approval date.

   Same defect shape as `FAERS_DRUG_NAME_FIELDS` in `openfda_adv_tool.py`:
   query only the resolved `openfda.*` names and anything openFDA failed to
   resolve to an SPL silently looks absent.

Hermetic: nothing here touches the network. `requests.get` is stubbed with a
fixture responder, and `requests.request`, `requests.Session.request` and
`socket.create_connection` are ALL patched to raise -- these tools can reach
out through `http_utils.request_with_retry` -> `requests.request` as well as
through `requests.get`, so stubbing `requests.get` alone would not prove it.
"""

import json
import socket
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import requests  # noqa: E402

import tooluniverse  # noqa: E402
from tooluniverse.openfda_approval_tool import (  # noqa: E402
    DRUGSFDA_DRUG_NAME_FIELDS,
    OpenFDAApprovalTool,
    build_drug_name_query,
)

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(tooluniverse.__file__).parent / "data" / "openfda_approval_tools.json"
)

# The two doses the old `sorted(...)[:5]` dropped. Named explicitly because the
# regression is not "a list got shorter", it is "these specific high doses
# disappeared".
DROPPED_BY_THE_OLD_CUT = [
    "7.2MG/0.75ML (7.2MG/0.75ML)",
    "9.6MG/3ML (3.2MG/ML)",
]

# NDA215256 as openFDA actually returns it: 12 products, 7 distinct strengths,
# three product brand names, and `"openfda": {}` -- the empty block that made
# the application invisible to the old name query and blanked its brand_name.
NDA215256 = {
    "application_number": "NDA215256",
    "sponsor_name": "NOVO",
    "openfda": {},
    "submissions": [
        {
            "submission_type": "ORIG",
            "submission_number": "1",
            "submission_status": "AP",
            "submission_status_date": "20210604",
        },
        {
            "submission_type": "SUPPL",
            "submission_number": "12",
            "submission_status": "AP",
            "submission_status_date": "20250820",
        },
    ],
    "products": [
        {
            "product_number": product_number,
            "brand_name": brand_name,
            "active_ingredients": [{"name": "SEMAGLUTIDE", "strength": strength}],
            "dosage_form": "SOLUTION",
            "route": "SUBCUTANEOUS",
            "marketing_status": "Prescription",
        }
        for product_number, brand_name, strength in [
            ("001", "WEGOVY", "0.25MG/0.5ML (0.25MG/0.5ML)"),
            ("002", "WEGOVY", "0.5MG/0.5ML (0.5MG/0.5ML)"),
            ("003", "WEGOVY", "1MG/0.5ML (1MG/0.5ML)"),
            ("004", "WEGOVY", "1.7MG/0.75ML (1.7MG/0.75ML)"),
            ("005", "WEGOVY", "2.4MG/0.75ML (2.4MG/0.75ML)"),
            ("006", "WEGOVY HD", "7.2MG/0.75ML (7.2MG/0.75ML)"),
            ("007", "WEGOVY", "0.25MG/0.5ML (0.25MG/0.5ML)"),
            ("008", "WEGOVY", "0.5MG/0.5ML (0.5MG/0.5ML)"),
            ("009", "WEGOVY", "1MG/0.5ML (1MG/0.5ML)"),
            ("010", "WEGOVY", "1.7MG/0.75ML (1.7MG/0.75ML)"),
            ("011", "WEGOVY", "2.4MG/0.75ML (2.4MG/0.75ML)"),
            ("012", "WEGOVY FLEXTOUCH", "9.6MG/3ML (3.2MG/ML)"),
        ]
    ],
}

# NDA209637 -- the Ozempic INJECTION, empty openfda block, approved 2017-12-05.
NDA209637 = {
    "application_number": "NDA209637",
    "sponsor_name": "NOVO",
    "openfda": {},
    "submissions": [
        {
            "submission_type": "ORIG",
            "submission_number": "1",
            "submission_status": "AP",
            "submission_status_date": "20171205",
        }
    ],
    "products": [
        {
            "product_number": "001",
            "brand_name": "OZEMPIC",
            "active_ingredients": [
                {"name": "SEMAGLUTIDE", "strength": "2MG/1.5ML (1.34MG/ML)"}
            ],
            "dosage_form": "SOLUTION",
            "route": "SUBCUTANEOUS",
            "marketing_status": "Prescription",
        }
    ],
}

# NDA213051 -- the ORAL tablet, the record the old query returned for "Ozempic".
NDA213051 = {
    "application_number": "NDA213051",
    "sponsor_name": "NOVO",
    "openfda": {"brand_name": ["OZEMPIC", "RYBELSUS"], "generic_name": ["SEMAGLUTIDE"]},
    "submissions": [
        {
            "submission_type": "ORIG",
            "submission_number": "1",
            "submission_status": "AP",
            "submission_status_date": "20190920",
        }
    ],
    "products": [
        {
            "product_number": "001",
            "brand_name": "RYBELSUS",
            "active_ingredients": [{"name": "SEMAGLUTIDE", "strength": "7MG"}],
            "dosage_form": "TABLET",
            "route": "ORAL",
            "marketing_status": "Prescription",
        }
    ],
}


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly on any real egress, through every door these tools use."""

    def _blocked(*args, **kwargs):  # pragma: no cover - only runs on a leak
        raise AssertionError("network call attempted in a hermetic test")

    monkeypatch.setattr(requests, "request", _blocked)
    monkeypatch.setattr(requests.Session, "request", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(requests, "get", _blocked)


@pytest.fixture
def tool():
    return OpenFDAApprovalTool({"name": "test", "parameter": {}})


@pytest.fixture
def wegovy_summary(tool):
    """The `search_approvals` summary for NDA215256, served from the fixture."""
    fake_get, _ = _serve([NDA215256])
    with patch.object(requests, "get", fake_get):
        result = tool.run({"operation": "search_approvals", "drug_name": "Wegovy"})
    return result["data"]["approvals"][0]


def _serve(results, total=None):
    """Stub `requests.get` with a canned drugsfda payload; capture the query."""
    seen = {}

    def _fake_get(url, params=None, timeout=None):
        seen["url"] = url
        seen["params"] = params or {}
        return _FakeResponse(
            {
                "meta": {
                    "results": {"total": len(results) if total is None else total}
                },
                "results": results,
            }
        )

    return _fake_get, seen


# --------------------------------------------------------------------------
# Defect 1: completeness of the lists a summary reports
# --------------------------------------------------------------------------


def test_all_seven_wegovy_strengths_survive(wegovy_summary):
    """12 products, 7 distinct strengths, and all 7 come back."""
    assert wegovy_summary["application_number"] == "NDA215256"
    assert wegovy_summary["product_count"] == 12
    assert len(wegovy_summary["strengths"]) == 7


def test_the_two_highest_doses_are_not_dropped(wegovy_summary):
    """The exact regression: `sorted(...)[:5]` deleted the top two doses.

    Lexicographic order put 7.2MG and 9.6MG last, so the slice removed the two
    highest-dose Wegovy presentations while `product_count: 12` sat beside the
    list implying nothing was missing.
    """
    for dose in DROPPED_BY_THE_OLD_CUT:
        assert dose in wegovy_summary["strengths"], f"{dose} was dropped again"


def test_strengths_are_ordered_by_dose_not_alphabet(wegovy_summary):
    """A dose list is read as a ladder; make the ordering match the reading."""
    assert wegovy_summary["strengths"] == [
        "0.25MG/0.5ML (0.25MG/0.5ML)",
        "0.5MG/0.5ML (0.5MG/0.5ML)",
        "1MG/0.5ML (1MG/0.5ML)",
        "1.7MG/0.75ML (1.7MG/0.75ML)",
        "2.4MG/0.75ML (2.4MG/0.75ML)",
        "7.2MG/0.75ML (7.2MG/0.75ML)",
        "9.6MG/3ML (3.2MG/ML)",
    ]


def test_product_count_never_sits_beside_an_undisclosed_truncation(wegovy_summary):
    """`strength_count` must equal the length of the list actually returned.

    If a cap is ever reintroduced, this fails unless the response also discloses
    the true distinct count -- `product_count` alone must never be the only
    number next to the list.
    """
    distinct = {
        ingredient["strength"]
        for product in NDA215256["products"]
        for ingredient in product["active_ingredients"]
    }
    assert wegovy_summary["strength_count"] == len(distinct) == 7
    assert len(wegovy_summary["strengths"]) == wegovy_summary["strength_count"]


def test_brand_and_generic_names_are_complete_and_product_sourced(wegovy_summary):
    """`openfda` is empty for NDA215256; the product names still identify it.

    The old code read `openfda.brand_name[:3]` only, so this record reported
    `brand_name: null` despite three plainly named products, and the `[:3]` cut
    would have hidden a fourth had one existed.
    """
    assert wegovy_summary["brand_name"] == "WEGOVY, WEGOVY FLEXTOUCH, WEGOVY HD"
    assert wegovy_summary["generic_name"] == "SEMAGLUTIDE"


# --------------------------------------------------------------------------
# Defect 2: the name query must reach the authoritative per-product fields
# --------------------------------------------------------------------------


def test_name_query_searches_products_brand_name():
    """Without this field Wegovy is unreachable by name (live total 0 vs 2)."""
    assert "products.brand_name" in DRUGSFDA_DRUG_NAME_FIELDS
    assert 'products.brand_name:"Wegovy"' in build_drug_name_query("Wegovy")


def test_name_query_keeps_the_openfda_fields_too():
    """The union is additive -- dropping the resolved fields loses other drugs."""
    for field in ("openfda.brand_name", "openfda.generic_name"):
        assert field in DRUGSFDA_DRUG_NAME_FIELDS


def test_name_query_is_a_parenthesized_or_group():
    """It is joined to sponsor / application_number filters with AND.

    Unparenthesized, the trailing AND would bind to the last OR branch only and
    the filter would be silently ignored for every other branch.
    """
    query = build_drug_name_query("Wegovy")
    assert query.startswith("(") and query.endswith(")")
    assert query.count(" OR ") == len(DRUGSFDA_DRUG_NAME_FIELDS) - 1
    assert " AND " not in query


def test_search_approvals_sends_the_widened_parenthesized_query(tool):
    fake_get, seen = _serve([NDA215256])
    with patch.object(requests, "get", fake_get):
        result = tool.run(
            {"operation": "search_approvals", "drug_name": "Wegovy", "sponsor": "NOVO"}
        )

    sent = seen["params"]["search"]
    assert sent == build_drug_name_query("Wegovy") + ' AND sponsor_name:"NOVO"'
    assert result["data"]["query"] == sent


def test_ozempic_returns_the_injection_alongside_the_tablet(tool):
    """Both applications, so the 2017-12-05 injection is no longer unreachable."""
    fake_get, _ = _serve([NDA213051, NDA209637])
    with patch.object(requests, "get", fake_get):
        result = tool.run({"operation": "search_approvals", "drug_name": "Ozempic"})

    by_number = {a["application_number"]: a for a in result["data"]["approvals"]}
    assert set(by_number) == {"NDA213051", "NDA209637"}
    assert by_number["NDA209637"]["original_approval_date"] == "2017-12-05"
    assert by_number["NDA213051"]["original_approval_date"] == "2019-09-20"


def test_single_application_operations_disclose_the_siblings(tool):
    """These ops describe one application; they must say which ones they didn't.

    `get_approved_products(drug_name="Ozempic")` can only return one record.
    Returning the tablet without naming NDA209637 is how "wrong product,
    confidently" happens.
    """
    fake_get, _ = _serve([NDA213051, NDA209637])
    with patch.object(requests, "get", fake_get):
        result = tool.run(
            {"operation": "get_approved_products", "drug_name": "Ozempic"}
        )

    data = result["data"]
    assert data["application_number"] == "NDA213051"
    assert data["matching_applications"] == 2
    assert data["other_matching_applications"] == ["NDA209637"]
    assert data["other_matching_applications_truncated"] is False


def test_sibling_list_never_repeats_the_defect_it_was_added_to_fix(tool):
    """Only NAME_CANDIDATE_LIMIT records are fetched, so the list can fall short.

    A sibling list cut off beside `matching_applications` is the exact shape of
    the `strengths` defect this module just removed -- a truncated list next to
    a count implying it is complete. It must be flagged, not left to be read as
    exhaustive.
    """
    fake_get, _ = _serve([NDA213051, NDA209637], total=40)
    with patch.object(requests, "get", fake_get):
        result = tool.run(
            {"operation": "get_approved_products", "drug_name": "Ozempic"}
        )

    data = result["data"]
    assert data["matching_applications"] == 40
    assert len(data["other_matching_applications"]) == 1
    assert data["other_matching_applications_truncated"] is True


def test_approval_history_uses_the_same_widened_query(tool):
    """All three operations must resolve names through one field list."""
    fake_get, seen = _serve([NDA215256])
    with patch.object(requests, "get", fake_get):
        result = tool.run({"operation": "get_approval_history", "drug_name": "Wegovy"})

    assert seen["params"]["search"] == build_drug_name_query("Wegovy")
    assert result["data"]["application_number"] == "NDA215256"
    assert result["data"]["brand_name"] == "WEGOVY, WEGOVY FLEXTOUCH, WEGOVY HD"


def test_application_number_lookup_is_left_alone(tool):
    """Only the name clause widened; an explicit application number stays exact."""
    fake_get, seen = _serve([NDA215256])
    with patch.object(requests, "get", fake_get):
        tool.run(
            {"operation": "get_approval_history", "application_number": "NDA215256"}
        )

    assert seen["params"]["search"] == 'application_number:"NDA215256"'


# --------------------------------------------------------------------------
# The JSON config must describe what the code now returns
# --------------------------------------------------------------------------


def test_config_documents_the_new_disclosure_fields():
    configs = {c["name"]: c for c in json.loads(CONFIG_PATH.read_text())}

    search_items = configs["OpenFDA_search_drug_approvals"]["return_schema"][
        "properties"
    ]["approvals"]["items"]["properties"]
    assert "strength_count" in search_items

    for name in ("OpenFDA_get_approval_history", "OpenFDA_get_approved_products"):
        properties = configs[name]["return_schema"]["properties"]
        assert "matching_applications" in properties
        assert "other_matching_applications" in properties
        assert "other_matching_applications_truncated" in properties
