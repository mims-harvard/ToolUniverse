# Changelog

All notable changes to the ToolUniverse Claude Code plugin.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.2.0] — 2026-05-16

### Added
- `read_executed_notebook` surfaces a new `preprocessing_cells` field that
  flags code cells performing sample exclusions or filtering, so the agent
  matches the published pipeline rather than silently diverging.
- New deterministic analysis scripts for common clinical-trial and
  regression workflows (SDTM ordinal logistic, natural-spline model
  comparison) accessible to the agent through their owning skills.

### Changed
- Router skill description tightened; specialized skills more reliably
  match data-file analysis questions.
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

### Removed
- Three slash commands that duplicated default agent behavior. The four
  remaining commands each enforce a discipline the agent won't apply on
  its own (cross-validation, namespace-complete ID resolution,
  domain-aware comparison, graded literature triage).

### Fixed
- Plugin build excludes test and cache artifacts from skill directories.
- Skill count in the plugin manifest and README now matches what ships.
- Removed a stale duplicate `marketplace.json` from the plugin source.

## [1.1.11] — earlier

See git history for prior releases.
