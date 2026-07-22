# Installation Documentation Audit & Plan

**Branch:** `docs/install-full-guidance` · **Scope:** docs / README / skills / extras naming only. No product code, no service/credential files, no website repo.

## Problem (corrected scope)

Users treat ToolUniverse as "just a pip package," run bare `pip install tooluniverse`, and get an **incomplete system**. The gap is **not only** the missing package extras — it is that ToolUniverse is a **complete platform** and the package is one component. A working setup is a multi-step onboarding:

1. **`uv`** — the single prerequisite
2. **An access mode** — MCP server (chat), `tu` CLI, or Python SDK (the SDK is where the full `[all]` package matters)
3. **API keys** — NCBI/PubMed, NVIDIA structure prediction, FDA, USPTO, DisGeNET, OMIM, … Key-gated tools still register and are discoverable, but return a clear "set XXX env var" error (or run rate-limited) at call time until a key is provided
4. **Agent skills / research workflows** — installed into the client (`npx skills add …` or the plugin); these make it a research platform, not a tool list
5. **Validation** — `tu status`, a test tool call

Every install surface must therefore **lead with the whole-system onboarding** and stop implying `pip install` = done. Package-level guidance (`[all]` vs core-only) is a sub-step of the SDK access mode, not the headline.

### Website audit (aiscientist.tools) — `setup.md` source IS in this repo (fixed here)

The site is a full platform, not a package page. Sitemap routes: `/`, `/search` (tool registry), `/graph` (tool relationship graph), `/BuildAIScientist`, `/mcp`, `/workflows` (skills), `/submit`, `/contributors`, `/citation`. Most are client-rendered (React SPA); only `/setup.md` returns static markdown.

**`https://aiscientist.tools/setup.md`** is the canonical onboarding (5 steps: install `uv` → choose access mode → API keys → test → install skills). **It is served byte-for-byte from this repo's `skills/setup-tooluniverse/SKILL.md`** — verified: the live file carries the `name: setup-tooluniverse` YAML frontmatter, the "Internal Notes (do not show)" / "Agent Behavior" / "AskQuestion" markers, and the "# Setup ToolUniverse" header. The website just serves the raw skill markdown (the `web/` dir here holds only data JSON — the site SPA is separate, but the *content* of setup.md is this skill).

It had the same crippled default (SDK step `uv pip install tooluniverse`, no `[all]`). **This branch fixes it directly**: the `setup-tooluniverse` skill's SDK step is now `uv pip install "tooluniverse[all]"` + core-only caveat, 5-step framing intact, mirrored across all three skill trees. Once this merges to `main`, the live setup.md updates when the site re-pulls. The CLI step (`uvx --from tooluniverse tu status`) is intentionally left on the base package (ephemeral `tu` calls hit API tools; forcing `[all]` would download the full heavy stack on every run).

---

## Phase 1 — Canonical "full install" (verified against `pyproject.toml`)

`pyproject.toml` `[project.optional-dependencies]` defines these groups:
`client`, `smolagents`, `singlecell`, `dev`, `docs`, `embedding`, `ml`, `graph`, `visualization`, `space`, `bioinformatics`, `build`, and the aggregate:

```toml
all = ["tooluniverse[dev,docs,graph,visualization,space,embedding,ml,bioinformatics]"]
```

**Canonical recommended full install (settled):**

```bash
uv pip install "tooluniverse[all]"     # or:  pip install "tooluniverse[all]"
```

- The `[all]` extra **exists and works** — it is the single "install everything meaningful" command. No pyproject change is required to express the full story.
- Quotes are required in zsh (default macOS shell), where unquoted `[all]` is a glob. Existing docs write `pip install tooluniverse[all]` unquoted; standardize on the quoted form.
- **Extras NOT in `all`** (flagged for review, not changed here):
  - `singlecell` (cellxgene-census, tiledbsoma) — heavyweight, platform-specific; intentionally separate. Documented as an add-on: `pip install "tooluniverse[singlecell]"`.
  - `smolagents`, `client`, `build` — narrow/niche; correctly excluded from `all`.
  - **Review question (do NOT change without sign-off):** should `singlecell` be folded into `all`? Recommendation: **keep separate** (its native deps break on many platforms), but document it as a prominent add-on wherever `[all]` appears. This is the only extras-naming ambiguity found; everything else is expressible today.

**Platform framing one-liner (reuse verbatim):**
> ToolUniverse is a platform — an MCP server, a registry of 2,600+ scientific tools, and 150+ agent skills — not just a Python package. Install the full package so every tool registers.

