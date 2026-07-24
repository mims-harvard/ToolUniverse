# Troubleshooting Guide

Common statistical modeling issues and solutions.

## Convergence Issues

### Problem: Model doesn't converge

**Symptoms**:
```
Warning: Maximum iterations reached
ConvergenceWarning: Maximum Likelihood optimization failed to converge
```

**Solutions**:

1. **Increase max iterations**:
```python
# Logistic regression
model = smf.logit('y ~ x + z', data=df).fit(disp=0, maxiter=500)

# Ordinal logit
model = OrderedModel(y, X, distr='logit').fit(method='bfgs', maxiter=500)

# Cox model (lifelines handles this automatically)
```

2. **Scale predictors**:
```python
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)
model = OrderedModel(y, X_scaled, distr='logit').fit(method='bfgs')
```

3. **Try different optimization method**:
```python
# Try Nelder-Mead instead of BFGS
model = OrderedModel(y, X, distr='logit').fit(method='nm')
```

4. **Check for separation** (see below)

---

## Separation Problems

### Problem: Perfect or quasi-complete separation

**Symptoms**:
- Very large coefficients (>10)
- Very large standard errors
- Warning: "Perfect separation detected"

**Check for separation**:
```python
# Crosstab of predictor vs outcome
for pred in ['exposure', 'treatment']:
    print(f"\n{pred} by outcome:")
    print(pd.crosstab(df[pred], df['outcome']))

# Look for cells with 0 counts - that's separation
```

**Solutions**:

1. **Remove problematic predictor**:
```python
# If one predictor causes separation, exclude it
model = smf.logit('outcome ~ age + sex', data=df).fit(disp=0)  # Exclude 'exposure'
```

2. **Use Firth logistic regression** (penalized likelihood):
```python
# Requires logistf package (not standard)
# Alternative: use Ridge penalty in sklearn

from sklearn.linear_model import LogisticRegression
lr = LogisticRegression(penalty='l2', C=1.0, solver='lbfgs')
lr.fit(X, y)
```

3. **Collapse categories**:
```python
# If categorical predictor has sparse levels, combine them
df['stage_collapsed'] = df['stage'].replace({'I': 'Early', 'II': 'Early',
                                               'III': 'Late', 'IV': 'Late'})
```

4. **Increase sample size** (if possible)

---

## Multicollinearity

### Problem: Predictors highly correlated

**Symptoms**:
- Large standard errors
- VIF > 10
- Coefficients change dramatically when adding/removing predictors

**Check for multicollinearity**:
```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

X = df[['age', 'bmi', 'weight', 'height']].copy()
X['const'] = 1

for i, col in enumerate(X.columns[:-1]):
    vif = variance_inflation_factor(X.values, i)
    print(f"{col}: VIF = {vif:.2f}")
    if vif > 10:
        print(f"  ⚠️  High multicollinearity")
```

**Solutions**:

1. **Remove correlated predictors**:
```python
# Check correlation matrix
corr_matrix = df[['age', 'bmi', 'weight', 'height']].corr()
print(corr_matrix)

# Remove one of highly correlated pairs (r > 0.8)
# E.g., remove weight if weight and BMI are r=0.9
model = smf.ols('outcome ~ age + bmi', data=df).fit()  # Exclude weight
```

2. **Use Ridge regression** (L2 regularization):
```python
from sklearn.linear_model import Ridge

ridge = Ridge(alpha=1.0)
ridge.fit(X, y)
```

3. **Principal Component Analysis**:
```python
from sklearn.decomposition import PCA

pca = PCA(n_components=3)
X_pca = pca.fit_transform(X)
# Use principal components as predictors
```

---

## Heteroscedasticity

### Problem: Non-constant variance of residuals

**Symptoms**:
- Breusch-Pagan test p < 0.05
- Residual plot shows funnel shape

**Check**:
```python
from statsmodels.stats.diagnostic import het_breuschpagan

residuals = model.resid
bp_stat, bp_p, _, _ = het_breuschpagan(residuals, model.model.exog)

if bp_p < 0.05:
    print("⚠️  Heteroscedasticity detected")
```

**Solutions**:

1. **Robust standard errors**:
```python
model_robust = model.get_robustcov_results(cov_type='HC3')
print(model_robust.summary())
```

2. **Log transformation** (if outcome is right-skewed):
```python
df['outcome_log'] = np.log(df['outcome'] + 1)
model = smf.ols('outcome_log ~ x + z', data=df).fit()
```

