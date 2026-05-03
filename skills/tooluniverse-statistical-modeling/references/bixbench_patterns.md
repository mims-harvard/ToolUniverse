# BixBench Question Patterns

Common BixBench statistical question patterns with solutions.

## Pattern 1: Odds Ratio from Binary Logistic Regression

**Question format**: "What is the odds ratio of [outcome] associated with [exposure]?"

**Example**: "What is the odds ratio of disease associated with exposure to chemical X?"

**Solution**:
```python
import statsmodels.formula.api as smf
import numpy as np

# Fit logistic regression
model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)

# Extract odds ratio
or_exposure = np.exp(model.params['exposure'])
ci = np.exp(model.conf_int())
ci_lower = ci.loc['exposure', 0]
ci_upper = ci.loc['exposure', 1]
p_val = model.pvalues['exposure']

# Answer
print(f"Odds Ratio: {or_exposure:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")
```

---

## Pattern 2: Odds Ratio from Ordinal Logistic Regression

**Question format**: "What is the odds ratio of [ordinal outcome] associated with [exposure] in ordinal logistic regression?"

**Example**: "What is the odds ratio of COVID-19 severity associated with BCG vaccination?"

**Solution**:
```python
from statsmodels.miscmodels.ordinal_model import OrderedModel
import pandas as pd
import numpy as np

# Set up ordered outcome
severity_order = ['Mild', 'Moderate', 'Severe']
df['severity'] = pd.Categorical(df['severity'], categories=severity_order, ordered=True)
y = df['severity'].cat.codes

# Prepare predictors
X = pd.get_dummies(df[['bcg_vaccination', 'age', 'sex']], drop_first=True, dtype=float)

# Fit ordinal logit
model = OrderedModel(y, X, distr='logit').fit(method='bfgs', disp=0)

# Extract OR for BCG vaccination (first predictor)
or_bcg = np.exp(model.params[0])
ci = np.exp(model.conf_int())
ci_lower = ci.iloc[0, 0]
ci_upper = ci.iloc[0, 1]
p_val = model.pvalues[0]

# Answer
print(f"Odds Ratio (BCG): {or_bcg:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")
```

---

## Pattern 3: Percentage Reduction in Odds Ratio

**Question format**: "What is the percentage reduction in odds ratio for [outcome] after adjusting for [confounders]?"

**Example**: "What is the percentage reduction in OR for disease after adjusting for age and sex?"

**Solution**:
```python
# Unadjusted model
model_crude = smf.logit('disease ~ exposure', data=df).fit(disp=0)
or_crude = np.exp(model_crude.params['exposure'])

# Adjusted model
model_adj = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)
or_adj = np.exp(model_adj.params['exposure'])

# Percentage reduction
pct_reduction = (or_crude - or_adj) / or_crude * 100

# Answer
print(f"Crude OR: {or_crude:.4f}")
print(f"Adjusted OR: {or_adj:.4f}")
print(f"Percentage reduction: {pct_reduction:.1f}%")
```

---

## Pattern 4: Hazard Ratio from Cox Regression

**Question format**: "What is the hazard ratio for [exposure] in a Cox proportional hazards model?"

**Example**: "What is the hazard ratio for treatment in a Cox model adjusting for age and stage?"

**Solution**:
```python
from lifelines import CoxPHFitter

# Fit Cox model
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age', 'stage']],
        duration_col='time', event_col='event')

# Extract HR
hr_treatment = cph.hazard_ratios_['treatment']
summary = cph.summary
ci_lower = summary.loc['treatment', 'exp(coef) lower 95%']
ci_upper = summary.loc['treatment', 'exp(coef) upper 95%']
p_val = summary.loc['treatment', 'p']

# Answer
print(f"Hazard Ratio: {hr_treatment:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")
print(f"Concordance: {cph.concordance_index_:.4f}")
```

---

## Pattern 5: Kaplan-Meier Survival Estimate

