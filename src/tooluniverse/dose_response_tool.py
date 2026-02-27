"""
Dose-Response Analysis Tool

Implements 4-Parameter Logistic (4PL) curve fitting for dose-response analysis.
Calculates IC50, Hill slope, Emax, Emin, and curve fitting statistics.

No external API calls. Uses scipy.optimize for curve fitting.
"""

import math
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    import numpy as np
    from scipy.optimize import curve_fit
    from scipy.stats import pearsonr

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def _hill_equation(x, emin, emax, ec50, n):
    """Hill / 4PL sigmoidal model: f(x) = Emin + (Emax - Emin) / (1 + (EC50 / x)^n)"""
    x_clipped = np.where(x > 0, x, 1e-15)
    return emin + (emax - emin) / (1.0 + (ec50 / x_clipped) ** n)


@register_tool("DoseResponseTool")
class DoseResponseTool(BaseTool):
    """
    Local dose-response curve fitting and IC50 calculation tools.

    Implements the 4-Parameter Logistic (4PL) model:
    f(x) = Bottom + (Top - Bottom) / (1 + (IC50/x)^Hill)

    No external API required. Uses scipy.optimize for curve fitting.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute dose-response analysis."""
        if not HAS_SCIPY:
            return {
                "status": "error",
                "error": "scipy and numpy are required. Install with: pip install scipy numpy",
            }

        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "fit_curve": self._fit_curve,
            "calculate_ic50": self._calculate_ic50,
            "compare_potency": self._compare_potency,
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
            return {"status": "error", "error": f"Analysis failed: {str(e)}"}

    def _fit_4pl(
        self, concentrations: List[float], responses: List[float]
    ) -> Dict[str, Any]:
        """Fit Hill / 4PL sigmoidal model to dose-response data."""
        x = np.array(concentrations, dtype=float)
        y = np.array(responses, dtype=float)

        if len(x) < 4:
            return {"error": "At least 4 data points required for 4PL fitting"}

        if np.any(~np.isfinite(y)):
            return {
                "error": (
                    "Response values contain non-finite values (NaN or inf). "
                    "All responses must be finite real numbers. "
                    "Remove or correct the affected data points before fitting."
                )
            }

        # NaN comparison always returns False: NaN <= 0 = False, so NaN bypasses the
        # positivity check and is passed to log(x) inside ec50_init, producing cryptic
        # "domain error" or NaN results.  Check isfinite BEFORE the <= 0 guard.
        if np.any(~np.isfinite(x)):
            return {
                "error": (
                    "Concentration values contain non-finite values (NaN or inf). "
                    "All concentrations must be finite positive numbers. "
                    "Remove or correct the affected data points before fitting."
                )
            }

        if np.any(x <= 0):
            return {"error": "All concentrations must be positive (> 0)"}

        # Detect all-identical concentrations: if every x value is the same, the
        # dose-response curve is unidentifiable regardless of the response values.
        # This is distinct from the flat-response guard below — here the problem is
        # zero dose range (no concentration gradient), not zero effect range.
        if len(np.unique(x)) < 2:
            return {
                "error": (
                    "All concentration values are identical (no dose range). "
                    "IC50 estimation requires at least 2 distinct concentration levels "
                    "to define the dose-response relationship. Use a dose series spanning "
                    "multiple orders of magnitude (e.g., 0.001–100 μM)."
                )
            }

        # Detect flat response data: if all responses are identical (or near-identical),
        # the 4PL model is not identifiable — IC50 cannot be estimated.
        y_range = float(np.max(y) - np.min(y))
        if y_range < 1e-10:
            return {
                "error": (
                    "All response values are identical (flat data). "
                    "Cannot estimate IC50 — the dose-response relationship is not identifiable. "
                    "A sigmoidal model requires variation in response across concentrations."
                )
            }

        # Starting estimates:
        # Emin / Emax: 10th / 90th percentile (robust to outliers at curve extremes)
        # EC50: geometric centre of the concentration range (natural for log-spaced data)
        # Hill coefficient n = 1 (standard starting point for unimodal sigmoidal)
        emin_init = float(np.percentile(y, 10))
        emax_init = float(np.percentile(y, 90))
        ec50_init = float(np.exp(np.mean(np.log(x))))
        n_init = 1.0

        try:
            popt, pcov = curve_fit(
                _hill_equation,
                x,
                y,
                p0=[emin_init, emax_init, ec50_init, n_init],
                # EC50 must be positive; Hill exponent constrained to (0.05, 20)
                bounds=(
                    [-np.inf, -np.inf, 1e-15, 0.05],
                    [np.inf, np.inf, np.inf, 20.0],
                ),
                max_nfev=3000,
            )
            emin, emax, ec50, n_hill = popt

            # Detect Hill slope at numerical lower bound (0.05).
            # This occurs when the optimal n would be even smaller — typically
            # a stimulatory dose-response, very shallow curve, or insufficient
            # data range.  Flag with a warning rather than silently returning
            # what look like plausible (but physically incorrect) parameters.
            hill_bound_warning = None
            if float(n_hill) <= 0.05 + 1e-4:
                hill_bound_warning = (
                    "Hill slope converged at the lower bound (0.05). "
                    "This may indicate a stimulatory (increasing) dose-response, "
                    "a very shallow curve, or data that do not span the sigmoidal "
                    "range. Verify that responses decrease with increasing "
                    "concentration. The 4PL model may not be appropriate."
                )
            elif float(n_hill) >= 20.0 - 1e-4:
                hill_bound_warning = (
                    "Hill slope converged at the upper bound (20.0). "
                    "This indicates an extremely steep dose-response (near-threshold "
                    "or switch-like response). The true Hill slope may be even steeper "
                    "than the model allows. Treat EC50 and Hill slope with caution; "
                    "consider whether the sigmoidal model is appropriate for this data."
                )

            # Coefficient of determination: R² = 1 - SSE/SST
            y_hat = _hill_equation(x, *popt)
            y_mean = float(np.mean(y))
            sse_resid = float(np.sum((y - y_hat) ** 2))
            sse_total = float(np.sum((y - y_mean) ** 2))
            r_sq = (1.0 - sse_resid / sse_total) if sse_total > 1e-15 else 0.0

            # Use full float precision for IC50.
            # Rounding to a fixed number of decimal places (e.g. round(x, 6))
            # silently truncates IC50 values < 5e-7 to 0.0, which is incorrect for
            # typical pharmacological IC50s in the nanomolar range (1e-9 to 1e-7 M).
            ec50_f = float(ec50)

            # Parameter standard errors from diagonal of covariance matrix.
            # When n_data == n_parameters (e.g. exactly 4 points for a 4PL model),
            # scipy sets pcov to all-inf (zero degrees of freedom for residuals).
            # Guard: replace inf with None so the output is valid JSON.
            # Stimulatory curve check (compute once; applied to both singular and main paths).
            # In the 4PL model: f(x→0) = emin, f(x→∞) = emax.
            # Inhibitory curves: emin > emax.  Stimulatory curves: emax > emin.
            stimulatory_warning = None
            if float(emax) > float(emin):
                # Apply + 0.0 to eliminate IEEE-754 negative zero (-0.0)
                # that arises from round(~0.0, 4) when scipy returns a value like
                # -7.8e-15.  Same pattern applied to bottom/top fields below.
                _emin_disp = round(float(emin), 4) + 0.0
                _emax_disp = round(float(emax), 4) + 0.0
                stimulatory_warning = (
                    "Stimulatory dose-response detected: the fitted curve rises with "
                    f"increasing concentration (emin = {_emin_disp}, "
                    f"emax = {_emax_disp}, emax > emin). "
                    "The fitted EC50 represents activation potency (EC50), not inhibitory "
                    "potency (IC50). Interpret as EC50/ED50 rather than IC50."
                )

            perr = np.sqrt(np.diag(np.abs(pcov)))
            if not np.all(np.isfinite(perr)):
                # Covariance is singular — CIs and SEs are not estimable.
                singular_result = {
                    "bottom": round(float(emin), 4) + 0.0,
                    "top": round(float(emax), 4) + 0.0,
                    "ic50": ec50_f,
                    "hill_slope": round(float(n_hill), 4),
                    "r_squared": round(float(r_sq), 4),
                    "ic50_95ci": None,
                    "standard_errors": None,
                    "ci_note": (
                        "Covariance matrix is singular (zero residual degrees of "
                        "freedom, n_data == n_parameters). Standard errors and "
                        "confidence intervals cannot be estimated. Add more data "
                        "points to enable uncertainty quantification."
                    ),
                    "fitted_values": [round(float(v), 4) for v in y_hat],
                }
                if hill_bound_warning:
                    singular_result["hill_slope_warning"] = hill_bound_warning
                if stimulatory_warning:
                    singular_result["stimulatory_curve_warning"] = stimulatory_warning
                return singular_result

            # Log-scale delta method CI (Motulsky & Christopoulos 2004):
            #   SE_log = SE_ec50 / ec50  (delta method applied to log(EC50))
            #   CI = [ec50 * exp(-1.96*SE_log), ec50 * exp(+1.96*SE_log)]
            # Always positive and asymmetric; uses z=1.96 for exact 95%.
            se_log_ec50 = perr[2] / ec50
            perr2_f = float(perr[2])
            # Guard against overflow: when IC50 lies far outside the tested
            # concentration range the SE is enormous and exp overflows to inf.
            # Return None for the CI with an explanatory note.
            with np.errstate(over="ignore"):
                ci_lo_raw = float(ec50 * np.exp(-1.96 * se_log_ec50))
                ci_hi_raw = float(ec50 * np.exp(+1.96 * se_log_ec50))
            if np.isfinite(ci_lo_raw) and np.isfinite(ci_hi_raw):
                ic50_ci = [ci_lo_raw, ci_hi_raw]
                ci_overflow_note = None
            else:
                ic50_ci = None
                ci_overflow_note = (
                    "IC50 confidence interval could not be computed: the SE of "
                    "log(IC50) is too large, likely because the IC50 lies outside "
                    "the tested concentration range. Extend the concentration range "
                    "to include the half-maximal response."
                )

            main_result = {
                "bottom": round(float(emin), 4) + 0.0,
                "top": round(float(emax), 4) + 0.0,
                "ic50": ec50_f,
                "hill_slope": round(float(n_hill), 4),
                "r_squared": round(float(r_sq), 4),
                "ic50_95ci": ic50_ci,
                "standard_errors": {
                    "bottom": round(float(perr[0]), 4),
                    "top": round(float(perr[1]), 4),
                    "ic50": perr2_f,
                    "hill": round(float(perr[3]), 4),
                },
                "fitted_values": [round(float(v), 4) for v in y_hat],
            }
            if ci_overflow_note:
                main_result["ci_note"] = ci_overflow_note
            if hill_bound_warning:
                main_result["hill_slope_warning"] = hill_bound_warning
            if stimulatory_warning:
                main_result["stimulatory_curve_warning"] = stimulatory_warning
            return main_result
        except RuntimeError:
            return {"error": "4PL curve fitting did not converge. Check data quality."}
        except Exception as e:
            return {"error": f"Curve fitting failed: {str(e)}"}

    def _fit_curve(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fit 4PL dose-response curve and return all parameters."""
        concentrations = arguments.get("concentrations", [])
        responses = arguments.get("responses", [])

        if not concentrations or not responses:
            return {
                "status": "error",
                "error": "concentrations and responses are required",
            }

        if len(concentrations) != len(responses):
            return {
                "status": "error",
                "error": "concentrations and responses must have the same length",
            }

        result = self._fit_4pl(concentrations, responses)

        if "error" in result:
            return {"status": "error", "error": result["error"]}

        data = {
            "model": "4-Parameter Logistic (4PL)",
            "formula": "f(x) = Bottom + (Top - Bottom) / (1 + (IC50/x)^Hill)",
            "parameters": {
                # Labels corrected to match pharmacological convention.
                # emax = numerically larger asymptote (uninhibited baseline ≈100% for inhibitory).
                # emin = numerically smaller asymptote (inhibited floor ≈0% for inhibitory).
                "top_emax": max(result["top"], result["bottom"]),
                "bottom_emin": min(result["top"], result["bottom"]),
                "ic50": result["ic50"],
                "hill_slope": result["hill_slope"],
            },
            "goodness_of_fit": {
                "r_squared": result["r_squared"],
            },
            "ic50_95_confidence_interval": result["ic50_95ci"],
            "standard_errors": result["standard_errors"],
            "fitted_values": result["fitted_values"],
            "input_concentrations": list(concentrations),
            "input_responses": list(responses),
        }
        if "ci_note" in result:
            data["ci_note"] = result["ci_note"]
        if "hill_slope_warning" in result:
            data["hill_slope_warning"] = result["hill_slope_warning"]
        if "stimulatory_curve_warning" in result:
            data["stimulatory_curve_warning"] = result["stimulatory_curve_warning"]
        # Warn when 4PL fit quality is poor.  _compare_potency already
        # warns when R² < 0.8; _fit_curve and _calculate_ic50 had no equivalent
        # check, so the same bad IC50 was silently accepted here.
        r_sq_val = result["r_squared"]
        if r_sq_val < 0.8:
            data["fit_quality_warning"] = (
                f"Poor 4PL fit quality (R² = {round(r_sq_val, 4)} < 0.8). "
                "The fitted parameters (IC50, Hill slope, Emax) may be unreliable. "
                "Check for noisy data, insufficient data points, or a non-sigmoidal "
                "dose-response relationship."
            )
        # _calculate_ic50 already emits ic50_extrapolation_warning
        # and ic50_range_warning, but _fit_curve silently omitted them even though it
        # returns the same IC50 parameter.  Add the same checks here.
        ic50_val = result["ic50"]
        conc_arr = np.array(concentrations, dtype=float)
        resp_arr_fc = np.array(responses, dtype=float)
        conc_min = float(np.min(conc_arr))
        conc_max = float(np.max(conc_arr))
        if ic50_val < conc_min or ic50_val > conc_max:
            data["ic50_extrapolation_warning"] = (
                f"The estimated IC50 ({ic50_val:.4g}) is outside the tested "
                f"concentration range [{conc_min:.4g}, {conc_max:.4g}]. "
                "This is an extrapolated value and may be unreliable. "
                "Extend the concentration range to include the half-maximal response."
            )
        fitted_dr = abs(float(result["top"]) - float(result["bottom"]))
        obs_range_fc = float(np.max(resp_arr_fc)) - float(np.min(resp_arr_fc))
        midpt_fc = (result["top"] + result["bottom"]) / 2.0
        midpt_check_fc = (
            float(np.min(resp_arr_fc)) > midpt_fc
            or float(np.max(resp_arr_fc)) < midpt_fc
        )
        narrow_cov_fc = fitted_dr > 0 and obs_range_fc < 0.5 * fitted_dr
        if midpt_check_fc or narrow_cov_fc:
            data["ic50_range_warning"] = (
                "The response data may not adequately bracket the half-maximal response. "
                f"Observed response range ({obs_range_fc:.4g}) covers "
                f"{round(100 * obs_range_fc / fitted_dr, 1) if fitted_dr > 0 else 'N/A'}% "
                f"of the fitted dynamic range ({fitted_dr:.4g}). "
                "The IC50 is likely extrapolated outside the measured range and should "
                "be interpreted with caution."
            )
        return {"status": "success", "data": data}

    def _calculate_ic50(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Extract IC50 from dose-response data via 4PL fitting."""
        concentrations = arguments.get("concentrations", [])
        responses = arguments.get("responses", [])

        if not concentrations or not responses:
            return {
                "status": "error",
                "error": "concentrations and responses are required",
            }

        if len(concentrations) != len(responses):
            return {
                "status": "error",
                "error": "concentrations and responses must have the same length",
            }

        result = self._fit_4pl(concentrations, responses)

        if "error" in result:
            return {"status": "error", "error": result["error"]}

        # Np.log10(x) where x ≈ 1.0 can return a value like −1.93e-16,
        # which round(…, 4) maps to −0.0 (IEEE 754 negative zero).  −0.0 is equal to
        # 0.0 mathematically but looks wrong in JSON output and confuses downstream
        # consumers.  Adding 0.0 converts negative zero to positive zero per IEEE 754.
        log_ic50_val = (
            0.0 + round(float(np.log10(result["ic50"])), 4)
            if result["ic50"] > 0
            else None
        )

        # Emax/emin were inverted relative to pharmacological convention.
        # The 4PL Hill equation f(x) = emin_param + (emax_param - emin_param)/(1+(EC50/x)^n)
        # means: emin_param = f(x→0) = low-dose asymptote = uninhibited baseline (≈100%)
        # and emax_param = f(x→∞) = high-dose asymptote = inhibited floor (≈0%) for an
        # inhibitory assay.  Reporting "emax" = emax_param = 0% and "emin" = 100% is the
        # INVERSE of the standard definition (Emax = max effect = baseline ≈ 100%).
        # Fix: emax = max(top, bottom) = numerically larger asymptote = uninhibited baseline;
        #      emin = min(top, bottom) = numerically smaller asymptote = inhibited floor.
        _top_val = result["top"]
        _bot_val = result["bottom"]
        data = {
            "ic50": result["ic50"],
            "ic50_95_confidence_interval": result["ic50_95ci"],
            "hill_slope": result["hill_slope"],
            "emax": max(_top_val, _bot_val),
            "emin": min(_top_val, _bot_val),
            "r_squared": result["r_squared"],
            "log_ic50": log_ic50_val,
            "note": "IC50 estimated via 4PL curve fitting",
        }
        if "ci_note" in result:
            data["ci_note"] = result["ci_note"]
        if "hill_slope_warning" in result:
            data["hill_slope_warning"] = result["hill_slope_warning"]
        if "stimulatory_curve_warning" in result:
            data["stimulatory_curve_warning"] = result["stimulatory_curve_warning"]
        # fit_quality_warning (shared with _fit_curve)
        r_sq_val = result["r_squared"]
        if r_sq_val < 0.8:
            data["fit_quality_warning"] = (
                f"Poor 4PL fit quality (R² = {round(r_sq_val, 4)} < 0.8). "
                "The IC50 estimate may be unreliable. Check for noisy data, "
                "insufficient data points, or a non-sigmoidal dose-response."
            )

        # Warn if the IC50 falls outside the tested concentration range
        # (extrapolated IC50 values are unreliable).
        ic50_val = result["ic50"]
        conc_min = float(np.min(concentrations))
        conc_max = float(np.max(concentrations))
        if ic50_val < conc_min or ic50_val > conc_max:
            data["ic50_extrapolation_warning"] = (
                f"The estimated IC50 ({ic50_val:.4g}) is outside the tested "
                f"concentration range [{conc_min:.4g}, {conc_max:.4g}]. "
                "This is an extrapolated value and may be unreliable. "
                "Extend the concentration range to include the half-maximal response."
            )

        # The previous ic50_range_warning used a midpoint derived from the
        # *fitted* top/bottom.  When the 4PL model must extrapolate heavily (e.g., data
        # spans only the top 15% of the curve), the fitted dynamic range can be enormous,
        # causing midpoint to fall inside the narrow observed response window even though
        # the IC50 is effectively extrapolated.
        # Fix: additionally warn when the observed response range is less than 50% of the
        # fitted dynamic range — a direct indicator that the data does not adequately
        # bracket the IC50.
        resp_arr = np.array(responses, dtype=float)
        fitted_dynamic_range = abs(float(result["top"]) - float(result["bottom"]))
        observed_range = float(np.max(resp_arr)) - float(np.min(resp_arr))
        midpoint = (result["top"] + result["bottom"]) / 2.0
        midpoint_check = (
            float(np.min(resp_arr)) > midpoint or float(np.max(resp_arr)) < midpoint
        )
        narrow_coverage = (
            fitted_dynamic_range > 0 and observed_range < 0.5 * fitted_dynamic_range
        )
        if midpoint_check or narrow_coverage:
            data["ic50_range_warning"] = (
                "The response data may not adequately bracket the half-maximal response. "
                f"Observed response range ({observed_range:.4g}) covers "
                f"{round(100 * observed_range / fitted_dynamic_range, 1) if fitted_dynamic_range > 0 else 'N/A'}% "
                f"of the fitted dynamic range ({fitted_dynamic_range:.4g}). "
                "The IC50 is likely extrapolated outside the measured range and should "
                "be interpreted with caution. Extend the concentration range to include "
                "both the upper and lower plateaus of the dose-response curve."
            )

        return {"status": "success", "data": data}

    @staticmethod
    def _interpret_potency(fold_shift):
        """Return a human-readable potency comparison string."""
        # Use explicit `is None` check: `not fold_shift` conflates None and 0.0.
        if fold_shift is None:
            return "Cannot determine potency (IC50 computation failed)"
        # Guard against zero: fold_shift = IC50_B / IC50_A; EC50 bounds prevent
        # this in normal operation, but direct callers could pass 0.0, which would
        # cause ZeroDivisionError in the `1 / fold_shift` branch below.
        if fold_shift == 0.0:
            return "Cannot determine potency (IC50 is zero)"
        # Guard against NaN/inf: IEEE 754 NaN comparisons always return False, so
        # NaN would fall through to "Equal potency" — a misleading result.
        if not math.isfinite(fold_shift):
            return "Cannot determine potency (non-finite fold shift)"
        if fold_shift > 1:
            # IC50_B > IC50_A → A is fold_shift times more potent.
            # Guard near-unity: round(1.004, 2) = 1.0 via IEEE 754, which would
            # produce "Compound A is 1.0x more potent" — contradicting more_potent='A'.
            display = round(fold_shift, 2)
            if display <= 1.0:
                return f"Compound A marginally more potent than B (fold shift = {fold_shift:.4g})"
            return f"Compound A is {display}x more potent than B"
        if fold_shift < 1:
            # IC50_A > IC50_B → B is (1/fold_shift) times more potent.
            inv = 1 / fold_shift
            inv_display = round(inv, 2)
            if inv_display <= 1.0:
                return (
                    f"Compound B marginally more potent than A (fold shift = {inv:.4g})"
                )
            return f"Compound B is {inv_display}x more potent than A"
        return "Equal potency"

    def _compare_potency(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare IC50 fold-shift between two compounds."""
        conc_a = arguments.get("conc_a", [])
        resp_a = arguments.get("resp_a", [])
        conc_b = arguments.get("conc_b", [])
        resp_b = arguments.get("resp_b", [])

        for name, vals in [
            ("conc_a", conc_a),
            ("resp_a", resp_a),
            ("conc_b", conc_b),
            ("resp_b", resp_b),
        ]:
            if not vals:
                return {"status": "error", "error": f"{name} is required"}

        result_a = self._fit_4pl(conc_a, resp_a)
        result_b = self._fit_4pl(conc_b, resp_b)

        if "error" in result_a:
            return {
                "status": "error",
                "error": f"Compound A fitting failed: {result_a['error']}",
            }
        if "error" in result_b:
            return {
                "status": "error",
                "error": f"Compound B fitting failed: {result_b['error']}",
            }

        ic50_a = result_a["ic50"]
        ic50_b = result_b["ic50"]

        fold_shift = ic50_b / ic50_a if ic50_a > 0 else None

        # Preserve full float precision for fold_shift: round(1e-5, 2) = 0.0, which
        # would be inconsistent with potency_interpretation reporting "100000x more
        # potent". Both fields must use the same underlying value to avoid contradictions.
        fold_shift_out = float(fold_shift) if fold_shift is not None else None

        # Warn when either compound's fit is poor (R² < 0.8): the IC50 and
        # fold-shift derived from a poorly-fitted curve are unreliable.
        poor_fit_warnings = []
        rsq_a = result_a["r_squared"]
        rsq_b = result_b["r_squared"]
        if rsq_a < 0.8:
            poor_fit_warnings.append(
                f"Compound A R² = {round(rsq_a, 4)} (< 0.8): poor curve fit. "
                "The IC50 estimate for compound A is unreliable."
            )
        if rsq_b < 0.8:
            poor_fit_warnings.append(
                f"Compound B R² = {round(rsq_b, 4)} (< 0.8): poor curve fit. "
                "The IC50 estimate for compound B is unreliable."
            )

        # Apply the same emax correction here.
        # result_a["top"] is the high-concentration asymptote (floor ≈0% for inhibitory);
        # emax should be the numerically LARGER asymptote = max(top, bottom).
        data = {
            "compound_a": {
                "ic50": ic50_a,
                "hill_slope": result_a["hill_slope"],
                "emax": max(result_a["top"], result_a["bottom"]),
                "r_squared": rsq_a,
            },
            "compound_b": {
                "ic50": ic50_b,
                "hill_slope": result_b["hill_slope"],
                "emax": max(result_b["top"], result_b["bottom"]),
                "r_squared": rsq_b,
            },
            "ic50_fold_shift_b_over_a": fold_shift_out,
            "more_potent": "A"
            if ic50_a < ic50_b
            else ("B" if ic50_b < ic50_a else "Equal"),
            "potency_interpretation": self._interpret_potency(fold_shift),
        }
        if poor_fit_warnings:
            data["poor_fit_warning"] = " | ".join(poor_fit_warnings)
        # Forward stimulatory_curve_warning and hill_slope_warning from
        # each compound's _fit_4pl result.  Without this, comparing an inhibitory
        # compound A against a stimulatory compound B (whose "IC50" is actually an EC50)
        # would silently report a fold-shift and "more potent" interpretation with no
        # indication that the comparison is scientifically invalid.  Hill slope warnings
        # are forwarded for the same reason: a clamped Hill slope affects IC50 reliability.
        for label, res in (("compound_a", result_a), ("compound_b", result_b)):
            if "stimulatory_curve_warning" in res:
                data[f"{label}_stimulatory_warning"] = res["stimulatory_curve_warning"]
            if "hill_slope_warning" in res:
                data[f"{label}_hill_slope_warning"] = res["hill_slope_warning"]
        return {"status": "success", "data": data}
