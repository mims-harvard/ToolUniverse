# DevTU GitHub CI & Testing Skill

You are an expert at debugging and fixing GitHub CI failures, test issues, and pre-commit hook problems in ToolUniverse development.

## Mission

When the user reports GitHub CI failures, test failures, or wants to push changes to GitHub:
1. **Activate pre-commit hooks** if not already active
2. **Run tests locally** to catch issues before pushing
3. **Fix test failures** systematically
4. **Ensure temp files are not pushed** to GitHub
5. **Commit and push** fixes properly

## Pre-Commit Hook Setup

### Step 1: Check if Pre-Commit is Installed
```bash
pre-commit --version
```

If not installed:
```bash
pip install pre-commit
```

### Step 2: Activate Pre-Commit Hooks
```bash
pre-commit install
```

This installs hooks that run automatically on `git commit`:
- `ruff check` - Python linting
- `ruff format` - Code formatting
- YAML/TOML validation
- Trailing whitespace removal
- End of file fixes

### Step 3: Verify Installation
```bash
ls -la .git/hooks/pre-commit
```

Should show an executable pre-commit file.

## Running Tests Locally

### Before Every Push
**CRITICAL**: Always run tests locally before pushing to avoid CI failures.

### Full Test Suite (Recommended)
```bash
python -m pytest tests/ -x --tb=short -q
```

Options:
- `-x`: Stop at first failure
- `--tb=short`: Short traceback format
- `-q`: Quiet mode (less verbose)

Expected time: ~6 minutes for full suite

### Quick Test (Specific Files)
```bash
python -m pytest tests/test_task_manager.py -v
python -m pytest tests/test_tooluniverse_cache_integration.py -v
python -m pytest tests/unit/test_run_parameters.py -v
```

### Test a Single Failing Test
```bash
python -m pytest tests/path/to/test.py::TestClass::test_method -xvs
```

## Common Test Failure Patterns

### Pattern 1: KeyError: 'role' in Message Tests

**Symptom:**
```python
KeyError: 'role'
# in code like: if msg["role"] == "tool"
```

**Root Cause:**
The test is calling `tu.run()` without `return_message=True`, so messages don't have "role" and "content" fields.

**How tu.run() Works:**
- `return_message=False` (default): Returns raw results as list
- `return_message=True`: Returns formatted messages with "role" and "content"

**Fix:**
```python
# WRONG:
messages = tu.run(batch_calls, use_cache=True)
if msg["role"] == "tool":  # ❌ KeyError!

# CORRECT:
messages = tu.run(batch_calls, use_cache=True, return_message=True)
if msg.get("role") == "tool":  # ✅ Safe access
```

**Files Affected Today:**
- `tests/test_tooluniverse_cache_integration.py`
- `tests/unit/test_run_parameters.py`

### Pattern 2: Mock Object Not Subscriptable

**Symptom:**
```python
TypeError: 'Mock' object is not subscriptable
# in code like: result["data"]["value"]
```

**Root Cause:**
The mock is returning a Mock object instead of actual data because:
1. Mock methods aren't configured properly
2. Missing `_get_tool_instance` method on mock ToolUniverse
3. Shared mock instances between tests

**Fix for Mock ToolUniverse:**
```python
@pytest.fixture
def mock_tool_universe():
    mock_tu = Mock()

    # Create SEPARATE mock tools (avoid shared state)
    mock_tool1 = Mock()
    mock_tool1.run = AsyncMock(return_value={"data": {"result": "success"}})

    mock_tool2 = Mock()
    mock_tool2.run = AsyncMock(return_value={"data": {"result": "success"}})

    # Use real dict (not mock)
    mock_tu.all_tool_dict = {"TestTool": mock_tool1, "OtherTool": mock_tool2}

    # Add _get_tool_instance method (TaskManager needs this!)
    def get_tool_instance(tool_name, cache=True):
        return mock_tu.all_tool_dict.get(tool_name)

    mock_tu._get_tool_instance = get_tool_instance

    return mock_tu
```

