---

name: tooluniverse-protein-lof-mechanism
description: "Propose the mechanism by which a missense variant causes loss-of-function (LoF), synthesizing evidence from 5 independent layers: AlphaMissense pathogenicity, AlphaFold structural context, ESMC sequence likelihood, SAE feature disruption, and DynaMut2 stability ΔΔG. Distinguishes 'structural stability LoF' (mis-folding) from 'direct functional disruption' (catalytic / binding / PTM site damage). Use for coding missense variants where you need a mechanistic causal model, not just a pathogenicity score."
---

# Protein LoF Mechanism Synthesis

For a single missense variant, integrate 5 independent computational signals to propose a specific loss-of-function mechanism. Each signal answers a different question:

| Signal | Tool | Answers |
|---|---|---|
| Pathogenicity | `AlphaMissense_get_variant_score` | "Is this variant damaging?" |
| Structural context | `alphafold_get_prediction` | "Is the mutation in a folded vs disordered region?" |
| Sequence likelihood | `ESM_score_sequence` | "Is the substitution evolutionarily plausible?" |
| Feature disruption | `ESM_explain_variant_mechanism` (or `ESM_score_variant_sae_disruption` + `ESM_describe_sae_feature` for raw control) | "Which biological feature breaks?" |
| Stability | `DynaMut2_predict_stability` | "Does the protein still fold correctly?" |

---

## When to use this skill

Apply for **missense (coding) variants** where:
- You already have evidence the variant is damaging (or want to find out)
- You need to know **WHY** it's damaging in molecular terms
- Downstream work depends on the mechanism: drug rescue strategies need to know what's broken, gene-therapy decisions need to distinguish "fix the protein" vs "replace the protein", clinical reporting wants a mechanism narrative

**Not for** (use other skills instead):
- Non-coding / regulatory variants → `tooluniverse-variant-to-mechanism`
- ACMG pathogenicity classification → `tooluniverse-variant-interpretation`
- Just the SAE feature disruption (without full synthesis) → `tooluniverse-protein-sae-variant-interpretation`
- Cancer-specific drivers → `tooluniverse-cancer-variant-interpretation`

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| Variant ID | `{accession}_{ref_aa}{position}{alt_aa}` | `P04637_R175H` |
| Or: UniProt accession + variant string | accession + ref/pos/alt | `P04637`, `R175H` |
| Or: gene symbol + variant | HGNC symbol + ref/pos/alt | `TP53`, `R175H` |

Parse the variant string:
```python
import re
m = re.match(r"([A-Z])(\d+)([A-Z])", variant_str)
ref_aa, position, alt_aa = m.group(1), int(m.group(2)), m.group(3)
```

---

## Prerequisites

