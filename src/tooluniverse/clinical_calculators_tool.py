"""
Validated clinical risk calculators for ToolUniverse.

Pure-compute, deterministic implementations of standard validated clinical
scores (no network, no API key). Each calculator is selected by
``fields.calculator`` and returns the score, a risk interpretation, and the
component breakdown so the result is auditable.

These encode published, widely-used formulas (citations in each handler). They
are decision-support calculators for research/education, not a substitute for
clinical judgement.
"""

import math
from typing import Dict, Any, Callable

from .base_tool import BaseTool
from .tool_registry import register_tool


def _truthy(v: Any) -> bool:
    """Interpret a boolean-ish argument (True/'yes'/1) as a clinical 'present'."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ("true", "yes", "y", "1", "present", "positive")


def _req_number(args: Dict[str, Any], key: str) -> float:
    val = args.get(key)
    if val is None or val == "":
        raise ValueError(f"'{key}' is required")
    try:
        return float(val)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be a number, got {val!r}")


def _ok(score, interpretation, components, **extra) -> Dict[str, Any]:
    data = {"score": score, "interpretation": interpretation, "components": components}
    data.update(extra)
    return {
        "status": "success",
        "data": data,
        "metadata": {"calculator_type": "clinical_risk_score"},
    }


# --------------------------------------------------------------------------- #
# Point-based scores
# --------------------------------------------------------------------------- #
def _cha2ds2_vasc(a: Dict[str, Any]) -> Dict[str, Any]:
    """CHA2DS2-VASc stroke risk in atrial fibrillation (Lip 2010)."""
    age = _req_number(a, "age")
    comp = {
        "CHF": int(_truthy(a.get("chf"))),
        "Hypertension": int(_truthy(a.get("hypertension"))),
        # Age contributes either the >=75 (2) or 65-74 (1) bucket, never both.
        "Age>=75": 2 if age >= 75 else 0,
        "Diabetes": int(_truthy(a.get("diabetes"))),
        "Stroke/TIA/thromboembolism": 2 if _truthy(a.get("stroke_history")) else 0,
        "Vascular_disease": int(_truthy(a.get("vascular_disease"))),
        "Age_65-74": 1 if 65 <= age < 75 else 0,
        "Female": int(_truthy(a.get("female"))),
    }
    score = sum(comp.values())
    if score == 0:
        interp = "Low risk (0) — no anticoagulation generally needed"
    elif score == 1:
        interp = "Low-moderate risk (1) — consider anticoagulation"
    else:
        interp = f"Elevated risk ({score}) — oral anticoagulation recommended"
    return _ok(score, interp, comp, max_score=9)


def _has_bled(a: Dict[str, Any]) -> Dict[str, Any]:
    """HAS-BLED major bleeding risk on anticoagulation (Pisters 2010)."""
    comp = {
        "Hypertension_uncontrolled": int(_truthy(a.get("hypertension"))),
        "Abnormal_renal": int(_truthy(a.get("renal_disease"))),
        "Abnormal_liver": int(_truthy(a.get("liver_disease"))),
        "Stroke": int(_truthy(a.get("stroke_history"))),
        "Bleeding_history": int(_truthy(a.get("bleeding_history"))),
        "Labile_INR": int(_truthy(a.get("labile_inr"))),
        "Elderly_>65": 1 if _req_number(a, "age") > 65 else 0,
        "Drugs_antiplatelet_NSAID": int(_truthy(a.get("drugs"))),
        "Alcohol": int(_truthy(a.get("alcohol"))),
    }
    score = sum(comp.values())
    interp = (
        f"High bleeding risk ({score}) — caution, review reversible factors"
        if score >= 3
        else f"Lower bleeding risk ({score})"
    )
    return _ok(score, interp, comp, max_score=9)


def _curb_65(a: Dict[str, Any]) -> Dict[str, Any]:
    """CURB-65 community-acquired pneumonia severity (Lim 2003)."""
    comp = {
        "Confusion": int(_truthy(a.get("confusion"))),
        "Urea>7mmol/L": int(_truthy(a.get("elevated_urea"))),
        "RR>=30": int(_truthy(a.get("high_resp_rate"))),
        "Low_BP(SBP<90 or DBP<=60)": int(_truthy(a.get("low_bp"))),
        "Age>=65": 1 if _req_number(a, "age") >= 65 else 0,
    }
    score = sum(comp.values())
    if score <= 1:
        interp = f"Low severity ({score}) — consider outpatient treatment"
    elif score == 2:
        interp = "Moderate severity (2) — consider short inpatient/supervised treatment"
    else:
        interp = f"High severity ({score}) — hospitalize; assess for ICU if 4-5"
    return _ok(score, interp, comp, max_score=5)


def _qsofa(a: Dict[str, Any]) -> Dict[str, Any]:
    """qSOFA bedside sepsis risk (Singer 2016)."""
    comp = {
        "RR>=22": int(_truthy(a.get("high_resp_rate"))),
        "Altered_mentation": int(_truthy(a.get("altered_mentation"))),
        "SBP<=100": int(_truthy(a.get("low_sbp"))),
    }
    score = sum(comp.values())
    interp = (
        f"High risk ({score}>=2) — greater risk of poor outcome; assess for sepsis"
        if score >= 2
        else f"Lower risk ({score})"
    )
    return _ok(score, interp, comp, max_score=3)


def _child_pugh(a: Dict[str, Any]) -> Dict[str, Any]:
    """Child-Pugh cirrhosis severity (Pugh 1973)."""
    bili = _req_number(a, "bilirubin")  # mg/dL
    alb = _req_number(a, "albumin")  # g/dL
    inr = _req_number(a, "inr")
    ascites = str(a.get("ascites", "none")).strip().lower()
    enceph = str(a.get("encephalopathy", "none")).strip().lower()

    def _grade3(x, lo, hi):
        if x < lo:
            return 1
        if x <= hi:
            return 2
        return 3

    def _albumin_pts(alb):
        if alb > 3.5:
            return 1
        if alb >= 2.8:
            return 2
        return 3

    bili_pts = _grade3(bili, 2.0, 3.0)
    alb_pts = _albumin_pts(alb)
    inr_pts = _grade3(inr, 1.7, 2.3)
    ascites_map = {
        "none": 1,
        "absent": 1,
        "mild": 2,
        "slight": 2,
        "moderate": 3,
        "severe": 3,
    }
    enceph_map = {
        "none": 1,
        "absent": 1,
        "grade1-2": 2,
        "grade1": 2,
        "grade2": 2,
        "grade3-4": 3,
        "grade3": 3,
        "grade4": 3,
    }
    if ascites not in ascites_map:
        raise ValueError(
            f"'ascites' must be one of {sorted(ascites_map)}, got {ascites!r}"
        )
    if enceph not in enceph_map:
        raise ValueError(
            f"'encephalopathy' must be one of {sorted(enceph_map)}, got {enceph!r}"
        )
    ascites_pts = ascites_map[ascites]
    enceph_pts = enceph_map[enceph]

    comp = {
        "Bilirubin": bili_pts,
        "Albumin": alb_pts,
        "INR": inr_pts,
        "Ascites": ascites_pts,
        "Encephalopathy": enceph_pts,
    }
    score = sum(comp.values())
    if score <= 6:
        cls, cls_desc = "A", "well-compensated disease"
    elif score <= 9:
        cls, cls_desc = "B", "significant functional compromise"
    else:
        cls, cls_desc = "C", "decompensated disease"
    interp = f"Class {cls} (score {score}): {cls_desc}"
    return _ok(score, interp, comp, child_pugh_class=cls, max_score=15)


def _wells_dvt(a: Dict[str, Any]) -> Dict[str, Any]:
    """Wells score for DVT pretest probability (Wells 2003)."""
    comp = {
        "Active_cancer": int(_truthy(a.get("active_cancer"))),
        "Paralysis/immobilization": int(_truthy(a.get("immobilization"))),
        "Recently_bedridden/surgery": int(_truthy(a.get("recent_surgery"))),
        "Localized_tenderness": int(_truthy(a.get("localized_tenderness"))),
        "Entire_leg_swollen": int(_truthy(a.get("leg_swollen"))),
        "Calf_swelling>3cm": int(_truthy(a.get("calf_swelling"))),
        "Pitting_edema": int(_truthy(a.get("pitting_edema"))),
        "Collateral_superficial_veins": int(_truthy(a.get("collateral_veins"))),
        "Previous_DVT": int(_truthy(a.get("previous_dvt"))),
        "Alternative_dx_as_likely": -2
        if _truthy(a.get("alternative_diagnosis"))
        else 0,
    }
    score = sum(comp.values())
    interp = (
        f"DVT likely (score {score}>=2)"
        if score >= 2
        else f"DVT unlikely (score {score})"
    )
    return _ok(score, interp, comp)


def _wells_pe(a: Dict[str, Any]) -> Dict[str, Any]:
    """Wells score for PE pretest probability (Wells 2000)."""
    comp = {
        "Clinical_signs_DVT": 3.0 if _truthy(a.get("clinical_dvt")) else 0,
        "PE_most_likely_dx": 3.0 if _truthy(a.get("pe_most_likely")) else 0,
        "HR>100": 1.5 if _truthy(a.get("tachycardia")) else 0,
        "Immobilization/surgery": 1.5 if _truthy(a.get("immobilization")) else 0,
        "Previous_DVT/PE": 1.5 if _truthy(a.get("previous_vte")) else 0,
        "Hemoptysis": 1.0 if _truthy(a.get("hemoptysis")) else 0,
        "Malignancy": 1.0 if _truthy(a.get("malignancy")) else 0,
    }
    score = sum(comp.values())
    if score < 2:
        three_tier = "low"
    elif score <= 6:
        three_tier = "moderate"
    else:
        three_tier = "high"
    two_tier = "PE unlikely" if score <= 4 else "PE likely"
    interp = (
        f"{three_tier.capitalize()} probability (score {score}); two-tier: {two_tier}"
    )
    return _ok(score, interp, comp, three_tier=three_tier, two_tier=two_tier)


# --------------------------------------------------------------------------- #
# Continuous-formula scores
# --------------------------------------------------------------------------- #
def _meld_na(a: Dict[str, Any]) -> Dict[str, Any]:
    """MELD-Na for liver disease severity (UNOS/OPTN 2016)."""
    creat = _req_number(a, "creatinine")  # mg/dL
    bili = _req_number(a, "bilirubin")  # mg/dL
    inr = _req_number(a, "inr")
    na = _req_number(a, "sodium")  # mmol/L
    dialysis = _truthy(a.get("dialysis"))

    # Lower bounds of 1.0; creatinine capped at 4.0 (and set to 4.0 if dialysis).
    c = min(max(creat, 1.0), 4.0)
    if dialysis:
        c = 4.0
    b = max(bili, 1.0)
    i = max(inr, 1.0)

    meld = 0.957 * math.log(c) + 0.378 * math.log(b) + 1.120 * math.log(i) + 0.643
    meld = round(meld * 10)
    if meld > 11:
        na_b = min(max(na, 125.0), 137.0)
        meld = meld + 1.32 * (137 - na_b) - (0.033 * meld * (137 - na_b))
    score = int(min(round(meld), 40))
    if score <= 9:
        band = "low (~1.9% 90-day mortality)"
    elif score <= 19:
        band = "moderate"
    elif score <= 29:
        band = "high"
    else:
        band = "very high (>50% 90-day mortality at >=40)"
    comp = {
        "creatinine_used": c,
        "bilirubin_used": b,
        "inr_used": i,
        "sodium_used": na,
        "dialysis": dialysis,
    }
    return _ok(
        score, f"MELD-Na {score}: {band} 90-day mortality risk", comp, max_score=40
    )


def _ckd_epi(a: Dict[str, Any]) -> Dict[str, Any]:
    """eGFR by CKD-EPI 2021 creatinine equation, race-free (Inker 2021)."""
    scr = _req_number(a, "creatinine")  # mg/dL
    age = _req_number(a, "age")
    female = _truthy(a.get("female"))
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    egfr = (
        142
        * (min(scr / kappa, 1.0) ** alpha)
        * (max(scr / kappa, 1.0) ** -1.200)
        * (0.9938**age)
        * (1.012 if female else 1.0)
    )
    egfr = round(egfr, 1)
    if egfr >= 90:
        stage = "G1 (normal, >=90)"
    elif egfr >= 60:
        stage = "G2 (mild, 60-89)"
    elif egfr >= 45:
        stage = "G3a (mild-moderate, 45-59)"
    elif egfr >= 30:
        stage = "G3b (moderate-severe, 30-44)"
    elif egfr >= 15:
        stage = "G4 (severe, 15-29)"
    else:
        stage = "G5 (kidney failure, <15)"
    comp = {"creatinine_mg_dL": scr, "age": age, "sex": "female" if female else "male"}
    return _ok(
        egfr,
        f"eGFR {egfr} mL/min/1.73m^2 — CKD stage {stage}",
        comp,
        unit="mL/min/1.73m^2",
    )


# ASCVD 2013 Pooled Cohort Equations (Goff 2013). Coefficients per race/sex group;
# baseline survival S0 and group mean of the linear predictor.
_ASCVD_COEFF = {
    "white_female": {
        "ln_age": -29.799,
        "ln_age_sq": 4.884,
        "ln_tc": 13.540,
        "ln_age_tc": -3.114,
        "ln_hdl": -13.578,
        "ln_age_hdl": 3.149,
        "ln_sbp_treated": 2.019,
        "ln_sbp_untreated": 1.957,
        "smoker": 7.574,
        "ln_age_smoker": -1.665,
        "diabetes": 0.661,
        "s0": 0.9665,
        "mean": -29.18,
    },
    "white_male": {
        "ln_age": 12.344,
        "ln_tc": 11.853,
        "ln_age_tc": -2.664,
        "ln_hdl": -7.990,
        "ln_age_hdl": 1.769,
        "ln_sbp_treated": 1.797,
        "ln_sbp_untreated": 1.764,
        "smoker": 7.837,
        "ln_age_smoker": -1.795,
        "diabetes": 0.658,
        "s0": 0.9144,
        "mean": 61.18,
    },
    "black_female": {
        "ln_age": 17.114,
        "ln_tc": 0.940,
        "ln_hdl": -18.920,
        "ln_age_hdl": 4.475,
        "ln_sbp_treated": 29.291,
        "ln_age_sbp_treated": -6.432,
        "ln_sbp_untreated": 27.820,
        "ln_age_sbp_untreated": -6.087,
        "smoker": 0.691,
        "diabetes": 0.874,
        "s0": 0.9533,
        "mean": 86.61,
    },
    "black_male": {
        "ln_age": 2.469,
        "ln_tc": 0.302,
        "ln_hdl": -0.307,
        "ln_sbp_treated": 1.916,
        "ln_sbp_untreated": 1.809,
        "smoker": 0.549,
        "diabetes": 0.645,
        "s0": 0.8954,
        "mean": 19.54,
    },
}


def _ascvd(a: Dict[str, Any]) -> Dict[str, Any]:
    """10-year ASCVD risk by the 2013 ACC/AHA Pooled Cohort Equations (Goff 2013).

    Valid for age 40-79, non-Hispanic White or African American. Other
    race/ethnicities use the White coefficients (per the guideline)."""
    age = _req_number(a, "age")
    if not 40 <= age <= 79:
        return {
            "status": "error",
            "error": "ASCVD PCE is validated only for ages 40-79",
        }
    tc = _req_number(a, "total_cholesterol")  # mg/dL
    hdl = _req_number(a, "hdl_cholesterol")  # mg/dL
    sbp = _req_number(a, "systolic_bp")  # mmHg
    treated = _truthy(a.get("bp_treated"))
    smoker = _truthy(a.get("smoker"))
    diabetes = _truthy(a.get("diabetes"))
    female = _truthy(a.get("female"))
    black = str(a.get("race", "")).strip().lower() in (
        "black",
        "african american",
        "aa",
    )

    key = f"{'black' if black else 'white'}_{'female' if female else 'male'}"
    c = _ASCVD_COEFF[key]
    ln_age, ln_tc, ln_hdl, ln_sbp = (
        math.log(age),
        math.log(tc),
        math.log(hdl),
        math.log(sbp),
    )

    s = 0.0
    s += c["ln_age"] * ln_age
    s += c.get("ln_age_sq", 0) * ln_age * ln_age
    s += c["ln_tc"] * ln_tc + c.get("ln_age_tc", 0) * ln_age * ln_tc
    s += c["ln_hdl"] * ln_hdl + c.get("ln_age_hdl", 0) * ln_age * ln_hdl
    if treated:
        s += (
            c["ln_sbp_treated"] * ln_sbp
            + c.get("ln_age_sbp_treated", 0) * ln_age * ln_sbp
        )
    else:
        s += (
            c["ln_sbp_untreated"] * ln_sbp
            + c.get("ln_age_sbp_untreated", 0) * ln_age * ln_sbp
        )
    s += c["smoker"] * (1 if smoker else 0) + c.get("ln_age_smoker", 0) * ln_age * (
        1 if smoker else 0
    )
    s += c["diabetes"] * (1 if diabetes else 0)

    risk = (1 - c["s0"] ** math.exp(s - c["mean"])) * 100
    risk = round(risk, 1)
    if risk < 5:
        band = "low (<5%)"
    elif risk < 7.5:
        band = "borderline (5-7.4%)"
    elif risk < 20:
        band = "intermediate (7.5-19.9%)"
    else:
        band = "high (>=20%)"
    comp = {
        "group": key,
        "age": age,
        "total_cholesterol": tc,
        "hdl": hdl,
        "systolic_bp": sbp,
        "bp_treated": treated,
        "smoker": smoker,
        "diabetes": diabetes,
    }
    return _ok(risk, f"10-year ASCVD risk {risk}% — {band} risk", comp, unit="percent")


_DISPATCH: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "cha2ds2_vasc": _cha2ds2_vasc,
    "has_bled": _has_bled,
    "curb_65": _curb_65,
    "qsofa": _qsofa,
    "child_pugh": _child_pugh,
    "wells_dvt": _wells_dvt,
    "wells_pe": _wells_pe,
    "meld_na": _meld_na,
    "ckd_epi": _ckd_epi,
    "ascvd": _ascvd,
}


@register_tool("ClinicalCalculatorTool")
class ClinicalCalculatorTool(BaseTool):
    """Compute a validated clinical risk score selected by ``fields.calculator``."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.calculator = tool_config.get("fields", {}).get("calculator")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handler = _DISPATCH.get(self.calculator)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown calculator '{self.calculator}'. Available: {', '.join(sorted(_DISPATCH))}",
            }
        try:
            return handler(arguments or {})
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:  # noqa: BLE001 - tools must never raise
            return {
                "status": "error",
                "error": f"{self.calculator} calculation error: {str(e)}",
            }
