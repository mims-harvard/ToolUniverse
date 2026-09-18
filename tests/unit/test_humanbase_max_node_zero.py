"""HumanBase must keep max_node=0 instead of substituting the default 10."""

from unittest.mock import patch

import networkx as nx
import pytest

from tooluniverse.humanbase_tool import HumanBaseTool

pytestmark = pytest.mark.unit


def test_zero_max_node_is_forwarded():
    tool = HumanBaseTool(
        {"name": "humanbase_ppi_analysis", "type": "HumanBaseTool", "parameter": {}}
    )
    captured = {}

    def fake_retrieve(genes, tissue, max_node=10, interaction=None):
        captured["max_node"] = max_node
        graph = nx.Graph()
        graph.add_node("TP53")
        return graph, ["apoptotic process"]

    with patch.object(tool, "humanbase_ppi_retrieve", side_effect=fake_retrieve):
        result = tool.run(
            {
                "gene_list": ["TP53"],
                "tissue": "brain",
                "max_node": 0,
                "string_mode": False,
            }
        )

    assert captured["max_node"] == 0
    assert result["status"] == "success"
