# Changelog

All notable changes to the ToolUniverse Claude Code plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.1] — 2026-05-22 (unreleased)

### Added — ESM-C SAE variant interpretation + DMS analysis suite

Full ToolUniverse implementation of the [upstream methodology repo](https://github.com/upstream methodology repo)
methodology . Adds 4 new tools and 8 new skills
covering single-variant mechanistic interpretation through whole-protein DMS analysis.

**New tools (4):**
- `ESM_get_sae_features` — per-residue ESM-C 6B Sparse Autoencoder feature
  activations (16,384-dim codebook, k=64 sparse) around a position window.
- `ESM_score_variant_sae_disruption` — composite: validates `ref_aa`, runs
  ref+mutant through the SAE, returns top features lost/gained ranked by Δ.
- `ESM_describe_sae_feature` — on-demand SAE feature labeling via UniProt
  feature annotations + voting on a curated 10-protein panel; cached locally.
- `Structure_annotate_per_residue` — per-residue annotation from a PDB:
  binding interface, ligand pocket, RSA (core/surface), optional secondary
  structure from PDBe REST. Adds optional dep `freesasa>=2.2.0`.

**New skills (8):**
- `tooluniverse-protein-sae-variant-interpretation` — single-variant SAE
  workflow with quick + long path, 6-category interpretation table.
- `tooluniverse-protein-lof-mechanism` — 5-signal LoF synthesis (ESMC +
  AlphaMissense + AlphaFold + UniProt + DynaMut2) with 6-category decision rule.
- `tooluniverse-protein-structural-annotation-pdb` — wraps Structure_annotate_per_residue.
- `MaveDB_get_effect_matrix` — orchestrates `MaveDB_*` tools + HGVS parsing.
- `tooluniverse-variant-predictor-dms-benchmarking` — validate ANY
  per-variant predictor (AlphaMissense / SAE / ESM logits / EVE / conservation
  / DynaMut2 / custom) against DMS data via Mann-Whitney U + robustness sweep.
  SAE is shown as the worked example; the methodology is predictor-agnostic.
- `tooluniverse-residue-functional-mechanism-interpretation` — given any set
  of residues in a protein (DMS hotspots / ClinVar recurrent variants /
  literature hot regions / conserved positions / user-curated list), explain
  WHY they are functionally critical by combining structural context
  (binding interface / ligand pocket / core / SS), UniProt features (active
  site / binding site / PTM / disulfide), and optional SAE feature evidence.
  Two entry paths: Path A accepts `user_provided_positions` directly; Path B
  detects hotspots from a DMS matrix. Returns a mechanism call: catalytic /
  ligand-binding / interface / structural-core / PTM / regulatory / mixed /
  unknown. Step 7 produces the annotated DMS heatmap (when DMS data is
  available).

**Verification:**
- 46 unit tests pass (18 SAE + 11 structural-annotation + 17 DMS skill snippet tests).
- `Structure_annotate_per_residue` reproduces the reference annotation
  with **168/168 region matches** on 6VJJ (KRAS-RAF1-GTP).
- TP53 R175H end-to-end SAE skill workflow returns expected DNA-binding LoF mechanism.
- PDBe live secondary-structure path verified: KRAS β1 (residues 2-9) and α3
  (residues 87-104) come back labeled correctly.

**Prerequisites:**
- `ESM_API_KEY` env var (EvolutionaryScale Forge token, https://forge.evolutionaryscale.ai)
- `pip install 'esm @ git+https://github.com/evolutionaryscale/esm@ee891c52'` —
  `SAEConfig` is on the upstream feature branch, not yet in PyPI `esm 3.2.x`.
- For Structure tool: `pip install tooluniverse[bioinformatics]`.

Outputs from ESM SAE via Forge are governed by the [Cambrian Inference
Clickthrough License](https://www.evolutionaryscale.ai/policies/cambrian-inference-clickthrough-license-agreement)
(non-commercial / academic use only) — surfaced in tool metadata.

## [1.2.0] — 2026-05-20

### Added
- New `/tooluniverse:research` slash command — drives a multi-database
  investigation **inline in the current conversation**, so you can watch
  each tool call and refine. The `/tooluniverse:researcher` agent is the
  sibling that runs the same investigation in a forked subagent and
  returns one summary.
- `read_executed_notebook` surfaces a new `preprocessing_cells` field that
  flags code cells performing sample exclusions or filtering, so the agent
  matches the published pipeline rather than silently diverging.
- New deterministic analysis scripts for common clinical-trial and
  regression workflows (SDTM ordinal logistic, natural-spline model
  comparison) accessible to the agent through their owning skills.
- General analysis-discipline rules across 8 skills (router, rnaseq-deseq2,
  gene-enrichment, stat-modeling, epigenomics, sequence-analysis,
  variant-analysis, phylogenetics) that improve answer quality on
  ambiguous method-choice questions. None of the rules encode
  benchmark-specific content; they're principles like "report all standard
  DEG-count variants in your answer body", "Trimmomatic 'reads
  completely discarded' = F + R + 2*D", "long-format methylation CSV —
  'sites removed' means ROWS not unique positions", "percentage" vs
  "proportion" units convention.

### Changed
- Slash commands renamed to drop the redundant `tu-` prefix —
  `/tooluniverse:` already namespaces them. New names:
  `compare`, `cross-validate`, `literature-sweep`, `translate-id`,
  `research`. The `researcher` agent name is unchanged.
- Router skill description tightened; specialized skills more reliably
  match data-file analysis questions.
- Two skills with non-kebab-case `name:` fields fixed
  (`tooluniverse-microbiome-research`, `tooluniverse-protein-interactions`)
  so the router's `Skill('<name>')` dispatch resolves correctly.
- Phylogenetics scripts accept `--data-folder` as the canonical input
  flag.
- Researcher agent trimmed to a focused mission + tool-discovery pattern;
  domain-specific analysis conventions now live exclusively in their
  specialized skills.
- Skill text uses general "data folder" terminology throughout.
- `.mcp.json` no longer forces a PyPI refresh on every session start —
  faster startup and offline-tolerant. The README documents how to force
  a refresh or pin a version.
- SessionStart cleanup of legacy global skills runs once via a marker
  file instead of every session.
- Skill count corrected to 115 across all manifests, READMEs, and the
  install skill (previously claimed 116).

### Removed
- Three slash commands that duplicated default agent behavior. The four
  remaining commands each enforce a discipline the agent won't apply on
  its own (cross-validation, namespace-complete ID resolution,
  domain-aware comparison, graded literature triage).

### Fixed
- Plugin build excludes test and cache artifacts from skill directories.
- Removed a stale duplicate `marketplace.json` from the plugin source.

### Docs
- New comprehensive Claude Code plugin install + usage page in the docs
  guide (`docs/guide/building_ai_scientists/claude_code.rst`) covering
  the two-command install, version pinning, API-key setup,
  troubleshooting, and the manual-MCP fallback.

## [1.1.11] — earlier

See git history for prior releases.