- **ESM_API_KEY** env var for SAE signals (https://forge.evolutionaryscale.ai)
- **esm package with SAE support**: `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'`
- Internet access for AlphaMissense, AlphaFold, UniProt, DynaMut2 (all hosted endpoints, no API key required for these)

---

## Workflow

### Step 0: Resolve accession + fetch canonical sequence

If user gave a gene symbol:
```python
UniProt_search(
    query="gene:TP53 AND organism_id:9606 AND reviewed:true",
    fields=["accession"],
)
# → P04637
```

Get the canonical sequence:
```python
UniProt_get_sequence_by_accession(accession="P04637")
```

Validate the reference residue:
```python
assert sequence[position - 1] == ref_aa, "Wrong sequence or wrong isoform"
```

### Step 1: AlphaMissense pathogenicity

```python
AlphaMissense_get_variant_score(
    uniprot_id="P04637",
    position=175,
    ref_aa="R",
    alt_aa="H",
)
# → returns score 0..1; ≥0.564 is the "likely pathogenic" threshold per the
#   AlphaMissense paper. Above 0.9 is very confident damaging.
```

If AlphaMissense says benign (≤0.34), the rest of the analysis is exploratory — most benign variants don't have a clear LoF mechanism.

### Step 2: AlphaFold structural context

```python
alphafold_get_prediction(uniprot_id="P04637")
# → returns structure data including per-residue pLDDT
```

Check pLDDT at the mutation position:
- **pLDDT > 70** → well-folded region; the variant is in a structured area; structural / functional disruption is meaningful
- **pLDDT 50-70** → flexible / partially folded; interpretation is ambiguous
- **pLDDT < 50** → disordered; SAE / stability signals may not be reliable

### Step 3: ESMC sequence likelihood

```python
ESM_score_sequence(
    sequence=ref_sequence,
    model="esmc-600m-2024-12",  # or 300m for cheaper
)
# Then for the mutant sequence:
ESM_score_sequence(
    sequence=mutant_sequence,
    model="esmc-600m-2024-12",
)
```

Compute **ΔlogP = mean_logP(mutant) − mean_logP(reference)** at the position window:
- **ΔlogP < −1** → mutation is evolutionarily implausible (strong signal of functional cost)
- **ΔlogP ≈ 0** → mutation is conservative or in a tolerant position
- ΔlogP > 0 is rare and usually noise

### Step 4: SAE feature disruption (the unique signal)

**Recommended — one call** (composite tool, returns disruption + category labels + summary):
```python
ESM_explain_variant_mechanism(
    sequence=ref_sequence,
    position=175,
    ref_aa="R",
    alt_aa="H",
    window=8,
    top_k_features=5,
)
# data["mechanism_summary"] e.g.:
#   "Disrupted feature categories (lost): catalytic=2, ligand-binding=1"
# data["lost_feature_categories"] / data["gained_feature_categories"] give the raw counts
# data["top_features_lost"] / data["top_features_gained"] include per-feature deltas + categories
```

**Lower-level alternative** (use only if you need the raw feature_ids before labeling, e.g. to filter to one category before describe calls):
```python
ESM_score_variant_sae_disruption(
    sequence=ref_sequence, position=175, ref_aa="R", alt_aa="H",
    window=8, top_k_features=10,
)
# Then for each kept feature:
ESM_describe_sae_feature(feature_id=feat["feature_id"])
# → returns category: catalytic | ligand-binding | ptm | domain |
#   motif | structural-stability | secondary-structure |
#   transmembrane | signal-peptide | propeptide | uncategorized
```

**Dominant category among top lost features = the function most likely disrupted.**

### Step 5: DynaMut2 stability (ΔΔG)

DynaMut2 needs a PDB structure. Two options:

**Option A** — use a PDB ID if available for this protein:
```python
# Look up PDB cross-references from UniProt entry
UniProt_get_entry_by_accession(accession="P04637")
# → check `uniProtKBCrossReferences` for entries with database == "PDB"
# → pick a structure that covers the mutation position
```

```python
DynaMut2_predict_stability(
    pdb_id="2FEJ",   # example TP53 DNA-binding domain crystal structure
    chain="A",
    mutation="R175H",
)
# → returns ddG in kcal/mol
```

**Option B** — if no experimental PDB covers the position, use the AlphaFold model (output of Step 2). DynaMut2 accepts AlphaFold PDBs the same way.

### Step 6: Synthesis — decide the LoF mechanism category

Apply the upstream variant_lof_mechanism decision rule:

| Signal pattern | Inferred mechanism |
|---|---|
| ddG > +1 kcal/mol **AND** ΔlogP < 0 | **Structural stability LoF** — mutation destabilizes the fold; protein may misfold / be degraded. Drug rescue strategy: pharmacological chaperones, refolding agents. |
| ddG ≈ 0 (in [-0.5, +1]) **AND** SAE features lost are catalytic | **Direct catalytic LoF** — protein folds normally but the active site is broken. Strategy: substrate analog / cofactor supplementation. |
| ddG ≈ 0 **AND** SAE features lost are ligand-binding | **Binding LoF** — fold preserved, binding pocket disrupted. Strategy: small-molecule restoration. |
| ddG ≈ 0 **AND** SAE features lost are PTM | **PTM LoF** — regulatory site (phospho / glyco / ubiquitin) broken. Mechanism: dysregulation, not direct activity loss. |
| ddG ≈ 0 **AND** SAE features lost are domain / motif | **Interface LoF** — protein-protein interaction surface affected. Strategy: PPI restoration. |
| ddG > 0 + AlphaMissense pathogenic + ΔlogP < 0 but no clear SAE signal | **Generic damaging mutation** — clearly bad but mechanism unclear. Investigate via experimental assay. |

### Step 7: Honest evidence grading

Before reporting, score the synthesis:

| Confidence | Signal requirement |
|---|---|
| **High** | ≥4 signals point the same direction (e.g. AlphaMissense pathogenic + low ΔlogP + ddG > +1 + SAE feature loss) |
| **Medium** | 2-3 signals agree but 1+ are inconclusive |
| **Low** | Signals conflict (e.g. AlphaMissense pathogenic but SAE shows no specific category) — flag for experimental follow-up |

---

## Reporting format

```
Variant: {VARIANT_ID}  e.g.  P04637_R175H = TP53 R175H

EVIDENCE LAYERS
  1. AlphaMissense:   {score:.3f}  ({pathogenic|ambiguous|benign})
  2. AlphaFold pLDDT: {plddt:.1f}  ({well-folded|flexible|disordered})
  3. ESMC ΔlogP:      {dlogp:+.3f}  ({implausible|tolerated})
  4. SAE feature loss: top 3 features lost, dominant category = {category}
        Feature {f1.id}: Δ={f1.delta:+.3f}, category={cat1}
        Feature {f2.id}: Δ={f2.delta:+.3f}, category={cat2}
        Feature {f3.id}: Δ={f3.delta:+.3f}, category={cat3}
  5. DynaMut2 ΔΔG:    {ddg:+.2f} kcal/mol  ({destabilizing|neutral|stabilizing})

PROPOSED MECHANISM: {one of the 6 categories from Step 6}

SUPPORTING LOGIC: {one paragraph synthesizing the signals}

CONFIDENCE: {high|medium|low}

LIMITATIONS: {any signals that conflicted, missing data, low pLDDT, etc.}
```

---

## Honest limitations

1. **Missense only.** Indels, nonsense, splice variants need other workflows.
2. **Single-isoform.** Uses UniProt canonical. Variants in non-canonical isoforms may not apply.
3. **SAE labels are inferred, not curated.** `ESM_describe_sae_feature` labels are best-effort aggregations from a 10-protein panel; some features stay "uncategorized" with high activation values — flag this as low-confidence interpretation.
4. **DynaMut2 needs PDB.** If no PDB covers the mutation position and AlphaFold confidence is low (pLDDT < 50), the stability signal is unreliable.
5. **Long-range allosteric effects not captured.** SAE window is ±8 residues. Some mutations break protein function via distant effects (e.g., dimerization interface modulation) — SAE alone won't see this.
6. **Synthesis decision rule is heuristic.** The 6-category mapping in Step 6 — it's a reasonable starting point, not a clinical gold standard. For high-stakes interpretation, the rule should be treated as a hypothesis to be tested experimentally.
7. **Non-commercial license on SAE outputs** (per EvolutionaryScale Cambrian License).

---

## Optional: ThermoMPNN instead of DynaMut2 (advanced users with GPU)

DynaMut2 is the recommended default — it's already wired into TU via a hosted academic API (BioSig lab, UQ Australia) and requires zero extra setup. But if you need the higher accuracy of the newer ThermoMPNN model (Dieckhaus et al., PNAS 2024), here are your options:

### Local install (you have GPU + want full control)

```bash
git clone https://github.com/Kuhlman-Lab/ThermoMPNN.git
cd ThermoMPNN
# Install conda env from environment.yaml — note the GitHub README warns
# the .yaml may install CPU-only PyTorch by mistake; verify GPU PyTorch
conda env create -f environment.yaml
conda activate ThermoMPNN
# The checkpoint thermoMPNN_default.pt ships in models/
python custom_inference.py --pdb <your.pdb> --mutation <e.g. R175H>
```

Requirements: NVIDIA GPU with CUDA 11.8, ~15 min one-time setup.

License: **MIT** (no commercial restrictions).

Citation: Dieckhaus et al. (2024). *Transfer learning to leverage larger datasets for improved prediction of protein stability changes.* PNAS 121(6):e2314853121. doi:10.1073/pnas.2314853121.

### Hosted SaaS (no GPU, but registration + API key required)

Several commercial platforms host ThermoMPNN with free tiers (specific quota varies and is not always documented):

- [**Tamarind Bio**](https://www.tamarind.bio/tools/thermompnn) — REST API at `app.tamarind.bio/api/`, `x-api-key` auth
- [**Neurosnap**](https://neurosnap.ai/service/ThermoMPNN) — credit-based, HTTP API
- [**BioLM**](https://biolm.ai/models/thermompnn/) — `POST /api/v3/thermompnn/predict/`, Token auth
- [**ProteinIQ**](https://proteiniq.io/app/thermompnn) — web-first
- [**Levitate Bio**](https://support.levitate.bio/api/api-thermompnn/) — REST API

These are commercial SaaS — "free tier" usually means "try a few calls then pay". Not as clean as DynaMut2's purely academic endpoint, which is why TU defaults to DynaMut2.

### When ThermoMPNN actually matters over DynaMut2

For LoF mechanism classification (this skill's use case), the binary distinction `ddG > +1` vs `ddG ≈ 0` is what drives the synthesis. Both models give this signal correctly for clear-cut cases. ThermoMPNN's edge over DynaMut2:

- More accurate ΔΔG near the threshold (e.g., distinguishing +0.5 from +1.2 reliably)
- Handles double mutants (ThermoMPNN-D)
- Handles insertion/deletion variants (ThermoMPNN-I)

If your work depends on any of those three, switch to ThermoMPNN. Otherwise DynaMut2 is sufficient for the LoF mechanism decision in this skill.

