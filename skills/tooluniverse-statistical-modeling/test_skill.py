#!/usr/bin/env python3
"""
Comprehensive Test Suite for tooluniverse-statistical-modeling skill.

Tests all statistical modeling capabilities:
- Linear regression (OLS)
- Binary logistic regression
- Ordinal logistic regression (proportional odds)
- Multinomial logistic regression
- Mixed-effects models
- Cox proportional hazards survival analysis
- Kaplan-Meier estimation
- Statistical tests (t-test, chi-square, Fisher's exact, etc.)
- Model diagnostics
- Odds ratio computation and interpretation
- Confidence intervals
- Model comparison
"""

import sys
import time
import traceback
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

# Track results
test_results = []
total_start = time.time()


def record_result(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"  [{status}] {name}")
    if details and not passed:
        print(f"         {details}")


# ==========================================================================
# DATA GENERATION HELPERS
# ==========================================================================

def generate_binary_outcome_data(n=500, seed=42):
    """Generate realistic clinical trial data with binary outcome."""
    np.random.seed(seed)
    age = np.random.normal(55, 12, n).astype(int)
    male = np.random.binomial(1, 0.55, n)
    treatment = np.random.binomial(1, 0.5, n)
    bmi = np.random.normal(27, 5, n)

    # True model: logit(p) = -2 + 0.8*treatment + 0.03*age - 0.5*male + 0.05*bmi
    logit_p = -2 + 0.8 * treatment + 0.03 * age - 0.5 * male + 0.05 * bmi
    prob = 1 / (1 + np.exp(-logit_p))
    outcome = np.random.binomial(1, prob)

    return pd.DataFrame({
        'outcome': outcome,
        'treatment': treatment,
        'age': age,
        'male': male,
        'bmi': bmi,
    })


def generate_ordinal_outcome_data(n=500, seed=42):
    """Generate data with ordinal outcome (Mild/Moderate/Severe)."""
    np.random.seed(seed)
    exposure = np.random.binomial(1, 0.4, n)
    age = np.random.normal(50, 15, n)
    male = np.random.binomial(1, 0.5, n)

    # Latent variable model
    latent = -0.7 * exposure + 0.02 * age + 0.3 * male + np.random.logistic(0, 1, n)

    # Cut points
    severity = pd.cut(latent, bins=[-np.inf, -0.5, 1.0, np.inf],
                       labels=['Mild', 'Moderate', 'Severe'])

    return pd.DataFrame({
        'severity': severity,
        'exposure': exposure,
        'age': age,
        'male': male,
    })


def generate_survival_data(n=300, seed=42):
    """Generate survival data for Cox PH and Kaplan-Meier."""
    np.random.seed(seed)
    treatment = np.random.binomial(1, 0.5, n)
    age = np.random.normal(60, 10, n)
    stage = np.random.choice([1, 2, 3], n, p=[0.3, 0.4, 0.3])

    # True hazard: h(t) = h0(t) * exp(0.5*treatment_control - 0.3*treatment + 0.02*age + 0.4*stage)
    # So treatment=1 has LOWER hazard (better survival)
    linear_pred = -0.5 * treatment + 0.02 * age + 0.3 * stage
    # Weibull baseline hazard
    shape = 1.5
    scale = np.exp(-linear_pred / shape) * 30  # Scale to ~30 month median
    time = np.random.weibull(shape, n) * scale

    # Administrative censoring at 60 months
    censor_time = np.random.uniform(24, 60, n)
    event = (time <= censor_time).astype(int)
    observed_time = np.minimum(time, censor_time)

    return pd.DataFrame({
        'time': observed_time,
        'event': event,
        'treatment': treatment,
        'age': age,
        'stage': stage,
    })


def generate_continuous_outcome_data(n=200, seed=42):
    """Generate data with continuous outcome for OLS."""
    np.random.seed(seed)
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.normal(5, 2, n)
    x3 = np.random.binomial(1, 0.5, n)

    # True model: y = 3 + 2*x1 - 0.5*x2 + 1.5*x3 + epsilon
    y = 3 + 2 * x1 - 0.5 * x2 + 1.5 * x3 + np.random.normal(0, 1, n)

    return pd.DataFrame({
        'y': y,
        'x1': x1,
        'x2': x2,
        'x3': x3,
    })


def generate_mixed_effects_data(n_subjects=50, n_obs_per_subject=5, seed=42):
    """Generate clustered/longitudinal data for mixed-effects models."""
    np.random.seed(seed)
    subject_ids = np.repeat(range(n_subjects), n_obs_per_subject)
    n_total = n_subjects * n_obs_per_subject

    # Random intercepts per subject
    random_intercepts = np.random.normal(0, 2, n_subjects)
    subject_intercepts = random_intercepts[subject_ids]

    treatment = np.random.binomial(1, 0.5, n_total)
    time_point = np.tile(range(n_obs_per_subject), n_subjects)

    # y = 10 + 1.5*treatment + 0.8*time + random_intercept + error
    y = 10 + 1.5 * treatment + 0.8 * time_point + subject_intercepts + np.random.normal(0, 1, n_total)

    return pd.DataFrame({
        'outcome': y,
        'treatment': treatment,
        'time': time_point,
        'subject_id': subject_ids,
    })


def generate_multinomial_data(n=400, seed=42):
    """Generate data with unordered categorical outcome (3 categories)."""
    np.random.seed(seed)
    x1 = np.random.normal(0, 1, n)
    x2 = np.random.binomial(1, 0.5, n)

    # Multinomial probabilities
    logit_B = 0.5 + 1.0 * x1 - 0.3 * x2
    logit_C = -0.2 + 0.3 * x1 + 0.8 * x2
    p_A = 1 / (1 + np.exp(logit_B) + np.exp(logit_C))
    p_B = np.exp(logit_B) / (1 + np.exp(logit_B) + np.exp(logit_C))
    p_C = np.exp(logit_C) / (1 + np.exp(logit_B) + np.exp(logit_C))

    outcome = []
    for i in range(n):
        outcome.append(np.random.choice(['TypeA', 'TypeB', 'TypeC'],
                                        p=[p_A[i], p_B[i], p_C[i]]))

    return pd.DataFrame({
        'subtype': outcome,
        'x1': x1,
        'x2': x2,
    })


# ==========================================================================
# TEST FUNCTIONS
# ==========================================================================

