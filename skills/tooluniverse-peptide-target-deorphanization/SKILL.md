---
name: tooluniverse-peptide-target-deorphanization
description: Find the real protein target(s) of a peptide from its sequence — peptide target deorphanization / off-target identification, for ANY target class (GPCR, ion channel, protease, cytokine/growth-factor receptor, enzyme, integrin), not only GPCRs. Use when a peptide has a phenotype but does not bind its hypothesized target, when a peptide binds a target in one species or assay but not another, or to screen candidate targets for an orphan peptide. A target-class router steers a multi-route keyless pipeline (PROSITE/ELM motif, BLAST homology, HGNC/InterPro/GPCRdb/GtoPdb target-family enumeration, OpenTargets phenotype anchor, EnsemblCompara/Alliance cross-species reconciliation) plus optional NVIDIA-NIM co-folding (Boltz2, AlphaFold2-Multimer, OpenFold3) for structural confirmation.
disable-model-invocation: true
---

# Peptide Target Deorphanization

Deorphanize a peptide: given a peptide **sequence** plus an **observed phenotype** (and often a *hypothesized* target the peptide does NOT actually bind), find its likely real protein target(s) — using ToolUniverse's keyless characterization, homology, target-family, phenotype, cross-species, and (optional, key-gated) co-folding tools.

**The target can be anything, not just a GPCR.** A *target-class router* (GPCR ligand / ion-channel toxin / protease target / cytokine or growth-factor receptor / integrin ligand / antimicrobial / unknown) classifies the peptide up front and adapts the enumeration strategy. GPCRs are the best-trodden case (and the validated control), but the pipeline's spine — homology, motif, phenotype, cross-species, co-fold — is target-class-agnostic, and family enumeration uses **HGNC gene-family (general) + InterPro (general) + GPCRdb (GPCR-only cross-check)**.

## Core reasoning: LOOK UP, DON'T GUESS

The failure mode this skill defends against is **guessing a target from the peptide's name or its assumed mechanism**. A peptide can be **phenotypically active yet not bind the hypothesized target** — because it hits a *paralog*, a *different family member*, or the *same receptor in a different species* whose binding interface has diverged. So:

1. **Never assert a target from memory.** Every candidate must come from a tool result (homology hit, family enumeration, phenotype association, or structural co-fold), with the tool name and accession recorded.
2. **Anchor on PHENOTYPE × STRUCTURE/SEQUENCE plausibility, not on the peptide's reputed mechanism.** The real target is the intersection of (a) what the *sequence/motif/structure* says it could bind and (b) what the *phenotype* says is biologically relevant. A name-level guess ("it's a GLP-1 analog so it's GLP1R") is exactly what produces off-target errors.
3. **Reconcile across species.** "Binds in species A but not B" is usually **interface sequence divergence**, not a different target. Always pull the ortholog set and align the candidate receptor's ligand-binding interface across the assay species before concluding the peptide "doesn't work."
4. **A non-binding result against the hypothesized target is a clue, not a dead end.** It promotes the *paralogs* and *phenotype-shared* receptors to the top of the candidate list.

This skill is built on **validated, mostly keyless tools** (BLAST, ELM/PROSITE, GPCRdb/HGNC/GtoPdb, OpenTargets, EnsemblCompara/Alliance). The single key-gated step is the **optional structural confirmation by co-folding** (NVIDIA NIM), used only to rank an already-narrowed shortlist.

---

## Automated pipeline (scripts) — the fast path

Two runnable scripts in `scripts/` execute the whole pipeline so you don't have to chain the phase calls by hand. Both load ToolUniverse via the SDK and run from the repo root.

### `deorphanize_peptide.py` — keyless candidate generation + ranking (Phases 1–4)

No API key. For each peptide it characterizes it (PepCalc/ProtParam), flags **non-canonical/cyclic** residues, scans **PROSITE + ELM** signatures, flags **protease/degradation liability**, **classifies the target class** (GPCR / channel / protease / cytokine-receptor / integrin / …) and enumerates the candidate **target family** accordingly, anchors on **phenotype** (OpenTargets), and — for the top candidates — **resolves the ortholog protein sequences and aligns the binding interface across human / assay-species / source-species** (the mechanistic "binds in A, not B" step) and **suggests a ClusPro-ready PDB** structure. Prints a ranked candidate shortlist with evidence tiers.

