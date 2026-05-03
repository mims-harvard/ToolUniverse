---
name: devtu-code-optimization
description: >
  Code quality patterns and guidelines for ToolUniverse tool development.
  Apply when writing, fixing, or refactoring tool Python code in the ToolUniverse project.
  Encodes lessons from 80+ debug rounds. Use alongside devtu-fix-tool and devtu-self-evolve.
  Triggers: implementing tool fixes, writing new tool classes, reviewing tool code quality,
  checking schema correctness, looking up API-specific bug fixes.
---

# ToolUniverse Code Optimization

Always run `Skill(skill="simplify")` after writing or modifying code.

## Pre-Commit Checklist

- [ ] `return_schema` has `oneOf: [{data+metadata}, {error}]`
- [ ] Test examples use real IDs (no DUMMY/PLACEHOLDER)
- [ ] `try:` has `except:` at exact same indentation level
- [ ] No trailing commas in JSON (`python3 -c "import json; json.load(open('f.json'))"`)
- [ ] New tool class registered in `_lazy_registry_static.py` and `default_config.py`
- [ ] `ruff check src/tooluniverse/<file>.py` passes
- [ ] `python -c "from tooluniverse.<module> import <Class>"` passes
- [ ] `python -m tooluniverse.cli run <Tool> '<real_args_json>'` returns expected data
- [ ] Ran `Skill(skill="simplify")` on all modified files

## Key Fix Categories

| Category | Signal | Reference |
|---|---|---|
| Silent param ignored | API accepts but drops filter | [code-patterns.md](code-patterns.md) — Client-Side Filter |
| Wrong API field/endpoint | 0 results or 404 | [api-fixes.md](api-fixes.md) — Quick Lookup Table |
| Schema invalid | null type, missing oneOf | [code-patterns.md](code-patterns.md) — Schema Patterns |
| Undisclosed normalization | Auto-transform hidden from user | [code-patterns.md](code-patterns.md) — Normalization Disclosure |
| try/except indent | SyntaxError at runtime | [code-patterns.md](code-patterns.md) — try/except section |
| Truncation buried | Data count hidden in notes | [code-patterns.md](code-patterns.md) — Truncation |

## References

- **[references/api-fixes.md](references/api-fixes.md)** — Per-API bug fixes (GtoPdb, CIViC, GTEx, ENCODE, CPIC, etc.)
- **[references/code-patterns.md](references/code-patterns.md)** — Reusable Python patterns (schema, filtering, pagination, normalization)

## Git & PR Workflow

```bash
git fetch origin && git stash && git rebase origin/main && git stash pop
git push --force-with-lease origin fix/round-XX-bugs
gh pr view <N> --json mergeable  # must be MERGEABLE before done
```

- Never push to `main` directly
- Never have multiple open fix PRs
- Commit messages: "Feature" or "Fix" — never "Bug"
- No AI attribution in commits
- Repo: `mims-harvard/ToolUniverse` — verify with `git remote -v`
