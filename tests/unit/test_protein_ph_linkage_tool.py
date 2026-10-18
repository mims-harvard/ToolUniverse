"""Analytic reaction controls, inventory closure, and real framework dispatch."""

import copy
import json
import math
from pathlib import Path

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.protein_ph_linkage_tool import ProteinPHLinkageTool, R_KCAL

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/protein_ph_linkage_tools.json").read_text()
)[0]


def request():
    return copy.deepcopy(CONFIG["test_examples"][0])


def calculate(args=None):
    result = ProteinPHLinkageTool(CONFIG).run(request() if args is None else args)
    jsonschema.validate(result, CONFIG["return_schema"])
    return result


def energy(result, index=1):
    return result["data"]["curve"][index]["total"]["relative_linkage_energy_kcal_mol"]


def test_analytic_sign_and_base_ten():
    data = calculate()["data"]
    value = data["curve"][1]["total"]
    assert value["relative_log10_association"] == pytest.approx(math.log10(40 / 121))
    assert energy({"data": data}) == pytest.approx(
        -R_KCAL * 298.15 * math.log(40 / 121)
    )
    for row in data["curve"]:
        assert row["total"]["delta_proton_count_bound_minus_free"] == pytest.approx(
            9 / 22
        )
    assert data["curve"][0]["total"]["relative_log10_association"] == 0
    assert not data["binding_verified"] and not data["pH_selectivity_verified"]
    assert not data["inventory"]["structural_completeness_verified"]


@pytest.mark.parametrize("pka", [-1000, -10, 0, 6, 7, 14, 30, 1000])
def test_identical_states_cancel_at_extreme_and_ordinary_pkas(pka):
    args = request()
    args["bound_groups"][0]["pka"] = args["free_groups"][0]["pka"] = pka
    args["ph_values"] = [14, 0, 6, 7]
    for row in calculate(args)["data"]["curve"]:
        assert row["total"]["relative_linkage_energy_kcal_mol"] == 0
        assert row["total"]["delta_proton_count_bound_minus_free"] == 0


def test_reverse_reference_and_temperature():
    original = calculate()
    args = request()
    args.update(reference_ph=7, ph_values=[6], temperature_kelvin=310)
    assert energy(calculate(args), 0) == pytest.approx(-energy(original) * 310 / 298.15)


def test_derivative_matches_proton_uptake():
    args = request()
    epsilon = 1e-5
    args["ph_values"] = [6.5 - epsilon, 6.5, 6.5 + epsilon]
    rows = calculate(args)["data"]["curve"]
    derivative = (
        rows[2]["total"]["relative_log10_association"]
        - rows[0]["total"]["relative_log10_association"]
    ) / (2 * epsilon)
    assert derivative == pytest.approx(
        -rows[1]["total"]["delta_proton_count_bound_minus_free"], abs=1e-9
    )


def test_component_terminal_subtotals_and_explicit_molecular_copies():
    args = request()
    for key in ("bound_groups", "free_groups", "expected_groups"):
        original = args[key][0]
        second_copy = {**original, "chain": "B"}
        terminal = {**original, "chain": "C", "group_type": "N+"}
        if key == "expected_groups":
            second_copy["component"] = "receptor_copy_1"
            terminal["component"] = "receptor_copy_2"
        args[key] += [second_copy, terminal]
    data = calculate(args)["data"]
    row = data["curve"][1]
    one_site = energy(calculate())
    assert row["total"]["relative_linkage_energy_kcal_mol"] == pytest.approx(
        3 * one_site
    )
    assert row["termini"]["group_count"] == 1
    assert row["nonterminal_same_mask"][
        "relative_linkage_energy_kcal_mol"
    ] == pytest.approx(2 * one_site)
    assert sum(
        c["relative_linkage_energy_kcal_mol"] for c in row["components"].values()
    ) == pytest.approx(3 * one_site)
    assert data["inventory"]["component_counts"] == {
        "binder": 1,
        "receptor_copy_1": 1,
        "receptor_copy_2": 1,
    }


@pytest.mark.parametrize(
    "inventory", ["bound_groups", "free_groups", "expected_groups"]
)
def test_duplicate_identity_rejected(inventory):
    args = request()
    args[inventory].append(dict(args[inventory][0]))
    assert "duplicate" in calculate(args)["error"]