```bash
python3 scripts/deorphanize_peptide.py \
  --sequence <PEPTIDE_SEQ> \             # OR  --fasta peptides.fasta  for BATCH mode
  --hypothesized-target <GENE> \         # optional; seeds family enumeration (e.g. GLP1R). OMIT for SEEDLESS mode
  --phenotype "<disease name>" \         # optional, REPEATABLE; OpenTargets anchor (use the DISEASE node, not a symptom) — pass several to union plausible phenotypes
  --assay-species mus_musculus \         # species of the NEGATIVE binding assay
  --source-species <organism> \          # optional; species where binding WAS observed -> 3-way interface alignment
  [--no-blast] [--out result.json]
```

**Modes:**
- **Seeded** (`--hypothesized-target GLP1R`) — enumerate that gene's family as the candidate panel (cleanest). **Even seeded, the sequence-derived candidates (below) are always unioned in**, so a *wrong* hypothesized seed cannot blind the search to the real target's family — exactly the deorphanization premise.
- **Seedless** (omit it) — derive candidate targets from PROSITE **and BLAST-homolog** keywords × the **target-class nouns** (e.g. `receptor`/`channel`/`protease`, chosen by the router) via UniProt; degrades to phenotype-only if that resolver is transiently down. No longer receptor-only.
- **Multi-phenotype** — `--phenotype` is repeatable; pass every plausible disease and the anchor is the **union** (max score per target). Best when you don't know the single right phenotype.
- **Batch** (`--fasta`) — one record per FASTA entry, sharing `--phenotype`/`--assay-species`.

**Extra signals it always reports:**
- **Target class** — the router's call (gpcr_ligand / ion_channel_toxin / protease_inhibitor_or_substrate / cytokine_or_growth_factor / integrin_ligand / guanylyl_cyclase_ligand / antimicrobial / unknown) with the evidence that triggered it and the seedless nouns it selected. This is what makes the skill general rather than GPCR-only.
- **DPP4 / protease liability** — a peptide can be assay-negative because it is *cleaved*, not because it fails to bind. Native GLP-1 (`A@P2`) is **DPP4-LABILE**; exendin-4 (`G@P2`) is **resistant**. A labile flag triggers a "re-test with a DPP4 inhibitor or protease-resistant analog" note — a key alternative explanation for "works in vitro, not in the mouse assay."
- **ELM LIG motifs** (ranked by rarity) + the Pfam binding domain each engages — low-confidence context for peptides without a named PROSITE family.
- **Non-canonical / cyclic flag** — any residue outside the 20 standard L-amino acids is surfaced, because BLAST/PROSITE/ProtParam silently assume a canonical linear peptide and will mischaracterize a non-ribosomal/cyclic peptide (common for unicellular-organism natural products). Look such peptides up by name with `Norine_get_peptide` and pass `--cyclic` to `cofold_screen.py`.
- **Cross-species interface alignment** (top ≤3 candidates) — resolves each candidate's human + assay-species (+ optional source-species) ortholog sequence (UniProt) and aligns them (`EBI_msa_align`), reporting per-pair % identity and substitution count. A low human-vs-assay identity flags the ortholog whose binding interface most plausibly diverged — the mechanistic answer to "binds in A, not B". If the source organism is a protist absent from UniProt, it reports `insufficient` and tells you to supply the partner sequence by hand.
- **ClusPro-ready PDB** (top ≤3 candidates) — `PDBeSIFTS_get_best_structures` resolves a representative solved PDB id you can feed straight to `ClusPro_submit_peptide_docking`.

**Validated on the control** (`--sequence HGEGTFTSDLSKQMEEEAVRLFIEWLKNGGPSSGAPPPS --hypothesized-target GLP1R --phenotype "type 2 diabetes mellitus"`): recovers the class-B panel `{GCGR, GHRHR, GIPR, GLP1R, GLP2R, SCTR}`, flags **GLP1R as hypothesized (tested negative)**, and promotes **GIPR to Tier 1 (family + phenotype, score 0.674)** as the leading real-target hypothesis — exactly the deorphanization re-ranking, produced with zero API keys.

### `cofold_screen.py` — structural confirmation (Phase 5, key-gated)

Co-folds the peptide against each shortlisted receptor and ranks by interface confidence (ipTM). Requires `NVIDIA_API_KEY`; **without it, runs a DRY RUN** that still resolves every receptor sequence (GPCRdb → UniProt fallback) and prints the co-fold plan, so you can verify inputs before paying for GPU time.

```bash
python3 scripts/cofold_screen.py --peptide <SEQ> --candidates GIPR GCGR GLP2R \
  [--backend boltz2|alphafold2_multimer|openfold3] [--assay-species mus_musculus] [--out cofold.json]
```

