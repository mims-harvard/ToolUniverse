"""
Degrees of Unsaturation Calculator Tool

Calculate DoU from a molecular formula string or explicit atom counts.
DoU = (2C + 2 + N - H - X) / 2  where X = total halogens.

No external API calls. Pure Python with stdlib re only.
"""

import re
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


_INTERPRETATION = [
    (0, 0, "No rings or pi bonds — fully saturated, open-chain compound."),
    (1, 1, "One ring OR one double bond (e.g. cyclopropane, alkene, ketone)."),
    (2, 2, "Two degrees: ring + double bond, two double bonds, or one triple bond."),
    (3, 3, "Three degrees: ring + two double bonds or a diene in a ring."),
    (4, 4, "Four degrees — consistent with a benzene ring (3 C=C + 1 ring)."),
]


def _parse_formula(formula: str) -> Dict[str, int]:
    """Parse molecular formula string into element counts."""
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    counts: Dict[str, int] = {}
    for element, count_str in tokens:
        if not element:
            continue
        count = int(count_str) if count_str else 1
        counts[element] = counts.get(element, 0) + count
    return counts


def _interpret(dou: float) -> str:
    for lo, hi, msg in _INTERPRETATION:
        if lo <= dou <= hi:
            return msg
    if dou > 4:
        return f"{dou:.0f} degrees — likely contains multiple rings and/or aromatic systems."
    return "Negative DoU — check your formula."


@register_tool("DegreesOfUnsaturationTool")
class DegreesOfUnsaturationTool(BaseTool):
    """Calculate degrees of unsaturation from a molecular formula."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "calculate")
        if operation != "calculate":
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Only 'calculate' is supported.",
            }

        try:
            return self._calculate(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Calculation failed: {str(e)}"}

    def _calculate(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        formula = arguments.get("formula")

        if formula:
            counts = _parse_formula(formula)
            C = counts.get("C", 0)
            H = counts.get("H", 0)
            N = counts.get("N", 0)
            n_O = counts.get("O", 0)
            S = counts.get("S", 0)
            F = counts.get("F", 0)
            Cl = counts.get("Cl", 0)
            Br = counts.get("Br", 0)
            n_I = counts.get("I", 0)
        else:
            C = arguments.get("C", 0)
            H = arguments.get("H", 0)
            N = arguments.get("N", 0)
            n_O = arguments.get("oxygen", arguments.get("O", 0))
            S = arguments.get("S", 0)
            F = arguments.get("F", 0)
            Cl = arguments.get("Cl", 0)
            Br = arguments.get("Br", 0)
            n_I = arguments.get("iodine", arguments.get("I", 0))

        if C <= 0:
            return {"status": "error", "error": "Number of carbon atoms must be > 0."}

        halogens = F + Cl + Br + n_I
        dou = (2 * C + 2 + N - H - halogens) / 2

        # Build display formula
        parts = []
        for sym, cnt in [
            ("C", C),
            ("H", H),
            ("N", N),
            ("O", n_O),
            ("S", S),
            ("F", F),
            ("Cl", Cl),
            ("Br", Br),
            ("I", n_I),
        ]:
            if cnt > 0:
                parts.append(f"{sym}{cnt}" if cnt > 1 else sym)
        formula_display = "".join(parts)

        return {
            "status": "success",
            "data": {
                "formula": formula_display,
                "C": C,
                "H": H,
                "N": N,
                "O": n_O,
                "S": S,
                "halogens": halogens,
                "degrees_of_unsaturation": dou,
                "calculation": f"(2*{C} + 2 + {N} - {H} - {halogens}) / 2 = {dou}",
                "interpretation": _interpret(dou),
                "is_integer": dou == int(dou),
            },
        }
