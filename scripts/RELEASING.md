# Releasing the ToolUniverse Claude Code and Codex plugins

Quick reference. Three ways to release, ranked from most to least automatic.

---

## Versioning scheme

Both plugins (Claude Code and Codex) share the PyPI `tooluniverse` package's
**MAJOR.MINOR** and carry their own **PATCH** (the plugin revision):

```
plugin version = <package MAJOR>.<package MINOR>.<plugin revision>
```

- A **plugin-only change** (e.g. a skill edit) bumps the PATCH — `1.2.18 → 1.2.19`
  — and ships **without** an empty PyPI package release.
- When the **package's MAJOR.MINOR advances** (e.g. PyPI `1.3.0`), the next plugin
  release **resets to `1.3.0`**.
- The package keeps its own independent PyPI release line (`pyproject.toml` +
  `vX.Y.Z` tags); a plugin release never touches it.

`release-plugin.sh` derives the next version automatically from
`pyproject.toml`, so `auto`/`patch`/`minor`/`major` all do the same thing (next
plugin revision). The level argument is advisory only — the plugin's MAJOR.MINOR
is decided by the package, not the marker. Pass an explicit `X.Y.Z` to override.

---

## 1. Commit-message marker (most automatic)

Add `[release:patch]`, `[release:minor]`, or `[release:major]` to a commit
message. On push to `main`, the `auto-release.yml` workflow fires the rest.
(Any of the three markers triggers a release; the level is advisory — see above.)

```bash
git commit -m "Add tooluniverse-foo skill [release:patch]"
git push origin main
```

What happens automatically:
1. `auto-release.yml` reads the marker, runs `scripts/release-plugin.sh`
2. Script bumps the version in all 4 plugin manifests, creates a `Release vX.Y.Z`
   commit + tag, pushes both
3. Tag push triggers `release-plugin.yml` → builds zip + creates GitHub Release
4. Users receive it automatically: **Claude Code** on the version bump (next
   startup), **Codex** on the git push (startup marketplace auto-upgrade)

No marker = no release. Routine commits (typo fixes, refactors, doc updates)
land normally.

> Before a release that changes skills, run `plugin/sync-skills.sh` so both
> plugins' bundled `skills/` are rebuilt from the canonical `skills/` tree.

---

## 2. GitHub Actions UI (no terminal)

Go to: https://github.com/mims-harvard/ToolUniverse/actions/workflows/auto-release.yml

Click **Run workflow** → pick any level → Run. Same pipeline as #1.

---

## 3. Local script (full control)

```bash
# Next plugin revision (tracks the package MAJOR.MINOR)
bash scripts/release-plugin.sh auto

# Explicit version (manual override)
bash scripts/release-plugin.sh 1.3.0

# Preview without changing anything
bash scripts/release-plugin.sh auto --dry-run

# Bump + commit + tag locally; review before pushing
bash scripts/release-plugin.sh auto --no-push
```

The script:
- Refuses on a dirty working tree (no accidental bundling of unrelated changes)
- Refuses if new version equals current
- Bumps all 4 plugin manifests in lockstep
- Tags with `vX.Y.Z` (annotated tag)
- Pushes commit + tag (unless `--no-push`)

After the script, the tag push triggers `release-plugin.yml` to build the zip
and create the GitHub Release.

---

## What gets bumped (must stay in sync)

Four plugin manifests share the version. The release script bumps all of them
(absent manifests in the current layout are skipped):

| File | Field | Read by |
|---|---|---|
| `plugin/.claude-plugin/plugin.json` | `version` | **Claude auto-update** — read on every Claude Code startup |
| `plugin/.claude-plugin/marketplace.json` | `metadata.version` | Claude marketplace listing |
| `.claude-plugin/marketplace.json` | `metadata.version` | Claude marketplace listing |
| `plugins/tooluniverse/.codex-plugin/plugin.json` | `version` | Codex plugin manifest |

The Claude `plugin.json` is critical for Claude: **without bumping it on `main`,
auto-update users won't receive the new version even if you've tagged and
released.** Codex keys off the git commit instead, so the push itself delivers
the update — but the version bump keeps the two plugins coherent.

The PyPI `tooluniverse` package (`pyproject.toml`) is **not** bumped here — it has
its own release line. Both plugins serve tools from it over MCP via
`uvx tooluniverse`, so a package release reaches both plugins independently.

---

## What users see

**Claude Code** users with auto-update enabled for the `tooluniverse` marketplace
(third-party marketplaces default to off — users opt in once):
1. Restart Claude Code (or wait for periodic refresh)
2. Claude re-pulls `marketplace.json` from `mims-harvard/ToolUniverse`, sees the
   bumped `version`, stages the new version, prompts `/reload-plugins`

Users without auto-update enabled:
```
/plugin marketplace update tooluniverse
/plugin uninstall tooluniverse@tooluniverse
/plugin install tooluniverse@tooluniverse
/reload-plugins
```

**Codex** users get it automatically on the next startup (Codex auto-upgrades
configured Git marketplaces by default), or on demand:
```
codex plugin marketplace upgrade tooluniverse
```

---

## Safety mechanisms

- **Dirty-tree check** — the script won't run if there are uncommitted changes
- **Marker required for auto-release** — routine plugin commits don't trigger releases
- **No-loop guarantee** — the bump commit's message is `Release vX.Y.Z` (no marker), so
  it can't re-trigger the auto-release workflow
- **`--dry-run` to preview** any version bump without making changes
- **`--no-push` to inspect** the local commit before pushing

---

## What ships in each release

Skills, slash commands, the research agent, hooks, and the bundled MCP server
config all update atomically with the plugin version. The Python `tooluniverse`
package on PyPI is independent — the bundled `.mcp.json` runs `uvx tooluniverse`,
so the tool definitions track the published PyPI release separately from the
plugin version.

---

## Files involved

```
.github/workflows/auto-release.yml                 # marker-triggered or UI-triggered
.github/workflows/release-plugin.yml               # tag-push → zip + GitHub Release
scripts/release-plugin.sh                          # local one-command release
scripts/RELEASING.md                               # this file
plugin/sync-skills.sh                              # rebuild both plugins' skills/
plugin/.claude-plugin/plugin.json                  # Claude version (auto-update reads this)
plugin/.claude-plugin/marketplace.json
.claude-plugin/marketplace.json
plugins/tooluniverse/.codex-plugin/plugin.json     # Codex version
```
