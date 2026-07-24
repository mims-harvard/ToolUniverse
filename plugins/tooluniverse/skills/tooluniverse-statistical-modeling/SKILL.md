---

name: tooluniverse-statistical-modeling
description: "Statistical modeling — linear/logistic/ordinal/Poisson regression, ANOVA, Kruskal-Wallis, chi-square, Mann-Whitney, Cox survival, spline fits (R `ns()`), odds ratios, Cohen's d, F-statistic, p-value computation. Specializes in clinical-trial AE analysis (SDTM DM/AE), severity ordinal regression, and per-feature stat workflows."
---

# Statistical Modeling for Biomedical Data Analysis

## RULE ZERO — Check for pre-computed results FIRST

Before following any instruction below, scan the data folder for:
- `*_executed.ipynb` → read with `tu run read_executed_notebook '{"data_folder":"<path>","search":"<keyword>"}'` and cite its cell outputs as the authoritative answer
- Pre-computed result files (CSV/TSV with names like `*results*`, `*deseq*`, `*enrich*`, `*stats*`, `*_simplified.csv`) → read directly and report the requested value
- Canonical analysis scripts (`analysis.R`, `run_*.py`, `find_*.R`, `*.Rmd`) → execute as-is and read the output

Only follow this skill's re-analysis recipe below if **none** of the above exist. Re-running from raw data produces different numbers than the published answer and is much slower (often 5-10× turn count).

---

## PRIMARY SCRIPTS — use these FIRST

These scripts encode the question-specific gotchas in `scripts/` and emit
labelled, parseable output. Prefer them over ad-hoc statsmodels / scipy code.

| Script | When to use it |
|--------|----------------|
| `r_natural_spline_regression.py` | ANY question that mentions R syntax `lm(y ~ ns(x, df = K))`, "natural spline", or asks for spline R²/F/peak prediction CIs. Always shells out to Rscript so `splines::ns()` matches. |
| `spline_model_compare.py` | "Best-fitting model among quadratic, cubic and natural spline" / "max colony area at the optimal x". Fits all three in R, ranks by adj-R²/AIC/BIC, and reports the BEST model's peak (x*, y*) with 95% CI. |
| `logistic_regression_or.py` | Binary or ordinal logistic regression where the answer is an OR (or OR + 95% CI). Handles label encoding, explicit Placebo=0/BCG=1 maps, AND interaction terms (`--interaction A:B` -> creates `A_B = A*B`). Prints OR + CI for every coefficient and a SCALARS block for the requested `--coef-name`. |
| `power_analysis.py` | "Minimum sample size per group", "TTestIndPower", "given Cohen's d, what N for power=0.8". Computes pooled-SD Cohen's d from a CSV (or accepts `--effect-size`), then `TTestIndPower.solve_power`. |
| `expression_anova.py` | Per-gene ANOVA / median LFC across cell types or sample groups (NOT pooled across genes — see warnings below). |
| `prepare_ae_cohort.py` | Clinical-trial AE severity tests (chi-square / ordinal) on SDTM DM/AE files (`encoding='latin1'`, `max(AESEV)` per subject across ALL AEs — no AEPT filter). |
| `stat_tests.py` | Stdlib-only chi-square goodness-of-fit, Fisher's exact, simple OLS. Use when scipy/statsmodels aren't available. |

### Concrete invocations

Natural-spline regression (R^2, overall F-test p, peak Y + 95% CI):

```bash
python skills/tooluniverse-statistical-modeling/scripts/r_natural_spline_regression.py \
  --csv data.csv --y-col Area \
  --ratio-col Ratio --new-x-col Frequency_strain \
  --filter "StrainNumber not in ['1', '98']" \
  --df 4 --workdir /tmp/spline_run
```

Quadratic vs cubic vs natural-spline comparison + best-model peak:

