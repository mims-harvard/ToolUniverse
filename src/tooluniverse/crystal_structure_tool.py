"""
Crystal Structure Validator Tool

Compute theoretical density from unit cell parameters (a, b, c, alpha, beta,
gamma), Z value, and molecular weight, then compare against a reported density.

No external API calls. Pure Python with stdlib math only.
"""

import math
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool

AVOGADRO = 6.02214076e23
ANG3_TO_CM3 = 1e-24


def _unit_cell_volume(a, b, c, alpha_deg, beta_deg, gamma_deg) -> float:
    """Compute unit cell volume in A^3 for any crystal system."""
    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    gamma = math.radians(gamma_deg)

    ca, cb, cg = math.cos(alpha), math.cos(beta), math.cos(gamma)
    val = 1.0 - ca**2 - cb**2 - cg**2 + 2.0 * ca * cb * cg
    if val < 0:
        raise ValueError(
            f"Invalid cell angles: alpha={alpha_deg}, beta={beta_deg}, "
            f"gamma={gamma_deg} produce negative discriminant ({val:.6f})"
        )
    return a * b * c * math.sqrt(val)


def _theoretical_density(Z, MW, volume_ang3) -> float:
    """Calculate density in g/cm^3."""
    volume_cm3 = volume_ang3 * ANG3_TO_CM3
    return (Z * MW) / (volume_cm3 * AVOGADRO)


def _detect_crystal_system(a, b, c, alpha, beta, gamma, tol=0.01, ang_tol=0.1) -> str:
    eq_ab = abs(a - b) < tol
    eq_ac = abs(a - c) < tol
    eq_bc = abs(b - c) < tol
    all_eq = eq_ab and eq_ac

    def is_90(x):
        return abs(x - 90.0) < ang_tol

    def is_120(x):
        return abs(x - 120.0) < ang_tol

    all_90 = is_90(alpha) and is_90(beta) and is_90(gamma)

    if all_eq and all_90:
        return "cubic"
    if eq_ab and all_90 and not eq_ac:
        return "tetragonal"
    if all_90 and not eq_ab and not eq_ac and not eq_bc:
        return "orthorhombic"
    if eq_ab and is_90(alpha) and is_90(beta) and is_120(gamma):
        return "hexagonal"
    if (
        all_eq
        and abs(alpha - beta) < ang_tol
        and abs(alpha - gamma) < ang_tol
        and not all_90
    ):
        return "trigonal (rhombohedral)"
    if is_90(alpha) and is_90(gamma) and not is_90(beta):
        return "monoclinic"
    return "triclinic"


@register_tool("CrystalStructureTool")
class CrystalStructureTool(BaseTool):
    """Validate crystal structure by computing density from unit cell parameters."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "validate")
        if operation != "validate":
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Only 'validate' is supported.",
            }

        try:
            return self._validate(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Validation failed: {str(e)}"}

    def _validate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        a = arguments.get("a")
        b = arguments.get("b")
        c = arguments.get("c")
        alpha = arguments.get("alpha", 90.0)
        beta = arguments.get("beta", 90.0)
        gamma = arguments.get("gamma", 90.0)
        Z = arguments.get("Z")
        mw = arguments.get("mw")
        reported_density = arguments.get("reported_density")

        for name, val in [("a", a), ("Z", Z), ("mw", mw)]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }

        # Default b and c to a for cubic
        if b is None:
            b = a
        if c is None:
            c = a

        V = _unit_cell_volume(a, b, c, alpha, beta, gamma)
        d_calc = _theoretical_density(Z, mw, V)
        system = _detect_crystal_system(a, b, c, alpha, beta, gamma)

        data = {
            "crystal_system": system,
            "cell_params": {
                "a": a,
                "b": b,
                "c": c,
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma,
            },
            "volume_ang3": round(V, 4),
            "Z": Z,
            "mw": mw,
            "calculated_density_g_cm3": round(d_calc, 4),
        }

        if reported_density is not None:
            diff = abs(d_calc - reported_density)
            pct = (
                (diff / reported_density) * 100
                if reported_density != 0
                else float("inf")
            )
            data["reported_density_g_cm3"] = reported_density
            data["difference_g_cm3"] = round(diff, 4)
            data["percent_error"] = round(pct, 2)
            if pct < 1.0:
                data["verdict"] = "OK"
            elif pct < 5.0:
                data["verdict"] = "WARNING — deviation > 1%"
            else:
                data["verdict"] = "MISMATCH — deviation > 5%"

        return {"status": "success", "data": data}
