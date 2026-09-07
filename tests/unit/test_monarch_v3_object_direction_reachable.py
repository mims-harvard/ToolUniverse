"""Unit test: MonarchV3_get_associations must expose the `object` side.

Regression: Biolink association categories are directed --
biolink:CausalGeneToDiseaseAssociation has the GENE as subject and the DISEASE
as object. `MonarchV3Tool._get_associations` already read an `object` argument
and forwarded it upstream, but the registered JSON schema exposed only
`subject` and marked it required, so the single most common question for that
category -- "which genes cause this disease?" -- was unreachable:

    {"object": "MONDO:0006559", ...}  -> rejected before reaching the tool
    {"subject": "MONDO:0006559", ...} -> accepted, confident empty list

Confirmed live against the API: object=MONDO:0006559 with that category
returns 3 rows (NCSTN, PSENEN, PSEN1). The schema now requires only
`category`, exposes `object`, and the tool itself rejects a call that supplies
neither anchor with an error naming both parameters.

Offline: `requests.get` in the tool module is patched.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.monarch_v3_tool import MonarchV3Tool

pytestmark = pytest.mark.unit

CATEGORY = "biolink:CausalGeneToDiseaseAssociation"
DISEASE = "MONDO:0006559"

# Shape of https://api.monarchinitiative.org/v3/api/association/all
# ?object=MONDO:0006559&category=biolink:CausalGeneToDiseaseAssociation
OBJECT_SIDE_RESPONSE = {
    "total": 3,
    "items": [
        {
            "subject": "HGNC:17091",
            "subject_label": "NCSTN",
            "object": "MONDO:0007728",
            "object_label": "acne inversa, familial, 1",
            "category": CATEGORY,
            "predicate": "biolink:causes",
            "negated": None,
            "provided_by": "omim_gene_to_disease_edges",
            "primary_knowledge_source": "infores:omim",
        },
        {
            "subject": "HGNC:30100",
            "subject_label": "PSENEN",
            "object": "MONDO:0013397",
            "object_label": "acne inversa, familial, 2",
            "category": CATEGORY,
            "predicate": "biolink:causes",
            "negated": None,
            "provided_by": "omim_gene_to_disease_edges",
            "primary_knowledge_source": "infores:omim",
        },
        {
            "subject": "HGNC:9508",
            "subject_label": "PSEN1",
            "object": "MONDO:0013398",
            "object_label": "acne inversa, familial, 3",
            "category": CATEGORY,
            "predicate": "biolink:causes",
            "negated": None,
            "provided_by": "omim_gene_to_disease_edges",
            "primary_knowledge_source": "infores:omim",
        },
    ],
}

SUBJECT_SIDE_RESPONSE = {
    "total": 1,
    "items": [OBJECT_SIDE_RESPONSE["items"][0]],
}

EMPTY_RESPONSE = {"total": 0, "items": []}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _tool():
    return MonarchV3Tool(
        {
            "name": "MonarchV3_get_associations",
            "type": "MonarchV3Tool",
            "parameter": {"properties": {}},
            "fields": {"endpoint": "associations"},
        }
    )


def _run(arguments, payload):
    """Run the tool with requests.get patched; return (result, captured params)."""
    captured = {}

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse(payload)

    with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
        result = _tool().run(arguments)
    return result, captured


# --- the schema must actually expose `object` --------------------------------


def _associations_schema():
    import json

    config_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "tooluniverse"
        / "data"
        / "monarch_v3_tools.json"
    )
    configs = json.loads(config_path.read_text())
    for cfg in configs:
        if cfg.get("name") == "MonarchV3_get_associations":
            return cfg["parameter"]
    raise AssertionError("MonarchV3_get_associations not found in monarch_v3_tools.json")


def test_schema_exposes_object_parameter():
    schema = _associations_schema()
    assert "object" in schema["properties"], (
        "the implementation forwards an `object` argument upstream; the schema "
        "must expose it or disease->gene queries are unreachable"
    )
    assert "subject" in schema["properties"]


def test_schema_does_not_force_subject():
    # subject must be optional so an object-only call validates; `category`
    # stays required exactly as before.
    schema = _associations_schema()
    assert "subject" not in schema["required"]
    assert "object" not in schema["required"]
    assert "category" in schema["required"]


def test_schema_documents_the_direction():
    schema = _associations_schema()
    obj_doc = schema["properties"]["object"]["description"].lower()
    assert "object" in obj_doc
    assert "disease" in obj_doc


# --- object-only call: accepted, forwarded, parsed ---------------------------


def test_object_only_call_forwards_object_upstream():
    result, captured = _run(
        {"object": DISEASE, "category": CATEGORY, "limit": 20},
        OBJECT_SIDE_RESPONSE,
    )

    assert result["status"] == "success"
    assert captured["params"]["object"] == DISEASE
    assert "subject" not in captured["params"], (
        "an object-only query must not be silently rewritten onto the subject side"
    )
    assert captured["params"]["category"] == CATEGORY
    assert captured["params"]["limit"] == 20


def test_object_only_call_returns_the_three_causal_genes():
    result, _ = _run({"object": DISEASE, "category": CATEGORY}, OBJECT_SIDE_RESPONSE)

    assert len(result["data"]) == 3
    assert [row["subject"] for row in result["data"]] == [
        "HGNC:17091",
        "HGNC:30100",
        "HGNC:9508",
    ]
    assert [row["subject_label"] for row in result["data"]] == [
        "NCSTN",
        "PSENEN",
        "PSEN1",
    ]
    assert result["metadata"]["object"] == DISEASE
    assert result["metadata"]["total_results"] == 3


def test_object_curie_is_normalized_like_subject():
    _, captured = _run(
        {"object": "MONDO_0006559", "category": CATEGORY}, OBJECT_SIDE_RESPONSE
    )
    assert captured["params"]["object"] == "MONDO:0006559"


# --- subject-only call: unchanged -------------------------------------------


def test_subject_only_call_unchanged():
    result, captured = _run(
        {"subject": "HGNC:17091", "category": CATEGORY, "limit": 5},
        SUBJECT_SIDE_RESPONSE,
    )

    assert result["status"] == "success"
    assert captured["params"]["subject"] == "HGNC:17091"
    assert "object" not in captured["params"]
    assert captured["params"]["limit"] == 5
    assert len(result["data"]) == 1
    assert result["data"][0]["object"] == "MONDO:0007728"
    assert result["metadata"]["subject"] == "HGNC:17091"
    assert result["metadata"]["category"] == CATEGORY
    assert result["metadata"]["total_results"] == 1


def test_both_sides_may_be_supplied_together():
    _, captured = _run(
        {"subject": "HGNC:17091", "object": "MONDO:0007728", "category": CATEGORY},
        SUBJECT_SIDE_RESPONSE,
    )
    assert captured["params"]["subject"] == "HGNC:17091"
    assert captured["params"]["object"] == "MONDO:0007728"


# --- neither side supplied: clear error naming both --------------------------


def test_neither_subject_nor_object_is_a_clear_error():
    called = []

    def fake_get(url, params=None, timeout=None):  # pragma: no cover - must not run
        called.append(url)
        return _FakeResponse(EMPTY_RESPONSE)

    with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
        result = _tool().run({"category": CATEGORY})

    assert result["status"] == "error"
    assert "subject" in result["error"]
    assert "object" in result["error"]
    assert not called, "no upstream request should be made without an anchor CURIE"


# --- zero results keep status success, but hint at the direction -------------


def test_wrong_side_zero_result_stays_success_and_hints():
    result, _ = _run(
        {"subject": DISEASE, "category": CATEGORY, "limit": 20}, EMPTY_RESPONSE
    )

    assert result["status"] == "success", "an empty result must not become an error"
    assert result["data"] == []
    note = result["metadata"].get("note", "")
    assert "object" in note and DISEASE in note


def test_correct_side_zero_result_has_no_misleading_hint():
    # A gene subject is on the right side for this category; an empty result
    # there just means "no known causal disease", not a direction mistake.
    result, _ = _run({"subject": "HGNC:11998", "category": CATEGORY}, EMPTY_RESPONSE)

    assert result["status"] == "success"
    assert "note" not in result["metadata"]


def test_non_empty_result_carries_no_hint():
    result, _ = _run({"object": DISEASE, "category": CATEGORY}, OBJECT_SIDE_RESPONSE)
    assert "note" not in result["metadata"]