**Question format**: "What is the Kaplan-Meier survival estimate at time T?"

**Example**: "What is the 5-year survival probability in the treatment group?"

**Solution**:
```python
from lifelines import KaplanMeierFitter

# Subset treatment group
treatment_df = df[df['treatment'] == 1]

# Fit KM
kmf = KaplanMeierFitter()
kmf.fit(treatment_df['time'], treatment_df['event'])

# Survival at 5 years (60 months)
survival_5yr = kmf.predict(60)

# Answer
print(f"5-year survival probability: {survival_5yr:.4f}")
print(f"Median survival time: {kmf.median_survival_time_:.1f} months")
```

---

## Pattern 6: Interaction Effect

**Question format**: "What is the odds ratio associated with the interaction between [A] and [B]?"

**Example**: "What is the OR for the interaction between treatment and biomarker status?"

**Solution**:
```python
# Fit model with interaction
model = smf.logit('outcome ~ treatment * biomarker + age', data=df).fit(disp=0)

# Interaction term
interaction_coef = model.params['treatment:biomarker']
interaction_or = np.exp(interaction_coef)
interaction_p = model.pvalues['treatment:biomarker']

# Answer
print(f"Interaction OR: {interaction_or:.4f}")
print(f"p-value: {interaction_p:.6f}")

# Interpretation
if interaction_p < 0.05:
    print("Significant interaction: effect of treatment varies by biomarker status")
```

---

## Pattern 7: Linear Regression Coefficient

**Question format**: "What is the coefficient for [predictor] in a linear regression model?"

**Example**: "What is the coefficient for BMI in a linear regression of blood pressure?"

**Solution**:
```python
import statsmodels.formula.api as smf

# Fit OLS
model = smf.ols('blood_pressure ~ bmi + age + sex', data=df).fit()

# Extract coefficient
coef_bmi = model.params['bmi']
ci = model.conf_int()
ci_lower = ci.loc['bmi', 0]
ci_upper = ci.loc['bmi', 1]
p_val = model.pvalues['bmi']

# Answer
print(f"Coefficient (BMI): {coef_bmi:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")
print(f"R-squared: {model.rsquared:.4f}")

# Interpretation
print(f"Interpretation: Each 1-unit increase in BMI is associated with {coef_bmi:.2f} mmHg change in blood pressure")
```

---

## Pattern 8: Mixed-Effects Model Coefficient

**Question format**: "What is the coefficient for [predictor] in a mixed-effects model with random intercepts for [grouping]?"

**Example**: "What is the treatment effect in a mixed model with random intercepts for patient?"

**Solution**:
```python
import statsmodels.formula.api as smf

# Fit LMM
model = smf.mixedlm('outcome ~ treatment + time', data=df, groups=df['patient_id']).fit(reml=True)

# Extract fixed effect
coef_treatment = model.fe_params['treatment']
se = model.bse_fe['treatment']
p_val = model.pvalues['treatment']
ci = model.conf_int()
ci_lower = ci.loc['treatment', 0]
ci_upper = ci.loc['treatment', 1]

# Answer
print(f"Coefficient (treatment): {coef_treatment:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")

# ICC
group_var = float(model.cov_re.iloc[0, 0])
resid_var = float(model.scale)
icc = group_var / (group_var + resid_var)
print(f"ICC: {icc:.4f}")
```

---

## Pattern 9: Model Comparison with AIC/BIC

**Question format**: "Which model has better fit according to AIC?"

**Example**: "Compare models with and without interaction term using AIC"

**Solution**:
```python
# Fit models
model1 = smf.logit('outcome ~ A + B', data=df).fit(disp=0)
model2 = smf.logit('outcome ~ A * B', data=df).fit(disp=0)

# Compare
print("Model 1 (no interaction):")
print(f"  AIC: {model1.aic:.2f}")
print(f"  BIC: {model1.bic:.2f}")

print("\nModel 2 (with interaction):")
print(f"  AIC: {model2.aic:.2f}")
print(f"  BIC: {model2.bic:.2f}")

# Answer
if model2.aic < model1.aic:
    print("\nModel 2 preferred (lower AIC)")
else:
    print("\nModel 1 preferred (lower AIC)")
```

