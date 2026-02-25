"""
Dose-Response Analysis Tool

Implements 4-Parameter Logistic (4PL) curve fitting for dose-response analysis.
Calculates IC50, Hill slope, Emax, Emin, and curve fitting statistics.

No external API calls. Uses scipy.optimize for curve fitting.
"""

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

        if np.any(x <= 0):
            return {"error": "All concentrations must be positive (> 0)"}

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

            # Coefficient of determination: R² = 1 - SSE/SST
            y_hat = _hill_equation(x, *popt)
            y_mean = float(np.mean(y))
            sse_resid = float(np.sum((y - y_hat) ** 2))
            sse_total = float(np.sum((y - y_mean) ** 2))
            r_sq = (1.0 - sse_resid / sse_total) if sse_total > 1e-15 else 0.0

            # Parameter standard errors from diagonal of covariance matrix
            perr = np.sqrt(np.diag(np.abs(pcov)))
            ci_ec50 = (ec50 - 2.0 * perr[2], ec50 + 2.0 * perr[2])

            return {
                "bottom": round(float(emin), 4),
                "top": round(float(emax), 4),
                "ic50": round(float(ec50), 6),
                "hill_slope": round(float(n_hill), 4),
                "r_squared": round(float(r_sq), 4),
                "ic50_95ci": [round(float(ci_ec50[0]), 6), round(float(ci_ec50[1]), 6)],
                "standard_errors": {
                    "bottom": round(float(perr[0]), 4),
                    "top": round(float(perr[1]), 4),
                    "ic50": round(float(perr[2]), 6),
                    "hill": round(float(perr[3]), 4),
                },
                "fitted_values": [round(float(v), 4) for v in y_hat],
            }
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

        return {
            "status": "success",
            "data": {
                "model": "4-Parameter Logistic (4PL)",
                "formula": "f(x) = Bottom + (Top - Bottom) / (1 + (IC50/x)^Hill)",
                "parameters": {
                    "bottom_emin": result["bottom"],
                    "top_emax": result["top"],
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
            },
        }

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

        return {
            "status": "success",
            "data": {
                "ic50": result["ic50"],
                "ic50_95_confidence_interval": result["ic50_95ci"],
                "hill_slope": result["hill_slope"],
                "emax": result["top"],
                "emin": result["bottom"],
                "r_squared": result["r_squared"],
                "log_ic50": round(float(np.log10(result["ic50"])), 4)
                if result["ic50"] > 0
                else None,
                "note": "IC50 estimated via 4PL curve fitting",
            },
        }

    @staticmethod
    def _interpret_potency(fold_shift):
        """Return a human-readable potency comparison string."""
        if not fold_shift:
            return "Equal potency"
        if fold_shift > 1:
            return f"Compound A is {round(1 / fold_shift, 2)}x more potent than B"
        if fold_shift < 1:
            return f"Compound B is {round(fold_shift, 2)}x more potent than A"
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

        return {
            "status": "success",
            "data": {
                "compound_a": {
                    "ic50": ic50_a,
                    "hill_slope": result_a["hill_slope"],
                    "emax": result_a["top"],
                    "r_squared": result_a["r_squared"],
                },
                "compound_b": {
                    "ic50": ic50_b,
                    "hill_slope": result_b["hill_slope"],
                    "emax": result_b["top"],
                    "r_squared": result_b["r_squared"],
                },
                "ic50_fold_shift_b_over_a": round(float(fold_shift), 2)
                if fold_shift
                else None,
                "more_potent": "A" if ic50_a < ic50_b else "B",
                "potency_interpretation": self._interpret_potency(fold_shift),
            },
        }
