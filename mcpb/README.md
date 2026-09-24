# ToolUniverse MCPB Bundle

This directory is the source of truth for `tooluniverse.mcpb` — the
Model Context Protocol Bundle published at
`https://github.com/mims-harvard/ToolUniverse/releases/download/mcpb/tooluniverse.mcpb`.

## Contents

| File | Purpose |
|---|---|
| `manifest.json` | MCPB 0.4 manifest. `server.type = "uv"` lets Claude Desktop install dependencies before starting MCP. |
| `pyproject.toml` | Bundle-specific deps. Keep in sync with the repo root `pyproject.toml`. |
| `.python-version` | Python 3.12 selection shared by installation and launch. |
| `src/run_stdio.py` | Entry point. Launches `tooluniverse.smcp_server.run_stdio_server` in compact mode. |
| `icon.png` | Bundle icon. |
| `build.sh` | Builds the `.mcpb` zip from this directory + the repo's `src/tooluniverse/`. |

## Build

This bundle requires a host with MCPB 0.4 UV runtime support, such as current
Claude Desktop. Older loaders that only accept `python`, `node`, and `binary`
server types must be updated. See the [MCPB UV runtime specification](https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md#uv-runtime-v04).

Claude Desktop prepares the virtual environment and dependencies during
installation. This can take several minutes on the first install. The server
then uses `uv run --no-sync` to start that prepared environment without network
resolution or a second `--with .` installation inside the MCP handshake timeout.
Keep `.python-version` in the bundle so both phases select the same Python.

The manifest's Python compatibility range uses semver (`>=3.10 <3.15`), while
`pyproject.toml` uses PEP 440 (`>=3.10,<3.15`). The bundle itself runs on Python
3.12; installing it on a machine with system Python 3.14 does not test the
dependencies under Python 3.14.

```bash
bash mcpb/build.sh
# → dist/tooluniverse.mcpb
```

The script:

1. Copies `mcpb/*` and the repo's `src/tooluniverse/` into a clean build dir
   (excluding `test/`, `__pycache__/`, `.pytest_cache/`, generated wrappers).
2. Runs `npx @anthropic-ai/mcpb@2.1.2 validate` against the manifest (or the
   executable specified by `MCPB_CLI` for offline builds).
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

## Privacy Policy

ToolUniverse runs locally and collects nothing: no telemetry, no analytics, no
conversation data. When you run a tool, that tool's arguments are sent to that
tool's data provider (UniProt, openFDA, Open Targets and so on) so it can
answer, and nothing else leaves your machine. API keys stay local and are sent
only to the service they belong to. Full policy:
https://github.com/mims-harvard/ToolUniverse/blob/main/PRIVACY.md
