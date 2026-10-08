"""MGnify_list_biomes: `depth` was sent to /biomes and rejected with HTTP 400.

The API has no depth or lineage filter on /biomes ("invalid query parameter"),
so depth is now filtered client-side on the lineage (root = 1) and `lineage`
lists a biome and its descendants. HTTP is mocked; shapes trimmed from the real API.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.mgnify_expanded_tool import MGnifyExpandedTool

pytestmark = pytest.mark.unit


def _tool():
    return MGnifyExpandedTool(
        {
            "name": "MGnify_list_biomes",
            "fields": {"endpoint_type": "biome", "query_mode": "list"},
        }
    )


def _biome(lineage, n=1):
    return {
        "id": lineage,
        "attributes": {
            "biome-name": lineage.split(":")[-1],
            "samples-count": n,
            "lineage": lineage,
        },
    }


def _resp(rows, page=1, pages=1, count=None):
    r = Mock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = {
        "data": rows,
        "meta": {
            "pagination": {
                "page": page,
                "pages": pages,
                "count": count if count is not None else len(rows),
            }
        },
    }
    return r


ROWS = [
    _biome("root:Engineered"),
    _biome("root:Host-associated"),
    _biome("root:Host-associated:Human"),
    _biome("root:Host-associated:Mammals"),
    _biome("root:Host-associated:Human:Digestive system"),
]


def test_depth_is_filtered_client_side_and_never_sent_to_the_api():
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        get.return_value = _resp(ROWS)
        out = _tool().run({"depth": 3})
    assert out["status"] == "success"
    assert [r["biome_id"] for r in out["data"]] == [
        "root:Host-associated:Human",
        "root:Host-associated:Mammals",
    ]
    assert out["metadata"]["total_results"] == 2
    for call in get.call_args_list:
        assert "depth" not in call.kwargs["params"]


def test_depth_walks_every_page_and_paginates_the_filtered_list():
    page1 = _resp([_biome(f"root:A:B{i}") for i in range(3)], page=1, pages=2)
    page2 = _resp([_biome(f"root:A:C{i}") for i in range(2)], page=2, pages=2)
    with patch(
        "tooluniverse.mgnify_expanded_tool.requests.get", side_effect=[page1, page2]
    ):
        out = _tool().run({"depth": 3, "page": 2, "page_size": 2})
    assert out["metadata"]["total_results"] == 5
    assert out["metadata"]["pages"] == 3
    assert [r["biome_id"] for r in out["data"]] == ["root:A:B2", "root:A:C0"]


def test_lineage_uses_the_children_endpoint():
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        get.return_value = _resp(
            [_biome("root:Host-associated:Human:Digestive system")]
        )
        out = _tool().run({"lineage": "root:Host-associated:Human"})
    url = get.call_args.args[0]
    assert url.endswith("/biomes/root:Host-associated:Human/children")
    assert out["data"][0]["biome_name"] == "Digestive system"


def test_no_depth_or_lineage_keeps_the_plain_paginated_listing():
    with patch("tooluniverse.mgnify_expanded_tool.requests.get") as get:
        get.return_value = _resp(ROWS, page=1, pages=98, count=491)
        out = _tool().run({"page_size": 5})
    assert get.call_args.args[0].endswith("/biomes")
    assert get.call_args.kwargs["params"]["page_size"] == 5
    assert out["metadata"]["total_results"] == 491
    assert out["metadata"]["pages"] == 98
