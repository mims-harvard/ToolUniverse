---
name: tooluniverse-statistical-modeling
description: Perform statistical modeling and regression analysis on biomedical datasets. Supports linear regression, logistic regression (binary/ordinal/multinomial), mixed-effects models, Cox proportional hazards survival analysis, Kaplan-Meier estimation, and comprehensive model diagnostics. Extracts odds ratios, hazard ratios, confidence intervals, p-values, and effect sizes. Designed to solve BixBench statistical reasoning questions involving clinical/experimental data. Use when asked to fit regression models, compute odds ratios, perform survival analysis, run statistical tests, or interpret model coefficients from provided data.
---

# Statistical Modeling for Biomedical Data Analysis

Comprehensive statistical modeling skill that fits regression models, survival models, and mixed-effects models to biomedical data. Produces publication-quality statistical summaries with odds ratios, hazard ratios, confidence intervals, and p-values.

**KEY PRINCIPLES**:
1. **Data-first approach** - Always inspect and validate data before modeling
2. **Model selection by outcome type** - Continuous -> linear, binary -> logistic, ordinal -> ordinal logit, time-to-event -> Cox/KM
3. **Assumption checking** - Verify model assumptions (linearity, proportional hazards, etc.)
4. **Complete reporting** - Always report effect sizes, CIs, p-values, and model fit statistics
5. **Confounder awareness** - Adjust for confounders when specified or clinically relevant
6. **Reproducible analysis** - All code must be deterministic and reproducible
7. **Robust error handling** - Graceful handling of convergence failures, separation, collinearity
8. **Round correctly** - Match the precision requested (typically 2-4 decimal places)

---

## When to Use

Apply when user asks:
- "What is the odds ratio of X associated with Y in logistic regression?"
- "What is the hazard ratio for treatment in a Cox model?"
- "Fit a linear regression of Y on X1, X2, X3"
- "Perform ordinal logistic regression for severity outcome"
- "What is the Kaplan-Meier survival estimate at time T?"
- "Run a mixed-effects model with random intercepts for subject"
- "What is the percentage reduction in odds ratio after adjusting for confounders?"
- "Compute the interaction term between A and B"
- "What are the confidence intervals for the regression coefficients?"

---

## Input Parsing

### Data Input Formats

The skill handles data in these formats:

| Format | Description | How to Handle |
|--------|-------------|--------------|
| CSV/TSV file path | File on disk | `pd.read_csv(path)` or `pd.read_csv(path, sep='\t')` |
| Inline table | Markdown or text table in the question | Parse with pandas |
| DataFrame description | Column names + summary stats | Reconstruct or simulate |
| JSON data | Structured data object | `pd.DataFrame(data)` |
| Supplementary data | Referenced from a paper/question | Extract from context |

### Outcome Variable Detection

| Outcome Type | Indicators | Model Choice |
|-------------|-----------|-------------|
| Continuous | Height, weight, blood pressure, score (numeric range) | Linear regression / LMM |
| Binary | Yes/No, 0/1, Disease/Healthy, Positive/Negative | Logistic regression |
| Ordinal | Mild/Moderate/Severe, Stage I/II/III/IV, Likert scale | Ordinal logistic regression |
| Multinomial | >2 unordered categories (e.g., cancer subtypes) | Multinomial logistic regression |
| Time-to-event | Survival time + censoring indicator | Cox PH / Kaplan-Meier |
| Count | Number of events, occurrences | Poisson / Negative binomial |

### Variable Type Detection

```python
def detect_variable_type(series):
    """Detect whether a variable is continuous, binary, ordinal, or categorical."""
    unique_vals = series.dropna().unique()
    n_unique = len(unique_vals)

    if n_unique == 2:
        return 'binary'
    elif n_unique <= 7 and series.dtype in ['object', 'category']:
        return 'categorical'
    elif n_unique <= 10 and all(isinstance(v, (int, float)) for v in unique_vals):
        # Could be ordinal - check if integer-valued
        if all(float(v).is_integer() for v in unique_vals):
            return 'ordinal'
        return 'continuous'
    elif series.dtype in ['float64', 'float32', 'int64', 'int32']:
        return 'continuous'
    else:
        return 'categorical'
```

---

## Phase 0: Data Loading and Validation

**Goal**: Load data, identify variable types, check for missing values and outliers.

### 0.1 Load Data

```python
import pandas as pd
import numpy as np

def load_data(source):
    """Load data from various sources."""
    if isinstance(source, pd.DataFrame):
        return source
    elif isinstance(source, str) and source.endswith('.csv'):
        return pd.read_csv(source)
    elif isinstance(source, str) and source.endswith('.tsv'):
        return pd.read_csv(source, sep='\t')
    elif isinstance(source, dict):
        return pd.DataFrame(source)
    elif isinstance(source, list):
        return pd.DataFrame(source)
    else:
        raise ValueError(f"Unsupported data source type: {type(source)}")
```

### 0.2 Data Summary

```python
def summarize_data(df):
    """Generate comprehensive data summary."""
    summary = {
        'n_rows': len(df),
        'n_cols': len(df.columns),
        'columns': {},
        'missing_values': df.isnull().sum().to_dict(),
    }
    for col in df.columns:
        col_info = {
            'dtype': str(df[col].dtype),
            'n_unique': df[col].nunique(),
            'n_missing': df[col].isnull().sum(),
            'variable_type': detect_variable_type(df[col]),
        }
        if df[col].dtype in ['float64', 'int64']:
            col_info['mean'] = df[col].mean()
            col_info['std'] = df[col].std()
            col_info['min'] = df[col].min()
            col_info['max'] = df[col].max()
        else:
            col_info['value_counts'] = df[col].value_counts().to_dict()
        summary['columns'][col] = col_info
    return summary
```

