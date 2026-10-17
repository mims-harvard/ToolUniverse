---
name: tooluniverse-enzyme-design
description: De novo enzyme design by catalytic-motif scaffolding — build a transition-state motif, generate scaffolds with AlphaProtein Novo, fold every mechanistic state, and triage with mechanism-inspired filters (catalytic geometry, multi-state H-bonds, multi-resequence backbone scoring). Use for designing enzymes for a named reaction, scoring or filtering existing designs, or deciding which designs to order.
disable-model-invocation: true
---

# De Novo Enzyme Designer

Design enzymes for a named reaction by scaffolding a catalytic motif, then triage the output with filters derived from the reaction's mechanism. Built around AlphaProtein Novo (AP Novo), whose own finding is that **the filters, not the generator, decided success**.

**KEY PRINCIPLES**:
1. **Motif-first** — the input motif dominates the outcome more than any model choice
2. **Mechanism-inspired metrics** — catalytic geometry beats generic confidence
3. **Multi-state** — fold every state along the mechanism, require agreement across them
4. **Backbone quality is an ensemble property** — score a backbone by how many resequences of it pass
5. **Report the funnel, not the survivors** — know which filter killed what
6. **In-silico pass is not activity** — grade designs, never promise them
7. **English-first queries** — always use English terms in tool calls

De novo enzyme design starts with chemistry, not protein. You must be able to draw the transition state or a covalent intermediate as 3D coordinates — catalytic side-chain atoms plus ligand — before any model is useful. Everything downstream is scaffolding that geometry and then asking whether a predictor still believes it.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when the user asks to:
- Design an enzyme for a specific reaction or substrate
- Scaffold a catalytic motif / active site into a new protein
- Filter, score, rank or triage an existing set of enzyme designs
- Decide which designs are worth ordering, and why
- Optimize an already-active design (recycled scaffold / partial diffusion)

**Not this skill**: binder or interface design with no catalytic chemistry — use `tooluniverse-protein-therapeutic-design` or `tooluniverse-binder-discovery`. Structure prediction alone — use `tooluniverse-protein-structure-prediction`.

---

## What AP Novo is, exactly

A conditional joint sequence–structure diffusion model (147.5 M parameters, 32 blocks) that co-generates backbone coordinates and sequence, conditioned on a fixed catalytic motif and fixed ligand atoms. Because it co-generates sequence, the LigandMPNN resequencing step is **optional** rather than required.

Pipeline, four stages, each independently runnable:

| stage | script | what it does |
|---|---|---|
| generation | `run_generator.py` | motif + ligand → backbones + sequences |
| resequence | `run_ligandmpnn.py` | optional; LigandMPNN on the fixed backbone |
| folding | `run_alphafold.py` | AF3 / AF3-LA prediction, per state, per seed |
| evaluation | `evaluate_design.py` | metrics → `04_eval/*_evaluation.json` + `evaluation_summary.csv` |

`run_pipeline.py` runs all four from one **manifest** (JSON).

**In ToolUniverse the `apnovo` remote provider covers three of those four, not all of them.** It serves motif validation, generation and resequencing; it has **no folding operation**, because AlphaFold 3 weights carry terms separate from AP Novo's. That is not a gap you can route around inside the provider: upstream's evaluation refuses a campaign it finds no folding seed for, so `apnovo_evaluate_designs` also cannot run until the designs have been folded somewhere. Phase 5 below is therefore the step you have to arrange yourself — with a structure-prediction provider that has settled its own weights question — and Phases 6 and 7 depend on its output. `skills/setup-apnovo-remote-tool/SKILL.md` covers installation, weights and terms.

**Licence, before you design anything.** The AP Novo generator weights are available for **non-commercial use only** (universities, non-profits, research institutes, educational, journalism, government). Output carries the AP Novo Output Terms of Use and must keep its notice when distributed, and any publication must cite the paper. The prohibited-use policy forbids motifs, ligands or substrates derived from or targeting toxins, venoms, virulence factors, regulated pathogens, or chemical/biological weapons precursors, and forbids circumventing gene-synthesis screening. Read `src/tooluniverse/remote/apnovo/README.md` before a campaign, not after.

