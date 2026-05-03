# Integration with devtu-optimize-skills

This skill builds on principles from `devtu-optimize-skills`. This reference explains how to apply those principles when creating new skills.

## When to Reference devtu-optimize-skills

**Invoke or review** devtu-optimize-skills when:
- Creating skills that generate research reports
- Need evidence grading patterns
- Want report optimization strategies
- Implementing completeness checking
- Designing synthesis sections

**Don't need** devtu-optimize-skills when:
- Creating simple data retrieval skills
- Building workflows without reports
- Pure tool integration (no analysis)

## The 10 Pillars Applied to Skill Creation

### 1. TEST FIRST

**devtu-optimize principle**: Never write skill documentation without testing all tool calls

**Application in skill creation**:
- Phase 2: Tool Discovery & Testing - Create test script BEFORE implementation
- Verify all tool parameters through actual API calls
- Document discoveries (response formats, parameter mismatches)
- Only proceed to Phase 4 (Implementation) after 100% tool verification

**Why critical**: All 4 broken skills (DDI, Clinical Trial, Antibody, CRISPR) had 0-20% functionality because tools were never tested.

### 2. Verify Tool Contracts

**devtu-optimize principle**: Check params via `get_tool_info()`; maintain corrections table; don't trust function names

**Application in skill creation**:
- Test script checks actual parameter names
- Create parameter corrections table in SKILL.md
- Document: "Tool function names DO NOT predict parameter names"
- Example: `drugbank_get_drug_by_name(query=...)` not `name=...`

### 3. Handle SOAP Tools

**devtu-optimize principle**: Add `operation` parameter to IMGT, SAbDab, TheraSAbDab tools

**Application in skill creation**:
- Test script identifies SOAP tools (error: "operation is required")
- Add `operation` parameter to all SOAP tool calls
- Document prominently in SKILL.md and QUICK_START
- Show side-by-side Python/MCP examples

### 4. Implementation-Agnostic Docs

**devtu-optimize principle**: SKILL.md general; separate python_implementation.py; QUICK_START for both SDK and MCP

**Application in skill creation**:
- Phase 5: Documentation - SKILL.md has ZERO Python/MCP code
- python_implementation.py contains working pipeline
- QUICK_START.md equal treatment of both interfaces
- Tool parameter table notes "applies to all implementations"

### 5. Foundation First

**devtu-optimize principle**: Query comprehensive aggregators before specialized tools

**Application in skill creation**:
- Identify if domain has comprehensive aggregator (e.g., Open Targets for targets)
- Structure workflow: Phase 0 (aggregator) → Phases 1-N (specialized)
- Document in SKILL.md which tool provides foundation data
- Use aggregator to provide baseline when specialized tools fail

**Example**:
- Target research: Open Targets (foundation) → specialized databases (details)
- Pathway analysis: Reactome top-level (foundation) → keyword search (specific)

### 6. Disambiguate Carefully

**devtu-optimize principle**: Resolve IDs (versioned + unversioned), detect collisions, get baseline from annotation DBs

**Application in skill creation**:
- Include disambiguation phase early in workflow
- Support multiple ID types (e.g., gene symbols, Ensembl, UniProt)
- Handle versioned IDs where needed (GTEx requires versioned Ensembl)
- Document ID resolution strategy in SKILL.md

**When critical**:
- Skills with ambiguous inputs (gene names, compound names)
- Skills querying multiple databases with different ID systems
- Skills where ID collisions are common

### 7. Implement Fallbacks

**devtu-optimize principle**: Primary → Fallback → Default chains for critical functionality

**Application in skill creation**:
- Identify critical tools that may fail
- Design fallback strategy for each
- Implement try/except with fallback calls
- Document strategy in SKILL.md

**Example from CRISPR skill**:
```markdown
## Fallback Strategy

**Primary**: DepMap_search_genes (comprehensive data)
**Fallback**: Pharos_get_target (TDL classification)
**Default**: Continue with unvalidated genes

Impact: 20% → 60% functional when primary down
```

### 8. Grade Evidence

**devtu-optimize principle**: T1-T4 tiers on all claims; summarize quality per section

