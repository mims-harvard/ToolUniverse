from typing import Any

from tooluniverse.eol_tool import EOLTool


def test_hierarchy_children_are_pageable_with_true_total(monkeypatch) -> None:
    payload: dict[str, Any] = {
        "taxonID": 1,
        "scientificName": "Aves",
        "children": [
            {
                "taxonID": index,
                "scientificName": f"Child {index}",
                "taxonConceptID": index,
            }
            for index in range(25)
        ],
    }

    monkeypatch.setattr(
        "tooluniverse.eol_tool._eol_http_get", lambda *args, **kwargs: payload
    )
    tool = EOLTool({"fields": {"endpoint": "hierarchy_entries"}})

    result = tool.run(
        {"hierarchy_entry_id": 136838168, "child_limit": 3, "child_offset": 20}
    )

    assert result["status"] == "success"
    assert [child["scientific_name"] for child in result["data"]["children"]] == [
        "Child 20",
        "Child 21",
        "Child 22",
    ]
    assert result["metadata"]["num_children"] == 25
    assert result["metadata"]["children_returned"] == 3
    assert result["metadata"]["children_truncated"] is True
    assert result["metadata"]["next_child_offset"] == 23
