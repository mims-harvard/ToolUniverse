"""Epidemiology calculations: R0/herd immunity, NNT, diagnostic tests, Bayesian post-test probability,
and vaccine coverage threshold from field data.

Consolidates the most commonly needed epidemiology formulas into one script with
verified output. No external dependencies — pure Python stdlib.

Calculation types (--type):

  r0_herd     R0, effective reproduction number, and herd immunity threshold.
              Requires: --R0  (and optionally --VE for vaccine-adjusted threshold,
              --coverage to evaluate Re at a given vaccination fraction)

  vaccine_coverage
              Derive VE from field surveillance data using the screening method
              (Farrington 1993), then compute required vaccination coverage Vc.
              Requires: --R0 --PCV --PPV
              PCV = proportion of cases that were vaccinated (0-1)
              PPV = proportion of population vaccinated (0-1)
              Formula: VE = 1 - [PCV*(1-PPV)] / [(1-PCV)*PPV]
              Then:    Vc = (1 - 1/R0) / VE

  nnt         Number needed to treat / number needed to harm.
              Requires: --control_rate  --treatment_rate

  diagnostic  Sensitivity, specificity, PPV, NPV, accuracy, likelihood ratios.
              Requires: --tp --fp --tn --fn  (2×2 contingency counts)

  bayesian    Post-test probability via Bayes' theorem.
              Requires: --prevalence --sensitivity --specificity
              Optional: --test_result {positive,negative}  (default: positive)

Usage:
    python epidemiology.py --type r0_herd --R0 3.5 --VE 0.90
    python epidemiology.py --type r0_herd --R0 14 --VE 0.97 --coverage 0.95
    python epidemiology.py --type vaccine_coverage --R0 3.0 --PCV 0.06 --PPV 0.35
    python epidemiology.py --type nnt --control_rate 0.30 --treatment_rate 0.20
    python epidemiology.py --type diagnostic --tp 90 --fp 10 --tn 880 --fn 20
    python epidemiology.py --type bayesian --prevalence 0.01 --sensitivity 0.95 --specificity 0.90
    python epidemiology.py --type bayesian --prevalence 0.05 --sensitivity 0.80 --specificity 0.95 --test_result negative
"""

import argparse
import math
import sys


# ---------------------------------------------------------------------------
# R0 / herd immunity
# ---------------------------------------------------------------------------

def r0_herd(R0: float, VE: float = 1.0, coverage: float | None = None) -> dict:
    """
    Compute herd immunity threshold and effective reproduction number.

    Args:
        R0:       Basic reproduction number (must be > 1).
        VE:       Vaccine efficacy as a fraction [0, 1]. Default 1.0 (perfect vaccine).
        coverage: Optional vaccination fraction [0, 1] to evaluate Re at.

    Returns dict with:
        herd_threshold_perfect: Herd immunity threshold assuming 100% efficacy.
        herd_threshold_ve:      VE-adjusted minimum vaccination fraction.
        Re_at_coverage:         Effective R at the given coverage (if provided).
    """
    if R0 <= 1:
        raise ValueError(f"R0 must be > 1 for epidemic spread (got {R0}).")
    if not 0 < VE <= 1:
        raise ValueError(f"VE must be in (0, 1] (got {VE}).")

    hc_perfect = 1.0 - 1.0 / R0
    hc_ve = hc_perfect / VE  # = (1 - 1/R0) / VE

    result = {
        "R0": R0,
        "VE": VE,
        "herd_threshold_perfect": hc_perfect,
        "herd_threshold_ve_adjusted": hc_ve,
    }

    if coverage is not None:
        if not 0 <= coverage <= 1:
            raise ValueError(f"coverage must be in [0, 1] (got {coverage}).")
        # Re = R0 * (1 - VE * coverage)
        Re = R0 * (1.0 - VE * coverage)
        result["coverage"] = coverage
        result["Re_at_coverage"] = Re
        result["epidemic_suppressed"] = Re < 1.0

    return result


