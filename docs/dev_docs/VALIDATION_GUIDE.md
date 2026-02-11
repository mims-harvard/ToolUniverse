# Documentation Validation Guide

This guide explains how to use the documentation validation system to ensure documentation quality before committing changes.

## Overview

The validation system includes:

1. **Pre-commit hook** (`.githooks/pre-commit-docs`) - Automatic validation on git commit
2. **Manual validation** - Scripts you can run independently
3. **CI/CD validation** - Automatic checks on pull requests

## Quick Start

### Enable Pre-Commit Hook

```bash
# One-time setup
./setup_precommit.sh

# Or manually
git config core.hooksPath .githooks
```

### Run Validation Manually

```bash
# Validate documentation changes
./.githooks/pre-commit-docs

# Or run specific validation scripts
cd docs
python validate_examples.py  # Validate code examples
python doc_sync_tool.py      # Check API/docs sync
```

## Pre-Commit Hook Features

The `.githooks/pre-commit-docs` hook automatically checks:

### 1. RST Syntax Validation

**What it checks:**
- Title/underline length mismatches
- Common reStructuredText syntax errors

**Example issue:**
```rst
My Title
========  <-- ❌ Wrong length (9 chars vs 8)

My Title
========  <-- ✅ Correct (8 chars = 8)
```

**How to fix:**
```bash
# The hook will show you the mismatch:
⚠️  Line 42: Title/underline length mismatch in docs/quickstart.rst
   Title: 'My Title' (length: 8)
   Underline: '=========' (length: 9)

# Fix by matching lengths exactly
```

### 2. Broken Internal References

**What it checks:**
- `:doc:` references to non-existent files
- Missing cross-reference targets

**Example issue:**
```rst
See :doc:`installation` for details.  <-- ✅ OK (file exists)
See :doc:`setup_guide` for details.   <-- ❌ File not found
```

**How to fix:**
```rst
# Use correct path
See :doc:`installation` for details.

# Or use relative paths
See :doc:`../guide/installation` for details.

# Or use explicit labels
.. _my-label:

See :ref:`my-label` for details.
```

### 3. TODO/FIXME Markers

**What it checks:**
- Uncommitted TODO/FIXME comments in documentation

**Example:**
```rst
.. TODO: Update this section  <-- ⚠️ Warning
.. FIXME: Broken link          <-- ⚠️ Warning
```

**Why it matters:**
- Documentation should be complete before committing
- TODO markers indicate unfinished work

**How to fix:**
```bash
# Either complete the TODOs:
# "Update this section" → Actually update it

# Or create GitHub issues:
# Convert TODO to tracked issue
# Remove TODO from docs
```

### 4. Long Lines

**What it checks:**
- Lines longer than 120 characters (excluding code blocks and URLs)

**Why it matters:**
- Improves readability
- Better diffs in version control

**How to fix:**
```rst
# ❌ Bad: Long line
This is a very long line that goes on and on and on and contains too much information on a single line making it hard to read.

# ✅ Good: Broken into multiple lines
This is a long line that has been broken into multiple shorter lines,
making it much easier to read and maintain in version control.
```

### 5. Auto-Generated Files

**What it checks:**
- Manual edits to files in `docs/tools/` and `docs/api/`

**Example warning:**
```
⚠️  Warning: You are modifying auto-generated files:
  - docs/tools/uniprot_tools.rst
  - docs/api/tooluniverse.core.rst
```

**How to fix:**
```bash
# Don't edit these files directly!
# Instead, edit source files and regenerate:

# For tool documentation
cd docs
python generate_config_index.py
python generate_tool_reference.py

# For API documentation
# Edit Python docstrings in src/tooluniverse/
cd docs
sphinx-apidoc -f -o api ../src/tooluniverse
```

### 6. Tool Count Consistency

**What it checks:**
- Inconsistent tool counts across documentation (e.g., "600 tools" vs "750 tools")

