"""HumanBase must not iterate a gene symbol string as characters."""

from unittest.mock import patch

import networkx as nx
import pytest

from tooluniverse.humanbase_tool import HumanBaseTool, _coerce_gene_list

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TP53", ["TP53"]),
        ("BRCA1, TP53", ["BRCA1", "TP53"]),
        ("BRCA1;TP53", ["BRCA1", "TP53"]),
        (["BRCA1", "TP53"], ["BRCA1", "TP53"]),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_coerce_gene_list(raw, expected):
    assert _coerce_gene_list(raw) == expected


def test_string_gene_list_is_passed_as_one_symbol():
    tool = HumanBaseTool(
        {"name": "humanbase_ppi_analysis", "type": "HumanBaseTool", "parameter": {}}
    )
    captured = {}

    def fake_retrieve(genes, tissue, max_node=10, interaction=None):
        captured["genes"] = genes
        graph = nx.Graph()
        graph.add_node("TP53")
        return graph, ["apoptotic process"]

    with patch.object(tool, "humanbase_ppi_retrieve", side_effect=fake_retrieve):
        result = tool.run(
            {"gene_list": "TP53", "tissue": "brain", "string_mode": False}
        )

    assert captured["genes"] == ["TP53"]
    assert result["status"] == "success"