**Application in skill creation**:
- Include evidence tier in report if skill analyzes literature
- T1 (★★★): Mechanistic study
- T2 (★★☆): Functional study
- T3 (★☆☆): Association
- T4 (☆☆☆): Mention
- Document in SKILL.md how to assign tiers

**When to apply**:
- Skills that search literature
- Skills that aggregate evidence from multiple sources
- Skills making scientific claims

**When not needed**:
- Pure data retrieval skills
- Skills without analysis component

### 9. Require Quantified Completeness

**devtu-optimize principle**: Numeric minimums, not just "include X"

**Application in skill creation**:
- Define numeric minimums for each section in SKILL.md
- Example: "≥20 pathways OR explanation why fewer"
- Document what constitutes "complete" for each data type
- Implement checks in python_implementation.py

**Example**:
```markdown
## Quantified Minimums

| Section | Minimum Data | If Not Met |
|---------|--------------|------------|
| Pathways | ≥10 pathways | Note "limited pathways available" |
| Interactions | ≥20 interactors | Explain why fewer + which tools failed |
| Expression | Top 10 tissues | Note specific gaps |
```

### 10. Synthesize

**devtu-optimize principle**: Biological models and testable hypotheses, not just paper lists

**Application in skill creation**:
- Include synthesis section if skill does analysis
- Document what synthesis looks like for the domain
- Provide template for biological model
- Show example testable hypotheses

**When to apply**:
- Research-oriented skills
- Skills that integrate multiple data sources
- Skills where users need actionable insights

**Example sections**:
- Biological Model (3-5 paragraphs integrating all evidence)
- Testable Hypotheses (table with predictions)
- Suggested Experiments (how to test hypotheses)

---

## Skill-Specific Additions

Beyond the 10 pillars, skills may need:

### Multi-Database Integration
- Document which databases provide what
- Note overlaps and complementary coverage
- Cross-reference results across sources

### Progressive Report Writing
- Create report file first
- Add sections progressively
- Each section self-contained
- Handles empty data gracefully

### Domain-Specific Quality Checks
- Metabolomics: Chemical structure validation
- Genomics: Variant format checking
- Proteomics: Sequence validation

---

## When devtu-optimize-skills Doesn't Apply

**Not applicable for**:
- Simple data retrieval skills (no analysis)
- Tool integration without reporting
- Workflows without literature component
- Pure visualization skills

**Partially applicable for**:
- Data transformation skills (use TEST FIRST, fallbacks)
- Multi-tool orchestration (use fallbacks, error handling)
- Specialized analysis (use relevant pillars only)

---

## Quick Reference: Which Principles for Which Skills

| Skill Type | Applicable Principles |
|------------|----------------------|
| Research/Analysis | All 10 pillars |
| Data Retrieval | 1-4, 6-7 (test, verify, agnostic, disambiguate, fallbacks) |
| Multi-Database | 1-5, 7 (test, verify, agnostic, foundation, fallbacks) |
| Specialized Analysis | 1-4, 7-9 (test, verify, agnostic, fallbacks, evidence, completeness) |
| Simple Tool Wrapper | 1-4 (test, verify, agnostic) |

---

## Integration Checklist

When creating a new skill, check devtu-optimize-skills integration:

- [ ] Reviewed 10 pillars
- [ ] Identified which principles apply
- [ ] Implemented TEST FIRST (always)
- [ ] Verified tool contracts (always)
- [ ] Implementation-agnostic docs (always)
- [ ] Fallback strategies (if external APIs)
- [ ] Evidence grading (if literature)
- [ ] Quantified completeness (if multi-section)
- [ ] Synthesis (if research-oriented)
- [ ] Documented application in SKILL.md

---

## Summary

devtu-optimize-skills provides foundational principles for all ToolUniverse skills:

**Always apply**:
1. TEST FIRST
2. Verify tool contracts
3. Handle SOAP tools (if present)
4. Implementation-agnostic docs

**Apply when relevant**:
5. Foundation first (if aggregator exists)
6. Disambiguate carefully (if ambiguous inputs)
7. Implement fallbacks (if external APIs)
8. Grade evidence (if literature)
9. Quantified completeness (if multi-section)
10. Synthesize (if research-oriented)

**Result**: High-quality, production-ready skills following established best practices.