---

## Pattern 10: Proportional Odds Assumption Test

**Question format**: "Is the proportional odds assumption met?"

**Example**: "Test if proportional odds assumption holds for ordinal severity model"

**Solution**:
```python
import statsmodels.api as sm

# Fit binary logits at each cutpoint
severity_order = ['Mild', 'Moderate', 'Severe']
df['severity'] = pd.Categorical(df['severity'], categories=severity_order, ordered=True)
y_codes = df['severity'].cat.codes

X = pd.get_dummies(df[['exposure', 'age']], drop_first=True, dtype=float)
X_const = sm.add_constant(X)

# Fit at each cutpoint
coef_by_cutpoint = {}
for k in range(len(severity_order) - 1):
    y_binary = (y_codes > k).astype(int)
    model = sm.Logit(y_binary, X_const).fit(disp=0)
    coef_by_cutpoint[k] = model.params['exposure']

# Check if coefficients similar
coefs = list(coef_by_cutpoint.values())
coef_range = max(coefs) - min(coefs)

print(f"Coefficients by cutpoint: {coefs}")
print(f"Range: {coef_range:.4f}")

# Answer
if coef_range < 0.5:
    print("Proportional odds assumption likely satisfied")
else:
    print("Proportional odds assumption may be violated")
```

---

## Pattern 11: Log-Rank Test

**Question format**: "Is there a significant difference in survival between groups?"

**Example**: "Test if survival differs between treatment and control groups"

**Solution**:
```python
from lifelines.statistics import logrank_test

# Split by group
treatment_group = df['treatment'] == 1
control_group = df['treatment'] == 0

# Log-rank test
result = logrank_test(
    df.loc[treatment_group, 'time'],
    df.loc[control_group, 'time'],
    df.loc[treatment_group, 'event'],
    df.loc[control_group, 'event']
)

# Answer
print(f"Log-rank test statistic: {result.test_statistic:.4f}")
print(f"p-value: {result.p_value:.6f}")

if result.p_value < 0.05:
    print("Survival curves are significantly different")
else:
    print("No significant difference in survival")
```

---

## Pattern 12: R-squared Interpretation

**Question format**: "What is the R-squared of the model?"

**Example**: "What proportion of variance is explained by the linear model?"

**Solution**:
```python
model = smf.ols('outcome ~ predictor1 + predictor2 + age', data=df).fit()

# R-squared
r2 = model.rsquared
adj_r2 = model.rsquared_adj

# Answer
print(f"R-squared: {r2:.4f}")
print(f"Adjusted R-squared: {adj_r2:.4f}")
print(f"Interpretation: {r2*100:.1f}% of variance in outcome is explained by predictors")
```

---

## Pattern 13: Concordance Index Interpretation

**Question format**: "What is the concordance index of the Cox model?"

**Example**: "How well does the Cox model discriminate between patients?"

**Solution**:
```python
# Already fitted cph model
c_index = cph.concordance_index_

# Answer
print(f"Concordance index: {c_index:.4f}")

# Interpretation
if c_index > 0.7:
    print("Good discrimination (C > 0.7)")
elif c_index > 0.6:
    print("Acceptable discrimination (0.6 < C < 0.7)")
else:
    print("Poor discrimination (C < 0.6)")
```

---

## Pattern 14: Coefficient Change After Adjustment

**Question format**: "How does the coefficient change after adjusting for confounders?"

**Example**: "Compare exposure coefficient before and after adjusting for age"

