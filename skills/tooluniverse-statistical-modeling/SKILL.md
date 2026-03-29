---
name: tooluniverse-statistical-modeling
description: Perform statistical modeling and regression analysis on biomedical datasets. Supports linear regression, logistic regression (binary/ordinal/multinomial), mixed-effects models, Cox proportional hazards survival analysis, Kaplan-Meier estimation, and comprehensive model diagnostics. Extracts odds ratios, hazard ratios, confidence intervals, p-values, and effect sizes. Designed to solve BixBench statistical reasoning questions involving clinical/experimental data. Use when asked to fit regression models, compute odds ratios, perform survival analysis, run statistical tests, or interpret model coefficients from provided data.
---

# Statistical Modeling for Biomedical Data Analysis

Comprehensive statistical modeling skill for fitting regression models, survival models, and mixed-effects models to biomedical data. Produces publication-quality statistical summaries with odds ratios, hazard ratios, confidence intervals, and p-values.

## COMPUTE, DON'T DESCRIBE
Write and run Python code (via Bash) for every statistical analysis. Never describe what you "would do" — do it. Use pandas for data wrangling, statsmodels for regression, scipy for tests, and matplotlib for plots. Execute the code and report actual numbers (β, p-value, CI, N).

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory.

## Features

- **Linear Regression** - OLS for continuous outcomes with diagnostic tests
- **Logistic Regression** - Binary, ordinal, and multinomial models with odds ratios
- **Survival Analysis** - Cox proportional hazards and Kaplan-Meier curves
- **Mixed-Effects Models** - LMM/GLMM for hierarchical/repeated measures data
- **ANOVA** - One-way/two-way ANOVA, per-feature ANOVA for omics data
- **Model Diagnostics** - Assumption checking, fit statistics, residual analysis
- **Statistical Tests** - t-tests, chi-square, Mann-Whitney, Kruskal-Wallis, etc.

## When to Use

Apply this skill when user asks:
- "What is the odds ratio of X associated with Y?"
- "What is the hazard ratio for treatment?"
- "Fit a linear regression of Y on X1, X2, X3"
- "Perform ordinal logistic regression for severity outcome"
- "What is the Kaplan-Meier survival estimate at time T?"
- "What is the percentage reduction in odds ratio after adjusting for confounders?"
- "Run a mixed-effects model with random intercepts"
- "Compute the interaction term between A and B"
- "What is the F-statistic from ANOVA comparing groups?"
- "Test if gene/miRNA expression differs across cell types"

## Model Selection Decision Tree

```
START: What type of outcome variable?
|
+-- CONTINUOUS (height, blood pressure, score)
|   +-- Independent observations -> Linear Regression (OLS)
|   +-- Repeated measures -> Mixed-Effects Model (LMM)
|   +-- Count data -> Poisson/Negative Binomial
|
+-- BINARY (yes/no, disease/healthy)
|   +-- Independent observations -> Logistic Regression
|   +-- Repeated measures -> Logistic Mixed-Effects (GLMM/GEE)
|   +-- Rare events -> Firth logistic regression
|
+-- ORDINAL (mild/moderate/severe, stages I/II/III/IV)
|   +-- Ordinal Logistic Regression (Proportional Odds)
|
+-- MULTINOMIAL (>2 unordered categories)
|   +-- Multinomial Logistic Regression
|
+-- TIME-TO-EVENT (survival time + censoring)
    +-- Regression -> Cox Proportional Hazards
    +-- Survival curves -> Kaplan-Meier
```

## Workflow

### Phase 0: Data Validation

**Goal**: Load data, identify variable types, check for missing values.

**CRITICAL: Identify the Outcome Variable First**

Before any analysis, verify what you're actually predicting:

1. **Read the full question** - Look for "predict [outcome]", "model [outcome]", or "dependent variable"
2. **Examine available columns** - List all columns in the dataset
3. **Match question to data** - Find the column that matches the described outcome
4. **Verify outcome exists** - Don't create outcome variables from predictors

**Common mistake**: Question mentions "obesity" -> Assumed outcome = BMI >= 30 (circular logic with BMI predictor). Always check data columns first: `print(df.columns.tolist())`