**Minimal / core-only note (reuse verbatim — honest version):**
> `pip install tooluniverse` (without `[all]`) installs just the core package — the tool *library*, not the assembled system (no skills, no chat/MCP, no API keys). All tools still register and appear in `tu list`/`tu status`; but tools that need optional scientific dependencies (ML models, RDKit/cheminformatics, visualization, bioinformatics, single-cell) return a clear error when called (e.g. `Install with: pip install rdkit`) until you add `[all]`.

### Accuracy correction + number unification (this pass)

- **Wording:** verified in code that all optional imports are `try/except`-guarded and `@register_tool` runs unconditionally, so bare-install tools **still register** and fail **loudly at call time** with actionable messages — not "silently." All "silently fail to register/run" phrasing was corrected to the honest version above across README/docs/all three skill trees.
- **Numbers (deterministic counts):** tool config entries = **2,620** across 607 configs → standardized on **"2,600+ tools"**; `SKILL.md` dirs = **152** (canonical `skills/` tree; 139 shipped in the plugin) → standardized on **"150+ skills"**. Replaced scattered `1000+/1200+/2,000+` (tools) and `60+/115/120+/130+/68` (skills) across README, docs, the three skill trees, and the plugin/marketplace manifests. Deliberately left untouched: the `docs/index.rst` per-category card badges (`15/6/1` — a separate categorized breakdown, not a platform-scale claim), the `devtu-docs-quality` QA skill (uses counts as teaching examples), and non-tool "1000+" data counts (epigenomics "1000+ positions", binder "1000+ SMILES").
- **Deferred (separate follow-up, report R27):** `setup.md` = `setup-tooluniverse/SKILL.md` still leaks agent-only content to the public site (`## Internal Notes (do not show)`, `## Agent Behavior`, `AskQuestion`, routing frontmatter). Not touched this pass — needs a decouple-public-page-from-agent-skill decision.

---

## Phase 1 — Website copy location (`setup.md` source is in THIS repo)

- The README + every `docs/guide/building_ai_scientists/*.rst` page point the "recommended" agent path at **`https://aiscientist.tools/setup.md`**.
- **Correction (initial audit was wrong):** `setup.md` is **served byte-for-byte from this repo's `skills/setup-tooluniverse/SKILL.md`**. Verified against the live URL — it carries the `name: setup-tooluniverse` frontmatter, the "Internal Notes (do not show)" / "Agent Behavior" / "AskQuestion" markers, and the "# Setup ToolUniverse" header. The site's React SPA (separate repo) just serves the raw skill markdown; the *content* is this skill. (`web/` here is only data JSON, which is why the first grep missed it — the source was hiding in plain sight as the skill.)
- **Action:** editable directly, and **fixed by this branch** — the `setup-tooluniverse` skill's SDK step is corrected to `uv pip install "tooluniverse[all]"` across all three skill trees. No separate site-repo change needed; live setup.md updates when the site re-pulls `main`.

---

## Phase 2 — Global audit (file:line → proposed edit)

Legend: **FIX** = change lead to full install + demote bare; **KEEP** = correct as-is (context-specific extra or lightweight-by-design); **NOTE** = leave command, add one-line pointer.

### Tier 1 — Primary entry points (FIX)

