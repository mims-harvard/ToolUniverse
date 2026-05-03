#!/usr/bin/env python3
"""
Automated Model Diagnostics

Comprehensive automated diagnostic testing for regression models.
Checks assumptions and provides actionable recommendations.

Usage:
    from model_diagnostics import run_ols_diagnostics, run_cox_diagnostics

Example:
    model = smf.ols('outcome ~ x + z', data=df).fit()
    diagnostics = run_ols_diagnostics(model, df)
    print_diagnostic_report(diagnostics)
"""

import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from typing import Dict, Any, List, Optional
import warnings


def run_ols_diagnostics(model, data: pd.DataFrame) -> Dict[str, Any]:
    """
    Run comprehensive diagnostics for OLS linear regression.

    Args:
        model: Fitted statsmodels OLS model
        data: Original dataframe used for fitting

    Returns:
        Dict with diagnostic results and recommendations
    """
    diagnostics = {
        'model_type': 'OLS',
        'n_obs': int(model.nobs),
        'n_predictors': model.df_model,
        'tests': {},
        'warnings': [],
        'recommendations': []
    }

    # 1. Residual Normality (Shapiro-Wilk)
    residuals = model.resid
    if len(residuals) <= 5000:
        sw_stat, sw_p = scipy_stats.shapiro(residuals)
        diagnostics['tests']['shapiro_wilk'] = {
            'statistic': round(sw_stat, 4),
            'p_value': round(sw_p, 6),
            'normal': sw_p > 0.05
        }
        if sw_p < 0.05:
            diagnostics['warnings'].append(
                "Residuals not normally distributed (Shapiro-Wilk p < 0.05)"
            )
            diagnostics['recommendations'].append(
                "Consider: log transformation, robust regression, or bootstrapped CIs"
            )
    else:
        diagnostics['warnings'].append(
            "Sample too large for Shapiro-Wilk test (n > 5000)"
        )

    # 2. Heteroscedasticity (Breusch-Pagan)
    try:
        from statsmodels.stats.diagnostic import het_breuschpagan
        bp_stat, bp_p, _, _ = het_breuschpagan(residuals, model.model.exog)
        diagnostics['tests']['breusch_pagan'] = {
            'statistic': round(bp_stat, 4),
            'p_value': round(bp_p, 6),
            'homoscedastic': bp_p > 0.05
        }
        if bp_p < 0.05:
            diagnostics['warnings'].append(
                "Heteroscedasticity detected (Breusch-Pagan p < 0.05)"
            )
            diagnostics['recommendations'].append(
                "Consider: robust standard errors (HC3), WLS, or log transformation"
            )
    except Exception as e:
        diagnostics['warnings'].append(f"Could not run Breusch-Pagan test: {e}")

    # 3. Autocorrelation (Durbin-Watson)
    try:
        from statsmodels.stats.stattools import durbin_watson
        dw = durbin_watson(residuals)
        diagnostics['tests']['durbin_watson'] = {
            'statistic': round(dw, 4),
            'no_autocorr': 1.5 < dw < 2.5
        }
        if not (1.5 < dw < 2.5):
            diagnostics['warnings'].append(
                f"Possible autocorrelation (Durbin-Watson = {dw:.4f})"
            )
            diagnostics['recommendations'].append(
                "Consider: time series methods or GEE for clustered data"
            )
    except Exception as e:
        diagnostics['warnings'].append(f"Could not run Durbin-Watson test: {e}")

    # 4. Multicollinearity (VIF)
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        X = model.model.exog
        vif_data = {}
        high_vif = []

        for i in range(X.shape[1]):
            var_name = model.model.exog_names[i]
            if var_name != 'Intercept':
                vif = variance_inflation_factor(X, i)
                vif_data[var_name] = round(vif, 2)
                if vif > 10:
                    high_vif.append(f"{var_name} (VIF={vif:.2f})")

        diagnostics['tests']['vif'] = vif_data

        if high_vif:
            diagnostics['warnings'].append(
                f"High multicollinearity detected: {', '.join(high_vif)}"
            )
            diagnostics['recommendations'].append(
                "Consider: removing correlated predictors, Ridge regression, or PCA"
            )
    except Exception as e:
        diagnostics['warnings'].append(f"Could not compute VIF: {e}")

    # 5. Influential Observations
    try:
        influence = model.get_influence()
        cooks_d = influence.cooks_distance[0]
        influential_threshold = 4 / len(data)
        n_influential = (cooks_d > influential_threshold).sum()

        diagnostics['tests']['influential_obs'] = {
            'n_influential': int(n_influential),
            'threshold': round(influential_threshold, 6)
        }

        if n_influential > len(data) * 0.05:  # > 5% influential
            diagnostics['warnings'].append(
                f"{n_influential} influential observations detected (>5% of data)"
            )
            diagnostics['recommendations'].append(
                "Consider: robust regression, investigate outliers"
            )
    except Exception as e:
        diagnostics['warnings'].append(f"Could not assess influential points: {e}")

    # 6. Sample Size Adequacy
    obs_per_predictor = diagnostics['n_obs'] / max(diagnostics['n_predictors'], 1)
    if obs_per_predictor < 20:
        diagnostics['warnings'].append(
            f"Small sample size ({obs_per_predictor:.1f} obs per predictor)"
        )
        diagnostics['recommendations'].append(
            "Recommended: ≥20 observations per predictor for stable estimates"
        )

    # Overall assessment
    if len(diagnostics['warnings']) == 0:
        diagnostics['overall'] = "✅ All diagnostic checks passed"
    else:
        diagnostics['overall'] = f"⚠️ {len(diagnostics['warnings'])} diagnostic warnings"

    return diagnostics