```python
import pandas as pd
import numpy as np

df = pd.read_csv('data.csv')
print(f"Observations: {len(df)}, Variables: {len(df.columns)}, Missing: {df.isnull().sum().sum()}")

for col in df.columns:
    n_unique = df[col].nunique()
    if n_unique == 2:
        print(f"{col}: binary")
    elif n_unique <= 10 and df[col].dtype == 'object':
        print(f"{col}: categorical ({n_unique} levels)")
    elif df[col].dtype in ['float64', 'int64']:
        print(f"{col}: continuous (mean={df[col].mean():.2f})")
```

### Phase 1: Model Fitting

**Goal**: Fit appropriate model based on outcome type.

Use the decision tree above to select model type, then refer to the appropriate reference file for detailed code:

- **Linear Regression**: `references/linear_models.md`
- **Logistic Regression** (binary): `references/logistic_regression.md`
- **Ordinal Logistic**: `references/ordinal_logistic.md`
- **Cox Proportional Hazards**: `references/cox_regression.md`
- **ANOVA / Statistical Tests**: `anova_and_tests.md`

**Quick reference for key models**:

```python
import statsmodels.formula.api as smf
import numpy as np

# Linear regression
model = smf.ols('outcome ~ predictor1 + predictor2', data=df).fit()

# Logistic regression (odds ratios)
model = smf.logit('disease ~ exposure + age + sex', data=df).fit(disp=0)
ors = np.exp(model.params)
ci = np.exp(model.conf_int())

# Cox proportional hazards
from lifelines import CoxPHFitter
cph = CoxPHFitter()
cph.fit(df[['time', 'event', 'treatment', 'age']], duration_col='time', event_col='event')
hr = cph.hazard_ratios_['treatment']
```

### Phase 1b: ANOVA for Multi-Feature Data

When data has multiple features (genes, miRNAs, metabolites), use **per-feature ANOVA** (not aggregate). This is the most common pattern in genomics.

See `anova_and_tests.md` for the full decision tree, both methods, and worked examples.

**Default for gene expression data**: Per-feature ANOVA (Method B).

### Phase 2: Model Diagnostics

**Goal**: Check model assumptions and fit quality.

Key diagnostics by model type:
- **OLS**: Shapiro-Wilk (normality), Breusch-Pagan (heteroscedasticity), VIF (multicollinearity)
- **Cox**: Proportional hazards test via `cph.check_assumptions()`
- **Logistic**: Hosmer-Lemeshow, ROC/AUC

See `references/troubleshooting.md` for diagnostic code and common issues.

### Phase 3: Interpretation

**Goal**: Generate publication-quality summary.

For every result, report: effect size (OR/HR/coefficient), 95% CI, p-value, and model fit statistic. See `bixbench_patterns_summary.md` for common question-answer patterns.

## Common BixBench Patterns

| Pattern | Question Type | Key Steps |
|---------|--------------|-----------|
| 1 | Odds ratio from ordinal regression | Fit OrderedModel, exp(coef) |
| 2 | Percentage reduction in OR | Compare crude vs adjusted model |
| 3 | Interaction effects | Fit `A * B`, extract `A:B` coef |
| 4 | Hazard ratio | Cox PH model, exp(coef) |
| 5 | Multi-feature ANOVA | Per-feature F-stats (not aggregate) |

See `bixbench_patterns_summary.md` for solution code for each pattern.
See `references/bixbench_patterns.md` for 15+ detailed question patterns.

## Statsmodels vs Scikit-learn

| Use Case | Library | Reason |
|----------|---------|--------|
| **Inference** (p-values, CIs, ORs) | **statsmodels** | Full statistical output |
| **Prediction** (accuracy, AUC) | **scikit-learn** | Better prediction tools |
| **Mixed-effects models** | **statsmodels** | Only option |
| **Regularization** (LASSO, Ridge) | **scikit-learn** | Better optimization |
| **Survival analysis** | **lifelines** | Specialized library |

**General rule**: Use statsmodels for BixBench questions (they ask for p-values, ORs, HRs).

## Python Package Requirements

```
statsmodels>=0.14.0
scikit-learn>=1.3.0
lifelines>=0.27.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
```

## Key Principles

1. **Data-first approach** - Always inspect and validate data before modeling
2. **Model selection by outcome type** - Use decision tree above
3. **Assumption checking** - Verify model assumptions (linearity, proportional hazards, etc.)
4. **Complete reporting** - Always report effect sizes, CIs, p-values, and model fit statistics
5. **Confounder awareness** - Adjust for confounders when specified or clinically relevant
6. **Reproducible analysis** - All code must be deterministic and reproducible
7. **Robust error handling** - Graceful handling of convergence failures, separation, collinearity
8. **Round correctly** - Match the precision requested (typically 2-4 decimal places)

