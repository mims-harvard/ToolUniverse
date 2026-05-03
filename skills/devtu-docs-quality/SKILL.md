---
name: devtu-docs-quality
description: TOP PRIORITY skill — find and immediately fix or remove every piece of wrong, outdated, or redundant information in ToolUniverse docs. Wrong code, broken links, incorrect counts, and overlapping instructions must be fixed or removed — never left in place. Runs five phases: (D) static method scan, (C) live code execution, (A) automated validation, (B) ToolUniverse audit, (E) less-is-more simplification. Core philosophy: each concept appears exactly once; remove don't add; no emojis; single setup entry point. Use when reviewing docs, before releases, after API changes, or when asked to audit, fix, or simplify documentation.
---

# Documentation Quality Assurance

## Two Equal Priorities

Both of the following must be satisfied before an audit is done. Neither overrides the other.

**1. Technical correctness** — wrong code is worse than no code; it actively breaks users' workflows.

**2. Less is more** — redundant content is worse than no content; it creates confusion, dilutes trust, and makes maintenance harder.

> When in doubt about technical accuracy: **verify against source** (`src/tooluniverse/execute_function.py`).
> When in doubt about whether content is needed: **delete it**.

---

## Less Is More — The Core Philosophy

ToolUniverse is a serious research tool. Documentation should reflect that with restraint and precision, not volume.

### What "less is more" means in practice

**Remove, don't add.** Every edit should end with fewer words, fewer pages, fewer links. The field moves fast — outdated instructions are actively harmful. When two approaches both work, keep one.

**Each concept appears exactly once.** If setup instructions appear in three places, a user reading one doesn't know the others exist, and maintainers must update all three on every change. Pick one canonical location and cross-link everywhere else.

**No emojis.** Emojis in headings, nav items, card titles, and bullet points signal "AI-generated" and undermine trust in a serious scientific tool. Remove them unconditionally — no exceptions for "emphasis."

**Shrink, don't summarize.** A page reduced from 1000 lines to 30 pointer lines is better than a 1000-line page summarized with a TL;DR box. Do the surgery.

**Size budgets (hard limits):**

| Page type | Max lines |
|-----------|-----------|
| Per-platform setup page (`claude_desktop.rst`, `cursor.rst`, etc.) | 15 |
| Homepage grid sections | 4 cards max per grid |
| "See Also" / "Related" link lists | 4 links max |
| Tutorial pages that duplicate the Python guide | 0 — delete or make a pointer |

### Less-is-more decision tree

When reviewing any piece of content, ask:

1. **Does this content exist elsewhere on the site?** → Remove it; add a cross-link to the canonical location.
2. **Is this content outdated or hard to keep current?** → Remove it; link to the upstream source (e.g., `aiscientist.tools/setup.md`).
3. **Can a user reach this information in 2 clicks from the homepage?** → If yes and the info is already there, remove this copy.
4. **Is this an emoji, decorative header, or filler sentence?** → Remove it unconditionally.
5. **Is this a "Explore More" card pointing somewhere already in the sidebar?** → Remove it.

---

## Apple-Style Simplification Rules

Apply these rules to every file touched during an audit.

**No emojis** in headings, bullet items, card titles, toctree captions, nav bar entries, or button text.

**Single setup entry point.** The canonical installation path is:
```
Read https://aiscientist.tools/setup.md and set up ToolUniverse for me.
```
Per-platform pages must contain exactly three things: (1) official install link, (2) official MCP setup guide link, (3) the setup prompt above. Nothing else — no JSON snippets, no step-by-step instructions, no troubleshooting. Those belong in the setup skill at `aiscientist.tools/setup.md`.

**Consistent tool count.** Always "1000+ tools". Never "600+", "750+", "1200+", "10000+", or any other number.

**Clean navigation bar.** Must not contain "API", "API Keys", or "Contribution" items. Must include a link to `https://aiscientist.tools` as the first item.

**Homepage "Explore More" grid.** Maximum 4 cards. Remove any card whose destination is already reachable from the sidebar or the "Get Started" section.

