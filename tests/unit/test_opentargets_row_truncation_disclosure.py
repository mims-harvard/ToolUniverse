"""Open Targets ``count`` + ``rows`` collections must disclose partial pages.

Regression: ``OpenTargets_get_drug_adverse_events_by_chemblId`` for CHEMBL521
(ibuprofen) returned an ``adverseEvents`` object holding ``count: 55``,
``criticalValue: 514.94`` and exactly 25 rows, with no truncation flag and no
note anywhere in the response. ``count`` sitting directly beside a shorter
``rows`` list reads either as "the number of rows you were given" or makes the
25 rows look like the complete set; 30 adverse-event signals were dropped in
silence. For ibuprofen the dropped rows include toxic epidermal necrolysis,
urticaria, systemic lupus erythematosus and hepatic enzyme increased -- exactly
the signals a safety reviewer is looking for, so the truncated answer was
well-formed, confident and unsafe to act on.

The 25 is the Open Targets API's own default page size, not anything this repo
sets: the tool config declares no default for ``page``, ``GraphQLTool.run``
only injects a default for a flat ``size`` parameter, and probing the v4 API
directly with ``page`` omitted returns 25 rows beside ``count: 55`` while
``page: {index: 0, size: 60}`` returns all 55.

The fix is purely additive: every ``count`` + ``rows`` container gains
``returned`` and ``truncated`` beside the untouched ``count``/``rows``, and a
``metadata.truncation_note`` names the real total, how many rows came back and
the exact argument that fetches the rest. The same code path serves the other
Open Targets collections that truncate identically -- measured live at 25 of
41523 publications, 25 of 8626 interactions and 25 of 5638 associated diseases.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import tooluniverse
from tooluniverse.graphql_tool import OpentargetTool

pytestmark = pytest.mark.unit

_CONFIG = Path(tooluniverse.__file__).parent / "data" / "opentarget_tools.json"
ADVERSE_EVENTS = "OpenTargets_get_drug_adverse_events_by_chemblId"


def _tool_config(name):
    for entry in json.loads(_CONFIG.read_text()):
        if isinstance(entry, dict) and entry.get("name") == name:
            return entry
    raise AssertionError(f"{name} not found in {_CONFIG}")


def _mock_post(payload):
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = payload
    return resp


def _adverse_events_payload(count, n_rows):
    return {
        "data": {
            "drug": {
                "id": "CHEMBL521",
                "name": "IBUPROFEN",
                "adverseEvents": {
                    "count": count,
                    "criticalValue": 514.9413841626665,
                    "rows": [
                        {
                            "name": f"event{i}",
                            "meddraCode": "",
                            "count": 100 + i,
                            "logLR": 1000.0 - i,
                        }
                        for i in range(n_rows)
                    ],
                },
            }
        }
    }


def _run(name, payload, arguments):
    tool = OpentargetTool(_tool_config(name))
    with patch("tooluniverse.graphql_tool.requests.post") as post:
        post.return_value = _mock_post(payload)
        return tool.run(arguments)


def test_partial_page_is_flagged_and_explained():
    """25 rows beside count 55 must say so, and say how to get the other 30."""
    result = _run(
        ADVERSE_EVENTS, _adverse_events_payload(55, 25), {"chemblId": "CHEMBL521"}
    )

    events = result["data"]["drug"]["adverseEvents"]
    assert events["count"] == 55, "the real total must not be rewritten"
    assert len(events["rows"]) == 25, "the delivered rows must not be changed"
    assert events["returned"] == 25
    assert events["truncated"] is True

    note = result["metadata"]["truncation_note"]
    assert "25 of 55" in note
    # The exact argument that fetches the remainder, not just "there is more".
    assert '{"index": 0, "size": 55}' in note


def test_complete_page_is_not_flagged():
    """rows == count means nothing is missing: truncated False, no note."""
    result = _run(
        ADVERSE_EVENTS,
        _adverse_events_payload(55, 55),
        {"chemblId": "CHEMBL521", "page": {"index": 0, "size": 60}},
    )

    events = result["data"]["drug"]["adverseEvents"]
    assert events["returned"] == 55
    assert events["truncated"] is False
    assert "truncation_note" not in result.get("metadata", {})


def test_collection_without_a_count_is_left_alone():
    """``mechanismsOfAction { rows }`` reports no total, so truncation is not
    detectable there -- the payload must come back untouched rather than gain a
    flag that cannot be computed honestly."""
    payload = {
        "data": {
            "drug": {
                "id": "CHEMBL521",
                "name": "IBUPROFEN",
                "mechanismsOfAction": {
                    "rows": [{"mechanismOfAction": "COX inhibitor"}],
                },
            }
        }
    }
    result = _run(
        "OpenTargets_get_drug_mechanisms_of_action_by_chemblId",
        payload,
        {"chemblId": "CHEMBL521"},
    )

    moa = result["data"]["drug"]["mechanismsOfAction"]
    assert "truncated" not in moa
    assert "returned" not in moa
    assert "truncation_note" not in result.get("metadata", {})


def test_rows_of_a_collection_are_not_themselves_annotated():
    """An adverse-event row carries its own report ``count`` but no ``rows``
    list, so it must not be mistaken for a paginated collection."""
    result = _run(
        ADVERSE_EVENTS, _adverse_events_payload(55, 25), {"chemblId": "CHEMBL521"}
    )
    for row in result["data"]["drug"]["adverseEvents"]["rows"]:
        assert "truncated" not in row
        assert "returned" not in row


def test_hint_matches_how_the_tool_actually_paginates():
    """The remedy is read off the tool's own parameters: a ``size``/``index``
    tool must not be told to pass a ``page`` object, and a tool with no
    pagination parameter must not be told to pass one at all."""
    payload = {
        "data": {
            "disease": {
                "id": "MONDO_0005011",
                "name": "Crohn disease",
                "associatedTargets": {
                    "count": 6289,
                    "rows": [
                        {"target": {"id": f"ENSG{i}"}, "score": 0.5} for i in range(50)
                    ],
                },
            }
        }
    }
    note = _run(
        "OpenTargets_get_associated_targets_by_disease_efoId",
        payload,
        {"efoId": "MONDO_0005011"},
    )["metadata"]["truncation_note"]
    assert "size: 3000" in note, "must be clamped to the API's page ceiling"
    assert "index: 0" in note
    assert '{"index"' not in note

    payload = {
        "data": {
            "drug": {
                "id": "CHEMBL521",
                "name": "IBUPROFEN",
                "literatureOcurrences": {
                    "count": 41523,
                    "rows": [{"pmid": str(i)} for i in range(25)],
                },
            }
        }
    }
    note = _run(
        "OpenTargets_get_publications_by_drug_chemblId",
        payload,
        {"entityId": "CHEMBL521"},
    )["metadata"]["truncation_note"]
    assert "25 of 41523" in note
    assert "no pagination parameter" in note


def test_baseline_expression_keeps_its_own_page_aware_disclosure():
    """OpenTargets_get_target_expression_by_ensemblID already computes a
    truncation flag that accounts for the rows skipped by ``index``; the
    generic pass must not overwrite it with an index-blind one."""
    payload = {
        "data": {
            "target": {
                "id": "ENSG00000167634",
                "approvedSymbol": "NLRP7",
                "baselineExpression": {
                    "count": 900,
                    "rows": [{"datasourceId": "gtex"} for _ in range(400)],
                },
            }
        }
    }
    result = _run(
        "OpenTargets_get_target_expression_by_ensemblID",
        payload,
        {"ensemblId": "ENSG00000167634", "size": 500, "index": 1},
    )
    expr = result["data"]["target"]["baselineExpression"]
    # 500 skipped + 400 returned == 900, so nothing is missing despite
    # len(rows) < count, which an index-blind check would call truncated.
    assert expr["truncated"] is False
    assert "truncation_note" not in result.get("metadata", {})


def test_config_declares_the_new_keys():
    config = _tool_config(ADVERSE_EVENTS)
    events_props = config["return_schema"]["properties"]["drug"]["properties"][
        "adverseEvents"
    ]["properties"]
    assert events_props["returned"]["type"] == "integer"
    assert events_props["truncated"]["type"] == "boolean"
    assert events_props["count"]["type"] == "integer"

    description = config["description"]
    assert "truncated" in description
    assert "returned" in description
