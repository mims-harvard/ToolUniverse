# Examples: Statistical Modeling Skill

## Example 1: Ordinal Logistic Regression - BCG Vaccination and COVID-19 Severity

**BixBench Pattern**: "What is the odds ratio of COVID-19 severity associated with BCG vaccination in ordinal logistic regression?"

### Setup

```python
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# Example dataset: COVID-19 patients with severity and vaccination status
data = {
    'severity': ['Mild']*40 + ['Moderate']*35 + ['Severe']*25,
    'bcg_vaccinated': [1]*25 + [0]*15 + [1]*10 + [0]*25 + [1]*5 + [0]*20,
    'age': np.random.normal(55, 15, 100).astype(int),
    'male': np.random.binomial(1, 0.55, 100),
}
df = pd.DataFrame(data)
```

### Analysis

```python
# Step 1: Define ordinal outcome
severity_order = ['Mild', 'Moderate', 'Severe']
df['severity'] = pd.Categorical(df['severity'], categories=severity_order, ordered=True)
y = df['severity'].cat.codes

# Step 2: Prepare predictors
X = df[['bcg_vaccinated', 'age', 'male']].astype(float)

# Step 3: Fit ordinal logistic regression
model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0)

# Step 4: Extract odds ratio
bcg_coef = fit.params['bcg_vaccinated']
bcg_or = np.exp(bcg_coef)
bcg_ci = np.exp(fit.conf_int().loc['bcg_vaccinated'])

print(f"BCG Vaccination Odds Ratio: {bcg_or:.4f}")
print(f"95% CI: ({bcg_ci.iloc[0]:.4f}, {bcg_ci.iloc[1]:.4f})")
print(f"P-value: {fit.pvalues['bcg_vaccinated']:.6f}")
```

### Interpretation

- OR < 1: BCG vaccination is associated with lower odds of being in a higher severity category
- OR > 1: BCG vaccination is associated with higher odds of being in a higher severity category
- The proportional odds assumption means this OR applies uniformly across all severity cut points

---

## Example 2: Binary Logistic Regression - Treatment Response

**BixBench Pattern**: "What is the odds ratio of treatment response associated with biomarker positivity?"

```python
import statsmodels.formula.api as smf
import numpy as np

# Fit logistic regression
model = smf.logit('response ~ biomarker_positive + age + stage', data=df).fit(disp=0)

# Odds ratios with confidence intervals
or_table = np.exp(model.params)
ci = np.exp(model.conf_int())
ci.columns = ['OR_lower', 'OR_upper']
results = pd.DataFrame({
    'OR': or_table,
    'CI_lower': ci['OR_lower'],
    'CI_upper': ci['OR_upper'],
    'p_value': model.pvalues
})
print(results.round(4))
```

---

## Example 3: Percentage Reduction in Odds Ratio (Confounding Assessment)

**BixBench Pattern**: "What is the percentage reduction in odds ratio for higher severity after adjusting for confounders?"

```python
import statsmodels.formula.api as smf
import numpy as np

# Unadjusted (crude) model
model_crude = smf.logit('outcome ~ exposure', data=df).fit(disp=0)
or_crude = np.exp(model_crude.params['exposure'])

# Adjusted model (with confounders)
model_adj = smf.logit('outcome ~ exposure + age + sex + comorbidity', data=df).fit(disp=0)
or_adj = np.exp(model_adj.params['exposure'])

# Calculate percentage reduction
pct_reduction = ((or_crude - or_adj) / or_crude) * 100

print(f"Crude OR: {or_crude:.4f}")
print(f"Adjusted OR: {or_adj:.4f}")
print(f"Percentage reduction in OR: {pct_reduction:.1f}%")
print(f"Interpretation: Adjusting for confounders reduced the OR by {pct_reduction:.1f}%,")
print(f"suggesting {'substantial' if abs(pct_reduction) > 10 else 'minimal'} confounding.")
```

---

## Example 4: Interaction Effect in Ordered Logit

**BixBench Pattern**: "What is the odds ratio associated with patient interaction using ordered logit model?"

```python
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# When "patient interaction" refers to interaction between patient-level variables:
# e.g., interaction between treatment and comorbidity

# Prepare data with interaction term
df['treatment_x_comorbidity'] = df['treatment'] * df['comorbidity']

# Predictors including interaction
X = df[['treatment', 'comorbidity', 'treatment_x_comorbidity', 'age']].astype(float)

# Ordinal outcome
y = df['severity'].cat.codes

model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0)

# Interaction OR
interaction_or = np.exp(fit.params['treatment_x_comorbidity'])
print(f"Interaction OR: {interaction_or:.4f}")
print(f"P-value: {fit.pvalues['treatment_x_comorbidity']:.6f}")
```

---

## Example 5: Cox Proportional Hazards Survival Analysis

**BixBench Pattern**: "What is the hazard ratio for drug treatment in a Cox regression model?"

