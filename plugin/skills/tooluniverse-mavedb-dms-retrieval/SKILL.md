---
name: tooluniverse-mavedb-dms-retrieval
description: "Fetch a deep mutational scanning (DMS) score set from MaveDB and normalize it into a (position × substitution) effect matrix. Use as the first step of any DMS analysis: SAE-vs-DMS comparison, hotspot detection, annotated heatmap plotting. Handles HGVS parsing, single-mutant filtering, canonical numbering pinning."
disable-model-invocation: true
---

# Retrieve DMS data from MaveDB

[MaveDB](https://www.mavedb.org) is the public repository of multiplexed
variant-effect assays (deep mutational scanning, MPRAs, etc.). This skill
orchestrates ToolUniverse's MaveDB tools to fetch a score set and reshape it
into the `(position × substitution)` effect matrix every downstream DMS skill
consumes.

**Provenance**: Workflow adapted from `dms_analysis/skills/retrieve_dms_data_mavedb.md`
in [ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka
Zitnik lab). ToolUniverse already provides the MaveDB API tools — this skill
is the orchestration + HGVS parsing + numbering step on top.

---

## When to use this skill

- You need a DMS effect matrix for a specific protein (e.g. KRAS, TP53, GFP)
- You want to compare model predictions (AlphaMissense, SAE drops, ESMC
  logits) against measured functional effects
- You need a benchmark dataset to validate a variant-interpretation method

**Not for**:
- Single-variant interpretation (use `tooluniverse-protein-sae-variant-interpretation`)
- Non-DMS variant-effect data (use `tooluniverse-variant-interpretation`)

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| Search query | gene symbol / protein name | `"KRAS"` or `"BRCA1"` |
| (optional) Specific assay type | e.g. abundance, binding, fitness | `"stability"` |
| (optional) Reference sequence | for numbering verification | UniProt sequence |

---

## ToolUniverse tools used

| Tool | Role |
|---|---|
| `MaveDB_search_score_sets` | find score sets by gene / keyword → URN list |
| `MaveDB_get_score_set` | score-set metadata: assay method, variant count, publication |
| `MaveDB_get_variant_scores` | the variant table: HGVS string + functional score |
| `MaveDB_search_experiments` | (optional) browse experiments grouping multiple score sets |
| `UniProt_get_sequence_by_accession` | canonical reference sequence for numbering check |

---

## Workflow (5 steps)

### Step 1: Find the score set

```python
MaveDB_search_score_sets(query="KRAS")
# Returns a list of score sets, each with a URN like "urn:mavedb:00000xxx-x-x"
```

Multiple score sets often exist per gene — different assays (stability vs
binding vs fitness), different conditions, different scoring conventions.
**Read the title and target description** to pick the right one. If unsure,
get full metadata before committing:

```python
MaveDB_get_score_set(urn="urn:mavedb:00000115-a-1")
# Returns: title, assay description, target sequence, variant count,
# publication, score range
```

### Step 2: Decide on the disruptive sign

DMS scores come with **different sign conventions**. Read the metadata to
decide which tail is "disruptive":

| Assay type | Disruptive tail | Why |
|---|---|---|
| Stability / abundance (ΔΔG) | top (positive = destabilizing) | Positive ΔΔG means less folded |
| Binding affinity score | bottom (low = weak binding) | Disrupting binding lowers the score |
| Fitness / growth | bottom (low = sick cell) | LoF variants reduce fitness |
| Variant abundance score | bottom (low = degraded) | LoF often destabilizes |

If the metadata is ambiguous, check the source publication. **A flipped sign
silently inverts every downstream conclusion** — never guess.

### Step 3: Pull the variants

```python
# Omit `limit` (or set limit=0) to receive ALL variants in one call.
# The MaveDB /scores endpoint returns the full CSV in a single HTTP request,
# so "unlimited" is the correct setting for whole-protein DMS analyses.
# (KRAS folding ΔΔG urn:mavedb:00000115-a-7 has ~3550 variants — all returned
# in one call once `limit` is omitted.)
MaveDB_get_variant_scores(urn="urn:mavedb:00000115-a-1")
# Returns:
#   {data: {urn, total_variants_in_set, returned, truncated, limit_applied,
#           hgvs_filter, variants: [{hgvs_pro: "p.Arg175His", score: -2.34, ...}, ...]}}
# Set limit=N (positive integer) only if you genuinely want to truncate for a
# preview; otherwise leave it unset.
```

### Step 4: Parse HGVS to (position, ref_aa, alt_aa) and filter

Variants come as HGVS protein strings. Parse them and **keep single missense
variants only** for the downstream tensor-building skill:

```python
import re

THREE_TO_ONE = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
}

SINGLE_MISSENSE_RE = re.compile(r"^p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})$")

def parse_hgvs(hgvs):
    m = SINGLE_MISSENSE_RE.match(hgvs)
    if not m:
        return None  # drop synonymous, nonsense, indels, multi-mutants
    ref3, pos, alt3 = m.group(1), int(m.group(2)), m.group(3)
    if ref3 not in THREE_TO_ONE or alt3 not in THREE_TO_ONE:
        return None
    return THREE_TO_ONE[ref3], pos, THREE_TO_ONE[alt3]

parsed = []
for row in variants:
    res = parse_hgvs(row["hgvs_pro"])
    if res is None:
        continue
    ref_aa, pos, alt_aa = res
    parsed.append({"position": pos, "ref_aa": ref_aa, "alt_aa": alt_aa, "score": row["score"]})
```

Drop synonymous (`p.Arg175=`), nonsense (`p.Arg175*`), indels (`p.Arg175del`),
and multi-mutant rows.

### Step 5: Verify numbering against canonical

MaveDB targets carry their own coordinate system, which may not equal the
canonical UniProt sequence. **Always verify before joining to any other source**:

```python
ref_sequence = UniProt_get_sequence_by_accession(accession="P01116")["sequence"]

# Pick the most-mutated position as a landmark
position_counts = Counter(p["position"] for p in parsed)
landmark = position_counts.most_common(1)[0][0]
landmark_ref_aa = next(p["ref_aa"] for p in parsed if p["position"] == landmark)

if ref_sequence[landmark - 1] != landmark_ref_aa:
    raise ValueError(
        f"MaveDB position {landmark} has ref_aa={landmark_ref_aa} but "
        f"UniProt position {landmark} is {ref_sequence[landmark - 1]}. "
        f"There is a numbering offset — resolve before continuing."
    )
```

If the offset is non-zero (e.g. +4 for an N-terminal tag), apply it
explicitly: `canonical_pos = mavedb_pos + offset`. **Never silently rebase.**

### Step 6: Emit the effect matrix

Reshape into the `(20 amino acids × n_positions)` layout the downstream
skills expect:

```python
import numpy as np

AAS = "ACDEFGHIKLMNPQRSTVWY"
positions = sorted({p["position"] for p in parsed})
pos_index = {p: i for i, p in enumerate(positions)}
aa_index = {a: i for i, a in enumerate(AAS)}

matrix = np.full((20, len(positions)), np.nan)
for row in parsed:
    if row["alt_aa"] not in aa_index:
        continue  # selenocys, pyrrolys, etc. — drop
    matrix[aa_index[row["alt_aa"]], pos_index[row["position"]]] = row["score"]
```

---

## Output

A NumPy array `(20, n_positions)` of functional scores, plus a metadata dict:

```python
{
    "matrix": matrix,  # (20, n_positions), np.nan for unmeasured
    "amino_acid_order": AAS,
    "positions": positions,  # 1-based canonical residue numbers
    "urn": "urn:mavedb:00000115-a-1",
    "assay_type": "fitness",
    "disruptive_tail": "bottom",  # from step 2
    "n_variants_kept": len(parsed),
    "n_variants_dropped": n_total - len(parsed),
    "numbering_offset": 0,
}
```

---

## Honest limitations

1. **Score semantics vary**. The disruptive tail decision is per-score-set —
   getting it wrong inverts every downstream result.
2. **Coverage is partial**. Most score sets do not measure all 20
   substitutions at every position. Treat missing cells as `NaN`, not 0 —
   averaging with implicit zeros biases the analysis.
3. **Multi-mutant rows are dropped**. Many score sets include double or
   higher-order mutants; the SAE-vs-DMS skills here assume single
   substitutions. If you need multi-mutant analysis, extend the tensor
   layout deliberately.
4. **Numbering offsets are silent**. Always verify with a landmark; the
   skill cannot detect offsets for you.
5. **One assay at a time**. To compare across assays of the same gene
   (e.g. KRAS folding × KRAS binding), retrieve each independently and
   align them at the analysis stage — not by averaging.

---

## Cross-references

| Skill | Why |
|---|---|
| `tooluniverse-variant-predictor-dms-benchmarking` | Next: validate a variant-effect predictor (SAE / AlphaMissense / EVE / etc.) against this DMS data |
| `tooluniverse-residue-functional-mechanism-interpretation` | Next: pick the top hotspots from this DMS and explain why each is functionally critical |
| (visualization is Step 7 of `tooluniverse-residue-functional-mechanism-interpretation`) | Annotated DMS heatmap with hotspot callouts |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/retrieve_dms_data_mavedb.md`
MaveDB: https://www.mavedb.org (Esposito et al., *Genome Biology* 2019)
