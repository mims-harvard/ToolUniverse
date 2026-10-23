from unittest.mock import patch

import pytest

from tooluniverse.aopwiki_tool import AOPWikiDetailTool, AOPWikiListTool


pytestmark = pytest.mark.unit


def _page(current, total_pages, total_entries, ids):
    return {
        "aops": [
            {"id": item, "title": f"AOP {item}", "short_name": f"Short {item}"}
            for item in ids
        ],
        "pagination": {
            "current_page": current,
            "per_page": 500,
            "total_entries": total_entries,
            "total_pages": total_pages,
        },
    }


def test_list_fetches_and_certifies_every_page():
    tool = AOPWikiListTool({})
    with patch(
        "tooluniverse.aopwiki_tool._get_json",
        side_effect=[_page(1, 2, 3, [1, 2]), _page(2, 2, 3, [3])],
    ) as get:
        result = tool.run({"search": "aop"})
    assert get.call_count == 2
    assert result["status"] == "success"
    assert result["count"] == 3
    assert result["metadata"] == {
        "total_aops": 3,
        "total_aops_is_exact": True,
        "pages_fetched": 2,
        "result_set_complete": True,
    }


def test_list_rejects_missing_pagination_instead_of_assuming_complete():
    tool = AOPWikiListTool({})
    with patch(
        "tooluniverse.aopwiki_tool._get_json",
        return_value=[{"id": 1, "title": "AOP 1"}],
    ):
        result = tool.run({})
    assert result["status"] == "error"
    assert "completeness cannot be verified" in result["error"]


def test_list_rejects_repeated_ids_across_pages():
    tool = AOPWikiListTool({})
    with patch(
        "tooluniverse.aopwiki_tool._get_json",
        side_effect=[_page(1, 2, 3, [1, 2]), _page(2, 2, 3, [2])],
    ):
        result = tool.run({})
    assert result["status"] == "error"
    assert "repeated" in result["error"]


def test_aop_preserves_types_and_marks_relation_reference_opaque():
    payload = {
        "id": 3,
        "title": "AOP 3",
        "aop_stressors": [],
        "aop_mies": [
            {
                "event_id": 888,
                "event": "Binding",
                "event_type": "MolecularInitiatingEvent",
            }
        ],
        "aop_kes": [{"event_id": 887, "event": "Inhibition", "event_type": "KeyEvent"}],
        "aop_aos": [
            {"event_id": 896, "event": "Deficit", "event_type": "AdverseOutcome"}
        ],
        "relationships": [
            {
                "relation": 604,
                "upstream_event_id": 177,
                "upstream_event": "Dysfunction",
                "downstream_event_id": 890,
                "downstream_event": "Degeneration",
            }
        ],
    }
    tool = AOPWikiDetailTool({"settings": {}})
    with patch("tooluniverse.aopwiki_tool._get_json", return_value=payload):
        result = tool.run({"aop_id": 3})
    assert result["data"]["molecular_initiating_events"][0]["event_type"] == (
        "MolecularInitiatingEvent"
    )
    relation = result["data"]["relationships"][0]
    assert relation["source_relation"] == 604
    assert relation["source_relation_semantics"] == "opaque_aop_association_reference"
    assert (
        result["metadata"]["source_relation_values_safe_as_relationship_ids"] is False
    )


@pytest.mark.parametrize(
    ("settings", "arguments"),
    [
        ({}, {"aop_id": "3"}),
        ({}, {"aop_id": 0}),
        ({"endpoint_kind": "event"}, {"event_id": True}),
    ],
)
def test_invalid_identifiers_are_rejected_before_network(settings, arguments):
    tool = AOPWikiDetailTool({"settings": settings})
    with patch("tooluniverse.aopwiki_tool._get_json") as get:
        result = tool.run(arguments)
    assert result["status"] == "error"
    get.assert_not_called()
