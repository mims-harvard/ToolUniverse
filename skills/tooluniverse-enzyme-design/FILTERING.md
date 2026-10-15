# Filtering enzyme designs

The machinery here is reaction-agnostic; only the threshold sets are reaction-specific. That split is the point — to design for a new reaction you write a new threshold dict, not new code.

## The metric namespace

`evaluate_design.py` writes one `04_eval/<design>_evaluation.json` per design and an `evaluation_summary.csv` whose columns are the **union of all scalar metrics seen** — so never hard-code the column list. Keys are hierarchical:

| pattern | means |
|---|---|
| `sampled/<metric>` | measured on the diffusion output; cannot be used for self-consistency |
| `sequence/<metric>` | sequence sanity, no structure involved |
| `<state>/<metric>/seed_N` | one folded state, one trunk seed |
| `<state>/<metric>/{mean,median,max,min}` | aggregated across that state's seeds |
| `<cross-state metric>` | spans states, e.g. `es_ti1_min_cross_state_rmsd` |

State names are whatever the manifest's `folding.states` declares. The published serine-hydrolase campaigns use `apo`/`es`/`ti1`/`aei`/`ti2`; the released example manifests use `monomer`/`complex` for the same roles, so **a threshold set is only valid for the state names it was written against**.

### Generic metrics worth knowing

*Self-consistency* (prediction vs diffusion output):
- `rmsd` — all protein Cα
- `tm_score` — global, length-normalised
- `motif_allatom_rmsd` — all-atom, prediction vs **input motif**
- `motif_bb_aligned_allatom_rmsd` — same, after aligning on motif backbone N/Cα/C
- `fixed_res_bb_aligned_allatom_sc_rmsd` — backbone-aligned all-atom, residues carrying a motif atom
- `mean_pocket_bb_aligned_ligand_rmsd` — ligand heavy atoms, superimposed on backbone within 10 Å of the ligand
- `mean_pocket_bb_rmsd` — that pocket backbone itself

*Confidence*: `protein_plddt_mean`, `ligand_plddt_mean`, `predicted_distance_error` (PDE over all atoms), `chain_pair_pde_mean_sym` (symmetrised inter-chain PDE), `interface_lddt` (between atoms not on the same chain).

*Sterics*: `percent_ligand_bb_clashes_1_5` — ligand atoms within 1.5 Å of any protein backbone atom.

*Topology*: `sampled/topology_string_len` — count of secondary-structure elements (3 = three-helical bundle).

*Sequence*: `seq_len`, `max_single_aatype_frac`, `max_consecutive_identical_aatypes`, `unknown_count`, and `num_blocklisted_motifs` — matches against purification/epitope tags (Strep WSHPQFEK, c-Myc EQKLISEEDL, TEV ENLYFQ[SGAMCH], 3C LEVLFQGP, HA YPYDVPDYA, His HHHHH, FLAG DYKDDDDK, V5 GKPIPNPLLGLDST, thrombin LVPRGS).

**Not used anywhere in the published filters**: pTM, ipTM, PAE, radius of gyration. They appear in AF3's output JSON but no campaign filtered on them.

## The funnel

Three comparators cover every published filter: `>=`, `<=`, and a closed range. What makes this useful rather than a one-line mask is the **cumulative** view: applying filters in order and recording how many survive each step tells you which filter is doing the work and which is dead weight.

```python
import enum, json, pandas as pd
from pathlib import Path

class C(enum.Enum):
    GE = ">="
    LE = "<="
    RANGE = "within_range"

def _mask(series, comparator, value):
    if comparator is C.GE:
        return series >= value
    if comparator is C.LE:
        return series <= value
    low, high = value
    return series.between(low, high)

def load_eval(eval_dir):
    """One row per design from 04_eval/*_evaluation.json."""
    rows = []
    for path in sorted(Path(eval_dir).glob("*_evaluation.json")):
        d = json.loads(path.read_text())
        rows.append({"sample_name": d["sample_name"], "spec_name": d["spec_name"],
                     "designed_cif": d.get("designed_cif"), **d["metrics"]})
    return pd.DataFrame(rows)

def funnel(df, thresholds):
    """Per-metric and cumulative pass counts, in the order given."""
    missing = [m for m in thresholds if m not in df.columns]
    if missing:
        raise KeyError(f"metrics absent from this campaign: {missing}")
    masks = pd.DataFrame({m: _mask(df[m], c, v) for m, (c, v) in thresholds.items()})
    cumulative = masks.cumprod(axis=1).astype(bool)
    return pd.DataFrame({
        "metric": list(thresholds),
        "comparator": [c.value for c, _ in thresholds.values()],
        "threshold": [v for _, v in thresholds.values()],
        "pass_rate": masks.mean().values,
        "cumulative_pass": cumulative.sum().values,
    }), masks.all(axis=1)
```

