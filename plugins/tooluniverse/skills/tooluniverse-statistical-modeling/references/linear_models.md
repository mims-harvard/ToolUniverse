# Linear Models and Mixed-Effects Reference

Complete guide to linear regression and mixed-effects models.

## Ordinary Least Squares (OLS) Regression

### Basic Linear Regression

```python
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Method 1: Formula API (recommended)
model = smf.ols('outcome ~ predictor1 + predictor2 + age', data=df).fit()

# Method 2: Matrix API
X = sm.add_constant(df[['predictor1', 'predictor2', 'age']])
y = df['outcome']
model = sm.OLS(y, X).fit()

# Print summary
print(model.summary())
```

### Interpreting Coefficients

```python
# Extract coefficients
coefs = model.params
se = model.bse
t_vals = model.tvalues
p_vals = model.pvalues
ci = model.conf_int()

for var in coefs.index:
    print(f"\n{var}:")
    print(f"  Coefficient: {coefs[var]:.4f}")
    print(f"  Std Error: {se[var]:.4f}")
    print(f"  t-value: {t_vals[var]:.4f}")
    print(f"  p-value: {p_vals[var]:.6f}")
    print(f"  95% CI: ({ci.loc[var, 0]:.4f}, {ci.loc[var, 1]:.4f})")
```

### Model Fit Statistics

```python
# R-squared
print(f"R-squared: {model.rsquared:.4f}")
print(f"Adjusted R-squared: {model.rsquared_adj:.4f}")

# F-statistic
print(f"F-statistic: {model.fvalue:.4f}")
print(f"F-test p-value: {model.f_pvalue:.6f}")

# AIC/BIC
print(f"AIC: {model.aic:.2f}")
print(f"BIC: {model.bic:.2f}")

# Root mean squared error
rmse = np.sqrt(model.mse_resid)
print(f"RMSE: {rmse:.4f}")
```

## Diagnostics

### Residual Normality

```python
from scipy import stats as scipy_stats

# Shapiro-Wilk test
residuals = model.resid
sw_stat, sw_p = scipy_stats.shapiro(residuals)

print(f"Shapiro-Wilk test:")
print(f"  Statistic: {sw_stat:.4f}")
print(f"  p-value: {sw_p:.6f}")
if sw_p > 0.05:
    print("  ✅ Residuals appear normally distributed")
else:
    print("  ⚠️  Residuals may not be normally distributed")
```

### Homoscedasticity (Equal Variance)

```python
from statsmodels.stats.diagnostic import het_breuschpagan

# Breusch-Pagan test
bp_stat, bp_p, _, _ = het_breuschpagan(residuals, model.model.exog)

print(f"\nBreusch-Pagan test:")
print(f"  Statistic: {bp_stat:.4f}")
print(f"  p-value: {bp_p:.6f}")
if bp_p > 0.05:
    print("  ✅ Homoscedasticity assumption met")
else:
    print("  ⚠️  Heteroscedasticity detected")
    print("  Consider: robust standard errors, log transformation, or WLS")
```

### Autocorrelation

```python
from statsmodels.stats.stattools import durbin_watson

# Durbin-Watson test
dw = durbin_watson(residuals)

print(f"\nDurbin-Watson statistic: {dw:.4f}")
if 1.5 < dw < 2.5:
    print("  ✅ No autocorrelation detected")
else:
    print("  ⚠️  Possible autocorrelation")
```

### Multicollinearity (VIF)

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

X = model.model.exog
vif_data = []

for i in range(X.shape[1]):
    var_name = model.model.exog_names[i]
    if var_name != 'Intercept':
        vif = variance_inflation_factor(X, i)
        vif_data.append({'variable': var_name, 'VIF': vif})

vif_df = pd.DataFrame(vif_data)
print("\nVariance Inflation Factors:")
print(vif_df)

# Rule of thumb: VIF > 10 indicates multicollinearity
if (vif_df['VIF'] > 10).any():
    print("\n⚠️  High multicollinearity detected (VIF > 10)")
    print("Consider: removing correlated predictors or PCA")
