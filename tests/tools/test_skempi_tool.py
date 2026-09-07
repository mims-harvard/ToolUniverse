"""Tests for the SKEMPI experimental binding affinity tool.

SKEMPI supplies measured ground truth for mutation effects on protein-protein
binding, so these tests check the thermodynamics the tool derives, not just
the response shape. A wrong gas constant or an inverted Kd ratio would still
produce schema-valid output.
"""

import math

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

EXPECTED_TOOLS = [
    "SKEMPI_search_by_structure",
    "SKEMPI_get_mutation",
    "SKEMPI_search_by_protein",
]


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert not [n for n in EXPECTED_TOOLS if n not in names]


class TestThermodynamics:
    """ddG must follow RT.ln(Kd_mut/Kd_wt) with the recorded temperature."""

    def test_ddg_matches_the_defining_equation(self, tu):
        rows = data_of(tu.tools.SKEMPI_get_mutation(pdb_id="1CSE", mutation="LI38G"))
        record = rows[0]
        expected = (
            1.987204258640832e-3
            * record["temperature_K"]
            * math.log(record["kd_mutant_M"] / record["kd_wildtype_M"])
        )
        assert record["ddg_kcal_per_mol"] == pytest.approx(expected, abs=0.01)

    def test_weaker_binding_gives_positive_ddg(self, tu):
        # LI38G raises Kd from 1.12e-12 to 5.26e-11: binding is weakened.
        record = data_of(
            tu.tools.SKEMPI_get_mutation(pdb_id="1CSE", mutation="LI38G")
        )[0]
        assert record["kd_mutant_M"] > record["kd_wildtype_M"]
        assert record["ddg_kcal_per_mol"] > 0

    def test_proline_substitution_is_most_destabilizing_at_this_site(self, tu):
        # Position 38 of eglin c sits in the binding core; proline disrupts it
        # far more than a conservative change.
        pro = data_of(tu.tools.SKEMPI_get_mutation(pdb_id="1CSE", mutation="LI38P"))[0]
        ser = data_of(tu.tools.SKEMPI_get_mutation(pdb_id="1CSE", mutation="LI38S"))[0]
        assert pro["ddg_kcal_per_mol"] > ser["ddg_kcal_per_mol"]


class TestSearchByStructure:
    def test_returns_partners_and_summary(self, tu):
        result = tu.tools.SKEMPI_search_by_structure(pdb_id="1CSE")
        rows = data_of(result)
        assert rows
        assert result["metadata"]["partners"] == ["Subtilisin Carlsberg", "Eglin c"]
        assert result["metadata"]["measurements_with_ddg"] > 0

    def test_single_mutant_filter(self, tu):
        result = tu.tools.SKEMPI_search_by_structure(
            pdb_id="1VFB", only_single_mutants=True
        )
        assert all(r["mutation_count"] == 1 for r in data_of(result))

    def test_pdb_id_is_case_insensitive(self, tu):
        lower = data_of(tu.tools.SKEMPI_search_by_structure(pdb_id="1cse"))
        upper = data_of(tu.tools.SKEMPI_search_by_structure(pdb_id="1CSE"))
        assert len(lower) == len(upper)

    def test_structure_without_measurements(self, tu):
        result = tu.tools.SKEMPI_search_by_structure(pdb_id="9ZZZ")
        assert result["status"] == "error"


class TestSearchByProtein:
    def test_lysozyme_complexes(self, tu):
        result = tu.tools.SKEMPI_search_by_protein(name="lysozyme", limit=10)
        rows = data_of(result)
        assert rows
        assert result["metadata"]["structure_count"] > 1
        # Interface mutations weaken binding far more often than they help.
        meta = result["metadata"]
        assert meta["destabilizing_count"] > meta["stabilizing_count"]

    def test_unknown_protein(self, tu):
        result = tu.tools.SKEMPI_search_by_protein(name="notaprotein")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("SKEMPI_search_by_structure", {"pdb_id": ""}),
            ("SKEMPI_get_mutation", {"pdb_id": "1CSE", "mutation": ""}),
            ("SKEMPI_search_by_protein", {"name": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