def run_logistic_diagnostics(model, data: pd.DataFrame) -> Dict[str, Any]:
    """
    Run diagnostics for logistic regression.

    Args:
        model: Fitted statsmodels Logit model
        data: Original dataframe

    Returns:
        Dict with diagnostic results
    """
    diagnostics = {
        'model_type': 'Logistic',
        'n_obs': int(model.nobs),
        'n_predictors': model.df_model,
        'tests': {},
        'warnings': [],
        'recommendations': []
    }

    # 1. Check for separation
    outcome = data[model.model.endog_names]
    predictors = data[model.model.exog_names]

    # Check if any predictor perfectly separates outcome
    separation_detected = False
    for pred in predictors.columns:
        if pred != 'Intercept':
            crosstab = pd.crosstab(data[pred], outcome)
            if (crosstab == 0).any().any():
                diagnostics['warnings'].append(
                    f"Possible separation with predictor: {pred}"
                )
                separation_detected = True

    if separation_detected:
        diagnostics['recommendations'].append(
            "Consider: Firth logistic regression, removing problematic predictors"
        )

    # 2. Large coefficients (indicator of quasi-separation)
    large_coefs = []
    for var, coef in model.params.items():
        if abs(coef) > 10:
            large_coefs.append(f"{var} (β={coef:.2f})")

    if large_coefs:
        diagnostics['warnings'].append(
            f"Very large coefficients: {', '.join(large_coefs)}"
        )
        diagnostics['recommendations'].append(
            "Check for quasi-complete separation or convergence issues"
        )

    # 3. Sample size (events per predictor)
    n_events = outcome.sum()
    events_per_predictor = n_events / max(diagnostics['n_predictors'], 1)

    diagnostics['tests']['sample_size'] = {
        'n_events': int(n_events),
        'events_per_predictor': round(events_per_predictor, 1)
    }

    if events_per_predictor < 10:
        diagnostics['warnings'].append(
            f"Small sample size ({events_per_predictor:.1f} events per predictor)"
        )
        diagnostics['recommendations'].append(
            "Recommended: ≥10 events per predictor for stable estimates"
        )

    # 4. Multicollinearity
    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        X = model.model.exog
        vif_data = {}
        high_vif = []

        for i in range(X.shape[1]):
            var_name = model.model.exog_names[i]
            if var_name != 'Intercept':
                vif = variance_inflation_factor(X, i)
                vif_data[var_name] = round(vif, 2)
                if vif > 10:
                    high_vif.append(f"{var_name} (VIF={vif:.2f})")

        diagnostics['tests']['vif'] = vif_data

        if high_vif:
            diagnostics['warnings'].append(
                f"High multicollinearity: {', '.join(high_vif)}"
            )
    except Exception as e:
        pass

    # Overall
    if len(diagnostics['warnings']) == 0:
        diagnostics['overall'] = "✅ All diagnostic checks passed"
    else:
        diagnostics['overall'] = f"⚠️ {len(diagnostics['warnings'])} diagnostic warnings"

    return diagnostics