**Standard:** Use `1000+ tools` consistently

**How to fix:**
```bash
# Search for tool count mentions
grep -r "tools" docs/ --include="*.rst" | grep -E "[0-9]+"

# Update to standard format
sed -i 's/600+ tools/1000+ tools/g' docs/quickstart.rst
sed -i 's/750 tools/1000+ tools/g' docs/index.rst
```

## Manual Validation Scripts

### validate_examples.py

**Purpose:** Validates Python code examples in documentation

```bash
cd docs
python validate_examples.py
```

**What it checks:**
- Python syntax errors
- Import availability
- Common code issues

**Example output:**
```bash
✅ quickstart.rst: All 5 code blocks valid
❌ advanced.rst: Syntax error in block 3
   Line 12: unexpected indent
```

### doc_sync_tool.py

**Purpose:** Ensures documentation matches source code

```bash
cd docs
python doc_sync_tool.py
```

**What it checks:**
- Docstring/documentation sync
- API signature changes
- Missing documentation

**Example output:**
```bash
⚠️  API change detected in tooluniverse.core
   Method `load_tools()` signature changed
   → Update docs/api/tooluniverse.core.rst
```

### doc_analytics.py

**Purpose:** Analyzes documentation quality metrics

```bash
cd docs
python doc_analytics.py
```

**What it provides:**
- Page statistics (word count, code blocks, links)
- Quality recommendations
- Coverage analysis

## Validation Workflow

### Before Committing

```bash
# 1. Make documentation changes
vim docs/quickstart.rst

# 2. Regenerate auto-generated content if needed
cd docs
python generate_config_index.py
python generate_tool_reference.py

# 3. Build locally to test
./quick_doc_build.sh

# 4. Run validation (automatic on commit)
git add docs/quickstart.rst
git commit -m "docs: update quickstart"  # Validation runs automatically

# If validation fails, fix issues and try again
```

### Dealing with Warnings

Warnings **won't block** your commit, but you should fix them:

```bash
# Commit with warnings (allowed but not recommended)
git commit -m "docs: update quickstart"
⚠️  Validation completed with 2 warning(s)
You can still commit, but consider fixing these issues

# Fix warnings and amend commit
vim docs/quickstart.rst  # Fix issues
git add docs/quickstart.rst
git commit --amend --no-edit
```

### Dealing with Errors

Errors **will block** your commit:

```bash
git commit -m "docs: update quickstart"
❌ Validation failed with 1 error(s)

# Fix the error
vim docs/quickstart.rst
git add docs/quickstart.rst
git commit -m "docs: update quickstart"
✅ Documentation validation passed!
```

## CI/CD Validation

GitHub Actions automatically validates documentation on pull requests:

```yaml
# .github/workflows/deploy-docs.yml
- name: Validate documentation
  run: |
    ./.githooks/pre-commit-docs
```

**What happens:**
- ✅ Validation passes → PR can be merged
- ❌ Validation fails → PR blocked until fixed
- ⚠️  Warnings → PR can be merged but review recommended

## Common Issues & Solutions

### Issue: "Title/underline length mismatch"

**Cause:** RST heading underline doesn't match title length

**Solution:**
```rst
# Count characters carefully
Installation Guide
==================  (18 characters = 18 equals signs)
```

**Tip:** Use an editor with column indicators or run:
```bash
echo "My Title" | wc -c  # Get exact length
```

### Issue: "Possibly broken reference"

**Cause:** `:doc:` or `:ref:` points to non-existent file

**Solution:**
```rst
# Check if file exists
ls docs/installation.rst

# Use correct path
:doc:`installation`          # For docs/installation.rst
:doc:`guide/loading_tools`   # For docs/guide/loading_tools.rst

# Or use explicit references
.. _my-section:

Some content here

Reference it: :ref:`my-section`
```

### Issue: "Modifying auto-generated files"

