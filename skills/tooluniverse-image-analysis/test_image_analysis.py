#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-image-analysis skill.

Tests all 21 BixBench imaging questions across 4 projects:
- bix-18: Colony morphometry (5 questions)
- bix-19: NeuN cell counting statistics (5 questions)
- bix-41: Co-culture Dunnett's analysis (4 questions)
- bix-54: Regression modeling (7 questions)
"""

import os
import sys
import traceback
import requests
import zipfile
import io

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.power import TTestIndPower

# ---------------------------------------------------------------------------
# Data download helpers
# ---------------------------------------------------------------------------

DATA_DIR = "/tmp/bixbench_image_data"
BASE_URL = "https://huggingface.co/datasets/futurehouse/BixBench/resolve/main/"

CAPSULES = {
    "bix-18": "d59734d2-a3e0-462a-a5fd-c8ddc11392b8",
    "bix-19": "8c64b1fa-fdcc-41e2-be8d-2f0c8d5faaa1",
    "bix-41": "8b462015-86ab-434f-29e1-04dda1588031",
    "bix-54": "9e52daf6-ca58-43e8-e732-fbac3459d295",
}


def download_capsule(bix_id):
    """Download and extract a BixBench data capsule if not already present."""
    uuid = CAPSULES[bix_id]
    extract_dir = os.path.join(DATA_DIR, bix_id)
    if os.path.exists(extract_dir) and os.listdir(extract_dir):
        return extract_dir
    os.makedirs(extract_dir, exist_ok=True)
    zip_name = f"CapsuleFolder-{uuid}.zip"
    url = BASE_URL + zip_name
    r = requests.get(url)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    z.extractall(extract_dir)
    return extract_dir


def get_data_csv(bix_id):
    """Find and load the CSV data file for a BixBench project."""
    extract_dir = download_capsule(bix_id)
    uuid = CAPSULES[bix_id]
    data_subdir = os.path.join(extract_dir, f"CapsuleData-{uuid}")
    csv_files = [f for f in os.listdir(data_subdir) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_subdir}")
    return pd.read_csv(os.path.join(data_subdir, csv_files[0]))


# ---------------------------------------------------------------------------
# Test tracking
# ---------------------------------------------------------------------------

RESULTS = []


def check(test_name, value, expected, eval_mode="range", tolerance=None):
    """Evaluate a test result and record it.

    eval_mode:
      - 'range': expected is (low, high), value must be within
      - 'exact': expected is exact string/int match
      - 'approx': expected is numeric, tolerance is fraction (default 0.02)
    """
    passed = False
    detail = ""

    try:
        if eval_mode == "range":
            low, high = expected
            passed = low <= float(value) <= high
            detail = f"value={value}, expected=({low}, {high})"
        elif eval_mode == "exact":
            passed = str(value).strip() == str(expected).strip()
            detail = f"value={value!r}, expected={expected!r}"
        elif eval_mode == "approx":
            tol = tolerance or 0.02
            passed = abs(float(value) - float(expected)) / max(abs(float(expected)), 1e-10) < tol
            detail = f"value={value}, expected={expected}, tol={tol}"
        else:
            detail = f"Unknown eval_mode: {eval_mode}"
    except Exception as e:
        detail = f"Error: {e}"

    status = "PASS" if passed else "FAIL"
    RESULTS.append((test_name, status, detail))
    print(f"  [{status}] {test_name}: {detail}")
    return passed


# ===================================================================
# bix-18 TESTS: Colony Morphometry
# ===================================================================

def test_bix18():
    """Test all bix-18 questions on Swarm_1.csv."""
    print("\n========== bix-18: Colony Morphometry ==========")
    df = get_data_csv("bix-18")

    # Group by Genotype
    summary = df.groupby("Genotype").agg(
        Mean_Area=("Area", "mean"),
        Mean_Circ=("Circularity", "mean"),
        SD_Circ=("Circularity", "std"),
        N=("Circularity", "count"),
    ).reset_index()
    summary["SEM_Circ"] = summary["SD_Circ"] / np.sqrt(summary["N"])

    # q1: Mean circularity for genotype with largest mean area
    max_area_row = summary.loc[summary["Mean_Area"].idxmax()]
    check("bix-18-q1: Circ of max-area genotype",
          max_area_row["Mean_Circ"], (0.07, 0.08), "range")

    # q2: Mean swarming area of wildtype to nearest thousand
    wt_mean = summary[summary["Genotype"] == "Wildtype"]["Mean_Area"].values[0]
    wt_rounded = int(round(wt_mean, -3))
    check("bix-18-q2: WT mean area (nearest 1000)",
          wt_rounded, "82000", "exact")

    # q3: Percent reduction in mean colony area for lasR vs wildtype
    lasR_mean = summary[summary["Genotype"] == "\u0394lasR"]["Mean_Area"].values[0]
    pct_reduction = (wt_mean - lasR_mean) / wt_mean * 100
    check("bix-18-q3: % reduction lasR vs WT",
          pct_reduction, (69, 72), "range")

    # q4: SEM for circularity in rhlR- mutant
    rhlR_sem = summary[summary["Genotype"] == "rhlR-"]["SEM_Circ"].values[0]
    check("bix-18-q4: SEM circularity rhlR-",
          rhlR_sem, (0.031, 0.032), "range")

    # q5: Relative proportion of lasR area to wildtype (as %)
    proportion = (lasR_mean / wt_mean) * 100
    check("bix-18-q5: Proportion lasR/WT (%)",
          proportion, (25, 30), "range")


# ===================================================================
# bix-19 TESTS: NeuN Cell Counting Statistics
# ===================================================================

def test_bix19():
    """Test all bix-19 questions on NeuN_quantification.csv."""
    print("\n========== bix-19: NeuN Cell Counting Statistics ==========")
    df = get_data_csv("bix-19")
    # Fix column name typo in data
    df = df.rename(columns={"Hemispere": "Hemisphere"})

    kd_data = df[df["Hemisphere"] == "KD"]["NeuN"]
    ctrl_data = df[df["Hemisphere"] == "CTRL"]["NeuN"]

    # q1 & q5: Power analysis -> sample size
    n_kd, n_ctrl = len(kd_data), len(ctrl_data)
    sd_pooled = np.sqrt(
        ((n_kd - 1) * kd_data.std()**2 + (n_ctrl - 1) * ctrl_data.std()**2)
        / (n_kd + n_ctrl - 2)
    )
    d = (kd_data.mean() - ctrl_data.mean()) / sd_pooled

    analysis = TTestIndPower()
    sample_size = analysis.solve_power(
        effect_size=abs(d), alpha=0.05, power=0.8, alternative="two-sided"
    )
    n_required = int(np.ceil(sample_size))
    check("bix-19-q1: Sample size per group",
          n_required, "337", "exact")

    # q2: Cohen's d
    check("bix-19-q2: Cohen's d",
          abs(d), (0.215, 0.217), "range")

    # q3: Shapiro-Wilk W for KD group
    w_stat, _ = stats.shapiro(kd_data)
    check("bix-19-q3: Shapiro-Wilk W (KD)",
          w_stat, (0.955, 0.957), "range")

    # q4: F-statistic for Hemisphere:Sex interaction
    model = ols("NeuN ~ C(Hemisphere) * C(Sex)", data=df).fit()
    anova_table = sm.stats.anova_lm(model, typ=2)
    f_interaction = anova_table.loc["C(Hemisphere):C(Sex)", "F"]
    check("bix-19-q4: F-stat Hemisphere:Sex interaction",
          f_interaction, (1.065, 1.067), "range")

    # q5: Same as q1 (llm_verifier expects "337 samples")
    check("bix-19-q5: Min sample size (llm)",
          f"{n_required}", "337", "exact")


# ===================================================================
# bix-41 TESTS: Co-culture Dunnett's Analysis
# ===================================================================

def test_bix41():
    """Test all bix-41 questions on Swarm_2.csv."""
    print("\n========== bix-41: Co-culture Dunnett's Analysis ==========")
    df = get_data_csv("bix-41")

    # Create combined group label as in R analysis
    df["Strain_Ratio"] = df["StrainNumber"].astype(str) + "_" + df["Ratio"].astype(str)

    # Control group: Strain 1 at 1:0
    control = "1_1:0"

    # Identify co-culture groups (those with two strains = "287_98")
    coculture_mask = df["StrainNumber"].astype(str) == "287_98"
    coculture_df = df[coculture_mask | (df["Strain_Ratio"] == control)].copy()

    # Get unique treatment groups (excluding control)
    treatment_groups = sorted(
        [g for g in coculture_df["Strain_Ratio"].unique() if g != control]
    )

    # Run Dunnett's test for Area
    control_area = coculture_df[coculture_df["Strain_Ratio"] == control]["Area"].values
    treatment_area_data = [
        coculture_df[coculture_df["Strain_Ratio"] == g]["Area"].values
        for g in treatment_groups
    ]
    dunnett_area = stats.dunnett(*treatment_area_data, control=control_area)

    # Run Dunnett's test for Circularity
    control_circ = coculture_df[coculture_df["Strain_Ratio"] == control]["Circularity"].values
    treatment_circ_data = [
        coculture_df[coculture_df["Strain_Ratio"] == g]["Circularity"].values
        for g in treatment_groups
    ]
    dunnett_circ = stats.dunnett(*treatment_circ_data, control=control_circ)

    # Build results table
    results = pd.DataFrame({
        "group": treatment_groups,
        "p_area": dunnett_area.pvalue,
        "p_circ": dunnett_circ.pvalue,
    })
    results["sig_area"] = results["p_area"] < 0.05
    results["sig_circ"] = results["p_circ"] < 0.05
    results["equiv_both"] = ~results["sig_area"] & ~results["sig_circ"]
    results["diff_both"] = results["sig_area"] & results["sig_circ"]

    # Extract ratio from group name (e.g., "287_98_5:1" -> "5:1")
    results["ratio"] = results["group"].str.replace("287_98_", "")

    # q1: How many co-culture conditions equivalent to Strain 1 in BOTH?
    n_equiv = results["equiv_both"].sum()
    check("bix-41-q1: Co-cultures equivalent in both",
          n_equiv, "6", "exact")

    # q3: Raw difference in mean circularity between Strain 98 and Strain 1
    strain98_circ = df[df["StrainNumber"].astype(str) == "98"]["Circularity"].mean()
    strain1_circ = df[df["StrainNumber"].astype(str) == "1"]["Circularity"].mean()
    raw_diff = abs(strain98_circ - strain1_circ)
    check("bix-41-q3: Raw diff circularity 98 vs 1",
          raw_diff, (0.42, 0.43), "range")

    # q4: How many different co-culture RATIOS show significant differences in BOTH?
    n_diff = results["diff_both"].sum()
    check("bix-41-q4: Co-culture ratios different in both",
          n_diff, "4", "exact")

    # q5: Which ratio of 287:98 most similar to Strain 1?
    # Compare mean Area and Circularity
    strain1_means = df[df["Strain_Ratio"] == "1_1:0"][["Area", "Circularity"]].mean()

    coculture_only = df[df["StrainNumber"].astype(str) == "287_98"].copy()
    ratio_means = coculture_only.groupby("Ratio")[["Area", "Circularity"]].mean()

    # Normalize by range for fair comparison
    all_vals = pd.concat([ratio_means, pd.DataFrame([strain1_means], index=["ref"])])
    ranges = all_vals.max() - all_vals.min()
    ranges = ranges.replace(0, 1)

    distances = {}
    for ratio_val in ratio_means.index:
        diff = (ratio_means.loc[ratio_val] - strain1_means) / ranges
        distances[ratio_val] = np.sqrt((diff**2).sum())

    most_similar = min(distances, key=distances.get)
    check("bix-41-q5: Most similar ratio to Strain 1",
          most_similar, "5:1", "exact")


# ===================================================================
# bix-54 TESTS: Regression Modeling
# ===================================================================

def test_bix54():
    """Test all bix-54 questions on Swarm_2.csv."""
    print("\n========== bix-54: Regression Modeling ==========")
    df = get_data_csv("bix-54")

    # Prepare data: filter to co-cultures only and compute frequency
    coculture = df[~df["StrainNumber"].astype(str).isin(["1", "98"])].copy()
    ratio_parts = coculture["Ratio"].str.split(":", expand=True).astype(int)
    coculture["rhlI_D"] = ratio_parts[0]
    coculture["lasI_D"] = ratio_parts[1]
    coculture["Frequency_rhlI"] = coculture["rhlI_D"] / (coculture["rhlI_D"] + coculture["lasI_D"])

    x = coculture["Frequency_rhlI"].values
    y = coculture["Area"].values

    # --- Cubic model ---
    X_cubic = np.column_stack([x, x**2, x**3])
    X_cubic = sm.add_constant(X_cubic)
    cubic_model = sm.OLS(y, X_cubic).fit()

    check("bix-54-q2: R-squared cubic model",
          cubic_model.rsquared, (0.58, 0.59), "range")

    # --- Natural spline model ---
    # Use patsy's cr() with explicit quantile knots to match R's ns(df=4)
    # R's ns(x, df=4) places df-1=3 internal knots at the 25th, 50th, 75th percentiles
    from patsy import dmatrix

    quantiles = np.percentile(x, [25, 50, 75])
    knot_str = ", ".join([str(k) for k in quantiles])
    spline_formula = f"cr(Frequency_rhlI, knots=[{knot_str}]) - 1"

    X_spline = np.array(dmatrix(spline_formula, coculture))
    X_spline_full = sm.add_constant(X_spline)
    spline_model = sm.OLS(y, X_spline_full).fit()

    # q6: R-squared for natural spline model
    check("bix-54-q6: R-squared spline model",
          spline_model.rsquared, (0.80, 0.81), "range")

    # Predict over fine grid for peak finding
    x_grid = np.linspace(x.min(), x.max(), 1000)
    grid_df = pd.DataFrame({"Frequency_rhlI": x_grid})
    X_grid_spline = np.array(dmatrix(spline_formula, grid_df))
    X_grid_full = sm.add_constant(X_grid_spline)

    predictions = spline_model.get_prediction(X_grid_full)
    pred_mean = predictions.predicted_mean
    pred_ci = predictions.conf_int(alpha=0.05)

    max_idx = np.argmax(pred_mean)
    peak_freq = x_grid[max_idx]
    peak_area = pred_mean[max_idx]
    peak_ci_lower = pred_ci[max_idx, 0]
    peak_ci_upper = pred_ci[max_idx, 1]

    # q1: Peak frequency from spline
    check("bix-54-q1: Peak frequency (spline)",
          peak_freq, (0.88, 1.0), "range")

    # q3: Lower bound 95% CI for peak area
    check("bix-54-q3: Lower CI for peak area",
          peak_ci_lower, (157500, 158000), "range")

    # q4: p-value of F-statistic for spline model
    # Range is (1.13e-10, 1.13e-12) which means any p-value that small
    f_pvalue = spline_model.f_pvalue
    check("bix-54-q4: F-stat p-value (spline)",
          f_pvalue, (1.13e-12, 1.13e-10), "range")

    # q5: Peak frequency ratio (same as q1 but different wording)
    check("bix-54-q5: Peak freq ratio rhlI:lasI",
          peak_freq, (0.90, 0.99), "range")

    # q7: Maximum area from best-fitting model
    # Compare quadratic, cubic, and spline R-squared
    # Quadratic model
    X_quad = np.column_stack([x, x**2])
    X_quad = sm.add_constant(X_quad)
    quad_model = sm.OLS(y, X_quad).fit()

    models = {
        "quadratic": {"r2": quad_model.rsquared},
        "cubic": {"r2": cubic_model.rsquared},
        "spline": {"r2": spline_model.rsquared, "peak": peak_area},
    }

    # Best model is spline (highest R-squared)
    best = max(models.items(), key=lambda item: item[1]["r2"])
    # The spline model's peak area
    check("bix-54-q7: Max area from best model",
          peak_area, (184000, 185000), "range")


# ===================================================================
# Main runner
# ===================================================================

def main():
    print("=" * 70)
    print("tooluniverse-image-analysis: BixBench Test Suite")
    print("=" * 70)

    # Download all data capsules first
    print("\nDownloading data capsules...")
    for bix_id in CAPSULES:
        download_capsule(bix_id)
        print(f"  {bix_id}: OK")

    # Run all tests
    try:
        test_bix18()
    except Exception as e:
        print(f"  [ERROR] bix-18: {e}")
        traceback.print_exc()

    try:
        test_bix19()
    except Exception as e:
        print(f"  [ERROR] bix-19: {e}")
        traceback.print_exc()

    try:
        test_bix41()
    except Exception as e:
        print(f"  [ERROR] bix-41: {e}")
        traceback.print_exc()

    try:
        test_bix54()
    except Exception as e:
        print(f"  [ERROR] bix-54: {e}")
        traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    n_pass = sum(1 for _, s, _ in RESULTS if s == "PASS")
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    total = len(RESULTS)

    for name, status, detail in RESULTS:
        marker = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {marker} {name}")

    print(f"\nTotal: {total} tests, {n_pass} passed, {n_fail} failed")
    print(f"Pass rate: {n_pass}/{total} ({100*n_pass/total:.1f}%)")

    return n_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
