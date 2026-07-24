---
name: tooluniverse-protein-sae-variant-interpretation
description: "Interpret a missense variant via ESMC-6B Sparse Autoencoder (SAE) feature activations. For a given protein + variant, computes which interpretable SAE features (catalytic, ligand-binding, PTM, structural motif, domain, etc.) are lost or gained at the mutation site. Use when standard pathogenicity scores (AlphaMissense, ClinVar) say a variant is damaging but you need a MECHANISTIC explanation — e.g. 'why is this variant LoF?' Complements (does not replace) variant-interpretation and variant-to-mechanism skills, which focus on ACMG classification or regulatory mechanism."
disable-model-invocation: true
---

# Protein SAE Variant Interpretation

Interpret a single missense variant by comparing reference vs mutant Sparse Autoencoder (SAE) feature activations from the ESMC-6B protein language model. SAE features are interpretable latent dimensions of the model's hidden state — many activate on biologically meaningful patterns (active sites, ligand-binding pockets, PTM sequons, structural motifs).

---

## When to use this skill

Apply when users:
- Ask "why is variant X (a missense) loss-of-function?" and need a mechanistic answer beyond a pathogenicity score
- Have an AlphaMissense / ClinVar "damaging" variant and want to know **which functional feature breaks** (catalytic? binding? PTM site? structural?)
- Want to compare ref vs mutant protein representation at a specific residue
- Are interpreting why a structurally subtle change (single AA) has a big functional impact

**Not for** (use other skills instead):
- ACMG pathogenicity classification → `tooluniverse-variant-interpretation`
- Regulatory / non-coding variants → `tooluniverse-variant-to-mechanism`
- Variant-to-disease association without mechanism → `tooluniverse-gene-disease-association`
- Cancer-specific variant interpretation → `tooluniverse-cancer-variant-interpretation`

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| Protein identifier | UniProt accession or HGNC gene symbol | `P04637` or `TP53` |
| Variant | Single-letter code: `{ref_aa}{position_1idx}{alt_aa}` | `R175H` |

Optional:
- Window radius (default 8): residues around the mutation to analyze
- Reference protein sequence (skip the UniProt lookup if already known)

---

## Prerequisites

