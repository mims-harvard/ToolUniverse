# Skill Quality Checklists

## Skill Review Checklist

### Tool Contract
- [ ] Tool parameters verified via `get_tool_info()` or documented corrections
- [ ] Versioned vs unversioned ID handling specified
- [ ] Foundation data source identified (if available for domain)

### Report Quality
- [ ] Report focuses on content, not search process
- [ ] Methodology in separate appendix (optional)
- [ ] Evidence grades applied to claims (T1-T4)
- [ ] Source attribution on every fact
- [ ] Sections exist even if "limited evidence"

### Query Strategy
- [ ] Disambiguation phase before search
- [ ] Collision detection for ambiguous names
- [ ] High-precision seeds before broad search
- [ ] Citation expansion for sparse topics
- [ ] Negative filters documented

### Tool Usage
- [ ] Annotation tools used (not just literature)
- [ ] Fallback chains defined
- [ ] Failure handling with retry
- [ ] OA handling (full or best-effort)

### Completeness
- [ ] Quantified minimums defined per section
- [ ] Completeness checklist with checkboxes
- [ ] Data Gaps section aggregates all missing data
- [ ] "Negative results" explicitly documented

### Output Structure
- [ ] Main report is narrative-focused
- [ ] Bibliography in separate JSON/CSV
- [ ] Synthesis sections required

## Implementation & Testing (2026-02 Standards)
- [ ] All tool calls tested in real ToolUniverse instance (MANDATORY)
- [ ] Test script with >=30 tests
- [ ] 100% test pass rate
- [ ] All tests use real data (no placeholders)
- [ ] Edge cases: empty, large, invalid, boundary
- [ ] Phase-level + integration + cross-example tests
- [ ] SOAP tools have `operation` parameter (if applicable)
- [ ] Fallback strategies implemented and tested
- [ ] API quirks documented

## Documentation (2026-02 Standards)
- [ ] SKILL.md is implementation-agnostic (no Python/MCP code)
- [ ] Working python_implementation.py
- [ ] QUICK_START.md with both SDK and MCP examples
- [ ] TOOLS_REFERENCE.md with verified parameters
- [ ] All code examples actually work (copy-paste ready)

## Pre-Release Final Check
```bash
# 1. Run test suite
python test_*.py  # Expect 100% pass

# 2. Check for placeholders
grep -r "TEST\|DUMMY\|PLACEHOLDER" *.md *.py  # Should find none

# 3. Performance benchmark
time python test_*.py  # Document time

# 4. Edge case coverage
grep "def test_edge" test_*.py  # Should have 5+
```