## Reasoning Framework for Result Interpretation

### Evidence Grading

| Grade | Criteria | Example |
|-------|----------|---------|
| **Strong** | p < 0.001, effect size clinically meaningful, model assumptions met | OR = 3.5 (95% CI: 2.1-5.8), p < 0.001, Hosmer-Lemeshow p > 0.05 |
| **Moderate** | p < 0.05, reasonable effect size, minor assumption concerns | HR = 1.8 (95% CI: 1.1-2.9), p = 0.02, borderline PH test |
| **Weak** | p < 0.05 but wide CI, small effect, or assumption violations | OR = 1.2 (95% CI: 1.01-1.43), p = 0.04, VIF > 5 for a covariate |
| **Insufficient** | p >= 0.05, or model fails convergence/diagnostics | Non-significant coefficient with model separation warning |

### Interpretation Guidance

- **Model diagnostics (R-squared)**: For OLS, R-squared > 0.7 indicates good fit in biomedical data; 0.3-0.7 is moderate. Adjusted R-squared penalizes added predictors. For logistic models, use pseudo-R-squared (McFadden > 0.2 is acceptable) and AUC (> 0.7 = acceptable, > 0.8 = good discrimination).
- **AIC/BIC for model comparison**: Lower is better. AIC difference > 10 between models is strong evidence for the lower-AIC model. BIC penalizes complexity more heavily than AIC, preferring simpler models. Use AIC for prediction-focused selection, BIC for inference.
- **Coefficient significance thresholds**: Report exact p-values rather than just significance stars. For multiple predictors, apply Bonferroni or FDR correction. A coefficient with p = 0.049 in a model with 20 predictors is likely a false positive without correction.
- **Survival analysis HR interpretation**: HR > 1 means increased hazard (worse outcome) for the exposed group. HR = 2.0 means twice the instantaneous risk of the event. Always verify the proportional hazards assumption -- if violated, the HR is an average over time and may be misleading. Report median survival times alongside HRs for clinical interpretability.
- **Odds ratio interpretation**: OR = 1.0 means no association. OR > 1 indicates increased odds. The 95% CI excluding 1.0 confirms significance. For rare outcomes, OR approximates relative risk; for common outcomes (> 10% prevalence), OR overstates the relative risk.
- **Confounding assessment**: Compare crude vs adjusted ORs/HRs. A change > 10% in the effect estimate after adjusting for a covariate suggests confounding by that variable.

### Synthesis Questions

1. Do the model diagnostics (residual plots, Hosmer-Lemeshow, PH test) support the validity of the chosen model, or do assumption violations require alternative approaches (e.g., robust standard errors, stratified models)?
2. For adjusted models, does the inclusion of confounders change the primary effect estimate by more than 10%, indicating meaningful confounding?
3. Are the reported effect sizes (OR, HR, coefficients) clinically meaningful in addition to being statistically significant, considering the scale of the predictor and outcome?
4. When comparing nested models via AIC/BIC, does the more complex model provide substantially better fit, or is the simpler model preferred by parsimony?
5. For survival analysis, is the proportional hazards assumption met throughout the follow-up period, or do Schoenfeld residuals suggest time-varying effects?

---

## Completeness Checklist

Before finalizing any statistical analysis:

- [ ] **Outcome variable identified**: Verified which column is the actual outcome
- [ ] **Data validated**: N, missing values, variable types confirmed
- [ ] **Multi-feature data identified**: If multiple features, use per-feature approach
- [ ] **Model appropriate**: Outcome type matches model family
- [ ] **Assumptions checked**: Relevant diagnostics performed
- [ ] **Effect sizes reported**: OR/HR/Cohen's d with CIs
- [ ] **P-values reported**: With appropriate correction if needed
- [ ] **Model fit assessed**: R-squared, AIC/BIC, concordance
- [ ] **Results interpreted**: Plain-language interpretation
- [ ] **Precision correct**: Numbers rounded appropriately

## Bundled Scripts

These ready-to-run scripts live in `skills/tooluniverse-statistical-modeling/scripts/`.
Use them via the Bash tool for quick calculations that do not require a full dataset.