- **ESM_API_KEY** env var with a valid EvolutionaryScale Forge token (https://forge.evolutionaryscale.ai)
- **esm package with SAE support**:
  ```
  pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'
  ```
  The PyPI release of `esm` does NOT yet include SAEConfig. Install from the upstream feature branch.

**License note**: SAE outputs from Forge are governed by the [Cambrian Inference Clickthrough License](https://www.evolutionaryscale.ai/policies/cambrian-inference-clickthrough-license-agreement) — non-commercial / academic research use only unless a separate commercial agreement applies.

---

## Workflow (5 steps)

### Step 1: Resolve gene → UniProt accession (if needed)

If the user gave a gene symbol, resolve to a reviewed human accession:

```python
UniProt_search(
    query="gene:TP53 AND organism_id:9606 AND reviewed:true",
    fields=["accession", "gene_names", "protein_name"],
)
# → returns accession P04637 as the canonical reviewed human TP53
```

### Step 2: Fetch the canonical reference sequence

```python
UniProt_get_sequence_by_accession(accession="P04637")
# → returns the canonical isoform 1 sequence (393 AA for TP53)
```

### Step 3: Validate the reference residue + build mutant sequence

Parse the variant string (e.g. `R175H`):
- `ref_aa = "R"`, `position = 175` (1-indexed), `alt_aa = "H"`
- Verify `ref_sequence[174] == "R"` (Python is 0-indexed, position is 1-indexed)
- Build mutant: `mutant_sequence = ref_sequence[:174] + "H" + ref_sequence[175:]`

If the reference residue does NOT match, return an explicit error — do not silently mutate the wrong position.

### Quick path (recommended for variant analysis): composite tool

For the standard variant-interpretation use case, use one of two composite tools depending on how much you need:

**Fullest one-call** — disruption + per-feature biological category labels + mechanism summary:
```python
ESM_explain_variant_mechanism(
    sequence=ref_sequence,
    position=175, ref_aa="R", alt_aa="H",
    window=8,
    top_k_features=5,       # describe top 5 lost + top 5 gained
)
# data["mechanism_summary"] e.g. "Disrupted feature categories (lost): catalytic=2, ligand-binding=1"
# data["lost_feature_categories"] / ["gained_feature_categories"] — category counts
# data["top_features_lost"] / ["top_features_gained"] — per-feature delta + category + confidence
```
This is the right default for variant-mechanism reports — saves you from chaining `ESM_score_variant_sae_disruption` + N `ESM_describe_sae_feature` calls. Set `include_descriptions=false` to skip labeling (2 Forge calls only) when you just need the deltas.

**Raw delta only** (no category labels, no describe calls — faster):
```python
ESM_score_variant_sae_disruption(
    sequence=ref_sequence,
    position=175, ref_aa="R", alt_aa="H",
    window=8, top_k_features=10,
)
# → returns top_features_lost + top_features_gained ranked by |delta|
#   plus ref / mut activation sums per feature
```

If ref_aa doesn't match the sequence at the given position, both tools return a clear error (you supplied the wrong isoform / mis-labeled the variant). The longer path below is for inspecting raw per-residue features.

**Multiple variants at once** (e.g. saturation at residue 175 — all 19 alternates):
```python
alts = "ACDEFGHIKLMNPQRSTVWY".replace("R", "")
variants = [{"position": 175, "ref_aa": "R", "alt_aa": a} for a in alts]
ESM_score_variant_sae_batch(sequence=ref_sequence, variants=variants, top_k_features=5)
# 1 + 19 = 20 Forge calls, not 38
```

### Step 4 (long path): Get SAE features for reference and mutant

```python
ref_features = ESM_get_sae_features(
    sequence=ref_sequence,
    position=175,          # 1-indexed mutation position
    window=8,              # +/- 8 residues = 17-residue window
    top_k_per_residue=64,  # full sparsity (k=64 is the SAE's actual k)
)

mut_features = ESM_get_sae_features(
    sequence=mutant_sequence,
    position=175,
    window=8,
    top_k_per_residue=64,
)
```

Each call returns a list of `{residue_idx_1based, active_features: [{feature_id, activation}]}` for residues in the window. Typical latency: ~1-3 seconds per call (so ~2-6s total). Forge cost: 2 credits (1 per call).

### Step 5: Compute per-feature activation deltas

Aggregate gained / lost features over the window:

```python
# Build per-feature activation arrays across the window
def feature_to_window_sum(features_response):
    sums = {}  # feature_id -> sum of activations across all residues in window
    for residue in features_response["data"]["activations"]:
        for f in residue["active_features"]:
            sums[f["feature_id"]] = sums.get(f["feature_id"], 0.0) + f["activation"]
    return sums

ref_sums = feature_to_window_sum(ref_features)
mut_sums = feature_to_window_sum(mut_features)

# Delta = mut - ref. Positive = gained on mutation. Negative = lost.
all_features = set(ref_sums) | set(mut_sums)
deltas = {
    f: mut_sums.get(f, 0.0) - ref_sums.get(f, 0.0)
    for f in all_features
}

top_lost = sorted(deltas.items(), key=lambda x: x[1])[:10]       # most negative
top_gained = sorted(deltas.items(), key=lambda x: -x[1])[:5]     # most positive
```

---

## Interpretation table

The 16,384 SAE features have been categorized (by UniRef90 activation patterns) into ~6 biological types. Interpret features by their dominant category:

| Category | What it means biologically | Variant types it often catches |
|---|---|---|
| **Catalytic function** | Activates on residues at or near enzyme active sites | Variants that disrupt enzymatic activity (kinases, hydrolases, transferases) |
| **Ligand-binding site** | Activates on residues that contact small-molecule / ion / nucleotide ligands | Variants disrupting drug binding, ATP/GTP binding, metal coordination, DNA/RNA binding |
| **Post-translational modification (PTM)** | Activates on phospho-sites, glycosylation sequons, ubiquitin sites, acetylation sites | Variants disrupting phospho-regulation, N-glycosylation, ubiquitin-mediated degradation |
| **Domain / motif** | Activates on classic structural domains (Zn finger, leucine zipper, EF-hand, etc.) | Variants disrupting tertiary fold within a domain |
| **Structural stability** | Activates on residues critical to local fold | Variants destabilizing the protein → folding LoF |
| **Secondary structure / surface** | Activates on alpha helices, beta strands, solvent-exposed residues | Lower-specificity; weak mechanism signal |

When SAE features are lost in mutation → that biological capability is plausibly disrupted.  
When SAE features are gained → mutation may have introduced a non-native signal (often disorder / alternative fold).

Look up the biological category of any specific `feature_id` via `ESM_describe_sae_feature(feature_id=...)`. The first call for a given feature is slow (~30s, ~10 Forge credits as the tool runs SAE on a 10-protein labeling panel + checks UniProt annotations); subsequent calls for the same feature hit a local cache and are instant.

---

## Honest limitations

1. **SAE features ≠ ground-truth function**. SAE features are LEARNED from sequence patterns. "Feature 16076 looks like an N-glycosylation detector" is a hypothesis from how the feature behaves across UniRef90, not a per-residue functional annotation. Use it as **evidence, not proof**.
2. **±8 residue window only**. The window covers local effects (active-site disruption, motif breakage). It does NOT capture long-range allosteric effects, dimerization interface effects, or domain-domain rearrangements that change features far from the mutation.
3. **Feature label coverage is partial**. Some of the 16,384 features have not been categorized well — they activate diffusely or on unclear patterns. For uncategorized features, the SAE delta is still informative (something changed) but the biological interpretation is weaker.
4. **Single-isoform only**. Uses UniProt canonical sequence. If the variant lives in a non-canonical isoform, results may not apply.
5. **6b SAE only**. Currently TU supports the `esmc-6b-2024-12_k64_codebook16384_layer60` SAE. The smaller `600m` SAE exists but has not been validated against the LoF benchmark from the source repo.
6. **Forge API non-commercial**. Outputs from this skill cannot be used for commercial purposes without a separate license from EvolutionaryScale.

---

## Cross-validation pattern (recommended)

A single SAE-based analysis can be misleading on its own. For high-stakes interpretation, cross-validate with structural / population evidence:

| Layer | Tool | Confirms |
|---|---|---|
| Population frequency | `gnomad_get_variant` / `gnomad_search_variants` | Is the variant rare? (LoF candidates are usually rare or absent) |
| Pathogenicity prediction | `AlphaMissense_get_variant_score` | Does an independent ML predictor agree it's damaging? |
| Clinical evidence | `ClinVar_search_variants` + `ClinVar_get_variant_details` | Is this variant already curated with clinical significance? |
| Structural context | `alphafold_get_prediction` (returns pLDDT per residue) | Is the mutated residue in a well-folded region (pLDDT > 70)? |
| Functional annotation | `UniProt_get_disease_variants_by_accession`, `UniProt_get_function_by_accession` | Is the mutated residue in a known catalytic / binding / PTM site? |

If 3+ layers agree the variant is damaging, the SAE feature analysis is the **mechanistic explanation layer**: "AlphaMissense says it's damaging, gnomAD confirms it's absent in population, SAE shows the catalytic feature is lost → this is a catalytic LoF variant."

---

## Reporting format

After completing the workflow, summarize as:

```
Variant: {VARIANT_ID}  (e.g. P04637_R175H = TP53 R175H)
Protein: {gene} ({uniprot_accession})

Top features LOST at position {position} ± {window}:
  - Feature {id}: activation Δ = {delta:.2f}  (category: {category})
    {one-line biological summary}
  ...

Top features GAINED at position {position} ± {window}:
  - Feature {id}: Δ = +{delta:.2f}  (category: {category if known else "uncategorized"})
  ...

Mechanistic interpretation: {2-3 sentences synthesizing the SAE evidence
with cross-validation layers}

Confidence: {high|medium|low}, based on:
  - SAE evidence: {how clear is the dominant category?}
  - Cross-validation: {how many layers agree?}
  - Limitations encountered: {any of the 6 caveats above that apply}
```

