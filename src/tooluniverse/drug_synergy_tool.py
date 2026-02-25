"""
Drug Synergy Computation Tool

Implements standard drug synergy models from peer-reviewed literature:
- Bliss Independence (1939)
- Highest Single Agent (HSA)
- ZIP (Zero Interaction Potency)

No external API calls. Uses numpy/scipy for computation.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@register_tool("DrugSynergyTool")
class DrugSynergyTool(BaseTool):
    """
    Local drug combination synergy analysis tools.

    Implements standard pharmacological synergy models:
    - Bliss Independence model
    - Highest Single Agent (HSA) model
    - ZIP (Zero Interaction Potency) model

    No external API required. Uses numpy for computation.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not HAS_NUMPY:
            return {
                "status": "error",
                "error": "numpy is required for drug synergy calculations. Install with: pip install numpy",
            }

        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "calculate_bliss": self._calculate_bliss,
            "calculate_hsa": self._calculate_hsa,
            "calculate_zip": self._calculate_zip,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Calculation failed: {str(e)}"}

    def _interpret_synergy_score(self, score: float, model: str) -> str:
        if model in ("bliss", "hsa"):
            if score > 10:
                return "Strong synergy"
            elif score > 0:
                return "Synergy"
            elif score == 0:
                return "Additivity"
            elif score > -10:
                return "Antagonism"
            else:
                return "Strong antagonism"
        else:
            if score > 10:
                return "Synergy"
            elif score > -10:
                return "Additive"
            else:
                return "Antagonism"

    def _calculate_bliss(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Bliss Independence synergy score.

        Bliss model: E_expected = E_a + E_b - E_a * E_b
        Synergy score = E_combination - E_expected
        Positive score = synergy; Negative = antagonism.

        Effects should be expressed as fractional inhibition (0-1).
        """
        effect_a = arguments.get("effect_a")
        effect_b = arguments.get("effect_b")
        effect_combination = arguments.get("effect_combination")

        if effect_a is None or effect_b is None or effect_combination is None:
            return {
                "status": "error",
                "error": "effect_a, effect_b, and effect_combination are all required",
            }

        try:
            ea = float(effect_a)
            eb = float(effect_b)
            ec = float(effect_combination)
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        # Validate range
        for name, val in [
            ("effect_a", ea),
            ("effect_b", eb),
            ("effect_combination", ec),
        ]:
            if not (0 <= val <= 1):
                return {
                    "status": "error",
                    "error": f"{name}={val} must be between 0 and 1 (fractional inhibition)",
                }

        expected = ea + eb - ea * eb
        synergy_score = (ec - expected) * 100  # Express as percentage points

        return {
            "status": "success",
            "data": {
                "model": "Bliss Independence",
                "effect_a": ea,
                "effect_b": eb,
                "effect_combination_observed": ec,
                "effect_combination_expected": round(expected, 4),
                "bliss_synergy_score": round(synergy_score, 2),
                "interpretation": self._interpret_synergy_score(synergy_score, "bliss"),
                "note": "Positive score = synergy; Negative = antagonism. Based on Bliss (1939).",
            },
        }

    def _calculate_hsa(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Highest Single Agent (HSA) synergy score.

        HSA model: E_expected = max(E_a, E_b) at each dose point
        Synergy = E_combination - max single agent effect.
        """
        effects_a = arguments.get("effects_a", [])
        effects_b = arguments.get("effects_b", [])
        effects_combo = arguments.get("effects_combo", [])

        if not effects_a or not effects_b or not effects_combo:
            return {
                "status": "error",
                "error": "effects_a, effects_b, and effects_combo are all required",
            }

        try:
            ea = np.array([float(x) for x in effects_a])
            eb = np.array([float(x) for x in effects_b])
            ec = np.array([float(x) for x in effects_combo])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        if len(ea) != len(ec) or len(eb) != len(ec):
            return {
                "status": "error",
                "error": "effects_a, effects_b, and effects_combo must have the same length",
            }

        hsa = np.maximum(ea, eb)
        synergy_matrix = (ec - hsa) * 100  # percentage points

        return {
            "status": "success",
            "data": {
                "model": "Highest Single Agent (HSA)",
                "mean_hsa_synergy_score": round(float(np.mean(synergy_matrix)), 2),
                "max_hsa_synergy_score": round(float(np.max(synergy_matrix)), 2),
                "min_hsa_synergy_score": round(float(np.min(synergy_matrix)), 2),
                "synergy_scores_per_point": [
                    round(float(s), 2) for s in synergy_matrix
                ],
                "hsa_expected": [round(float(h), 4) for h in hsa],
                "interpretation": self._interpret_synergy_score(
                    float(np.mean(synergy_matrix)), "hsa"
                ),
                "note": "Positive score = synergy over best single agent; Negative = antagonism.",
            },
        }

    def _calculate_zip(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate ZIP (Zero Interaction Potency) synergy score.

        ZIP model uses dose-response curves to calculate delta scores.
        Input: doses_a, doses_b (1D arrays), viability_matrix (2D).
        Output: ZIP delta synergy score.
        """
        doses_a = arguments.get("doses_a", [])
        doses_b = arguments.get("doses_b", [])
        viability_matrix = arguments.get("viability_matrix", [])

        if not doses_a or not doses_b or not viability_matrix:
            return {
                "status": "error",
                "error": "doses_a, doses_b, and viability_matrix are all required",
            }

        try:
            da = np.array([float(x) for x in doses_a])
            db = np.array([float(x) for x in doses_b])
            vm = np.array([[float(x) for x in row] for row in viability_matrix])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        if vm.shape != (len(da), len(db)):
            return {
                "status": "error",
                "error": f"viability_matrix shape {vm.shape} must be ({len(da)}, {len(db)})",
            }

        # Inhibition matrix (1 - viability)
        inhibition = 1 - vm / 100 if vm.max() > 1 else 1 - vm

        # Fit simple Hill curves for each drug
        from scipy.optimize import curve_fit

        def hill_curve(x, ic50, hill, emax):
            x = np.maximum(x, 1e-12)
            return emax * x**hill / (ic50**hill + x**hill)

        def fit_hill(doses, effects):
            try:
                valid = doses > 0
                d, e = doses[valid], effects[valid]
                if len(d) < 3:
                    return None
                p0 = [np.median(d), 1.0, max(e)]
                bounds = ([0, 0.1, 0], [np.inf, 10, 1])
                popt, _ = curve_fit(hill_curve, d, e, p0=p0, bounds=bounds, maxfev=5000)
                return popt
            except Exception:
                return None

        # Get marginal effects
        effects_a_marginal = (
            inhibition[:, 0] if inhibition.shape[1] > 0 else inhibition.mean(axis=1)
        )
        effects_b_marginal = (
            inhibition[0, :] if inhibition.shape[0] > 0 else inhibition.mean(axis=0)
        )

        params_a = fit_hill(da, effects_a_marginal)
        params_b = fit_hill(db, effects_b_marginal)

        if params_a is None or params_b is None:
            # Fallback: simplified ZIP using means
            expected_zip = (
                np.outer(effects_a_marginal, np.ones(len(db)))
                + np.outer(np.ones(len(da)), effects_b_marginal)
                - np.outer(effects_a_marginal, effects_b_marginal)
            )
        else:
            # ZIP expected using Hill fits
            pred_a = np.array([hill_curve(d, *params_a) for d in da])
            pred_b = np.array([hill_curve(d, *params_b) for d in db])
            expected_zip = (
                np.outer(pred_a, np.ones(len(db)))
                + np.outer(np.ones(len(da)), pred_b)
                - np.outer(pred_a, pred_b)
            )

        delta = (inhibition - expected_zip) * 100

        return {
            "status": "success",
            "data": {
                "model": "ZIP (Zero Interaction Potency)",
                "mean_zip_score": round(float(np.mean(delta)), 2),
                "max_zip_score": round(float(np.max(delta)), 2),
                "min_zip_score": round(float(np.min(delta)), 2),
                "zip_delta_matrix": [
                    [round(float(v), 2) for v in row] for row in delta
                ],
                "interpretation": self._interpret_synergy_score(
                    float(np.mean(delta)), "zip"
                ),
                "note": "ZIP delta > 10: synergy; < -10: antagonism. Based on Yadav et al. (2015).",
            },
        }
