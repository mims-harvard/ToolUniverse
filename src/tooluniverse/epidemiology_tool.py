"""
Epidemiology Calculator Tool

R0/herd immunity, NNT/NNH, diagnostic test metrics, Bayesian post-test
probability, and vaccine coverage threshold (screening method).

No external API calls. Pure Python with stdlib math only.
"""

import math
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("EpidemiologyTool")
class EpidemiologyTool(BaseTool):
    """Epidemiology calculator: R0, NNT, diagnostic tests, Bayes, vaccine coverage."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "r0_herd": self._r0_herd,
            "vaccine_coverage": self._vaccine_coverage,
            "nnt": self._nnt,
            "diagnostic": self._diagnostic,
            "bayesian": self._bayesian,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Calculation failed: {str(e)}"}

    def _r0_herd(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        R0 = arguments.get("R0")
        VE = arguments.get("VE", 1.0)
        coverage = arguments.get("coverage")

        if R0 is None:
            return {"status": "error", "error": "Missing required parameter: R0"}
        if R0 <= 1:
            return {"status": "error", "error": f"R0 must be > 1 (got {R0})."}
        if not 0 < VE <= 1:
            return {"status": "error", "error": f"VE must be in (0, 1] (got {VE})."}

        hc_perfect = 1.0 - 1.0 / R0
        hc_ve = hc_perfect / VE

        data = {
            "R0": R0,
            "VE": VE,
            "herd_threshold_perfect": round(hc_perfect, 6),
            "herd_threshold_ve_adjusted": round(hc_ve, 6),
        }

        if coverage is not None:
            if not 0 <= coverage <= 1:
                return {
                    "status": "error",
                    "error": f"coverage must be in [0, 1] (got {coverage}).",
                }
            Re = R0 * (1.0 - VE * coverage)
            data["coverage"] = coverage
            data["Re_at_coverage"] = round(Re, 6)
            data["epidemic_suppressed"] = Re < 1.0

        return {"status": "success", "data": data}

    def _vaccine_coverage(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        R0 = arguments.get("R0")
        PCV = arguments.get("PCV")
        PPV = arguments.get("PPV")

        for name, val in [("R0", R0), ("PCV", PCV), ("PPV", PPV)]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }

        if R0 <= 1:
            return {"status": "error", "error": f"R0 must be > 1 (got {R0})."}
        if not 0 < PCV < 1:
            return {
                "status": "error",
                "error": f"PCV must be in (0, 1) exclusive (got {PCV}).",
            }
        if not 0 < PPV < 1:
            return {
                "status": "error",
                "error": f"PPV must be in (0, 1) exclusive (got {PPV}).",
            }

        numerator = PCV * (1.0 - PPV)
        denominator = (1.0 - PCV) * PPV
        VE = 1.0 - numerator / denominator

        if VE <= 0:
            return {
                "status": "error",
                "error": f"Derived VE = {VE:.4f} <= 0 with PCV={PCV}, PPV={PPV}.",
            }

        Hc = 1.0 - 1.0 / R0
        Vc = Hc / VE
        Re_current = R0 * (1.0 - VE * PPV)

        return {
            "status": "success",
            "data": {
                "R0": R0,
                "PCV": PCV,
                "PPV": PPV,
                "VE": round(VE, 6),
                "herd_threshold_perfect": round(Hc, 6),
                "Vc": round(Vc, 6),
                "Re_current": round(Re_current, 6),
                "Vc_achievable": Vc <= 1.0,
            },
        }

    def _nnt(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        control_rate = arguments.get("control_rate")
        treatment_rate = arguments.get("treatment_rate")

        for name, val in [
            ("control_rate", control_rate),
            ("treatment_rate", treatment_rate),
        ]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }
            if not 0 <= val <= 1:
                return {
                    "status": "error",
                    "error": f"{name} must be in [0, 1] (got {val}).",
                }

        ARR = control_rate - treatment_rate
        RR = treatment_rate / control_rate if control_rate > 0 else float("nan")
        RRR = 1.0 - RR if not math.isnan(RR) else float("nan")

        odds_c = (
            control_rate / (1.0 - control_rate) if control_rate < 1 else float("inf")
        )
        odds_t = (
            treatment_rate / (1.0 - treatment_rate)
            if treatment_rate < 1
            else float("inf")
        )
        OR = odds_t / odds_c if odds_c > 0 else float("nan")

        if abs(ARR) < 1e-12:
            NNT = None
            label = "NNT"
        elif ARR > 0:
            NNT = round(1.0 / ARR, 4)
            label = "NNT"
        else:
            NNT = round(1.0 / abs(ARR), 4)
            label = "NNH"

        data = {
            "control_rate": control_rate,
            "treatment_rate": treatment_rate,
            "ARR": round(ARR, 6),
            "RR": round(RR, 6) if not math.isnan(RR) else None,
            "RRR": round(RRR, 6) if not math.isnan(RRR) else None,
            "OR": round(OR, 6) if (not math.isnan(OR) and not math.isinf(OR)) else None,
            "NNT_value": NNT,
            "NNT_label": label,
        }

        return {"status": "success", "data": data}

    def _diagnostic(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tp = arguments.get("tp")
        fp = arguments.get("fp")
        tn = arguments.get("tn")
        fn = arguments.get("fn")

        for name, val in [("tp", tp), ("fp", fp), ("tn", tn), ("fn", fn)]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }
            if val < 0:
                return {"status": "error", "error": f"{name} must be >= 0 (got {val})."}

        n_pos = tp + fn
        n_neg = fp + tn
        n_total = n_pos + n_neg

        if n_pos == 0:
            return {
                "status": "error",
                "error": "No disease-positive cases (tp + fn = 0).",
            }
        if n_neg == 0:
            return {
                "status": "error",
                "error": "No disease-negative cases (fp + tn = 0).",
            }

        sensitivity = tp / n_pos
        specificity = tn / n_neg
        prevalence = n_pos / n_total
        PPV = tp / (tp + fp) if (tp + fp) > 0 else None
        NPV = tn / (tn + fn) if (tn + fn) > 0 else None
        accuracy = (tp + tn) / n_total
        LR_pos = sensitivity / (1.0 - specificity) if specificity < 1.0 else None
        LR_neg = (1.0 - sensitivity) / specificity if specificity > 0.0 else None

        return {
            "status": "success",
            "data": {
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "n_total": n_total,
                "prevalence": round(prevalence, 6),
                "sensitivity": round(sensitivity, 6),
                "specificity": round(specificity, 6),
                "PPV": round(PPV, 6) if PPV is not None else None,
                "NPV": round(NPV, 6) if NPV is not None else None,
                "accuracy": round(accuracy, 6),
                "LR_pos": round(LR_pos, 4) if LR_pos is not None else None,
                "LR_neg": round(LR_neg, 4) if LR_neg is not None else None,
            },
        }

    def _bayesian(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        prevalence = arguments.get("prevalence")
        sensitivity = arguments.get("sensitivity")
        specificity = arguments.get("specificity")
        test_result = arguments.get("test_result", "positive")

        for name, val in [
            ("prevalence", prevalence),
            ("sensitivity", sensitivity),
            ("specificity", specificity),
        ]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }
            if not 0 <= val <= 1:
                return {
                    "status": "error",
                    "error": f"{name} must be in [0, 1] (got {val}).",
                }

        if test_result not in ("positive", "negative"):
            return {
                "status": "error",
                "error": "test_result must be 'positive' or 'negative'.",
            }

        pre_test_odds = (
            prevalence / (1.0 - prevalence) if prevalence < 1 else float("inf")
        )

        if test_result == "positive":
            LR = (
                sensitivity / (1.0 - specificity) if specificity < 1.0 else float("inf")
            )
        else:
            LR = (
                (1.0 - sensitivity) / specificity if specificity > 0.0 else float("nan")
            )

        post_test_odds = pre_test_odds * LR
        if math.isinf(post_test_odds):
            post_test_prob = 1.0
        elif math.isnan(post_test_odds):
            post_test_prob = None
        else:
            post_test_prob = post_test_odds / (1.0 + post_test_odds)

        data = {
            "prevalence": prevalence,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "test_result": test_result,
            "pre_test_odds": round(pre_test_odds, 6)
            if not math.isinf(pre_test_odds)
            else None,
            "LR": round(LR, 6) if (not math.isinf(LR) and not math.isnan(LR)) else None,
            "post_test_probability": round(post_test_prob, 6)
            if post_test_prob is not None
            else None,
        }

        return {"status": "success", "data": data}
