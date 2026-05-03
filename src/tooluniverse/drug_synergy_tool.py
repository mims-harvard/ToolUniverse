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

import math
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
            # Scores are fractional (0-1 scale, same as inputs)
            # Boundary |score| = 0.10 is classified as "Strong" (inclusive threshold)
            if score >= 0.10:
                return "Strong synergy"
            elif score > 0:
                return "Synergy"
            elif score == 0:
                return "Additivity"
            elif score > -0.10:
                # Asymmetric boundary fix: -0.10 should be "Strong antagonism"
                # to match the symmetric positive side (0.10 → "Strong synergy").
                return "Antagonism"
            else:
                return "Strong antagonism"
        else:
            # ZIP scores are in percentage points (×100); thresholds ±10 pp.
            # The result note documents "< -10: antagonism"
            # (strict), so -10.0 exactly should be "Additivity" not "Antagonism".
            # Changed `elif score > -10` → `elif score >= -10` to make the negative
            # boundary exclusive (matching the positive boundary: > 10 for Synergy,
            # so 10.0 → "Additivity").
            # Use "Additivity" (matching Bliss/HSA labels) for
            # the no-interaction label instead of "Additive" for consistency.
            if score > 10:
                return "Synergy"
            elif score >= -10:
                return "Additivity"
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
        synergy_score = ec - expected  # Fractional units (same scale as inputs)
        # Use raw (unrounded) score for interpretation to avoid boundary
        # misclassification. round(-0.099, 2) = -0.1, and -0.1 > -0.10 is False, so
        # the rounded score would label -0.099 as "Strong antagonism" instead of
        # "Antagonism". The display value is still rounded for readability.
        # Add 0.0 to eliminate IEEE-754 negative zero (-0.0 + 0.0 = 0.0).
        # round(-0.004, 2) returns -0.0 in Python; json.dumps serializes it as "-0.0",
        # which looks contradictory alongside interpretation="Additivity".
        synergy_score_rounded = round(synergy_score, 2) + 0.0

        return {
            "status": "success",
            "data": {
                "model": "Bliss Independence",
                "effect_a": ea,
                "effect_b": eb,
                "effect_combination_observed": ec,
                "effect_combination_expected": round(expected, 4),
                "bliss_synergy_score": synergy_score_rounded,
                "interpretation": self._interpret_synergy_score(
                    synergy_score_rounded,
                    "bliss",  # rounded (displayed) score keeps label consistent with value
                ),
                "note": "Scores in fractional units (0-1 scale, same as inputs). Positive = synergy; Negative = antagonism. |score| ≥ 0.1 = strong effect. Based on Bliss (1939).",
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

        # Validate [0,1] range — same requirement as Bliss and Loewe.
        for name, arr in [
            ("effects_a", list(ea)),
            ("effects_b", list(eb)),
            ("effects_combo", list(ec)),
        ]:
            bad = [i for i, v in enumerate(arr) if not (0 <= v <= 1)]
            if bad:
                return {
                    "status": "error",
                    "error": (
                        f"{name} values must be between 0 and 1 (fractional inhibition). "
                        f"Invalid values at indices: {bad}"
                    ),
                }

        hsa = np.maximum(ea, eb)
        synergy_matrix = ec - hsa  # Fractional units (same scale as inputs)
        # Use raw mean score for interpretation to avoid boundary
        # misclassification at round-to-threshold values (same as Bliss fix).
        # Add 0.0 to eliminate IEEE-754 negative zero.
        _mean_raw = float(np.mean(synergy_matrix))
        mean_score_rounded = round(_mean_raw, 2) + 0.0

        return {
            "status": "success",
            "data": {
                "model": "Highest Single Agent (HSA)",
                "mean_hsa_synergy_score": mean_score_rounded,
                "max_hsa_synergy_score": round(float(np.max(synergy_matrix)), 2) + 0.0,
                "min_hsa_synergy_score": round(float(np.min(synergy_matrix)), 2) + 0.0,
                "synergy_scores_per_point": [
                    round(float(s), 2) + 0.0 for s in synergy_matrix
                ],
                "hsa_expected": [round(float(h), 4) for h in hsa],
                "interpretation": self._interpret_synergy_score(
                    mean_score_rounded,
                    "hsa",  # rounded (displayed) score keeps label consistent with value
                ),
                "note": "Scores in fractional units (0-1 scale, same as inputs). Positive = synergy over best single agent; Negative = antagonism. |score| ≥ 0.1 = strong effect.",
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

        # A flat (1D) viability_matrix produces a misleading error
        # "Invalid numeric values: 'float' object is not iterable" because the
        # nested comprehension iterates over individual floats rather than rows.
        # Detect 1D input early with a clear, actionable message.
        if viability_matrix and not hasattr(viability_matrix[0], "__iter__"):
            return {
                "status": "error",
                "error": (
                    "viability_matrix must be a 2D array (list of lists), "
                    f"but received a 1D array with {len(viability_matrix)} elements. "
                    "Each row should contain viability values for one concentration of "
                    "drug A across all concentrations of drug B. "
                    f"Expected shape: ({len(doses_a)}, {len(doses_b)})."
                ),
            }

        try:
            da = np.array([float(x) for x in doses_a])
            db = np.array([float(x) for x in doses_b])
            vm = np.array([[float(x) for x in row] for row in viability_matrix])
        except (ValueError, TypeError) as e:
            return {"status": "error", "error": f"Invalid numeric values: {e}"}

        # NaN in dose arrays bypasses the >= 0 guard below (NaN < 0 = False) and
        # corrupts Hill fits, producing misleading "fitting failed" messages.
        for arr, name in [(da, "doses_a"), (db, "doses_b")]:
            if np.any(~np.isfinite(arr)):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains non-finite values (NaN or inf). "
                        "All dose values must be finite real numbers."
                    ),
                }

        # NaN/inf in viability_matrix propagates to inhibition → ZIP scores are NaN
        # or -inf, which are invalid JSON and produce meaningless synergy labels.
        if np.any(~np.isfinite(vm)):
            return {
                "status": "error",
                "error": (
                    "viability_matrix contains non-finite values (NaN or inf). "
                    "All viability values must be finite real numbers. "
                    "Replace missing values (NaN) or outliers (inf) before computing ZIP scores."
                ),
            }

        if vm.shape != (len(da), len(db)):
            return {
                "status": "error",
                "error": f"viability_matrix shape {vm.shape} must be ({len(da)}, {len(db)})",
            }

        # ZIP requires dose=0 as the first element in each dose array so that
        # the first row (inhibition[0, :]) and first column (inhibition[:, 0])
        # represent single-drug marginals (drug B alone and drug A alone).
        has_zero_a = float(da[0]) == 0.0
        has_zero_b = float(db[0]) == 0.0
        if not has_zero_a or not has_zero_b:
            return {
                "status": "error",
                "error": (
                    "ZIP model requires doses_a[0] == 0 and doses_b[0] == 0 so that "
                    "the first row/column of viability_matrix represents single-drug "
                    "effects. Please include a zero-dose (vehicle control) as the "
                    "first element of each dose array."
                ),
            }

        # Validate dose values are non-negative (DS-5).
        if np.any(da < 0) or np.any(db < 0):
            return {
                "status": "error",
                "error": "All dose values in doses_a and doses_b must be non-negative (>= 0).",
            }

        # The ZIP model anchors its marginal Hill curves
        # at inhibition=0 when dose=0.  This is only correct when the vehicle-control
        # viability (viability_matrix[0][0]) has been normalized to exactly 100% (or 1.0
        # for fractional scale).  If the control is 90% (under-normalized) or 110%
        # (over-normalized), all inhibition values are shifted by ~10 percentage points,
        # injecting systematic bias into the ZIP delta scores.  Warn the user if the
        # control value deviates by more than 5% from the expected 100/1.0 anchor.
        vm00 = float(vm[0, 0])
        vm_max_check = float(vm.max())
        _expected_ctrl = 100.0 if vm_max_check > 5 else 1.0
        _ctrl_dev = abs(vm00 - _expected_ctrl) / _expected_ctrl
        _control_norm_note = None
        if _ctrl_dev > 0.05:
            _control_norm_note = (
                f"Vehicle-control viability (viability_matrix[0][0] = {vm00:.4g}) "
                f"deviates by {round(_ctrl_dev * 100, 1)}% from the expected anchor of "
                f"{_expected_ctrl:.0f}. The ZIP model assumes the control is normalized "
                f"to {_expected_ctrl:.0f}; a mis-normalized control shifts all inhibition "
                "values and biases ZIP scores toward false antagonism or false synergy. "
                f"Consider normalizing: vm / vm[0,0] × {_expected_ctrl:.0f}."
            )

        # Negative viability values are physically impossible.
        # They typically arise from background-subtraction artefacts (e.g., a blank-well
        # value subtracted from low-signal wells).  Returning a "success" with inhibition
        # > 1.0 (= 1 − negative_viability) would silently corrupt every downstream metric.
        n_neg_vm = int(np.sum(vm < 0))
        if n_neg_vm > 0:
            return {
                "status": "error",
                "error": (
                    f"viability_matrix contains {n_neg_vm} negative value(s) "
                    f"(min = {float(vm.min()):.4g}). "
                    "Cell viability cannot be negative. Negative values typically "
                    "indicate background-subtraction artefacts. "
                    "Clip values to 0 (e.g., np.clip(matrix, 0, None)) before calling "
                    "this function, or review your normalization procedure."
                ),
            }

        # Scale detection: convert viability → inhibition = 1 - viability.
        # Threshold rationale:
        #   > 5: unambiguously percentage scale (typical values like 50, 80, 95)
        #   (1, 5]: ambiguous — most likely fractional with noise or mild outliers;
        #           treat as fractional and warn (old threshold of > 2 silently treated
        #           values like 2.05 as percentage scale, corrupting the data)
        #   ≤ 1: clearly fractional scale (0–1)
        vm_max = float(vm.max())
        scale_note = None
        if vm_max > 5:
            # Unambiguously percentage scale (0–100): values like 50, 80, 95
            inhibition = 1 - vm / 100
        elif vm_max > 1:
            # Ambiguous or clearly fractional with noise. Values slightly above 1.0
            # (e.g., 1.05) are common normalization artefacts; values up to ~5 could
            # be fractional outliers. In all cases, treat as fractional scale and warn.
            inhibition = 1 - vm
            if vm_max > 2:
                scale_note = (
                    f"viability_matrix max ({vm_max:.4f}) exceeds 2.0. "
                    "Treating as fractional scale (0–1). If data is in percentage "
                    "(0–100), divide all values by 100 before passing to this function. "
                    "Values > 5 are treated as unambiguously percentage scale."
                )
            else:
                scale_note = (
                    f"viability_matrix max ({vm_max:.4f}) slightly exceeds 1.0. "
                    "Treating as fractional scale (0–1). If data is in percentage (0–100), "
                    "divide all values by 100 before passing to this function, or ensure "
                    "your vehicle control viability is normalized to 1.0."
                )
        else:
            # Clearly fractional scale (0–1)
            inhibition = 1 - vm

        # After scale detection, verify that the computed inhibition values
        # are physically plausible.  When a matrix contains mixed-scale data (e.g., one
        # row is fractional 0–1 while the rest are percentage 0–100), the scale detector
        # bases its decision on a single global max and misclassifies the minority rows.
        # The resulting inhibition matrix will contain impossible values (> 1.2 or < −0.2)
        # that silently corrupt the ZIP score.  Detect and warn rather than silently
        # returning a meaningless result.
        n_impossible_high = int(np.sum(inhibition > 1.2))
        # Strict `< -0.2` misses the IEEE-754 representation of exactly
        # 120% viability.  `1 - 120/100` evaluates to -0.19999999999999996 in float
        # (about 4e-17 above -0.2), so the exact boundary case silently bypasses the
        # impossible-inhibition guard.  Use `< -0.2 + 1e-9` (≈ -0.199999999) which
        # lies above the float representation of -0.2 and correctly catches 120% viability.
        n_impossible_low = int(np.sum(inhibition < -0.2 + 1e-9))
        if n_impossible_high > 0 or n_impossible_low > 0:
            mixed_scale_note = (
                f"After scale conversion, {n_impossible_high + n_impossible_low} "
                "cell(s) in viability_matrix produce inhibition outside [−0.2, 1.2] "
                f"(impossible range). This indicates mixed-scale data "
                f"(vm_max = {float(vm.max()):.4g}): some cells appear to be in "
                "fractional (0–1) scale while others are in percentage (0–100) scale. "
                "Ensure the entire matrix uses the same scale."
            )
            if scale_note:
                scale_note = scale_note + " " + mixed_scale_note
            else:
                scale_note = mixed_scale_note

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
                # Require at least 3 unique concentration levels: curve_fit on a
                # single unique x-value is degenerate (produces meaningless parameters
                # and scipy warns about covariance estimation failure).
                if len(np.unique(d)) < 3:
                    return None
                # Guard: majority-negative inhibition indicates the scale_warning
                # scenario (viability > 1.0 treated as fractional, then 1-vm < 0).
                # curve_fit can still "succeed" on mixed negative/positive arrays,
                # producing parameters that look plausible but are physically wrong
                # (e.g., IC50 extrapolated to a dose that barely produces inhibition).
                # Reject: if more than half of effects are negative, the data is
                # too corrupted by scale ambiguity for reliable Hill fitting.
                n_negative = int(np.sum(e < 0))
                if n_negative > len(e) / 2:
                    return None

                # Drug has no measurable inhibition: emax_init=0 puts the initial
                # guess on the lower bound — curve_fit produces degenerate Hill
                # parameters (IC50 near zero, arbitrary hill slope).
                emax_init = float(max(e))
                if emax_init <= 0:
                    return None
                # Flat dose-response: constant (non-zero) inhibition is also
                # degenerate — IC50 is not identifiable and curve_fit converges
                # to an arbitrary parameter set.  Same check as _fit_hill_for_loewe.
                if float(np.max(e) - np.min(e)) < 1e-6:
                    return None
                p0 = [np.median(d), 1.0, emax_init]
                bounds = ([0, 0.1, 0], [np.inf, 10, 1])
                popt, _ = curve_fit(hill_curve, d, e, p0=p0, bounds=bounds, maxfev=5000)
                return popt
            except Exception:
                return None

        # Marginals: first column = drug A alone (db=0), first row = drug B alone (da=0)
        effects_a_marginal = inhibition[:, 0]  # drug A at each dose, drug B = 0
        effects_b_marginal = inhibition[0, :]  # drug B at each dose, drug A = 0

        params_a = fit_hill(da, effects_a_marginal)
        params_b = fit_hill(db, effects_b_marginal)

        if params_a is None or params_b is None:
            # ZIP fundamentally requires Hill curve fits for each drug to compute
            # the expected interaction surface.  Without fitted Hill parameters we
            # cannot compute a valid ZIP score — returning a Bliss-independence
            # surface here would silently report the wrong model.
            failed = []
            if params_a is None:
                failed.append("drug A")
            if params_b is None:
                failed.append("drug B")
            # Include scale_note in the error so the user gets the
            # actionable hint ("divide by 100 if data is in percentage") even when
            # Hill fitting fails (which it will when 1 < vm_max ≤ 5 because all
            # inhibition values are negative after 1 − fractional > 1).
            scale_hint = f" {scale_note}" if scale_note else ""
            return {
                "status": "error",
                "error": (
                    f"ZIP model requires Hill curve fitting for each drug, but fitting "
                    f"failed for {' and '.join(failed)}. "
                    "Ensure each drug has ≥3 non-zero dose points with measurable inhibition. "
                    "Use calculate_bliss for a simpler non-parametric synergy score."
                    f"{scale_hint}"
                ),
            }
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

        # The ZIP delta mean was computed over ALL cells including
        # the first row (drug A = 0, i.e. drug B single-agent) and first column (drug B
        # = 0, i.e. drug A single-agent).  These border cells are structural zeros by
        # construction (the Hill fits are calibrated to exactly those marginal values),
        # so including them in the mean dilutes the true interior synergy score.  Per
        # Yadav et al. (2015), the summary ZIP score uses the interior combination cells
        # only.  Exclude row 0 and column 0 from the mean/max/min.
        if delta.shape[0] > 1 and delta.shape[1] > 1:
            delta_interior = delta[1:, 1:]
        else:
            delta_interior = delta  # fallback if only 1 dose per compound
        # Apply + 0.0 to eliminate IEEE-754 negative zero (-0.0) from all rounded
        # ZIP scores, consistent with the Bliss and HSA fix applied in Round 17.
        # round(-0.004, 2) returns -0.0 in Python; json.dumps serializes it as "-0.0".
        _mean_zip = round(float(np.mean(delta_interior)), 2) + 0.0
        zip_data = {
            "model": "ZIP (Zero Interaction Potency)",
            "mean_zip_score": _mean_zip,
            "max_zip_score": round(float(np.max(delta_interior)), 2) + 0.0,
            "min_zip_score": round(float(np.min(delta_interior)), 2) + 0.0,
            "zip_delta_matrix": [
                [round(float(v), 2) + 0.0 for v in row] for row in delta
            ],
            "interpretation": self._interpret_synergy_score(_mean_zip, "zip"),
            "note": "ZIP delta > 10: synergy; < -10: antagonism. Based on Yadav et al. (2015).",
        }
        if scale_note:
            zip_data["scale_warning"] = scale_note
        if _control_norm_note:
            zip_data["control_normalization_warning"] = _control_norm_note

        return {"status": "success", "data": zip_data}

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
            # Require at least 3 unique concentration levels: curve_fit on a single
            # unique x-value is degenerate (produces meaningless parameters and scipy
            # warns about covariance estimation failure).
            if len(np.unique(d)) < 3:
                return None
            # Flat dose-response: all effects are identical (or nearly so).
            # curve_fit converges to IC50 at the lower bound (1e-15), which rounds
            # to 0.0 — a scientifically invalid IC50 suggesting infinite potency.
            if float(np.max(e) - np.min(e)) < 1e-6:
                return None  # IC50 is not identifiable for flat data
            # Initial guesses
            emax_init = float(np.max(e))
            if emax_init <= 0:
                emax_init = 0.5
            dm_init = float(np.median(d))
            m_init = 1.0
            p0 = [dm_init, m_init, emax_init]
            bounds = ([1e-15, 0.1, 1e-6], [np.inf, 10.0, 1.0])

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

        # NaN comparison always returns False: NaN <= 0 = False, so NaN bypasses the
        # positivity guard and enters Hill fitting, producing misleading "infinite potency"
        # or "effect outside model range" errors. Check isfinite first.
        if not math.isfinite(da_combo) or not math.isfinite(db_combo):
            return {
                "status": "error",
                "error": (
                    f"dose_a_combo ({da_combo}) and dose_b_combo ({db_combo}) must be "
                    "finite positive numbers. NaN and inf are not valid dose values."
                ),
            }

        # Zero or negative combination doses are physically impossible (DS-1).
        if da_combo <= 0 or db_combo <= 0:
            return {
                "status": "error",
                "error": (
                    f"dose_a_combo ({da_combo}) and dose_b_combo ({db_combo}) must both "
                    "be positive (> 0). Zero or negative doses are not physically "
                    "meaningful in a combination experiment."
                ),
            }

        # Validate effect values in (0, 1) exclusive on both ends.
        # Zero: causes inverse_hill to return 0.0, triggering a confusing downstream error.
        # 1.0: nearly always causes inverse_hill to return inf because the Hill model
        # bounds emax to [1e-6, 1.0], making emax < 1.0 in almost all real fits.
        # An effect_combo = 1.0 effectively requests 100% inhibition which exceeds
        # the single-agent maximum — the Loewe index is undefined.
        if not (0 < e_combo < 1):
            return {
                "status": "error",
                "error": (
                    f"effect_combo={e_combo} must be in (0, 1) exclusive on both ends. "
                    "Zero effect makes the Loewe index indeterminate (no dose needed). "
                    "An effect of 1.0 (100% inhibition) nearly always exceeds the fitted "
                    "single-agent maximum, making inverse_hill undefined. Use a value "
                    "strictly between 0 and 1 (e.g., 0.5 for IC50)."
                ),
            }
        try:
            ea_arr = [float(x) for x in effects_a_single]
            eb_arr = [float(x) for x in effects_b_single]
        except (ValueError, TypeError) as e:
            return {
                "status": "error",
                "error": f"Invalid numeric values in effects: {e}",
            }
        for name, arr in [("effects_a_single", ea_arr), ("effects_b_single", eb_arr)]:
            bad = [i for i, v in enumerate(arr) if not (0 <= v <= 1)]
            if bad:
                return {
                    "status": "error",
                    "error": (
                        f"{name} values must be between 0 and 1 (fractional effects). "
                        f"Invalid values at indices: {bad}"
                    ),
                }

        # NaN in dose arrays is silently dropped by _fit_hill_for_loewe (valid = doses > 0
        # returns False for NaN), potentially leaving too few points for a reliable fit.
        # Detect and reject up front with a clear error.
        try:
            da_arr = np.array([float(x) for x in doses_a_single])
            db_arr = np.array([float(x) for x in doses_b_single])
        except (ValueError, TypeError) as e:
            return {
                "status": "error",
                "error": f"Invalid numeric values in dose arrays: {e}",
            }
        for arr, name in [(da_arr, "doses_a_single"), (db_arr, "doses_b_single")]:
            if np.any(~np.isfinite(arr)):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains non-finite values (NaN or inf). "
                        "All dose values must be finite real numbers."
                    ),
                }

        # Negative doses are physically invalid: _fit_hill_for_loewe silently drops
        # them via `valid = doses > 0`, possibly leaving too few points for fitting
        # and causing a misleading "too few data points" error.  Reject upfront.
        for arr, name in [(da_arr, "doses_a_single"), (db_arr, "doses_b_single")]:
            if np.any(arr < 0):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains negative values. All dose values must be "
                        "non-negative (>= 0). Negative doses are not physically meaningful."
                    ),
                }

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

        # Loewe excess score: positive = synergy (CI < 1), negative = antagonism (CI > 1)
        loewe_excess = 1.0 - loewe_index

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
                "loewe_excess_score": 0.0 + round(float(loewe_excess), 2),
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
                "note": (
                    "Loewe index < 1 = synergy; = 1 = additive; > 1 = antagonism. "
                    "loewe_excess_score = 1 - index: positive = synergy, negative = antagonism. "
                    "Based on Loewe & Muischnek (1926)."
                ),
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

        # NaN comparison always returns False: NaN <= 0 = False, so NaN bypasses the
        # positivity guard and produces a CI of 0 regardless of the combination effect,
        # falsely suggesting very strong synergy. Check isfinite first.
        if not math.isfinite(da_combo) or not math.isfinite(db_combo):
            return {
                "status": "error",
                "error": (
                    f"dose_a_combo ({da_combo}) and dose_b_combo ({db_combo}) must be "
                    "finite positive numbers. NaN and inf are not valid dose values."
                ),
            }

        # Zero or negative combination doses are physically impossible (DS-1).
        if da_combo <= 0 or db_combo <= 0:
            return {
                "status": "error",
                "error": (
                    f"dose_a_combo ({da_combo}) and dose_b_combo ({db_combo}) must both "
                    "be positive (> 0). Zero or negative doses are not physically "
                    "meaningful in a combination experiment and produce a CI of zero "
                    "regardless of the combination effect, falsely suggesting synergy."
                ),
            }

        if not (0 < fa_combo < 1):
            return {
                "status": "error",
                "error": f"effect_combo={fa_combo} must be between 0 and 1 (exclusive) for CI calculation",
            }

        # Validate single-agent effect values are in [0,1]
        try:
            ea_arr = [float(x) for x in effects_a_single]
            eb_arr = [float(x) for x in effects_b_single]
        except (ValueError, TypeError) as e:
            return {
                "status": "error",
                "error": f"Invalid numeric values in effects: {e}",
            }
        for name, arr in [("effects_a_single", ea_arr), ("effects_b_single", eb_arr)]:
            bad = [i for i, v in enumerate(arr) if not (0 <= v <= 1)]
            if bad:
                return {
                    "status": "error",
                    "error": (
                        f"{name} values must be between 0 and 1 (fractional effects). "
                        f"Invalid values at indices: {bad}"
                    ),
                }

        # NaN in dose arrays is silently dropped by _fit_hill_for_loewe (valid = doses > 0
        # returns False for NaN), potentially leaving too few points for a reliable fit.
        try:
            da_arr_ci = np.array([float(x) for x in doses_a_single])
            db_arr_ci = np.array([float(x) for x in doses_b_single])
        except (ValueError, TypeError) as e:
            return {
                "status": "error",
                "error": f"Invalid numeric values in dose arrays: {e}",
            }
        for arr, name in [(da_arr_ci, "doses_a_single"), (db_arr_ci, "doses_b_single")]:
            if np.any(~np.isfinite(arr)):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains non-finite values (NaN or inf). "
                        "All dose values must be finite real numbers."
                    ),
                }

        # Negative doses are physically invalid: _fit_hill_for_loewe silently drops
        # them via `valid = doses > 0`, possibly leaving too few points for fitting.
        for arr, name in [(da_arr_ci, "doses_a_single"), (db_arr_ci, "doses_b_single")]:
            if np.any(arr < 0):
                return {
                    "status": "error",
                    "error": (
                        f"{name} contains negative values. All dose values must be "
                        "non-negative (>= 0). Negative doses are not physically meaningful."
                    ),
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

        # MNEE term (da_combo*db_combo)/(dx_a*dx_b) can overflow to inf
        # when dx_a or dx_b is extremely small (effect near single-agent Emax, so the
        # equivalent single-drug dose is astronomically large relative to the combination
        # dose). ci=inf propagates to "Very strong antagonism" label but round(inf, 4)
        # is still inf, which is invalid JSON. Return an informative error instead.
        if not math.isfinite(ci):
            return {
                "status": "error",
                "error": (
                    f"Combination Index is non-finite (CI = {ci}). This occurs when "
                    "dx_a or dx_b (the single-agent doses that produce the combination "
                    "effect level) are extremely small or zero, meaning the combination "
                    "effect is near or exceeds the single-agent Emax. "
                    "Verify that effect_combo is within the range of the single-agent "
                    "dose-response curves, or use the 'mutually_exclusive' assumption."
                ),
            }

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
