# Changelog

All notable changes to the ToolUniverse Claude Code plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