### 0.3 Data Preprocessing

```python
def preprocess_data(df, outcome_col, predictor_cols, reference_levels=None):
    """Preprocess data for modeling."""
    df_model = df[predictor_cols + [outcome_col]].dropna().copy()

    # Encode categorical variables
    for col in predictor_cols:
        if df_model[col].dtype == 'object' or df_model[col].dtype.name == 'category':
            if reference_levels and col in reference_levels:
                ref = reference_levels[col]
                categories = [ref] + [c for c in df_model[col].unique() if c != ref]
                df_model[col] = pd.Categorical(df_model[col], categories=categories)
            dummies = pd.get_dummies(df_model[col], prefix=col, drop_first=True, dtype=int)
            df_model = pd.concat([df_model.drop(col, axis=1), dummies], axis=1)

    return df_model
```

---

## Phase 1: Linear Regression

**Goal**: Fit ordinary least squares (OLS) regression for continuous outcomes.

### 1.1 OLS Regression

```python
import statsmodels.api as sm
import statsmodels.formula.api as smf

def fit_linear_regression(df, formula=None, outcome=None, predictors=None):
    """Fit OLS linear regression.

    Args:
        df: pandas DataFrame
        formula: R-style formula (e.g., 'y ~ x1 + x2 + x1:x2')
        outcome: outcome variable name (alternative to formula)
        predictors: list of predictor names (alternative to formula)

    Returns:
        dict with coefficients, p-values, CIs, R-squared, diagnostics
    """
    if formula:
        model = smf.ols(formula, data=df).fit()
    else:
        X = sm.add_constant(df[predictors])
        y = df[outcome]
        model = sm.OLS(y, X).fit()

    results = {
        'model_type': 'OLS Linear Regression',
        'formula': formula or f'{outcome} ~ {" + ".join(predictors)}',
        'n_observations': int(model.nobs),
        'coefficients': {},
        'r_squared': round(model.rsquared, 4),
        'adj_r_squared': round(model.rsquared_adj, 4),
        'f_statistic': round(model.fvalue, 4),
        'f_pvalue': model.f_pvalue,
        'aic': round(model.aic, 2),
        'bic': round(model.bic, 2),
    }

    conf_int = model.conf_int()
    for i, name in enumerate(model.params.index):
        results['coefficients'][name] = {
            'estimate': round(model.params[name], 4),
            'std_error': round(model.bse[name], 4),
            't_value': round(model.tvalues[name], 4),
            'p_value': round(model.pvalues[name], 6),
            'ci_lower': round(conf_int.iloc[i, 0], 4),
            'ci_upper': round(conf_int.iloc[i, 1], 4),
        }

    return results, model
```

### 1.2 Model Diagnostics for OLS

```python
from scipy import stats as scipy_stats

def ols_diagnostics(model):
    """Run OLS diagnostic tests."""
    diagnostics = {}

    # Residual normality (Shapiro-Wilk)
    residuals = model.resid
    if len(residuals) <= 5000:
        sw_stat, sw_p = scipy_stats.shapiro(residuals)
        diagnostics['shapiro_wilk'] = {
            'statistic': round(sw_stat, 4),
            'p_value': round(sw_p, 6),
            'normal_residuals': sw_p > 0.05
        }

    # Durbin-Watson (autocorrelation)
    from statsmodels.stats.stattools import durbin_watson
    dw = durbin_watson(residuals)
    diagnostics['durbin_watson'] = {
        'statistic': round(dw, 4),
        'interpretation': 'No autocorrelation' if 1.5 < dw < 2.5 else 'Possible autocorrelation'
    }

    # Breusch-Pagan (heteroscedasticity)
    from statsmodels.stats.diagnostic import het_breuschpagan
    bp_stat, bp_p, _, _ = het_breuschpagan(residuals, model.model.exog)
    diagnostics['breusch_pagan'] = {
        'statistic': round(bp_stat, 4),
        'p_value': round(bp_p, 6),
        'homoscedastic': bp_p > 0.05
    }

    # VIF (multicollinearity)
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    X = model.model.exog
    if X.shape[1] > 1:
        vif_data = {}
        for i in range(X.shape[1]):
            col_name = model.model.exog_names[i]
            if col_name != 'Intercept':
                vif_data[col_name] = round(variance_inflation_factor(X, i), 2)
        diagnostics['vif'] = vif_data

    return diagnostics
```

---

## Phase 2: Logistic Regression (Binary)

**Goal**: Fit logistic regression for binary outcomes. Extract odds ratios.

### 2.1 Binary Logistic Regression

```python
def fit_logistic_regression(df, formula=None, outcome=None, predictors=None):
    """Fit binary logistic regression.

    Returns:
        dict with odds ratios, CIs, p-values, model fit
    """
    if formula:
        model = smf.logit(formula, data=df).fit(disp=0, maxiter=100)
    else:
        X = sm.add_constant(df[predictors])
        y = df[outcome]
        model = sm.Logit(y, X).fit(disp=0, maxiter=100)

    results = {
        'model_type': 'Binary Logistic Regression',
        'formula': formula or f'{outcome} ~ {" + ".join(predictors)}',
        'n_observations': int(model.nobs),
        'coefficients': {},
        'odds_ratios': {},
        'pseudo_r_squared': round(model.prsquared, 4),
        'log_likelihood': round(model.llf, 4),
        'aic': round(model.aic, 2),
        'bic': round(model.bic, 2),
    }

    conf_int = model.conf_int()
    for i, name in enumerate(model.params.index):
        coef = model.params[name]
        results['coefficients'][name] = {
            'estimate': round(coef, 4),
            'std_error': round(model.bse[name], 4),
            'z_value': round(model.tvalues[name], 4),
            'p_value': round(model.pvalues[name], 6),
            'ci_lower': round(conf_int.iloc[i, 0], 4),
            'ci_upper': round(conf_int.iloc[i, 1], 4),
        }
        # Odds ratios (exponentiate coefficients)
        or_val = np.exp(coef)
        or_ci_lower = np.exp(conf_int.iloc[i, 0])
        or_ci_upper = np.exp(conf_int.iloc[i, 1])
        results['odds_ratios'][name] = {
            'OR': round(or_val, 4),
            'ci_lower': round(or_ci_lower, 4),
            'ci_upper': round(or_ci_upper, 4),
        }

    return results, model
```

