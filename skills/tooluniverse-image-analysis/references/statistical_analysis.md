# Statistical Analysis for Imaging Data

Complete reference for statistical tests, effect sizes, power analysis, and regression modeling on microscopy measurement data.

---

## Table of Contents

1. [Descriptive Statistics](#descriptive-statistics)
2. [Normality Testing](#normality-testing)
3. [Two-Group Comparisons](#two-group-comparisons)
4. [Multiple Comparisons](#multiple-comparisons)
5. [Two-Way ANOVA](#two-way-anova)
6. [Effect Sizes](#effect-sizes)
7. [Power Analysis](#power-analysis)
8. [Regression Modeling](#regression-modeling)
9. [Model Comparison](#model-comparison)

---

## Descriptive Statistics

### Grouped Summary Statistics

```python
import pandas as pd
import numpy as np

def grouped_summary(df, group_cols, measure_col):
    """Calculate summary statistics by group.

    Returns DataFrame with Mean, SD, SEM, Median, Min, Max, N per group.
    """
    if isinstance(group_cols, str):
        group_cols = [group_cols]

    summary = df.groupby(group_cols)[measure_col].agg(
        Mean='mean',
        SD='std',
        Median='median',
        Min='min',
        Max='max',
        N='count'
    ).reset_index()

    summary['SEM'] = summary['SD'] / np.sqrt(summary['N'])

    return summary
```

### Percent Reduction

```python
def percent_reduction(df, group_col, measure_col, reference_group, comparison_group):
    """Calculate percent reduction of comparison vs reference.

    Returns: (percent_reduction, ref_mean, comp_mean)
    """
    ref_mean = df[df[group_col] == reference_group][measure_col].mean()
    comp_mean = df[df[group_col] == comparison_group][measure_col].mean()
    pct_reduction = ((ref_mean - comp_mean) / ref_mean) * 100
    return pct_reduction, ref_mean, comp_mean
```

### Relative Proportion

```python
def relative_proportion(df, group_col, measure_col, numerator_group, denominator_group):
    """Calculate relative proportion (as percentage) of one group vs another.

    Returns: proportion as percentage
    """
    num_mean = df[df[group_col] == numerator_group][measure_col].mean()
    den_mean = df[df[group_col] == denominator_group][measure_col].mean()
    return (num_mean / den_mean) * 100
```

---

## Normality Testing

### Shapiro-Wilk Test

```python
from scipy import stats

def shapiro_wilk_test(data):
    """Perform Shapiro-Wilk test for normality.

    Returns: (W_statistic, p_value)

    Interpretation:
    - p < 0.05: Data is NOT normally distributed
    - p >= 0.05: Data is normally distributed
    """
    stat, pvalue = stats.shapiro(data)
    return stat, pvalue

# Example usage
data = df[df['Condition'] == 'Control']['Measurement']
w_stat, p_val = shapiro_wilk_test(data)
print(f"Shapiro-Wilk W={w_stat:.4f}, p={p_val:.4f}")
```

---

## Two-Group Comparisons

### Independent T-Test

```python
def independent_ttest(group1, group2, equal_var=True):
    """Perform independent two-sample t-test.

    Args:
        group1, group2: array-like data
        equal_var: If True, use standard t-test. If False, use Welch's t-test

    Returns: (t_statistic, p_value)
    """
    t_stat, p_val = stats.ttest_ind(group1, group2, equal_var=equal_var)
    return t_stat, p_val
```

### Mann-Whitney U Test (non-parametric)

```python
def mann_whitney_test(group1, group2):
    """Perform Mann-Whitney U test (non-parametric alternative to t-test).

    Use when data is NOT normally distributed.

    Returns: (U_statistic, p_value)
    """
    u_stat, p_val = stats.mannwhitneyu(group1, group2, alternative='two-sided')
    return u_stat, p_val
```

---

## Multiple Comparisons

### Dunnett's Test

**CRITICAL**: Dunnett's test compares each treatment group to a single control group. R uses `multcomp::glht()` with `mcp(Strain_Ratio = "Dunnett")`. Python equivalent uses scipy.

```python
from scipy import stats

def dunnetts_test_scipy(df, group_col, value_col, control_group, alpha=0.05):
    """Dunnett's test using scipy.stats.dunnett (scipy >= 1.10).

    This is the preferred method - uses exact Dunnett distribution.

    Args:
        df: DataFrame
        group_col: Column with group labels
        value_col: Column with measurements
        control_group: Label of the control group
        alpha: Significance level (default 0.05)

    Returns: DataFrame with group, p_value, statistic, significant
    """
    groups = sorted(df[group_col].unique())
    control_data = df[df[group_col] == control_group][value_col].values
    treatment_groups = [g for g in groups if g != control_group]

    treatment_data = [df[df[group_col] == g][value_col].values for g in treatment_groups]

    # scipy.stats.dunnett: compare multiple treatment groups against control
    result = stats.dunnett(*treatment_data, control=control_data, alternative='two-sided')

    results = []
    for i, tg in enumerate(treatment_groups):
        results.append({
            'group': tg,
            'control': control_group,
            'p_value': result.pvalue[i],
            'statistic': result.statistic[i],
            'significant': result.pvalue[i] < alpha
        })

    return pd.DataFrame(results)
```

### Combined Dunnett's Test (Two Measures)

```python
def dunnett_area_circularity(df, group_col, area_col, circ_col, control_group, alpha=0.05):
    """Run Dunnett's test on both area and circularity.

    Returns: dict with:
        - area_results: Dunnett results for area
        - circ_results: Dunnett results for circularity
        - merged: Combined results
        - equivalent_in_both: groups NOT significant in EITHER (equivalent to control)
        - different_in_both: groups significant in BOTH (different from control)
    """
    area_dunnett = dunnetts_test_scipy(df, group_col, area_col, control_group, alpha)
    circ_dunnett = dunnetts_test_scipy(df, group_col, circ_col, control_group, alpha)

    # Merge results
    merged = area_dunnett[['group', 'p_value', 'significant']].merge(
        circ_dunnett[['group', 'p_value', 'significant']],
        on='group', suffixes=('_area', '_circ')
    )

    # Groups NOT significant in EITHER (equivalent to control in both)
    both_equiv = merged[~merged['significant_area'] & ~merged['significant_circ']]['group'].tolist()

    # Groups significant in both (different from control in both)
    both_diff = merged[merged['significant_area'] & merged['significant_circ']]['group'].tolist()

    return {
        'area_results': area_dunnett,
        'circ_results': circ_dunnett,
        'merged': merged,
        'equivalent_in_both': both_equiv,
        'different_in_both': both_diff,
    }
```

### Tukey HSD (all pairwise comparisons)

```python
from statsmodels.stats.multicomp import pairwise_tukeyhsd

def tukey_hsd_test(df, value_col, group_col, alpha=0.05):
    """Perform Tukey HSD test for all pairwise comparisons.

    Use when you want to compare ALL groups to EACH OTHER (not just vs control).

    Returns: Tukey HSD result object with summary table
    """
    result = pairwise_tukeyhsd(
        endog=df[value_col],
        groups=df[group_col],
        alpha=alpha
    )
    return result
```

---

## Two-Way ANOVA

```python
import statsmodels.api as sm
from statsmodels.formula.api import ols

def two_way_anova(df, dependent_var, factor1, factor2, anova_type=2):
    """Perform two-way ANOVA with interaction term.

    Args:
        df: DataFrame
        dependent_var: Column name of dependent variable
        factor1: First factor column name
        factor2: Second factor column name
        anova_type: Type of sum of squares (1, 2, or 3)
            - Type 1: Sequential (order matters)
            - Type 2: Hierarchical (recommended for balanced designs)
            - Type 3: Marginal (recommended for unbalanced designs)

    Returns: ANOVA table as DataFrame with columns:
        sum_sq, df, F, PR(>F) for each term including interaction
    """
    formula = f'{dependent_var} ~ C({factor1}) * C({factor2})'
    model = ols(formula, data=df).fit()
    anova_table = sm.stats.anova_lm(model, typ=anova_type)
    return anova_table


def extract_anova_interaction(anova_table, factor1, factor2):
    """Extract interaction F-statistic and p-value from ANOVA table.

    Returns: (F_statistic, p_value)
    """
    interaction_key = f'C({factor1}):C({factor2})'
    f_stat = anova_table.loc[interaction_key, 'F']
    p_val = anova_table.loc[interaction_key, 'PR(>F)']
    return f_stat, p_val

# Example usage
anova_result = two_way_anova(df, 'NeuN_count', 'Condition', 'Sex')
print(anova_result)

# Extract interaction
f_stat, p_val = extract_anova_interaction(anova_result, 'Condition', 'Sex')
print(f"Interaction F={f_stat:.3f}, p={p_val:.4f}")
```

---

## Effect Sizes

### Cohen's d

```python
def cohens_d(group1, group2):
    """Calculate Cohen's d using pooled standard deviation.

    This matches the standard formula: d = (mean1 - mean2) / sd_pooled
    where sd_pooled = sqrt(((n1-1)*s1^2 + (n2-1)*s2^2) / (n1+n2-2))

    NOTE: Uses pandas .std() which defaults to ddof=1 (sample std).

    Interpretation:
    - |d| < 0.2: Small effect
    - |d| = 0.2-0.5: Small to medium effect
    - |d| = 0.5-0.8: Medium to large effect
    - |d| > 0.8: Large effect

    Returns: Cohen's d value
    """
    n1, n2 = len(group1), len(group2)
    s1, s2 = group1.std(), group2.std()  # ddof=1 by default in pandas

    sd_pooled = np.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    d = (group1.mean() - group2.mean()) / sd_pooled

    return d

# Example usage
control = df[df['Condition'] == 'Control']['Measurement']
treatment = df[df['Condition'] == 'Treatment']['Measurement']
effect_size = cohens_d(control, treatment)
print(f"Cohen's d = {effect_size:.3f}")
```

---

## Power Analysis

### Sample Size Calculation

```python
from statsmodels.stats.power import TTestIndPower

def power_analysis_sample_size(effect_size, alpha=0.05, power=0.8, alternative='two-sided'):
    """Calculate required sample size per group for a two-sample t-test.

    Args:
        effect_size: Cohen's d (can be negative, absolute value used)
        alpha: Significance level (Type I error rate)
        power: Desired statistical power (1 - Type II error rate)
        alternative: 'two-sided', 'larger', or 'smaller'

    Returns: Required sample size per group (rounded up to integer)

    Example:
        # To detect effect size of 0.8 with 80% power
        n = power_analysis_sample_size(0.8, alpha=0.05, power=0.8)
        print(f"Need {n} samples per group")
    """
    analysis = TTestIndPower()
    # Use absolute value of effect size for sample size calculation
    n = analysis.solve_power(
        effect_size=abs(effect_size),
        alpha=alpha,
        power=power,
        alternative=alternative
    )
    return int(np.ceil(n))
```

### Post-hoc Power Calculation

```python
def calculate_achieved_power(n_per_group, effect_size, alpha=0.05, alternative='two-sided'):
    """Calculate achieved power given sample size and effect size.

    Args:
        n_per_group: Sample size per group
        effect_size: Cohen's d
        alpha: Significance level
        alternative: 'two-sided', 'larger', or 'smaller'

    Returns: Achieved power (0-1)
    """
    analysis = TTestIndPower()
    power = analysis.solve_power(
        effect_size=abs(effect_size),
        nobs1=n_per_group,
        alpha=alpha,
        alternative=alternative
    )
    return power
```

---

## Regression Modeling

### Data Preparation for Co-culture Ratios

```python
def prepare_ratio_data(df, strain_col='StrainNumber', ratio_col='Ratio',
                       area_col='Area', exclude_strains=None):
    """Prepare co-culture ratio data for regression analysis.

    Converts ratio strings (e.g., "3:1") to frequency fractions.
    Filters out pure strains if requested.

    Args:
        df: DataFrame with swarming data
        strain_col: Column with strain identifiers
        ratio_col: Column with ratio strings
        area_col: Column with area measurements
        exclude_strains: List of strain IDs to exclude (e.g., pure strains)

    Returns: DataFrame with Frequency_rhlI column added
    """
    result = df.copy()

    if exclude_strains:
        result = result[~result[strain_col].isin(exclude_strains)]

    # Parse ratio into frequency
    # Ratio format: "rhlI_D:lasI_D" (e.g., "3:1" means 3 parts rhlI, 1 part lasI)
    ratio_parts = result[ratio_col].str.split(':', expand=True).astype(int)
    result['rhlI_D'] = ratio_parts[0]
    result['lasI_D'] = ratio_parts[1]
    result['Frequency_rhlI'] = result['rhlI_D'] / (result['rhlI_D'] + result['lasI_D'])

    return result
```

### Polynomial Regression

```python
def fit_polynomial_model(df, x_col, y_col, degree=2):
    """Fit polynomial regression model.

    Equivalent to R: lm(y ~ poly(x, degree, raw=TRUE))

    Args:
        df: DataFrame
        x_col: Predictor column name
        y_col: Response column name
        degree: Polynomial degree (2=quadratic, 3=cubic)

    Returns: dict with model, coefficients, R-squared, F-statistic, p-value,
             peak_frequency, peak_value, peak_ci
    """
    x = df[x_col].values
    y = df[y_col].values

    # Build design matrix for polynomial
    X_poly = np.column_stack([x**i for i in range(1, degree+1)])
    X = sm.add_constant(X_poly)

    model = sm.OLS(y, X).fit()

    result = {
        'model': model,
        'coefficients': model.params,
        'r_squared': model.rsquared,
        'adj_r_squared': model.rsquared_adj,
        'f_statistic': model.fvalue,
        'f_pvalue': model.f_pvalue,
        'aic': model.aic,
        'bic': model.bic,
        'summary': model.summary(),
    }

    # Find peak (maximum) using calculus
    if degree == 2:
        # y = b0 + b1*x + b2*x^2
        # Peak at x = -b1 / (2*b2)
        b1, b2 = model.params[1], model.params[2]
        peak_x = -b1 / (2 * b2)
    elif degree == 3:
        # y = b0 + b1*x + b2*x^2 + b3*x^3
        # Derivative: b1 + 2*b2*x + 3*b3*x^2 = 0
        b1, b2, b3 = model.params[1], model.params[2], model.params[3]
        discriminant = (2*b2)**2 - 4*(3*b3)*b1
        if discriminant >= 0:
            x1 = (-2*b2 + np.sqrt(discriminant)) / (2*3*b3)
            x2 = (-2*b2 - np.sqrt(discriminant)) / (2*3*b3)
            # Choose the one that's a maximum (second derivative < 0)
            candidates = [x1, x2]
            peak_x = None
            for cx in candidates:
                second_deriv = 2*b2 + 6*b3*cx
                if second_deriv < 0:
                    peak_x = cx
                    break
            if peak_x is None:
                peak_x = candidates[0]  # fallback
        else:
            peak_x = x.mean()  # no real critical points
    else:
        # For higher degrees, use numerical optimization
        from scipy.optimize import minimize_scalar
        poly_func = lambda xx: -sum(model.params[i] * xx**i for i in range(degree+1))
        opt = minimize_scalar(poly_func, bounds=(x.min(), x.max()), method='bounded')
        peak_x = opt.x

    # Predict at peak and get confidence interval
    X_peak = np.array([[1] + [peak_x**i for i in range(1, degree+1)]])
    peak_pred = model.get_prediction(X_peak)
    peak_value = peak_pred.predicted_mean[0]
    peak_ci = peak_pred.conf_int(alpha=0.05)[0]

    result['peak_x'] = peak_x
    result['peak_value'] = peak_value
    result['peak_ci_lower'] = peak_ci[0]
    result['peak_ci_upper'] = peak_ci[1]

    return result
```

### Natural Spline Regression

**CRITICAL**: This must match R's `lm(Area ~ ns(Frequency_rhlI, df=4))`.

```python
from patsy import dmatrix

def fit_natural_spline_model(df, x_col, y_col, spline_df=4):
    """Fit natural spline regression model.

    Equivalent to R: lm(y ~ ns(x, df=spline_df))
    Uses patsy's cr() with explicit quantile knots to match R's ns().

    CRITICAL: R's ns(x, df=N) places N-1 internal knots at equally-spaced
    quantiles (25th, 50th, 75th for df=4). patsy's cr(df=N) does NOT place
    knots at the same locations by default. You MUST specify knots explicitly.

    Args:
        df: DataFrame
        x_col: Predictor column name
        y_col: Response column name
        spline_df: Degrees of freedom for natural spline basis

    Returns: dict with model, R-squared, F-statistic, p-value,
             peak_frequency, peak_value, peak_ci
    """
    x = df[x_col].values
    y = df[y_col].values

    # Match R's ns() knot placement: df-1 internal knots at equally-spaced quantiles
    n_internal_knots = spline_df - 1
    quantile_pcts = np.linspace(100.0 / (n_internal_knots + 1),
                                100.0 * n_internal_knots / (n_internal_knots + 1),
                                n_internal_knots)
    knots = np.percentile(x, quantile_pcts)
    knot_str = ", ".join([str(k) for k in knots])

    # Create natural spline basis using patsy's cr() with explicit knots
    formula_str = f"cr({x_col}, knots=[{knot_str}]) - 1"
    X_spline = np.array(dmatrix(formula_str, df))
    X = sm.add_constant(X_spline)

    model = sm.OLS(y, X).fit()

    result = {
        'model': model,
        'r_squared': model.rsquared,
        'adj_r_squared': model.rsquared_adj,
        'f_statistic': model.fvalue,
        'f_pvalue': model.f_pvalue,
        'aic': model.aic,
        'bic': model.bic,
    }

    # Find peak by evaluating over fine grid
    x_grid = np.linspace(x.min(), x.max(), 1000)
    grid_df = pd.DataFrame({x_col: x_grid})
    X_grid_spline = np.array(dmatrix(formula_str, grid_df))
    X_grid = sm.add_constant(X_grid_spline)

    predictions = model.get_prediction(X_grid)
    pred_mean = predictions.predicted_mean
    pred_ci = predictions.conf_int(alpha=0.05)

    # Find peak
    max_idx = np.argmax(pred_mean)

    result['peak_x'] = x_grid[max_idx]
    result['peak_value'] = pred_mean[max_idx]
    result['peak_ci_lower'] = pred_ci[max_idx, 0]
    result['peak_ci_upper'] = pred_ci[max_idx, 1]
    result['predictions'] = pred_mean
    result['x_grid'] = x_grid
    result['ci_lower'] = pred_ci[:, 0]
    result['ci_upper'] = pred_ci[:, 1]

    return result
```

---

## Model Comparison

```python
def compare_regression_models(models_dict):
    """Compare multiple regression models.

    Args:
        models_dict: Dict mapping model_name -> result dict from fit_* functions

    Returns: DataFrame with model comparison metrics

    Example:
        models = {
            'quadratic': fit_polynomial_model(df, 'x', 'y', degree=2),
            'cubic': fit_polynomial_model(df, 'x', 'y', degree=3),
            'spline': fit_natural_spline_model(df, 'x', 'y', spline_df=4)
        }
        comparison = compare_regression_models(models)
        print(comparison)
    """
    comparison = []
    for name, result in models_dict.items():
        comparison.append({
            'model': name,
            'r_squared': result['r_squared'],
            'adj_r_squared': result['adj_r_squared'],
            'f_statistic': result['f_statistic'],
            'f_pvalue': result['f_pvalue'],
            'aic': result.get('aic'),
            'bic': result.get('bic'),
            'peak_x': result.get('peak_x'),
            'peak_value': result.get('peak_value'),
            'peak_ci_lower': result.get('peak_ci_lower'),
            'peak_ci_upper': result.get('peak_ci_upper'),
        })

    comparison_df = pd.DataFrame(comparison)
    comparison_df['best_r2'] = comparison_df['r_squared'] == comparison_df['r_squared'].max()
    comparison_df['best_aic'] = comparison_df['aic'] == comparison_df['aic'].min()
    comparison_df['best_bic'] = comparison_df['bic'] == comparison_df['bic'].min()

    return comparison_df.sort_values('r_squared', ascending=False)
```

---

## Answer Extraction Patterns

### BixBench-specific formatting

```python
def format_answer(value, question_type):
    """Format answer according to BixBench expectations.

    Args:
        value: Numeric value to format
        question_type: Type of answer expected

    Returns: Formatted value
    """
    if question_type == "nearest_thousand":
        return int(round(value, -3))
    elif question_type == "percentage_int":
        return int(round(value))
    elif question_type == "percentage_2dec":
        return round(value, 2)
    elif question_type == "cohen_d":
        return round(value, 3)
    elif question_type == "statistic_3dec":
        return round(value, 3)
    elif question_type == "sample_size":
        return int(np.ceil(value))
    elif question_type == "count":
        return int(value)
    elif question_type == "r_squared":
        return round(value, 2)
    elif question_type == "p_value":
        if value < 0.0001:
            return f"{value:.2e}"
        else:
            return round(value, 4)
    else:
        return value
```

---

## Complete Example: bix-54 Workflow

```python
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv("Swarm_2.csv")

# Prepare ratio data
df_coculture = prepare_ratio_data(
    df,
    strain_col='StrainNumber',
    ratio_col='Ratio',
    area_col='Area',
    exclude_strains=['1', '98']  # Exclude pure strains
)

# Fit models
quadratic = fit_polynomial_model(df_coculture, 'Frequency_rhlI', 'Area', degree=2)
cubic = fit_polynomial_model(df_coculture, 'Frequency_rhlI', 'Area', degree=3)
spline = fit_natural_spline_model(df_coculture, 'Frequency_rhlI', 'Area', spline_df=4)

# Compare models
models = {'quadratic': quadratic, 'cubic': cubic, 'spline': spline}
comparison = compare_regression_models(models)
print(comparison)

# Best model by R-squared
best_model_name = comparison.iloc[0]['model']
best_model = models[best_model_name]

# Extract answers
print(f"Best model: {best_model_name}")
print(f"R-squared: {best_model['r_squared']:.4f}")
print(f"Peak frequency: {best_model['peak_x']:.4f}")
print(f"Peak area: {best_model['peak_value']:.1f}")
print(f"95% CI: [{best_model['peak_ci_lower']:.1f}, {best_model['peak_ci_upper']:.1f}]")
```