**Solution**:
```python
# Unadjusted
model_crude = smf.ols('outcome ~ exposure', data=df).fit()
coef_crude = model_crude.params['exposure']

# Adjusted
model_adj = smf.ols('outcome ~ exposure + age + sex', data=df).fit()
coef_adj = model_adj.params['exposure']

# Change
absolute_change = coef_adj - coef_crude
pct_change = (coef_adj - coef_crude) / coef_crude * 100

# Answer
print(f"Crude coefficient: {coef_crude:.4f}")
print(f"Adjusted coefficient: {coef_adj:.4f}")
print(f"Absolute change: {absolute_change:.4f}")
print(f"Percentage change: {pct_change:.1f}%")
```

---

## Pattern 15: Stratified Analysis

**Question format**: "What is the odds ratio stratified by [variable]?"

**Example**: "What is the OR for exposure separately in men and women?"

**Solution**:
```python
# Stratify by sex
results_by_sex = {}

for sex in ['M', 'F']:
    df_subset = df[df['sex'] == sex]
    model = smf.logit('outcome ~ exposure + age', data=df_subset).fit(disp=0)

    or_exposure = np.exp(model.params['exposure'])
    ci = np.exp(model.conf_int())

    results_by_sex[sex] = {
        'OR': or_exposure,
        'CI_lower': ci.loc['exposure', 0],
        'CI_upper': ci.loc['exposure', 1],
        'p_value': model.pvalues['exposure']
    }

# Answer
for sex, result in results_by_sex.items():
    print(f"\n{sex}:")
    print(f"  OR: {result['OR']:.4f}")
    print(f"  95% CI: ({result['CI_lower']:.4f}, {result['CI_upper']:.4f})")
    print(f"  p-value: {result['p_value']:.6f}")
```

---

## Quick Reference Table

| Pattern | Model Type | Key Output | Formula Example |
|---------|------------|------------|-----------------|
| 1 | Binary Logistic | Odds Ratio | `logit('y ~ x + z')` |
| 2 | Ordinal Logistic | Odds Ratio | `OrderedModel(y, X)` |
| 3 | Logistic (2 models) | % Reduction | Compare crude vs adjusted |
| 4 | Cox PH | Hazard Ratio | `cph.fit(..., duration_col, event_col)` |
| 5 | Kaplan-Meier | Survival Prob | `kmf.predict(time)` |
| 6 | Logistic + Interaction | Interaction OR | `'y ~ A * B'` |
| 7 | Linear Regression | Coefficient | `ols('y ~ x + z')` |
| 8 | Mixed-Effects | Fixed Effect | `mixedlm(..., groups=...)` |
| 9 | Model Comparison | AIC/BIC | Compare `.aic` values |
| 10 | Ordinal Assumption | PO Test | Binary logits at cutpoints |
| 11 | Survival Comparison | Log-rank | `logrank_test(...)` |
| 12 | Linear Regression | R² | `.rsquared` |
| 13 | Cox PH | C-index | `.concordance_index_` |
| 14 | Any Regression | Coef Change | Compare models |
| 15 | Stratified Analysis | Stratum-specific OR | Subset + fit |

---

## Common Mistakes to Avoid

1. **Forgetting to exponentiate**: Logistic/Cox coefficients are log-odds/log-hazards. Must use `np.exp()` for ORs/HRs.

2. **Wrong variable type**: Ordinal outcomes need `OrderedModel`, not `Logit`.

3. **Missing confounders**: Always check if question specifies "adjusting for" variables.

4. **Interpretation direction**: HR > 1 = worse outcome (higher hazard), OR > 1 = higher odds.

5. **Precision**: Round to requested decimal places (typically 4 for ORs/HRs, 6 for p-values).

6. **CI extraction**: Use `conf_int()` method, not `conf_int` attribute.

7. **Formula syntax**: Interactions use `*`, not `+`. E.g., `'y ~ A * B'` includes A, B, and A:B.

8. **Duration/event cols**: Cox models require explicit `duration_col` and `event_col` parameters.