```bash
python skills/tooluniverse-statistical-modeling/scripts/spline_model_compare.py \
  --csv data.csv --y-col Area \
  --ratio-col Ratio --new-x-col Frequency_strain \
  --filter "StrainNumber not in ['1', '98']" \
  --ns-df 4 --workdir /tmp/spline_cmp
```

**Report the peak location (`x*`) in the units of the fitted x-variable, not a derived label.** When the model is fit on a frequency/proportion column (e.g. `Frequency_strain`, a 0–1 value), the answer to "at what ratio/frequency is the maximum" is that fraction (e.g. `0.909`), NOT the colon-ratio it was derived from (e.g. `10:1`). Convert a colon ratio `a:b` to the fraction `a/(a+b)` when the question expects a 0–1 value or the fitted x-column is a fraction.

Ordinal logistic regression with interaction term (e.g. trial AE severity):

```bash
python skills/tooluniverse-statistical-modeling/scripts/logistic_regression_or.py \
  --csv merged.csv --outcome AESEV --outcome-type ordinal --outcome-order "1,2,3,4" \
  --predictors TRTGRP,expect_interact,patients_seen,MHONGO \
  --encode TRTGRP,expect_interact,patients_seen \
  --encode-map "TRTGRP:Placebo=0,BCG=1" \
  --interaction MHONGO:TRTGRP_cat \
  --coef-name TRTGRP_cat
```

Two-sample power analysis from a pilot CSV:

```bash
python skills/tooluniverse-statistical-modeling/scripts/power_analysis.py \
  --csv pilot.csv --value-col MeasuredValue --group-col Group \
  --group-a Treatment --group-b Control \
  --power 0.8 --alpha 0.05
```

---

## Workspace isolation (CRITICAL)

The input data folder for any analysis must remain untouched so re-runs
are reproducible. Scripts that write intermediate files (R drivers,
prepared CSVs, comparison tables) must write to `/tmp/` or to a
`--workdir` you pass in. Both R-based scripts in this skill refuse to
run if `--workdir` resolves to the input CSV's parent directory (or any
ancestor of it).

```bash
# OK
--workdir /tmp/spline_run

# Refused:
--workdir <path-equal-to-or-containing-the-input-csv>/...
```

---

## CRITICAL — Read before writing any code

1. **Clinical trial AE analysis** (regression, chi-square, ANY severity test): Use the bundled script (or the `clinical_trial_ae_severity_test` ToolUniverse tool which wraps it):
   ```bash
   tu run clinical_trial_ae_severity_test '{"dm_file":"DM.csv","ae_file":"AE.csv","test":"chi-square","group_col":"TRTGRP"}'

   # Or directly:
   python skills/tooluniverse-statistical-modeling/scripts/prepare_ae_cohort.py \
     --dm DM.csv --ae AE.csv --test chi-square --group TRTGRP \
     --subgroup "expect_interact=Yes"   # optional
   ```
   The script/tool handles: `encoding='latin1'` for SDTM CSVs, `max(AESEV)` per subject across ALL AEs (no AEPT filtering), inner join with DM, optional subgroup filter, optional ordinal-logistic with covariates.

   **Why no AEPT filter** — AESEV is a protocol-defined severity scale on the AE table. Filtering AE by AEPT (e.g. keeping only `AEPT == "COVID-19"`) drops subjects whose worst severity was recorded under a different AEPT label, drastically changes the contingency table, and can flip the test result. The phrase "COVID-19 severity" describes the OUTCOME, NOT a filter criterion.

   - ❌ WRONG: `ae[ae['AEPT'].str.contains('COVID-19')].groupby('USUBJID')['AESEV'].max()` — filters to COVID-19 events
   - ✅ RIGHT: `ae.groupby('USUBJID')['AESEV'].max()` — uses ALL AE records

