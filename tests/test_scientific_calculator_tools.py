"""Tests for ScientificCalculatorTool: DNA translation, molecular formula,
equilibrium solver, enzyme kinetics, and statistical tests."""

import math
import pytest
from tooluniverse.scientific_calculator_tools import ScientificCalculatorTool


@pytest.fixture
def make_tool():
    """Factory to create a ScientificCalculatorTool with a minimal config."""

    def _make(name="test_tool", operation_enum=None):
        config = {
            "name": name,
            "type": "ScientificCalculatorTool",
            "description": "test",
            "parameter": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "op",
                    }
                },
                "required": ["operation"],
            },
        }
        return ScientificCalculatorTool(config)

    return _make


# ── DNA Translation ──


class TestDNATranslateReadingFrames:
    def test_all_frames(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "translate_reading_frames",
                "sequence": "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG",
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["sequence_length"] == 39
        assert "frame_1" in data["frames"]
        assert "frame_2" in data["frames"]
        assert "frame_3" in data["frames"]
        assert data["frames"]["frame_1"]["protein"].startswith("MAIVMGR")

    def test_single_frame(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "translate_reading_frames",
                "sequence": "ATGAAACCCGGGTTTTAA",
                "frame": "1",
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert "frame_1" in data["frames"]
        assert "frame_2" not in data["frames"]
        protein = data["frames"]["frame_1"]["protein"]
        assert protein == "MKPGF*"

    def test_best_frame_selection(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "translate_reading_frames",
                "sequence": "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG",
            }
        )
        data = result["data"]
        assert data["best_frame"] in [1, 2, 3]
        assert data["best_orf_length_aa"] > 0

    def test_empty_sequence(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {"operation": "translate_reading_frames", "sequence": ""}
        )
        assert result["status"] == "error"

    def test_invalid_chars_stripped(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "translate_reading_frames",
                "sequence": "ATG NNN CCC",  # spaces stripped, NNN stripped
            }
        )
        assert result["status"] == "success"
        assert result["data"]["sequence_length"] == 6  # only ATGCCC


# ── Molecular Formula ──


class TestMolecularFormulaAnalyze:
    def test_glucose(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {"operation": "analyze_formula", "formula": "C6H12O6"}
        )
        assert result["status"] == "success"
        data = result["data"]
        assert abs(data["molar_mass"] - 180.156) < 0.01
        assert data["degrees_of_unsaturation"] == 1.0

    def test_benzene(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {"operation": "analyze_formula", "formula": "C6H6"}
        )
        data = result["data"]
        assert abs(data["molar_mass"] - 78.114) < 0.01
        assert data["degrees_of_unsaturation"] == 4.0

    def test_composition_sums_to_100(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {"operation": "analyze_formula", "formula": "C8H9NO2"}
        )
        data = result["data"]
        total = sum(data["elemental_composition"].values())
        assert abs(total - 100.0) < 0.1

    def test_combustion_analysis(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "combustion_analysis",
                "sample_g": 0.5,
                "CO2_g": 0.7472,
                "H2O_g": 0.1834,
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert "empirical_formula" in data
        assert data["empirical_molar_mass"] > 0

    def test_combustion_with_molar_mass(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "combustion_analysis",
                "sample_g": 0.2,
                "CO2_g": 0.4874,
                "H2O_g": 0.1998,
                "molar_mass": 78,
            }
        )
        data = result["data"]
        assert "molecular_formula" in data

    def test_missing_formula(self, make_tool):
        tool = make_tool()
        result = tool.run({"operation": "analyze_formula"})
        assert result["status"] == "error"


# ── Equilibrium Solver ──