---

## Workflow Overview

```
Phase 1: Define the reaction and build the motif
  Mechanism -> transition state / intermediate -> 3D motif CIF + ligand

Phase 2: Validate the motif spec          <- do this BEFORE spending GPU
  motif_str parses, segments resolve, ligand chain present

Phase 3: Generate scaffolds
  1000 denoising steps, indexed or unindexed, N designs per motif

Phase 4: Resequence (optional)
  LigandMPNN T=0.1; or keep AP Novo's own sequence

Phase 5: Fold every mechanistic state
  apo + each intermediate, multiple seeds per state

Phase 6: Evaluate and filter             <- the funnel; report it
  generic metrics -> catalytic geometry -> multi-state agreement

Phase 7: Backbone-ensemble scoring (MR / MPD)
  the single highest-value filter in the paper

Phase 8: Triage, novelty check, report
```

---

## Phase 1 — Define the reaction and build the motif

You need, as 3D coordinates in one CIF: the catalytic side-chain atoms and the ligand representing a **transition state or covalent intermediate**, in the conformation you want the enzyme to hold.

Decide four things, each of which changes the manifest:

| decision | field | trade-off |
|---|---|---|
| Full residue vs tip atoms | `motif_atoms` | tip atoms ("atomic motif") let the model build the side chain; more freedom, less control |
| Indexed vs unindexed | `unindexed_motif_residues` | unindexed can find better placements in theory; **indexed works slightly better in practice** |
| Novel scaffold vs partial diffusion | `partial_diffusion_*` | partial diffusion diversifies a known-active parent |
| Total length | `seq_length` | campaign-dependent; see the table in `FILTERING.md` |

Sources for motif geometry, in order of preference: a crystal structure of a natural enzyme with the right machinery (search the PDB), a DFT-derived theozyme, or RDKit-generated ligand conformers placed against a natural triad. The published campaigns used all three.

**The motif is the dominant variable.** In one matched comparison, an Asp/Glu catalytic base gave a 37% hit rate (32/86) where a His base gave 10% (9/87) — same pipeline, same filters. If a campaign fails, re-examine the motif before re-tuning filters.

## Phase 2 — Validate the motif spec first

`motif_str` is the field that silently wastes GPU-days. Its grammar:

```
A1,5-10,A5-6,3/B1
└┬┘ └┬─┘ └─┬┘ │ └┬┘
 │   │     │  │  └── chain B residue 1: the ligand, fixed
 │   │     │  └───── 3 generated residues
 │   │     └──────── scaffold input chain A residues 5-6, fixed
 │   └────────────── 5 to 10 generated residues (sampled once per design)
 └────────────────── scaffold input chain A residue 1, fixed
```

`|` before the segment list randomises segment order: `"A1,A5-6|{},5-10,{},3/B1"`. `is_author_naming: true` means the numbers are the author numbering PyMOL and papers use; the PDB web viewer shows internal numbering instead.

Validate before generating — the `apnovo_validate_motif` operation parses the CIF and the motif string with upstream's own `MotifSpec` and reports the resolved segment lengths, which atoms are fixed, and the ligand chains. It needs no weights and no GPU. A malformed `motif_str` caught here costs seconds; caught in Phase 6 it costs the campaign.

## Phase 3 — Generate scaffolds