### 2.2 Odds Ratio Interpretation

```python
def interpret_odds_ratio(or_val, ci_lower, ci_upper, variable_name, p_value):
    """Generate human-readable interpretation of an odds ratio."""
    if or_val > 1:
        pct_increase = round((or_val - 1) * 100, 1)
        direction = f'{pct_increase}% increase in odds'
    elif or_val < 1:
        pct_decrease = round((1 - or_val) * 100, 1)
        direction = f'{pct_decrease}% decrease in odds'
    else:
        direction = 'no change in odds'

    sig = 'statistically significant' if p_value < 0.05 else 'not statistically significant'

    ci_contains_1 = ci_lower <= 1 <= ci_upper

    return {
        'variable': variable_name,
        'odds_ratio': or_val,
        'interpretation': direction,
        'significance': sig,
        'p_value': p_value,
        'ci_95': f'({ci_lower}, {ci_upper})',
        'ci_contains_null': ci_contains_1,
    }
```

---

## Phase 3: Ordinal Logistic Regression

**Goal**: Fit proportional odds (ordered logit) model for ordinal outcomes. This is critical for BixBench questions about severity scales, Likert scores, etc.

### 3.1 Ordinal Logit Model

```python
from statsmodels.miscmodels.ordinal_model import OrderedModel

def fit_ordinal_logistic(df, outcome, predictors, order=None):
    """Fit ordinal logistic (proportional odds) regression.

    Args:
        df: DataFrame
        outcome: ordinal outcome variable name
        predictors: list of predictor variable names
        order: explicit ordering of outcome levels (e.g., ['Mild', 'Moderate', 'Severe'])

    Returns:
        dict with odds ratios, thresholds, p-values
    """
    df_model = df.copy()

    # Set up ordered outcome
    if order:
        df_model[outcome] = pd.Categorical(df_model[outcome], categories=order, ordered=True)
    else:
        # Try to detect order from data
        unique_vals = sorted(df_model[outcome].dropna().unique())
        df_model[outcome] = pd.Categorical(df_model[outcome], categories=unique_vals, ordered=True)

    # Encode outcome as integer codes
    y = df_model[outcome].cat.codes
    X = df_model[predictors].copy()

    # Handle categorical predictors
    X_encoded = pd.get_dummies(X, drop_first=True, dtype=float)

    model = OrderedModel(y, X_encoded, distr='logit')
    fit = model.fit(method='bfgs', disp=0, maxiter=200)

    # Parse results
    n_thresholds = len(df_model[outcome].cat.categories) - 1
    param_names = list(X_encoded.columns)

    results = {
        'model_type': 'Ordinal Logistic Regression (Proportional Odds)',
        'outcome': outcome,
        'outcome_levels': list(df_model[outcome].cat.categories),
        'n_observations': int(len(y.dropna())),
        'predictors': param_names,
        'coefficients': {},
        'odds_ratios': {},
        'thresholds': {},
        'log_likelihood': round(fit.llf, 4),
        'aic': round(fit.aic, 2),
    }

    # Extract coefficients for predictors
    conf_int = fit.conf_int()
    for i, name in enumerate(fit.params.index):
        coef = fit.params[name]
        p_val = fit.pvalues[name]

        if i < len(param_names):
            # Predictor coefficient
            results['coefficients'][name] = {
                'estimate': round(coef, 4),
                'std_error': round(fit.bse[name], 4),
                'z_value': round(fit.tvalues[name], 4),
                'p_value': round(p_val, 6),
                'ci_lower': round(conf_int.iloc[i, 0], 4),
                'ci_upper': round(conf_int.iloc[i, 1], 4),
            }
            or_val = np.exp(coef)
            results['odds_ratios'][name] = {
                'OR': round(or_val, 4),
                'ci_lower': round(np.exp(conf_int.iloc[i, 0]), 4),
                'ci_upper': round(np.exp(conf_int.iloc[i, 1]), 4),
            }
        else:
            # Threshold (cut-point)
            threshold_idx = i - len(param_names)
            results['thresholds'][f'threshold_{threshold_idx}'] = {
                'estimate': round(coef, 4),
                'std_error': round(fit.bse[name], 4),
            }

    return results, fit
```

### 3.2 Proportional Odds Assumption Test

```python
def test_proportional_odds(df, outcome, predictors, order=None):
    """Test proportional odds assumption using Brant test approximation.

    Fits separate binary logistic regressions at each cut point and
    compares coefficients.
    """
    df_model = df.copy()
    if order:
        df_model[outcome] = pd.Categorical(df_model[outcome], categories=order, ordered=True)
    y_codes = df_model[outcome].cat.codes

    n_levels = len(df_model[outcome].cat.categories)
    X = pd.get_dummies(df_model[predictors], drop_first=True, dtype=float)
    X_const = sm.add_constant(X)

    cutpoint_results = {}
    for k in range(n_levels - 1):
        y_binary = (y_codes > k).astype(int)
        try:
            binary_model = sm.Logit(y_binary, X_const).fit(disp=0)
            cutpoint_results[k] = {
                name: round(binary_model.params[name], 4)
                for name in X.columns
            }
        except Exception:
            pass

    # Compare coefficients across cut points
    if len(cutpoint_results) >= 2:
        coef_variation = {}
        for pred in X.columns:
            coefs = [cutpoint_results[k][pred] for k in cutpoint_results if pred in cutpoint_results[k]]
            if len(coefs) >= 2:
                coef_variation[pred] = {
                    'coefficients_by_cutpoint': coefs,
                    'range': round(max(coefs) - min(coefs), 4),
                    'likely_proportional': max(coefs) - min(coefs) < 0.5,
                }
        return coef_variation

    return None
```