**Fix for Async Tool Mocks:**
```python
# WRONG:
mock_tool.run = async_function  # Direct assignment

# CORRECT:
mock_tool.run = AsyncMock(side_effect=async_function)  # Proper async mock
```

**Files Affected Today:**
- `tests/test_task_manager.py`

### Pattern 3: Linting Errors (F841, E731)

**Symptom:**
```
F841 Local variable assigned but never used
E731 Do not assign a lambda expression, use a def
```

**Common F841 Fixes:**
```python
# Unused variable
result = some_function()  # ❌ F841 if not used

# Fix 1: Use underscore
_ = some_function()  # ✅ Indicates intentionally unused

# Fix 2: Actually use it
result = some_function()
assert result is not None  # ✅ Now it's used
```

**Common E731 Fixes:**
```python
# Lambda assignment
get_value = lambda x: x * 2  # ❌ E731

# Fix: Use def
def get_value(x):  # ✅
    return x * 2
```

### Pattern 4: Temp Files Being Pushed to GitHub

**Symptom:**
```
User: "do not push temp folder into github!"
```

**Root Cause:**
Files were added to git using `git mv` before being added to .gitignore, so they're tracked even though .gitignore lists them.

**Fix:**
```bash
# 1. Remove from git tracking (keeps local files)
git rm -r --cached temp_docs_and_tests/

# 2. Verify .gitignore has the entry
grep "temp_docs_and_tests" .gitignore
# Should show: temp_docs_and_tests/

# 3. Commit the removal
git commit -m "Remove temp_docs_and_tests/ from git tracking"

# 4. Push
git push origin auto

# 5. Verify (local files exist, git doesn't track)
ls temp_docs_and_tests/ | wc -l  # Should show files
git ls-files temp_docs_and_tests/ | wc -l  # Should show 0
```

**Prevention:**
Always add folders to .gitignore BEFORE creating/moving files:
```bash
echo "temp_docs_and_tests/" >> .gitignore
git add .gitignore
git commit -m "Add temp folder to gitignore"
```

## Systematic Debugging Workflow

### Step 1: Activate Pre-Commit Hook
```bash
pre-commit install
```

### Step 2: Run Tests Locally
```bash
python -m pytest tests/ -x --tb=short -q 2>&1 | tail -50
```

**Look for:**
- `FAILED tests/...` - Which test failed
- Error message - KeyError, TypeError, AssertionError, etc.
- Line number - Where the failure occurred

### Step 3: Reproduce the Specific Failure
```bash
python -m pytest tests/path/to/test.py::TestClass::test_method -xvs
```

### Step 4: Read the Test File
```bash
# Read the failing test to understand what it's testing
cat tests/path/to/test.py | grep -A 20 "def test_method"
```

### Step 5: Apply Pattern-Based Fix
- KeyError 'role' → Add `return_message=True` and use `.get()`
- Mock not subscriptable → Fix mock configuration
- F841/E731 → Fix linting issues
- Temp files pushed → Remove from git tracking

### Step 6: Verify Fix Locally
```bash
python -m pytest tests/path/to/test.py -xvs
```

Should see: `1 passed`

### Step 7: Run Full Test Suite
```bash
python -m pytest tests/ -x --tb=short -q
```

Ensure no regressions were introduced.

### Step 8: Commit with Pre-Commit Hook
```bash
git add <fixed_files>
git commit -m "Fix test: <brief description>"
```

The pre-commit hook will run automatically and check:
- ✅ Ruff linting
- ✅ Ruff formatting
- ✅ YAML/TOML validity
- ✅ Trailing whitespace

### Step 9: Push to GitHub
```bash
git push origin auto
```

## Quick Reference Commands

### Pre-Commit
```bash
pre-commit install              # Activate hooks
pre-commit run --all-files      # Run manually on all files
pre-commit autoupdate           # Update hook versions
```

### Testing
```bash
# All tests
pytest tests/ -x --tb=short -q

# Specific test
pytest tests/test_file.py::TestClass::test_method -xvs

# With coverage
pytest tests/ --cov=src/tooluniverse --cov-report=term-missing

# Stop after N failures
pytest tests/ --maxfail=3
```

