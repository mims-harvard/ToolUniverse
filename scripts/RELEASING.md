# Releasing the ToolUniverse Claude Code plugin

Quick reference. Three ways to release, ranked from most to least automatic.

---

## 1. Commit-message marker (most automatic)

Add `[release:patch]`, `[release:minor]`, or `[release:major]` to a commit
message. On push to `main`, the `auto-release.yml` workflow fires the rest.

```bash
git commit -m "Add tooluniverse-foo skill [release:minor]"
git push origin main
```

What happens automatically:
1. `auto-release.yml` reads the marker, runs `scripts/release-plugin.sh minor`
2. Script bumps version in 3 manifests, creates `Release v1.2.0` commit + tag,
   pushes both
3. Tag push triggers `release-plugin.yml` → builds zip + creates GitHub Release
4. Auto-update users receive the new version on next Claude Code startup

No marker = no release. Routine commits (typo fixes, refactors, doc updates)
land normally.

---

## 2. GitHub Actions UI (no terminal)

Go to: https://github.com/mims-harvard/ToolUniverse/actions/workflows/auto-release.yml

Click **Run workflow** → pick `patch` / `minor` / `major` → Run.

Same pipeline as #1, just triggered from the web UI.

---

## 3. Local script (full control)

```bash
# Patch (1.1.11 → 1.1.12)
bash scripts/release-plugin.sh patch

# Minor (1.1.11 → 1.2.0)
bash scripts/release-plugin.sh minor

# Major (1.1.11 → 2.0.0)
bash scripts/release-plugin.sh major

# Explicit version
bash scripts/release-plugin.sh 1.5.0

# Preview without changing anything
bash scripts/release-plugin.sh patch --dry-run

# Bump + commit + tag locally; review before pushing
bash scripts/release-plugin.sh patch --no-push
```

The script:
- Refuses on a dirty working tree (no accidental bundling of unrelated changes)
- Refuses if new version equals current
- Bumps all 3 manifests in lockstep
- Tags with `vX.Y.Z` (annotated tag)
- Pushes commit + tag (unless `--no-push`)

After the script, the tag push triggers `release-plugin.yml` to build the zip
and create the GitHub Release.

---

## What gets bumped (must stay in sync)

Three manifest files share the version. The release script bumps all three:

| File | Field | Read by |
|---|---|---|
| `plugin/.claude-plugin/plugin.json` | `version` | **Auto-update** — reads on every Claude Code startup |
| `plugin/.claude-plugin/marketplace.json` | `metadata.version` | Marketplace listing |
| `.claude-plugin/marketplace.json` | `metadata.version` | Marketplace listing |

The first one is critical: **without bumping it on `main`, auto-update users won't
receive the new version even if you've tagged and released.** The script handles
this; if you ever release manually, don't forget.

---

## What users see

Users with auto-update enabled for the `tooluniverse` marketplace:
1. Restart Claude Code (or wait for periodic refresh)
2. Claude Code re-pulls `marketplace.json` from `mims-harvard/ToolUniverse`
3. Sees the bumped `version` in the plugin's `plugin.json`
4. Downloads and stages the new version silently
5. Notification prompts them to run `/reload-plugins`

Users without auto-update enabled need to:
```
/plugin marketplace update tooluniverse
/plugin uninstall tooluniverse@tooluniverse
/plugin install tooluniverse@tooluniverse
/reload-plugins
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
config all update atomically with the plugin. Users don't update them
separately. The Python `tooluniverse` package on PyPI is independent — the
bundled `.mcp.json` uses `uvx --refresh` to pull the latest PyPI release on
every server launch, so even an older plugin install gets the freshest tool
definitions at MCP startup.

---

## Files involved

```
.github/workflows/auto-release.yml      # marker-triggered or UI-triggered
.github/workflows/release-plugin.yml    # tag-push → zip + GitHub Release
scripts/release-plugin.sh               # local one-command release
scripts/RELEASING.md                    # this file
plugin/.claude-plugin/plugin.json       # version field (auto-update reads this)
plugin/.claude-plugin/marketplace.json
.claude-plugin/marketplace.json
```
