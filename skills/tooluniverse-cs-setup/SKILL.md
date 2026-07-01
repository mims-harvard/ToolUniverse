---
name: tooluniverse-cs-setup
description: Install or update ToolUniverse in Claude Science — create the conda env, install the tooluniverse pip package, and (re)build the tooluniverse-research skill by fetching the current workflow library from GitHub. Use for first-time setup, upgrading the ToolUniverse version, refreshing the bundled workflows after an upstream release, or reinstalling on a new machine.
---

# Set up ToolUniverse for Claude Science

The upstream ToolUniverse ships a Claude **Code** plugin (MCP server + `uvx` + slash commands). Claude **Science** loads capabilities differently, so this skill installs the equivalent natively: the `tooluniverse` **pip package** supplies the 2500+ tools, and the workflow library is packaged into a single dynamically-loaded skill, `tooluniverse-research`. No `uv`, no MCP server, no plugin marketplace.

Loading this skill defines `tu_build_research_bundle()` in the kernel (run cells in the **`tooluniverse`** conda env).

## Full install / update — four steps

**1. Create the conda env** (skip if it already exists):
```
manage_environments(mode="create", name="tooluniverse", python_version="3.11", packages=["pip"])
```

**2. Install (or upgrade) the tools** — the pip package is the tool layer:
```
manage_packages(mode="install", environment="tooluniverse", packages=["tooluniverse"], use_pip=True)
```
Pin a version for reproducibility with `["tooluniverse==1.3.0"]`.

**3. Stage the workflow bundle** — fetch the current repo and rebuild the file tree (run in a `python` cell, env `tooluniverse`):
```python
res = tu_build_research_bundle(staging="./tu_staging")
res  # {out_dir, n_workflows, n_files, dropped, files_head}
```
This downloads the repo tarball, parses every `tooluniverse-*` workflow (dropping the plugin/installer entries), and writes `./tu_staging/out/` = `SKILL.md`, `kernel.py`, `index.json`, `workflows/*.md`.

**4. Publish the skill** — push the staged tree into the catalog (run in the **`repl`** tool; `host.skills.*` lives there, not in `python`):
```python
import os
SKILL = "tooluniverse-research"
out = os.path.abspath("./tu_staging/out")
if any(s["name"] == SKILL for s in host.skills.list()):
    host.skills.delete(SKILL)                       # clean rebuild
for root, _d, fs in os.walk(out):
    for f in fs:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, out)
        host.skills.edit(SKILL, rel, open(p, encoding="utf-8").read())
print(host.skills.publish(SKILL, overwrite=True))
```
(`host.skills.publish` refuses if `kernel.py` fails the sidecar gate — the `edit` result carries the verdict.)

## Verify

```python
skill("tooluniverse-research")                      # loads router + injects helpers
tu = get_tu()
tu.run({"name": "PubChem_get_CID_by_compound_name", "arguments": {"name": "metformin"}})
# -> {'status': 'success', 'data': {'IdentifierList': {'CID': [4091]}}}
```

## Notes

- **Sandbox cache**: ToolUniverse defaults its cache to `~/.tooluniverse`, which is read-only here; `get_tu()` redirects it to the workspace via `TOOLUNIVERSE_CACHE_DIR`. Nothing to configure.
- **API keys** (optional): most tools work without them. For NCBI / OncoKB / NVIDIA etc., add keys under Customize → Credentials, then expose them in the `tooluniverse` env.
- **What is NOT ported**: the plugin's slash commands (`/tooluniverse:research`) and MCP server — replaced by natural-language routing (`search_skills` → `find_tu_workflow`). The two `*-plugin` installer docs are dropped as non-research entries.
- **Updating**: rerun steps 2–4. Step 2 upgrades the tools; steps 3–4 refresh the workflow library from the latest GitHub state.