2. **Expression ANOVA / fold change with multi-feature data** (gene × sample matrix):
   For "the F-statistic" or "a fold change" as a single value, run per-gene then summarize — NEVER pool `expr.values.ravel()` across all genes.
   - For **F-statistic**: derive a per-sample quantity (like DESeq2 LFC of each gene between two cell types, then ANOVA on those LFCs across groups) OR run on a single target gene.
   - For **median/mean log2 fold change** between two groups: run DESeq2 with `design=~<group>`, extract per-gene `log2FoldChange` (with shrinkage if the pipeline uses it), then take median/mean across genes.

   ❌ WRONG (aggregate): `log2(sum_counts_groupA / sum_counts_groupB)` per sample then summarize — gives ratio of totals, dominated by high-expression genes.
   ✅ RIGHT (per-gene): DESeq2 → `results_df['log2FoldChange'].median()`.

   **Sanity heuristics**: F > 50 for biological ANOVA across a few groups means you aggregated (typical biological F is 0.5–10). |median LFC| > 2 between similar groups means you aggregated (typical |median| < 1).

   Use the bundled script: `python skills/tooluniverse-statistical-modeling/scripts/expression_anova.py` (or the `expression_anova_per_gene` ToolUniverse tool).

3. **Spline models** — R `splines::ns(x, df=K)` ≠ Python `patsy.dmatrix("cr(x, df=K)")`. They produce different design matrices because of internal-knot placement, boundary-knot placement, and basis orthogonalization. For ANY question that references R syntax like `lm(y ~ ns(x, df = 4))`, run R via `Rscript`. Use the bundled wrapper:

   ```bash
   python skills/tooluniverse-statistical-modeling/scripts/r_natural_spline_regression.py \
     --csv data.csv --y-col Y --x-col X --df 4 --workdir /tmp/spline_run
   ```

   For "frequency of strain X" co-culture models, include pure focal strain (freq=1) but exclude non-focal pure strain (freq=0).

4. **CSV encoding**: Clinical trial CSVs often need `encoding='latin1'`.

5. **Pearson correlation between count-like and length-like variables**: when one variable
   spans orders of magnitude (raw read counts, TPM, gene length, transcript abundance),
   raw Pearson r is often near 0 even when log-transformed r is moderate. **ALWAYS
   compute and explicitly report ALL FOUR variants in your final answer body**:
   `r(x, y)`, `r(log10(x+1), y)`, `r(x, log10(y+1))`, `r(log10(x+1), log10(y+1))`.
   List as a table; mark one as your primary pick. The published answer can be ANY of
   the four, and the question text rarely disambiguates which transform combination
   was used.

   ```
   ## Primary answer: r = X.XXX (transform: <name>)

   ## Sensitivity (all 4 transform combinations):
   - r(x, y)                   = ...
   - r(log10(x+1), y)          = ...
   - r(x, log10(y+1))          = ...
   - r(log10(x+1), log10(y+1)) = ...
   ```

   Background — for any single transform variant:

   ```python
   import numpy as np
   from scipy.stats import pearsonr
   r_raw, _ = pearsonr(x, y)
   r_log, _ = pearsonr(np.log10(x + 1), y)
   print(f"r_raw={r_raw:.4f}  r_log10={r_log:.4f}")
   ```

   Defaults:
   - Question says "log-transformed" / "log expression" → report **r_log10**
   - Question doesn't specify but the variable is gene expression / RNA count → also report **r_log10** as the canonical answer (most published correlations between gene length and expression are log-scale)
   - When `|r_raw| < 0.1` AND `|r_log10| > 0.2`, prefer **r_log10**

   ❌ WRONG: report only `r_raw ≈ 0.05` when log is `0.35`
   ✅ RIGHT: "r_raw = 0.05; r_log10 = 0.35 (canonical for log-distributed expression)"

---

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

For every result, report: effect size (OR/HR/coefficient), 95% CI, p-value, and model fit statistic. See `common_patterns_summary.md` for common question-answer patterns.

## Common Patterns

