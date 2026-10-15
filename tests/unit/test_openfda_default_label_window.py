"""Without a caller limit, label tools show the first labels and an inventory of the rest.

``FDA_get_adverse_reactions_by_drug_name`` for ibuprofen with no ``limit``
returned 100 labels and 514k characters, nearly all the same drug from other
manufacturers. With no caller limit the tools still fetch up to 100 labels, but
return the first ``DEFAULT_LABEL_WINDOW`` (8) in openFDA's order plus a
``label_inventory`` that counts every matched label by route, so an injectable
or topical label the window left out is one call away. An explicit ``limit`` is
honoured exactly as before.

Everything mocks the HTTP layer -- no network.
"""

import urllib.parse
from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import (
    DEFAULT_LABEL_WINDOW,
    FDADrugLabelTool,
    _default_label_window,
)


def _row(route=None, generic="DRUG X", brand=None, text="Dosage text."):
    row = {
        "dosage_and_administration": [text],
        "openfda.generic_name": [generic] if generic else None,
        "openfda.brand_name": [brand] if brand else None,
    }
    if route:
        row["openfda.route"] = route
    return row


def _result(rows):
    return {
        "meta": {"total": 250, "limit": 100},
        "results": rows,
        "result_count": len(rows),
        "duplicates_removed": 0,
        "note": "broadened match",
    }


def test_the_window_is_eight_labels():
    assert DEFAULT_LABEL_WINDOW == 8


def test_first_eight_in_openfda_order_with_an_inventory_of_all():
    rows = (
        [_row(["ORAL"], text=f"oral {i}") for i in range(62)]
        + [_row(["INTRAMUSCULAR"], text="im")] * 13
        + [_row(None, generic=None, text="no id")] * 20
        + [_row(["ORAL"], generic="X AND Y")] * 5
    )
    out = _default_label_window(_result(rows), {"drug_name": "x"})
    assert out["results"] == rows[:8]
    assert out["result_count"] == 8
    inventory = out["label_inventory"]
    assert (inventory["labels_matched"], inventory["labels_shown"]) == (100, 8)
    assert inventory["routes_of_all_matched_labels"] == {
        "ORAL": 67,
        "not stated": 20,
        "INTRAMUSCULAR": 13,
    }
    # most common route first
    assert list(inventory["routes_of_all_matched_labels"]) == [
        "ORAL",
        "not stated",
        "INTRAMUSCULAR",
    ]
    assert inventory["routes_of_shown_labels"] == ["ORAL"]
    assert inventory["combination_products_matched"] == 5
    assert inventory["labels_without_product_identity"] == 20
    assert "Showing the first 8 of 100 labels" in out["label_window_note"]
    assert "INTRAMUSCULAR 13" in out["label_window_note"]
    assert "call again with limit" in out["label_window_note"]
    # everything else the tool said is kept
    assert out["meta"] == {"total": 250, "limit": 100}
    assert out["note"] == "broadened match"
    assert out["duplicates_removed"] == 0


@pytest.mark.parametrize("limit", [100, 40, 3, 0])
def test_an_explicit_limit_is_honoured_exactly(limit):
    result = _result([_row(["ORAL"])] * 40)
    assert _default_label_window(result, {"drug_name": "x", "limit": limit}) is result


def test_short_results_and_other_shapes_are_untouched():
    short = _result([_row(["ORAL"])] * 8)
    assert _default_label_window(short, {"drug_name": "x"}) is short
    for odd in ({"error": {"code": "NOT_FOUND"}}, "text", None, {"results": "x"}):
        assert _default_label_window(odd, {"drug_name": "x"}) is odd
    long_result = _result([_row()] * 20)
    assert _default_label_window(long_result, None) is long_result


def test_it_never_raises_and_never_adds_a_label():
    odd = _result([None, 3, "x"] + [_row(["ORAL"])] * 20 + [{"openfda.route": "ORAL"}])
    out = _default_label_window(odd, {"drug_name": "x"})
    assert out["results"] == odd["results"][:8]
    assert out["label_inventory"]["labels_matched"] == 24
    broken = {"results": [_row()] * 20}
    broken["results"][9] = {"openfda.route": object()}
    assert len(_default_label_window(broken, {})["results"]) <= 20


def test_the_input_result_is_not_mutated():
    result = _result([_row(["ORAL"])] * 30)
    _default_label_window(result, {"drug_name": "x"})
    assert len(result["results"]) == 30
    assert "label_inventory" not in result


# --- through the real tool --------------------------------------------------


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _tool():
    return FDADrugLabelTool(
        {
            "name": "FDA_get_adverse_reactions_by_drug_name",
            "description": "adverse reactions",
            "type": "FDADrugLabel",
            "parameter": {
                "type": "object",
                "properties": {"drug_name": {"type": "string"}},
                "required": ["drug_name"],
            },
            "fields": {
                "search_fields": {
                    "drug_name": ["openfda.brand_name", "openfda.generic_name"]
                },
                "return_fields": ["adverse_reactions"],
            },
        }
    )


def _labels(n):
    routes = ["ORAL"] * (n - 3) + ["INTRAVENOUS"] * 3
    return [
        {
            "id": f"id-{i}",
            "set_id": f"set-{i}",
            "openfda": {
                "brand_name": [f"Brand {i}"],
                "generic_name": ["IBUPROFEN"],
                "route": [routes[i]],
            },
            "adverse_reactions": [f"Adverse reactions of label {i} ..."],
        }
        for i in range(n)
    ]


def _serve(labels):
    seen = []

    def fake_get(url, *args, **kwargs):
        seen.append(urllib.parse.unquote_plus(url))
        return _FakeResponse(
            {
                "meta": {"results": {"skip": 0, "limit": 100, "total": len(labels)}},
                "results": labels,
            }
        )

    return fake_get, seen


def test_the_label_tool_without_a_limit_shows_eight_and_counts_all():
    fake_get, seen = _serve(_labels(20))
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = _tool().run({"drug_name": "ibuprofen"})
    assert "limit=100" in seen[0]  # the fetch itself is unchanged
    assert len(out["results"]) == 8
    assert out["label_inventory"]["labels_matched"] == 20
    assert out["label_inventory"]["routes_of_all_matched_labels"] == {
        "ORAL": 17,
        "INTRAVENOUS": 3,
    }
    assert out["label_inventory"]["routes_of_shown_labels"] == ["ORAL"]
    assert out["results"][0]["openfda.route"] == ["ORAL"]


def test_the_label_tool_with_a_limit_returns_what_was_asked_for():
    fake_get, _ = _serve(_labels(20))
    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        out = _tool().run({"drug_name": "ibuprofen", "limit": 20})
    assert len(out["results"]) == 20
    assert "label_inventory" not in out
