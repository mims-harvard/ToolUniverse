"""
Drug Synergy Computation Tool

Implements standard drug synergy models from peer-reviewed literature:
- Bliss Independence (1939)
- Highest Single Agent (HSA)
- ZIP (Zero Interaction Potency)
- Loewe Additivity (Loewe & Muischnek, 1926)
- Combination Index (Chou & Talalay, 1984)

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

try:
    from scipy.optimize import curve_fit, brentq

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@register_tool("DrugSynergyTool")
class DrugSynergyTool(BaseTool):
    """
    Local drug combination synergy analysis tools.

    Implements standard pharmacological synergy models:
    - Bliss Independence model
    - Highest Single Agent (HSA) model
    - ZIP (Zero Interaction Potency) model
    - Loewe Additivity model
    - Combination Index (Chou-Talalay) model

    No external API required. Uses numpy/scipy for computation.
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
            "calculate_loewe": self._calculate_loewe,
            "calculate_ci": self._calculate_ci,
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
        def hill_curve(x, ic50, hill, emax):
            x = np.maximum(x, 1e-12)
            return emax * x**hill / (ic50**hill + x**hill)

        def fit_hill(doses, effects):
            if not HAS_SCIPY:
                return None
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

    def _fit_hill_for_loewe(self, doses, effects):
        """
        Fit a Hill/sigmoid model: f(d) = Emax * d^m / (Dm^m + d^m)
        Returns (Dm, m, Emax) or None if fitting fails.
        Dm = dose producing half-maximal effect (IC50/EC50).
        m = Hill coefficient (slope).
        Emax = maximum effect.
        """
        if not HAS_SCIPY:
            return None
        try:
            doses = np.array(doses, dtype=float)
            effects = np.array(effects, dtype=float)
            valid = doses > 0
            d, e = doses[valid], effects[valid]
            if len(d) < 3:
                return None
            # Initial guesses
            emax_init = float(np.max(e))
            if emax_init <= 0:
                emax_init = 0.5
            dm_init = float(np.median(d))
            m_init = 1.0
            p0 = [dm_init, m_init, emax_init]
            bounds = ([1e-15, 0.1, 1e-6], [np.inf, 10.0, 1.5])

            def hill(x, dm, m, emax):
                x = np.maximum(x, 1e-15)
                return emax * x**m / (dm**m + x**m)

            popt, _ = curve_fit(hill, d, e, p0=p0, bounds=bounds, maxfev=5000)
            return popt  # (Dm, m, Emax)
        except Exception:
            return None

    def _calculate_loewe(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Loewe Additivity synergy score.

        Loewe model: d_a/D_a(E) + d_b/D_b(E) = 1 for additive combinations.
        Where D_a(E) and D_b(E) are the doses of A and B alone that produce
        effect E. If the sum < 1, the combination is synergistic; > 1 antagonistic.

        Requires dose-response data for each drug individually, plus
        combination doses and their observed effects.
        """
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy is required for Loewe calculations. Install with: pip install scipy",
            }

        doses_a_single = arguments.get("doses_a_single", [])
        effects_a_single = arguments.get("effects_a_single", [])
        doses_b_single = arguments.get("doses_b_single", [])
        effects_b_single = arguments.get("effects_b_single", [])
        dose_a_combo = arguments.get("dose_a_combo")
        dose_b_combo = arguments.get("dose_b_combo")
        effect_combo = arguments.get("effect_combo")

        # Validate required params
        if not doses_a_single or not effects_a_single:
            return {
                "status": "error",
                "error": "doses_a_single and effects_a_single are required (single-agent dose-response for drug A)",
            }
        if not doses_b_single or not effects_b_single:
            return {
                "status": "error",
                "error": "doses_b_single and effects_b_single are required (single-agent dose-response for drug B)",
            }
        if dose_a_combo is None or dose_b_combo is None or effect_combo is None:
            return {
                "status": "error",
                "error": "dose_a_combo, dose_b_combo, and effect_combo are all required",
            }

        if len(doses_a_single) != len(effects_a_single):
            return {
                "status": "error",
                "error": "doses_a_single and effects_a_single must have the same length",
            }
        if len(doses_b_single) != len(effects_b_single):
            return {
                "status": "error",
                "error": "doses_b_single and effects_b_single must have the same length",
            }

        try:
            da_combo = float(dose_a_combo)
            db_combo = float(dose_b_combo)
            e_combo = float(effect_combo)
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        # Fit Hill curves to single-agent data
        params_a = self._fit_hill_for_loewe(doses_a_single, effects_a_single)
        params_b = self._fit_hill_for_loewe(doses_b_single, effects_b_single)

        if params_a is None:
            return {
                "status": "error",
                "error": "Could not fit dose-response curve for drug A. Need at least 3 valid data points with positive doses.",
            }
        if params_b is None:
            return {
                "status": "error",
                "error": "Could not fit dose-response curve for drug B. Need at least 3 valid data points with positive doses.",
            }

        dm_a, m_a, emax_a = params_a
        dm_b, m_b, emax_b = params_b

        # Inverse Hill function: given effect E, find dose D such that f(D) = E
        # f(d) = Emax * d^m / (Dm^m + d^m) => d = Dm * (E / (Emax - E))^(1/m)
        def inverse_hill(effect, dm, m, emax):
            if effect <= 0:
                return 0.0
            if effect >= emax:
                return float("inf")
            ratio = effect / (emax - effect)
            if ratio <= 0:
                return 0.0
            return dm * (ratio ** (1.0 / m))

        # Calculate D_a(E_combo) and D_b(E_combo)
        da_equiv = inverse_hill(e_combo, dm_a, m_a, emax_a)
        db_equiv = inverse_hill(e_combo, dm_b, m_b, emax_b)

        if da_equiv == float("inf") or db_equiv == float("inf"):
            return {
                "status": "error",
                "error": "Combination effect exceeds single-agent maximum effect. Cannot compute Loewe index.",
            }
        if da_equiv <= 0 or db_equiv <= 0:
            return {
                "status": "error",
                "error": "Equivalent single-agent dose is zero or negative. Effect may be outside model range.",
            }

        # Loewe Additivity Index: CI = d_a/D_a(E) + d_b/D_b(E)
        loewe_index = da_combo / da_equiv + db_combo / db_equiv

        # Loewe synergy score (similar to other models): convert to interpretable scale
        # CI < 1 => synergy, CI = 1 => additive, CI > 1 => antagonism
        loewe_excess = (1.0 - loewe_index) * 100  # percentage-based excess

        # Interpretation
        if loewe_index < 0.3:
            interpretation = "Strong synergy"
        elif loewe_index < 0.7:
            interpretation = "Synergy"
        elif loewe_index < 0.85:
            interpretation = "Moderate synergy"
        elif loewe_index < 1.15:
            interpretation = "Additive (near Loewe additivity)"
        elif loewe_index < 1.45:
            interpretation = "Moderate antagonism"
        elif loewe_index < 3.3:
            interpretation = "Antagonism"
        else:
            interpretation = "Strong antagonism"

        return {
            "status": "success",
            "data": {
                "model": "Loewe Additivity",
                "loewe_additivity_index": round(float(loewe_index), 4),
                "loewe_excess_score": round(float(loewe_excess), 2),
                "interpretation": interpretation,
                "combination_dose_a": da_combo,
                "combination_dose_b": db_combo,
                "combination_effect_observed": e_combo,
                "equivalent_dose_a_alone": round(float(da_equiv), 6),
                "equivalent_dose_b_alone": round(float(db_equiv), 6),
                "drug_a_fit": {
                    "ic50": round(float(dm_a), 6),
                    "hill_slope": round(float(m_a), 4),
                    "emax": round(float(emax_a), 4),
                },
                "drug_b_fit": {
                    "ic50": round(float(dm_b), 6),
                    "hill_slope": round(float(m_b), 4),
                    "emax": round(float(emax_b), 4),
                },
                "note": "Loewe index < 1 = synergy; = 1 = additive; > 1 = antagonism. Based on Loewe & Muischnek (1926).",
            },
        }

    def _calculate_ci(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Chou-Talalay Combination Index (CI).

        Based on the Median Effect Equation: fa/fu = (D/Dm)^m
        where fa = fraction affected, fu = fraction unaffected,
        D = dose, Dm = median-effect dose (IC50), m = Hill coefficient.

        CI < 1: synergy
        CI = 1: additive
        CI > 1: antagonism

        Supports both mutually exclusive (MEE) and mutually non-exclusive (MNEE) assumptions.
        """
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy is required for CI calculations. Install with: pip install scipy",
            }

        doses_a_single = arguments.get("doses_a_single", [])
        effects_a_single = arguments.get("effects_a_single", [])
        doses_b_single = arguments.get("doses_b_single", [])
        effects_b_single = arguments.get("effects_b_single", [])
        dose_a_combo = arguments.get("dose_a_combo")
        dose_b_combo = arguments.get("dose_b_combo")
        effect_combo = arguments.get("effect_combo")
        assumption = arguments.get("assumption", "mutually_exclusive")

        # Validate
        if not doses_a_single or not effects_a_single:
            return {
                "status": "error",
                "error": "doses_a_single and effects_a_single are required",
            }
        if not doses_b_single or not effects_b_single:
            return {
                "status": "error",
                "error": "doses_b_single and effects_b_single are required",
            }
        if dose_a_combo is None or dose_b_combo is None or effect_combo is None:
            return {
                "status": "error",
                "error": "dose_a_combo, dose_b_combo, and effect_combo are all required",
            }

        if len(doses_a_single) != len(effects_a_single):
            return {
                "status": "error",
                "error": "doses_a_single and effects_a_single must have same length",
            }
        if len(doses_b_single) != len(effects_b_single):
            return {
                "status": "error",
                "error": "doses_b_single and effects_b_single must have same length",
            }

        if assumption not in ("mutually_exclusive", "mutually_non_exclusive"):
            return {
                "status": "error",
                "error": "assumption must be 'mutually_exclusive' or 'mutually_non_exclusive'",
            }

        try:
            da_combo = float(dose_a_combo)
            db_combo = float(dose_b_combo)
            fa_combo = float(effect_combo)
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        if not (0 < fa_combo < 1):
            return {
                "status": "error",
                "error": f"effect_combo={fa_combo} must be between 0 and 1 (exclusive) for CI calculation",
            }

        # Fit Hill curves to single-agent data (using same method)
        params_a = self._fit_hill_for_loewe(doses_a_single, effects_a_single)
        params_b = self._fit_hill_for_loewe(doses_b_single, effects_b_single)

        if params_a is None:
            return {
                "status": "error",
                "error": "Could not fit dose-response curve for drug A",
            }
        if params_b is None:
            return {
                "status": "error",
                "error": "Could not fit dose-response curve for drug B",
            }

        dm_a, m_a, emax_a = params_a
        dm_b, m_b, emax_b = params_b

        # Median-Effect equation: Dx = Dm * (fa / (1 - fa))^(1/m)
        # For the effect level of the combination, find what dose each drug alone would need
        def dose_for_effect(fa, dm, m, emax):
            # Clamp fa to valid range
            if fa <= 0:
                return 0.0
            if fa >= emax:
                return float("inf")
            ratio = fa / (emax - fa)
            if ratio <= 0:
                return 0.0
            return dm * (ratio ** (1.0 / m))

        dx_a = dose_for_effect(fa_combo, dm_a, m_a, emax_a)
        dx_b = dose_for_effect(fa_combo, dm_b, m_b, emax_b)

        if dx_a == float("inf") or dx_b == float("inf") or dx_a <= 0 or dx_b <= 0:
            return {
                "status": "error",
                "error": "Cannot compute CI: combination effect outside single-agent model range.",
            }

        # CI calculation
        # Mutually exclusive (MEE): CI = (D1/Dx1) + (D2/Dx2)
        # Mutually non-exclusive (MNEE): CI = (D1/Dx1) + (D2/Dx2) + (D1*D2)/(Dx1*Dx2)
        ci = da_combo / dx_a + db_combo / dx_b
        if assumption == "mutually_non_exclusive":
            ci += (da_combo * db_combo) / (dx_a * dx_b)

        # Dose Reduction Index (DRI): how many fold dose can be reduced
        dri_a = dx_a / da_combo if da_combo > 0 else float("inf")
        dri_b = dx_b / db_combo if db_combo > 0 else float("inf")

        # Interpretation (Chou, 2006 classification)
        if ci < 0.1:
            interpretation = "Very strong synergy"
        elif ci < 0.3:
            interpretation = "Strong synergy"
        elif ci < 0.7:
            interpretation = "Synergy"
        elif ci < 0.85:
            interpretation = "Moderate synergy"
        elif ci < 0.9:
            interpretation = "Slight synergy"
        elif ci < 1.1:
            interpretation = "Nearly additive"
        elif ci < 1.2:
            interpretation = "Slight antagonism"
        elif ci < 1.45:
            interpretation = "Moderate antagonism"
        elif ci < 3.3:
            interpretation = "Antagonism"
        elif ci < 10:
            interpretation = "Strong antagonism"
        else:
            interpretation = "Very strong antagonism"

        return {
            "status": "success",
            "data": {
                "model": "Combination Index (Chou-Talalay)",
                "combination_index": round(float(ci), 4),
                "interpretation": interpretation,
                "assumption": assumption,
                "dose_reduction_index": {
                    "drug_a": round(float(dri_a), 2) if dri_a != float("inf") else None,
                    "drug_b": round(float(dri_b), 2) if dri_b != float("inf") else None,
                },
                "combination_dose_a": da_combo,
                "combination_dose_b": db_combo,
                "combination_effect": fa_combo,
                "equivalent_dose_a_alone": round(float(dx_a), 6),
                "equivalent_dose_b_alone": round(float(dx_b), 6),
                "drug_a_fit": {
                    "dm_ic50": round(float(dm_a), 6),
                    "m_hill_slope": round(float(m_a), 4),
                    "emax": round(float(emax_a), 4),
                },
                "drug_b_fit": {
                    "dm_ic50": round(float(dm_b), 6),
                    "m_hill_slope": round(float(m_b), 4),
                    "emax": round(float(emax_b), 4),
                },
                "note": "CI < 1: synergy; CI = 1: additive; CI > 1: antagonism. DRI > 1 means dose can be reduced. Based on Chou & Talalay (1984).",
            },
        }