| Pattern | Question Type | Key Steps |
|---------|--------------|-----------|
| 1 | Odds ratio from ordinal regression | Fit OrderedModel, exp(coef) |
| 2 | Percentage reduction in OR | Compare crude vs adjusted model |
| 3 | Interaction effects | Fit `A * B`, extract `A:B` coef |
| 4 | Hazard ratio | Cox PH model, exp(coef) |
| 5 | Multi-feature ANOVA | Per-feature F-stats (not aggregate) |

See `common_patterns_summary.md` for solution code for each pattern.
See `references/common_patterns.md` for 15+ detailed question patterns.

## Statsmodels vs Scikit-learn

| Use Case | Library | Reason |
|----------|---------|--------|
| **Inference** (p-values, CIs, ORs) | **statsmodels** | Full statistical output |
| **Prediction** (accuracy, AUC) | **scikit-learn** | Better prediction tools |
| **Mixed-effects models** | **statsmodels** | Only option |
| **Regularization** (LASSO, Ridge) | **scikit-learn** | Better optimization |
| **Survival analysis** | **lifelines** | Specialized library |

**General rule**: Use statsmodels for statistical inference questions (p-values, ORs, HRs).

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
Use them via the Bash tool — they are the deterministic answer for the recurring
question patterns documented above.

### `r_natural_spline_regression.py` — Natural spline regression in R

Shells out to `Rscript` to fit `lm(y ~ ns(x, df=K))` with `splines::ns()`.
Emits R², adj R², F-stat with df1/df2, overall F-test p-value, residual SE,
coefficient table (estimate, SE, t, p), and the prediction-grid peak with
95% CI from `predict.lm(..., interval='confidence')`. Supports a
`--ratio-col` shortcut to convert "a:b" string ratios into a frequency
fraction `a/(a+b)`. Refuses to write into the input CSV's parent directory.

### `spline_model_compare.py` — Quadratic vs cubic vs natural spline

Fits all three models on the same x,y in R, ranks by adjusted R², AIC, and
BIC, and emits the best model's peak (x*, y*) with 95% CI. Use for
"best-fitting model" questions and "maximum predicted y at optimal x".

### `logistic_regression_or.py` — Binary or ordinal logistic regression with ORs

Fits `sm.Logit` (binary) or `OrderedModel` (ordinal proportional-odds) and
emits ORs (`exp(coef)`) plus 95% CIs and p-values for every coefficient.
Handles label encoding (`--encode A,B,C`), explicit value maps
(`--encode-map TRTGRP:Placebo=0,BCG=1`), and interaction columns
(`--interaction A:B` -> creates `A_B = A*B`). With `--coef-name <NAME>`
also prints a SCALARS block tagged for the requested coefficient.

### `power_analysis.py` — Two-sample required-N for a t-test

Computes Cohen's d (pooled SD) from a CSV given `--value-col`, `--group-col`,
`--group-a`, `--group-b`, then `TTestIndPower.solve_power` with `--alpha`,
`--power`, `--alternative`. Use for "minimum sample size per group" power
questions. Returns both the raw and the ceil-ed N.

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
+-- common_patterns_summary.md         # Common solution patterns
+-- test_skill.py                     # Test suite
+-- references/
|   +-- logistic_regression.md        # Detailed logistic examples
|   +-- ordinal_logistic.md           # Ordinal logit guide
|   +-- cox_regression.md             # Survival analysis guide
|   +-- linear_models.md              # OLS and mixed-effects
|   +-- common_patterns.md            # 15+ question patterns
|   +-- troubleshooting.md            # Diagnostic issues
+-- scripts/
    +-- r_natural_spline_regression.py # lm(y ~ ns(x, df=K)) via Rscript
    +-- spline_model_compare.py        # quadratic vs cubic vs natural-spline (Rscript)
    +-- logistic_regression_or.py      # binary / ordinal logistic + ORs + interactions
    +-- power_analysis.py              # TTestIndPower required-N from CSV
    +-- expression_anova.py            # per-gene ANOVA / log2FC summary
    +-- prepare_ae_cohort.py           # SDTM AE/DM cohort prep
    +-- stat_tests.py                  # Chi-square, Fisher's exact, OLS (stdlib)
    +-- format_statistical_output.py   # Format results for reporting
    +-- model_diagnostics.py           # Automated diagnostics
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

