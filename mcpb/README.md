# ToolUniverse MCPB Bundle

This directory is the source of truth for `tooluniverse.mcpb` — the
Model Context Protocol Bundle published at
`https://github.com/mims-harvard/ToolUniverse/releases/download/mcpb/tooluniverse.mcpb`.

## Contents

| File | Purpose |
|---|---|
| `manifest.json` | MCPB manifest (validated by Claude Code). `server.type` MUST be `python \| node \| binary`. |
| `pyproject.toml` | Bundle-specific deps. Keep in sync with the repo root `pyproject.toml`. |
| `src/run_stdio.py` | Entry point. Launches `tooluniverse.smcp_server.run_stdio_server` in compact mode. |
| `icon.png` | Bundle icon. |
| `build.sh` | Builds the `.mcpb` zip from this directory + the repo's `src/tooluniverse/`. |

## Build

```bash
bash mcpb/build.sh
# → dist/tooluniverse.mcpb
```

The script:

1. Copies `mcpb/*` and the repo's `src/tooluniverse/` into a clean build dir
   (excluding `test/`, `__pycache__/`, `.pytest_cache/`, generated wrappers).
2. Runs `npx @anthropic-ai/mcpb validate` against the manifest.
3. Zips into `dist/tooluniverse.mcpb`.

## Release

After building locally:

```bash
gh release upload mcpb dist/tooluniverse.mcpb --clobber --repo mims-harvard/ToolUniverse
```

The release tag is the literal string `mcpb` (not version-tagged), so the
download URL stays stable for marketplaces (e.g. `anthropics/life-sciences`).

## Version sync

Bump `version` in BOTH `mcpb/manifest.json` and `mcpb/pyproject.toml` to match
the repo root `pyproject.toml` when shipping a new bundle.
