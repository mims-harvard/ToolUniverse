---
name: devtu-github
description: GitHub workflow for ToolUniverse - push code safely by moving temp files, activating pre-commit hooks, running tests, and cleaning staged files. Use when pushing to GitHub, fixing CI failures, or cleaning up before commits.
---

# DevTU GitHub Workflow

Safely push ToolUniverse code to GitHub by enforcing pre-push cleanup, pre-commit hooks, and test validation.

## Instructions

When the user wants to push code, fix CI, or prepare a commit, follow this workflow:

### Phase 1: Pre-Push Cleanup

1. **Move temp files out of root** - session docs and ad-hoc test scripts must NOT be pushed:

```bash
# Move session markdown files to temp_docs_and_tests/
for f in $(ls *.md 2>/dev/null | grep -v README.md | grep -v CHANGELOG.md | grep -v LICENSE.md); do
  mv "$f" temp_docs_and_tests/
done

# Move root-level test scripts to temp_docs_and_tests/
for f in $(ls test_*.py 2>/dev/null); do
  mv "$f" temp_docs_and_tests/
done
```

2. **Verify nothing unwanted is staged**:

```bash
git status --short
```

**Red flags** - these should NEVER be staged:
- `*_SUMMARY.md`, `*_REPORT.md`, `SESSION_*.md` in root
- `test_*.py` in root (these are ad-hoc scripts, not real tests)
- `.env` or credential files
- `temp_docs_and_tests/` contents

### Phase 2: Activate Pre-Commit Hooks

3. **Ensure pre-commit is installed and active**:

```bash
pre-commit install
```

This enables automatic checks on every `git commit`:
- `ruff check --fix` - Python linting with auto-fix
- `ruff format` - Code formatting
- YAML/TOML validation
- Trailing whitespace removal
- End of file fixes

4. **Verify hooks are active**:

```bash
ls -la .git/hooks/pre-commit
```

### Phase 3: Run Tests

5. **Run the full test suite locally**:

```bash
python -m pytest tests/ -x --tb=short -q
```

6. **If tests fail**, diagnose using the error patterns below and fix before proceeding.

### Phase 4: Commit and Push

7. **Stage only specific files** (never use `git add .` or `git add -A`):

```bash
git add src/tooluniverse/specific_file.py tests/specific_test.py
```

8. **Commit** (pre-commit hooks run automatically):

```bash
git commit -m "Clear, descriptive message"
```

9. **Rebase onto latest main BEFORE pushing** (CRITICAL — prevents PR conflicts):

```bash
git fetch origin
git stash            # stash any uncommitted work
git rebase origin/main
git stash pop        # restore uncommitted work
```

If rebase conflicts arise, resolve them (keep our newer changes), then:
```bash
git add <conflicted-file>
git rebase --continue
```

10. **Push** (force-with-lease after a rebase):

```bash
git push --force-with-lease origin <branch-name>
```

After pushing, verify the PR is conflict-free:
```bash
gh pr view <PR-number> --json mergeable,mergeStateStatus
# Must show: "mergeable":"MERGEABLE"
```

## Files That Must NEVER Be Pushed

### Temp Session Documents (Root-Level .md)

These are session notes created during development. Move to `temp_docs_and_tests/` before committing:

| Pattern | Example |
|---------|---------|
| `*_SUMMARY.md` | `API_DISCOVERY_SESSION_SUMMARY.md` |
| `*_REPORT.md` | `SKILL_TESTING_REPORT.md`, `TOOLUNIVERSE_BUG_REPORT.md` |
| `SESSION_*.md` | `SESSION_2026_02_13.md` |
| `IMPLEMENTATION_*.md` | `IMPLEMENTATION_COMPLETE.md` |
| `BUG_ANALYSIS_*.md` | `BUG_ANALYSIS_DETAILED.md` |
| `FIX_*.md` | `FIX_SUMMARY.md`, `CORRECT_FIX.md` |
| `AGENT_*.md` | `AGENT_DESIGN_UPDATES.md` |