---

## Phase 4: Multinomial Logistic Regression

**Goal**: Fit multinomial logistic regression for unordered categorical outcomes with 3+ levels.

### 4.1 Multinomial Logit Model

```python
def fit_multinomial_logistic(df, outcome, predictors, reference_level=None):
    """Fit multinomial logistic regression.

    Args:
        df: DataFrame
        outcome: categorical outcome (3+ unordered levels)
        predictors: list of predictor names
        reference_level: reference category for outcome

    Returns:
        dict with odds ratios per comparison level
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder

    df_model = df[predictors + [outcome]].dropna().copy()

    # Encode outcome
    if reference_level:
        categories = [reference_level] + [c for c in df_model[outcome].unique() if c != reference_level]
    else:
        categories = sorted(df_model[outcome].unique())
    le = LabelEncoder()
    le.classes_ = np.array(categories)
    y = le.transform(df_model[outcome])

    # Prepare predictors
    X = pd.get_dummies(df_model[predictors], drop_first=True, dtype=float)
    X_array = X.values

    # Fit model
    model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
    model.fit(X_array, y)

    # Also fit with statsmodels for p-values using MNLogit
    try:
        X_const = sm.add_constant(X)
        mn_model = sm.MNLogit(y, X_const).fit(disp=0, maxiter=200)

        results = {
            'model_type': 'Multinomial Logistic Regression',
            'outcome': outcome,
            'reference_level': categories[0],
            'comparison_levels': categories[1:],
            'n_observations': len(y),
            'coefficients': {},
            'odds_ratios': {},
            'pseudo_r_squared': round(mn_model.prsquared, 4),
            'log_likelihood': round(mn_model.llf, 4),
            'aic': round(mn_model.aic, 2),
        }

        conf_int = mn_model.conf_int()
        for j, comp_level in enumerate(categories[1:]):
            level_coefs = {}
            level_ors = {}
            for i, name in enumerate(X_const.columns):
                param_idx = j * len(X_const.columns) + i
                coef = mn_model.params.iloc[i, j]
                p_val = mn_model.pvalues.iloc[i, j]
                ci_low = conf_int.iloc[param_idx, 0] if param_idx < len(conf_int) else np.nan
                ci_high = conf_int.iloc[param_idx, 1] if param_idx < len(conf_int) else np.nan

                level_coefs[name] = {
                    'estimate': round(float(coef), 4),
                    'p_value': round(float(p_val), 6),
                }
                level_ors[name] = {
                    'OR': round(float(np.exp(coef)), 4),
                }
            results['coefficients'][comp_level] = level_coefs
            results['odds_ratios'][comp_level] = level_ors

        return results, mn_model

    except Exception:
        # Fallback: sklearn only (no p-values)
        results = {
            'model_type': 'Multinomial Logistic Regression (sklearn)',
            'outcome': outcome,
            'reference_level': categories[0],
            'n_observations': len(y),
            'coefficients': {},
        }
        for j, comp_level in enumerate(categories[1:]):
            coefs = model.coef_[j] if j < len(model.coef_) else model.coef_[-1]
            level_coefs = {}
            for i, name in enumerate(X.columns):
                level_coefs[name] = {
                    'estimate': round(float(coefs[i]), 4),
                    'OR': round(float(np.exp(coefs[i])), 4),
                }
            results['coefficients'][comp_level] = level_coefs
        return results, model
```

---

## Phase 5: Mixed-Effects Models

**Goal**: Fit linear mixed-effects models (LMM) and generalized linear mixed-effects models (GLMM) for hierarchical/clustered data.

### 5.1 Linear Mixed-Effects Model

```python
import statsmodels.formula.api as smf

def fit_mixed_effects(df, formula, groups, re_formula=None):
    """Fit linear mixed-effects model.

    Args:
        df: DataFrame
        formula: R-style formula for fixed effects (e.g., 'y ~ x1 + x2')
        groups: grouping variable name (e.g., 'subject_id')
        re_formula: random effects formula (e.g., '~x1' for random slope)
                   Default is random intercept only

    Returns:
        dict with fixed effects, random effects variance, ICCs
    """
    if re_formula:
        model = smf.mixedlm(formula, data=df, groups=df[groups],
                            re_formula=re_formula)
    else:
        model = smf.mixedlm(formula, data=df, groups=df[groups])

    fit = model.fit(reml=True)

    results = {
        'model_type': 'Linear Mixed-Effects Model',
        'formula': formula,
        'groups': groups,
        're_formula': re_formula or '~1 (random intercept)',
        'n_observations': int(fit.nobs),
        'n_groups': int(fit.nobs / fit.nobs * len(df[groups].unique())),
        'fixed_effects': {},
        'random_effects_variance': {},
        'log_likelihood': round(fit.llf, 4),
        'aic': round(fit.aic, 2) if hasattr(fit, 'aic') else None,
        'bic': round(fit.bic, 2) if hasattr(fit, 'bic') else None,
        'converged': fit.converged,
    }

    # Fixed effects
    conf_int = fit.conf_int()
    for name in fit.fe_params.index:
        results['fixed_effects'][name] = {
            'estimate': round(float(fit.fe_params[name]), 4),
            'std_error': round(float(fit.bse_fe[name]) if name in fit.bse_fe else float(fit.bse[name]), 4),
            'z_value': round(float(fit.tvalues[name]), 4),
            'p_value': round(float(fit.pvalues[name]), 6),
            'ci_lower': round(float(conf_int.loc[name, 0]), 4),
            'ci_upper': round(float(conf_int.loc[name, 1]), 4),
        }

    # Random effects variance
    re_var = fit.cov_re
    if hasattr(re_var, 'values'):
        for i, name in enumerate(re_var.index):
            results['random_effects_variance'][name] = round(float(re_var.iloc[i, i]), 4)
    else:
        results['random_effects_variance']['Group Var'] = round(float(re_var), 4)

    # Residual variance
    results['residual_variance'] = round(float(fit.scale), 4)

    # ICC (Intraclass Correlation Coefficient)
    if 'Group Var' in results['random_effects_variance'] or len(results['random_effects_variance']) > 0:
        group_var = list(results['random_effects_variance'].values())[0]
        resid_var = results['residual_variance']
        if group_var + resid_var > 0:
            results['icc'] = round(group_var / (group_var + resid_var), 4)

    return results, fit
```