def run_cox_diagnostics(cph, data: pd.DataFrame) -> Dict[str, Any]:
    """
    Run diagnostics for Cox proportional hazards model.

    Args:
        cph: Fitted CoxPHFitter model
        data: Original dataframe

    Returns:
        Dict with diagnostic results
    """
    diagnostics = {
        'model_type': 'Cox PH',
        'n_obs': len(data),
        'n_events': int(cph.event_observed.sum()),
        'tests': {},
        'warnings': [],
        'recommendations': []
    }

    # 1. Proportional Hazards Assumption
    try:
        ph_results = cph.check_assumptions(data, p_value_threshold=0.05,
                                           show_plots=False)
        if len(ph_results) > 0:
            diagnostics['warnings'].append(
                f"PH assumption violated for: {ph_results}"
            )
            diagnostics['recommendations'].append(
                "Consider: stratification, time-varying coefficients, or AFT model"
            )
        diagnostics['tests']['proportional_hazards'] = {
            'violated': len(ph_results) > 0,
            'variables': list(ph_results) if len(ph_results) > 0 else []
        }
    except Exception as e:
        diagnostics['warnings'].append(f"Could not test PH assumption: {e}")

    # 2. Concordance Index
    c_index = cph.concordance_index_
    diagnostics['tests']['concordance'] = round(c_index, 4)

    if c_index < 0.6:
        diagnostics['warnings'].append(
            f"Poor discrimination (C-index = {c_index:.4f})"
        )
        diagnostics['recommendations'].append(
            "Consider: adding predictors or checking for non-proportional hazards"
        )

    # 3. Sample Size (events per predictor)
    n_predictors = len(cph.params_)
    events_per_predictor = diagnostics['n_events'] / max(n_predictors, 1)

    diagnostics['tests']['sample_size'] = {
        'n_predictors': n_predictors,
        'events_per_predictor': round(events_per_predictor, 1)
    }

    if events_per_predictor < 10:
        diagnostics['warnings'].append(
            f"Small sample size ({events_per_predictor:.1f} events per predictor)"
        )
        diagnostics['recommendations'].append(
            "Recommended: ≥10 events per predictor for stable estimates"
        )

    # Overall
    if len(diagnostics['warnings']) == 0:
        diagnostics['overall'] = "✅ All diagnostic checks passed"
    else:
        diagnostics['overall'] = f"⚠️ {len(diagnostics['warnings'])} diagnostic warnings"

    return diagnostics


def print_diagnostic_report(diagnostics: Dict[str, Any]):
    """
    Print formatted diagnostic report.

    Args:
        diagnostics: Results from run_*_diagnostics()
    """
    print("=" * 60)
    print(f"DIAGNOSTIC REPORT - {diagnostics['model_type']}")
    print("=" * 60)

    print(f"\n{diagnostics['overall']}\n")

    # Basic info
    print("Model Information:")
    print(f"  N observations: {diagnostics.get('n_obs', '-')}")
    if 'n_events' in diagnostics:
        print(f"  N events: {diagnostics['n_events']}")
    if 'n_predictors' in diagnostics:
        print(f"  N predictors: {diagnostics['n_predictors']}")

    # Test results
    if diagnostics['tests']:
        print("\nDiagnostic Tests:")
        for test_name, result in diagnostics['tests'].items():
            print(f"\n  {test_name.replace('_', ' ').title()}:")
            if isinstance(result, dict):
                for key, val in result.items():
                    print(f"    {key}: {val}")
            else:
                print(f"    Result: {result}")

    # Warnings
    if diagnostics['warnings']:
        print("\n⚠️  Warnings:")
        for i, warning in enumerate(diagnostics['warnings'], 1):
            print(f"  {i}. {warning}")

    # Recommendations
    if diagnostics['recommendations']:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(diagnostics['recommendations'], 1):
            print(f"  {i}. {rec}")

    print("\n" + "=" * 60)


def quick_diagnostic_check(model, data: pd.DataFrame, model_type: str = 'auto'):
    """
    Quick diagnostic check with automatic model type detection.

    Args:
        model: Fitted model
        data: Original dataframe
        model_type: 'ols', 'logistic', 'cox', or 'auto'

    Returns:
        Diagnostic results dict
    """
    # Auto-detect model type
    if model_type == 'auto':
        model_class = model.__class__.__name__
        if 'OLS' in model_class:
            model_type = 'ols'
        elif 'Logit' in model_class:
            model_type = 'logistic'
        elif 'CoxPH' in model_class:
            model_type = 'cox'
        else:
            raise ValueError(f"Cannot auto-detect model type: {model_class}")

    # Run appropriate diagnostics
    if model_type == 'ols':
        diagnostics = run_ols_diagnostics(model, data)
    elif model_type == 'logistic':
        diagnostics = run_logistic_diagnostics(model, data)
    elif model_type == 'cox':
        diagnostics = run_cox_diagnostics(model, data)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    print_diagnostic_report(diagnostics)
    return diagnostics


# Example usage
if __name__ == "__main__":
    print("Model Diagnostics Utilities")
    print("=" * 60)
    print("\nExample usage:")
    print("""
    # OLS diagnostics
    model = smf.ols('outcome ~ x + z', data=df).fit()
    diagnostics = run_ols_diagnostics(model, df)
    print_diagnostic_report(diagnostics)

    # Logistic diagnostics
    model = smf.logit('disease ~ exposure + age', data=df).fit(disp=0)
    diagnostics = run_logistic_diagnostics(model, df)
    print_diagnostic_report(diagnostics)

    # Cox diagnostics
    cph = CoxPHFitter()
    cph.fit(df, duration_col='time', event_col='event')
    diagnostics = run_cox_diagnostics(cph, df)
    print_diagnostic_report(diagnostics)

    # Auto-detect and run
    quick_diagnostic_check(model, df)
    """)
