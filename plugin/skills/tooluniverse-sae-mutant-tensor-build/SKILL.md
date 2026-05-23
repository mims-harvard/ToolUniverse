---
name: tooluniverse-sae-mutant-tensor-build
description: "Compute ESM-C 6B Sparse Autoencoder (SAE) features for every single mutant in a deep mutational scanning library and assemble them into a (20 amino acids × n_positions × 16384 features) tensor aligned to the DMS layout, plus the wild-type reference vector. This tensor is the input every downstream SAE-vs-DMS skill consumes."
disable-model-invocation: true
---

# Build a per-mutant ESM-C SAE tensor

For any protein with a deep-mutational-scanning (DMS) library, compute ESM
Cambrian SAE features for every single amino-acid substitution and assemble
them into one tensor aligned to the DMS layout. Output feeds the
`tooluniverse-sae-dms-global-validation` and
`tooluniverse-sae-dms-hotspot-features` skills.

**Provenance**: Workflow adapted from `dms_analysis/skills/build_per_mutant_sae_tensor.md`
and reference scripts `01_compute_sae_features.py` + `02_export_sae_tensors.py`
in [ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka
Zitnik lab).

---

## When to use this skill

- You have a DMS effect matrix (from `tooluniverse-mavedb-dms-retrieval` or
  a local source) and want to compute SAE features for every variant
- You're preparing inputs for SAE-vs-DMS statistical tests or per-position
  hotspot enrichment

**Not for**:
- Single-variant analysis — use `tooluniverse-protein-sae-variant-interpretation`
- Per-residue feature inspection at a known mutation site only — use
  `ESM_get_sae_features` directly

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| Wild-type sequence | string, 1-based | KRAS canonical 188 AA |
| List of single mutants | `[(position, ref_aa, alt_aa), ...]` | From the DMS retrieval skill |
| ESM_API_KEY | env var | EvolutionaryScale Forge token |

---

## Prerequisites

```bash
pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'
export ESM_API_KEY=<your-forge-token>
```

The PyPI release of `esm` does NOT include SAEConfig — install from the
upstream feature branch. See `tooluniverse-protein-sae-variant-interpretation`
for the full prerequisites.

---

## ToolUniverse tools used

| Tool | Role |
|---|---|
| `ESM_get_sae_features` | atomic SAE feature extraction per residue (called once per mutant + once for WT) |

---

## Workflow

### Step 1: Verify the WT sequence

```python
ref_seq = wild_type_sequence  # from the user or UniProt_get_sequence_by_accession

# Spot-check at known landmarks
for pos, ref_aa, _ in mutants[:5]:
    if ref_seq[pos - 1] != ref_aa:
        raise ValueError(f"WT mismatch at position {pos}: seq has {ref_seq[pos-1]}, mutant ref is {ref_aa}")
```

### Step 2: Build mutant sequences in a recorded order

The order in which mutants are sent and reassembled **must match exactly** —
this ordering is the contract between the API call and the tensor reshape.

```python
import numpy as np

AAS = "ACDEFGHIKLMNPQRSTVWY"

mutant_inputs = []   # list of (allele_idx, pos_idx, sequence)
positions = sorted({p for p, _, _ in mutants})
pos_index = {p: i for i, p in enumerate(positions)}
aa_index = {a: i for i, a in enumerate(AAS)}

for pos, ref_aa, alt_aa in mutants:
    if alt_aa not in aa_index:
        continue  # selenocys / non-standard
    if pos not in pos_index:
        continue
    mut_seq = ref_seq[:pos - 1] + alt_aa + ref_seq[pos:]
    mutant_inputs.append((aa_index[alt_aa], pos_index[pos], mut_seq))
```

### Step 3: Run the SAE for WT first, then every mutant

The atomic tool returns per-residue features in a window. For library-scale
analysis use a **window that spans the whole sequence** — set `window` to the
sequence length to get all residues, then mean-pool to a single per-sequence
vector. (Per-residue features for a whole library are ~100× larger and not
needed for per-variant analyses.)