@pytest.mark.parametrize("inventory", ["bound_groups", "free_groups"])
@pytest.mark.parametrize("change", ["missing", "extra"])
def test_missing_or_extra_groups_never_silently_intersect(inventory, change):
    args = request()
    extra = {**args[inventory][0], "residue_number": 2}
    if change == "missing":
        args["expected_groups"].append(
            {
                "chain": "A",
                "residue_number": 2,
                "group_type": "HIS",
                "component": "binder",
            }
        )
    else:
        args[inventory].append(extra)
    assert change in calculate(args)["error"]


def test_same_omission_on_both_sides_detected_by_expected_inventory():
    args = request()
    args["expected_groups"].append(
        {"chain": "A", "residue_number": 2, "group_type": "C-", "component": "binder"}
    )
    assert "1 missing" in calculate(args)["error"]


@pytest.mark.parametrize(
    "field,value,fragment",
    [
        ("reference_kind", "fixed_protons", "both titrate"),
        ("ph_values", [], "1 to 20"),
        ("ph_values", [15], "pH"),
        ("ph_values", [float("nan")], "finite"),
        ("reference_ph", True, "finite"),
        ("temperature_kelvin", 0, "finite"),
        ("provenance", {}, "pka_method"),
    ],
)
def test_invalid_top_level_inputs(field, value, fragment):
    args = request()
    args[field] = value
    assert fragment in calculate(args)["error"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, 1001, None])
def test_nonfinite_or_invalid_pka_rejected(value):
    args = request()
    args["bound_groups"][0]["pka"] = value
    assert "finite" in calculate(args)["error"]


def test_ambiguous_carboxyl_group_rejected():
    args = request()
    args["bound_groups"][0]["group_type"] = "COO"
    assert "resolve COO" in calculate(args)["error"]


def test_insertion_codes_and_termini_are_distinct():
    args = request()
    for key in ("bound_groups", "free_groups", "expected_groups"):
        group = args[key][0]
        args[key] += [{**group, "insertion_code": "A"}, {**group, "group_type": "C-"}]
    assert calculate(args)["data"]["inventory"]["group_count"] == 3


def test_reference_mode_preserved_and_both_modes_titrate():
    args = request()
    args["reference_kind"] = "same_coordinate_components"
    result = calculate(args)
    assert result["data"]["reference_kind"] == args["reference_kind"]
    assert energy(result) == energy(calculate())


def test_digest_order_invariant_but_reference_sensitive():
    args = request()
    original = calculate(args)["data"]["calculation_sha256"]
    args["bound_groups"][0]["insertion_code"] = ""
    assert calculate(args)["data"]["calculation_sha256"] == original
    args["reference_kind"] = "same_coordinate_components"
    assert calculate(args)["data"]["calculation_sha256"] != original


def test_real_sdk_route_and_generated_wrapper():
    tu = ToolUniverse()
    tu.load_tools(include_tools=[CONFIG["name"]])
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": request()}, use_cache=False
    )
    jsonschema.validate(result, CONFIG["return_schema"])
    assert result["status"] == "success"
    assert energy(result) == pytest.approx(energy(calculate()))
    from tooluniverse.tools.Protein_calculate_pH_linkage import (
        Protein_calculate_pH_linkage,
    )

    assert Protein_calculate_pH_linkage(**request())["status"] == "success"


def test_real_sdk_rejects_unmatched_inventory():
    tu = ToolUniverse()
    tu.load_tools(include_tools=[CONFIG["name"]])
    args = request()
    args["free_groups"][0]["residue_number"] = 3
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": args}, use_cache=False
    )
    assert result["status"] == "error" and "missing" in result["error"]


def test_nullable_temperature_defaults_through_real_sdk():
    tu = ToolUniverse()
    tu.load_tools(include_tools=[CONFIG["name"]])
    args = request()
    args["temperature_kelvin"] = None
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": args}, use_cache=False
    )
    assert result["status"] == "success"
    assert result["data"]["temperature_kelvin"] == 298.15
    assert energy(result) == pytest.approx(energy(calculate()))


def test_blank_chain_is_an_explicit_identity():
    args = request()
    for label in ("bound_groups", "free_groups", "expected_groups"):
        args[label][0]["chain"] = " "
    assert calculate(args)["status"] == "success"