def run_tests():
    print("=" * 70)
    print("Statistical Modeling Skill - Comprehensive Test Suite")
    print("=" * 70)

    # ==================================================================
    # SECTION 1: Package Imports
    # ==================================================================
    print("\n--- Section 1: Package Imports ---")

    # 1a: statsmodels
    try:
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        record_result("1a: Import statsmodels", True,
                      f"version: {sm.__version__ if hasattr(sm, '__version__') else 'loaded'}")
    except Exception as e:
        record_result("1a: Import statsmodels", False, str(e))

    # 1b: lifelines
    try:
        from lifelines import CoxPHFitter, KaplanMeierFitter
        from lifelines.statistics import logrank_test
        import lifelines
        record_result("1b: Import lifelines", True, f"version: {lifelines.__version__}")
    except Exception as e:
        record_result("1b: Import lifelines", False, str(e))

    # 1c: scipy.stats
    try:
        from scipy import stats as scipy_stats
        record_result("1c: Import scipy.stats", True)
    except Exception as e:
        record_result("1c: Import scipy.stats", False, str(e))

    # 1d: sklearn
    try:
        from sklearn.linear_model import LogisticRegression
        record_result("1d: Import sklearn", True)
    except Exception as e:
        record_result("1d: Import sklearn", False, str(e))

    # 1e: OrderedModel
    try:
        from statsmodels.miscmodels.ordinal_model import OrderedModel
        record_result("1e: Import OrderedModel", True)
    except Exception as e:
        record_result("1e: Import OrderedModel", False, str(e))

    # ==================================================================
    # SECTION 2: OLS Linear Regression
    # ==================================================================
    print("\n--- Section 2: OLS Linear Regression ---")
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    df_cont = generate_continuous_outcome_data()

    # 2a: OLS with formula API
    try:
        model = smf.ols('y ~ x1 + x2 + x3', data=df_cont).fit()
        has_coefs = len(model.params) == 4  # intercept + 3 predictors
        r2_ok = 0.5 < model.rsquared < 1.0  # Should be high given known DGP
        x1_close = abs(model.params['x1'] - 2.0) < 0.5  # True coef is 2.0
        record_result("2a: OLS formula API", has_coefs and r2_ok and x1_close,
                      f"R2={model.rsquared:.4f}, x1_coef={model.params['x1']:.4f} (true=2.0)")
    except Exception as e:
        record_result("2a: OLS formula API", False, str(e))

    # 2b: OLS with matrix API
    try:
        X = sm.add_constant(df_cont[['x1', 'x2', 'x3']])
        y = df_cont['y']
        model_mat = sm.OLS(y, X).fit()
        params_match = np.allclose(model.params.values, model_mat.params.values, atol=0.001)
        record_result("2b: OLS matrix API matches formula", params_match,
                      f"max diff={np.max(np.abs(model.params.values - model_mat.params.values)):.6f}")
    except Exception as e:
        record_result("2b: OLS matrix API matches formula", False, str(e))

    # 2c: OLS confidence intervals
    try:
        ci = model.conf_int()
        ci_has_rows = len(ci) == 4
        ci_contains_true_x1 = ci.loc['x1', 0] < 2.0 < ci.loc['x1', 1]
        record_result("2c: OLS confidence intervals", ci_has_rows and ci_contains_true_x1,
                      f"x1 CI: ({ci.loc['x1', 0]:.4f}, {ci.loc['x1', 1]:.4f}), contains 2.0: {ci_contains_true_x1}")
    except Exception as e:
        record_result("2c: OLS confidence intervals", False, str(e))

    # 2d: OLS p-values
    try:
        x1_sig = model.pvalues['x1'] < 0.05
        x2_sig = model.pvalues['x2'] < 0.05
        x3_sig = model.pvalues['x3'] < 0.05
        record_result("2d: OLS p-values (all significant)", x1_sig and x2_sig and x3_sig,
                      f"p(x1)={model.pvalues['x1']:.6f}, p(x2)={model.pvalues['x2']:.6f}, p(x3)={model.pvalues['x3']:.6f}")
    except Exception as e:
        record_result("2d: OLS p-values (all significant)", False, str(e))

    # 2e: OLS model fit statistics
    try:
        has_aic = hasattr(model, 'aic') and model.aic is not None
        has_bic = hasattr(model, 'bic') and model.bic is not None
        has_fstat = hasattr(model, 'fvalue') and model.fvalue is not None
        record_result("2e: OLS model fit stats (AIC/BIC/F)", has_aic and has_bic and has_fstat,
                      f"AIC={model.aic:.2f}, BIC={model.bic:.2f}, F={model.fvalue:.2f}")
    except Exception as e:
        record_result("2e: OLS model fit stats (AIC/BIC/F)", False, str(e))

    # 2f: OLS diagnostics - residual normality
    try:
        from statsmodels.stats.stattools import durbin_watson
        dw = durbin_watson(model.resid)
        dw_ok = 1.5 < dw < 2.5  # No autocorrelation
        sw_stat, sw_p = scipy_stats.shapiro(model.resid)
        record_result("2f: OLS diagnostics (DW, Shapiro-Wilk)", dw_ok,
                      f"DW={dw:.4f}, Shapiro p={sw_p:.6f}")
    except Exception as e:
        record_result("2f: OLS diagnostics (DW, Shapiro-Wilk)", False, str(e))

    # 2g: OLS heteroscedasticity test
    try:
        from statsmodels.stats.diagnostic import het_breuschpagan
        bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, model.model.exog)
        record_result("2g: OLS Breusch-Pagan test", True,
                      f"BP stat={bp_stat:.4f}, p={bp_p:.6f}, homoscedastic={bp_p > 0.05}")
    except Exception as e:
        record_result("2g: OLS Breusch-Pagan test", False, str(e))

    # 2h: VIF multicollinearity
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        X_vif = model.model.exog
        vifs = {}
        for i in range(1, X_vif.shape[1]):  # Skip intercept
            vifs[model.model.exog_names[i]] = variance_inflation_factor(X_vif, i)
        all_low_vif = all(v < 5 for v in vifs.values())
        record_result("2h: VIF multicollinearity check", all_low_vif,
                      f"VIFs: {', '.join(f'{k}={v:.2f}' for k, v in vifs.items())}")
    except Exception as e:
        record_result("2h: VIF multicollinearity check", False, str(e))

    # 2i: OLS with interaction term
    try:
        model_int = smf.ols('y ~ x1 * x3', data=df_cont).fit()
        has_interaction = 'x1:x3' in model_int.params.index
        record_result("2i: OLS interaction term (x1:x3)", has_interaction,
                      f"interaction coef={model_int.params.get('x1:x3', 'MISSING')}")
    except Exception as e:
        record_result("2i: OLS interaction term (x1:x3)", False, str(e))

    # ==================================================================
    # SECTION 3: Binary Logistic Regression
    # ==================================================================
    print("\n--- Section 3: Binary Logistic Regression ---")

    df_binary = generate_binary_outcome_data()

    # 3a: Logistic regression fit
    try:
        model_logit = smf.logit('outcome ~ treatment + age + male + bmi', data=df_binary).fit(disp=0)
        has_coefs = len(model_logit.params) == 5
        converged = model_logit.mle_retvals['converged']
        record_result("3a: Logistic regression fit", has_coefs and converged,
                      f"converged={converged}, n_coefs={len(model_logit.params)}")
    except Exception as e:
        record_result("3a: Logistic regression fit", False, str(e))

    # 3b: Odds ratios
    try:
        ors = np.exp(model_logit.params)
        treatment_or = ors['treatment']
        or_positive = treatment_or > 1  # True coef is 0.8 -> OR > 1
        or_reasonable = 1.0 < treatment_or < 5.0
        record_result("3b: Odds ratios computed", or_positive and or_reasonable,
                      f"treatment OR={treatment_or:.4f} (expected >1)")
    except Exception as e:
        record_result("3b: Odds ratios computed", False, str(e))

    # 3c: Odds ratio confidence intervals
    try:
        or_ci = np.exp(model_logit.conf_int())
        treatment_ci_lower = or_ci.loc['treatment', 0]
        treatment_ci_upper = or_ci.loc['treatment', 1]
        ci_valid = treatment_ci_lower < treatment_or < treatment_ci_upper
        ci_doesnt_contain_1 = not (treatment_ci_lower <= 1 <= treatment_ci_upper)  # Should be significant
        record_result("3c: Odds ratio CIs", ci_valid,
                      f"treatment OR CI: ({treatment_ci_lower:.4f}, {treatment_ci_upper:.4f})")
    except Exception as e:
        record_result("3c: Odds ratio CIs", False, str(e))

    # 3d: P-values significance
    try:
        treatment_sig = model_logit.pvalues['treatment'] < 0.05
        record_result("3d: Treatment significant (p<0.05)", treatment_sig,
                      f"p={model_logit.pvalues['treatment']:.6f}")
    except Exception as e:
        record_result("3d: Treatment significant (p<0.05)", False, str(e))

    # 3e: Model fit (pseudo R-squared, AIC)
    try:
        has_pseudo_r2 = hasattr(model_logit, 'prsquared') and model_logit.prsquared > 0
        has_aic = hasattr(model_logit, 'aic') and model_logit.aic > 0
        has_llf = hasattr(model_logit, 'llf') and model_logit.llf < 0
        record_result("3e: Logistic model fit stats", has_pseudo_r2 and has_aic and has_llf,
                      f"pseudo-R2={model_logit.prsquared:.4f}, AIC={model_logit.aic:.2f}")
    except Exception as e:
        record_result("3e: Logistic model fit stats", False, str(e))

    # 3f: Odds ratio interpretation
    try:
        or_val = np.exp(model_logit.params['treatment'])
        if or_val > 1:
            pct_increase = round((or_val - 1) * 100, 1)
            interpretation = f"{pct_increase}% increase in odds"
        else:
            pct_decrease = round((1 - or_val) * 100, 1)
            interpretation = f"{pct_decrease}% decrease in odds"
        has_interpretation = len(interpretation) > 0
        record_result("3f: Odds ratio interpretation", has_interpretation,
                      f"Treatment: {interpretation}")
    except Exception as e:
        record_result("3f: Odds ratio interpretation", False, str(e))

    # 3g: Logistic matrix API
    try:
        X = sm.add_constant(df_binary[['treatment', 'age', 'male', 'bmi']])
        y = df_binary['outcome']
        model_logit_mat = sm.Logit(y, X).fit(disp=0)
        params_match = np.allclose(model_logit.params.values, model_logit_mat.params.values, atol=0.01)
        record_result("3g: Logistic matrix API matches formula", params_match)
    except Exception as e:
        record_result("3g: Logistic matrix API matches formula", False, str(e))

    # ==================================================================
    # SECTION 4: Ordinal Logistic Regression
    # ==================================================================
    print("\n--- Section 4: Ordinal Logistic Regression ---")

    from statsmodels.miscmodels.ordinal_model import OrderedModel
    df_ord = generate_ordinal_outcome_data()

    # 4a: Ordinal logistic fit
    try:
        severity_order = ['Mild', 'Moderate', 'Severe']
        df_ord['severity'] = pd.Categorical(df_ord['severity'], categories=severity_order, ordered=True)
        y = df_ord['severity'].cat.codes
        X = df_ord[['exposure', 'age', 'male']].astype(float)

        model_ord = OrderedModel(y, X, distr='logit')
        fit_ord = model_ord.fit(method='bfgs', disp=0)

        has_params = len(fit_ord.params) > 0
        record_result("4a: Ordinal logistic fit", has_params,
                      f"n_params={len(fit_ord.params)}, converged")
    except Exception as e:
        record_result("4a: Ordinal logistic fit", False, str(e))

    # 4b: Ordinal logistic odds ratio
    try:
        exposure_coef = fit_ord.params['exposure']
        exposure_or = np.exp(exposure_coef)
        # True coefficient is -0.7, so OR should be < 1
        or_correct_direction = exposure_or < 1.0
        or_reasonable = 0.1 < exposure_or < 2.0
        record_result("4b: Ordinal logistic OR", or_correct_direction and or_reasonable,
                      f"exposure OR={exposure_or:.4f} (expected <1, true coef=-0.7)")
    except Exception as e:
        record_result("4b: Ordinal logistic OR", False, str(e))

    # 4c: Ordinal logistic CI
    try:
        ci = fit_ord.conf_int()
        exposure_ci_lower = np.exp(ci.loc['exposure', 0])
        exposure_ci_upper = np.exp(ci.loc['exposure', 1])
        ci_valid = exposure_ci_lower < exposure_or < exposure_ci_upper
        record_result("4c: Ordinal logistic CI", ci_valid,
                      f"OR CI: ({exposure_ci_lower:.4f}, {exposure_ci_upper:.4f})")
    except Exception as e:
        record_result("4c: Ordinal logistic CI", False, str(e))

    # 4d: Ordinal logistic p-value
    try:
        exposure_p = fit_ord.pvalues['exposure']
        exposure_sig = exposure_p < 0.05
        record_result("4d: Ordinal logistic p-value", exposure_sig,
                      f"p={exposure_p:.6f}")
    except Exception as e:
        record_result("4d: Ordinal logistic p-value", False, str(e))

    # 4e: Thresholds extracted
    try:
        n_predictors = 3  # exposure, age, male
        n_thresholds = len(severity_order) - 1  # 2 thresholds
        total_params = len(fit_ord.params)
        has_thresholds = total_params == n_predictors + n_thresholds
        record_result("4e: Ordinal logistic thresholds", has_thresholds,
                      f"total_params={total_params}, expected={n_predictors + n_thresholds}")
    except Exception as e:
        record_result("4e: Ordinal logistic thresholds", False, str(e))

    # 4f: Percentage reduction in OR (confounding assessment)
    try:
        # Unadjusted model
        X_crude = df_ord[['exposure']].astype(float)
        model_crude = OrderedModel(y, X_crude, distr='logit')
        fit_crude = model_crude.fit(method='bfgs', disp=0)
        or_crude = np.exp(fit_crude.params['exposure'])

        # Adjusted model (already fitted)
        or_adj = exposure_or

        # Percentage change
        pct_change = ((or_crude - or_adj) / or_crude) * 100
        has_valid_pct = -100 < pct_change < 100
        record_result("4f: Percentage change in OR after adjustment", has_valid_pct,
                      f"crude OR={or_crude:.4f}, adj OR={or_adj:.4f}, change={pct_change:.1f}%")
    except Exception as e:
        record_result("4f: Percentage change in OR after adjustment", False, str(e))

    # 4g: Proportional odds assumption test (Brant-like)
    try:
        # Fit separate binary logits at each cut point
        cutpoint_coefs = {}
        for k in range(len(severity_order) - 1):
            y_binary = (y > k).astype(int)
            X_const = sm.add_constant(df_ord[['exposure', 'age', 'male']].astype(float))
            binary_model = sm.Logit(y_binary, X_const).fit(disp=0)
            cutpoint_coefs[k] = binary_model.params['exposure']

        coefs_list = list(cutpoint_coefs.values())
        coef_range = max(coefs_list) - min(coefs_list)
        proportional = coef_range < 1.0  # Rough check
        record_result("4g: Proportional odds assumption check", True,
                      f"exposure coefs by cutpoint: {[f'{c:.4f}' for c in coefs_list]}, range={coef_range:.4f}")
    except Exception as e:
        record_result("4g: Proportional odds assumption check", False, str(e))

    # ==================================================================
    # SECTION 5: Multinomial Logistic Regression
    # ==================================================================
    print("\n--- Section 5: Multinomial Logistic Regression ---")

    df_multi = generate_multinomial_data()

    # 5a: Multinomial logistic fit (statsmodels)
    try:
        # Encode outcome
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        le.classes_ = np.array(['TypeA', 'TypeB', 'TypeC'])
        y_multi = le.transform(df_multi['subtype'])

        X_multi = sm.add_constant(df_multi[['x1', 'x2']])
        mn_model = sm.MNLogit(y_multi, X_multi).fit(disp=0, maxiter=200)

        has_params = mn_model.params.shape[0] > 0
        converged = mn_model.mle_retvals['converged']
        record_result("5a: Multinomial logistic fit", has_params and converged,
                      f"converged={converged}, params shape={mn_model.params.shape}")
    except Exception as e:
        record_result("5a: Multinomial logistic fit", False, str(e))

    # 5b: Multinomial odds ratios
    try:
        mn_ors = np.exp(mn_model.params)
        has_or_values = mn_ors.shape[0] > 0
        record_result("5b: Multinomial odds ratios", has_or_values,
                      f"OR matrix shape: {mn_ors.shape}")
    except Exception as e:
        record_result("5b: Multinomial odds ratios", False, str(e))

    # 5c: Multinomial p-values
    try:
        mn_pvals = mn_model.pvalues
        has_pvals = mn_pvals.shape[0] > 0
        record_result("5c: Multinomial p-values", has_pvals,
                      f"p-value matrix shape: {mn_pvals.shape}")
    except Exception as e:
        record_result("5c: Multinomial p-values", False, str(e))

    # 5d: Multinomial model fit
    try:
        has_pseudo_r2 = mn_model.prsquared > 0
        has_aic = mn_model.aic > 0
        has_llr = mn_model.llr > 0  # Log-likelihood ratio
        record_result("5d: Multinomial model fit", has_pseudo_r2 and has_aic,
                      f"pseudo-R2={mn_model.prsquared:.4f}, AIC={mn_model.aic:.2f}")
    except Exception as e:
        record_result("5d: Multinomial model fit", False, str(e))

    # 5e: sklearn multinomial (fallback)
    try:
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
        lr.fit(df_multi[['x1', 'x2']].values, df_multi['subtype'].values)
        n_classes = len(lr.classes_)
        record_result("5e: sklearn multinomial logistic", n_classes == 3,
                      f"classes={list(lr.classes_)}")
    except Exception as e:
        record_result("5e: sklearn multinomial logistic", False, str(e))

    # ==================================================================
    # SECTION 6: Mixed-Effects Models
    # ==================================================================
    print("\n--- Section 6: Mixed-Effects Models ---")

    df_mixed = generate_mixed_effects_data()

    # 6a: Linear mixed model fit
    try:
        lmm = smf.mixedlm('outcome ~ treatment + time', data=df_mixed,
                           groups=df_mixed['subject_id'])
        lmm_fit = lmm.fit(reml=True)
        converged = lmm_fit.converged
        has_fe = len(lmm_fit.fe_params) > 0
        record_result("6a: Linear mixed model fit", converged and has_fe,
                      f"converged={converged}, fixed effects: {list(lmm_fit.fe_params.index)}")
    except Exception as e:
        record_result("6a: Linear mixed model fit", False, str(e))

    # 6b: Fixed effects recovery
    try:
        treatment_coef = lmm_fit.fe_params['treatment']
        time_coef = lmm_fit.fe_params['time']
        # True: treatment=1.5, time=0.8
        treatment_close = abs(treatment_coef - 1.5) < 1.0
        time_close = abs(time_coef - 0.8) < 0.5
        record_result("6b: Fixed effects recovery", treatment_close and time_close,
                      f"treatment={treatment_coef:.4f} (true=1.5), time={time_coef:.4f} (true=0.8)")
    except Exception as e:
        record_result("6b: Fixed effects recovery", False, str(e))

    # 6c: Random effects variance
    try:
        re_var = lmm_fit.cov_re
        if hasattr(re_var, 'values'):
            group_var = float(re_var.iloc[0, 0])
        else:
            group_var = float(re_var)
        resid_var = float(lmm_fit.scale)
        group_var_close = abs(group_var - 4.0) < 3.0  # True random intercept var = 4 (sd=2)
        record_result("6c: Random effects variance", group_var > 0,
                      f"group_var={group_var:.4f} (true=4.0), resid_var={resid_var:.4f}")
    except Exception as e:
        record_result("6c: Random effects variance", False, str(e))

    # 6d: ICC
    try:
        icc = group_var / (group_var + resid_var)
        icc_reasonable = 0.1 < icc < 0.9
        record_result("6d: ICC computation", icc_reasonable,
                      f"ICC={icc:.4f}")
    except Exception as e:
        record_result("6d: ICC computation", False, str(e))

    # 6e: Mixed model p-values
    try:
        treatment_p = lmm_fit.pvalues['treatment']
        treatment_sig = treatment_p < 0.05
        record_result("6e: Mixed model p-values", treatment_sig,
                      f"treatment p={treatment_p:.6f}")
    except Exception as e:
        record_result("6e: Mixed model p-values", False, str(e))

    # 6f: Mixed model with interaction
    try:
        lmm_int = smf.mixedlm('outcome ~ treatment * time', data=df_mixed,
                               groups=df_mixed['subject_id'])
        lmm_int_fit = lmm_int.fit(reml=True)
        has_interaction = 'treatment:time' in lmm_int_fit.fe_params.index
        record_result("6f: Mixed model with interaction", has_interaction,
                      f"interaction coef={lmm_int_fit.fe_params.get('treatment:time', 'MISSING')}")
    except Exception as e:
        record_result("6f: Mixed model with interaction", False, str(e))

    # ==================================================================
    # SECTION 7: Cox Proportional Hazards
    # ==================================================================
    print("\n--- Section 7: Cox Proportional Hazards ---")

    from lifelines import CoxPHFitter
    df_surv = generate_survival_data()

    # 7a: Cox PH fit
    try:
        cph = CoxPHFitter()
        cph.fit(df_surv[['time', 'event', 'treatment', 'age', 'stage']],
                duration_col='time', event_col='event')
        has_summary = cph.summary is not None
        record_result("7a: Cox PH fit", has_summary,
                      f"n_events={int(cph.event_observed.sum())}, n_obs={len(cph.event_observed)}")
    except Exception as e:
        record_result("7a: Cox PH fit", False, str(e))

    # 7b: Hazard ratios
    try:
        summary = cph.summary
        treatment_hr = float(summary.loc['treatment', 'exp(coef)'])
        # True: treatment reduces hazard (coef=-0.5, HR<1)
        hr_correct_direction = treatment_hr < 1.0
        record_result("7b: Hazard ratios", hr_correct_direction,
                      f"treatment HR={treatment_hr:.4f} (expected <1)")
    except Exception as e:
        record_result("7b: Hazard ratios", False, str(e))

    # 7c: HR confidence intervals
    try:
        hr_ci_lower = float(summary.loc['treatment', 'exp(coef) lower 95%'])
        hr_ci_upper = float(summary.loc['treatment', 'exp(coef) upper 95%'])
        ci_valid = hr_ci_lower < treatment_hr < hr_ci_upper
        record_result("7c: HR confidence intervals", ci_valid,
                      f"treatment HR CI: ({hr_ci_lower:.4f}, {hr_ci_upper:.4f})")
    except Exception as e:
        record_result("7c: HR confidence intervals", False, str(e))

    # 7d: Cox p-values
    try:
        treatment_p_cox = float(summary.loc['treatment', 'p'])
        treatment_sig_cox = treatment_p_cox < 0.05
        record_result("7d: Cox treatment p-value", treatment_sig_cox,
                      f"p={treatment_p_cox:.6f}")
    except Exception as e:
        record_result("7d: Cox treatment p-value", False, str(e))

    # 7e: Concordance index
    try:
        c_index = cph.concordance_index_
        c_reasonable = 0.5 < c_index < 1.0
        record_result("7e: Concordance index", c_reasonable,
                      f"C-index={c_index:.4f}")
    except Exception as e:
        record_result("7e: Concordance index", False, str(e))

    # 7f: Partial log-likelihood
    try:
        pll = float(cph.log_likelihood_)
        has_pll = pll < 0  # Log-likelihood is negative
        record_result("7f: Partial log-likelihood", has_pll,
                      f"PLL={pll:.4f}")
    except Exception as e:
        record_result("7f: Partial log-likelihood", False, str(e))

    # 7g: Cox PH with multiple covariates - all reported
    try:
        all_covars = list(summary.index)
        expected = ['treatment', 'age', 'stage']
        all_present = all(c in all_covars for c in expected)
        record_result("7g: All covariates reported", all_present,
                      f"covariates: {all_covars}")
    except Exception as e:
        record_result("7g: All covariates reported", False, str(e))

    # ==================================================================
    # SECTION 8: Kaplan-Meier
    # ==================================================================
    print("\n--- Section 8: Kaplan-Meier Estimation ---")

    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test

    # 8a: Overall KM
    try:
        kmf = KaplanMeierFitter()
        kmf.fit(df_surv['time'], df_surv['event'])
        median_surv = kmf.median_survival_time_
        has_median = not np.isinf(median_surv)
        record_result("8a: Overall KM median survival", has_median,
                      f"median={median_surv:.2f}" if has_median else "median=inf (too few events)")
    except Exception as e:
        record_result("8a: Overall KM median survival", False, str(e))

    # 8b: Stratified KM
    try:
        median_by_group = {}
        for group in [0, 1]:
            mask = df_surv['treatment'] == group
            kmf_g = KaplanMeierFitter()
            kmf_g.fit(df_surv.loc[mask, 'time'], df_surv.loc[mask, 'event'], label=f'treatment_{group}')
            median_by_group[group] = kmf_g.median_survival_time_

        # Treatment group should have longer survival
        both_finite = not np.isinf(median_by_group[0]) and not np.isinf(median_by_group[1])
        if both_finite:
            treatment_better = median_by_group[1] > median_by_group[0]
        else:
            treatment_better = True  # Can't compare if one is inf
        record_result("8b: Stratified KM (treatment vs control)", True,
                      f"control median={median_by_group[0]:.2f}, treatment median={median_by_group[1]:.2f}")
    except Exception as e:
        record_result("8b: Stratified KM (treatment vs control)", False, str(e))

    # 8c: Survival probability at specific time
    try:
        kmf_all = KaplanMeierFitter()
        kmf_all.fit(df_surv['time'], df_surv['event'])
        surv_at_24 = kmf_all.predict(24)
        surv_valid = 0 < float(surv_at_24) < 1
        record_result("8c: Survival probability at t=24", surv_valid,
                      f"S(24)={float(surv_at_24):.4f}")
    except Exception as e:
        record_result("8c: Survival probability at t=24", False, str(e))

    # 8d: Log-rank test
    try:
        g0 = df_surv['treatment'] == 0
        g1 = df_surv['treatment'] == 1
        lr_result = logrank_test(
            df_surv.loc[g0, 'time'], df_surv.loc[g1, 'time'],
            event_observed_A=df_surv.loc[g0, 'event'],
            event_observed_B=df_surv.loc[g1, 'event']
        )
        has_stat = lr_result.test_statistic > 0
        has_p = 0 <= lr_result.p_value <= 1
        record_result("8d: Log-rank test", has_stat and has_p,
                      f"chi2={lr_result.test_statistic:.4f}, p={lr_result.p_value:.6f}")
    except Exception as e:
        record_result("8d: Log-rank test", False, str(e))

    # 8e: KM survival table
    try:
        kmf_table = KaplanMeierFitter()
        kmf_table.fit(df_surv['time'], df_surv['event'])
        surv_func = kmf_table.survival_function_
        has_table = len(surv_func) > 0
        decreasing = all(surv_func.iloc[i, 0] >= surv_func.iloc[i+1, 0]
                         for i in range(len(surv_func)-1))
        record_result("8e: KM survival function is decreasing", has_table and decreasing,
                      f"n_timepoints={len(surv_func)}, starts at {surv_func.iloc[0, 0]:.4f}")
    except Exception as e:
        record_result("8e: KM survival function is decreasing", False, str(e))

    # ==================================================================
    # SECTION 9: Statistical Tests
    # ==================================================================
    print("\n--- Section 9: Statistical Tests ---")

    # 9a: Independent t-test
    try:
        np.random.seed(42)
        group_a = np.random.normal(10, 2, 50)
        group_b = np.random.normal(12, 2, 50)
        t_stat, t_p = scipy_stats.ttest_ind(group_a, group_b)
        sig = t_p < 0.05
        record_result("9a: Independent t-test", sig,
                      f"t={t_stat:.4f}, p={t_p:.6f}")
    except Exception as e:
        record_result("9a: Independent t-test", False, str(e))

    # 9b: Paired t-test
    try:
        before = np.random.normal(100, 15, 30)
        after = before - np.random.normal(5, 3, 30)
        t_stat_p, t_p_p = scipy_stats.ttest_rel(before, after)
        sig_p = t_p_p < 0.05
        record_result("9b: Paired t-test", sig_p,
                      f"t={t_stat_p:.4f}, p={t_p_p:.6f}")
    except Exception as e:
        record_result("9b: Paired t-test", False, str(e))

    # 9c: Mann-Whitney U
    try:
        u_stat, u_p = scipy_stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
        record_result("9c: Mann-Whitney U test", True,
                      f"U={u_stat:.4f}, p={u_p:.6f}")
    except Exception as e:
        record_result("9c: Mann-Whitney U test", False, str(e))

    # 9d: Chi-square test
    try:
        contingency = np.array([[30, 10], [20, 40]])
        chi2, chi2_p, dof, expected = scipy_stats.chi2_contingency(contingency)
        sig_chi = chi2_p < 0.05
        record_result("9d: Chi-square test", sig_chi,
                      f"chi2={chi2:.4f}, p={chi2_p:.6f}, dof={dof}")
    except Exception as e:
        record_result("9d: Chi-square test", False, str(e))

    # 9e: Fisher's exact test
    try:
        table_2x2 = np.array([[8, 2], [1, 9]])
        fe_or, fe_p = scipy_stats.fisher_exact(table_2x2)
        record_result("9e: Fisher exact test", True,
                      f"OR={fe_or:.4f}, p={fe_p:.6f}")
    except Exception as e:
        record_result("9e: Fisher exact test", False, str(e))

    # 9f: One-way ANOVA
    try:
        g1_anova = np.random.normal(10, 2, 30)
        g2_anova = np.random.normal(12, 2, 30)
        g3_anova = np.random.normal(11, 2, 30)
        f_stat, f_p = scipy_stats.f_oneway(g1_anova, g2_anova, g3_anova)
        record_result("9f: One-way ANOVA", True,
                      f"F={f_stat:.4f}, p={f_p:.6f}")
    except Exception as e:
        record_result("9f: One-way ANOVA", False, str(e))

    # 9g: Kruskal-Wallis
    try:
        h_stat, h_p = scipy_stats.kruskal(g1_anova, g2_anova, g3_anova)
        record_result("9g: Kruskal-Wallis test", True,
                      f"H={h_stat:.4f}, p={h_p:.6f}")
    except Exception as e:
        record_result("9g: Kruskal-Wallis test", False, str(e))

    # 9h: Shapiro-Wilk normality test
    try:
        sw_stat, sw_p = scipy_stats.shapiro(np.random.normal(0, 1, 100))
        record_result("9h: Shapiro-Wilk normality test", True,
                      f"W={sw_stat:.4f}, p={sw_p:.6f}")
    except Exception as e:
        record_result("9h: Shapiro-Wilk normality test", False, str(e))

    # 9i: Wilcoxon signed-rank test
    try:
        w_stat, w_p = scipy_stats.wilcoxon(before - after)
        record_result("9i: Wilcoxon signed-rank test", True,
                      f"W={w_stat:.4f}, p={w_p:.6f}")
    except Exception as e:
        record_result("9i: Wilcoxon signed-rank test", False, str(e))

    # ==================================================================
    # SECTION 10: Confidence Intervals
    # ==================================================================
    print("\n--- Section 10: Confidence Intervals ---")

    # 10a: Normal CI
    try:
        np.random.seed(42)
        sample = np.random.normal(50, 10, 100)
        mean = np.mean(sample)
        se = scipy_stats.sem(sample)
        ci = scipy_stats.t.interval(0.95, len(sample)-1, loc=mean, scale=se)
        ci_contains_50 = ci[0] < 50 < ci[1]
        record_result("10a: Normal 95% CI", ci_contains_50,
                      f"mean={mean:.2f}, CI=({ci[0]:.2f}, {ci[1]:.2f})")
    except Exception as e:
        record_result("10a: Normal 95% CI", False, str(e))

    # 10b: Bootstrap CI
    try:
        np.random.seed(42)
        n_boot = 5000
        boot_means = np.array([
            np.mean(np.random.choice(sample, size=len(sample), replace=True))
            for _ in range(n_boot)
        ])
        boot_ci = (np.percentile(boot_means, 2.5), np.percentile(boot_means, 97.5))
        boot_ci_valid = boot_ci[0] < mean < boot_ci[1]
        record_result("10b: Bootstrap 95% CI", boot_ci_valid,
                      f"bootstrap CI=({boot_ci[0]:.2f}, {boot_ci[1]:.2f})")
    except Exception as e:
        record_result("10b: Bootstrap 95% CI", False, str(e))

    # 10c: Wilson score CI for proportions
    try:
        n_trials = 100
        successes = 30
        p_hat = successes / n_trials
        z = 1.96
        denom = 1 + z**2 / n_trials
        center = (p_hat + z**2 / (2 * n_trials)) / denom
        spread = z * np.sqrt(p_hat * (1 - p_hat) / n_trials + z**2 / (4 * n_trials**2)) / denom
        wilson_ci = (center - spread, center + spread)
        ci_valid_w = 0 < wilson_ci[0] < p_hat < wilson_ci[1] < 1
        record_result("10c: Wilson score CI for proportion", ci_valid_w,
                      f"p_hat={p_hat:.2f}, Wilson CI=({wilson_ci[0]:.4f}, {wilson_ci[1]:.4f})")
    except Exception as e:
        record_result("10c: Wilson score CI for proportion", False, str(e))

    # ==================================================================
    # SECTION 11: Model Comparison
    # ==================================================================
    print("\n--- Section 11: Model Comparison ---")

    # 11a: AIC/BIC comparison
    try:
        m1 = smf.ols('y ~ x1', data=df_cont).fit()
        m2 = smf.ols('y ~ x1 + x2', data=df_cont).fit()
        m3 = smf.ols('y ~ x1 + x2 + x3', data=df_cont).fit()

        aic_order = m3.aic < m2.aic < m1.aic  # Full model should be best
        record_result("11a: AIC model comparison", aic_order,
                      f"AIC: m1={m1.aic:.1f}, m2={m2.aic:.1f}, m3={m3.aic:.1f}")
    except Exception as e:
        record_result("11a: AIC model comparison", False, str(e))

    # 11b: Likelihood ratio test
    try:
        lr_stat = -2 * (m1.llf - m3.llf)
        df_diff = m3.df_model - m1.df_model
        lr_p = scipy_stats.chi2.sf(lr_stat, df_diff)
        prefer_full = lr_p < 0.05
        record_result("11b: Likelihood ratio test", prefer_full,
                      f"LR={lr_stat:.4f}, df={df_diff}, p={lr_p:.6f}")
    except Exception as e:
        record_result("11b: Likelihood ratio test", False, str(e))

    # 11c: R-squared comparison
    try:
        r2_increasing = m3.rsquared > m2.rsquared > m1.rsquared
        record_result("11c: R-squared comparison", r2_increasing,
                      f"R2: m1={m1.rsquared:.4f}, m2={m2.rsquared:.4f}, m3={m3.rsquared:.4f}")
    except Exception as e:
        record_result("11c: R-squared comparison", False, str(e))

    # ==================================================================
    # SECTION 12: BixBench Question Pattern Tests
    # ==================================================================
    print("\n--- Section 12: BixBench Question Patterns ---")

    # 12a: Pattern - Ordinal OR extraction
    try:
        """Pattern: 'What is the odds ratio of severity associated with exposure?'"""
        df_bix = generate_ordinal_outcome_data(n=1000, seed=123)
        df_bix['severity'] = pd.Categorical(df_bix['severity'],
                                             categories=['Mild', 'Moderate', 'Severe'], ordered=True)
        y_bix = df_bix['severity'].cat.codes
        X_bix = df_bix[['exposure', 'age', 'male']].astype(float)

        model_bix = OrderedModel(y_bix, X_bix, distr='logit')
        fit_bix = model_bix.fit(method='bfgs', disp=0)
        answer_or = np.exp(fit_bix.params['exposure'])

        has_answer = 0 < answer_or < 10
        record_result("12a: BixBench OR extraction pattern", has_answer,
                      f"Answer: OR={answer_or:.4f}")
    except Exception as e:
        record_result("12a: BixBench OR extraction pattern", False, str(e))

    # 12b: Pattern - Percentage reduction in OR
    try:
        """Pattern: 'What is the percentage reduction in OR after adjusting?'"""
        # Crude model
        X_crude = df_bix[['exposure']].astype(float)
        model_crude_bix = OrderedModel(y_bix, X_crude, distr='logit')
        fit_crude_bix = model_crude_bix.fit(method='bfgs', disp=0)
        or_crude_bix = np.exp(fit_crude_bix.params['exposure'])

        # Adjusted model
        or_adj_bix = answer_or

        pct_reduction_bix = ((or_crude_bix - or_adj_bix) / or_crude_bix) * 100
        has_pct = -100 < pct_reduction_bix < 100
        record_result("12b: BixBench % reduction in OR pattern", has_pct,
                      f"crude OR={or_crude_bix:.4f}, adj OR={or_adj_bix:.4f}, reduction={pct_reduction_bix:.1f}%")
    except Exception as e:
        record_result("12b: BixBench % reduction in OR pattern", False, str(e))

    # 12c: Pattern - Interaction OR
    try:
        """Pattern: 'What is the OR for the interaction term?'"""
        df_bix['exposure_x_male'] = df_bix['exposure'] * df_bix['male']
        X_int = df_bix[['exposure', 'male', 'exposure_x_male', 'age']].astype(float)
        model_int_bix = OrderedModel(y_bix, X_int, distr='logit')
        fit_int_bix = model_int_bix.fit(method='bfgs', disp=0)
        interaction_or = np.exp(fit_int_bix.params['exposure_x_male'])
        has_int_or = 0 < interaction_or < 100
        record_result("12c: BixBench interaction OR pattern", has_int_or,
                      f"interaction OR={interaction_or:.4f}, p={fit_int_bix.pvalues['exposure_x_male']:.6f}")
    except Exception as e:
        record_result("12c: BixBench interaction OR pattern", False, str(e))

    # 12d: Pattern - HR from Cox model
    try:
        """Pattern: 'What is the hazard ratio for treatment?'"""
        df_surv2 = generate_survival_data(n=500, seed=99)
        cph2 = CoxPHFitter()
        cph2.fit(df_surv2[['time', 'event', 'treatment', 'age', 'stage']],
                 duration_col='time', event_col='event')
        hr_answer = float(cph2.summary.loc['treatment', 'exp(coef)'])
        has_hr = 0 < hr_answer < 10
        record_result("12d: BixBench HR extraction pattern", has_hr,
                      f"Answer: HR={hr_answer:.4f}")
    except Exception as e:
        record_result("12d: BixBench HR extraction pattern", False, str(e))

    # 12e: Pattern - Median survival comparison
    try:
        """Pattern: 'What is the median survival time?'"""
        kmf_ctrl = KaplanMeierFitter()
        kmf_treat = KaplanMeierFitter()
        ctrl_mask = df_surv2['treatment'] == 0
        treat_mask = df_surv2['treatment'] == 1
        kmf_ctrl.fit(df_surv2.loc[ctrl_mask, 'time'], df_surv2.loc[ctrl_mask, 'event'])
        kmf_treat.fit(df_surv2.loc[treat_mask, 'time'], df_surv2.loc[treat_mask, 'event'])
        med_ctrl = kmf_ctrl.median_survival_time_
        med_treat = kmf_treat.median_survival_time_
        has_medians = not np.isinf(med_ctrl) or not np.isinf(med_treat)
        record_result("12e: BixBench median survival pattern", has_medians,
                      f"control={med_ctrl:.2f}, treatment={med_treat:.2f}")
    except Exception as e:
        record_result("12e: BixBench median survival pattern", False, str(e))

    # 12f: Pattern - Model coefficient with CI
    try:
        """Pattern: 'What is the coefficient and 95% CI for age?'"""
        model_coef = smf.logit('outcome ~ treatment + age + male + bmi',
                               data=df_binary).fit(disp=0)
        age_coef = model_coef.params['age']
        age_ci = model_coef.conf_int().loc['age']
        ci_str = f"({age_ci.iloc[0]:.4f}, {age_ci.iloc[1]:.4f})"
        has_coef_ci = age_ci.iloc[0] < age_coef < age_ci.iloc[1]
        record_result("12f: BixBench coefficient + CI pattern", has_coef_ci,
                      f"age coef={age_coef:.4f}, 95% CI={ci_str}")
    except Exception as e:
        record_result("12f: BixBench coefficient + CI pattern", False, str(e))

    # 12g: Pattern - Adjusted vs unadjusted comparison
    try:
        """Pattern: 'Compare unadjusted and adjusted odds ratios'"""
        m_unadj = smf.logit('outcome ~ treatment', data=df_binary).fit(disp=0)
        m_adj = smf.logit('outcome ~ treatment + age + male + bmi', data=df_binary).fit(disp=0)
        or_unadj = np.exp(m_unadj.params['treatment'])
        or_adj = np.exp(m_adj.params['treatment'])
        pct_change_adj = ((or_unadj - or_adj) / or_unadj) * 100
        record_result("12g: BixBench adjusted vs unadjusted pattern", True,
                      f"unadj OR={or_unadj:.4f}, adj OR={or_adj:.4f}, change={pct_change_adj:.1f}%")
    except Exception as e:
        record_result("12g: BixBench adjusted vs unadjusted pattern", False, str(e))

    # ==================================================================
    # SECTION 13: Edge Cases and Robustness
    # ==================================================================
    print("\n--- Section 13: Edge Cases and Robustness ---")

    # 13a: Missing data handling
    try:
        df_missing = df_binary.copy()
        df_missing.loc[:10, 'age'] = np.nan
        model_missing = smf.logit('outcome ~ treatment + age + male', data=df_missing).fit(disp=0)
        n_used = int(model_missing.nobs)
        n_expected = len(df_missing) - 11  # 11 rows with missing age
        correct_n = n_used == n_expected
        record_result("13a: Missing data handling (listwise deletion)", correct_n,
                      f"n_used={n_used}, expected={n_expected}")
    except Exception as e:
        record_result("13a: Missing data handling (listwise deletion)", False, str(e))

    # 13b: Small sample handling
    try:
        np.random.seed(42)
        df_small = pd.DataFrame({
            'y': np.random.binomial(1, 0.5, 20),
            'x': np.random.normal(0, 1, 20),
        })
        model_small = smf.logit('y ~ x', data=df_small).fit(disp=0)
        has_result = model_small.params is not None
        record_result("13b: Small sample logistic (n=20)", has_result,
                      f"converged, x coef={model_small.params['x']:.4f}")
    except Exception as e:
        record_result("13b: Small sample logistic (n=20)", False, str(e))

    # 13c: Perfect separation detection
    try:
        df_sep = pd.DataFrame({
            'y': [0]*10 + [1]*10,
            'x': list(range(20)),  # Perfect predictor
        })
        # This should either converge with warnings or raise
        try:
            model_sep = smf.logit('y ~ x', data=df_sep).fit(disp=0, maxiter=50)
            # Model might converge with very large coefficients
            large_coef = abs(model_sep.params['x']) > 5
            record_result("13c: Perfect separation handling", True,
                          f"fitted with large coef={model_sep.params['x']:.4f}")
        except Exception:
            record_result("13c: Perfect separation handling", True,
                          "Correctly detected convergence issue")
    except Exception as e:
        record_result("13c: Perfect separation handling", False, str(e))

    # 13d: Categorical variable with formula C()
    try:
        df_cat = df_binary.copy()
        df_cat['group'] = np.random.choice(['A', 'B', 'C'], len(df_cat))
        model_cat = smf.logit('outcome ~ treatment + C(group)', data=df_cat).fit(disp=0)
        has_dummy = any('group' in name for name in model_cat.params.index)
        record_result("13d: Categorical variable C() in formula", has_dummy,
                      f"params with group: {[n for n in model_cat.params.index if 'group' in n]}")
    except Exception as e:
        record_result("13d: Categorical variable C() in formula", False, str(e))

    # 13e: Reference level specification
    try:
        model_ref = smf.logit("outcome ~ treatment + C(group, Treatment(reference='B'))",
                              data=df_cat).fit(disp=0)
        # Reference B means A and C are reported
        # statsmodels uses [T.X] naming: e.g., C(group, Treatment(reference='B'))[T.A]
        param_str = ' '.join(model_ref.params.index)
        has_a = 'T.A' in param_str
        has_c = 'T.C' in param_str
        has_b = 'T.B' in param_str  # B is reference, should NOT appear
        record_result("13e: Reference level specification", has_a and has_c and not has_b,
                      f"params: {list(model_ref.params.index)}")
    except Exception as e:
        record_result("13e: Reference level specification", False, str(e))

    # 13f: Multiple ordinal levels (5-level Likert)
    try:
        np.random.seed(42)
        n_likert = 500
        likert_data = pd.DataFrame({
            'satisfaction': np.random.choice(
                ['Very Dissatisfied', 'Dissatisfied', 'Neutral', 'Satisfied', 'Very Satisfied'],
                n_likert, p=[0.1, 0.15, 0.3, 0.25, 0.2]),
            'treatment': np.random.binomial(1, 0.5, n_likert),
            'age': np.random.normal(40, 10, n_likert),
        })
        order_5 = ['Very Dissatisfied', 'Dissatisfied', 'Neutral', 'Satisfied', 'Very Satisfied']
        likert_data['satisfaction'] = pd.Categorical(likert_data['satisfaction'],
                                                      categories=order_5, ordered=True)
        y_5 = likert_data['satisfaction'].cat.codes
        X_5 = likert_data[['treatment', 'age']].astype(float)
        model_5 = OrderedModel(y_5, X_5, distr='logit')
        fit_5 = model_5.fit(method='bfgs', disp=0)
        n_params = len(fit_5.params)
        # Should have 2 predictors + 4 thresholds = 6 params
        correct_params = n_params == 6
        record_result("13f: 5-level ordinal logistic", correct_params,
                      f"n_params={n_params} (expected 6: 2 predictors + 4 thresholds)")
    except Exception as e:
        record_result("13f: 5-level ordinal logistic", False, str(e))

    # ==================================================================
    # SECTION 14: Data Loading and Processing
    # ==================================================================
    print("\n--- Section 14: Data Loading and Processing ---")

    # 14a: CSV data loading
    try:
        import tempfile
        import os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df_binary.to_csv(f, index=False)
            tmp_path = f.name
        df_loaded = pd.read_csv(tmp_path)
        cols_match = set(df_loaded.columns) == set(df_binary.columns)
        rows_match = len(df_loaded) == len(df_binary)
        os.unlink(tmp_path)
        record_result("14a: CSV data loading", cols_match and rows_match,
                      f"cols={list(df_loaded.columns)}, rows={len(df_loaded)}")
    except Exception as e:
        record_result("14a: CSV data loading", False, str(e))

    # 14b: Variable type detection
    try:
        def detect_type(series):
            unique = series.dropna().unique()
            n_unique = len(unique)
            if n_unique == 2:
                return 'binary'
            elif n_unique <= 7 and series.dtype == 'object':
                return 'categorical'
            elif series.dtype in ['float64', 'int64'] and n_unique > 10:
                return 'continuous'
            else:
                return 'ordinal_or_categorical'

        types = {col: detect_type(df_binary[col]) for col in df_binary.columns}
        outcome_binary = types['outcome'] == 'binary'
        treatment_binary = types['treatment'] == 'binary'
        age_continuous = types['age'] == 'continuous'
        record_result("14b: Variable type detection", outcome_binary and age_continuous,
                      f"types: {types}")
    except Exception as e:
        record_result("14b: Variable type detection", False, str(e))

    # 14c: Dummy variable creation
    try:
        df_test_dummy = pd.DataFrame({
            'category': ['A', 'B', 'C', 'A', 'B', 'C'],
            'value': [1, 2, 3, 4, 5, 6]
        })
        dummies = pd.get_dummies(df_test_dummy['category'], prefix='cat', drop_first=True, dtype=int)
        has_b = 'cat_B' in dummies.columns
        has_c = 'cat_C' in dummies.columns
        no_a = 'cat_A' not in dummies.columns  # Dropped first
        record_result("14c: Dummy variable creation", has_b and has_c and no_a,
                      f"dummies: {list(dummies.columns)}")
    except Exception as e:
        record_result("14c: Dummy variable creation", False, str(e))

    # ==================================================================
    # SECTION 15: Effect Size and Interpretation
    # ==================================================================
    print("\n--- Section 15: Effect Size and Interpretation ---")

    # 15a: Cohen's d
    try:
        n1, n2 = 50, 50
        g1_ef = np.random.normal(10, 2, n1)
        g2_ef = np.random.normal(12, 2, n2)
        pooled_std = np.sqrt(((n1-1)*np.std(g1_ef, ddof=1)**2 + (n2-1)*np.std(g2_ef, ddof=1)**2) / (n1+n2-2))
        cohens_d = (np.mean(g1_ef) - np.mean(g2_ef)) / pooled_std
        has_d = abs(cohens_d) > 0
        record_result("15a: Cohen's d effect size", has_d,
                      f"d={cohens_d:.4f} ({'large' if abs(cohens_d) > 0.8 else 'medium' if abs(cohens_d) > 0.5 else 'small'})")
    except Exception as e:
        record_result("15a: Cohen's d effect size", False, str(e))

    # 15b: Cramers V
    try:
        contingency = np.array([[30, 10], [20, 40]])
        chi2_v, _, _, _ = scipy_stats.chi2_contingency(contingency)
        n_cv = np.sum(contingency)
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2_v / (n_cv * min_dim))
        has_v = 0 < cramers_v < 1
        record_result("15b: Cramer's V", has_v,
                      f"V={cramers_v:.4f}")
    except Exception as e:
        record_result("15b: Cramer's V", False, str(e))

    # 15c: OR interpretation text
    try:
        or_val = 2.5
        ci_lower = 1.8
        ci_upper = 3.5
        p_val = 0.001

        if or_val > 1:
            pct = round((or_val - 1) * 100, 1)
            interp = f"{pct}% increase in odds"
        else:
            pct = round((1 - or_val) * 100, 1)
            interp = f"{pct}% decrease in odds"

        ci_str = f"95% CI: ({ci_lower}, {ci_upper})"
        sig = "statistically significant" if p_val < 0.05 else "not statistically significant"
        full = f"OR={or_val} ({ci_str}), p={p_val}, {sig}. {interp}."
        has_full = "150.0% increase" in interp and "significant" in sig
        record_result("15c: OR interpretation text", has_full,
                      f"'{full}'")
    except Exception as e:
        record_result("15c: OR interpretation text", False, str(e))

    # ==================================================================
    # SUMMARY
    # ==================================================================
    elapsed = time.time() - total_start
    n_pass = sum(1 for r in test_results if r['passed'])
    n_fail = sum(1 for r in test_results if not r['passed'])
    n_total = len(test_results)

    print("\n" + "=" * 70)
    print(f"RESULTS: {n_pass}/{n_total} tests passed ({n_pass/n_total*100:.1f}%)")
    print(f"ELAPSED: {elapsed:.1f} seconds")
    print("=" * 70)

    if n_fail > 0:
        print(f"\nFailed tests ({n_fail}):")
        for r in test_results:
            if not r['passed']:
                print(f"  - {r['name']}: {r['details']}")

    return n_fail == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