### 5.2 GLMM (Logistic Mixed-Effects)

```python
def fit_logistic_mixed(df, formula, groups, re_formula=None):
    """Fit logistic mixed-effects model (GLMM with binomial family).

    Note: statsmodels BinomialBayesMixedGLM or use formula-based approach.
    """
    import statsmodels.genmod.generalized_estimating_equations as gee

    # Use GEE as approximation when true GLMM not available
    fam = sm.families.Binomial()
    model = smf.gee(formula, groups=groups, data=df, family=fam)
    fit = model.fit()

    results = {
        'model_type': 'GEE Logistic (Binomial) - approximation for GLMM',
        'formula': formula,
        'groups': groups,
        'n_observations': int(fit.nobs),
        'fixed_effects': {},
        'odds_ratios': {},
    }

    conf_int = fit.conf_int()
    for name in fit.params.index:
        coef = float(fit.params[name])
        results['fixed_effects'][name] = {
            'estimate': round(coef, 4),
            'std_error': round(float(fit.bse[name]), 4),
            'z_value': round(float(fit.tvalues[name]), 4),
            'p_value': round(float(fit.pvalues[name]), 6),
        }
        results['odds_ratios'][name] = {
            'OR': round(float(np.exp(coef)), 4),
            'ci_lower': round(float(np.exp(conf_int.loc[name, 0])), 4),
            'ci_upper': round(float(np.exp(conf_int.loc[name, 1])), 4),
        }

    return results, fit
```

---

## Phase 6: Survival Analysis

**Goal**: Fit Cox proportional hazards model and compute Kaplan-Meier estimates.

### 6.1 Cox Proportional Hazards

```python
from lifelines import CoxPHFitter

def fit_cox_ph(df, duration_col, event_col, predictors=None, formula=None,
               strata=None, cluster_col=None):
    """Fit Cox proportional hazards model.

    Args:
        df: DataFrame
        duration_col: time-to-event column
        event_col: event indicator column (1=event, 0=censored)
        predictors: list of covariate names
        strata: stratification variable(s)
        cluster_col: cluster variable for robust variance

    Returns:
        dict with hazard ratios, CIs, p-values, concordance
    """
    cph = CoxPHFitter()

    if predictors:
        cols = [duration_col, event_col] + predictors
    else:
        cols = list(df.columns)

    df_model = df[cols].dropna().copy()

    # Encode categorical variables
    for col in (predictors or [c for c in cols if c not in [duration_col, event_col]]):
        if df_model[col].dtype == 'object':
            dummies = pd.get_dummies(df_model[col], prefix=col, drop_first=True, dtype=int)
            df_model = pd.concat([df_model.drop(col, axis=1), dummies], axis=1)

    cph.fit(df_model, duration_col=duration_col, event_col=event_col,
            strata=strata, cluster_col=cluster_col)

    summary = cph.summary

    results = {
        'model_type': 'Cox Proportional Hazards',
        'n_observations': int(cph.event_observed.shape[0]),
        'n_events': int(cph.event_observed.sum()),
        'duration_col': duration_col,
        'event_col': event_col,
        'coefficients': {},
        'hazard_ratios': {},
        'concordance_index': round(cph.concordance_index_, 4),
        'partial_log_likelihood': round(float(cph.log_likelihood_), 4),
        'aic': round(float(cph.AIC_partial_), 4) if hasattr(cph, 'AIC_partial_') else None,
    }

    for name in summary.index:
        coef = float(summary.loc[name, 'coef'])
        hr = float(summary.loc[name, 'exp(coef)'])
        p_val = float(summary.loc[name, 'p'])

        results['coefficients'][name] = {
            'estimate': round(coef, 4),
            'std_error': round(float(summary.loc[name, 'se(coef)']), 4),
            'z_value': round(float(summary.loc[name, 'z']), 4),
            'p_value': round(p_val, 6),
        }

        results['hazard_ratios'][name] = {
            'HR': round(hr, 4),
            'ci_lower': round(float(summary.loc[name, 'exp(coef) lower 95%']), 4),
            'ci_upper': round(float(summary.loc[name, 'exp(coef) upper 95%']), 4),
        }

    return results, cph
```

### 6.2 Kaplan-Meier Estimation

