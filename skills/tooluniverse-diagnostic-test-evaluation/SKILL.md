---
name: tooluniverse-diagnostic-test-evaluation
description: Diagnostic test / biomarker accuracy — sensitivity, specificity, PPV, NPV, likelihood ratios, accuracy from a 2x2 table; ROC curve, AUC, and the optimal cutoff (Youden) for a continuous biomarker; and post-test probability via Bayes. Use when you have test results vs a gold standard (binary 2x2, or a continuous score + true labels) and need to judge how good the test is, pick a threshold, or compute the probability of disease given a result. Emphasizes the prevalence-dependence of PPV/NPV.
disable-model-invocation: true
---

# Diagnostic Test / Biomarker Accuracy Evaluation

Judge how well a test or biomarker discriminates disease — at a fixed cutoff (2×2) or across all cutoffs (ROC) — and turn a result into a probability of disease.

## Which case are you in?

| You have… | Go to |
|---|---|
| A 2×2 table (TP/FP/TN/FN) at a fixed cutoff | **Step 1** (`Epidemiology_diagnostic`) |
| A **continuous** biomarker score + true labels | **Step 2** (ROC / AUC / Youden, Python) |
| A test's sens/spec + a patient's pre-test probability | **Step 3** (`Epidemiology_bayesian`) |

## Step 1 — Fixed-cutoff metrics from a 2×2 table

```bash
tu run Epidemiology_diagnostic '{"operation":"diagnostic","tp":90,"fp":10,"tn":180,"fn":20}'
```

Returns `sensitivity`, `specificity`, `PPV`, `NPV`, `accuracy`, `LR_pos`, `LR_neg`, and the sample `prevalence`.

| Metric | Question it answers | Depends on prevalence? |
|---|---|---|
| **Sensitivity** = TP/(TP+FN) | Of those WITH disease, what fraction test positive? | No |
| **Specificity** = TN/(TN+FP) | Of those WITHOUT disease, what fraction test negative? | No |
| **PPV** = TP/(TP+FP) | If positive, what's the chance of disease? | **Yes — strongly** |
| **NPV** = TN/(TN+FN) | If negative, what's the chance of being disease-free? | **Yes** |
| **LR+** = sens/(1−spec) | How much a positive raises the odds of disease | No |
| **LR−** = (1−sens)/spec | How much a negative lowers the odds | No |

> **The PPV/NPV trap.** Sensitivity and specificity are properties of the *test*; **PPV and NPV depend on the disease prevalence in the tested population.** A test with great sens/spec has poor PPV in a low-prevalence (screening) setting. Never quote PPV/NPV from a case-control design (its 50/50 prevalence is artificial) — compute them for the real-world prevalence with `Epidemiology_bayesian` (Step 3). Report **sensitivity, specificity, and likelihood ratios** as the prevalence-independent summary.

## Step 2 — ROC / AUC / optimal cutoff for a continuous biomarker

When the test is a continuous score, evaluate across **all** thresholds:

Prefer the **`ROC_analysis`** tool — one call returns structured JSON (AUC + bootstrap 95% CI, Youden-optimal cutoff with its sens/spec, optional metrics at a fixed cutoff, and the ROC curve), and works under the MCP server without a shell:

```
ROC_analysis(scores=[...], labels=[0,1,...])          # inline arrays
ROC_analysis(csv_path="scores.csv", cutoff=0.6)        # or a CSV (cols: label, score)
```

The bundled script is the equivalent CLI form:

```bash
python skills/tooluniverse-diagnostic-test-evaluation/scripts/roc_analysis.py --input scores.csv
# scores.csv columns: label (1=disease, 0=healthy), score (continuous biomarker)
```

Both report AUC (with a bootstrap 95% CI), the **Youden-optimal cutoff** (max sensitivity+specificity−1) and its sens/spec.

| AUC | Discrimination |
|---|---|
| 0.5 | no better than chance |
| 0.7–0.8 | acceptable |
| 0.8–0.9 | excellent |
| >0.9 | outstanding |

- The **Youden** cutoff weights sensitivity and specificity equally; if false negatives and false positives have different costs, pick the threshold from the clinical tradeoff, not Youden.
- Once you choose a cutoff, build its 2×2 and run Step 1 for the fixed-cutoff metrics at that operating point.

## Step 3 — Post-test probability (Bayes)

Turn a result into the probability of disease for a given pre-test probability/prevalence:

```bash
tu run Epidemiology_bayesian '{"operation":"bayesian","prevalence":0.10,
  "sensitivity":0.90,"specificity":0.95,"test_result":"positive"}'
```

Returns `pre_test_odds`, the `LR`, and `post_test_probability`. This is how you get the *real-world* PPV: plug the true prevalence in. (Example: a 90%/95% test at 10% prevalence gives a post-positive probability of only ~67%, not 95%.)

## Gotchas (state these)

- **PPV/NPV without a stated prevalence are meaningless** — always give the prevalence they assume.
- **AUC ignores the operating point.** A high AUC doesn't tell you the test is useful at the threshold you'll actually use — report sens/spec at the chosen cutoff too.
- **Class imbalance.** With very few positives, ROC/AUC can look good while PPV is poor; consider a precision-recall curve and always report PPV at the real prevalence.
- **Spectrum bias.** Sens/spec measured on clearly-sick vs clearly-healthy subjects overestimate real-world performance on borderline cases.
- **Single cutoff chosen on the same data** it's evaluated on is optimistic — validate the threshold on a held-out set.

## Honest limitations

- These are discrimination/accuracy metrics, not calibration — a well-discriminating model can still output poorly-calibrated probabilities.
- A single AUC compares nothing; to compare two tests on the same patients, use a paired AUC test (DeLong) — beyond the basic script here.

## Related skills
- `tooluniverse-statistical-modeling` — logistic regression that produces the score, ORs.
- `tooluniverse-epidemiological-analysis` — population-level risk, screening program metrics.
- `tooluniverse-meta-analysis` — pool diagnostic accuracy across studies.
