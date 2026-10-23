from unittest.mock import Mock, patch

from tooluniverse.ndex_tool import NDExTool


def _tool():
    return NDExTool({"fields": {"endpoint": "get_network"}})


def _cx(node_count=5, edge_count=7):
    return [
        {"networkAttributes": [{"n": "name", "v": "test network"}]},
        {"nodes": [{"@id": i, "n": f"node-{i}"} for i in range(node_count)]},
        {
            "edges": [
                {
                    "@id": i,
                    "s": i % node_count,
                    "t": (i + 1) % node_count,
                    "i": "interacts",
                }
                for i in range(edge_count)
            ]
        },
    ]


@patch("tooluniverse.ndex_tool.requests.get")
def test_network_nodes_and_edges_paginate_independently(mock_get):
    response = Mock()
    response.json.return_value = _cx()
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    result = _tool().run(
        {
            "uuid": "test",
            "node_limit": 2,
            "node_offset": 2,
            "edge_limit": 3,
            "edge_offset": 3,
        }
    )
    data = result["data"]

    assert [item["id"] for item in data["nodes"]] == [2, 3]
    assert [item["id"] for item in data["edges"]] == [3, 4, 5]
    assert data["total_nodes"] == 5
    assert data["total_edges"] == 7
    assert data["next_node_offset"] == 4
    assert data["next_edge_offset"] == 6
    assert data["nodes_have_more"] is True
    assert data["edges_have_more"] is True


@patch("tooluniverse.ndex_tool.requests.get")
def test_network_tail_page_has_no_continuation(mock_get):
    response = Mock()
    response.json.return_value = _cx()
    response.raise_for_status.return_value = None
    mock_get.return_value = response

    data = _tool().run(
        {
            "uuid": "test",
            "node_limit": 2,
            "node_offset": 4,
            "edge_limit": 3,
            "edge_offset": 6,
        }
    )["data"]

    assert data["returned_nodes"] == 1
    assert data["returned_edges"] == 1
    assert data["nodes_have_more"] is False
    assert data["edges_have_more"] is False
    assert data["next_node_offset"] is None
    assert data["next_edge_offset"] is None


def test_network_rejects_invalid_pagination():
    result = _tool().run({"uuid": "test", "node_offset": -1})
    assert result["status"] == "error"
    assert "node_offset" in result["error"]
