#!/usr/bin/env python3
"""
Format Statistical Output for Publication

Utility functions to format statistical results in publication-ready format.
Supports OLS, logistic, ordinal logit, Cox models, and more.

Usage:
    from format_statistical_output import format_regression_table, format_hr_table, format_or_table

Example:
    model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)
    table = format_or_table(model)
    print(table)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional


def format_regression_table(model, outcome_name: str = "Outcome",
                            model_type: str = "Linear") -> str:
    """
    Format linear/logistic regression results as publication table.

    Args:
        model: Fitted statsmodels model
        outcome_name: Name of outcome variable
        model_type: "Linear", "Logistic", or "Ordinal"

    Returns:
        Formatted table string (markdown format)
    """
    lines = []
    lines.append(f"# {model_type} Regression Results")
    lines.append(f"**Outcome**: {outcome_name}\n")

    # Model fit
    lines.append("## Model Fit")
    lines.append(f"- N = {int(model.nobs)}")

    if hasattr(model, 'rsquared'):
        lines.append(f"- R² = {model.rsquared:.4f}")
        lines.append(f"- Adjusted R² = {model.rsquared_adj:.4f}")
    elif hasattr(model, 'prsquared'):
        lines.append(f"- Pseudo R² = {model.prsquared:.4f}")

    if hasattr(model, 'aic'):
        lines.append(f"- AIC = {model.aic:.2f}")
    if hasattr(model, 'bic'):
        lines.append(f"- BIC = {model.bic:.2f}")

    lines.append("")

    # Coefficients table
    lines.append("## Coefficients")
    lines.append("")
    lines.append("| Variable | Estimate | SE | t/z | p-value | 95% CI | Sig |")
    lines.append("|----------|----------|----|----|---------|--------|-----|")

    for var in model.params.index:
        coef = model.params[var]
        se = model.bse[var]
        t_z = model.tvalues[var]
        p_val = model.pvalues[var]
        ci = model.conf_int().loc[var]

        # Significance stars
        if p_val < 0.001:
            sig = "***"
        elif p_val < 0.01:
            sig = "**"
        elif p_val < 0.05:
            sig = "*"
        else:
            sig = ""

        lines.append(
            f"| {var} | {coef:.4f} | {se:.4f} | {t_z:.4f} | "
            f"{p_val:.6f} | ({ci[0]:.4f}, {ci[1]:.4f}) | {sig} |"
        )

    lines.append("")
    lines.append("*p < 0.05, **p < 0.01, ***p < 0.001")

    return "\n".join(lines)


def format_or_table(model, outcome_name: str = "Outcome") -> str:
    """
    Format odds ratios table from logistic/ordinal regression.

    Args:
        model: Fitted logistic model
        outcome_name: Name of outcome variable

    Returns:
        Formatted OR table (markdown)
    """
    lines = []
    lines.append(f"# Odds Ratios - {outcome_name}")
    lines.append("")

    # Model info
    lines.append(f"**N** = {int(model.nobs)}")
    if hasattr(model, 'prsquared'):
        lines.append(f"**Pseudo R²** = {model.prsquared:.4f}")
    lines.append("")

    # OR table
    lines.append("| Variable | OR | 95% CI | p-value | Interpretation |")
    lines.append("|----------|-----|--------|---------|----------------|")

    # Extract relevant parameters (skip thresholds for ordinal)
    params_to_show = []
    for i, var in enumerate(model.params.index):
        if 'Intercept' in var or var.startswith('threshold'):
            continue
        params_to_show.append(var)

    for var in params_to_show:
        coef = model.params[var]
        or_val = np.exp(coef)
        ci = np.exp(model.conf_int().loc[var])
        p_val = model.pvalues[var]

        # Interpretation
        if or_val > 1:
            pct = (or_val - 1) * 100
            interp = f"{pct:.1f}% ↑ odds"
        elif or_val < 1:
            pct = (1 - or_val) * 100
            interp = f"{pct:.1f}% ↓ odds"
        else:
            interp = "No effect"

        sig = "*" if p_val < 0.05 else ""

        lines.append(
            f"| {var} | {or_val:.4f} | ({ci[0]:.4f}, {ci[1]:.4f}) | "
            f"{p_val:.6f}{sig} | {interp} |"
        )

    return "\n".join(lines)


def format_hr_table(cph, outcome_name: str = "Event") -> str:
    """
    Format hazard ratios table from Cox model.

    Args:
        cph: Fitted CoxPHFitter model
        outcome_name: Name of event

    Returns:
        Formatted HR table (markdown)
    """
    lines = []
    lines.append(f"# Hazard Ratios - Time to {outcome_name}")
    lines.append("")

    # Model info
    lines.append(f"**Events** = {int(cph.event_observed.sum())}/{len(cph.event_observed)}")
    lines.append(f"**Concordance** = {cph.concordance_index_:.4f}")
    if hasattr(cph, 'AIC_partial_'):
        lines.append(f"**AIC** = {cph.AIC_partial_:.2f}")
    lines.append("")

    # HR table
    lines.append("| Variable | HR | 95% CI | p-value | Interpretation |")
    lines.append("|----------|-----|--------|---------|----------------|")

    summary = cph.summary
    hrs = cph.hazard_ratios_

    for var in summary.index:
        hr = hrs[var]
        ci_lower = summary.loc[var, 'exp(coef) lower 95%']
        ci_upper = summary.loc[var, 'exp(coef) upper 95%']
        p_val = summary.loc[var, 'p']

        # Interpretation
        if hr > 1:
            pct = (hr - 1) * 100
            interp = f"{pct:.1f}% ↑ hazard"
        elif hr < 1:
            pct = (1 - hr) * 100
            interp = f"{pct:.1f}% ↓ hazard"
        else:
            interp = "No effect"

        sig = "*" if p_val < 0.05 else ""

        lines.append(
            f"| {var} | {hr:.4f} | ({ci_lower:.4f}, {ci_upper:.4f}) | "
            f"{p_val:.6f}{sig} | {interp} |"
        )

    return "\n".join(lines)


def format_comparison_table(models: Dict[str, Any],
                            criterion: str = "AIC") -> str:
    """
    Format model comparison table.

    Args:
        models: Dict of {model_name: fitted_model}
        criterion: "AIC" or "BIC"

    Returns:
        Formatted comparison table (markdown)
    """
    lines = []
    lines.append(f"# Model Comparison - {criterion}")
    lines.append("")
    lines.append("| Model | N | AIC | BIC | R²/Pseudo R² | Best |")
    lines.append("|-------|---|-----|-----|--------------|------|")

    results = []
    for name, model in models.items():
        entry = {'name': name}

        if hasattr(model, 'nobs'):
            entry['n'] = int(model.nobs)
        if hasattr(model, 'aic'):
            entry['aic'] = model.aic
        if hasattr(model, 'bic'):
            entry['bic'] = model.bic
        if hasattr(model, 'rsquared'):
            entry['r2'] = model.rsquared
        elif hasattr(model, 'prsquared'):
            entry['r2'] = model.prsquared

        results.append(entry)

    # Sort by criterion
    if criterion == "AIC":
        results.sort(key=lambda x: x.get('aic', float('inf')))
    else:
        results.sort(key=lambda x: x.get('bic', float('inf')))

    for i, entry in enumerate(results):
        best = "✓" if i == 0 else ""
        lines.append(
            f"| {entry['name']} | {entry.get('n', '-')} | "
            f"{entry.get('aic', '-'):.2f} | {entry.get('bic', '-'):.2f} | "
            f"{entry.get('r2', '-'):.4f} | {best} |"
        )

    return "\n".join(lines)


def format_diagnostic_summary(model, diagnostic_results: Dict[str, Any]) -> str:
    """
    Format diagnostic test results.

    Args:
        model: Fitted model
        diagnostic_results: Dict of diagnostic test results

    Returns:
        Formatted diagnostic summary (markdown)
    """
    lines = []
    lines.append("# Diagnostic Tests")
    lines.append("")

    # Shapiro-Wilk (normality)
    if 'shapiro_wilk' in diagnostic_results:
        sw = diagnostic_results['shapiro_wilk']
        lines.append("## Residual Normality (Shapiro-Wilk)")
        lines.append(f"- Statistic: {sw['statistic']:.4f}")
        lines.append(f"- p-value: {sw['p_value']:.6f}")
        if sw['p_value'] > 0.05:
            lines.append("- ✅ Residuals appear normally distributed")
        else:
            lines.append("- ⚠️ Residuals may not be normally distributed")
        lines.append("")

    # Breusch-Pagan (heteroscedasticity)
    if 'breusch_pagan' in diagnostic_results:
        bp = diagnostic_results['breusch_pagan']
        lines.append("## Homoscedasticity (Breusch-Pagan)")
        lines.append(f"- Statistic: {bp['statistic']:.4f}")
        lines.append(f"- p-value: {bp['p_value']:.6f}")
        if bp['p_value'] > 0.05:
            lines.append("- ✅ Homoscedasticity assumption met")
        else:
            lines.append("- ⚠️ Heteroscedasticity detected")
        lines.append("")

    # VIF (multicollinearity)
    if 'vif' in diagnostic_results:
        lines.append("## Multicollinearity (VIF)")
        lines.append("")
        lines.append("| Variable | VIF | Status |")
        lines.append("|----------|-----|--------|")
        for var, vif in diagnostic_results['vif'].items():
            status = "✅ OK" if vif < 10 else "⚠️ High"
            lines.append(f"| {var} | {vif:.2f} | {status} |")
        lines.append("")

    # Durbin-Watson (autocorrelation)
    if 'durbin_watson' in diagnostic_results:
        dw = diagnostic_results['durbin_watson']
        lines.append("## Autocorrelation (Durbin-Watson)")
        lines.append(f"- Statistic: {dw['statistic']:.4f}")
        lines.append(f"- {dw['interpretation']}")
        lines.append("")

    return "\n".join(lines)


def save_table_to_csv(table_string: str, output_file: str):
    """
    Convert markdown table to CSV.

    Args:
        table_string: Markdown formatted table
        output_file: Output CSV filename
    """
    # Parse markdown table
    lines = table_string.split('\n')
    table_lines = [l for l in lines if '|' in l and not l.startswith('|--')]

    # Convert to DataFrame
    rows = []
    for line in table_lines:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        rows.append(cells)

    df = pd.DataFrame(rows[1:], columns=rows[0])
    df.to_csv(output_file, index=False)
    print(f"Table saved to {output_file}")


# Example usage
if __name__ == "__main__":
    print("Statistical Output Formatting Utilities")
    print("=" * 50)
    print("\nExample usage:")
    print("""
    # Format logistic regression odds ratios
    model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)
    or_table = format_or_table(model, outcome_name="Disease Status")
    print(or_table)

    # Format Cox model hazard ratios
    cph = CoxPHFitter()
    cph.fit(df, duration_col='time', event_col='event')
    hr_table = format_hr_table(cph, outcome_name="Death")
    print(hr_table)

    # Compare multiple models
    models = {
        'Model 1': model1,
        'Model 2': model2,
        'Model 3': model3
    }
    comparison = format_comparison_table(models, criterion="AIC")
    print(comparison)
    """)
