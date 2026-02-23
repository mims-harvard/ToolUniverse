---
name: devtu-docs-quality
description: TOP PRIORITY skill — find and immediately fix or remove every piece of wrong or outdated information in ToolUniverse docs. Wrong code, invalid method calls, outdated API patterns, and incorrect examples must be fixed or removed — never left in place. Runs four phases: static method-name scan, live code block execution, automated validation, and ToolUniverse-specific audit. Use when reviewing docs, before releases, after API changes, or when a user asks to audit, check, fix, or improve documentation quality.
---

# Documentation Quality Assurance

## ⚠️ TOP PRIORITY — Zero Tolerance for Wrong Information

> **Fixing wrong and outdated documentation is the single highest priority task in this skill. It overrides all other work.**

If a code example calls a method that doesn't exist, crashes at runtime, or uses a deprecated pattern:
- **Fix it immediately** if there is a correct equivalent
- **Remove it immediately** if no equivalent exists

Leaving wrong code in docs is worse than having no docs — it actively misleads users and breaks their code. When in doubt about whether something is correct, **verify it against the source** (`src/tooluniverse/execute_function.py`) before moving on.

## When to Use

- Before a release, after an API refactor, or after adding new tools
- User reports confusing or broken documentation
- Code examples might reference methods that no longer exist
- Structural problems (circular navigation, inconsistent counts) suspected

## Four-Phase Strategy

Run phases in this order — **D first** (fastest), **C second**, then A/B.

| Phase | What it catches | Time |
|-------|----------------|------|
| **D** Static method scan | Wrong method names (`tu.run_batch`, `tu.call_tool`, etc.) | ~2 s |
| **C** Live code execution | Runtime failures (wrong key, bad return type) | 3-5 min |
| **A** Automated validation | Deprecated commands, broken links, term inconsistency | 15 min |
| **B** ToolUniverse audit | Circular nav, duplicate MCP configs, tool counts | 20 min |

## Complete Audit — Run This First

```bash
# Phase D: static method-name scan (no network, instant)
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
    print("✅ Phase D clean")
EOF

# Phase C: live code block execution
python scripts/test_doc_code_blocks.py

# Phase A: structural validation
python scripts/validate_documentation.py
```

## Phase D: Fix Wrong Method Calls

When Phase D reports a file, look up the wrong call in [API_REFERENCE.md](API_REFERENCE.md) for the exact fix.

**Most common fixes:**

```python
# ❌ → ✅
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

**Fix-or-remove rule — no exceptions:**
- Correct replacement exists → **fix it immediately**
- Feature is automatic/internal → **remove the call**, add a prose comment if needed
- Feature simply doesn't exist → **delete the code block or section entirely**

Do not mark something as "TODO fix later". Fix it now or remove it now.

**Special case — error diagrams:** Change `.. code-block:: python` to `.. code-block:: text` when showing intentionally-wrong code as an error example. This prevents the scanner from flagging it.

## Phase C: Fix Runtime Failures

The live test runner is at `scripts/test_doc_code_blocks.py`. It:
- Injects a real `ToolUniverse` instance as preamble
- Skips blocks that need API keys, start servers, or use async
- Classifies `NameError` on out-of-scope variables as "context-dependent" (not a failure)

**Common runtime failures and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 'parameters'` | `tool_specification()` without `format="openai"` | Add `format="openai"` |
| `KeyError: slice(...)` on OpenTargets result | Slicing a dict | Use `result['data']['disease']['associatedTargets']['rows'][:N]` |
| `TypeError: load_tools() got unexpected kwarg` | `use_cache` or `cache_dir` | Remove the kwarg |

For full patterns, see [API_REFERENCE.md](API_REFERENCE.md).

## Phase A: Automated Validation

```python
# scripts/validate_documentation.py checks:
DEPRECATED_PATTERNS = [
    (r"python -m tooluniverse\.server", "tooluniverse-server"),
    (r"600\+?\s+tools", "1000+ tools"),
    (r"750\+?\s+tools", "1000+ tools"),
]
```

Additional checks:
```bash
# Broken :doc: references
rg ':doc:`([^`]+)`' docs/ -o | python3 -c "
import sys, re
from pathlib import Path
for line in sys.stdin:
    m = re.search(r'`([^`]+)`', line)
    if m:
        ref = m.group(1)
        if not any(Path('docs', p).exists() for p in [ref+'.rst', ref+'.md', ref+'/index.rst']):
            print('broken:', ref)
"

# Tool count consistency
rg "[0-9]+\+?\s+(tools|integrations)" docs/ --no-filename | sort -u
```

## Phase B: ToolUniverse-Specific Audit

**Circular navigation** — trace `index.rst → quickstart → getting_started` manually; no loops allowed.

**Tool count** — use "1000+ tools" consistently everywhere.

**Auto-generated headers** — `docs/tools/*_tools.rst` and `docs/api/*.rst` must start with `.. AUTO-GENERATED`.

**CLI docs** — every entry under `[project.scripts]` in `pyproject.toml` must appear in `docs/reference/cli_tools.rst`.

**Env vars** — every `os.getenv("TOOLUNIVERSE_*")` in `src/` must appear in `docs/reference/environment_variables.rst`.

## RST Code Block Extractor (important)

Always use `re.MULTILINE` (not `re.DOTALL`) for RST blocks to avoid merging adjacent blocks:

```python
# ✅ correct
re.findall(r"\.\. code-block:: python\n((?:[ \t]+[^\n]*\n|[ \t]*\n)*)", text, re.MULTILINE)

# ❌ wrong — merges adjacent blocks
re.findall(r"\.\..*?code-block.*?python\n((?:[ \t]+.*\n|\n)*)", text, re.DOTALL)
```

## Validation Checklist

All items must be ✅ before the audit is considered done. A partial pass is not acceptable.

- [ ] Phase D scan exits 0 — **no invalid method calls remain anywhere**
- [ ] `python scripts/test_doc_code_blocks.py` exits 0 — **no runtime failures remain**
- [ ] No `spec['parameters']` without `format="openai"` ([check context](API_REFERENCE.md))
- [ ] Automated validation passes (0 HIGH issues)
- [ ] "1000+ tools" used consistently
- [ ] All CLIs from `pyproject.toml` documented
- [ ] No circular navigation

If any item is failing: stop, fix it, re-run the scan, confirm it passes. Do not proceed to the next item until the current one is clean.

## Reference Files

- [API_REFERENCE.md](API_REFERENCE.md) — valid method signatures, wrong-method table, correct patterns
- [DOCS_STRUCTURE.md](DOCS_STRUCTURE.md) — per-file audit status for all 122 doc files
- `scripts/test_doc_code_blocks.py` — Phase C live runner (run directly)
