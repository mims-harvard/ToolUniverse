# Ordinal Logistic Regression Reference

Complete guide to ordinal logistic regression (proportional odds model) for ordered categorical outcomes.

## When to Use Ordinal Logistic Regression

Use ordinal logit when your outcome has:
- **3 or more levels** (if 2 levels, use binary logistic)
- **Natural ordering** (mild < moderate < severe)
- **No numeric interpretation** (can't assume equal spacing between levels)

**Examples**:
- Disease severity: mild, moderate, severe, critical
- Cancer stage: I, II, III, IV
- Pain score: none, mild, moderate, severe
- Likert scale: strongly disagree, disagree, neutral, agree, strongly agree
- Performance status: 0, 1, 2, 3, 4

## Basic Ordinal Logit Model

```python
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# Load data
df = pd.read_csv('data.csv')

# Define order of outcome levels
severity_order = ['Mild', 'Moderate', 'Severe', 'Critical']

# Convert to ordered categorical
df['severity'] = pd.Categorical(df['severity'],
                                 categories=severity_order,
                                 ordered=True)

# Encode as integer codes (0, 1, 2, 3)
y = df['severity'].cat.codes

# Prepare predictors (handle categorical variables)
X = df[['exposure', 'age', 'sex']].copy()
X = pd.get_dummies(X, drop_first=True, dtype=float)

# Fit proportional odds model
model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0, maxiter=200)

# Print summary
print(fit.summary())
```

## Extracting Odds Ratios

```python
# Number of outcome levels
n_levels = len(df['severity'].cat.categories)
n_thresholds = n_levels - 1

# Number of predictors
n_predictors = len(X.columns)

# Parameters are: [predictors, thresholds]
# Extract predictor coefficients only
predictor_params = fit.params[:n_predictors]
predictor_names = X.columns.tolist()

# Odds ratios
odds_ratios = np.exp(predictor_params)

# Confidence intervals
conf_int = fit.conf_int()
conf_int_exp = np.exp(conf_int.iloc[:n_predictors, :])

# Print results
print("\n=== Odds Ratios ===")
for i, name in enumerate(predictor_names):
    or_val = odds_ratios[i]
    ci_lower = conf_int_exp.iloc[i, 0]
    ci_upper = conf_int_exp.iloc[i, 1]
    p_val = fit.pvalues[i]

    print(f"\n{name}:")
    print(f"  OR: {or_val:.4f}")
    print(f"  95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")
```

## Interpreting Odds Ratios

**Proportional odds assumption**: The odds ratio is constant across all levels of the outcome.

```python
# Example: OR = 2.5 for exposure
# Interpretation:
# - Exposure increases odds of being in higher severity category by factor of 2.5
# - This applies to ALL cutpoints:
#   * Odds of moderate vs mild
#   * Odds of severe vs (moderate or mild)
#   * Odds of critical vs (severe or moderate or mild)
```

### Interpretation Function

```python
def interpret_ordinal_or(or_val, ci_lower, ci_upper, p_val, var_name, outcome_name):
    """Generate interpretation for ordinal OR."""
    if or_val > 1:
        direction = "higher"
        magnitude = (or_val - 1) * 100
        interp = f"{var_name} is associated with {magnitude:.1f}% increased odds of being in a higher {outcome_name} category"
    elif or_val < 1:
        direction = "lower"
        magnitude = (1 - or_val) * 100
        interp = f"{var_name} is associated with {magnitude:.1f}% decreased odds of being in a higher {outcome_name} category"
    else:
        interp = f"{var_name} has no association with {outcome_name}"

    sig = "statistically significant" if p_val < 0.05 else "not statistically significant"

    return f"{interp} (OR={or_val:.4f}, 95% CI [{ci_lower:.4f}, {ci_upper:.4f}], p={p_val:.6f}, {sig})"

# Example usage
print(interpret_ordinal_or(2.5, 1.8, 3.5, 0.001, "BCG vaccination", "COVID-19 severity"))
```

## Thresholds (Cut Points)

```python
# Extract thresholds
threshold_params = fit.params[n_predictors:]
threshold_names = [f"Threshold_{i}" for i in range(n_thresholds)]

print("\n=== Thresholds ===")
for i, name in enumerate(threshold_names):
    threshold = threshold_params[i]
    print(f"{name} ({severity_order[i]}|{severity_order[i+1]}): {threshold:.4f}")
```

**Interpretation**: Thresholds represent the log-odds cutpoints between adjacent categories when all predictors are 0.

## Testing Proportional Odds Assumption

**Critical assumption**: The odds ratio is the same for all cutpoints.

### Brant Test (Approximation)

```python
import statsmodels.api as sm

def test_proportional_odds(df, outcome_col, predictors, order):
    """Test proportional odds assumption."""
    df_test = df.copy()
    df_test[outcome_col] = pd.Categorical(df_test[outcome_col],
                                          categories=order,
                                          ordered=True)
    y_codes = df_test[outcome_col].cat.codes
    n_levels = len(order)

    # Prepare predictors
    X = df_test[predictors].copy()
    X = pd.get_dummies(X, drop_first=True, dtype=float)
    X_const = sm.add_constant(X)

    # Fit binary logit at each cutpoint
    results = {}
    for k in range(n_levels - 1):
        y_binary = (y_codes > k).astype(int)
        try:
            binary_model = sm.Logit(y_binary, X_const).fit(disp=0)
            results[k] = {
                'cutpoint': f"{order[k]}|{order[k+1]}",
                'coefs': binary_model.params[1:].to_dict()  # Skip intercept
            }
        except Exception as e:
            print(f"Failed at cutpoint {k}: {e}")

    # Compare coefficients across cutpoints
    print("\n=== Proportional Odds Test ===")
    print("Coefficients should be similar across cutpoints:\n")

    for pred in X.columns:
        coefs = [results[k]['coefs'][pred] for k in results if pred in results[k]['coefs']]
        if len(coefs) > 1:
            coef_range = max(coefs) - min(coefs)
            print(f"{pred}:")
            for k in results:
                print(f"  {results[k]['cutpoint']}: {results[k]['coefs'].get(pred, 'N/A'):.4f}")
            print(f"  Range: {coef_range:.4f}")
            if coef_range > 0.5:
                print(f"  ⚠️  Warning: Large variation suggests violation of proportional odds")
            else:
                print(f"  ✅ Proportional odds likely satisfied")
            print()

    return results

# Run test
test_proportional_odds(df, 'severity', ['exposure', 'age', 'sex'], severity_order)
```

### What to Do if Assumption Violated

1. **Partial proportional odds model** - Allow some predictors to vary across cutpoints
2. **Multinomial logistic regression** - Treat outcome as nominal (loses ordering info)
3. **Alternative link functions** - Try probit instead of logit
4. **Transform outcome** - Consider different categorization

```python
# Multinomial logit as alternative (if PO violated)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

le = LabelEncoder()
y_encoded = le.fit_transform(df['severity'])

X_array = pd.get_dummies(df[['exposure', 'age', 'sex']], drop_first=True, dtype=float).values

model_multinom = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
model_multinom.fit(X_array, y_encoded)

print("Multinomial model fitted (proportional odds not assumed)")
```

## Model Fit Statistics

```python
# Log-likelihood
print(f"Log-likelihood: {fit.llf:.4f}")

# AIC/BIC
print(f"AIC: {fit.aic:.2f}")
print(f"BIC: {fit.bic:.2f}")

# Number of observations
print(f"N: {len(y)}")

# Pseudo R-squared (not directly available, compute manually)
# McFadden's R²
ll_null = OrderedModel(y, np.ones((len(y), 1)), distr='logit').fit(disp=0).llf
pseudo_r2 = 1 - (fit.llf / ll_null)
print(f"Pseudo R²: {pseudo_r2:.4f}")
```

## Prediction

```python
# Predicted probabilities for each outcome level
pred_probs = fit.model.predict(fit.params, exog=X)

# pred_probs is an array of shape (n_obs, n_levels)
# Each row sums to 1

# Add to dataframe
for i, level in enumerate(df['severity'].cat.categories):
    df[f'prob_{level}'] = pred_probs[:, i]

# Predicted category (highest probability)
df['predicted_severity'] = df['severity'].cat.categories[pred_probs.argmax(axis=1)]

# Show first few predictions
print(df[['severity', 'predicted_severity', 'prob_Mild', 'prob_Moderate', 'prob_Severe']].head())
```

## Complete Example: COVID-19 Severity

```python
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# Simulated COVID-19 severity data
np.random.seed(42)
n = 500

df = pd.DataFrame({
    'age': np.random.normal(55, 15, n),
    'bcg_vaccination': np.random.binomial(1, 0.6, n),
    'comorbidities': np.random.binomial(1, 0.3, n),
    'severity': np.random.choice(['Mild', 'Moderate', 'Severe'], n, p=[0.5, 0.3, 0.2])
})

# Define ordered outcome
severity_order = ['Mild', 'Moderate', 'Severe']
df['severity'] = pd.Categorical(df['severity'], categories=severity_order, ordered=True)
y = df['severity'].cat.codes

# Prepare predictors
X = df[['age', 'bcg_vaccination', 'comorbidities']].copy()

# Fit model
model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0)

# Extract results
n_predictors = len(X.columns)
ors = np.exp(fit.params[:n_predictors])
ci = np.exp(fit.conf_int().iloc[:n_predictors, :])

print("=== COVID-19 Severity Analysis ===\n")
print("Outcome: Mild → Moderate → Severe\n")

for i, var in enumerate(X.columns):
    or_val = ors[i]
    ci_lower = ci.iloc[i, 0]
    ci_upper = ci.iloc[i, 1]
    p_val = fit.pvalues[i]

    print(f"{var}:")
    print(f"  OR: {or_val:.4f} (95% CI: {ci_lower:.4f}-{ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")

    if var == 'bcg_vaccination' and or_val < 1 and p_val < 0.05:
        pct_reduction = (1 - or_val) * 100
        print(f"  Interpretation: BCG vaccination reduces odds of higher severity by {pct_reduction:.1f}%")
    print()
```

## BixBench Question Pattern

**Typical question**: "What is the odds ratio of COVID-19 severity associated with BCG vaccination in ordinal logistic regression?"

**Solution**:
1. Identify ordinal outcome (severity levels)
2. Define ordering (mild → moderate → severe)
3. Fit ordinal logistic regression
4. Extract OR for BCG vaccination predictor
5. Report OR with CI and p-value

```python
# Answer format
or_bcg = ors[X.columns.get_loc('bcg_vaccination')]
ci_lower_bcg = ci.iloc[X.columns.get_loc('bcg_vaccination'), 0]
ci_upper_bcg = ci.iloc[X.columns.get_loc('bcg_vaccination'), 1]

print(f"Answer: {or_bcg:.4f}")
print(f"95% CI: ({ci_lower_bcg:.4f}, {ci_upper_bcg:.4f})")
```

## Common Issues

### Issue 1: Convergence Failure

**Problem**: Model doesn't converge.

**Solutions**:
```python
# Solution 1: Increase max iterations
fit = model.fit(method='bfgs', disp=0, maxiter=500)

# Solution 2: Try different optimizer
fit = model.fit(method='nm', disp=0)  # Nelder-Mead

# Solution 3: Scale predictors
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)
fit = OrderedModel(y, X_scaled, distr='logit').fit(method='bfgs', disp=0)
```

### Issue 2: Separation

**Problem**: Predictor perfectly separates some categories.

**Check**:
```python
# Check crosstabs
for pred in ['bcg_vaccination', 'comorbidities']:
    print(f"\n{pred} by severity:")
    print(pd.crosstab(df[pred], df['severity']))
```

**Solution**: Remove problematic predictor or use regularization.

### Issue 3: Small Sample Size

**Problem**: Too few observations per category.

**Rule of thumb**: Need at least 10 events per predictor per category.

```python
# Check sample size requirements
n_predictors = len(X.columns)
n_per_level = df['severity'].value_counts()

print("\nSample size check:")
for level, count in n_per_level.items():
    ratio = count / n_predictors
    print(f"{level}: {count} obs ({ratio:.1f} per predictor)")
    if ratio < 10:
        print(f"  ⚠️  Warning: Small sample size for {level}")
```

## Reporting Template

```python
def report_ordinal_logit(fit, X, outcome_levels):
    """Generate publication-ready report."""
    n_predictors = len(X.columns)

    report = []
    report.append("=== Ordinal Logistic Regression Results ===\n")
    report.append(f"Outcome levels: {' → '.join(outcome_levels)}")
    report.append(f"N = {len(X)}")
    report.append(f"AIC = {fit.aic:.2f}\n")

    report.append("Odds Ratios (95% CI):\n")
    ors = np.exp(fit.params[:n_predictors])
    ci = np.exp(fit.conf_int().iloc[:n_predictors, :])

    for i, var in enumerate(X.columns):
        or_val = ors[i]
        ci_lower = ci.iloc[i, 0]
        ci_upper = ci.iloc[i, 1]
        p_val = fit.pvalues[i]
        sig = "*" if p_val < 0.05 else ""

        report.append(f"  {var}: OR={or_val:.4f} ({ci_lower:.4f}-{ci_upper:.4f}), p={p_val:.6f}{sig}")

    return "\n".join(report)

print(report_ordinal_logit(fit, X, severity_order))
```
