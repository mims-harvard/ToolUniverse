# Documentation Utility Scripts

This document provides a comprehensive guide to all utility scripts in the `docs/` directory.

## Quick Reference

| Script | Purpose | When to Run | CI/CD |
|--------|---------|-------------|-------|
| `generate_config_index.py` | Generate tool catalog pages | After tool config changes | ✅ Yes |
| `generate_tool_reference.py` | Generate tool reference docs | After tool config changes | ✅ Yes |
| `generate_remote_tools_docs.py` | Generate remote tool docs | After remote tool README changes | ✅ Yes |
| `quick_doc_build.sh` | Fast local documentation build | Before committing doc changes | ❌ No |
| `quick_build_zh.sh` | Fast Chinese docs build | Chinese localization work | ❌ No |
| `validate_examples.py` | Validate code examples | Before releases | ❌ Not yet |
| `doc_analytics.py` | Analyze documentation metrics | Documentation reviews | ❌ No |
| `doc_sync_tool.py` | Sync docstrings to docs | API doc updates | ❌ Not yet |
| `validate_simple.py` | (Empty file - unused) | N/A | ❌ No |

---

## Documentation Generation Scripts

### `generate_config_index.py`

**Purpose**: Generates separate RST pages for each tool configuration file.

**What it does**:
- Scans `src/tooluniverse/data/*.json` for tool configurations
- Creates individual pages in `docs/tools/` directory
- Organizes tools by source configuration file
- Generates a master index (`tools_config_index.rst`)

**When to run**:
- ✅ After adding new tool configuration files
- ✅ After modifying tool metadata (name, description, parameters)
- ✅ Before committing tool changes

**Usage**:
```bash
cd docs
python generate_config_index.py
```

**Output files**:
- `docs/tools/tools_config_index.rst` - Master catalog
- `docs/tools/*_tools.rst` - Individual config file pages

**Example**:
```bash
$ python generate_config_index.py
✅ Generated tools_config_index.rst with 42 config files
✅ Created docs/tools/uniprot_tools.rst (25 tools)
✅ Created docs/tools/pubmed_tools.rst (18 tools)
```

**CI/CD Integration**: ✅ Runs automatically in `.github/workflows/deploy-docs.yml`

---

### `generate_tool_reference.py`

**Purpose**: Generates comprehensive tool reference documentation from JSON configurations.

**What it does**:
- Scans all tool configuration files
- Extracts tool specifications (name, description, parameters, returns)
- Groups tools by category (e.g., Protein, Literature, Chemical)
- Generates detailed reference pages

**When to run**:
- ✅ After adding new tools
- ✅ After changing tool schemas
- ✅ Before major releases

**Usage**:
```bash
cd docs
python generate_tool_reference.py
```

**Output files**:
- `docs/tools/tool_reference.rst` - Comprehensive tool reference
- Individual category pages (if configured)

**CI/CD Integration**: ✅ Runs automatically in `.github/workflows/deploy-docs.yml`

---

### `generate_remote_tools_docs.py`

**Purpose**: Auto-generates documentation for remote tools by scanning their README files.

**What it does**:
- Scans `src/tooluniverse/remote/` for tool directories
- Finds README files (`.md`, `.rst`, `.txt`)
- Converts and embeds READMEs into Sphinx documentation
- Creates navigation structure for remote tools

**When to run**:
- ✅ After adding new remote tools
- ✅ After updating remote tool README files
- ✅ Before deploying documentation

**Usage**:
```bash
cd docs
python generate_remote_tools_docs.py
```

**Output files**:
- `docs/tools/remote/*.rst` - Individual remote tool pages
- `docs/tools/remote_tools_index.rst` - Remote tools index

**Example**:
```bash
$ python generate_remote_tools_docs.py
✅ Found 3 remote tools
✅ Generated docs/tools/remote/expert_feedback.rst
✅ Generated docs/tools/remote/custom_api.rst
```

**CI/CD Integration**: ✅ Runs automatically in `.github/workflows/deploy-docs.yml`

---

## Build Scripts

### `quick_doc_build.sh`

**Purpose**: Fast local documentation build for development.

**What it does**:
- Sets `DOC_OPTIMIZED=1` for minimal API doc generation
- Runs Sphinx build with warnings as errors
- Opens built HTML in browser
- Skips time-consuming full API generation

**When to run**:
- ✅ During documentation writing/editing
- ✅ Before committing documentation changes
- ✅ To preview changes locally