```python
from lifelines import KaplanMeierFitter

def fit_kaplan_meier(df, duration_col, event_col, group_col=None):
    """Fit Kaplan-Meier survival curve(s).

    Args:
        df: DataFrame
        duration_col: time-to-event column
        event_col: event indicator (1=event, 0=censored)
        group_col: optional grouping variable for stratified analysis

    Returns:
        dict with survival probabilities, median survival, log-rank test
    """
    results = {
        'model_type': 'Kaplan-Meier Survival Estimation',
        'n_observations': len(df),
        'groups': {},
    }

    if group_col:
        groups = df[group_col].unique()
        kmf_dict = {}

        for group in groups:
            mask = df[group_col] == group
            kmf = KaplanMeierFitter()
            kmf.fit(df.loc[mask, duration_col], df.loc[mask, event_col], label=str(group))
            kmf_dict[str(group)] = kmf

            median_survival = kmf.median_survival_time_
            results['groups'][str(group)] = {
                'n': int(mask.sum()),
                'n_events': int(df.loc[mask, event_col].sum()),
                'median_survival': round(float(median_survival), 2) if not np.isinf(median_survival) else None,
                'survival_at_timepoints': {},
            }

            # Survival at key time points
            for t in [12, 24, 36, 60]:
                if t <= df[duration_col].max():
                    sf = kmf.predict(t)
                    results['groups'][str(group)]['survival_at_timepoints'][f't={t}'] = round(float(sf), 4)

        # Log-rank test
        from lifelines.statistics import logrank_test
        if len(groups) == 2:
            g1, g2 = groups
            lr = logrank_test(
                df.loc[df[group_col] == g1, duration_col],
                df.loc[df[group_col] == g2, duration_col],
                event_observed_A=df.loc[df[group_col] == g1, event_col],
                event_observed_B=df.loc[df[group_col] == g2, event_col],
            )
            results['log_rank_test'] = {
                'test_statistic': round(float(lr.test_statistic), 4),
                'p_value': round(float(lr.p_value), 6),
                'significant': lr.p_value < 0.05,
            }

    else:
        kmf = KaplanMeierFitter()
        kmf.fit(df[duration_col], df[event_col])

        median_survival = kmf.median_survival_time_
        results['groups']['all'] = {
            'n': len(df),
            'n_events': int(df[event_col].sum()),
            'median_survival': round(float(median_survival), 2) if not np.isinf(median_survival) else None,
        }

    return results
```

### 6.3 Proportional Hazards Assumption Test

```python
def test_proportional_hazards(cph, df, duration_col, event_col):
    """Test the proportional hazards assumption using Schoenfeld residuals."""
    try:
        results = cph.check_assumptions(df, p_value_threshold=0.05, show_plots=False)
        return {
            'test': 'Schoenfeld residuals test',
            'assumption_met': len(results) == 0,
            'violations': [str(r) for r in results] if results else [],
        }
    except Exception as e:
        return {
            'test': 'Schoenfeld residuals test',
            'error': str(e),
            'note': 'Could not perform PH assumption test'
        }
```

---

## Phase 7: Statistical Tests

**Goal**: Perform common statistical tests as complements to regression models.

### 7.1 Common Tests

```python
from scipy import stats as scipy_stats

def run_statistical_test(test_type, data1, data2=None, **kwargs):
    """Run common statistical tests.

    Args:
        test_type: 't_test', 'paired_t', 'mann_whitney', 'chi_square',
                   'fisher_exact', 'anova', 'kruskal', 'wilcoxon'
        data1: first data array or contingency table
        data2: second data array (for 2-sample tests)

    Returns:
        dict with test statistic, p-value, effect size
    """
    results = {'test_type': test_type}

    if test_type == 't_test':
        stat, p = scipy_stats.ttest_ind(data1, data2, equal_var=kwargs.get('equal_var', True))
        # Cohen's d effect size
        n1, n2 = len(data1), len(data2)
        pooled_std = np.sqrt(((n1-1)*np.std(data1, ddof=1)**2 + (n2-1)*np.std(data2, ddof=1)**2) / (n1+n2-2))
        cohens_d = (np.mean(data1) - np.mean(data2)) / pooled_std if pooled_std > 0 else 0
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
            'cohens_d': round(float(cohens_d), 4),
            'mean_diff': round(float(np.mean(data1) - np.mean(data2)), 4),
        })

    elif test_type == 'paired_t':
        stat, p = scipy_stats.ttest_rel(data1, data2)
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
        })

    elif test_type == 'mann_whitney':
        stat, p = scipy_stats.mannwhitneyu(data1, data2, alternative='two-sided')
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
        })

    elif test_type == 'chi_square':
        # data1 should be a contingency table (2D array)
        chi2, p, dof, expected = scipy_stats.chi2_contingency(data1)
        n = np.sum(data1)
        min_dim = min(np.array(data1).shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if n * min_dim > 0 else 0
        results.update({
            'statistic': round(float(chi2), 4),
            'p_value': round(float(p), 6),
            'degrees_of_freedom': int(dof),
            'cramers_v': round(float(cramers_v), 4),
        })

    elif test_type == 'fisher_exact':
        # data1 should be a 2x2 contingency table
        odds_ratio, p = scipy_stats.fisher_exact(data1)
        results.update({
            'odds_ratio': round(float(odds_ratio), 4),
            'p_value': round(float(p), 6),
        })

    elif test_type == 'anova':
        # data1 should be a list of groups
        stat, p = scipy_stats.f_oneway(*data1)
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
        })

    elif test_type == 'kruskal':
        stat, p = scipy_stats.kruskal(*data1)
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
        })

    elif test_type == 'wilcoxon':
        stat, p = scipy_stats.wilcoxon(data1, data2)
        results.update({
            'statistic': round(float(stat), 4),
            'p_value': round(float(p), 6),
        })

    return results
```

### 7.2 Confidence Intervals