**No broken `:doc:` references.** Every `:doc:`some/path`` must resolve to an `.rst` or `.md` file on disk. Broken links are never acceptable — remove or replace immediately.

---

## Five-Phase Strategy

Run phases in order — **D first** (instant), then **E** (simplification scan), then C/A/B.

| Phase | What it catches | Time |
|-------|----------------|------|
| **D** Static method scan | Wrong method names (`tu.run_batch`, `tu.call_tool`, etc.) | ~2 s |
| **E** Simplification scan | Emojis, wrong counts, broken links, size violations | ~10 s |
| **C** Live code execution | Runtime failures (wrong key, bad return type) | 3-5 min |
| **A** Automated validation | Deprecated commands, term inconsistency | 15 min |
| **B** ToolUniverse audit | Circular nav, duplicate MCP configs, tool counts | 20 min |

---

## Phase D: Static Method Scan

```bash
python3 - <<'EOF'
import re, sys
from pathlib import Path
from collections import defaultdict
DOCS = Path("docs")
EXCLUDE = {"locale", "old", "_build", "__pycache__", "tools", "archive"}
KNOWN_BAD = {
    "list_tools", "run_batch", "run_async", "execute_tool", "call_tool",
    "list_tools_by_category", "configure_api_keys", "get_tool", "get_exposed_name",
    "list_available_methods", "register_tool_from_config", "register_tool",
}
STATIC = [
    (r"\.load_tools\([^)]*(?:use_cache|cache_dir)\s*=", "load_tools() invalid kwargs"),
    (r"ToolUniverse\([^)]*timeout\s*=", "ToolUniverse(timeout=) invalid"),
    (r'"name":\s*"opentarget_', 'old lowercase "opentarget_*" tool name'),
    (r"tu\.run_batch\(", "tu.run_batch() — use tu.run(list, max_workers=N)"),
    (r'\btu\.[A-Z]\w+\s*\(', "tu.ToolName() shorthand — use tu.run({name:...})"),
]
M = re.compile(r'\b(?:tu|tooluni)\.([\w]+)\s*\(')
issues = defaultdict(list)
for f in sorted(list(DOCS.rglob("*.rst")) + list(DOCS.rglob("*.md"))):
    if any(p in f.parts for p in EXCLUDE): continue
    t = f.read_text(errors="replace")
    code = "\n".join(
        re.findall(r"\.\. code-block:: python\n((?:[ \t]+[^\n]*\n|[ \t]*\n)*)", t, re.MULTILINE) +
        re.findall(r"```python\n(.*?)```", t, re.DOTALL))
    if not code.strip(): continue
    rel = str(f.relative_to(DOCS))
    for m in M.finditer(code):
        if not m.group(1).startswith("_") and m.group(1) in KNOWN_BAD:
            issues[rel].append(f"tu.{m.group(1)}()")
    for pat, label in STATIC:
        if re.search(pat, code): issues[rel].append(label)
if issues:
    [print(f"  {f}: {i}") for f in sorted(issues) for i in sorted(set(issues[f]))]
    sys.exit(1)
else:
    print("Phase D clean")
EOF
```

**Fix-or-remove rule — no exceptions:**
- Correct replacement exists → **fix immediately**
- Feature is automatic/internal → **remove the call**, add prose comment if needed
- Feature doesn't exist → **delete the code block or section entirely**

**Most common fixes:**

```python
# wrong → correct
tu.run_batch(list)              → tu.run(list, max_workers=4)
tu.run_async(query)             → await tu.run(query)
tu.call_tool('X', {...})        → tu.run({"name": "X", "arguments": {...}})
tu.execute_tool('X', {...})     → tu.run({"name": "X", "arguments": {...}})
tu.list_tools()                 → tu.list_built_in_tools(mode='list_name')
tu.get_tool('X')                → tu.get_tool_by_name('X')
tu.register_tool(instance)      → tu.register_custom_tool(tool_instance=instance)
tu.register_tool_from_config(c) → tu.register_custom_tool(tool_config=c)
tu.configure_api_keys({})       → REMOVE — use env vars
tu.get_exposed_name(name)       → REMOVE — shortening is automatic
ToolUniverse(timeout=30)        → ToolUniverse()  # no timeout kwarg
load_tools(use_cache=True)      → load_tools()  # no use_cache kwarg
tu.ToolName(key=val)            → tu.run({"name": "ToolName", "arguments": {"key": val}})
opentarget_get_*                → OpenTargets_get_*  (capital O and T)
```