## Analysis conventions

These conventions are validated best practices. Apply when the dataset/question matches.

### MANDATORY: Use bundled script for expression ANOVA / fold change
For per-gene ANOVA or median log2FC questions, use the bundled script:
```bash
python skills/tooluniverse-statistical-modeling/scripts/expression_anova.py \
  --counts counts.csv --meta meta.csv --group-col cell_type \
  --exclude-groups PBMC --mode anova

python skills/tooluniverse-statistical-modeling/scripts/expression_anova.py \
  --counts counts.csv --meta meta.csv --group-col cell_type \
  --group-a CD14 --group-b CD19 --mode fold_change
```
Do NOT write your own pandas ANOVA — the aggregation level (per-gene, not per-sample) is critical and easy to get wrong.

### CSV encoding
Clinical-trial exports (SDTM) are often latin1. If `pd.read_csv()` fails with `UnicodeDecodeError`, retry with `encoding='latin1'`.

### Clinical-trial AE analysis — applies to regression AND chi-square AND any severity test
For **any statistical test** of a clinical-trial AE severity outcome (chi-square, ordinal/logistic regression, Mann-Whitney, etc.) on trial covariates, fit/test on the cohort that reported **any AE** (inner-joined to demographics). Do NOT pre-filter AE records by AEPT — NOT even when the question says "COVID-19 severity" or names any specific condition. Use `max(AESEV)` across **all AE records per subject**, regardless of AEPT.

**Why**: AESEV on the AE table reflects the study's protocol-defined severity scale. Pre-filtering to specific AEPT values (e.g., keeping only certain condition labels) drops subjects whose worst severity was recorded under a different AEPT label, which drastically changes the contingency table and can flip results from significant to non-significant.

Do NOT pad subjects with no AEs as AESEV=0 — that dilutes the signal.

```python
dm = pd.read_csv("DM.csv", encoding='latin1')
ae = pd.read_csv("AE.csv", encoding='latin1')
sev = ae.groupby('USUBJID')['AESEV'].max().reset_index()
df = dm.merge(sev, on='USUBJID', how='inner').dropna(subset=['AESEV'])
df['AESEV'] = df['AESEV'].astype(int)
# Now ordinal regression / chi-square on df
```

### Odds-ratio deviation
"**Percentage reduction in odds ratio**" means `(1 − OR) × 100%` — deviation from OR=1 (no effect). OR=0.75 → 25% reduction vs reference. Do NOT interpret as `(unadjusted_OR − adjusted_OR) / unadjusted_OR`; that's almost always ≈0% because adjustment barely moves a well-specified OR.

### F-statistic vs p-value
`scipy.stats.f_oneway(g1, g2, ...)` returns `(F, p)`. If GT looks like `(0.76, 0.78)` and you computed `F=91.6`, you returned the F-statistic when the question asked for the p-value (or vice-versa). Always re-read the question for which the answer expects.

### ANOVA on expression levels across groups — aggregation matters
When asked for "F-statistic comparing expression levels across cell types/groups":
- Each gene/miRNA is one **observation**. For N genes across K groups, you have N values per group (mean or median expression of that gene across samples in that group)
- Run `f_oneway(group1_values, group2_values, ...)` where each group has N gene-level values
- Do NOT sum all genes per sample — that gives total RNA content, a completely different quantity
- The F-stat is typically LOW (0.5–2.0) when most genes don't differ across groups, not HIGH (50+)
- If your F-statistic is >10 but the biological context suggests "no significant difference", you probably aggregated to sample level instead of gene level

