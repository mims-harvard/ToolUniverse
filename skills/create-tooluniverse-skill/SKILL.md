---
name: create-tooluniverse-skill
description: Create high-quality ToolUniverse skills following test-driven, implementation-agnostic methodology. Integrates tools from ToolUniverse's 1,264+ tool library, creates missing tools when needed, tests thoroughly, and produces skills with Python SDK + MCP support.
---

# Create ToolUniverse Skill

Systematic workflow for creating production-ready ToolUniverse skills.

## Core Principles

Build on the 10 pillars from `devtu-optimize-skills`:
1. TEST FIRST - never document untested tools
2. Verify tool contracts - don't trust function names
3. Handle SOAP tools - add `operation` parameter
4. Implementation-agnostic docs - no Python/MCP code in SKILL.md
5. Foundation first - query aggregators before specialized tools
6. Disambiguate carefully - resolve IDs properly
7. Implement fallbacks - Primary -> Fallback -> Default
8. Grade evidence - T1-T4 tiers on claims
9. Quantified completeness - numeric minimums per section
10. Synthesize - models and hypotheses, not just lists

See `OPTIMIZE_INTEGRATION.md` for detailed application of each pillar.

## 7-Phase Workflow

| Phase | Duration | Description |
|-------|----------|-------------|
| 1. Domain Analysis | 15 min | Understand use cases, data types, analysis phases |
| 2. Tool Discovery | 30-45 min | Search, read configs, test tools (MANDATORY) |
| 3. Tool Creation | 0-60 min | Create missing tools via devtu-create-tool |
| 4. Implementation | 30-45 min | Write python_implementation.py with tested tools |
| 5. Documentation | 30-45 min | Write SKILL.md (agnostic) + QUICK_START.md |
| 6. Validation | 15-30 min | Run test suite, validate checklist, manual verify |
| 7. Packaging | 15 min | Create summary, update tracking |

**Total**: ~1.5-2 hours (without tool creation).

### Phase 1: Domain Analysis

- Gather concrete use cases and expected outputs
- Identify inputs, outputs, and intermediate data types
- Break workflow into logical phases
- Review existing skills in `skills/` for patterns

### Phase 2: Tool Discovery and Testing

Search tools in `/src/tooluniverse/data/*.json` (186 tool files). For each tool, read its config to understand parameters and return schema. See `PARAMETER_VERIFICATION.md` for common pitfalls.

**Create and run a test script** using `test_tools_template.py`. For each tool: call with known-good params, verify response format, document corrections. See `TESTING_GUIDE.md` for the full test suite template and procedures.

### Phase 3: Tool Creation (If Needed)

Invoke `devtu-create-tool` when required functionality is missing and analysis is blocked. Use `devtu-fix-tool` if new tools fail tests.

### Phase 4: Implementation

Create `skills/tooluniverse-[domain]/` with:
- `python_implementation.py` - use only tested tools, try/except per phase, progressive report writing
- `test_skill.py` - test each input type, combined inputs, error handling

Use templates from `CODE_TEMPLATES.md`.

### Phase 5: Documentation

Write implementation-agnostic SKILL.md using `SKILL_TEMPLATE.md`. Write multi-implementation QUICK_START.md using `QUICKSTART_TEMPLATE.md`. Key rules: zero Python/MCP code in SKILL.md, equal treatment of both interfaces in QUICK_START.

See `IMPLEMENTATION_AGNOSTIC.md` for format guidelines with examples.

### Phase 6: Validation

Run the comprehensive test suite (see `TESTING_GUIDE.md`). Validate against `VALIDATION_CHECKLIST.md`. Perform manual verification: load ToolUniverse fresh, copy-paste QUICK_START example, verify output works.

### Phase 7: Packaging

Create summary document using `PACKAGING_TEMPLATE.md`. Update session tracking if creating multiple skills.

## Skill Integration

| Skill | When to Use |
|-------|-------------|
| **devtu-create-tool** | Critical functionality missing |
| **devtu-fix-tool** | Tool returns errors or unexpected format |
| **devtu-optimize-skills** | Evidence grading, report optimization |

## Quality Indicators

**High quality**: 100% test coverage before docs, agnostic SKILL.md, multi-implementation QUICK_START, fallback strategies, parameter corrections table, response format docs.

**Red flags**: Docs before testing, Python in SKILL.md, assumed parameters, no fallbacks, SOAP tools missing `operation`, no test script.

## Reference Files

| File | Content |
|------|---------|
| `SKILL_TEMPLATE.md` | Template for writing SKILL.md |
| `QUICKSTART_TEMPLATE.md` | Template for writing QUICK_START.md |
| `TESTING_GUIDE.md` | Test suite template and procedures |
| `VALIDATION_CHECKLIST.md` | Pre-release quality checklist |
| `PACKAGING_TEMPLATE.md` | Summary document template |
| `PARAMETER_VERIFICATION.md` | Tool parameter verification guide |
| `OPTIMIZE_INTEGRATION.md` | devtu-optimize-skills 10-pillar integration |
| `IMPLEMENTATION_AGNOSTIC.md` | Implementation-agnostic format guide with examples |
| `CODE_TEMPLATES.md` | Python implementation and test templates |
| `test_tools_template.py` | Tool testing script template |