```

## Linear Mixed-Effects Models (LMM)

### When to Use LMM

Use LMM when:
- **Repeated measures** (same subject measured multiple times)
- **Nested/clustered data** (patients within hospitals)
- **Hierarchical structure** (students within schools)
- **Need to model between-subject and within-subject variation**

### Random Intercept Model

```python
import statsmodels.formula.api as smf

# Random intercepts for subjects
model = smf.mixedlm('outcome ~ treatment + time',
                     data=df,
                     groups=df['subject_id'])
fit = model.fit(reml=True)

print(fit.summary())
```

### Random Slope Model

```python
# Random slopes for time (subjects have different time trends)
model = smf.mixedlm('outcome ~ treatment + time',
                     data=df,
                     groups=df['subject_id'],
                     re_formula='~time')
fit = model.fit(reml=True)
```

### Fixed Effects Interpretation

```python
# Extract fixed effects
fe_params = fit.fe_params
fe_pvalues = fit.pvalues
fe_ci = fit.conf_int()

print("Fixed Effects:")
for var in fe_params.index:
    coef = fe_params[var]
    p_val = fe_pvalues[var]
    ci_lower = fe_ci.loc[var, 0]
    ci_upper = fe_ci.loc[var, 1]

    print(f"\n{var}:")
    print(f"  Coefficient: {coef:.4f}")
    print(f"  95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")
```

### Random Effects Variance

```python
# Group (subject) variance
cov_re = fit.cov_re
if hasattr(cov_re, 'values'):
    group_var = cov_re.iloc[0, 0]
else:
    group_var = float(cov_re)

# Residual variance
resid_var = fit.scale

print(f"\nRandom Effects Variance:")
print(f"  Between-subject (Group): {group_var:.4f}")
print(f"  Within-subject (Residual): {resid_var:.4f}")
```

### Intraclass Correlation Coefficient (ICC)

```python
# ICC: proportion of variance due to grouping
icc = group_var / (group_var + resid_var)

print(f"\nICC: {icc:.4f}")
print(f"Interpretation: {icc*100:.1f}% of variance is between subjects")

if icc > 0.1:
    print("  ✅ Substantial clustering - LMM appropriate")
else:
    print("  ⚠️  Low clustering - OLS may be sufficient")
```

## Complete Example: Longitudinal Study

```python
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

# Simulated longitudinal data
np.random.seed(42)
n_subjects = 50
n_timepoints = 4

data = []
for subject_id in range(n_subjects):
    treatment = np.random.binomial(1, 0.5)
    baseline = np.random.normal(100, 10)

    for time in range(n_timepoints):
        # Treatment effect + time trend + random noise
        outcome = baseline + treatment * 5 + time * 2 + np.random.normal(0, 3)
        data.append({
            'subject_id': subject_id,
            'treatment': treatment,
            'time': time,
            'outcome': outcome
        })

df = pd.DataFrame(data)

print("=== Longitudinal Analysis ===\n")

# 1. OLS (ignoring repeated measures - WRONG)
print("1. OLS (incorrect for repeated measures):\n")
ols_model = smf.ols('outcome ~ treatment + time', data=df).fit()
print(f"Treatment effect: {ols_model.params['treatment']:.4f}")
print(f"p-value: {ols_model.pvalues['treatment']:.6f}")
print(f"R-squared: {ols_model.rsquared:.4f}\n")

# 2. LMM with random intercepts (correct)
print("2. LMM with random intercepts (correct):\n")
lmm_model = smf.mixedlm('outcome ~ treatment + time',
                         data=df,
                         groups=df['subject_id'])
lmm_fit = lmm_model.fit(reml=True)

print(f"Treatment effect: {lmm_fit.fe_params['treatment']:.4f}")
print(f"p-value: {lmm_fit.pvalues['treatment']:.6f}")

# ICC
group_var = float(lmm_fit.cov_re.iloc[0, 0])
resid_var = float(lmm_fit.scale)
icc = group_var / (group_var + resid_var)
print(f"ICC: {icc:.4f}\n")

# 3. LMM with random slopes (allow different time trends)
print("3. LMM with random slopes:\n")
lmm_slopes = smf.mixedlm('outcome ~ treatment + time',
                          data=df,
                          groups=df['subject_id'],
                          re_formula='~time')