Raise on a missing metric rather than dropping it — a threshold silently skipped because the state was never folded is how a design set looks better than it is.

## Published threshold sets

**Two sources, different numbers; do not merge them.**

- **Campaign thresholds** (paper SI tables S7/S8/S10/S11/S12) are what produced the reported hit rates.
- **Demo thresholds** (the repo's `examples/filter_designs.ipynb`) accompany example manifests that run with reduced sampling, and are correspondingly looser. Where they disagree the campaign values are the ones with wet-lab evidence behind them — e.g. `mean_pocket_bb_aligned_ligand_rmsd` is `<= 2` in Table S8 and `<= 10.0` in the notebook, and `ligand_ca_neighbors_min` is `<= 18` vs `<= 21`.

### Kemp eliminase — campaign, rounds 5–7 (Table S8)

Reaction-specific metrics: `ligand_ca_neighbors_{min,mean}` (per ligand atom, count protein Cα within 6/8/12 Å and average the three; require a high mean for packing and a low min to keep an opening), `cat_base_tip_ca_neighbors_mean` (burial of the catalytic base), `protein_ligand_ipde_mean`, `acid_base/distance` (base's abstracting atom → substrate heavy atom bearing the proton), `oxyanion_oah/distance`, `base_dyad/distance`, and `dihedral2` out-of-plane angles relative to the substrate ring plane.

| metric | threshold | aggregation |
|---|---|---|
| `sampled/ligand_ca_neighbors_min` | ≤ 18 | — |
| `sampled/ligand_ca_neighbors_mean` | ≥ 18 | — |
| `sampled/cat_base_tip_ca_neighbors_mean` | ≥ 15 | — |
| `apo/tm_score` | ≥ 80 | median (and seed_0) |
| `apo/motif_bb_aligned_allatom_rmsd` | ≤ 1 | median |
| `complex/tm_score` | ≥ 80 | median |
| `complex/mean_pocket_bb_aligned_ligand_rmsd` | ≤ 2 | median |
| `complex/protein_ligand_ipde_mean` | ≤ 1.9 | median |
| `complex/acid_base/distance` | ≤ 3.7 Å | mean of 7 |
| `complex/oxyanion_oah/distance` | ≤ 3.7 Å | mean of 7 |
| `complex/base_dyad/distance` | ≤ 3.7 Å | mean of 7 |
| `complex/acid_base/dihedral2` | 150–210° | mean of 7 |
| `complex/oxyanion_oah/dihedral2` | 150–210° | mean of 7 |
| `complex/base_dyad/dihedral1` | 150–210° | mean of 7 |

Rounds 3–4 used the first eight rows only, with `complex/mean_pocket_bb_aligned_ligand_rmsd ≤ 2` and `protein_ligand_ipde_mean ≤ 1.9`. Adding the geometry rows tripled the prospective hit rate and moved best kobs 0.49 → 1.38 s⁻¹.

### Serine esterase / DEHPase — campaign base set (Table S10)

| metric | threshold |
|---|---|
| `apo/rmsd` | ≤ 1.5 |
| `apo/protein_plddt_mean` | ≥ 75 |
| `apo/motif_allatom_rmsd` | ≤ 1.5 |
| `apo/tm_score` | ≥ 80 |
| `apo/predicted_distance_error` | ≤ 2.0 |
| `ti1/interface_lddt` | ≥ 50 |
| `ti1/ligand_plddt_mean` | ≥ 80 |
| `ti1/fixed_res_bb_aligned_allatom_sc_rmsd` | ≤ 3.0 |
| `ti1/motif_allatom_rmsd` | ≤ 1.5 |
| `ti1/chain_pair_pde_mean_sym` | ≤ 2.0 |
| `ti1/mean_pocket_bb_aligned_ligand_rmsd` | ≤ 5 |
| `ti1/mean_pocket_bb_rmsd` | ≤ 2.0 |
| `ti1/num_missing_atoms` | = 0 |
| `sampled/topology_string_len` | ≥ 3 |
| `num_missing_motif_residues` | = 0 |
| `max_single_aatype_frac` | ≤ 0.25 |
| `max_consecutive_identical_aatypes` | ≤ 5 |
| `num_blocklisted_motifs` | = 0 |

Plus H-bond requirements in **every** state (see below), plus substrate-specific ligand-confidence floors: `ti1/ligand_plddt_mean/max ≥ 90.4` (4MU-Ac); `ti1 ≥ 85` and `{aei,ti2} ≥ 88` (DEHP).

**The H-bond criterion** — a geometric test, satisfied if **at least 1 of 10 seeded predictions** passes: donor–acceptor distance 2.0–3.6 Å; both angles 80–160° (sp² query atom) or 69.5–149.5° (sp³ middle atom); dihedrals 130–230° (and in some cases −50 to 50°) for sp², unconstrained otherwise. A *forward* H-bond (`hbond_fwd_*`) checks angle and dihedral around the first atom only. Six interactions are scored: `his_nuc`, `his_acid`, `oah1_oa`, `oah1_ester`, `oah2_oa`, `oah2_ester`.

Required: `hbond_fwd_his_nuc > 0` and `hbond_his_acid > 0` in all of `{apo, es, ti1, aei, ti2}`; oxyanion-hole H-bonds in `{ti1, aei}`; and in `ti2` — the authors note this filtered OAH→ester rather than OAH→oxyanion as intended, and was kept because it worked.

**Cross-state agreement**, the metric highlighted in the main text: `es_ti1_min_cross_state_rmsd` = minimum pocket-aligned ligand RMSD over all 10×10 ES/TI1 prediction pairs — `≤ 5` in round 7, tightened to **`≤ 1.0`** in round 8; with `es_ti1_cross_seed_ligand_coord_std ≤ 4.0`. Retrospective correlation with activity is real but modest (Spearman ρ = −0.19).

### Carbene transferase (Table S11)

`alanine_ratio < 0.225`; `apo/tm_score > 80`; `apo/rmsd < 3`; `apo/lddt > 80`; `complex/mean_pocket_bb_aligned_ligand_rmsd ≤ 2.25`; `complex/mean_pocket_bb_rmsd ≤ 1.1`; `complex/predicted_distance_error ≤ 1.5`; `complex/interface_lddt > 70`; `complex/gdt_ha > 60`; `transition_state_rmsd ≤ 2.25` (self-consistency on the transition state alone, heme excluded); `heme_rmsd ≤ 2.25`.

### Nitrene transferase (Table S12)

`seq_len ≥ 90`; `max_consecutive_identical_aatypes ≤ 5`; `max_single_aatype_frac ≤ 0.25`; `num_blocklisted_motifs = 0`; `sampled/percent_ligand_bb_clashes ≤ 5.0`; `sampled_his_rmsd ≤ 0.04` (relaxed to 0.08 in round 2); `n_self_rmsd ≤ 0.8`; `pocket_C9_min_atom_dist` 2.8–3.8; `pocket_C9_allatom_neighbors_mean` 38–62; `propionate_hbond_num_atoms` 3–6; `propionate_hbond_num_res` 3–5; `his_heme_dist ≤ 3.0`; `piperidine_propensity ≤ 0.35` (one facet only); `apo/tm_score ≥ 80`; `apo/predicted_distance_error ≤ 2.0`; `complex/ligand_plddt_mean ≥ 75`; `complex/interface_lddt ≥ 30`; `complex/mean_pocket_bb_aligned_ligand_rmsd ≤ 2.5`; `complex/mean_pocket_bb_rmsd ≤ 2.0`; `complex/chain_pair_pde_mean_sym ≤ 2.0`.

Here `fe_self_rmsd` / `n_self_rmsd` are agreement of the heme iron / ligating nitrogen across **five different ligand-state representations**, and `piperidine_propensity` is the C5–N minus C4–N distance difference — negative favours the six-membered product. That last one is the clearest example of a filter that encodes the selectivity you are designing for.

## Building a set for a new reaction

The five sets above differ in their reaction-specific rows and agree almost entirely in their generic rows. So:

1. **Start from the generic spine** — self-consistency (`tm_score ≥ 80`, motif RMSD ≤ 1–1.5 Å), confidence (`protein_plddt_mean ≥ 75`, `predicted_distance_error ≤ 2`), ligand placement (`mean_pocket_bb_aligned_ligand_rmsd`, `ligand_plddt_mean`), sterics, sequence sanity, `topology_string_len ≥ 3`.
2. **Enumerate your mechanism's states** and require the catalytic interactions to be geometrically satisfiable in **each** of them. A triad that only forms in one state is not a triad.
3. **Write one distance and one angle per catalytic interaction.** Every campaign reduced to this: donor–acceptor distances ≤ ~3.7 Å and out-of-plane angles near 180° relative to the reacting plane.
4. **Add one selectivity metric if selectivity is the goal** — a near-attack geometric difference between the two outcomes, as `piperidine_propensity` is.
5. **Filter on `seed_0` first, then aggregates.** Cheaper, and it is what the campaigns did.
6. **Then add MR** (see Phase 7 of `SKILL.md`), which needs no further reaction knowledge and was worth more than any single metric above.

Tighten until roughly tens of designs pass, not units: precision keeps rising as filters tighten — up to 100% when fewer than five designs pass — but you lose the diversity that makes a campaign informative. Hit rate and best-activity are maximised by *different* settings; for the serine esterases the best hit-rate filter was MR 10/10 + MPD 10/10 while the best kobs came from MR 10/10 + MPD ≥ 6/10.