```python
def compute_confidence_interval(data, confidence=0.95, method='normal'):
    """Compute confidence interval for a statistic.

    Args:
        data: array-like data
        confidence: confidence level (default 0.95)
        method: 'normal', 'bootstrap', 'wilson' (for proportions)

    Returns:
        dict with point estimate, CI lower, CI upper
    """
    data = np.array(data)
    alpha = 1 - confidence

    if method == 'normal':
        mean = np.mean(data)
        se = scipy_stats.sem(data)
        ci = scipy_stats.t.interval(confidence, len(data)-1, loc=mean, scale=se)
        return {
            'estimate': round(float(mean), 4),
            'ci_lower': round(float(ci[0]), 4),
            'ci_upper': round(float(ci[1]), 4),
            'confidence': confidence,
            'method': 'normal (t-distribution)',
        }

    elif method == 'bootstrap':
        n_boot = 10000
        boot_means = np.array([
            np.mean(np.random.choice(data, size=len(data), replace=True))
            for _ in range(n_boot)
        ])
        ci_lower = np.percentile(boot_means, 100 * alpha / 2)
        ci_upper = np.percentile(boot_means, 100 * (1 - alpha / 2))
        return {
            'estimate': round(float(np.mean(data)), 4),
            'ci_lower': round(float(ci_lower), 4),
            'ci_upper': round(float(ci_upper), 4),
            'confidence': confidence,
            'method': 'bootstrap (percentile)',
            'n_bootstrap': n_boot,
        }

    elif method == 'wilson':
        # Wilson score interval for proportions
        n = len(data)
        p_hat = np.mean(data)
        z = scipy_stats.norm.ppf(1 - alpha / 2)
        denom = 1 + z**2 / n
        center = (p_hat + z**2 / (2 * n)) / denom
        spread = z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) / denom
        return {
            'estimate': round(float(p_hat), 4),
            'ci_lower': round(float(center - spread), 4),
            'ci_upper': round(float(center + spread), 4),
            'confidence': confidence,
            'method': 'Wilson score',
        }
```

---

## Phase 8: Model Comparison and Selection

**Goal**: Compare multiple models, select best-fitting model.

### 8.1 Model Comparison

```python
def compare_models(models_dict):
    """Compare fitted models using information criteria and likelihood ratios.

    Args:
        models_dict: dict of {name: fitted_model_object}

    Returns:
        comparison table with AIC, BIC, log-likelihood
    """
    comparison = []
    for name, model in models_dict.items():
        entry = {'model': name}
        if hasattr(model, 'aic'):
            entry['aic'] = round(float(model.aic), 2)
        if hasattr(model, 'bic'):
            entry['bic'] = round(float(model.bic), 2)
        if hasattr(model, 'llf'):
            entry['log_likelihood'] = round(float(model.llf), 4)
        if hasattr(model, 'nobs'):
            entry['n_obs'] = int(model.nobs)
        if hasattr(model, 'rsquared'):
            entry['r_squared'] = round(float(model.rsquared), 4)
        if hasattr(model, 'prsquared'):
            entry['pseudo_r_squared'] = round(float(model.prsquared), 4)
        comparison.append(entry)

    # Sort by AIC
    comparison.sort(key=lambda x: x.get('aic', float('inf')))

    return {
        'comparison': comparison,
        'best_model': comparison[0]['model'] if comparison else None,
        'criterion': 'AIC (lower is better)',
    }
```

### 8.2 Likelihood Ratio Test

```python
def likelihood_ratio_test(model_reduced, model_full):
    """Perform likelihood ratio test comparing nested models.

    Args:
        model_reduced: restricted (simpler) model
        model_full: unrestricted (complex) model

    Returns:
        dict with LR statistic, df, p-value
    """
    llr_stat = -2 * (model_reduced.llf - model_full.llf)
    df_diff = model_full.df_model - model_reduced.df_model
    p_value = scipy_stats.chi2.sf(llr_stat, df_diff)

    return {
        'test': 'Likelihood Ratio Test',
        'lr_statistic': round(float(llr_stat), 4),
        'degrees_of_freedom': int(df_diff),
        'p_value': round(float(p_value), 6),
        'prefer_full_model': p_value < 0.05,
    }
```

---

## Phase 9: Report Generation

**Goal**: Generate comprehensive statistical analysis report.

### 9.1 Markdown Report

