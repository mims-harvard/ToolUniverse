# Tools Reference: Statistical Modeling Skill

## Core Python Packages (Computational)

This skill is primarily computational. The statistical modeling is done with Python packages, not ToolUniverse API tools.

### statsmodels (Primary statistical modeling)

| Function | Purpose | Key Parameters |
|----------|---------|---------------|
| `smf.ols(formula, data)` | OLS linear regression | formula (R-style), data (DataFrame) |
| `smf.logit(formula, data)` | Binary logistic regression | formula, data |
| `smf.mnlogit(formula, data)` | Multinomial logistic | formula, data |
| `smf.mixedlm(formula, data, groups)` | Linear mixed-effects | formula, data, groups, re_formula |
| `smf.gee(formula, groups, data, family)` | GEE models | formula, groups, data, family |
| `sm.OLS(y, X)` | OLS (matrix interface) | y (array), X (array with constant) |
| `sm.Logit(y, X)` | Logistic (matrix) | y (binary), X (array) |
| `sm.MNLogit(y, X)` | Multinomial logistic (matrix) | y (coded), X (array) |
| `OrderedModel(y, X, distr)` | Ordinal logistic | y (codes), X (array), distr='logit' |

### statsmodels diagnostics

| Function | Purpose | Returns |
|----------|---------|---------|
| `het_breuschpagan(resid, exog)` | Heteroscedasticity test | (LM, p, F, Fp) |
| `durbin_watson(resid)` | Autocorrelation test | DW statistic |
| `variance_inflation_factor(X, i)` | Multicollinearity | VIF value |
| `shapiro(resid)` | Normality test | (W, p) |

### lifelines (Survival analysis)

| Class/Function | Purpose | Key Parameters |
|----------------|---------|---------------|
| `CoxPHFitter()` | Cox PH model | `.fit(df, duration_col, event_col)` |
| `KaplanMeierFitter()` | KM estimation | `.fit(durations, event_observed)` |
| `logrank_test(T1, T2, E1, E2)` | Log-rank test | durations and events for 2 groups |
| `NelsonAalenFitter()` | Cumulative hazard | `.fit(durations, event_observed)` |

### scipy.stats (Statistical tests)

| Function | Purpose | Returns |
|----------|---------|---------|
| `ttest_ind(a, b)` | Independent t-test | (t, p) |
| `ttest_rel(a, b)` | Paired t-test | (t, p) |
| `mannwhitneyu(a, b)` | Mann-Whitney U | (U, p) |
| `chi2_contingency(table)` | Chi-square test | (chi2, p, dof, expected) |
| `fisher_exact(table)` | Fisher's exact test | (OR, p) |
| `f_oneway(*groups)` | One-way ANOVA | (F, p) |
| `kruskal(*groups)` | Kruskal-Wallis | (H, p) |
| `wilcoxon(a, b)` | Wilcoxon signed-rank | (W, p) |
| `shapiro(data)` | Shapiro-Wilk normality | (W, p) |

### scikit-learn (Supplementary)

| Class | Purpose | Key Methods |
|-------|---------|------------|
| `LogisticRegression(multi_class='multinomial')` | Multinomial logistic | `.fit(X, y)`, `.predict_proba(X)` |
| `StandardScaler()` | Feature scaling | `.fit_transform(X)` |
| `LabelEncoder()` | Label encoding | `.fit_transform(y)` |

---

## ToolUniverse Integration Tools (Data Retrieval)

These ToolUniverse tools can be used to retrieve data before modeling:

### Clinical Trial Data

| Tool | Parameters | Returns |
|------|-----------|---------|
| `clinical_trials_search` | `action="search_studies"`, `condition`, `intervention`, `limit` | `{total_count, studies}` |
| `get_clinical_trial_eligibility_criteria` | `nct_ids` (array), `eligibility_criteria="all"` | `[{NCT ID, eligibility_criteria}]` |

### Drug Safety / Adverse Events

| Tool | Parameters | Returns |
|------|-----------|---------|
| `FAERS_calculate_disproportionality` | `drug_name`, `adverse_event` | `{metrics: {PRR, ROR, IC}, signal_detection}` |
| `FAERS_stratify_by_demographics` | `drug_name`, `adverse_event`, `stratify_by` | Stratified counts |
| `FAERS_count_patient_reaction` | `medicinalproduct` | `[{term, count}]` |

### Gene-Disease Evidence

| Tool | Parameters | Returns |
|------|-----------|---------|
| `OpenTargets_target_disease_evidence` | `ensemblId`, `efoId` | Evidence scores |
| `OpenTargets_get_associated_targets_by_disease_efoId` | `efoId`, `size` | `{data: {disease: {associatedTargets}}}` |

### Literature

| Tool | Parameters | Returns |
|------|-----------|---------|
| `PubMed_search_articles` | `query`, `max_results` | List of article dicts |

---

## Model Selection Decision Tree

```
Outcome Type?
|
|-- Continuous (numeric, wide range)
|   |-- Independent observations -> OLS (smf.ols)
|   |-- Clustered/repeated -> LMM (smf.mixedlm)
|
|-- Binary (0/1, yes/no)
|   |-- Independent observations -> Logistic (smf.logit)
|   |-- Clustered/repeated -> GEE Logistic (smf.gee)
|
|-- Ordinal (ordered categories, 3+ levels)
|   |-- Independent observations -> OrderedModel (distr='logit')
|   |-- If proportional odds violated -> Multinomial logistic
|
|-- Nominal (unordered categories, 3+ levels)
|   |-- -> Multinomial logistic (sm.MNLogit)
|
|-- Time-to-event (survival)
|   |-- With covariates -> Cox PH (CoxPHFitter)
|   |-- Descriptive / curves -> Kaplan-Meier (KaplanMeierFitter)
|   |-- Group comparison -> Log-rank test
|
|-- Count (integer, events)
|   |-- -> Poisson or Negative Binomial (smf.poisson / smf.negativebinomial)
```

---

## Common Pitfalls

1. **OrderedModel coefficient sign**: In statsmodels OrderedModel, positive coefficient = higher odds of being in HIGHER category (same direction as R's polr with method="logistic")
2. **Formula syntax**: Use `C(variable)` for categorical variables in formulas, `:` for interaction, `*` for main effects + interaction
3. **Reference levels**: First level alphabetically is default reference. Use `C(var, Treatment(reference='level'))` to set explicitly
4. **Convergence**: OrderedModel may need `method='bfgs'` and `maxiter=200+`; logistic regression use `maxiter=100` and `disp=0`
5. **Missing data**: statsmodels formula API drops NA rows automatically; matrix API does not
6. **Odds ratio direction**: OR > 1 = increased odds, OR < 1 = decreased odds, OR = 1 = no effect
7. **Hazard ratio direction**: HR > 1 = increased hazard (worse survival), HR < 1 = decreased hazard (better survival)