```python
import pandas as pd
from lifelines import CoxPHFitter

# Load survival data
df = pd.read_csv('survival_data.csv')
# Columns: time, event, treatment, age, stage, biomarker

# Fit Cox model
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age', 'stage']],
        duration_col='time', event_col='event')

# Extract results
summary = cph.summary
for covar in summary.index:
    hr = summary.loc[covar, 'exp(coef)']
    ci_low = summary.loc[covar, 'exp(coef) lower 95%']
    ci_up = summary.loc[covar, 'exp(coef) upper 95%']
    p = summary.loc[covar, 'p']
    print(f"{covar}: HR={hr:.4f} (95% CI: {ci_low:.4f}-{ci_up:.4f}), p={p:.6f}")

print(f"\nConcordance index: {cph.concordance_index_:.4f}")

# Check proportional hazards assumption
cph.check_assumptions(df[['time', 'event', 'treatment', 'age', 'stage']],
                      p_value_threshold=0.05, show_plots=False)
```

---

## Example 6: Kaplan-Meier with Group Comparison

**BixBench Pattern**: "What is the median survival time for treatment vs control group?"

```python
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

df = pd.read_csv('survival_data.csv')

kmf = KaplanMeierFitter()

# Fit for each group
for group_name in ['Treatment', 'Control']:
    mask = df['group'] == group_name
    kmf.fit(df.loc[mask, 'time'], df.loc[mask, 'event'], label=group_name)

    median_s = kmf.median_survival_time_
    s_12mo = kmf.predict(12) if 12 <= df['time'].max() else None

    print(f"{group_name}:")
    print(f"  Median survival: {median_s:.1f} months")
    if s_12mo is not None:
        print(f"  12-month survival: {s_12mo:.1%}")

# Log-rank test
g_treat = df['group'] == 'Treatment'
g_ctrl = df['group'] == 'Control'
lr = logrank_test(
    df.loc[g_treat, 'time'], df.loc[g_ctrl, 'time'],
    event_observed_A=df.loc[g_treat, 'event'],
    event_observed_B=df.loc[g_ctrl, 'event']
)
print(f"\nLog-rank test: chi2={lr.test_statistic:.4f}, p={lr.p_value:.6f}")
```

---

## Example 7: Linear Mixed-Effects Model

**BixBench Pattern**: "What is the treatment effect in a mixed-effects model with random intercepts per site?"

```python
import statsmodels.formula.api as smf

# Longitudinal data with repeated measures
model = smf.mixedlm('outcome ~ treatment + time + treatment:time',
                     data=df, groups=df['site_id'])
fit = model.fit(reml=True)

# Fixed effects
print("Fixed Effects:")
for name in fit.fe_params.index:
    coef = fit.fe_params[name]
    p = fit.pvalues[name]
    print(f"  {name}: {coef:.4f} (p={p:.6f})")

# Random effects
group_var = float(fit.cov_re.iloc[0, 0])
resid_var = float(fit.scale)
icc = group_var / (group_var + resid_var)
print(f"\nRandom intercept variance: {group_var:.4f}")
print(f"Residual variance: {resid_var:.4f}")
print(f"ICC: {icc:.4f}")
```

---

## Example 8: Complete Analysis Pipeline (BixBench Style)

**BixBench Pattern**: Full statistical analysis from data loading to reporting.

```python
import pandas as pd
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel
from scipy import stats as scipy_stats

# Step 1: Load and inspect data
df = pd.read_csv('study_data.csv')
print(f"Dataset: {df.shape[0]} observations, {df.shape[1]} variables")
print(f"Outcome: {df['outcome'].value_counts().to_dict()}")

# Step 2: Determine outcome type and select model
outcome_type = 'ordinal'  # Based on inspection: Mild < Moderate < Severe
levels = ['Mild', 'Moderate', 'Severe']

# Step 3: Fit appropriate model
df['outcome_cat'] = pd.Categorical(df['outcome'], categories=levels, ordered=True)
y = df['outcome_cat'].cat.codes
X = df[['treatment', 'age', 'sex']].astype(float)

model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0)

# Step 4: Extract key results
treatment_coef = fit.params['treatment']
treatment_or = np.exp(treatment_coef)
treatment_p = fit.pvalues['treatment']
treatment_ci = np.exp(fit.conf_int().loc['treatment'])

# Step 5: Report
print(f"\n=== RESULTS ===")
print(f"Model: Ordinal Logistic Regression (Proportional Odds)")
print(f"Outcome: {' < '.join(levels)}")
print(f"N = {len(y)}")
print(f"\nTreatment effect:")
print(f"  Odds Ratio: {treatment_or:.4f}")
print(f"  95% CI: ({treatment_ci.iloc[0]:.4f}, {treatment_ci.iloc[1]:.4f})")
print(f"  P-value: {treatment_p:.6f}")
print(f"  Significant: {'Yes' if treatment_p < 0.05 else 'No'}")

if treatment_or > 1:
    print(f"  Interpretation: Treatment increases odds of higher severity by {(treatment_or-1)*100:.1f}%")
else:
    print(f"  Interpretation: Treatment decreases odds of higher severity by {(1-treatment_or)*100:.1f}%")
```