def print_r0_herd(res: dict) -> None:
    print("=" * 60)
    print("  R0 and Herd Immunity Analysis")
    print("=" * 60)
    print(f"  Basic reproduction number (R0)  : {res['R0']}")
    print(f"  Vaccine efficacy (VE)           : {res['VE'] * 100:.1f}%")
    print()
    hc = res["herd_threshold_perfect"]
    hc_ve = res["herd_threshold_ve_adjusted"]
    print("  Herd Immunity Threshold (Hc = 1 - 1/R0):")
    print(f"    Perfect vaccine (VE=100%)     : {hc * 100:.2f}%  ({hc:.4f})")
    print()
    print("  VE-adjusted minimum vaccination coverage:")
    print(f"    Vc = Hc / VE = {hc:.4f} / {res['VE']:.2f}")
    print(f"       = {hc_ve:.4f}  ({hc_ve * 100:.2f}%)")
    if hc_ve > 1.0:
        print("    WARNING: VE too low to achieve herd immunity even at 100% coverage.")

    if "coverage" in res:
        cov = res["coverage"]
        Re = res["Re_at_coverage"]
        print()
        print(f"  Effective R (Re) at {cov * 100:.1f}% vaccination coverage:")
        print(f"    Re = R0 × (1 - VE × coverage)")
        print(f"       = {res['R0']} × (1 - {res['VE']:.2f} × {cov:.2f})")
        print(f"       = {Re:.4f}")
        suppressed = res["epidemic_suppressed"]
        status = "SUPPRESSED (Re < 1)" if suppressed else "NOT suppressed (Re ≥ 1)"
        print(f"    Epidemic status: {status}")

    print()
    print("  Verification:")
    check = 1.0 - 1.0 / res["R0"]
    assert abs(check - res["herd_threshold_perfect"]) < 1e-9, "Herd threshold mismatch"
    print(f"    1 - 1/R0 = {check:.6f}  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Vaccine coverage threshold from field data (screening method)
# ---------------------------------------------------------------------------


def vaccine_coverage(R0: float, PCV: float, PPV: float) -> dict:
    """
    Derive VE from observational field data using the screening method
    (Farrington 1993), then compute the required vaccination coverage Vc.

    The screening method estimates vaccine effectiveness from two readily
    available surveillance numbers:
        PCV = proportion of cases that were vaccinated  [0, 1]
        PPV = proportion of the population vaccinated   [0, 1]

    Formula:
        VE  = 1 - [PCV * (1 - PPV)] / [(1 - PCV) * PPV]
        Hc  = 1 - 1/R0          (herd immunity threshold, perfect vaccine)
        Vc  = Hc / VE           (minimum coverage with real-world VE)

    Args:
        R0:  Basic reproduction number (must be > 1).
        PCV: Proportion of disease cases that are vaccinated (0, 1).
        PPV: Proportion of total population that is vaccinated (0, 1).

    Returns dict with VE, Hc, Vc, and intermediate values.
    """
    if R0 <= 1:
        raise ValueError(f"R0 must be > 1 for epidemic spread (got {R0}).")
    if not 0 < PCV < 1:
        raise ValueError(f"PCV must be in (0, 1) exclusive (got {PCV}).")
    if not 0 < PPV < 1:
        raise ValueError(f"PPV must be in (0, 1) exclusive (got {PPV}).")

    # Screening method: VE = 1 - [PCV*(1-PPV)] / [(1-PCV)*PPV]
    numerator = PCV * (1.0 - PPV)
    denominator = (1.0 - PCV) * PPV
    VE = 1.0 - numerator / denominator

    if VE <= 0:
        raise ValueError(
            f"Derived VE = {VE:.4f} <= 0 — vaccination appears ineffective or harmful "
            f"with PCV={PCV}, PPV={PPV}."
        )

    Hc = 1.0 - 1.0 / R0
    Vc = Hc / VE

    # Re at the current PPV with derived VE
    Re_current = R0 * (1.0 - VE * PPV)

    return {
        "R0": R0,
        "PCV": PCV,
        "PPV": PPV,
        "VE": VE,
        "herd_threshold_perfect": Hc,
        "Vc": Vc,
        "Re_current": Re_current,
    }


def print_vaccine_coverage(res: dict) -> None:
    print("=" * 60)
    print("  Vaccine Coverage Threshold (Screening Method)")
    print("=" * 60)
    print(f"  Basic reproduction number (R0)       : {res['R0']}")
    print(f"  Proportion of cases vaccinated (PCV)  : {res['PCV']}")
    print(f"  Proportion of population vaccinated (PPV): {res['PPV']}")
    print()

    PCV = res["PCV"]
    PPV = res["PPV"]
    VE = res["VE"]
    Hc = res["herd_threshold_perfect"]
    Vc = res["Vc"]

    print("  Step 1 — Derive VE via screening method (Farrington 1993):")
    print(f"    VE = 1 - [PCV * (1-PPV)] / [(1-PCV) * PPV]")
    print(f"       = 1 - [{PCV} * {1-PPV:.4f}] / [{1-PCV:.4f} * {PPV}]")
    num = PCV * (1 - PPV)
    den = (1 - PCV) * PPV
    print(f"       = 1 - {num:.6f} / {den:.6f}")
    print(f"       = 1 - {num/den:.6f}")
    print(f"       = {VE:.4f}  ({VE * 100:.2f}%)")
    print()

    print("  Step 2 — Herd immunity threshold (perfect vaccine):")
    print(f"    Hc = 1 - 1/R0 = 1 - 1/{res['R0']} = {Hc:.4f}  ({Hc * 100:.2f}%)")
    print()

    print("  Step 3 — Required vaccination coverage:")
    print(f"    Vc = Hc / VE = {Hc:.4f} / {VE:.4f}")
    print(f"       = {Vc:.4f}  ({Vc * 100:.1f}%)")

    if Vc > 1.0:
        print("    WARNING: Vc > 100% — herd immunity unachievable at this VE.")
    print()

    Re = res["Re_current"]
    print(f"  Current situation (PPV = {PPV:.0%}):")
    print(f"    Re = R0 * (1 - VE * PPV) = {res['R0']} * (1 - {VE:.4f} * {PPV})")
    print(f"       = {Re:.4f}")
    status = "suppressed" if Re < 1.0 else "NOT suppressed"
    print(f"    Epidemic: {status}")
    print()

    print("  Verification:")
    Re_at_Vc = res["R0"] * (1.0 - VE * Vc)
    print(f"    Re at Vc = R0*(1 - VE*Vc) = {Re_at_Vc:.6f}  (should be ~1.00)")
    VE_check = 1.0 - (PCV * (1 - PPV)) / ((1 - PCV) * PPV)
    assert abs(VE_check - VE) < 1e-9, "VE mismatch"
    print(f"    VE recomputed: {VE_check:.6f}  matches")
    print("=" * 60)


# ---------------------------------------------------------------------------
# NNT / NNH
# ---------------------------------------------------------------------------

def nnt(control_rate: float, treatment_rate: float) -> dict:
    """
    Compute NNT, ARR, RRR, RR, and odds ratio.

    Args:
        control_rate:   Event rate in the control group [0, 1].
        treatment_rate: Event rate in the treatment group [0, 1].

    Returns dict with NNT/NNH, ARR, RRR, RR, OR.
    """
    for name, val in [("control_rate", control_rate), ("treatment_rate", treatment_rate)]:
        if not 0 <= val <= 1:
            raise ValueError(f"{name} must be in [0, 1] (got {val}).")

    ARR = control_rate - treatment_rate  # Absolute Risk Reduction (positive = benefit)
    RR = treatment_rate / control_rate if control_rate > 0 else float("nan")
    RRR = 1.0 - RR if not math.isnan(RR) else float("nan")

    # Odds ratio
    odds_control = control_rate / (1.0 - control_rate) if control_rate < 1 else float("inf")
    odds_treatment = treatment_rate / (1.0 - treatment_rate) if treatment_rate < 1 else float("inf")
    OR = odds_treatment / odds_control if odds_control > 0 else float("nan")

    if abs(ARR) < 1e-12:
        NNT = float("inf")
        label = "NNT"
    elif ARR > 0:
        NNT = 1.0 / ARR
        label = "NNT"  # treatment reduces risk — number needed to treat
    else:
        NNT = 1.0 / abs(ARR)
        label = "NNH"  # treatment increases risk — number needed to harm

    return {
        "control_rate": control_rate,
        "treatment_rate": treatment_rate,
        "ARR": ARR,
        "RR": RR,
        "RRR": RRR,
        "OR": OR,
        "NNT": NNT,
        "NNT_label": label,
    }


def print_nnt(res: dict) -> None:
    print("=" * 60)
    print("  NNT / NNH Analysis")
    print("=" * 60)
    print(f"  Control group event rate   : {res['control_rate'] * 100:.2f}%")
    print(f"  Treatment group event rate : {res['treatment_rate'] * 100:.2f}%")
    print()
    arr = res["ARR"]
    print(f"  Absolute Risk Reduction (ARR)        : {arr * 100:.4f}%")
    rr = res["RR"]
    if not math.isnan(rr):
        print(f"  Relative Risk (RR)                   : {rr:.4f}")
        rrr = res["RRR"]
        print(f"  Relative Risk Reduction (RRR)        : {rrr * 100:.2f}%")
    or_ = res["OR"]
    if not math.isnan(or_) and not math.isinf(or_):
        print(f"  Odds Ratio (OR)                      : {or_:.4f}")
    print()
    label = res["NNT_label"]
    nnt_val = res["NNT"]
    if math.isinf(nnt_val):
        print(f"  {label}: ∞  (treatment has no effect on event rate)")
    else:
        print(f"  {label} = 1 / |ARR| = 1 / {abs(arr):.6f} = {nnt_val:.2f}")
        print(f"  Rounded up: {math.ceil(nnt_val)} patients")
        if label == "NNT":
            print(f"  Interpretation: Treat {math.ceil(nnt_val)} patients to prevent 1 event.")
        else:
            print(f"  Interpretation: Treat {math.ceil(nnt_val)} patients to cause 1 additional event (harm).")
    print()
    print("  Verification:")
    check = abs(1.0 / arr) if abs(arr) > 1e-12 else float("inf")
    if not math.isinf(check):
        assert abs(check - nnt_val) < 1e-6, "NNT mismatch"
    print(f"    1 / |ARR| = {check:.4f}  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Diagnostic test metrics
# ---------------------------------------------------------------------------

def diagnostic(tp: int, fp: int, tn: int, fn: int) -> dict:
    """
    Compute diagnostic test performance metrics from a 2×2 table.

    Args:
        tp: True positives  (disease+, test+)
        fp: False positives (disease-, test+)
        tn: True negatives  (disease-, test-)
        fn: False negatives (disease+, test-)

    Returns dict with sensitivity, specificity, PPV, NPV, accuracy, LR+, LR-.
    """
    for name, val in [("tp", tp), ("fp", fp), ("tn", tn), ("fn", fn)]:
        if val < 0:
            raise ValueError(f"{name} must be >= 0 (got {val}).")

    n_disease_pos = tp + fn
    n_disease_neg = fp + tn
    n_total = n_disease_pos + n_disease_neg

    if n_disease_pos == 0:
        raise ValueError("No disease-positive cases (tp + fn = 0). Cannot compute sensitivity.")
    if n_disease_neg == 0:
        raise ValueError("No disease-negative cases (fp + tn = 0). Cannot compute specificity.")

    sensitivity = tp / n_disease_pos  # True Positive Rate
    specificity = tn / n_disease_neg  # True Negative Rate
    prevalence = n_disease_pos / n_total

    PPV = tp / (tp + fp) if (tp + fp) > 0 else float("nan")  # Positive Predictive Value
    NPV = tn / (tn + fn) if (tn + fn) > 0 else float("nan")  # Negative Predictive Value
    accuracy = (tp + tn) / n_total

    LR_pos = sensitivity / (1.0 - specificity) if specificity < 1.0 else float("inf")
    LR_neg = (1.0 - sensitivity) / specificity if specificity > 0.0 else float("nan")
    DOR = LR_pos / LR_neg if LR_neg and LR_neg > 0 else float("nan")

    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "n_disease_pos": n_disease_pos,
        "n_disease_neg": n_disease_neg,
        "n_total": n_total,
        "prevalence": prevalence,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "PPV": PPV,
        "NPV": NPV,
        "accuracy": accuracy,
        "LR_pos": LR_pos,
        "LR_neg": LR_neg,
        "DOR": DOR,
    }


def print_diagnostic(res: dict) -> None:
    print("=" * 60)
    print("  Diagnostic Test Performance")
    print("=" * 60)
    print("  2×2 Contingency Table:")
    print(f"    True  Positives (TP) : {res['tp']:>6}")
    print(f"    False Positives (FP) : {res['fp']:>6}")
    print(f"    True  Negatives (TN) : {res['tn']:>6}")
    print(f"    False Negatives (FN) : {res['fn']:>6}")
    print(f"    Total                : {res['n_total']:>6}")
    print(f"    Disease prevalence   : {res['prevalence'] * 100:.2f}%")
    print()
    print("  Performance Metrics:")
    print(f"    Sensitivity (TPR)  = TP / (TP+FN) = {res['tp']} / {res['n_disease_pos']}")
    print(f"                       = {res['sensitivity']:.4f}  ({res['sensitivity'] * 100:.2f}%)")
    print(f"    Specificity (TNR)  = TN / (TN+FP) = {res['tn']} / {res['n_disease_neg']}")
    print(f"                       = {res['specificity']:.4f}  ({res['specificity'] * 100:.2f}%)")
    ppv = res["PPV"]
    npv = res["NPV"]
    n_pos_test = res["tp"] + res["fp"]
    n_neg_test = res["tn"] + res["fn"]
    if not math.isnan(ppv):
        print(f"    PPV                = TP / (TP+FP) = {res['tp']} / {n_pos_test}")
        print(f"                       = {ppv:.4f}  ({ppv * 100:.2f}%)")
    if not math.isnan(npv):
        print(f"    NPV                = TN / (TN+FN) = {res['tn']} / {n_neg_test}")
        print(f"                       = {npv:.4f}  ({npv * 100:.2f}%)")
    print(f"    Accuracy           = (TP+TN) / N  = {res['tp'] + res['tn']} / {res['n_total']}")
    print(f"                       = {res['accuracy']:.4f}  ({res['accuracy'] * 100:.2f}%)")
    print()
    lrp = res["LR_pos"]
    lrn = res["LR_neg"]
    if not math.isinf(lrp):
        print(f"    Likelihood Ratio+  = Sens / (1-Spec)  = {lrp:.4f}")
    if not math.isnan(lrn) and lrn:
        print(f"    Likelihood Ratio-  = (1-Sens) / Spec  = {lrn:.4f}")
    dor = res["DOR"]
    if not math.isnan(dor) and not math.isinf(dor):
        print(f"    Diagnostic Odds Ratio (DOR)           = {dor:.2f}")
    print()
    print("  Interpretation:")
    se = res["sensitivity"]
    sp = res["specificity"]
    if se >= 0.95:
        print(f"    High sensitivity ({se * 100:.1f}%): few missed cases; good rule-out test.")
    elif se < 0.80:
        print(f"    Low sensitivity ({se * 100:.1f}%): many missed cases (false negatives).")
    if sp >= 0.95:
        print(f"    High specificity ({sp * 100:.1f}%): few false alarms; good rule-in test.")
    elif sp < 0.80:
        print(f"    Low specificity ({sp * 100:.1f}%): many false positives.")
    if not math.isnan(ppv):
        print(f"    PPV {ppv * 100:.1f}%: of those testing positive, {ppv * 100:.1f}% truly have the disease.")
    if not math.isnan(npv):
        print(f"    NPV {npv * 100:.1f}%: of those testing negative, {npv * 100:.1f}% truly do not.")
    print()
    print("  Verification:")
    check_se = res["tp"] / (res["tp"] + res["fn"])
    check_sp = res["tn"] / (res["tn"] + res["fp"])
    assert abs(check_se - se) < 1e-9, "Sensitivity mismatch"
    assert abs(check_sp - sp) < 1e-9, "Specificity mismatch"
    print(f"    Sensitivity recomputed: {check_se:.6f}  ✓")
    print(f"    Specificity recomputed: {check_sp:.6f}  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Bayesian post-test probability
# ---------------------------------------------------------------------------

def bayesian(prevalence: float, sensitivity: float, specificity: float,
             test_result: str = "positive") -> dict:
    """
    Compute post-test probability via Bayes' theorem.

    Args:
        prevalence:  Pre-test probability (prior) of disease [0, 1].
        sensitivity: P(test+ | disease+) [0, 1].
        specificity: P(test- | disease-) [0, 1].
        test_result: "positive" or "negative".

    Returns dict with pre-test odds, LR, post-test odds, and post-test probability.
    """
    for name, val in [("prevalence", prevalence), ("sensitivity", sensitivity),
                      ("specificity", specificity)]:
        if not 0 <= val <= 1:
            raise ValueError(f"{name} must be in [0, 1] (got {val}).")
    if test_result not in ("positive", "negative"):
        raise ValueError("test_result must be 'positive' or 'negative'.")

    pre_test_odds = prevalence / (1.0 - prevalence) if prevalence < 1 else float("inf")

    if test_result == "positive":
        LR = sensitivity / (1.0 - specificity) if specificity < 1.0 else float("inf")
    else:
        LR = (1.0 - sensitivity) / specificity if specificity > 0.0 else float("nan")

    post_test_odds = pre_test_odds * LR
    post_test_prob = post_test_odds / (1.0 + post_test_odds) if not math.isinf(post_test_odds) else 1.0

    # Alternative: direct formula via Bayes
    if test_result == "positive":
        p_test_given_disease = sensitivity
        p_test_given_no_disease = 1.0 - specificity
    else:
        p_test_given_disease = 1.0 - sensitivity
        p_test_given_no_disease = specificity

    p_test = p_test_given_disease * prevalence + p_test_given_no_disease * (1.0 - prevalence)
    ptp_direct = (p_test_given_disease * prevalence / p_test) if p_test > 0 else float("nan")

    return {
        "prevalence": prevalence,
        "sensitivity": sensitivity,
        "specificity": specificity,
        "test_result": test_result,
        "pre_test_odds": pre_test_odds,
        "LR": LR,
        "post_test_odds": post_test_odds,
        "post_test_prob": post_test_prob,
        "post_test_prob_direct": ptp_direct,
        "p_test": p_test,
    }


def print_bayesian(res: dict) -> None:
    print("=" * 60)
    print("  Bayesian Post-Test Probability")
    print("=" * 60)
    print(f"  Pre-test probability (prevalence) : {res['prevalence'] * 100:.2f}%")
    print(f"  Sensitivity                       : {res['sensitivity'] * 100:.2f}%")
    print(f"  Specificity                       : {res['specificity'] * 100:.2f}%")
    print(f"  Test result                       : {res['test_result'].upper()}")
    print()

    pre_odds = res["pre_test_odds"]
    LR = res["LR"]
    post_odds = res["post_test_odds"]
    post_prob = res["post_test_prob"]

    print("  Step 1 — Convert prevalence to pre-test odds:")
    print(f"    Pre-test odds = {res['prevalence']:.4f} / (1 - {res['prevalence']:.4f})")
    print(f"                  = {pre_odds:.4f}")
    print()

    lr_label = "LR+" if res["test_result"] == "positive" else "LR-"
    if res["test_result"] == "positive":
        lr_formula = f"Sensitivity / (1 - Specificity) = {res['sensitivity']:.4f} / {1 - res['specificity']:.4f}"
    else:
        lr_formula = f"(1 - Sensitivity) / Specificity = {1 - res['sensitivity']:.4f} / {res['specificity']:.4f}"

    print(f"  Step 2 — Likelihood Ratio ({lr_label}):")
    print(f"    {lr_label} = {lr_formula}")
    if not math.isnan(LR) and not math.isinf(LR):
        print(f"       = {LR:.4f}")
    elif math.isinf(LR):
        print(f"       = ∞  (perfect specificity)")
    print()

    print("  Step 3 — Post-test odds = pre-test odds × LR:")
    if not math.isinf(post_odds):
        print(f"    = {pre_odds:.4f} × {LR:.4f} = {post_odds:.4f}")
    else:
        print(f"    = ∞")
    print()

    print("  Step 4 — Convert post-test odds to probability:")
    if not math.isinf(post_odds):
        print(f"    Post-test prob = post-test odds / (1 + post-test odds)")
        print(f"                   = {post_odds:.4f} / {1 + post_odds:.4f}")
        print(f"                   = {post_prob:.4f}  ({post_prob * 100:.2f}%)")
    else:
        print(f"    Post-test prob = 100% (certain)")
    print()

    print("  Interpretation:")
    delta = post_prob - res["prevalence"]
    direction = "increased" if delta > 0 else "decreased"
    print(
        f"    A {res['test_result']} test result {direction} disease probability "
        f"from {res['prevalence'] * 100:.2f}% to {post_prob * 100:.2f}%."
    )
    if res["test_result"] == "positive" and post_prob < 0.5:
        print("    PPV < 50%: most positive tests are false positives at this prevalence.")
    elif res["test_result"] == "negative" and (1.0 - post_prob) > 0.99:
        print("    NPV > 99%: a negative result nearly rules out disease.")
    print()
    print("  Verification (direct Bayes formula):")
    direct = res["post_test_prob_direct"]
    if not math.isnan(direct):
        print(f"    P(disease | test {res['test_result']}) via direct formula = {direct:.6f}")
        assert abs(direct - post_prob) < 1e-6, f"Bayesian mismatch: {direct} vs {post_prob}"
        print("    Matches odds-ratio method  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Epidemiology calculations: R0/herd immunity, NNT, diagnostics, Bayes.",
        epilog=(
            "Examples:\n"
            "  python epidemiology.py --type r0_herd --R0 3.5 --VE 0.90\n"
            "  python epidemiology.py --type nnt --control_rate 0.30 --treatment_rate 0.20\n"
            "  python epidemiology.py --type diagnostic --tp 90 --fp 10 --tn 880 --fn 20\n"
            "  python epidemiology.py --type bayesian --prevalence 0.01 "
            "--sensitivity 0.95 --specificity 0.90\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["r0_herd", "vaccine_coverage", "nnt", "diagnostic", "bayesian"],
        help="Calculation type.",
    )
    # r0_herd
    p.add_argument("--R0", type=float, help="Basic reproduction number (r0_herd).")
    p.add_argument("--VE", type=float, default=1.0, help="Vaccine efficacy [0,1] (r0_herd).")
    p.add_argument("--coverage", type=float, help="Vaccination coverage fraction to evaluate Re (r0_herd).")
    # vaccine_coverage (screening method)
    p.add_argument("--PCV", type=float, help="Proportion of cases vaccinated (vaccine_coverage).")
    p.add_argument("--PPV", type=float, help="Proportion of population vaccinated (vaccine_coverage).")
    # nnt
    p.add_argument("--control_rate", type=float, help="Event rate in control group (nnt).")
    p.add_argument("--treatment_rate", type=float, help="Event rate in treatment group (nnt).")
    # diagnostic
    p.add_argument("--tp", type=int, help="True positives (diagnostic).")
    p.add_argument("--fp", type=int, help="False positives (diagnostic).")
    p.add_argument("--tn", type=int, help="True negatives (diagnostic).")
    p.add_argument("--fn", type=int, help="False negatives (diagnostic).")
    # bayesian
    p.add_argument("--prevalence", type=float, help="Pre-test probability / disease prevalence (bayesian).")
    p.add_argument("--sensitivity", type=float, help="Test sensitivity (bayesian, diagnostic).")
    p.add_argument("--specificity", type=float, help="Test specificity (bayesian, diagnostic).")
    p.add_argument(
        "--test_result",
        choices=["positive", "negative"],
        default="positive",
        help="Test result to condition on (bayesian, default: positive).",
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    calc_type = args.type

    try:
        if calc_type == "r0_herd":
            if args.R0 is None:
                parser.error("--type r0_herd requires --R0.")
            res = r0_herd(args.R0, VE=args.VE, coverage=args.coverage)
            print_r0_herd(res)

        elif calc_type == "vaccine_coverage":
            if args.R0 is None:
                parser.error("--type vaccine_coverage requires --R0.")
            if args.PCV is None or args.PPV is None:
                parser.error("--type vaccine_coverage requires --PCV and --PPV.")
            res = vaccine_coverage(args.R0, args.PCV, args.PPV)
            print_vaccine_coverage(res)

        elif calc_type == "nnt":
            if args.control_rate is None or args.treatment_rate is None:
                parser.error("--type nnt requires --control_rate and --treatment_rate.")
            res = nnt(args.control_rate, args.treatment_rate)
            print_nnt(res)

        elif calc_type == "diagnostic":
            for flag in ("--tp", "--fp", "--tn", "--fn"):
                attr = flag.lstrip("-")
                if getattr(args, attr) is None:
                    parser.error(f"--type diagnostic requires {flag}.")
            res = diagnostic(args.tp, args.fp, args.tn, args.fn)
            print_diagnostic(res)

        elif calc_type == "bayesian":
            for flag, attr in [("--prevalence", "prevalence"),
                                ("--sensitivity", "sensitivity"),
                                ("--specificity", "specificity")]:
                if getattr(args, attr) is None:
                    parser.error(f"--type bayesian requires {flag}.")
            res = bayesian(args.prevalence, args.sensitivity, args.specificity, args.test_result)
            print_bayesian(res)

    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