class TestEquilibriumSolver:
    def test_ksp_simple_agcl(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "ksp_simple",
                "Ksp": 1.8e-10,
                "stoich_cation": 1,
                "stoich_anion": 1,
            }
        )
        assert result["status"] == "success"
        s = result["data"]["solubility_mol_per_L"]
        # AgCl: s = sqrt(Ksp) = 1.34e-5
        assert abs(s - 1.342e-5) < 1e-6

    def test_ksp_complex_al_oh3(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "ksp_complex",
                "Ksp": 5.3e-27,
                "Kf": 2e33,
                "stoich_cation": 1,
                "stoich_anion": 3,
            }
        )
        data = result["data"]
        assert data["solubility_mol_per_L"] > 0
        assert data["complex_conc"] > data["free_cation_conc"]

    def test_common_ion(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "common_ion",
                "Ksp": 1.8e-10,
                "stoich_cation": 1,
                "stoich_anion": 1,
                "common_ion_conc": 0.1,
            }
        )
        data = result["data"]
        # Common ion should decrease solubility
        s_common = data["solubility_mol_per_L"]
        s_simple = math.sqrt(1.8e-10)
        assert s_common < s_simple

    def test_missing_ksp(self, make_tool):
        tool = make_tool()
        result = tool.run({"operation": "ksp_simple"})
        assert result["status"] == "error"


# ── Enzyme Kinetics ──


class TestEnzymeKinetics:
    def test_michaelis_menten(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "michaelis_menten",
                "substrate_concs": [1, 2, 5, 10, 20],
                "velocities": [0.5, 0.8, 1.2, 1.4, 1.5],
            }
        )
        assert result["status"] == "success"
        data = result["data"]
        assert data["Km"] > 0
        assert data["Vmax"] > 0
        assert data["catalytic_efficiency"] > 0

    def test_hill_positive_cooperativity(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "hill",
                "substrate_concs": [0.1, 0.5, 1, 2, 5, 10, 50],
                "velocities": [0.02, 0.1, 0.2, 0.35, 0.6, 0.8, 0.95],
            }
        )
        data = result["data"]
        assert data["hill_coefficient"] > 0.5  # should be near 1
        assert data["K05"] > 0

    def test_inhibition_competitive(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "inhibition",
                "substrate_concs": [1, 2, 5, 10, 20],
                "velocities_no_inhibitor": [0.5, 0.8, 1.2, 1.5, 1.7],
                "velocities_with_inhibitor": [0.3, 0.5, 0.8, 1.0, 1.1],
                "inhibitor_conc": 5,
                "inhibition_type": "competitive",
            }
        )
        data = result["data"]
        assert "Ki" in data
        assert data["Ki"] > 0

    def test_too_few_points(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "michaelis_menten",
                "substrate_concs": [1, 2],
                "velocities": [0.5, 0.8],
            }
        )
        assert result["status"] == "error"


# ── Statistical Tests ──


class TestStatisticsTest:
    def test_chi_square(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "chi_square",
                "observed": [90, 110],
                "expected": [100, 100],
            }
        )
        data = result["data"]
        assert abs(data["chi2"] - 2.0) < 0.01
        assert data["df"] == 1
        assert 0.1 < data["p_value"] < 0.2  # p ~ 0.157

    def test_chi_square_significant(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "chi_square",
                "observed": [50, 150],
                "expected": [100, 100],
            }
        )
        data = result["data"]
        assert data["chi2"] == 50.0
        assert data["p_value"] < 0.001
        assert data["significant_at_005"] is True

    def test_fisher_exact(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "fisher_exact",
                "a": 10,
                "b": 5,
                "c": 3,
                "d": 20,
            }
        )
        data = result["data"]
        assert data["p_value"] < 0.01
        assert data["significant_at_005"] is True

    def test_linear_regression(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "linear_regression",
                "data_x": [1, 2, 3, 4, 5],
                "data_y": [2.1, 4.0, 5.9, 8.1, 10.0],
            }
        )
        data = result["data"]
        assert abs(data["slope"] - 1.99) < 0.01
        assert data["R2"] > 0.99
        assert data["p_slope"] < 0.001

    def test_t_test(self, make_tool):
        tool = make_tool()
        result = tool.run(
            {
                "operation": "t_test",
                "data_x": [5.1, 4.9, 5.2, 5.0, 4.8, 5.3],
                "data_y": [6.1, 5.9, 6.2, 6.0, 5.8, 6.3],
            }
        )
        data = result["data"]
        assert abs(data["mean_difference"] - (-1.0)) < 0.01
        assert data["p_value"] < 0.001
        assert data["significant_at_005"] is True

    def test_unknown_operation(self, make_tool):
        tool = make_tool()
        result = tool.run({"operation": "nonexistent"})
        assert result["status"] == "error"

    def test_missing_operation(self, make_tool):
        tool = make_tool()
        result = tool.run({})
        assert result["status"] == "error"