**Usage**:
```bash
cd docs
./quick_doc_build.sh
```

**Environment variables**:
```bash
DOC_OPTIMIZED=1  # Enable fast build mode (minimal API docs)
```

**Build time**:
- Normal build: ~3-5 minutes
- Quick build: ~30-60 seconds

**Example**:
```bash
$ ./quick_doc_build.sh
🔧 DOC_OPTIMIZED build enabled - minimal API generation
🏗️  Building documentation...
✅ Build complete! Opening in browser...
```

**Note**: Quick builds skip comprehensive API documentation generation. Always run full build (or let CI/CD do it) before releases.

---

### `quick_build_zh.sh`

**Purpose**: Fast build for Chinese localization documentation.

**What it does**:
- Builds Chinese language version of documentation
- Uses `locale/zh_CN` translation files
- Skips API generation for speed

**When to run**:
- ✅ During Chinese translation work
- ✅ To preview Chinese documentation

**Usage**:
```bash
cd docs
./quick_build_zh.sh
```

**Prerequisites**:
- `gettext` utilities installed
- Chinese `.po` translation files in `locale/zh_CN/`

---

## Validation Scripts

### `validate_examples.py`

**Purpose**: Validates Python code examples in documentation (Chinese comments).

**What it does**:
- Extracts Python code blocks from RST files
- Checks syntax validity with `ast.parse()`
- Verifies imports are available
- Reports syntax errors and unavailable imports

**When to run**:
- ✅ Before releases
- ✅ After updating code examples
- ✅ As part of pre-commit hooks (future)

**Usage**:
```bash
cd docs
python validate_examples.py
```

**Example output**:
```bash
✅ quickstart.rst: All 5 code blocks valid
❌ advanced.rst: Syntax error in block 3
   Line 12: unexpected indent
✅ All examples validated
```

**Status**: Implemented but not yet integrated into CI/CD.

**Future integration**:
```yaml
# .github/workflows/deploy-docs.yml
- name: Validate code examples
  run: |
    cd docs
    python validate_examples.py
```

---

### `validate_simple.py`

**Purpose**: Unknown (file is currently empty).

**Status**: ❌ Not implemented / unused

**Recommendation**: Remove this file or implement validation logic.

---

## Analysis Scripts

### `doc_analytics.py`

**Purpose**: Analyzes documentation quality and usage patterns (Chinese comments).

**What it does**:
- Counts words, lines, headers per page
- Tracks code blocks, links, images
- Identifies pages with missing content
- Generates analytics reports
- Suggests improvements

**When to run**:
- ✅ During quarterly documentation reviews
- ✅ To identify improvement opportunities
- ✅ For documentation health checks

**Usage**:
```bash
cd docs
python doc_analytics.py
```

**Example output**:
```json
{
  "pages": {
    "quickstart.rst": {
      "word_count": 1250,
      "code_blocks": 8,
      "external_links": 5,
      "last_modified": "2024-02-01"
    }
  },
  "recommendations": [
    "installation.rst has no code examples",
    "faq.rst has 50+ external links (consider caching)"
  ]
}
```

**Output**: `docs/analytics.json`

**Status**: Implemented but not used in CI/CD.

---

### `doc_sync_tool.py`

**Purpose**: Ensures documentation stays synchronized with source code (Chinese comments).

**What it does**:
- Extracts docstrings from Python modules
- Compares with RST documentation
- Identifies missing or outdated API docs
- Suggests documentation updates

**When to run**:
- ✅ After significant API changes
- ✅ Before major releases
- ✅ During API documentation reviews

**Usage**:
```bash
cd docs
python doc_sync_tool.py
```

**Example output**:
```bash
⚠️  API change detected in tooluniverse.core
   Method `load_tools()` signature changed
   → Update docs/api/tooluniverse.core.rst

✅ 42/45 modules in sync with docs
```

**Status**: Implemented but not yet integrated into CI/CD.

**Future integration**: Consider adding to pre-commit hooks for API changes.

---

## Configuration Files

### `conf.py`

**Purpose**: Sphinx configuration file (not a utility script).

**What it contains**:
- Sphinx extensions configuration
- Theme settings
- Path configuration
- Build options

**When to edit**:
- ✅ Adding new Sphinx extensions
- ✅ Changing theme or styling
- ✅ Modifying build behavior

**Key settings**:
```python
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_rtd_theme',
]

html_theme = 'sphinx_rtd_theme'
```

---

## Integration with CI/CD

The following scripts are integrated into `.github/workflows/deploy-docs.yml`:

```yaml
- name: Regenerate tool documentation
  run: |
    cd docs
    python generate_config_index.py
    python generate_remote_tools_docs.py
    python generate_tool_reference.py
```

**Why integrated**:
- Ensures documentation is always up-to-date with source
- Prevents stale content from being deployed
- Fails build if generation errors occur

**Not integrated** (but should be considered):
- `validate_examples.py` - Would catch broken code examples
- `doc_sync_tool.py` - Would prevent API/docs drift

---

## Best Practices

### Before Committing Documentation Changes

```bash
# 1. Regenerate auto-generated docs
cd docs
python generate_config_index.py
python generate_tool_reference.py
python generate_remote_tools_docs.py

# 2. Build and preview locally
./quick_doc_build.sh

# 3. Validate examples (optional)
python validate_examples.py

# 4. Commit both source and generated files
git add .
git commit -m "docs: update tool reference"
```

### Adding New Tools

```bash
# 1. Create tool JSON config
vim src/tooluniverse/data/my_new_tools.json

# 2. Regenerate documentation
cd docs
python generate_config_index.py
python generate_tool_reference.py

# 3. Verify output
ls docs/tools/my_new_tools.rst
grep "My_New_Tool" docs/tools/tools_config_index.rst

# 4. Build locally
./quick_doc_build.sh
```

### Major Documentation Updates

```bash
# 1. Run analytics to identify issues
cd docs
python doc_analytics.py
cat analytics.json

# 2. Check API sync status
python doc_sync_tool.py

# 3. Fix identified issues

# 4. Regenerate all auto-generated content
python generate_config_index.py
python generate_tool_reference.py
python generate_remote_tools_docs.py

# 5. Full build test
make clean
make html

# 6. Validate examples
python validate_examples.py
```

---

## Troubleshooting

### "Script fails with ModuleNotFoundError"

**Problem**: Script can't import `tooluniverse` modules.

**Solution**: Ensure you're in the correct directory and Python can find the package:

```bash
# Set PYTHONPATH
export PYTHONPATH=/path/to/ToolUniverse-main:$PYTHONPATH

# Or install in development mode
pip install -e .
```

### "Generated files not appearing"

**Problem**: Script runs but no output files created.

**Solution**: Check for errors in script output:

```bash
cd docs
python generate_config_index.py 2>&1 | tee generation.log
```

Common issues:
- JSON parsing errors in tool configs
- Missing directories (create `docs/tools/` manually)
- File permission issues

### "Documentation build fails after regeneration"

**Problem**: Sphinx build errors after running generation scripts.

**Solution**: Check generated RST syntax:

```bash
# Validate RST files
python -m sphinx.cmd.quickstart --dry-run

# Check specific file
rst2html.py docs/tools/problematic_tools.rst > /dev/null
```

---

## Adding New Utility Scripts

When creating new utility scripts, follow this template:

```python
#!/usr/bin/env python3
"""
Brief description of what this script does.

This script [detailed explanation of purpose and functionality].
"""

import sys
from pathlib import Path


def main():
    """Main entry point."""
    # Script logic here
    pass


if __name__ == "__main__":
    main()
```

**Add to this documentation**:

1. Add entry to Quick Reference table
2. Create detailed section with:
   - Purpose
   - What it does
   - When to run
   - Usage examples
   - Output description
   - CI/CD integration status

**Consider CI/CD integration** if:
- Script ensures content freshness
- Script validates correctness
- Script prevents common errors

---

## Future Improvements

### Planned Enhancements

1. **Integrate validation into CI/CD**:
   - Add `validate_examples.py` to pre-commit hooks
   - Add `doc_sync_tool.py` to API change detection

2. **Create comprehensive validation script**:
   - Check for broken internal links
   - Verify all code examples are tested
   - Ensure consistent terminology
   - Validate tool counts are up-to-date

3. **Automate analytics reporting**:
   - Generate monthly documentation health reports
   - Track documentation coverage metrics
   - Identify pages needing updates

4. **Improve error handling**:
   - Better error messages in generation scripts
   - Graceful fallbacks for missing files
   - Detailed logs for troubleshooting

---

## Contact & Questions

For questions about utility scripts:

1. Check this guide first
2. Check `DOCUMENTATION_STANDARDS.md`
3. Review script source code (all have docstrings)
4. Open GitHub issue with `[docs]` tag

---

**Last updated**: 2026-02-05  
**Maintained by**: ToolUniverse Documentation Team
