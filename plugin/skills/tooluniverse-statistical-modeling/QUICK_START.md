# Quick Start: Statistical Modeling Skill

## Example 1: Binary Logistic Regression - Odds Ratios

**Question**: "What is the odds ratio of disease associated with exposure, adjusting for age and sex?"

```python
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf

# Load data
df = pd.read_csv('clinical_data.csv')

# Fit logistic regression
model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)

# Extract odds ratios
odds_ratios = np.exp(model.params)
conf_int = np.exp(model.conf_int())

print(f"Odds Ratio for exposure: {odds_ratios['exposure']:.4f}")
print(f"95% CI: ({conf_int.loc['exposure', 0]:.4f}, {conf_int.loc['exposure', 1]:.4f})")
print(f"P-value: {model.pvalues['exposure']:.6f}")
```

## Example 2: Ordinal Logistic Regression

**Question**: "What is the odds ratio of COVID-19 severity associated with BCG vaccination?"

```python
import pandas as pd
import numpy as np
from statsmodels.miscmodels.ordinal_model import OrderedModel

# Load data with ordinal outcome
df = pd.read_csv('covid_data.csv')

# Set up ordinal outcome
severity_order = ['Mild', 'Moderate', 'Severe']
df['severity'] = pd.Categorical(df['severity'], categories=severity_order, ordered=True)
y = df['severity'].cat.codes

# Predictors
X = df[['bcg_vaccination', 'age', 'sex']].copy()
X = pd.get_dummies(X, drop_first=True, dtype=float)

# Fit ordered logit
model = OrderedModel(y, X, distr='logit')
fit = model.fit(method='bfgs', disp=0)

# Extract odds ratio for BCG vaccination
bcg_coef = fit.params['bcg_vaccination']
bcg_or = np.exp(bcg_coef)
print(f"Odds Ratio (BCG): {bcg_or:.4f}")
print(f"P-value: {fit.pvalues['bcg_vaccination']:.6f}")
```

## Example 3: Cox Proportional Hazards - Hazard Ratios

**Question**: "What is the hazard ratio for treatment arm in a Cox model?"

```python
import pandas as pd
from lifelines import CoxPHFitter

# Load survival data
df = pd.read_csv('survival_data.csv')

# Fit Cox PH model
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age', 'stage']],
        duration_col='time', event_col='event')

# Print summary with hazard ratios
cph.print_summary()
print(f"\nHR for treatment: {cph.hazard_ratios_['treatment']:.4f}")
print(f"Concordance index: {cph.concordance_index_:.4f}")
```

## Example 4: Kaplan-Meier with Log-Rank Test

**Question**: "Is there a significant survival difference between treatment groups?"

```python
import pandas as pd
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

df = pd.read_csv('survival_data.csv')

# Fit KM for each group
kmf = KaplanMeierFitter()
for group in df['treatment'].unique():
    mask = df['treatment'] == group
    kmf.fit(df.loc[mask, 'time'], df.loc[mask, 'event'], label=group)
    print(f"Group {group}: median survival = {kmf.median_survival_time_:.1f}")

# Log-rank test
g1 = df['treatment'] == 'Control'
g2 = df['treatment'] == 'Treatment'
result = logrank_test(
    df.loc[g1, 'time'], df.loc[g2, 'time'],
    event_observed_A=df.loc[g1, 'event'],
    event_observed_B=df.loc[g2, 'event']
)
print(f"Log-rank p-value: {result.p_value:.6f}")
```

## Example 5: Mixed-Effects Model

**Question**: "What is the treatment effect accounting for repeated measures per patient?"

```python
import pandas as pd
import statsmodels.formula.api as smf

df = pd.read_csv('longitudinal_data.csv')

# Fit linear mixed model with random intercepts for patient
model = smf.mixedlm('outcome ~ treatment + time + treatment:time',
                     data=df, groups=df['patient_id'])
fit = model.fit(reml=True)
print(fit.summary())

# ICC
group_var = float(fit.cov_re.iloc[0, 0])
resid_var = float(fit.scale)
icc = group_var / (group_var + resid_var)
print(f"ICC: {icc:.4f}")
```

## Example 6: Percentage Reduction in Odds Ratio (Confounding)

**Question**: "What is the percentage reduction in odds ratio for severity after adjusting for age?"

```python
import statsmodels.formula.api as smf
import numpy as np

# Unadjusted model
model_crude = smf.logit('outcome ~ exposure', data=df).fit(disp=0)
or_crude = np.exp(model_crude.params['exposure'])

# Adjusted model
model_adj = smf.logit('outcome ~ exposure + age + sex', data=df).fit(disp=0)
or_adj = np.exp(model_adj.params['exposure'])

# Percentage reduction
pct_reduction = (or_crude - or_adj) / or_crude * 100
print(f"Crude OR: {or_crude:.4f}")
print(f"Adjusted OR: {or_adj:.4f}")
print(f"Percentage reduction: {pct_reduction:.1f}%")
```

## Example 7: Interaction Terms

**Question**: "What is the interaction effect between treatment and biomarker?"

```python
import statsmodels.formula.api as smf
import numpy as np

# Model with interaction
model = smf.logit('outcome ~ treatment * biomarker + age', data=df).fit(disp=0)

# The interaction term
interaction_coef = model.params['treatment:biomarker']
interaction_or = np.exp(interaction_coef)
interaction_p = model.pvalues['treatment:biomarker']

print(f"Interaction OR: {interaction_or:.4f}")
print(f"P-value: {interaction_p:.6f}")
```

## Example 8: Model Comparison

**Question**: "Which model fits the data better?"

```python
import statsmodels.formula.api as smf

# Fit multiple models
m1 = smf.logit('outcome ~ exposure', data=df).fit(disp=0)
m2 = smf.logit('outcome ~ exposure + age', data=df).fit(disp=0)
m3 = smf.logit('outcome ~ exposure + age + sex + bmi', data=df).fit(disp=0)

# Compare
print(f"Model 1: AIC={m1.aic:.1f}, BIC={m1.bic:.1f}")
print(f"Model 2: AIC={m2.aic:.1f}, BIC={m2.bic:.1f}")
print(f"Model 3: AIC={m3.aic:.1f}, BIC={m3.bic:.1f}")

# Likelihood ratio test (m1 vs m2)
from scipy import stats
lr_stat = -2 * (m1.llf - m2.llf)
p_value = stats.chi2.sf(lr_stat, m2.df_model - m1.df_model)
print(f"LR test p-value (m1 vs m2): {p_value:.6f}")
```