Use the scripts for the fast path. When you need to run, debug, or extend a single step by hand, the **full per-phase manual reference** — every tool call the scripts automate, with exact parameter names, gotchas, fallback chains, runtime notes, and two fully worked examples — lives in **`references/phases.md`**. Read it when a script step fails, when you want to drive a phase manually, or when you extend the pipeline to a new tool.

---

## The pipeline at a glance

Six phases; the scripts automate 1–4 (and the Phase-5 dry run). **Full detail + exact tool calls + gotchas are in `references/phases.md`** — read it before driving any phase by hand.

| Phase | What it does | Key tools |
|---|---|---|
| **0** Verify | Confirm every tool loads; substitute fallbacks | `tooluniverse.cli run …` |
| **1** Characterize + motif + **classify** | Properties, non-canonical/cyclic flag, PROSITE/ELM signature → ligand family, **target-class router** (GPCR/channel/protease/cytokine/integrin/…) | `PepCalc`/`ProtParam`, `ScanProsite`→`PROSITE_get_entry`, `ELM_*`, `ESMFold` |
| **2** Candidate generation | 4 independent routes — homology, motif→domain, **target-family enumeration** (class-aware), phenotype anchor → union | `BLAST`/`EBI_msa_align`, `HGNC`+`InterPro`+`GPCRdb`+`GtoPdb`, `OpenTargets` |
| **3** Cross-species | Resolve "binds in A not B": align the ortholog interface across human / assay / source species | `EnsemblCompara`, `Alliance`, `UniProt`, `EBI_msa_align` |
| **4** Narrow + rank | Score on sequence × phenotype × pharmacology × cross-species → shortlist ≤15 | (intersection logic) |
| **5** Structural confirm *(optional, key-gated)* | Co-fold top candidates, rank by interface ipTM; or academic-free ClusPro docking | `NvidiaNIM_boltz2`/`…`, `ClusPro_submit_peptide_docking` |
| **6** Report | Ranked shortlist with evidence tiers + wet-lab plan | (inline report) |

**Core intersection rule:** the real target is where **phenotype-plausible** (Route 2D) meets **sequence/structure-plausible** (Routes 2A–2C). A name-level guess ("it's a GLP-1 analog so it's GLP1R") is exactly what produces off-target errors — never assert a target the union of routes didn't surface.

---

## Output format — ranked shortlist report (return inline, no extra files)

1. **Peptide characterization** — length, MW, pI, GRAVY, instability, PROSITE/ELM signature, non-canonical/cyclic flag, fold confidence (if run).
2. **Ranked candidate table** — one row per candidate target: gene + accession · target class · evidence tier · routes that surfaced it · OpenTargets phenotype score · known-pharmacology note (GtoPdb peptide ligands?) · cross-species status (`ortholog_one2one`? interface % identity in the assay species?).
3. **Cross-species reconciliation note** — for the lead, the human-vs-assay(-vs-source) interface comparison and what it predicts for "binds A not B."
4. **Recommended wet-lab validation** — binding/competition + a class-appropriate functional assay against the top ≤3 candidates and their assay-species orthologs (cAMP/β-arrestin for GPCRs; electrophysiology for channels; enzymatic/inhibition for proteases; reporter for cytokine receptors), with the GtoPdb-listed family antagonist as control where one exists.

**Evidence tiers** — always state which evidence is **keyless/validated** vs **key-gated (co-fold not run)**, and flag any candidate that is a **negative against the originally hypothesized target** so the reader sees the re-ranking:
- **Tier 1 (strong):** ≥2 independent sequence/structure routes **AND** present in the phenotype anchor **AND** (if Phase 5 run) top interface ipTM.
- **Tier 2 (moderate):** 1 sequence/structure route + phenotype support, OR ≥2 sequence routes without phenotype.
- **Tier 3 (weak/hypothesis):** single-route only (deep paralog, or a phenotype-only hit not corroborated by sequence/structure).

---

## Validation

Validated on the **exendin-4 → GLP1R control**: recovers the class-B panel `{GCGR, GHRHR, GIPR, GLP1R, GLP2R, SCTR}`, flags GLP1R as the (negative) hypothesized target, and promotes GIPR to Tier 1 — the deorphanization re-ranking, produced with zero API keys. Also validated on non-GPCR targets (ion channel, RTK, protease, cytokine receptor). The full step-by-step (control **and** the real "binds in the source organism, not in mouse" case) is in `references/phases.md`.