**Special case:** Change `.. code-block:: python` to `.. code-block:: text` when showing intentionally-wrong code as an error example.

---

## Phase E: Simplification Scan

```bash
python3 - <<'EOF'
import re, sys
from pathlib import Path

DOCS = Path("docs")
EXCLUDE = {"_build", "__pycache__", "locale"}
issues = []

EMOJI_RE = re.compile(
    r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001FA00-\U0001FA9F'
    r'\U0001F004\U0001F0CF\U00002702-\U000027B0]'
)

def in_code_block(text, pos):
    """Return True if pos is inside a code block."""
    before = text[:pos]
    # RST code blocks
    rst_starts = [m.end() for m in re.finditer(r'\.\. code-block::[^\n]*\n', before)]
    for start in reversed(rst_starts):
        block = text[start:]
        end_match = re.search(r'\n(?![ \t]|\n)', block)
        block_end = start + (end_match.start() if end_match else len(block))
        if start <= pos <= block_end:
            return True
    # Markdown fenced blocks
    fences = list(re.finditer(r'```', before))
    return len(fences) % 2 == 1

for f in sorted(DOCS.rglob("*.rst")) + sorted(DOCS.rglob("*.md")):
    if any(p in f.parts for p in EXCLUDE):
        continue
    text = f.read_text(errors="replace")
    rel = str(f.relative_to(DOCS))

    # Check emojis in prose
    for m in EMOJI_RE.finditer(text):
        if not in_code_block(text, m.start()):
            line = text[:m.start()].count('\n') + 1
            issues.append(f"EMOJI  {rel}:{line}  {repr(m.group())}")

    # Check wrong tool counts
    for bad in ["600+", "750+", "1200+", "10000+"]:
        if bad in text and "tools" in text[text.find(bad):text.find(bad)+20]:
            issues.append(f"COUNT  {rel}  contains '{bad} tools' (use '1000+')")

    # Check broken :doc: references
    for m in re.finditer(r':doc:`([^`]+)`', text):
        ref = m.group(1).lstrip('/')
        # Strip any display text (format: display <path>)
        if ' <' in ref:
            ref = re.search(r'<([^>]+)>', ref).group(1)
        base = DOCS / Path(ref.replace('/', '/'))
        candidates = [base.with_suffix('.rst'), base.with_suffix('.md'),
                      base / 'index.rst', base / 'index.md']
        if not any(c.exists() for c in candidates):
            line = text[:m.start()].count('\n') + 1
            issues.append(f"LINK   {rel}:{line}  broken :doc:`{ref}`")

# Check navbar in conf.py
conf = Path("docs/conf.py").read_text()
for bad_nav in ['"API"', '"API Keys"', '"Contribution"']:
    if bad_nav in conf:
        issues.append(f"NAV    conf.py  navbar contains {bad_nav}")
if "aiscientist.tools" not in conf:
    issues.append("NAV    conf.py  navbar missing aiscientist.tools link")

# Check per-platform page line counts
platform_dir = DOCS / "guide" / "building_ai_scientists"
for rst in platform_dir.glob("*.rst"):
    if rst.name in ("index.rst", "mcp_support.rst", "compact_mode.rst",
                    "mcpb_introduction.rst", "mcp_name_shortening.rst"):
        continue
    lines = rst.read_text().splitlines()
    if len(lines) > 15:
        issues.append(f"SIZE   guide/building_ai_scientists/{rst.name}  {len(lines)} lines (max 15)")

if issues:
    for i in sorted(issues):
        print(i)
    sys.exit(1)
else:
    print("Phase E clean")
