# Cox Proportional Hazards and Survival Analysis Reference

Complete guide to survival analysis using Cox regression and Kaplan-Meier estimation.

## When to Use Survival Analysis

Use survival analysis when:
- **Outcome is time-to-event** (time until death, disease progression, recovery)
- **Censoring present** (some participants didn't experience event by study end)
- **Want to model hazard** (instantaneous rate of event occurrence)

**Examples**:
- Time to death, progression-free survival, overall survival
- Time to hospital readmission, disease recurrence
- Duration of remission, time to treatment failure

## Cox Proportional Hazards Model

### Basic Cox Regression

```python
import pandas as pd
import numpy as np
from lifelines import CoxPHFitter

# Load survival data
# Required columns: duration (time), event (1=event, 0=censored), covariates
df = pd.read_csv('survival_data.csv')

# Initialize and fit Cox model
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age', 'stage']],
        duration_col='time',
        event_col='event')

# Print summary with hazard ratios
cph.print_summary()
```

### Extracting Hazard Ratios

```python
# Get summary table
summary = cph.summary

# Hazard ratios (HR)
hrs = cph.hazard_ratios_

# Print results
print("\n=== Hazard Ratios ===")
for var in summary.index:
    hr = hrs[var]
    ci_lower = summary.loc[var, 'exp(coef) lower 95%']
    ci_upper = summary.loc[var, 'exp(coef) upper 95%']
    p_val = summary.loc[var, 'p']
    coef = summary.loc[var, 'coef']
    se = summary.loc[var, 'se(coef)']

    print(f"\n{var}:")
    print(f"  HR: {hr:.4f}")
    print(f"  95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")
    print(f"  Coefficient: {coef:.4f} (SE: {se:.4f})")
```

### Interpreting Hazard Ratios

**HR > 1**: Increased hazard (worse prognosis, faster time to event)
**HR < 1**: Decreased hazard (better prognosis, slower time to event)
**HR = 1**: No effect on hazard

```python
def interpret_hazard_ratio(hr, ci_lower, ci_upper, p_val, var_name):
    """Interpret hazard ratio."""
    if hr > 1:
        pct_increase = (hr - 1) * 100
        interp = f"{var_name} is associated with {pct_increase:.1f}% increase in hazard (worse prognosis)"
    elif hr < 1:
        pct_decrease = (1 - hr) * 100
        interp = f"{var_name} is associated with {pct_decrease:.1f}% decrease in hazard (better prognosis)"
    else:
        interp = f"{var_name} has no effect on hazard"

    sig = "statistically significant" if p_val < 0.05 else "not statistically significant"

    return f"{interp} (HR={hr:.4f}, 95% CI [{ci_lower:.4f}, {ci_upper:.4f}], p={p_val:.6f}, {sig})"

# Example
print(interpret_hazard_ratio(0.65, 0.45, 0.92, 0.015, "Treatment"))
# Output: "Treatment is associated with 35.0% decrease in hazard (better prognosis)
#          (HR=0.6500, 95% CI [0.4500, 0.9200], p=0.015000, statistically significant)"
```

### Model Fit Statistics

```python
# Concordance index (C-index)
# Measures discrimination ability (similar to AUC)
# 0.5 = random, 1.0 = perfect
print(f"Concordance index: {cph.concordance_index_:.4f}")

# Partial log-likelihood
print(f"Partial log-likelihood: {cph.log_likelihood_:.4f}")

# AIC
if hasattr(cph, 'AIC_partial_'):
    print(f"AIC: {cph.AIC_partial_:.4f}")

# Number of events
print(f"Events: {cph.event_observed.sum()}/{len(cph.event_observed)}")
```

## Testing Proportional Hazards Assumption

**Critical assumption**: The hazard ratio is constant over time.

### Schoenfeld Residuals Test

```python
# Test PH assumption
results = cph.check_assumptions(df, p_value_threshold=0.05, show_plots=False)

if len(results) == 0:
    print("✅ Proportional hazards assumption met for all covariates")
else:
    print(f"⚠️  Proportional hazards assumption violated for: {results}")
```

### What to Do if Assumption Violated

1. **Stratify by problematic variable**
```python
# Stratify by treatment (doesn't estimate HR for treatment)
cph_strat = CoxPHFitter()
cph_strat.fit(df, duration_col='time', event_col='event', strata=['treatment'])
```

2. **Time-varying coefficient**
```python
# Allow coefficient to change over time (advanced)
# Use cph.fit(..., formula='...') with time interactions
```

3. **Parametric survival models**
```python
from lifelines import WeibullAFTFitter

# Accelerated failure time model (doesn't assume PH)
wf = WeibullAFTFitter()
wf.fit(df, duration_col='time', event_col='event')
```

## Kaplan-Meier Survival Curves

### Single Group

```python
from lifelines import KaplanMeierFitter

# Fit Kaplan-Meier estimator
kmf = KaplanMeierFitter()
kmf.fit(df['time'], df['event'], label='All patients')

# Median survival time
median_survival = kmf.median_survival_time_
print(f"Median survival: {median_survival:.1f} months")

# Survival probability at specific times
for t in [12, 24, 36, 60]:
    survival_prob = kmf.predict(t)
    print(f"Survival at {t} months: {survival_prob:.4f}")

# Plot survival curve
kmf.plot_survival_function()
```

### Comparing Groups (Log-Rank Test)

```python
from lifelines.statistics import logrank_test

# Split by treatment group
treatment_group = df['treatment'] == 1
control_group = df['treatment'] == 0

# Fit KM for each group
kmf_treatment = KaplanMeierFitter()
kmf_treatment.fit(df.loc[treatment_group, 'time'],
                  df.loc[treatment_group, 'event'],
                  label='Treatment')

kmf_control = KaplanMeierFitter()
kmf_control.fit(df.loc[control_group, 'time'],
                df.loc[control_group, 'event'],
                label='Control')

# Median survival times
print(f"Median survival (treatment): {kmf_treatment.median_survival_time_:.1f}")
print(f"Median survival (control): {kmf_control.median_survival_time_:.1f}")

# Log-rank test
result = logrank_test(
    df.loc[treatment_group, 'time'],
    df.loc[control_group, 'time'],
    df.loc[treatment_group, 'event'],
    df.loc[control_group, 'event']
)

print(f"\nLog-rank test:")
print(f"  Test statistic: {result.test_statistic:.4f}")
print(f"  p-value: {result.p_value:.6f}")
if result.p_value < 0.05:
    print("  Conclusion: Survival curves significantly different")
else:
    print("  Conclusion: No significant difference in survival")

# Plot both curves
import matplotlib.pyplot as plt
kmf_treatment.plot_survival_function()
kmf_control.plot_survival_function()
plt.title('Survival Curves by Treatment Group')
plt.xlabel('Time (months)')
plt.ylabel('Survival Probability')
plt.show()
```

## Advanced Features

### Robust Standard Errors (Clustered Data)

```python
# Use cluster_col for repeated measures or matched data
cph = CoxPHFitter()
cph.fit(df, duration_col='time', event_col='event',
        cluster_col='patient_id')  # Adjusts SEs for clustering
```

### Stratified Cox Model

```python
# Don't estimate HR for strata variable, but adjust for it
cph = CoxPHFitter()
cph.fit(df, duration_col='time', event_col='event',
        strata=['center', 'sex'])  # Stratify by center and sex
```

### Weighted Cox Model

```python
# Weight observations (e.g., for propensity score weighting)
cph = CoxPHFitter()
cph.fit(df, duration_col='time', event_col='event',
        weights_col='propensity_weight')
```

## Categorical Variables

### Encoding Categorical Predictors

```python
# One-hot encode (drop first level as reference)
df_encoded = pd.get_dummies(df, columns=['stage'], drop_first=True, dtype=int)

# Fit model
cph = CoxPHFitter()
cph.fit(df_encoded[['time', 'event', 'stage_II', 'stage_III', 'stage_IV', 'age']],
        duration_col='time', event_col='event')

# Interpret: HRs are relative to Stage I (reference)
print(f"HR (Stage II vs I): {cph.hazard_ratios_['stage_II']:.4f}")
print(f"HR (Stage III vs I): {cph.hazard_ratios_['stage_III']:.4f}")
print(f"HR (Stage IV vs I): {cph.hazard_ratios_['stage_IV']:.4f}")
```

## Prediction

### Individual Risk Scores

```python
# Predict partial hazard (relative risk)
# Higher score = higher risk
risk_scores = cph.predict_partial_hazard(df)
print(f"Risk score range: {risk_scores.min():.4f} to {risk_scores.max():.4f}")

# Add to dataframe
df['risk_score'] = risk_scores

# Identify high-risk patients
high_risk = df[risk_scores > risk_scores.quantile(0.75)]
print(f"High-risk patients (top 25%): {len(high_risk)}")
```

### Survival Curves for Individuals

```python
# Predict survival function for specific patient profiles
new_patient = pd.DataFrame({
    'treatment': [1],
    'age': [55],
    'stage_II': [0],
    'stage_III': [1],
    'stage_IV': [0]
})

# Get survival function
survival_func = cph.predict_survival_function(new_patient)

# Survival probability at specific times
print(f"Survival at 12 months: {survival_func.loc[12].values[0]:.4f}")
print(f"Survival at 24 months: {survival_func.loc[24].values[0]:.4f}")
```

## Model Comparison

### Likelihood Ratio Test

```python
# Compare nested models
cph_reduced = CoxPHFitter()
cph_reduced.fit(df[['time', 'event', 'treatment']], duration_col='time', event_col='event')

cph_full = CoxPHFitter()
cph_full.fit(df[['time', 'event', 'treatment', 'age', 'stage']], duration_col='time', event_col='event')

# LR test
from scipy import stats
lr_stat = -2 * (cph_reduced.log_likelihood_ - cph_full.log_likelihood_)
df_diff = cph_full.params_.shape[0] - cph_reduced.params_.shape[0]
p_value = stats.chi2.sf(lr_stat, df_diff)

print(f"LR statistic: {lr_stat:.4f}")
print(f"p-value: {p_value:.6f}")
if p_value < 0.05:
    print("Full model significantly better")
```

### AIC Comparison

```python
print(f"Reduced model AIC: {cph_reduced.AIC_partial_:.2f}")
print(f"Full model AIC: {cph_full.AIC_partial_:.2f}")

if cph_full.AIC_partial_ < cph_reduced.AIC_partial_:
    print("Full model preferred (lower AIC)")
```

## Complete Example: Cancer Clinical Trial

```python
import pandas as pd
import numpy as np
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test

# Simulated cancer trial data
np.random.seed(42)
n = 200

df = pd.DataFrame({
    'patient_id': range(1, n+1),
    'time': np.random.exponential(scale=24, size=n),
    'event': np.random.binomial(1, 0.6, n),
    'treatment': np.random.binomial(1, 0.5, n),
    'age': np.random.normal(60, 10, n),
    'stage': np.random.choice(['I', 'II', 'III', 'IV'], n, p=[0.1, 0.3, 0.4, 0.2])
})

# Encode stage
df = pd.get_dummies(df, columns=['stage'], drop_first=True, dtype=int)

print("=== Cancer Clinical Trial Survival Analysis ===\n")

# 1. Cox Proportional Hazards
print("1. Cox Proportional Hazards Model\n")
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age', 'stage_II', 'stage_III', 'stage_IV']],
        duration_col='time', event_col='event')

print(f"Concordance index: {cph.concordance_index_:.4f}\n")

# Hazard ratios
hrs = cph.hazard_ratios_
summary = cph.summary

for var in ['treatment', 'age', 'stage_II', 'stage_III', 'stage_IV']:
    hr = hrs[var]
    ci_lower = summary.loc[var, 'exp(coef) lower 95%']
    ci_upper = summary.loc[var, 'exp(coef) upper 95%']
    p_val = summary.loc[var, 'p']

    print(f"{var}:")
    print(f"  HR: {hr:.4f} (95% CI: {ci_lower:.4f}-{ci_upper:.4f})")
    print(f"  p-value: {p_val:.6f}")
    print()

# 2. Test proportional hazards assumption
print("\n2. Proportional Hazards Assumption Test\n")
ph_results = cph.check_assumptions(df, p_value_threshold=0.05, show_plots=False)
if len(ph_results) == 0:
    print("✅ All covariates meet PH assumption\n")
else:
    print(f"⚠️  PH violated for: {ph_results}\n")

# 3. Kaplan-Meier by treatment group
print("\n3. Kaplan-Meier Analysis by Treatment\n")

treatment_group = df['treatment'] == 1
control_group = df['treatment'] == 0

kmf_tx = KaplanMeierFitter()
kmf_tx.fit(df.loc[treatment_group, 'time'],
           df.loc[treatment_group, 'event'],
           label='Treatment')

kmf_ctrl = KaplanMeierFitter()
kmf_ctrl.fit(df.loc[control_group, 'time'],
             df.loc[control_group, 'event'],
             label='Control')

print(f"Median survival (treatment): {kmf_tx.median_survival_time_:.1f} months")
print(f"Median survival (control): {kmf_ctrl.median_survival_time_:.1f} months\n")

# Log-rank test
lr = logrank_test(df.loc[treatment_group, 'time'],
                  df.loc[control_group, 'time'],
                  df.loc[treatment_group, 'event'],
                  df.loc[control_group, 'event'])

print(f"Log-rank test:")
print(f"  Test statistic: {lr.test_statistic:.4f}")
print(f"  p-value: {lr.p_value:.6f}")
```

## BixBench Question Pattern

**Typical question**: "What is the hazard ratio for treatment in a Cox proportional hazards model?"

**Solution**:
1. Load survival data (time, event, covariates)
2. Fit Cox model with `duration_col` and `event_col`
3. Extract HR from `cph.hazard_ratios_['treatment']`
4. Report with CI, p-value, and concordance index

```python
# Answer format
hr_treatment = cph.hazard_ratios_['treatment']
ci_lower = cph.summary.loc['treatment', 'exp(coef) lower 95%']
ci_upper = cph.summary.loc['treatment', 'exp(coef) upper 95%']
p_val = cph.summary.loc['treatment', 'p']

print(f"Answer: {hr_treatment:.4f}")
print(f"95% CI: ({ci_lower:.4f}, {ci_upper:.4f})")
print(f"p-value: {p_val:.6f}")
print(f"Concordance: {cph.concordance_index_:.4f}")
```

## Reporting Template

```python
def report_cox_model(cph, duration_col='time', event_col='event'):
    """Generate publication-ready Cox model report."""
    summary = cph.summary
    hrs = cph.hazard_ratios_

    report = []
    report.append("=== Cox Proportional Hazards Model ===\n")
    report.append(f"Events: {cph.event_observed.sum()}/{len(cph.event_observed)}")
    report.append(f"Concordance index: {cph.concordance_index_:.4f}")
    if hasattr(cph, 'AIC_partial_'):
        report.append(f"AIC: {cph.AIC_partial_:.2f}\n")

    report.append("Hazard Ratios (95% CI):\n")
    for var in summary.index:
        hr = hrs[var]
        ci_lower = summary.loc[var, 'exp(coef) lower 95%']
        ci_upper = summary.loc[var, 'exp(coef) upper 95%']
        p_val = summary.loc[var, 'p']
        sig = "*" if p_val < 0.05 else ""

        report.append(f"  {var}: HR={hr:.4f} ({ci_lower:.4f}-{ci_upper:.4f}), p={p_val:.6f}{sig}")

    return "\n".join(report)

print(report_cox_model(cph))
```
