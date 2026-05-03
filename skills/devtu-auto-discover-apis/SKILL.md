---
name: devtu-auto-discover-apis
description: Automatically discover life science APIs online, create ToolUniverse tools, validate them, and prepare integration PRs. Performs gap analysis to identify missing tool categories, web searches for APIs, automated tool creation using devtu-create-tool patterns, validation with devtu-fix-tool, and git workflow management. Use when expanding ToolUniverse coverage, adding new API integrations, or systematically discovering scientific resources.
---

# Automated Life Science API Discovery & Tool Creation

Discover, create, validate, and integrate life science APIs into ToolUniverse.

## Four-Phase Workflow

```
Gap Analysis → API Discovery → Tool Creation → Validation → Integration
     ↓              ↓               ↓              ↓            ↓
  Coverage      Web Search      devtu-create   devtu-fix    Git PR
```

Human approval gates after: discovery, creation, validation, and before PR.

---

## Phase 1: Discovery & Gap Analysis

### 1.1 Analyze Current Coverage
Load ToolUniverse, categorize tools by domain (genomics, proteomics, drug discovery, clinical, omics, imaging, literature, pathways, systems biology). Count per category.

### 1.2 Identify Gap Domains
- **Critical Gap**: <5 tools in category
- **Moderate Gap**: 5-15 tools, missing key subcategories
- **Emerging Gap**: New technologies not represented

Common gaps: single-cell genomics, metabolomics, patient registries, microbial genomics, multi-omics integration, synthetic biology, toxicology.

### 1.3 Web Search for APIs
For each gap domain, run multiple queries:
1. `"[domain] API REST JSON"` — direct API search
2. `"[domain] public database"` — database discovery
3. `"[domain] API 2025 OR 2026"` — recent releases
4. `"[domain] database" site:nar.oxfordjournals.org` — NAR Database Issue

Extract: base URL, endpoints, auth method, parameter schemas, rate limits.

### 1.4 Score and Prioritize

| Criterion | Max Points |
|-----------|------------|
| Documentation Quality | 20 |
| API Stability | 15 |
| Authentication Simplicity | 15 |
| Coverage | 15 |
| Maintenance | 10 |
| Community | 10 |
| License | 10 |
| Rate Limits | 5 |

High priority (>=70), Medium (50-69), Low (<50).

### 1.5 Generate Discovery Report
Coverage analysis, prioritized candidates with scores, implementation roadmap.

---

## Phase 2: Tool Creation

For each API, use `Skill(skill="devtu-create-tool")` or follow these patterns.

### Architecture Decision
- Multiple endpoints → multi-operation tool (single class, multiple JSON wrappers)
- Single endpoint → single-operation acceptable

### Key Steps
1. Design tool class following template — see [references/tool-templates.md](references/tool-templates.md)
2. Create JSON config with oneOf return_schema
3. Find real test examples (use List endpoint → extract IDs → verify)
4. Register in `default_config.py`

### Critical Requirements
- return_schema MUST have `oneOf` (success + error schemas)
- test_examples MUST use real IDs (NO placeholders)
- Tool name <= 55 characters
- NEVER raise exceptions in `run()` — return error dict
- Set timeout on all HTTP requests (30s)

---

## Phase 3: Validation

Full guide: [references/validation-guide.md](references/validation-guide.md)

### Quick Validation Checklist
1. **Schema**: oneOf structure, data wrapper, error field
2. **Placeholders**: No TEST/DUMMY/PLACEHOLDER in test_examples
3. **Loading**: 3-step check (class registered, config registered, wrappers generated)
4. **Integration tests**: `python scripts/test_new_tools.py [api_name] -v` → 100% pass

Fix failures with `Skill(skill="devtu-fix-tool")`.

---

## Phase 4: Integration

Use `Skill(skill="devtu-github")` or:
1. Create branch: `feature/add-[api-name]-tools`
2. Stage tool files + default_config.py
3. Commit with descriptive message
4. Push and create PR with validation results

---

## Processing Patterns

| Pattern | When to Use |
|---------|------------|
| **Batch** (multiple APIs → single PR) | Same domain, similar structure |
| **Iterative** (one API at a time) | Complex auth, novel patterns |
| **Discovery-only** (report, no tools) | Planning roadmap |
| **Validation-only** (audit existing) | PR review, quality check |

---

## References

- **Tool templates** (Python class + JSON config): [references/tool-templates.md](references/tool-templates.md)
- **Validation & integration guide**: [references/validation-guide.md](references/validation-guide.md)
