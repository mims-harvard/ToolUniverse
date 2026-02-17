# Logistic Regression Reference

Complete guide to binary logistic regression for biomedical data analysis.

## Binary Logistic Regression

### Basic Model

```python
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Load data
df = pd.read_csv('clinical_data.csv')

# Method 1: Formula API (recommended)
model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)

# Method 2: Matrix API
X = sm.add_constant(df[['exposure', 'age', 'sex']])
y = df['disease']
model = sm.Logit(y, X).fit(disp=0)

# Print summary
print(model.summary())
```

### Extracting Odds Ratios

```python
# Coefficients (log odds)
coefs = model.params
print("Log odds (coefficients):")
print(coefs)

# Odds ratios (exponentiate coefficients)
odds_ratios = np.exp(model.params)
print("\nOdds ratios:")
print(odds_ratios)

# 95% Confidence intervals
conf_int = model.conf_int()
conf_int_exp = np.exp(conf_int)

# Pretty print
for var in model.params.index:
    or_val = odds_ratios[var]
    ci_lower = conf_int_exp.loc[var, 0]
    ci_upper = conf_int_exp.loc[var, 1]
    p_val = model.pvalues[var]

    print(f"\n{var}:")
    print(f"  OR: {or_val:.4f}")
    print(f"  95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")
    print(f"  Significant: {'Yes' if p_val < 0.05 else 'No'}")
```

### Model Fit Statistics

```python
# Pseudo R-squared
print(f"McFadden's R²: {model.prsquared:.4f}")

# Log-likelihood
print(f"Log-likelihood: {model.llf:.4f}")

# AIC/BIC
print(f"AIC: {model.aic:.2f}")
print(f"BIC: {model.bic:.2f}")

# Number of observations
print(f"N: {int(model.nobs)}")
```

## Categorical Predictors

### Manual Dummy Coding

```python
# Create dummy variables
df_encoded = pd.get_dummies(df, columns=['treatment_group'], drop_first=True, dtype=int)

# Fit model
model = smf.logit('disease ~ treatment_group_B + treatment_group_C + age',
                  data=df_encoded).fit(disp=0)
```

### Formula with Categorical Variables

```python
# statsmodels handles categorical automatically with C()
model = smf.logit('disease ~ C(treatment_group) + age', data=df).fit(disp=0)

# Set reference level
model = smf.logit('disease ~ C(treatment_group, Treatment("Control")) + age',
                  data=df).fit(disp=0)
```

## Interaction Terms

### Two-Way Interactions

```python
# Interaction between continuous and binary
model = smf.logit('disease ~ exposure * age + sex', data=df).fit(disp=0)

# The interaction term is 'exposure:age'
interaction_coef = model.params['exposure:age']
interaction_or = np.exp(interaction_coef)
print(f"Interaction OR: {interaction_or:.4f}")
```

### Interpreting Interactions

```python
# Main effects + interaction
# Model: logit(p) = β0 + β1*exposure + β2*age + β3*exposure*age

# OR for exposure depends on age:
# OR(exposure) = exp(β1 + β3*age)

# Example: OR at age=30 vs age=50
beta_exposure = model.params['exposure']
beta_interaction = model.params['exposure:age']

or_age30 = np.exp(beta_exposure + beta_interaction * 30)
or_age50 = np.exp(beta_exposure + beta_interaction * 50)

print(f"OR (exposure) at age 30: {or_age30:.4f}")
print(f"OR (exposure) at age 50: {or_age50:.4f}")
```

## Adjusted vs Unadjusted Analysis

### Percentage Reduction in OR

```python
# Unadjusted (crude) model
model_crude = smf.logit('disease ~ exposure', data=df).fit(disp=0)
or_crude = np.exp(model_crude.params['exposure'])

# Adjusted model
model_adj = smf.logit('disease ~ exposure + age + sex + bmi', data=df).fit(disp=0)
or_adj = np.exp(model_adj.params['exposure'])

# Calculate percentage reduction
pct_reduction = (or_crude - or_adj) / or_crude * 100

print(f"Crude OR: {or_crude:.4f}")
print(f"Adjusted OR: {or_adj:.4f}")
print(f"Percentage reduction: {pct_reduction:.1f}%")

# Interpretation
if pct_reduction > 10:
    print("Strong confounding detected")
elif pct_reduction > 5:
    print("Moderate confounding")
else:
    print("Minimal confounding")
```

## Model Comparison

### Likelihood Ratio Test

```python
from scipy import stats

# Nested models
model_reduced = smf.logit('disease ~ exposure', data=df).fit(disp=0)
model_full = smf.logit('disease ~ exposure + age + sex + bmi', data=df).fit(disp=0)

# LR test statistic
lr_stat = -2 * (model_reduced.llf - model_full.llf)
df_diff = model_full.df_model - model_reduced.df_model
p_value = stats.chi2.sf(lr_stat, df_diff)

print(f"LR statistic: {lr_stat:.4f}")
print(f"df: {df_diff}")
print(f"p-value: {p_value:.6f}")

if p_value < 0.05:
    print("Full model provides significantly better fit")
else:
    print("Additional predictors not significant")
```

### AIC/BIC Comparison