### `stat_tests.py` — Basic statistical tests (pure stdlib, no scipy)

Implements chi-square goodness-of-fit, Fisher's exact test, and simple linear regression
without any external dependencies. All p-values are computed from first principles using
the gamma function (chi-square) or hypergeometric enumeration (Fisher's).

```
# Chi-square goodness-of-fit
python stat_tests.py --type chi_square --observed 100,50,25 --expected 87.5,50,37.5

# Fisher's exact test (2×2 table)
python stat_tests.py --type fisher_exact --a 10 --b 5 --c 3 --d 20
python stat_tests.py --type fisher_exact --a 10 --b 5 --c 3 --d 20 --alternative greater

# Simple linear regression (OLS)
python stat_tests.py --type regression --x "1,2,3,4,5" --y "2.1,4.0,5.9,8.1,10.0"
```

Key formulas:
- `chi_square`: χ² = Σ (O−E)²/E; p-value via upper regularized incomplete gamma Q(df/2, χ²/2)
- `fisher_exact`: hypergeometric PMF; p-value = sum of probabilities ≤ P(observed)
- `regression`: b1 = Sxy/Sxx; b0 = ȳ − b1x̄; R² = 1 − SSR/SST; SE and t-statistics included

Output includes: full contingency/data table, step-by-step arithmetic, significance statement,
and a round-trip verification for each test.

When to use `stat_tests.py` vs `statsmodels`:
- Use `stat_tests.py` when you need a quick sanity check with no imports, or when the
  environment lacks scipy/statsmodels.
- Use statsmodels when you need multivariate regression, logistic models, or survival analysis.

### `format_statistical_output.py` — Format results for reporting

Utility functions to format fitted statsmodels results as publication-ready tables.
Import and call from analysis scripts; not a standalone CLI tool.

### `model_diagnostics.py` — Automated model diagnostics

Runs assumption checks (normality, heteroscedasticity, multicollinearity) on fitted models.
Import and call from analysis scripts; not a standalone CLI tool.

---

## File Structure

```
tooluniverse-statistical-modeling/
+-- SKILL.md                          # This file (workflow guide)
+-- QUICK_START.md                    # 8 quick examples
+-- EXAMPLES.md                       # Legacy examples
+-- TOOLS_REFERENCE.md                # ToolUniverse tool catalog
+-- anova_and_tests.md                # ANOVA decision tree and code
+-- bixbench_patterns_summary.md      # Common BixBench solution patterns
+-- test_skill.py                     # Test suite
+-- references/
|   +-- logistic_regression.md        # Detailed logistic examples
|   +-- ordinal_logistic.md           # Ordinal logit guide
|   +-- cox_regression.md             # Survival analysis guide
|   +-- linear_models.md              # OLS and mixed-effects
|   +-- bixbench_patterns.md          # 15+ question patterns
|   +-- troubleshooting.md            # Diagnostic issues
+-- scripts/
    +-- stat_tests.py                 # Chi-square, Fisher's exact, linear regression (stdlib)
    +-- format_statistical_output.py  # Format results for reporting
    +-- model_diagnostics.py          # Automated diagnostics
```

## ToolUniverse Integration

While this skill is primarily computational, ToolUniverse tools can provide data:

| Use Case | Tools |
|----------|-------|
| Clinical trial data | `search_clinical_trials` |
| Drug safety outcomes | `FAERS_calculate_disproportionality` |
| Gene-disease associations | `OpenTargets_target_disease_evidence` |
| Biomarker data | `fda_pharmacogenomic_biomarkers` |

See `TOOLS_REFERENCE.md` for complete tool catalog.

## References

- **statsmodels**: https://www.statsmodels.org/
- **lifelines**: https://lifelines.readthedocs.io/
- **scikit-learn**: https://scikit-learn.org/
- **Ordinal models**: statsmodels.miscmodels.ordinal_model.OrderedModel

## Support

For detailed examples and troubleshooting:
- **Logistic regression**: `references/logistic_regression.md`
- **Ordinal models**: `references/ordinal_logistic.md`
- **Survival analysis**: `references/cox_regression.md`
- **Linear/mixed models**: `references/linear_models.md`
- **BixBench patterns**: `references/bixbench_patterns.md`
- **ANOVA and tests**: `anova_and_tests.md`
- **Diagnostics**: `references/troubleshooting.md`