3. **Weighted Least Squares**:
```python
# Weight by inverse variance
residuals_sq = model.resid ** 2
weights = 1 / residuals_sq
wls_model = sm.WLS(y, X, weights=weights).fit()
```

---

## Non-Normality of Residuals

### Problem: Residuals not normally distributed

**Symptoms**:
- Shapiro-Wilk test p < 0.05
- Q-Q plot deviates from line

**Check**:
```python
from scipy import stats as scipy_stats

residuals = model.resid
sw_stat, sw_p = scipy_stats.shapiro(residuals)

if sw_p < 0.05:
    print("⚠️  Residuals not normally distributed")
```

**Solutions**:

1. **Transform outcome**:
```python
# Log transformation
df['outcome_log'] = np.log(df['outcome'] + 1)

# Square root transformation
df['outcome_sqrt'] = np.sqrt(df['outcome'])

# Box-Cox transformation
from scipy.stats import boxcox
df['outcome_bc'], lambda_param = boxcox(df['outcome'] + 1)
```

2. **Use robust regression**:
```python
from statsmodels.robust.robust_linear_model import RLM

rlm_model = RLM.from_formula('outcome ~ x + z', data=df).fit()
```

3. **Use non-parametric methods**:
```python
# Bootstrap confidence intervals instead of t-tests
```

**Note**: For large samples (n > 30), non-normality is less critical due to Central Limit Theorem.

---

## Missing Data

### Problem: Missing values in predictors or outcome

**Check**:
```python
# Count missing values
missing = df.isnull().sum()
print("\nMissing values:")
print(missing[missing > 0])

# Percentage missing
pct_missing = (missing / len(df) * 100)
print("\nPercentage missing:")
print(pct_missing[pct_missing > 0])
```

**Solutions**:

1. **Complete case analysis** (delete rows with missing):
```python
df_complete = df.dropna(subset=['outcome', 'x', 'z'])
model = smf.ols('outcome ~ x + z', data=df_complete).fit()
```

2. **Mean/median imputation** (simple):
```python
df['age'].fillna(df['age'].mean(), inplace=True)
```

3. **Multiple imputation** (best practice):
```python
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

imputer = IterativeImputer(random_state=42)
df_imputed = pd.DataFrame(imputer.fit_transform(df),
                          columns=df.columns)
```

4. **Missing indicator method**:
```python
# Create indicator for missingness
df['age_missing'] = df['age'].isnull().astype(int)
df['age'].fillna(df['age'].mean(), inplace=True)

# Include indicator in model
model = smf.ols('outcome ~ age + age_missing + x', data=df).fit()
```

---

## Proportional Hazards Violation

### Problem: PH assumption violated in Cox model

**Check**:
```python
# Test PH assumption
results = cph.check_assumptions(df, p_value_threshold=0.05, show_plots=False)

if len(results) > 0:
    print(f"⚠️  PH violated for: {results}")
```

**Solutions**:

1. **Stratify by problematic variable**:
```python
# Don't estimate HR for treatment, but adjust for it
cph_strat = CoxPHFitter()
cph_strat.fit(df, duration_col='time', event_col='event',
              strata=['treatment'])
```

2. **Time-varying coefficients**:
```python
# Allow coefficient to change over time (advanced)
# Interact predictor with time
df['treatment_time'] = df['treatment'] * df['time']
cph.fit(df[['time', 'event', 'treatment', 'treatment_time', 'age']],
        duration_col='time', event_col='event')
```

3. **Use parametric survival model**:
```python
from lifelines import WeibullAFTFitter

# Accelerated failure time model (no PH assumption)
wf = WeibullAFTFitter()
wf.fit(df, duration_col='time', event_col='event')
```

---

## Proportional Odds Violation

### Problem: PO assumption violated in ordinal logit

**Check**:
```python
# Fit binary logits at each cutpoint, compare coefficients
# See ordinal_logistic.md for full test
```

**Solutions**:

1. **Partial proportional odds model**:
```python
# Allow some predictors to vary across cutpoints (requires mord package)
```

2. **Multinomial logistic regression**:
```python
from sklearn.linear_model import LogisticRegression

# Treat outcome as nominal (loses ordering information)
model = LogisticRegression(multi_class='multinomial', solver='lbfgs')
model.fit(X, y)
```