| File:line | Current | Proposed edit |
|---|---|---|
| `README.md:46-49` | "Python developers — `uv pip install tooluniverse`" | Lead with `uv pip install "tooluniverse[all]"` + platform framing; add labeled **minimal / core-only** note for bare install. |
| `docs/guide/python_guide.rst:6-44` | `Installation` tab-set: pip / uv leads are bare | Reorder to a **Recommended (full)** lead `uv pip install "tooluniverse[all]"`; keep pip/uv/dev tabs but each uses `[all]`; add minimal-note admonition. |
| `docs/about/faq.rst:25-29` | "How do I install it?" → `pip install tooluniverse` | `pip install "tooluniverse[all]"` + one-line minimal note. |
| `docs/help/faq.rst:66-75` | "Basic Installation" tab → `pip install tooluniverse` | Rename tab "Full Installation (Recommended)" → `pip install "tooluniverse[all]"`; add minimal note. |
| `docs/help/faq.rst:344` | venv example ends `pip install tooluniverse` | `pip install "tooluniverse[all]"`. |
| `docs/help/troubleshooting.rst:55-80` | "Standard Installation" tab + venv → bare | `pip install "tooluniverse[all]"` in the standard + venv tabs. |
| `docs/help/troubleshooting.rst:99` | conda clean-env → bare | `pip install "tooluniverse[all]"`. |
| `skills/setup-tooluniverse/INSTALL.md` | Method 1/2 lead bare; `[all]` buried under "Optional" | Add **Recommended: full install** block at top (`uv pip install "tooluniverse[all]"`); relabel Method 1 "Core-only (minimal)" with warning; keep per-extra list. |
| `skills/setup-tooluniverse/SKILL.md:88-94` | SDK Setup → `uv pip install tooluniverse` | `uv pip install "tooluniverse[all]"` + inline minimal note. |
| `skills/setup-tooluniverse/EXAMPLES.md:22-25,332,410,467` | Example install steps lead bare | `pip install "tooluniverse[all]"` in the "Install ToolUniverse" steps. |
| `skills/tooluniverse-sdk/SKILL.md:16-20` | `pip install tooluniverse # Standard` first | Reorder: `[all]` first as recommended; bare labeled "core-only". |
| `skills/tooluniverse-sdk/REFERENCE.md:11-23` | bare `pip install tooluniverse` first | Lead with `[all]`; keep per-extra table below. |
| `skills/tooluniverse-metabolomics/QUICK_START.md:19-22` | bare pip / uv | `"tooluniverse[all]"`. |
| `skills/tooluniverse-gwas-snp-interpretation/QUICK_START.md:9` | bare pip | `"tooluniverse[all]"`. |
| `skills/tooluniverse-gwas-drug-discovery/QUICK_START.md:28` | bare pip | `"tooluniverse[all]"`. |

All skill edits are mirrored into `plugin/skills/<same>` and `plugins/tooluniverse/skills/<same>` (see mirroring note below).

### Tier 2 — Context-specific (KEEP / NOTE)

| File:line | Decision | Reason |
|---|---|---|
| `docs/guide/http_api.rst:19,69,298-299` | KEEP | Deliberate server/client split: `[client]` = requests+pydantic only, by design. |
| `docs/guide/chatgpt_api.rst:16` | KEEP | Tutorial-specific `pip install tooluniverse openai`; not a general "how to install." |
| `docs/guide/make_your_data_agent_searchable.rst:37` | KEEP | Tutorial building a local package; base is the relevant install. |
| `docs/guide/expert_feedback.md:28`, `docs/tools/remote/expert_feedback.md:30` | KEEP | Single-feature remote tool; base install is correct for it. |
| `docs/tools/remote/*.md` (boltz, immune_compass, pinnacle, …) | KEEP | Each remote model has its own heavyweight env; unrelated to core extras. |
| `skills/setup-tooluniverse/MCP_CONFIG.md:91` | KEEP | Prose reference ("installed via pip install tooluniverse"), not an install lead. |
| `Dockerfile:17` | NOTE | Slim MCP-stdio image (API tools) is intentional; adding `[all]` bloats it (torch/rdkit/faiss). Add a comment documenting `[all]` for full local-compute coverage; leave default slim. |
| All `tooluniverse[ml|visualization|bioinformatics|embedding|graph|singlecell|client]` references | KEEP | Correct targeted per-extra instructions. |

### Extras naming (Phase 2 finding)

- The "full" story **is** expressible today via `[all]`; no blocker. Only nuance is `singlecell` sitting outside `all` (see Phase 1). Flagged for review; **no pyproject.toml change made**.

---

## Phase 3 — Implementation notes

- **Skill mirroring:** `skills/` (build source), `plugin/skills/` (Claude marketplace → `.claude-plugin/marketplace.json` `source: ./plugin`), and `plugins/tooluniverse/skills/` (Codex plugin, `.codex-plugin/`) are all git-tracked. Target files are byte-identical across trees **except** `setup-tooluniverse/SKILL.md` and `tooluniverse-sdk/SKILL.md` differ in the `plugins/tooluniverse` copy → those get targeted edits; the rest are edited in `skills/` then `cp`-synced to both mirrors. Verify with `diff -rq`.
- **Quoting:** always `"tooluniverse[all]"` (zsh-safe).
- **No behavior change:** docs/skills text + extras documentation only.

## Deliverables recap

1. This plan.
2. Applied edits on `docs/install-full-guidance` (committed, not pushed).
3. Canonical command: **`uv pip install "tooluniverse[all]"`**. Website copy (`aiscientist.tools/setup.md`) = this repo's `skills/setup-tooluniverse/SKILL.md` — **fixed in this branch**, no separate lane needed.
