"""Live check: DepMap_get_gene_dependencies returns real scores (needs network)."""

import pytest

from tooluniverse import ToolUniverse

pytestmark = [pytest.mark.integration, pytest.mark.network]


@pytest.fixture(scope="module")
def tu():
    universe = ToolUniverse()
    universe.load_tools(include_tools=["DepMap_get_gene_dependencies"])
    return universe


def _run(tu, **arguments):
    return tu.run({"name": "DepMap_get_gene_dependencies", "arguments": arguments})


def test_kras_scores_round_trip(tu):
    """KRAS scores come back sorted, and model_id keeps the A549 screens."""
    result = _run(tu, gene_symbol="KRAS", limit=5)
    assert result["status"] == "success"
    data = result["data"]
    assert data["matched_gene"]["symbol"] == "KRAS"
    assert data["summary"]["screens"] > 1000
    assert 0 < data["summary"]["loss_of_fitness_screens"] < data["summary"]["screens"]
    assert set(data["summary"]["by_source"]) == {"Broad", "Sanger"}
    values = [row["bf_scaled"] for row in data["scores"]]
    assert len(values) == 5 and values == sorted(values) and values[0] < -20
    assert all(row["model_name"] and row["tissue"] for row in data["scores"])

    # A549 carries KRAS G12S and depends on it; the model filter is applied.
    a549 = _run(tu, gene_symbol="KRAS", model_id="A549")["data"]
    assert a549["scores"] and a549["total_scores"] <= 2
    assert all(
        row["model_id"] == "SIDM00903" and row["loss_of_fitness"]
        for row in a549["scores"]
    )


def test_unknown_model_id_is_an_error(tu):
    """The API answers an unknown model id with HTTP 200 and data null."""
    result = _run(tu, gene_symbol="KRAS", model_id="SIDM99999")
    assert result["status"] == "error"
    assert "no model with the id SIDM99999" in result["error"]