**Exception**: `README.md`, `CHANGELOG.md`, `LICENSE.md` are real docs and MUST stay.

### Root-Level Test Scripts

Ad-hoc test scripts like `test_*.py` in root are NOT part of the test suite (`tests/` directory is). Move them to `temp_docs_and_tests/`:

| File | Purpose |
|------|---------|
| `test_clear_tools.py` | One-off tool cleanup test |
| `test_finemapping_tools.py` | Ad-hoc tool validation |
| `test_metabolomics_tools.py` | Ad-hoc tool validation |
| `test_original_bug.py` | Bug reproduction |
| `test_pathway_tools.py` | Ad-hoc tool validation |
| `test_protein_interaction_skill.py` | Skill test |
| `test_reload_fix.py` | Bug reproduction |
| `test_round10_tools.py` | Ad-hoc tool validation |

### Other Excluded Files

- `.env` - Environment variables with secrets
- `temp_docs_and_tests/` - Already in .gitignore
- `.claude/` - Claude Code configuration
- `__pycache__/`, `*.pyc` - Python bytecode
- `.DS_Store` - macOS metadata

## Common Test Failure Patterns

### Pattern 1: KeyError: 'role'

**Symptom**: `KeyError: 'role'` when accessing message dicts

**Fix**: Add `return_message=True` to `tu.run()` and use `.get()`:
```python
messages = tu.run(calls, use_cache=True, return_message=True)
if msg.get("role") == "tool":
```

### Pattern 2: Mock Not Subscriptable

**Symptom**: `TypeError: 'Mock' object is not subscriptable`

**Fix**: Use real dicts for `all_tool_dict` and add `_get_tool_instance`:
```python
mock_tu.all_tool_dict = {"Tool": mock_tool}
mock_tu._get_tool_instance = lambda name, cache=True: mock_tu.all_tool_dict.get(name)
```

### Pattern 3: Linting Errors (F841, E731)

**Fix F841** (unused variable): Use `_` prefix or `_ = func()`
**Fix E731** (lambda assignment): Replace with `def`

### Pattern 4: Temp Files Tracked by Git

**Symptom**: `git status` shows temp files as modified/staged

**Fix**:
```bash
git rm -r --cached temp_docs_and_tests/
git rm --cached API_DISCOVERY_SESSION_SUMMARY.md
git commit -m "Remove temp files from tracking"
```

## Pre-Commit Hook Configuration

The project uses `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks: [end-of-file-fixer, trailing-whitespace, check-yaml, check-toml]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks: [ruff-check --fix, ruff-format]
```

Scope: Only files matching `^(ToolUniverse/)?src/tooluniverse/`

## Quick Reference

| Task | Command |
|------|---------|
| Activate hooks | `pre-commit install` |
| Run all tests | `pytest tests/ -x --tb=short -q` |
| Run specific test | `pytest tests/path/test.py::Class::method -xvs` |
| Check staged files | `git status --short` |
| Unstage a file | `git restore --staged <file>` |
| Remove from tracking | `git rm --cached <file>` |
| Move temp files | See Phase 1 commands |
| Run hooks manually | `pre-commit run --all-files` |

## Pre-Push Checklist

Before every push, verify:

- [ ] Temp markdown files moved from root to `temp_docs_and_tests/`
- [ ] Root-level `test_*.py` scripts moved to `temp_docs_and_tests/`
- [ ] Pre-commit hooks installed (`pre-commit install`)
- [ ] All tests pass locally (`pytest tests/ -x`)
- [ ] No linting errors
- [ ] Only relevant files staged (no `.env`, no temp files)
- [ ] Commit message is clear and descriptive
- [ ] Correct branch selected

## Git Commit Guidelines

- Never include AI attribution in commits
- Never commit session documentation markdown files
- Use `git add <specific-files>` instead of `git add .`
- Write clean, professional commit messages
- One logical change per commit