```python
def generate_report(analysis_results, title="Statistical Analysis Report"):
    """Generate a markdown statistical analysis report.

    Args:
        analysis_results: dict with all analysis outputs
    """
    report = []
    report.append(f"# {title}\n")

    # Data summary
    if 'data_summary' in analysis_results:
        ds = analysis_results['data_summary']
        report.append("## Data Summary\n")
        report.append(f"- **Observations**: {ds['n_rows']}")
        report.append(f"- **Variables**: {ds['n_cols']}")
        if any(v > 0 for v in ds['missing_values'].values()):
            report.append("- **Missing values**:")
            for col, n in ds['missing_values'].items():
                if n > 0:
                    report.append(f"  - {col}: {n} ({round(n/ds['n_rows']*100, 1)}%)")
        report.append("")

    # Model results
    for key, value in analysis_results.items():
        if key == 'data_summary':
            continue

        if isinstance(value, dict) and 'model_type' in value:
            report.append(f"## {value['model_type']}\n")

            if 'formula' in value:
                report.append(f"**Formula**: `{value['formula']}`\n")
            if 'n_observations' in value:
                report.append(f"**N**: {value['n_observations']}\n")

            # Coefficients table
            if 'coefficients' in value:
                report.append("### Coefficients\n")
                report.append("| Variable | Estimate | Std Error | z/t | p-value | 95% CI |")
                report.append("|----------|----------|-----------|-----|---------|--------|")
                for var, coefs in value['coefficients'].items():
                    if isinstance(coefs, dict) and 'estimate' in coefs:
                        ci = f"({coefs.get('ci_lower', '')}, {coefs.get('ci_upper', '')})"
                        sig = " *" if coefs.get('p_value', 1) < 0.05 else ""
                        t_val = coefs.get('z_value', coefs.get('t_value', ''))
                        report.append(f"| {var} | {coefs['estimate']} | {coefs.get('std_error', '')} | {t_val} | {coefs['p_value']}{sig} | {ci} |")
                report.append("")

            # Odds ratios table
            if 'odds_ratios' in value:
                report.append("### Odds Ratios\n")
                report.append("| Variable | OR | 95% CI |")
                report.append("|----------|-----|--------|")
                for var, ors in value['odds_ratios'].items():
                    if isinstance(ors, dict) and 'OR' in ors:
                        ci = f"({ors.get('ci_lower', '')}, {ors.get('ci_upper', '')})"
                        report.append(f"| {var} | {ors['OR']} | {ci} |")
                report.append("")

            # Hazard ratios table
            if 'hazard_ratios' in value:
                report.append("### Hazard Ratios\n")
                report.append("| Variable | HR | 95% CI |")
                report.append("|----------|-----|--------|")
                for var, hrs in value['hazard_ratios'].items():
                    if isinstance(hrs, dict) and 'HR' in hrs:
                        ci = f"({hrs.get('ci_lower', '')}, {hrs.get('ci_upper', '')})"
                        report.append(f"| {var} | {hrs['HR']} | {ci} |")
                report.append("")

            # Model fit statistics
            report.append("### Model Fit\n")
            for stat in ['r_squared', 'adj_r_squared', 'pseudo_r_squared',
                         'aic', 'bic', 'log_likelihood', 'concordance_index']:
                if stat in value and value[stat] is not None:
                    label = stat.replace('_', ' ').title()
                    report.append(f"- **{label}**: {value[stat]}")
            report.append("")

    return '\n'.join(report)
```

---

## BixBench Question Patterns

This section documents common BixBench question patterns and how to handle them.

### Pattern 1: Odds Ratio from Logistic/Ordinal Regression

**Question format**: "What is the odds ratio of [outcome] associated with [exposure] in [model type] regression?"

**Workflow**:
1. Load dataset
2. Identify outcome (ordinal -> ordinal logit, binary -> logistic)
3. Identify exposure/predictor
4. Fit appropriate model
5. Extract OR from exponentiated coefficient
6. Report OR with CI and p-value

**Example**: "What is the odds ratio of disease severity associated with treatment exposure in ordinal logistic regression?"
- Outcome: Disease severity (ordinal: mild, moderate, severe, critical)
- Predictor: Treatment exposure (binary: exposed/not exposed)
- Model: Ordinal logistic (proportional odds)
- Answer: exp(coefficient for treatment exposure)

### Pattern 2: Percentage Reduction in Odds

**Question format**: "What is the percentage reduction in odds ratio for [outcome] after adjusting for [confounders]?"

**Workflow**:
1. Fit unadjusted model: outcome ~ exposure
2. Fit adjusted model: outcome ~ exposure + confounders
3. Calculate: % reduction = (OR_unadjusted - OR_adjusted) / OR_unadjusted * 100

### Pattern 3: Interaction Effects

**Question format**: "What is the odds ratio associated with [interaction] using [model]?"

**Workflow**:
1. Create interaction term: exposure1 * exposure2
2. Fit model with main effects + interaction
3. Extract interaction coefficient
4. Interpret: OR for interaction = exp(beta_interaction)

### Pattern 4: Survival Analysis Questions

**Question format**: "What is the hazard ratio for [treatment] in Cox regression?"

**Workflow**:
1. Load survival data (time, event, covariates)
2. Fit Cox PH model
3. Extract HR = exp(coefficient)
4. Report with CI, p-value, concordance index

### Pattern 5: Model Diagnostics

**Question format**: "Is the proportional odds assumption met?" or "What is the R-squared?"

**Workflow**:
1. Fit model
2. Run diagnostic tests
3. Report test statistics and conclusions

### Pattern 6: Mixed-Effects Model Results

**Question format**: "What is the coefficient for [predictor] in a mixed-effects model with random intercepts for [grouping]?"

**Workflow**:
1. Fit LMM/GLMM with specified random effects structure
2. Extract fixed effects coefficients
3. Report ICC, random effects variance

---

## Completeness Checklist

Before finalizing any statistical analysis, verify:

- [ ] **Data validated**: N, missing values, variable types confirmed
- [ ] **Model appropriate**: Outcome type matches model family
- [ ] **Assumptions checked**: Relevant diagnostics performed
- [ ] **Effect sizes reported**: OR/HR/Cohen's d with CIs
- [ ] **P-values reported**: With appropriate multiple testing correction if needed
- [ ] **Model fit assessed**: R-squared, AIC/BIC, concordance
- [ ] **Results interpreted**: Plain-language interpretation of key findings
- [ ] **Precision correct**: Numbers rounded to appropriate decimal places
- [ ] **Confounders addressed**: Adjusted analyses if applicable
- [ ] **Sensitivity analyses**: At least one alternative model considered

---

## Python Package Requirements

```
statsmodels>=0.14.0
scikit-learn>=1.3.0
lifelines>=0.27.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
```

## ToolUniverse Integration

While this skill is primarily computational, ToolUniverse tools can be used for:

| Use Case | Tools |
|----------|-------|
| Clinical trial data retrieval | `clinical_trials_search`, `get_clinical_trial_eligibility_criteria` |
| Drug safety outcomes | `FAERS_calculate_disproportionality`, `FAERS_stratify_by_demographics` |
| Gene-disease associations | `OpenTargets_target_disease_evidence` |
| Biomarker data | `fda_pharmacogenomic_biomarkers` |
| Literature context | `PubMed_search_articles` |
