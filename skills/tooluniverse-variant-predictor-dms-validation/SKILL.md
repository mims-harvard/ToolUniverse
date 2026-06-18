---
name: tooluniverse-variant-predictor-dms-validation
description: "Validate a variant-effect predictor (AlphaMissense, ESM-C SAE, ESM logits, EVE, conservation scores, or any per-variant numeric score) against experimental deep mutational scanning (DMS) data. Computes per-variant predictor scores, splits variants into neutral vs disruptive groups by DMS effect, runs a Mann-Whitney U test on the predictor scores, and sweeps the stratification thresholds for robustness. Use when you need to know whether a predictor's scores track real functional disruption on a specific protein."
disable-model-invocation: true
---

# Variant-effect predictor benchmarking against DMS

The core user question: **"I have a variant-effect predictor — does it actually
correlate with experimental DMS measurements on this protein?"**

The predictor can be anything that assigns a numeric score to single missense
variants:
- ESM-C 6B Sparse Autoencoder (SAE) feature drops at the mutation site
- AlphaMissense pathogenicity scores
- ESM logits-based variant scoring (`ESM_score_sequence`)
- EVE / EVE++ scores
- Conservation scores (ConSurf, Rate4Site)
- DynaMut2 ΔΔG predictions
- A custom in-house model

This skill validates ALL of these against a DMS dataset with the same statistical
framework. SAE is shown as the worked example because the surrounding skills in
this collection are SAE-themed, but the procedure is predictor-agnostic.

---

## When to use this skill

- You picked a variant-effect predictor and want to know if it's worth trusting
  on your protein of interest
- You're comparing two predictors on the same DMS dataset (run this skill twice,
  compare the resulting per-K Mann-Whitney U p-values + effect sizes)
- Reviewers want robustness evidence — the parameter sweep (K, neutral band,
  disruptive quantile) is exactly that
- You're publishing a new variant-effect method and need a benchmark figure

**Not for**:
- Per-position / per-feature interpretation — use
  `tooluniverse-residue-functional-mechanism-interpretation`
- Single-variant interpretation (you have one variant, no DMS) — use
  `tooluniverse-protein-sae-variant-interpretation` or
  `tooluniverse-protein-lof-mechanism`
- Building a predictor from scratch — out of scope

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| DMS effect matrix | (20 amino acids × n_positions) `np.array`, NaN for unmeasured | from `MaveDB_get_effect_matrix` |
| Disruptive tail convention | `"top"` (ΔΔG positive = destabilizing) or `"bottom"` (fitness low = LoF) | metadata from DMS retrieval step |
| Per-variant predictor scores | (20 × n_positions) `np.array` matching DMS layout | computed from your chosen predictor — see Step 2 |
| Aggregation K | `int`, mean of top-K when the predictor outputs many sub-scores per variant | only relevant for multi-feature predictors like SAE; ignore otherwise |

---

## Workflow

### Step 1: Retrieve DMS as an effect matrix

One call returns a ready-to-analyze `(20 × n_positions)` matrix — HGVS parsing,
single-missense filtering, score-field detection, and (optional) UniProt
numbering verification are done inside the tool:

```python
r = MaveDB_get_effect_matrix(
    urn="urn:mavedb:00000115-a-7",
    uniprot_id="P01116",     # optional but recommended — enables numbering check
)
matrix = np.array(r["data"]["matrix"], dtype=np.float32)  # (20, n_positions)
positions = r["data"]["positions"]
amino_acid_order = r["data"]["amino_acid_order"]          # always 'ACDEFGHIKLMNPQRSTVWY'
# Audit fields — surface in your report:
#   r["data"]["n_parsed_single_missense"], n_dropped, score_field_used,
#   numbering_offset, numbering_check
```

If `numbering_offset != 0`, the MaveDB position numbering differs from the
UniProt canonical sequence — apply the offset before joining to any other
source (PDB / SAE features / AlphaMissense).

### Step 2: Compute per-variant predictor scores

Pick **one** of these predictor sources. The choice changes Step 2 only; Steps
3–5 are identical.

#### Predictor option A — ESM-C 6B SAE (the worked example)

For every variant, sum SAE activations across the residue window, compute
drop = max(0, WT − mut), and aggregate to one score per variant via the
top-K mean of drops:

```python
import numpy as np

def sae_drop_per_variant(wt_pooled, variant_pooled, K=3):
    """SAE drop for one variant = mean of the K largest feature drops."""
    drops = np.maximum(0.0, wt_pooled - variant_pooled)  # (n_features,)
    sorted_desc = -np.sort(-drops)
    return float(sorted_desc[:K].mean())
```

**Two ways to score a saturation sweep** — pick based on batch size:

| When | Use | Forge cost (for 19 alts × N positions) |
|---|---|---|
| Saturation at ≤100 variants OR you only need top-K-per-variant deltas | `ESM_score_variant_sae_batch(sequence, variants=[...], top_k_features=10)` | **1 + 19N** (1 ref + 1 per mut) |
| Full-protein per-feature tensor (e.g. for downstream PCA / clustering) | Loop `ESM_get_sae_features(sequence=mutant)`, cache by `(sequence, position)` | **2 × 19N** (cached reruns free) |

The batch tool is the right default — it halves Forge cost vs the per-variant
disruption pattern, and the cap of 100 variants per call covers saturation
mutagenesis at one position (19) or short positional sweeps (e.g. positions
10-15: 90 variants). For longer sweeps, split into multiple batch calls.

For the full per-residue × per-feature tensor needed by some predictor
analyses, fall back to the loop pattern. The full library scale is
well-tested: `tests/integration/test_dms_pipeline_e2e_kras.py` runs ~300
mutants for KRAS positions 10–25.

#### Predictor option B — AlphaMissense (hegelab proxy: categorical, not per-substitution numeric)

The TU AlphaMissense tools proxy a public API (hegelab.org) that returns
**residue-level categorical assignments**, not per-(position, alt_aa) numeric
scores. Three calls are available; pick the one that matches your scale:

| Tool | Signature | Returns |
|---|---|---|
| `AlphaMissense_get_variant_score` | `uniprot_id`, `variant` (e.g. `"p.G12V"`) | Residue-level data INCLUDING the alt_aa's bin (`benign` / `ambiguous` / `pathogenic`); also `mean`/`mean_all` |
| `AlphaMissense_get_residue_scores` | `uniprot_id`, `position` | Same residue-level data (per-position lookup, cheaper than 19 variant calls) |
| `AlphaMissense_get_protein_scores` | `uniprot_id` | Whole-protein dump in one call (cheapest for full-protein DMS analysis) |

The response shape is the same for all three. Example for KRAS pos 12:

```python
r = AlphaMissense_get_residue_scores(uniprot_id="P01116", position=12)
# r["data"]["scores"]:
#   {"uid":"P01116","aa":"G","resi":12,
#    "benign":"", "ambiguous":"",
#    "pathogenic":"6:A,C,D,R,S,V",                  # ← SNV-reachable subs only
#    "pathogenic_all":"19:A,C,D,E,F,...,Y",         # ← all 19 substitutions
#    "mean":0.9885,           # mean over SNV-reachable subs
#    "mean_all":0.9950}       # mean over all 19 substitutions
# r["data"]["thresholds"]:
#   {"pathogenic":"> 0.564","ambiguous":"0.34 - 0.564","benign":"< 0.34"}
```