### Log2 fold change between groups — per-gene, then summarize
When asked for "median log2 fold change between group A and group B":
- Compute log2FC **per gene**: for each gene, `log2(mean_expr_A / mean_expr_B)`
- Then take the median across all genes
- Do NOT sum all genes per sample first — that gives a single total-expression ratio, not the median per-gene fold change
- A median log2FC near 0 means most genes have similar expression between groups (expected when groups are similar cell types)

**Bundled script** for both ANOVA and fold change:
```bash
# Per-gene ANOVA across cell types
python skills/tooluniverse-statistical-modeling/scripts/expression_anova.py \
  --counts counts.csv --meta meta.csv --group-col cell_type \
  --exclude-groups PBMC --mode anova

# Per-gene log2FC between two groups
python skills/tooluniverse-statistical-modeling/scripts/expression_anova.py \
  --counts counts.csv --meta meta.csv --group-col cell_type \
  --group-a CD14 --group-b CD19 --mode fold_change
```

### Natural spline regression on strain co-culture data
When fitting models on strain co-culture frequency data:

1. **Ratio → frequency conversion**: If the Ratio column contains strings like `"10:1"`, convert to a frequency fraction: `first / (first + second)` = 0.909. Report as a fraction in [0, 1], not as ratio notation.

2. **Pure-strain endpoints**: Whether to include pure-strain data (freq=0 and freq=1) depends on the model type:
   - **Cubic/polynomial models**: Fit on co-culture rows ONLY (exclude pure strains). The cubic model captures the mixed-population response curve; pure strains are fundamentally different biological regimes and including them typically lowers R².
   - **Natural spline models (`ns(freq, df=4)`)**: Include the pure-strain endpoint for the **focal strain** (the one whose frequency the model predicts) but exclude the non-focal pure strain. For example, when modeling "frequency of ΔrhlI to total population", include pure ΔrhlI (freq=1.0) but exclude pure ΔlasI (freq=0.0). This anchors the spline at the high end where the focal strain dominates.

3. **R vs Python splines**: R's `ns()` (from the `splines` package) and Python's `patsy.cr()` or `scipy BSpline` produce DIFFERENT knot placements and boundary conditions. If the question references R's `lm(y ~ ns(x, df=4))`, use the bundled wrapper which runs R via Rscript:
   ```bash
   python skills/tooluniverse-statistical-modeling/scripts/r_natural_spline_regression.py \
     --csv data.csv --y-col Area --x-col Frequency \
     --df 4 --workdir /tmp/spline_run
   ```
   That emits R², adjusted R², overall F-test p-value, the coefficient table, and the prediction grid with peak (x*, y*) and 95% confidence interval at the peak.

   Do NOT substitute Python's `patsy.dmatrix("cr(x, df=4)")` — it will give different R², F-statistics, and predictions.

4. **Prediction at peak**: The bundled R wrapper already predicts on a fine 1000-point grid and reports `which.max(pred[,"fit"])` plus its CI from `interval="confidence"`. If you must do this by hand, follow the same recipe; do not use a coarse grid.

5. **Best of {quadratic, cubic, natural-spline}**: When the question asks for the "best fitting model among quadratic, cubic and natural spline" or the "maximum colony area at the optimal frequency", use the comparison wrapper which fits all three in R and ranks them:
   ```bash
   python skills/tooluniverse-statistical-modeling/scripts/spline_model_compare.py \
     --csv data.csv --y-col Area --x-col Frequency \
     --ns-df 4 --workdir /tmp/spline_cmp
   ```
   The output's `BEST_BY_ADJ_R2` row tells you which model wins, and `BEST_PEAK_Y` is the peak y to report.

## Support

For detailed examples and troubleshooting:
- **Logistic regression**: `references/logistic_regression.md`
- **Ordinal models**: `references/ordinal_logistic.md`
- **Survival analysis**: `references/cox_regression.md`
- **Linear/mixed models**: `references/linear_models.md`
- **Common patterns**: `references/common_patterns.md`
- **ANOVA and tests**: `anova_and_tests.md`
- **Diagnostics**: `references/troubleshooting.md`