```python
def get_pooled_features(sequence, sae_model="esmc-6b-2024-12_k64_codebook16384_layer60"):
    """Run SAE on the full sequence and mean-pool to a (16384,) vector."""
    result = ESM_get_sae_features(
        sequence=sequence,
        position=len(sequence) // 2,   # window center
        window=len(sequence),          # cover everything
        sae_model=sae_model,
        top_k_per_residue=64,
    )
    if result.get("status") != "success":
        raise RuntimeError(result.get("error"))
    # Sum activations per feature across all residues, then divide by L
    activations = result["data"]["activations"]
    pooled = np.zeros(16384, dtype=np.float32)
    for residue in activations:
        for feat in residue["active_features"]:
            pooled[feat["feature_id"]] += feat["activation"]
    pooled /= len(activations) if activations else 1
    return pooled

# WT once
wt_pooled = get_pooled_features(ref_seq)
np.save("wt_sae_vector.npy", wt_pooled)

# Then every mutant — cache aggressively, this is the bulk of API cost
import json, hashlib
from pathlib import Path
cache_dir = Path.home() / ".cache/tooluniverse/sae_dms_tensor"
cache_dir.mkdir(parents=True, exist_ok=True)

def cached_features(seq):
    key = hashlib.sha1(seq.encode()).hexdigest()[:16]
    cf = cache_dir / f"{key}.npy"
    if cf.exists():
        return np.load(cf)
    arr = get_pooled_features(seq)
    np.save(cf, arr)
    return arr
```

### Step 4: Assemble the tensor

```python
T = np.full((20, len(positions), 16384), np.nan, dtype=np.float32)

for aa_idx, pos_idx, mut_seq in mutant_inputs:
    T[aa_idx, pos_idx] = cached_features(mut_seq)

np.save("sae_tensor.npy", T)

# Difference tensor (mutant − WT) — some downstream skills want this directly
diff = T - wt_pooled[None, None, :]
np.save("sae_tensor_diff.npy", diff)
```

### Step 5: Set WT-diagonal cells to NaN

Cells where `mutant_aa == wild_type_aa[position]` are layout placeholders,
not real mutants. Mark them explicitly:

```python
for pos in positions:
    wt_aa = ref_seq[pos - 1]
    if wt_aa in aa_index:
        T[aa_index[wt_aa], pos_index[pos]] = np.nan
        diff[aa_index[wt_aa], pos_index[pos]] = np.nan
```

### Step 6: Record metadata

```python
import json
meta = {
    "amino_acid_order": AAS,
    "positions": positions,
    "shape": list(T.shape),
    "wt_diagonal_convention": "NaN",
    "sae_model": "esmc-6b-2024-12_k64_codebook16384_layer60",
    "pooling": "mean over residues",
    "n_mutants_computed": len(mutant_inputs),
}
with open("sae_tensor_meta.json", "w") as f:
    json.dump(meta, f, indent=2)
```

---

## Verification before trusting the tensor

Run these checks before using the tensor in any downstream test:

1. **Known benign mutation → near-zero diff**. Pick a synonymous-equivalent
   conservative substitution (e.g. Leu→Ile in a non-functional position);
   `||diff[L→I, pos]|| / ||wt||` should be tiny (<0.01).
2. **Known disruptive mutation → large diff**. Pick a known LoF variant
   (e.g. KRAS G12V); `||diff[G→V, 12]||` should be substantially larger.
3. **Every WT-diagonal cell is NaN**. `np.all(np.isnan(T[aa_index[ref_seq[p-1]], pos_index[p]])) for p in positions`.
4. **WT vector norm is reproducible**. Rerun WT extraction; norm should match.

---

## Honest limitations

1. **API cost scales linearly with library size**. KRAS DMS at 168 positions
   × 19 substitutions = 3,192 mutants = 3,193 API calls. Cache aggressively;
   the step is resumable if the cache directory persists.
2. **Pooled features lose positional information**. The pooling step is the
   right summary for whole-library statistics, but it means you cannot read
   "feature X activated at position Y" from this tensor. For position-resolved
   analysis use `tooluniverse-sae-dms-hotspot-features` (which uses per-residue
   features) or directly call `ESM_get_sae_features` per variant.
3. **Row-ordering bugs are silent**. An accidental `drop_duplicates` or sort
   between API call and reshape scrambles positions with no error. Always
   verify with a landmark (e.g. a known LoF mutant should appear at the
   expected `[aa_idx, pos_idx]` cell with a large diff norm).
4. **Sequence length cap**. The atomic `ESM_get_sae_features` tool caps
   sequences at 2700 residues — proteins longer than this need to be processed
   in domain-sized chunks (and the pooling no longer applies cleanly).
5. **License**: SAE outputs from Forge are governed by the [Cambrian Inference
   Clickthrough License](https://www.evolutionaryscale.ai/policies/cambrian-inference-clickthrough-license-agreement)
   — non-commercial / academic use only.

---

## Cross-references

| Skill / Tool | Why |
|---|---|
| `tooluniverse-mavedb-dms-retrieval` | Upstream: get the mutant list |
| `ESM_get_sae_features` | The atomic call this skill orchestrates |
| `tooluniverse-sae-dms-global-validation` | Downstream consumer 1 |
| `tooluniverse-sae-dms-hotspot-features` | Downstream consumer 2 |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/build_per_mutant_sae_tensor.md`
Reference scripts: `dms_analysis/scripts/01_compute_sae_features.py`, `02_export_sae_tensors.py`