lmm_slopes_fit = lmm_slopes.fit(reml=True)

print(f"Treatment effect: {lmm_slopes_fit.fe_params['treatment']:.4f}")
print(f"p-value: {lmm_slopes_fit.pvalues['treatment']:.6f}\n")

# Model comparison
print("4. Model Comparison:")
print(f"Random intercepts AIC: {lmm_fit.aic:.2f}")
print(f"Random slopes AIC: {lmm_slopes_fit.aic:.2f}")

if lmm_slopes_fit.aic < lmm_fit.aic:
    print("Random slopes model preferred (lower AIC)")
else:
    print("Random intercepts model sufficient")
```

## Weighted Least Squares (WLS)

### When to Use WLS

Use WLS when:
- Heteroscedasticity detected
- Known different precision across observations
- Want to downweight outliers

```python
# Estimate weights from variance model
# Common approach: inverse variance weighting
residuals_sq = model.resid ** 2
weights = 1 / residuals_sq

# Fit WLS
wls_model = sm.WLS(y, X, weights=weights).fit()
print(wls_model.summary())
```

## Robust Standard Errors

### Heteroscedasticity-Consistent Standard Errors

```python
# Use robust standard errors (HC3)
model_robust = model.get_robustcov_results(cov_type='HC3')

print("Robust Standard Errors:")
print(model_robust.summary())
```

## Generalized Estimating Equations (GEE)

### Alternative to LMM for Clustered Data

```python
import statsmodels.api as sm
from statsmodels.genmod.generalized_estimating_equations import GEE
from statsmodels.genmod.families import Gaussian
from statsmodels.genmod.cov_struct import Exchangeable

# GEE for continuous outcome
gee_model = GEE.from_formula('outcome ~ treatment + time',
                              groups='subject_id',
                              data=df,
                              family=Gaussian(),
                              cov_struct=Exchangeable())
gee_fit = gee_model.fit()

print(gee_fit.summary())
```

**GEE vs LMM**:
- **GEE**: Population-averaged effects, requires weaker assumptions
- **LMM**: Subject-specific effects, models random effects explicitly
- Use GEE when interested in marginal effects, LMM when interested in individual trajectories

## Polynomial and Spline Models

### Polynomial Regression

```python
# Add polynomial terms
df['age_sq'] = df['age'] ** 2
df['age_cube'] = df['age'] ** 3

model = smf.ols('outcome ~ age + age_sq + age_cube', data=df).fit()
```

### Natural Cubic Splines

```python
from patsy import dmatrix

# Create spline basis
spline_basis = dmatrix("bs(age, df=4, degree=3)", df, return_type='dataframe')
X_spline = pd.concat([spline_basis, df[['treatment']]], axis=1)
y = df['outcome']

model_spline = sm.OLS(y, X_spline).fit()
```

## Reporting Template

```python
def report_linear_model(model):
    """Generate publication-ready linear model report."""
    report = []
    report.append("=== Linear Regression Results ===\n")
    report.append(f"N = {int(model.nobs)}")
    report.append(f"R² = {model.rsquared:.4f}")
    report.append(f"Adjusted R² = {model.rsquared_adj:.4f}")
    report.append(f"F({model.df_model:.0f}, {model.df_resid:.0f}) = {model.fvalue:.4f}, p = {model.f_pvalue:.6f}\n")

    report.append("Coefficients:\n")
    report.append("Variable | Coef | SE | t | p | 95% CI")
    report.append("---------|------|----|----|---|-------")

    for var in model.params.index:
        coef = model.params[var]
        se = model.bse[var]
        t_val = model.tvalues[var]
        p_val = model.pvalues[var]
        ci = model.conf_int().loc[var]
        sig = "*" if p_val < 0.05 else ""

        report.append(f"{var} | {coef:.4f} | {se:.4f} | {t_val:.4f} | {p_val:.6f}{sig} | ({ci[0]:.4f}, {ci[1]:.4f})")

    return "\n".join(report)

print(report_linear_model(model))
```
