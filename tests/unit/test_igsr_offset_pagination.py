"""Regression tests for native/local IGSR offset pagination."""

from unittest.mock import patch

from tooluniverse.igsr_tool import IGSRTool


def _tool(operation):
    return IGSRTool(
        {
            "name": f"IGSR_{operation}",
            "parameter": {"properties": {"operation": {"default": operation}}},
        }
    )


def _hits(prefix, count, total=None):
    return {
        "hits": {
            "total": total if total is not None else count,
            "hits": [
                {
                    "_id": f"{prefix}{i}",
                    "_source": {
                        "name": f"{prefix}{i}",
                        "code": f"{prefix}{i}",
                        "samples": {"count": i},
                        "populations": [],
                        "dataCollections": [],
                    },
                }
                for i in range(count)
            ],
        }
    }


def test_sample_search_forwards_native_es_from():
    tool = _tool("search_samples")
    with patch.object(tool, "_es_search", return_value=_hits("HG", 3, 107)) as search:
        data = tool.run(
            {
                "operation": "search_samples",
                "population": "GBR",
                "limit": 3,
                "offset": 3,
            }
        )["data"]

    assert search.call_args.args[1]["from"] == 3
    assert data["total"] == 107
    assert data["offset"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 6


def test_superpopulation_offset_is_applied_after_client_filter():
    raw = {
        "hits": {
            "total": 8,
            "hits": [
                {
                    "_source": {
                        "code": f"P{i}",
                        "name": f"Population {i}",
                        "superpopulation": {
                            "code": "AFR" if i != 1 else "EUR",
                            "name": "African" if i != 1 else "European",
                        },
                        "samples": {"count": 1},
                    }
                }
                for i in range(8)
            ],
        }
    }
    tool = _tool("search_populations")
    with patch.object(tool, "_es_search", return_value=raw) as search:
        data = tool.run(
            {
                "operation": "search_populations",
                "superpopulation": "AFR",
                "limit": 3,
                "offset": 3,
            }
        )["data"]

    assert "from" not in search.call_args.args[1]
    assert data["total"] == 7
    assert [row["code"] for row in data["populations"]] == ["P4", "P5", "P6"]
    assert data["next_offset"] == 6


def test_collection_search_forwards_native_es_from():
    tool = _tool("list_data_collections")
    raw = _hits("DC", 3, 19)
    for hit in raw["hits"]["hits"]:
        hit["_source"]["populations"] = {"count": 2}
    with patch.object(tool, "_es_search", return_value=raw) as search:
        data = tool.run(
            {"operation": "list_data_collections", "limit": 3, "offset": 3}
        )["data"]

    assert search.call_args.args[1]["from"] == 3
    assert data["total"] == 19
    assert data["next_offset"] == 6