**To populate the `(20, n_positions)` predictor matrix**, parse the bin
strings and map each alt_aa to a numeric score (bin-midpoint is the standard
imputation since the tool doesn't expose true per-substitution numerics):

```python
BIN_MIDPOINTS = {"benign": 0.17, "ambiguous": 0.452, "pathogenic": 0.782}

def parse_bin_list(bin_str):
    """'6:A,C,D,R,S,V' → ['A','C','D','R','S','V']; '' → []."""
    if not bin_str:
        return []
    _, aas = bin_str.split(":", 1)
    return aas.split(",")

def am_per_variant_matrix(uniprot_id, positions, aa_index):
    AAS = list(aa_index)
    M = np.full((20, len(positions)), np.nan, dtype=np.float32)
    # One whole-protein call is much cheaper than n_positions calls
    p = AlphaMissense_get_protein_scores(uniprot_id=uniprot_id)
    per_res = {row["resi"]: row for row in p["data"]["scores"]}
    for pos_idx, pos in enumerate(positions):
        row = per_res.get(pos, {})
        for cat in ("benign", "ambiguous", "pathogenic"):
            for alt in parse_bin_list(row.get(f"{cat}_all", "")):
                if alt in aa_index:
                    M[aa_index[alt], pos_idx] = BIN_MIDPOINTS[cat]
    return M
```

**Higher-resolution alternative — DeepMind bulk CSV** (only if you genuinely
need true per-substitution numerics rather than bin-midpoints):

```python
# The official DeepMind release contains per-variant continuous scores
# (not just bin assignments). Not currently wrapped by a TU tool — fetch directly:
#   https://alphafold.ebi.ac.uk/files/AF-<uniprot_id>-F1-aa-substitutions.csv
# or stream-filter https://storage.googleapis.com/dm_alphamissense/AlphaMissense_aa_substitutions.tsv.gz
```

Use the bulk CSV when you need rank-correlation analysis (Spearman benefits
from continuous values, not 3-bin midpoints). Use the TU proxy when you only
need the binary "is this variant in the pathogenic bin" signal.

Both options are free, no API key required.

#### Predictor option C — ESM logits-based score

```python
ESM_score_sequence(
    sequence=mutant_sequence,
    model="esmc-600m-2024-12",
)
# returns per-residue logits; compute mutant-vs-WT log-odds at the mutation site
```

#### Predictor option C2 — ESM-2 masked-marginal (keyless, no API key)

When you have **no `ESM_API_KEY`** (the option A/C tools need one), use
`ESM2_score_missense_variant` — it runs ESM-2 over HuggingFace's free
`hf-inference` provider and returns the masked-marginal log-likelihood ratio
`logP(mut) − logP(wt)` (Meier et al. 2021) for one missense variant:

```python
# one call per variant; negative LLR = mutant disfavored (candidate deleterious)
res = ESM2_score_missense_variant(
    sequence=wild_type_sequence,   # 1-letter AA string
    position=position,             # 1-based
    mutant=alt_aa,                 # e.g. "V"
)
score = res["data"]["log_likelihood_ratio"]   # use directly as the predictor score
```

It is one HTTP call per variant (no batch endpoint), so for a saturation sweep
it is slower than the key-based ESM-C batch tools — prefer option A/C when you
have a key, and reach for this as the zero-setup fallback. Sequences over ~1022
residues are auto-windowed around the variant (see `metadata.windowed`). The
LLR is a ranking score, not a calibrated probability — Steps 3–5 handle the
thresholding, so feed the raw LLR straight into the `(20, n_positions)` matrix.

#### Predictor option D — any external score

Bring your own. Just produce a `(20, n_positions)` `np.ndarray` aligned to the
DMS matrix.

### Step 3: Stratify DMS into neutral vs disruptive

```python
def categorize(dms_matrix, disruptive_tail, neutral_abs=0.1, disruptive_quantile=0.05):
    """Split variants into neutral and disruptive masks.

    disruptive_tail: 'top' (positive = destabilizing, e.g. folding ΔΔG)
                     'bottom' (low = LoF, e.g. fitness)
    """
    flat = dms_matrix[~np.isnan(dms_matrix)]
    if disruptive_tail == "top":
        cut = np.quantile(flat, 1 - disruptive_quantile)
        disruptive = dms_matrix >= cut
    elif disruptive_tail == "bottom":
        cut = np.quantile(flat, disruptive_quantile)
        disruptive = dms_matrix <= cut
    else:
        raise ValueError("disruptive_tail must be 'top' or 'bottom'")
    neutral = np.abs(dms_matrix) <= neutral_abs
    disruptive = disruptive & ~np.isnan(dms_matrix)
    neutral = neutral & ~np.isnan(dms_matrix) & ~disruptive
    return neutral, disruptive
```

**Keep the neutral band tight** (`|effect| ≤ 0.1`). A loose neutral band leaks
weakly-disruptive variants into the "neutral" group and erodes the contrast.
**Sign matters** — get `disruptive_tail` from the DMS-retrieval skill's metadata;
a flipped sign silently inverts every conclusion.

### Step 3.5 (MANDATORY): Pre-MWU sanity gate — catch silent NaN failures

**Before running any statistical test**, verify the predictor scores actually
populated. Silent NaN matrices are the most common failure mode in this
workflow — a batch SAE compute that errored midway, an AlphaMissense fetch
that skipped variants, an ESM forge call that timed out — and they produce
"successful" runs that report meaningless statistics.

```python
neutral, disruptive = categorize(dms_matrix, disruptive_tail)
s_neutral_all = predictor_scores[neutral]
s_disruptive_all = predictor_scores[disruptive]
s_neutral_finite = s_neutral_all[~np.isnan(s_neutral_all)]
s_disruptive_finite = s_disruptive_all[~np.isnan(s_disruptive_all)]

# Hard gate: NaN coverage check
coverage_n = len(s_neutral_finite) / max(len(s_neutral_all), 1)
coverage_d = len(s_disruptive_finite) / max(len(s_disruptive_all), 1)
if len(s_neutral_finite) < 5 or len(s_disruptive_finite) < 5:
    raise ValueError(
        f"Insufficient predictor scores: only {len(s_neutral_finite)} neutral "
        f"and {len(s_disruptive_finite)} disruptive non-NaN values. "
        f"Coverage = {coverage_n:.0%} / {coverage_d:.0%}. "
        f"Predictor matrix may be empty / failed to populate. "
        f"INVESTIGATE THE PREDICTOR COMPUTATION STEP before continuing."
    )
if coverage_n < 0.5 or coverage_d < 0.5:
    print(f"WARNING: predictor coverage only {coverage_n:.0%} (neutral) / "
          f"{coverage_d:.0%} (disruptive). Results may be biased toward the "
          f"non-NaN subset.")
```

If you hit the `ValueError`: do not paper over with "predictor X wins by
default". The right response is to debug the predictor computation step
(re-run, check API keys, check log files) and report what failed.

**Sign-convention double-check** (also mandatory if the dataset is new):
verify `disruptive_tail` against the data using an internal landmark. The
metadata field can be misleading on subsets (e.g. a window of TP53 DBD
might run the opposite direction from the full TP53 abundance assay). The
cheapest check is Spearman correlation between DMS effect and a predictor
known to align in a fixed direction (AlphaMissense pathogenicity score is
always positive=more-damaging):

```python
from scipy.stats import spearmanr
flat_dms = dms_matrix.ravel()
flat_pred = predictor_scores.ravel()
mask = ~(np.isnan(flat_dms) | np.isnan(flat_pred))
rho, p_corr = spearmanr(flat_dms[mask], flat_pred[mask])
expected_sign = "+" if disruptive_tail == "top" else "-"
got_sign = "+" if rho > 0 else "-"
if got_sign != expected_sign and abs(rho) > 0.1:
    print(f"WARNING: Spearman rho = {rho:.3f} (sign={got_sign}) but "
          f"disruptive_tail='{disruptive_tail}' expects sign={expected_sign}. "
          f"Sign convention may be inverted for THIS subset. Verify before "
          f"interpreting MWU.")
```

### Step 4: One-sided Mann-Whitney U test

```python
from scipy.stats import mannwhitneyu

u, p = mannwhitneyu(s_disruptive_finite, s_neutral_finite, alternative="greater")
print(f"disruptive median = {np.median(s_disruptive_finite):.4f}, "
      f"neutral median = {np.median(s_neutral_finite):.4f}, p = {p:.3g}")
```

For SAE-style multi-feature predictors with a top-K parameter, run this for
K ∈ {1, 3, 10} and report all three — the best K is usually different across
predictors and you want the comparison transparent, not tuned.

**MWU is the discrimination test, but it's not the only valid analysis.**
Consider also reporting (one or both):
- **Spearman rank correlation** between predictor and DMS effect — captures
  graded calibration the binary neutral/disruptive split discards. Best for
  "is this predictor calibrated?" questions, not just "does it discriminate?"
- **AUROC** at a clinically-meaningful disruption threshold (e.g. ΔΔG > 1
  kcal/mol) — gives a 0-1 number practitioners recognize and lets you compare
  to literature predictors directly.

The eval that motivated this skill (KRAS folding AlphaMissense benchmark)
got *qualitatively similar* answers from MWU (p=0.20, "not reliable") and
Spearman (ρ=0.23, p<1e-30, "weakly calibrated") — but Spearman's reading was
richer. If the user just asks "is X reliable?", give both unless one is
clearly inappropriate for the data shape.

### Step 5: Robustness sweep

```python
sweep = []
for neutral_abs in (0.05, 0.1, 0.2):
    for q in (0.05, 0.1):
        neut, disr = categorize(dms_matrix, disruptive_tail,
                                neutral_abs=neutral_abs,
                                disruptive_quantile=q)
        s_n = predictor_scores[neut][~np.isnan(predictor_scores[neut])]
        s_d = predictor_scores[disr][~np.isnan(predictor_scores[disr])]
        if len(s_n) < 5 or len(s_d) < 5:
            continue
        _u, p = mannwhitneyu(s_d, s_n, alternative="greater")
        sweep.append({"neutral_abs": neutral_abs, "disruptive_q": q, "p": p,
                      "n_n": len(s_n), "n_d": len(s_d)})
```

A predictor that passes only at one (neutral_abs, q) point is suspect. A
predictor that passes across the grid is robust.

### Step 6: Visualize + interpret

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 4))
ax.boxplot(
    [s_neutral, s_disruptive],
    labels=[f"neutral (n={len(s_neutral)})", f"disruptive (n={len(s_disruptive)})"]
)
ax.set_ylabel("Predictor score")
ax.set_title(f"p = {p:.3g}")
plt.tight_layout()
plt.savefig("predictor_vs_dms.png", dpi=150)
```

---

## Interpretation

| Result | What it means |
|---|---|
| **p < 0.01 AND robust across sweep** | Predictor reliably distinguishes disruptive from neutral on this protein. Safe to use for prioritization (not classification — see limits) |
| **p < 0.05 but flips signs in sweep** | Borderline. Effect exists but is sensitive to stratification — needs more data or tighter neutral band |
| **p > 0.05** | Predictor is not informative on this DMS assay. Possible causes: wrong `disruptive_tail`, predictor mis-calibrated for this protein family, DMS measures something the predictor wasn't trained for |
| Significant **at K=1 but not K=10** (multi-feature predictors only) | Disruption is concentrated in a few features (K=1 best) vs distributed across many (K=10) |

---

## Comparing two predictors

Run this skill twice on the same DMS dataset (e.g. SAE drops AND AlphaMissense),
keep the same stratification (`disruptive_tail`, `neutral_abs`, `disruptive_quantile`),
and compare:

| Metric | Better predictor has |
|---|---|
| Lower p-value | More confidence of discrimination |
| Larger median gap (disruptive − neutral) | Larger effect size |
| Fewer NaNs in coverage | Predicts more variants |
| Robust across sweep | More reliable in different conditions |

---

## Honest limitations

1. **Per-protein test only**. Generalizing "predictor X is good" requires running
   this on multiple proteins from different families.
2. **Per-assay only**. A predictor calibrated for stability might fail on
   binding-fitness assays — same protein, different DMS, different result.
3. **Coarse signal**. This says "predictor responds to mutational disruptiveness."
   It does NOT say "predictor identifies the *right* residues" — for that, run
   `tooluniverse-residue-functional-mechanism-interpretation`.
4. **MWU assumes independence**. DMS variants at the same position are mildly
   correlated (shared structural context); the p-values are slightly optimistic.
5. **Tail definitions are arbitrary**. 5% disruptive cutoff and 0.1 neutral band
   are reasonable defaults; the right thresholds depend on the assay's
   signal-to-noise. The sweep is what gives you robustness, not any single choice.

---

## Cross-references

| Step | Tool / Skill |
|---|---|
| DMS retrieval | `MaveDB_get_effect_matrix` |
| Per-variant SAE scoring (≤100 variants) | `ESM_score_variant_sae_batch` (preferred — N+1 calls) |
| Per-variant SAE scoring (full tensor / unlimited) | `ESM_get_sae_features` (loop + cache), `ESM_score_variant_sae_disruption` (single variant) |
| Per-variant AlphaMissense (single lookup) | `AlphaMissense_get_variant_score(uniprot_id, variant)` |
| Per-position AlphaMissense (saturation) | `AlphaMissense_get_residue_scores(uniprot_id, position)` |
| Whole-protein AlphaMissense (cheapest for DMS) | `AlphaMissense_get_protein_scores(uniprot_id)` |
| Per-variant ESM logits | `ESM_score_sequence` |
| Structural prior (for predictor analysis) | `Structure_annotate_per_residue` |
| Next step: per-hotspot mechanism | `tooluniverse-residue-functional-mechanism-interpretation` |
| Final visualization | Step 7 of `tooluniverse-residue-functional-mechanism-interpretation` (annotated heatmap + callouts) |