3. **Adjacent category logit** (alternative ordinal model)

---

## Small Sample Size

### Problem: Too few observations per predictor

**Rule of thumb**:
- **Linear regression**: ≥20 observations per predictor
- **Logistic regression**: ≥10 events per predictor
- **Ordinal logit**: ≥10 observations per outcome level per predictor
- **Cox regression**: ≥10 events per predictor

**Check**:
```python
n = len(df)
n_predictors = len(['x', 'z', 'age', 'sex'])  # Your predictors

print(f"Observations per predictor: {n / n_predictors:.1f}")

# For logistic
n_events = df['outcome'].sum()
print(f"Events per predictor: {n_events / n_predictors:.1f}")

if n_events / n_predictors < 10:
    print("⚠️  Small sample size - results may be unreliable")
```

**Solutions**:

1. **Reduce number of predictors**:
```python
# Only include most important predictors
model = smf.logit('outcome ~ exposure + age', data=df).fit(disp=0)
```

2. **Use penalized regression**:
```python
from sklearn.linear_model import LogisticRegression

# Ridge penalty helps with small samples
lr = LogisticRegression(penalty='l2', C=1.0)
lr.fit(X, y)
```

3. **Exact logistic regression** (for very small samples):
```python
# Requires R or specialized packages
```

---

## Outliers and Influential Points

### Problem: Outliers affecting model fit

**Check**:
```python
from statsmodels.stats.outliers_influence import OLSInfluence

influence = model.get_influence()

# Cook's distance
cooks_d = influence.cooks_distance[0]
influential = cooks_d > 4 / len(df)

print(f"Influential points: {influential.sum()}")
print(f"Indices: {df.index[influential].tolist()}")
```

**Solutions**:

1. **Remove outliers** (if justified):
```python
# Remove points with Cook's distance > 4/n
df_clean = df[~influential]
model_clean = smf.ols('outcome ~ x + z', data=df_clean).fit()
```

2. **Robust regression**:
```python
from statsmodels.robust.robust_linear_model import RLM

# Downweights outliers automatically
rlm_model = RLM.from_formula('outcome ~ x + z', data=df).fit()
```

3. **Winsorize extreme values**:
```python
from scipy.stats.mstats import winsorize

# Cap extreme values at 5th and 95th percentiles
df['outcome_wins'] = winsorize(df['outcome'], limits=[0.05, 0.05])
```

---

## Model Selection Uncertainty

### Problem: Unsure which predictors to include

**Solutions**:

1. **Forward selection**:
```python
# Start with null model, add predictors one by one
# Keep if p < 0.05 or AIC improves
```

2. **Backward elimination**:
```python
# Start with full model, remove predictors one by one
# Remove if p > 0.10 or AIC improves
```

3. **LASSO for variable selection**:
```python
from sklearn.linear_model import LogisticRegressionCV

# LASSO automatically selects variables
lasso = LogisticRegressionCV(penalty='l1', solver='saga', cv=5)
lasso.fit(X, y)

# Non-zero coefficients are selected
selected = X.columns[lasso.coef_[0] != 0]
print(f"Selected variables: {selected.tolist()}")
```

4. **Use domain knowledge**:
```python
# Always include clinically important confounders
# Age, sex are usually important in biomedical studies
```

---

## Package-Specific Issues

### statsmodels singular matrix error

**Problem**:
```
LinAlgError: singular matrix
```

**Cause**: Perfect multicollinearity (one predictor is linear combination of others)

**Solution**:
```python
# Check correlation matrix
corr = X.corr()
print(corr)

# Remove one of perfectly correlated predictors
# Or use pd.get_dummies(..., drop_first=True)
```

### lifelines convergence warning

**Problem**:
```
ConvergenceWarning: Newton-Raphson failed to converge
```

**Solutions**:
```python
# 1. Check for separation
# 2. Scale predictors
# 3. Use robust=True
cph.fit(df, duration_col='time', event_col='event', robust=True)
```

---

## Quick Diagnostic Checklist

Before finalizing analysis:

- [ ] Check for missing data
- [ ] Check variable distributions (outliers, skewness)
- [ ] Check for multicollinearity (VIF < 10)
- [ ] Check model convergence
- [ ] Check sample size adequacy
- [ ] Run residual diagnostics
- [ ] Test model assumptions
- [ ] Compare alternative models
- [ ] Perform sensitivity analyses
- [ ] Interpret results in context
