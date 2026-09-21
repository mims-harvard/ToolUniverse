"""Gene input must reach the network the caller actually asked for."""

import json
from pathlib import Path
from unittest.mock import patch

import networkx as nx
import pytest

from tooluniverse.humanbase_tool import HumanBaseTool, _coerce_gene_list

pytestmark = pytest.mark.unit

CONFIG = Path(__file__).resolve().parents[2] / "src/tooluniverse/data/humanbase_tools.json"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TP53", ["TP53"]),
        ("BRCA1,TP53", ["BRCA1", "TP53"]),
        (["BRCA1", "TP53"], ["BRCA1", "TP53"]),
        # A single element carrying several symbols used to be fuzzy-resolved
        # whole, to an unrelated gene (BRIP1), dropping TP53 entirely.
        (["BRCA1,TP53"], ["BRCA1", "TP53"]),
        (["BRCA1;TP53"], ["BRCA1", "TP53"]),
        (["BRCA1, TP53", "EGFR"], ["BRCA1", "TP53", "EGFR"]),
        (None, None),
        ("  ", None),
    ],
)
def test_coerce_gene_list_splits_every_form(raw, expected):
    assert _coerce_gene_list(raw) == expected


def test_schema_accepts_the_string_form_the_tool_coerces():
    """The coercion is unreachable if validation rejects a string first."""
    tools = json.loads(CONFIG.read_text())
    props = tools[0]["parameter"]["properties"]
    for key in ("gene_list", "genes"):
        assert "string" in props[key]["type"], key
        assert "array" in props[key]["type"], key


def _tool():
    return HumanBaseTool(
        {"name": "humanbase_ppi_analysis", "type": "HumanBaseTool", "parameter": {}}
    )


def test_unresolved_gene_is_named_instead_of_blaming_the_api():
    tool = _tool()

    def fake_retrieve(genes, tissue, max_node=10, interaction=None):
        tool._unresolved = ["ZZZNOTAGENE"]
        return nx.Graph(), None

    with patch.object(tool, "humanbase_ppi_retrieve", side_effect=fake_retrieve):
        result = tool.run({"gene_list": ["ZZZNOTAGENE"], "tissue": "brain"})

    assert result["status"] == "error"
    assert "ZZZNOTAGENE" in result["error"]
    assert "temporarily unavailable" not in result["error"]
    assert result["unresolved_genes"] == ["ZZZNOTAGENE"]


def test_api_failure_still_reports_an_api_failure():
    """With nothing unresolved, the original diagnosis is the right one."""
    tool = _tool()
    with patch.object(
        tool, "humanbase_ppi_retrieve", return_value=(nx.Graph(), None)
    ):
        result = tool.run({"gene_list": ["TP53"], "tissue": "nowhere"})

    assert result["status"] == "error"
    assert "temporarily unavailable" in result["error"]


def test_symbol_substitutions_are_reported_in_the_payload():
    """The substitution is the only sign the network is for another gene."""
    tool = _tool()

    def fake_retrieve(genes, tissue, max_node=10, interaction=None):
        tool._resolutions = {"p53": "TP53"}
        graph = nx.Graph()
        graph.add_node("TP53", entrez="7157", description="tumor protein p53")
        return graph, []

    with patch.object(tool, "humanbase_ppi_retrieve", side_effect=fake_retrieve):
        result = tool.run({"gene_list": ["p53"], "tissue": "brain"})

    assert result["status"] == "success"
    assert result["resolved_genes"] == {"p53": "TP53"}
    assert "Resolved To: p53 -> TP53" in result["data"]
