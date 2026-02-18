# tooluniverse-statistical-modeling

Statistical modeling skill for biomedical data analysis, designed to solve BixBench regression, survival, and statistical testing questions.

## Capabilities

| Model Type | Implementation | Key Outputs |
|-----------|---------------|-------------|
| Linear Regression (OLS) | `statsmodels.formula.api.ols` | Coefficients, R-squared, F-test, AIC/BIC |
| Binary Logistic Regression | `statsmodels.formula.api.logit` | Odds ratios, CIs, p-values, pseudo-R-squared |
| Ordinal Logistic Regression | `statsmodels.miscmodels.ordinal_model.OrderedModel` | Odds ratios, thresholds, proportional odds test |
| Multinomial Logistic Regression | `statsmodels.MNLogit` / `sklearn.LogisticRegression` | Per-category ORs, relative risk ratios |
| Mixed-Effects Models | `statsmodels.formula.api.mixedlm` | Fixed effects, random variance, ICC |
| Cox Proportional Hazards | `lifelines.CoxPHFitter` | Hazard ratios, CIs, concordance index |
| Kaplan-Meier Estimation | `lifelines.KaplanMeierFitter` | Median survival, survival curves, log-rank test |
| Statistical Tests | `scipy.stats` | t-test, chi-square, Fisher, ANOVA, Mann-Whitney, etc. |

## BixBench Question Coverage

The skill handles these BixBench question patterns:

1. **Odds ratio extraction**: "What is the odds ratio of X associated with Y?"
2. **Ordinal logistic regression**: "What is the OR using ordered logit model?"
3. **Percentage reduction in OR**: "What is the percentage reduction after adjusting for confounders?"
4. **Interaction effects**: "What is the interaction odds ratio?"
5. **Hazard ratios**: "What is the hazard ratio for treatment in Cox regression?"
6. **Survival estimates**: "What is the median survival time?"
7. **Model coefficients**: "What is the coefficient and 95% CI?"
8. **Model comparison**: "Which model fits better (AIC/BIC)?"
9. **Adjusted vs unadjusted**: "How does the OR change after adjustment?"
10. **Statistical significance**: "Is the association statistically significant?"

## Dependencies

```
statsmodels>=0.14.0
scikit-learn>=1.3.0
lifelines>=0.27.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
```

## Files

| File | Description |
|------|-------------|
| `SKILL.md` | Full skill specification with all phases and code patterns |
| `QUICK_START.md` | 8 worked examples covering all model types |
| `EXAMPLES.md` | Detailed BixBench-style worked examples |
| `TOOLS_REFERENCE.md` | Package/function reference and decision tree |
| `test_skill.py` | 85-test comprehensive test suite |
| `README.md` | This file |

## Testing

```bash
python3 test_skill.py
```

Test coverage: 15 sections, 85 tests, covering:
- Package imports (5 tests)
- OLS linear regression + diagnostics (8 tests)
- Binary logistic regression + odds ratios (7 tests)
- Ordinal logistic regression + proportional odds (7 tests)
- Multinomial logistic regression (5 tests)
- Mixed-effects models + ICC (6 tests)
- Cox proportional hazards (7 tests)
- Kaplan-Meier estimation + log-rank (5 tests)
- Statistical tests (9 tests)
- Confidence intervals (3 tests)
- Model comparison (3 tests)
- BixBench question patterns (7 tests)
- Edge cases and robustness (6 tests)
- Data loading and processing (3 tests)
- Effect size and interpretation (3 tests)

Result: **85/85 tests pass (100.0%)**

## Model Selection Guide

```
Outcome Type           -> Model
------------------------------------
Continuous             -> OLS (smf.ols)
Continuous + clusters  -> LMM (smf.mixedlm)
Binary                 -> Logistic (smf.logit)
Ordinal (3+ levels)    -> OrderedModel (distr='logit')
Nominal (3+ levels)    -> MNLogit
Time-to-event          -> Cox PH / Kaplan-Meier
Count data             -> Poisson / NB
```