### Git
```bash
# Check what will be committed
git status --short

# Unstage files
git restore --staged <file>

# Remove from tracking but keep local
git rm --cached <file>

# Show what changed in last commit
git show HEAD

# Amend last commit (use carefully!)
git commit --amend --no-edit
```

## Common Mistakes to Avoid

### ❌ Don't: Push Without Running Tests
```bash
git add .
git commit -m "Fix"
git push  # ❌ Might fail CI!
```

### ✅ Do: Test Before Push
```bash
python -m pytest tests/ -x --tb=short -q  # Run tests first
git add <specific_files>
git commit -m "Fix test_something: add return_message=True"
git push
```

### ❌ Don't: Modify Multiple Unrelated Things
```bash
# Commit mixes test fixes with new features
git commit -m "Fix tests and add new feature"  # ❌ Hard to review
```

### ✅ Do: Commit Fixes Separately
```bash
git add tests/test_cache.py
git commit -m "Fix test_cache: add return_message=True"

git add src/feature.py
git commit -m "Add new feature X"
```

### ❌ Don't: Use `git add .` Blindly
```bash
git add .  # ❌ Might include temp files, logs, etc.
```

### ✅ Do: Add Specific Files
```bash
git add tests/test_file.py src/module.py
# Or review with: git add -p
```

## What to Push and What NOT to Push

### ✅ ALWAYS Push (Production Code)

**Source Code:**
- `src/tooluniverse/*.py` - Core library code
- `tests/*.py` - Test files
- `examples/*.py` - Example scripts
- `skills/*/` - Skill files (use `git add -f` if in .gitignore)

**Configuration:**
- `pyproject.toml` - Project configuration
- `setup.py` - Package setup
- `.pre-commit-config.yaml` - Pre-commit configuration
- `pytest.ini` - Test configuration
- `.gitignore` - Git ignore rules

**Documentation:**
- `README.md` - Main documentation
- `docs/**/*.rst` - Sphinx documentation
- `docs/**/*.md` - Markdown documentation (NOT temp docs!)
- `CHANGELOG.md` - Version history
- `LICENSE` - License file

### ❌ NEVER Push (Temporary/Local Files)

**Temp Folders:**
- `temp_docs_and_tests/` - Temporary documentation and test files
- `temp/`, `tmp/` - Any temporary directories
- `.temp/`, `._temp/` - Hidden temp directories

**Build Artifacts:**
- `build/`, `dist/` - Package build outputs
- `*.egg-info/` - Python package metadata
- `__pycache__/` - Python bytecode cache
- `*.pyc`, `*.pyo` - Compiled Python files

**IDE and Editor Files:**
- `.vscode/` - VS Code settings (usually)
- `.idea/` - PyCharm settings
- `*.swp`, `*.swo` - Vim swap files
- `.DS_Store` - macOS finder metadata

**Logs and Data:**
- `*.log` - Log files
- `*.sqlite`, `*.db` - Database files (unless example data)
- `cache/` - Cache directories
- `*.tmp` - Temporary files

**Environment Files:**
- `.env` - Environment variables (contains secrets!)
- `.env.local` - Local environment config
- `venv/`, `env/` - Virtual environments
- `.python-version` - Local Python version

**Personal Configuration:**
- `.claude/` - Claude Code configuration
- `*.local` - Personal config files

### ⚠️ MAYBE Push (Check First)

**Skills:**
- `skills/devtu-*/` - Development skills (check `.gitignore`)
- If creating new devtu skill: use `git add -f skills/devtu-skillname/`

**Data Files:**
- Small example data: ✅ Push
- Large datasets: ❌ Don't push (use Git LFS or external storage)

**Configuration:**
- `.vscode/settings.json` - Only if team shares settings
- `Makefile` - ✅ Push if used for automation

### How to Check What Will Be Pushed

**Before committing:**
```bash
# See what files are staged
git status --short

# See detailed diff of what will be committed
git diff --cached

# Check if a file is ignored
git check-ignore -v filename
```