```python
# Fit multiple models
models = {
    'Model 1': smf.logit('disease ~ exposure', data=df).fit(disp=0),
    'Model 2': smf.logit('disease ~ exposure + age', data=df).fit(disp=0),
    'Model 3': smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0),
}

# Compare
print("Model Comparison:")
for name, m in models.items():
    print(f"\n{name}:")
    print(f"  AIC: {m.aic:.2f}")
    print(f"  BIC: {m.bic:.2f}")
    print(f"  Pseudo R²: {m.prsquared:.4f}")

# Best model (lowest AIC)
best_model = min(models.items(), key=lambda x: x[1].aic)
print(f"\nBest model (by AIC): {best_model[0]}")
```

## Prediction

### Predicted Probabilities

```python
# Get predicted probabilities for existing data
df['predicted_prob'] = model.predict(df)

# Predict for new data
new_data = pd.DataFrame({
    'exposure': [1],
    'age': [45],
    'sex': ['M']
})
pred_prob = model.predict(new_data)
print(f"Predicted probability: {pred_prob[0]:.4f}")
```

### Classification

```python
# Binary classification with 0.5 threshold
df['predicted_class'] = (model.predict(df) > 0.5).astype(int)

# Confusion matrix
from sklearn.metrics import confusion_matrix, classification_report
cm = confusion_matrix(df['disease'], df['predicted_class'])
print("Confusion Matrix:")
print(cm)

# Accuracy, precision, recall
print("\nClassification Report:")
print(classification_report(df['disease'], df['predicted_class']))
```

## Diagnostics

### Influential Observations

```python
# Cook's distance
from statsmodels.stats.outliers_influence import OLSInfluence

# Get influence measures
influence = model.get_influence()

# Standardized residuals
std_resid = influence.resid_studentized

# Plot influential points
import matplotlib.pyplot as plt
plt.scatter(range(len(std_resid)), std_resid)
plt.axhline(y=2, color='r', linestyle='--')
plt.axhline(y=-2, color='r', linestyle='--')
plt.xlabel('Observation')
plt.ylabel('Studentized Residual')
plt.title('Influential Observations')
plt.show()
```

### Hosmer-Lemeshow Test

```python
# Goodness of fit test
from statsmodels.stats.diagnostic import _diagnostic_hl

# Not directly available in statsmodels
# Use manual implementation
def hosmer_lemeshow_test(y_true, y_pred, g=10):
    """Hosmer-Lemeshow goodness of fit test."""
    data = pd.DataFrame({'y': y_true, 'pred': y_pred})
    data['decile'] = pd.qcut(data['pred'], g, duplicates='drop')

    obs = data.groupby('decile')['y'].agg(['sum', 'count'])
    exp = data.groupby('decile')['pred'].agg(['sum', 'count'])

    hl_stat = ((obs['sum'] - exp['sum'])**2 / (exp['sum'] * (1 - exp['sum']/exp['count']))).sum()
    p_value = stats.chi2.sf(hl_stat, g-2)

    return hl_stat, p_value

hl_stat, hl_p = hosmer_lemeshow_test(df['disease'], model.predict(df))
print(f"Hosmer-Lemeshow: χ²={hl_stat:.4f}, p={hl_p:.6f}")
```

## Common Issues

### Separation (Perfect Prediction)

**Problem**: One predictor perfectly predicts the outcome.

**Solution**: Use Firth logistic regression (penalized likelihood):

```python
# This requires logistf package (not in standard statsmodels)
# Alternative: Remove the problematic predictor or use regularization

# Check for separation
print("Value counts by predictor:")
print(pd.crosstab(df['exposure'], df['disease']))

# If separation detected, try Ridge logistic
from sklearn.linear_model import LogisticRegression
lr = LogisticRegression(penalty='l2', C=1.0)
lr.fit(df[['exposure', 'age', 'sex']], df['disease'])
```

### Convergence Failure

**Problem**: Model doesn't converge (common with small samples or collinearity).

**Solution**: Increase max iterations or check for collinearity:

```python
# Increase iterations
model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0, maxiter=200)

# Check for collinearity
from statsmodels.stats.outliers_influence import variance_inflation_factor
X = df[['exposure', 'age', 'sex']].copy()
X = pd.get_dummies(X, drop_first=True, dtype=float)
X['const'] = 1

for i, col in enumerate(X.columns[:-1]):
    vif = variance_inflation_factor(X.values, i)
    print(f"{col}: VIF={vif:.2f}")
```

### Quasi-Complete Separation

**Problem**: Predictor almost perfectly separates outcomes.

**Symptoms**: Very large coefficients (>10), very large standard errors.

**Solution**: Use regularization or remove problematic predictor.

## Reporting Template

```python
def report_logistic_regression(model):
    """Generate publication-quality report."""
    report = []
    report.append("=== Logistic Regression Results ===\n")
    report.append(f"N = {int(model.nobs)}")
    report.append(f"Pseudo R² = {model.prsquared:.4f}")
    report.append(f"AIC = {model.aic:.2f}\n")

    report.append("Odds Ratios (95% CI):\n")
    ors = np.exp(model.params)
    ci = np.exp(model.conf_int())

    for var in model.params.index:
        if var == 'Intercept':
            continue
        or_val = ors[var]
        ci_lower = ci.loc[var, 0]
        ci_upper = ci.loc[var, 1]
        p_val = model.pvalues[var]
        sig = "*" if p_val < 0.05 else ""

        report.append(f"  {var}: OR={or_val:.4f} ({ci_lower:.4f}-{ci_upper:.4f}), p={p_val:.4f}{sig}")

    return "\n".join(report)

print(report_logistic_regression(model))
```