**Cause:** Editing files in `docs/tools/` or `docs/api/` directly

**Solution:**
```bash
# Don't edit generated files!
# Edit source instead:

# For tool docs:
vim src/tooluniverse/data/uniprot_tools.json
cd docs && python generate_config_index.py

# For API docs:
vim src/tooluniverse/core_tool.py  # Edit docstrings
cd docs && sphinx-apidoc -f -o api ../src/tooluniverse
```

### Issue: "Inconsistent tool counts"

**Cause:** Different tool counts mentioned across docs

**Solution:**
```bash
# Use standard format everywhere
grep -r "[0-9]\+ tools" docs/ --include="*.rst"

# Replace with "1000+ tools"
# See DOCUMENTATION_STANDARDS.md for details
```

## Bypassing Validation (Not Recommended)

In rare cases, you may need to bypass validation:

```bash
# Skip pre-commit hooks (not recommended)
git commit --no-verify -m "docs: emergency fix"
```

**When to bypass:**
- Emergency hotfixes
- False positives in validation
- Documented exceptions

**Always:**
- Document why you bypassed validation in commit message
- Create follow-up issue to fix properly
- Get code review before merging

## Best Practices

### 1. Validate Early and Often

```bash
# Don't wait until commit time
# Validate as you write

# After making changes
./quick_doc_build.sh  # Build and check
./.githooks/pre-commit-docs  # Validate
```

### 2. Fix Warnings Proactively

```bash
# Don't accumulate warnings
# Fix them immediately

# Each warning is a small issue
# Small issues → big problems
```

### 3. Use Auto-Generated Headers

All auto-generated files **must** include header:

```rst
.. AUTO-GENERATED - DO NOT EDIT MANUALLY
.. Generated by: docs/generate_config_index.py
.. Last updated: 2026-02-05 10:30:00
.. 
.. To modify, edit source files and regenerate.
```

This is now automatically added by generation scripts.

### 4. Keep Documentation in Sync

```bash
# When changing code, update docs
git diff src/tooluniverse/core_tool.py  # Changed code
# → Also update docs/api/ or relevant guides

# Use doc_sync_tool.py to check
python docs/doc_sync_tool.py
```

### 5. Test Code Examples

```bash
# All code examples should work
# Test them regularly

cd docs
python validate_examples.py

# Or run examples manually
python -c "$(sed -n '/.. code-block:: python/,/^$/p' quickstart.rst | tail -n +3)"
```

## Troubleshooting

### Hook not running

```bash
# Check hook path configuration
git config --get core.hooksPath
# Should be: .githooks

# Reconfigure if needed
git config core.hooksPath .githooks

# Make hook executable
chmod +x .githooks/pre-commit-docs
```

### Validation script errors

```bash
# Check Python environment
python --version  # Should be 3.8+

# Install dependencies
pip install sphinx sphinx-rtd-theme

# Check script permissions
ls -la docs/*.py
chmod +x docs/*.py  # If needed
```

### False positives

```bash
# Report false positives as issues
# Include:
# - File being validated
# - Warning/error message
# - Why it's a false positive

# Example:
# File: docs/advanced.rst
# Warning: "Broken reference :doc:`custom_page`"
# Reason: custom_page.rst exists but validation doesn't find it
```

## Contributing

Want to improve validation? See:

- `.githooks/pre-commit-docs` - Main validation script
- `docs/validate_examples.py` - Code example validator
- `docs/doc_sync_tool.py` - API/docs sync checker
- `docs/DOCUMENTATION_STANDARDS.md` - Documentation standards

## Additional Resources

- [Documentation Standards Guide](DOCUMENTATION_STANDARDS.md)
- [Utility Scripts Guide](UTILITY_SCRIPTS.md)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [reStructuredText Primer](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)

---

**Last updated**: 2026-02-05  
**Maintained by**: ToolUniverse Documentation Team