**After committing, before pushing:**
```bash
# See what commits will be pushed
git log origin/auto..HEAD

# See files changed in commits that will be pushed
git diff origin/auto..HEAD --name-status
```

### Emergency: Accidentally Staged Wrong Files

**Unstage specific file:**
```bash
git restore --staged filename
```

**Unstage all files:**
```bash
git restore --staged .
```

**Undo last commit (keeps changes):**
```bash
git reset --soft HEAD~1
```

**Remove file from git but keep local:**
```bash
git rm --cached filename
```

### Verifying .gitignore Works

**Check if files are ignored:**
```bash
# Check specific file
git check-ignore -v temp_docs_and_tests/somefile.md

# Should output the .gitignore rule that matches
# Example: .gitignore:152:temp_docs_and_tests/
```

**List all tracked files (should NOT include temp):**
```bash
git ls-files | grep temp_docs_and_tests
# Should return nothing (0 lines)
```

**List all ignored files:**
```bash
git status --ignored
```

## Success Checklist

Before pushing to GitHub, ensure:

- [ ] Pre-commit hook is installed (`pre-commit install`)
- [ ] All tests pass locally (`pytest tests/ -x`)
- [ ] No linting errors (pre-commit runs on commit)
- [ ] Temp files are in .gitignore and not tracked
- [ ] Commit message is clear and descriptive
- [ ] Only relevant files are committed (not temp/logs)
- [ ] Changes are on the correct branch

## Example Session

### User: "GitHub CI is failing with test errors"

**Your Response:**

```
I'll help you fix the CI failures. Let me follow the systematic approach:

**Step 1: Activate pre-commit hooks**
```bash
pre-commit install
```

**Step 2: Run tests locally to identify failures**
```bash
python -m pytest tests/ -x --tb=short -q 2>&1 | tail -50
```

*[Wait for results and analyze the failure pattern]*

**Step 3: Fix the specific failure**
*[Apply pattern-based fix - e.g., add return_message=True for KeyError 'role']*

**Step 4: Verify the fix**
```bash
python -m pytest tests/test_file.py -xvs
```

**Step 5: Run full test suite**
```bash
python -m pytest tests/ -x --tb=short -q
```

**Step 6: Commit and push**
```bash
git add tests/test_file.py
git commit -m "Fix test: add return_message=True"
git push origin auto
```

All tests should now pass in CI! ✅
```

## Files Changed Today (Real Examples)

### Commit 1: fca22e2 - Fix test_task_manager.py
**Issue:** Mock not subscriptable
**Fix:**
- Create separate mock tool instances
- Add `_get_tool_instance` method
- Use `AsyncMock(side_effect=...)` for async tools

### Commit 2: 890cb11 - Fix test_tooluniverse_cache_integration.py
**Issue:** KeyError: 'role'
**Fix:**
- Add `return_message=True`
- Change `msg["role"]` to `msg.get("role")`

### Commit 3: f775c6f - Fix test_run_parameters.py
**Issue:** KeyError: 'role' in batch test
**Fix:**
- Add `return_message=True`
- Use `.get()` for safe access

### Commit 4: 1d9222a - Remove temp_docs_and_tests/
**Issue:** Temp folder being pushed to GitHub
**Fix:**
- `git rm -r --cached temp_docs_and_tests/`
- Commit removal (keeps local files)

## Memory Markers

**When you see these patterns:**
- `KeyError: 'role'` → Missing `return_message=True`
- `Mock object is not subscriptable` → Fix mock configuration
- `F841` or `E731` → Linting errors to fix
- User says "don't push temp folder" → Check `git ls-files` and remove from tracking

**Always remember:**
1. Pre-commit hook MUST be active
2. Test locally BEFORE pushing
3. Fix one test at a time
4. Verify full suite before pushing
5. Check that temp files aren't tracked

## End of Instructions

Follow this systematic approach every time there are CI failures or test issues. The patterns are proven to work - we fixed 40 tests today using these exact techniques!