EOF
```

When Phase E reports issues, apply the less-is-more decision tree above. Fix all items before proceeding to Phase C.

---

## Phase C: Live Code Execution

```bash
python scripts/test_doc_code_blocks.py
```

The runner injects a real `ToolUniverse` instance as preamble, skips blocks needing API keys or async, and classifies `NameError` on out-of-scope variables as "context-dependent" (not a failure).

**Common runtime failures:**

| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 'parameters'` | `tool_specification()` without `format="openai"` | Add `format="openai"` |
| `KeyError: slice(...)` on OpenTargets result | Slicing a dict | Use `result['data']['disease']['associatedTargets']['rows'][:N]` |
| `TypeError: load_tools() got unexpected kwarg` | `use_cache` or `cache_dir` | Remove the kwarg |

---

## Phase A: Automated Validation

```bash
python scripts/validate_documentation.py
```

```python
# scripts/validate_documentation.py checks:
DEPRECATED_PATTERNS = [
    (r"python -m tooluniverse\.server", "tooluniverse-server"),
    (r"600\+?\s+tools", "1000+ tools"),
    (r"750\+?\s+tools", "1000+ tools"),
]
```

---

## Phase B: ToolUniverse-Specific Audit

**Circular navigation** — trace `index.rst → quickstart → getting_started` manually; no loops allowed.

**Tool count** — "1000+ tools" consistently everywhere. Run: `rg "[0-9]+\+?\s+(tools|integrations)" docs/ --no-filename | sort -u`

**Auto-generated headers** — `docs/tools/*_tools.rst` and `docs/api/*.rst` must start with `.. AUTO-GENERATED`.

**CLI docs** — every entry under `[project.scripts]` in `pyproject.toml` must appear in `docs/reference/cli_tools.rst`.

**Env vars** — every `os.getenv("TOOLUNIVERSE_*")` in `src/` must appear in `docs/reference/environment_variables.rst`.

---

## RST Code Block Extractor (important)

Always use `re.MULTILINE` (not `re.DOTALL`) for RST blocks to avoid merging adjacent blocks:

```python
# correct
re.findall(r"\.\. code-block:: python\n((?:[ \t]+[^\n]*\n|[ \t]*\n)*)", text, re.MULTILINE)

# wrong — merges adjacent blocks
re.findall(r"\.\..*?code-block.*?python\n((?:[ \t]+.*\n|\n)*)", text, re.DOTALL)
```

---

## Validation Checklist

All items must pass before the audit is done. A partial pass is not acceptable.

**Technical correctness:**
- [ ] Phase D scan exits 0 — no invalid method calls
- [ ] `python scripts/test_doc_code_blocks.py` exits 0 — no runtime failures
- [ ] No `spec['parameters']` without `format="openai"`
- [ ] Automated validation passes (0 HIGH issues)
- [ ] All CLIs from `pyproject.toml` documented
- [ ] No circular navigation

**Less is more (Apple-style):**
- [ ] Phase E scan exits 0 — no emojis, no wrong counts, no broken links, no oversized pages
- [ ] "1000+ tools" used consistently everywhere (not 600+, 750+, 10000+, etc.)
- [ ] Each per-platform setup page: install link + MCP guide link + setup prompt only (≤15 lines)
- [ ] No duplicate setup instructions anywhere on the site
- [ ] Navbar: no "API", "API Keys", "Contribution"; has `aiscientist.tools` link
- [ ] Homepage "Explore More" grid: ≤4 cards
- [ ] No concept or section appears verbatim in more than one place
- [ ] No "See Also" / "Related" section with more than 4 links

If any item is failing: stop, fix it, re-run the relevant phase, confirm it passes. Do not proceed to the next item until the current one is clean.

---

## Reference Files

- [API_REFERENCE.md](API_REFERENCE.md) — valid method signatures, wrong-method table, correct patterns
- [DOCS_STRUCTURE.md](DOCS_STRUCTURE.md) — per-file audit status for all doc files
- `scripts/test_doc_code_blocks.py` — Phase C live runner