Defaults that matter: `num_sampling_steps: 1000` (the published campaigns' value; conclusions were checked to hold at 200), and `num_designs` per motif in the hundreds — the authors flag sampling cost as a real limitation, since many samples are needed per motif to find one that passes.

Length sampling, as published: intervening segments 2–80 residues and termini 10–100 (Kemp eliminase); intervening 2–70, termini 5–100, total restricted to 100–250 (serine esterase); designable segments 1–278 either side of a heme-ligating His, total 60–280 (nitrene transferase).

## Phase 4 — Resequence, or don't

`resequence.enabled: false` folds AP Novo's co-generated sequence directly. That is a legitimate choice: AP Novo sequences had similar in-silico pass rates and comparable measured activity to LigandMPNN sequences on two reactions. When used, LigandMPNN ran at temperature 0.1 with weights `v_32_030_25`, one sequence per design in the standard pipeline.

Requiring a design to pass filters under **both** sequence models is itself a filter: it raised retrospective hit rates 29%→45% (Kemp) and 5%→15% (serine esterase).

## Phase 5 — Fold every mechanistic state

Enumerate the states your mechanism passes through and fold each. For a serine hydrolase that is five: `apo`, `es` (Michaelis, non-covalent), `ti1` (first tetrahedral intermediate, covalent, sp³), `aei` (acyl-enzyme, covalent, sp²), `ti2` (second tetrahedral intermediate). Each state is a manifest entry naming its ligand and its protein–ligand bond.

Seeds: 7 per state (Kemp), 10 (serine esterase / DEHP). Each AF3 trunk seed internally samples 5 structures and returns the top-ranked, so one trunk seed yields one prediction.

**AF3 vs AF3-LA.** Stock AF3 mishandles leaving atoms, producing ~180° bond angles at Ser Oγ for covalent tetrahedral intermediates where ~109° is correct. AF3-LA is a fine-tune that fixes this and is what the serine esterase and DEHP campaigns used. If your mechanism has covalent intermediates, this matters; if it does not, stock AF3 was used for Kemp, carbene and nitrene round 1.

## Phase 6 — Evaluate and filter

See `FILTERING.md` for the metric namespace, the funnel implementation, and all five published threshold sets. The short version:

- metrics are named `<state>/<metric>/<seed_or_aggregate>`, plus `sampled/*` (diffusion output) and `sequence/*` (sequence sanity)
- filter on `seed_0` first, then on aggregates across seeds
- **report the cumulative funnel**, so it is visible which filter is doing the work

## Phase 7 — Backbone-ensemble scoring (MR / MPD)

This is the highest-value step in the published pipeline, and the most general idea in it.

**Multi-Resequence (MR)**: hold the backbone fixed, generate N sequences for it, and score the *backbone* by how many of them pass your filter set. 10 resequences, pass = 10/10 (serine esterase); 7, pass = 6/7 then 7/7 (Kemp).

**Multi-Partial-Diffusion (MPD)**: same idea one level out — re-noise the design by 575 of 1000 steps (≈88–90% sequence identity to the parent, ≈0.5 Å backbone RMSD), generate 10, require 9/10 to pass.

Measured effect — this is why it is Phase 7 and not an afterthought:

| filter | retrospective | prospective |
|---|---|---|
| MR, Kemp | ×2.5 at 50% recall | 23% hit rate, 2× |
| MR, serine esterase | ×5.4 at 50% recall | up to 44%, 30× |
| MR + MPD, both 10/10 | Kemp 60%, SE 80% | — |

Why it generalises: the MR pass rate estimates the *resequencer-accessible volume of functional sequence space* for that backbone. It needs no new reaction knowledge beyond the filter set you already wrote — which is also its limit: MR is not reaction-agnostic, because it depends on having reaction-specific metrics first.

## Phase 8 — Triage, novelty check, report

Before claiming novelty, check it. Define a natural-topology flag the way the authors did: TM-score > 0.45 **and** scaffold-aligned catalytic-triad RMSD < 5 Å to any annotated enzyme of the same class in the PDB. In the published serine esterases, 16.4% of designs met that definition — and **six of the top seven by catalytic efficiency** did. Report the best design and the best *non*-natural-topology design separately, as the paper does.

Report, per design: the metrics that passed, the metrics that failed, the funnel position, max TM-score and max sequence identity to anything natural, and an explicit statement that in-silico pass rate is a weak proxy for activity. See `CAVEATS.md`.

---

## Reference files

- `FILTERING.md` — metric namespace, funnel code, all five published threshold sets, how to build a set for a new reaction
- `CAVEATS.md` — what this pipeline does not do, the published failure modes, and the licence terms
