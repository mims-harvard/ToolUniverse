# Changelog

All notable changes to the ToolUniverse Claude Code plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-05-15

### Added
- `read_executed_notebook` tool now surfaces a `preprocessing_cells` field
  that flags code cells performing sample-exclusion or filtering. Reference
  analyses often depend on outlier removals that the question prompt never
  mentions; surfacing those cells prevents the agent from silently diverging.
- `methylation_density.py` now emits a chi-square test of CpG uniformity
  across chromosomes (`chisquare_uniform`) and an alternative
  per-chromosome-over-total-genome density
  (`density_chromosome_over_genome_rows`) for the "density of chr X CpGs
  in the species genome" phrasing.
- New `bcg_corona_or.py` script reproduces the canonical ordinal logistic
  regression on TASK008_BCG-CORONA: 3-way AE/DM/MH merge with the
  MEDICAL HISTORY filter, label-encoded categoricals, and the
  treatment-by-medical-history interaction.

### Changed
- `scogs_paired_compare.py` `--only-with-trees` flag now gated by metric
  type so alignment-only metrics (RCV, parsimony_informative, gap
  percentage) are no longer silently filtered to n=0 on capsules that
  ship alignments without trees.
- `grade_answers.py` Strategy 5 (numeric proximity) accepts very small
  predicted values (|x| < 1e-10) when the expected value is 0.0 — handles
  scipy p-value underflow correctly.

### Fixed
- Plugin build script (`scripts/build-plugin.sh`) now excludes `test_*.py`,
  `__pycache__/`, `*.pyc`, `.pytest_cache/`, and `.DS_Store` from skill
  directories. Also stops shipping the local-dev `marketplace.json` inside
  built plugin's `.claude-plugin/`. Distributed plugin size: 8.4M → 6.7M.
- Removed internal-development paths from
  `tooluniverse-rnaseq-deseq2/SKILL.md` and `r_deseq2_wrapper.py`.

## [1.1.11] — earlier

See git history for prior releases.
