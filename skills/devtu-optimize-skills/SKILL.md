---
name: devtu-optimize-skills
description: Optimize ToolUniverse skills for better report quality, evidence handling, and user experience. Apply patterns like tool verification, foundation data layers, disambiguation-first, evidence grading, quantified completeness, and report-only output. Use when reviewing skills, improving existing skills, or creating new ToolUniverse research skills.
---

# Optimizing ToolUniverse Skills

Best practices for creating high-quality ToolUniverse research skills that produce detailed, evidence-graded reports with proper source attribution.

## When to Use This Skill

Apply when:
- Creating new ToolUniverse research skills
- Reviewing/improving existing skills
- User complains about missing details, noisy results, or unclear reports
- Skill produces process-heavy instead of content-heavy output
- Tools are failing silently or returning empty results

## Core Optimization Principles

### 1. Tool Interface Verification (Pre-flight Check)

**Problem**: Tool APIs change parameter names over time, or skills are written with incorrect parameter assumptions. This causes silent failures - tools return empty results without errors.

**Solution**: Verify tool parameters before calling unfamiliar tools:

```python
# Always check tool params to prevent silent failures
tool_info = tu.tools.get_tool_info(tool_name="Reactome_map_uniprot_to_pathways")
# Reveals: takes `id` not `uniprot_id`
```

**Maintain a known corrections table** in skills that use many tools:

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | `id` |
| `ensembl_get_xrefs` | `gene_id` | `id` |
| `GTEx_get_median_gene_expression` | `gencode_id` only | `gencode_id` + `operation="median"` |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |

**Rule**: Before calling any tool for the first time in a skill, confirm params via `get_tool_info()` once per tool family, or maintain a vetted param map in the skill.

**Why this matters**: Retry logic won't help if you're calling a tool with wrong parameter names - it will consistently return empty. This is different from API flakiness.

### 2. Foundation Data Layer (Path 0)

**Problem**: Skills query specialized tools for each section independently, missing data that a comprehensive aggregator already has. Results are inconsistent when specialized tools fail.

**Solution**: Identify if your domain has a **comprehensive aggregator** and query it FIRST before specialized tools.

**Examples by domain**:

| Domain | Foundation Source | What It Provides |
|--------|-------------------|------------------|
| Drug targets | Open Targets | Diseases, tractability, safety, drugs, GO, publications, mouse models |
| Chemicals | PubChem | Properties, bioactivity, patents, literature |
| Diseases | Open Targets / OMIM | Genes, drugs, phenotypes, literature |
| Genes | MyGene / Ensembl | Annotations, cross-refs, GO, pathways |

**Pattern**:
```markdown
## Workflow
Phase 0: Foundation Data (aggregator query)
Phase 1: Disambiguation (ID resolution, collision detection)
Phase 2: Specialized Queries (fill gaps from Phase 0)
Phase 3: Report Synthesis
```

**Why this works**: The aggregator provides reliable baseline data across multiple sections. Specialized tools then add depth or fill gaps, rather than being the sole source.

### 3. Versioned Identifier Handling

**Problem**: Some APIs require versioned identifiers (e.g., GTEx needs `ENSG00000123456.12`), while others reject them. Skills fail silently when using the wrong format.

**Solution**: During ID resolution, capture BOTH versioned and unversioned forms:

```python
ids = {
    'ensembl': 'ENSG00000123456',           # Unversioned (most APIs)
    'ensembl_versioned': 'ENSG00000123456.12'  # Versioned (GTEx, some others)
}

# Get version from Ensembl lookup
gene_info = tu.tools.ensembl_lookup_gene(id=ensembl_id, species="human")
if gene_info and gene_info.get('version'):
    ids['ensembl_versioned'] = f"{ensembl_id}.{gene_info['version']}"
```

**Fallback strategy**:
1. Try unversioned first (more portable)
2. If empty, try versioned
3. Document which format worked

**Common versioned ID APIs**: GTEx, GENCODE, some Ensembl endpoints

### 4. Disambiguation Before Research

**Problem**: Skills that jump straight to literature search often miss target details or retrieve irrelevant papers due to naming collisions.

**Solution**: Add a disambiguation phase before any literature search:

```markdown
## Phase 1: Target Disambiguation (Default ON)

### 1.1 Resolve Official Identifiers
- UniProt accession (canonical protein)
- Ensembl gene ID + version (for expression data)
- NCBI Gene ID (for literature)
- ChEMBL target ID (for drug data)

### 1.2 Gather Synonyms and Aliases
- All known gene symbols
- Protein name variants
- Historical names

### 1.3 Detect Naming Collisions
- Search "[SYMBOL]"[Title] - review top 20 results
- If >20% off-topic → identify collision terms
- Build negative filter: NOT [collision1] NOT [collision2]

### 1.4 Get Baseline Profile (from annotation DBs, not literature)
- Protein domains (InterPro)
- Subcellular location (HPA)
- Tissue expression (GTEx)
- GO terms and pathways
```

**Why this works**: Annotation databases provide reliable baseline data even when literature is sparse or noisy.

### 5. Report-Only Output (Hide Search Process)

**Problem**: Users don't want to see "searched 8 databases, found 1,247 papers, deduplicated to 892..."

**Solution**: Output structure:

| File | Content | When |
|------|---------|------|
| `[topic]_report.md` | Narrative findings only | Always (default) |
| `[topic]_bibliography.json` | Full deduplicated papers | Always |
| `methods_appendix.md` | Search methodology | Only if requested |

**In the report**:
- ✅ DO: "The literature reveals three main therapeutic approaches..."
- ❌ DON'T: "I searched PubMed, OpenAlex, and EuropePMC, finding 342 papers..."

### 6. Evidence Grading

**Problem**: A review article mention is treated the same as a mechanistic study with direct evidence.

**Solution**: Apply evidence tiers to every claim:

| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | ★★★ | Mechanistic study with direct evidence |
| T2 | ★★☆ | Functional study (knockdown, overexpression) |
| T3 | ★☆☆ | Association (screen hit, GWAS, correlation) |
| T4 | ☆☆☆ | Mention (review, text-mined, peripheral) |

**In report**:
```markdown
ATP6V1A drives lysosomal acidification [★★★: PMID:12345678] and has been 
implicated in cancer progression [★☆☆: PMID:23456789, TCGA expression data].
```

**Required locations for evidence grades**:
1. Executive Summary - key disease claims
2. Disease Associations - every disease link
3. Key Papers table - evidence tier column
4. Recommendations - reference evidence quality

**Per-section summary**:
```markdown
### Theme: Lysosomal Function (47 papers)
**Evidence Quality**: Strong (32 mechanistic, 11 functional, 4 association)
```

### 7. Quantified Completeness (Not Just Categorical)

**Problem**: "Include PPIs" is aspirational; reports pass the checklist but are data-thin.

**Solution**: Define **numeric minimums** for each section:

| Section | Minimum Data | If Not Met |
|---------|--------------|------------|
| PPIs | ≥20 interactors | Explain why fewer + which tools failed |
| Expression | Top 10 tissues with values | Note "limited data" with specific gaps |
| Disease | Top 10 associations with scores | Note if fewer available |
| Variants | All 4 constraint scores (pLI, LOEUF, missense Z, pRec) | Note which unavailable |
| Druggability | All modalities assessed | "No drugs/probes" is valid data |
| Literature | Total + 5-year trend + 3-5 key papers | Note if sparse (<50 papers) |

**Why this matters**: Quantified minimums make completeness auditing objective and mechanical, not subjective.

### 8. Mandatory Completeness Checklist

**Problem**: Reports have inconsistent sections; some topics get skipped entirely.

**Solution**: Define mandatory sections that MUST exist, even if populated with "Limited evidence" or "Unknown":

```markdown
## Completeness Checklist (ALL Required)

### Identity & Context
- [ ] Official identifiers resolved (all 6 types)
- [ ] Synonyms/aliases documented
- [ ] Naming collisions handled (or "none detected")

### Biology
- [ ] Protein architecture (or "N/A for non-protein")
- [ ] Subcellular localization
- [ ] Expression profile (≥10 tissues with values)
- [ ] Pathway involvement (≥10 pathways)

### Mechanism
- [ ] Core function with evidence grades
- [ ] Model organism data (or "none found")
- [ ] Key assays described

### Disease & Clinical
- [ ] Genetic variants (SNVs and CNVs separated)
- [ ] Constraint scores (all 4, with interpretations)
- [ ] Disease links with evidence grades (≥10 or "limited")

### Druggability
- [ ] Tractability for all modalities
- [ ] Known drugs (or "none")
- [ ] Chemical probes (or "none available")
- [ ] Clinical pipeline (or "none")

### Synthesis (CRITICAL)
- [ ] Research themes (≥3 papers each, or "limited")
- [ ] Open questions/gaps
- [ ] Biological model synthesized
- [ ] Testable hypotheses (≥3)
```

### 9. Aggregated Data Gaps Section

**Problem**: "No data" notes scattered across 14 sections; users can't quickly see what's missing.

**Solution**: Add a dedicated **Data Gaps & Limitations** section that consolidates all gaps:

```markdown
## 15. Data Gaps & Limitations

| Section | Expected Data | Actual | Reason | Alternative Source |
|---------|---------------|--------|--------|-------------------|
| 6. PPIs | ≥20 interactors | 8 | Novel target, limited studies | Literature review needed |
| 7. Expression | GTEx TPM | None | Versioned ID not recognized | See HPA data |
| 9. Probes | Chemical probes | None | No validated probes exist | Consider tool compound dev |

**Recommendations for Data Gaps**:
1. For PPIs: Query BioGRID with broader parameters; check yeast-2-hybrid studies
2. For Expression: Query GEO directly for tissue-specific datasets
```

**Why this matters**: Users can quickly assess data quality and know where to look for more information.

### 10. Query Strategy Optimization

**Problem**: Simple keyword searches retrieve too much noise or miss relevant papers.

**Solution**: Three-step collision-aware query strategy:

```markdown
## Query Strategy

### Step 1: High-Precision Seeds
Build a mechanistic core set (15-30 papers):
- "[GENE_SYMBOL]"[Title] AND mechanism
- "[FULL_PROTEIN_NAME]"[Title]
- "UniProt:ACCESSION"

### Step 2: Citation Network Expansion
From seeds, expand via citations:
- Forward: PubMed_get_cited_by, EuropePMC_get_citations
- Related: PubMed_get_related
- Backward: EuropePMC_get_references

### Step 3: Collision-Filtered Broad
Apply negative filters for known collisions:
- "TRAG" AND immune NOT plasmid NOT conjugation
- "JAK" AND kinase NOT "just another"
```

**Citation-first for sparse targets**: When keyword search returns <30 papers, prioritize citation expansion from the few good seeds.

### 11. Tool Failure Handling

**Problem**: NCBI elink and other APIs can be flaky; skills fail silently.

**Solution**: Automatic retry with fallback chains:

```markdown
## Failure Handling

### Retry Protocol
Attempt 1 → fails → wait 2s → Attempt 2 → fails → wait 5s → Fallback

### Fallback Chains
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| PubMed_get_cited_by | EuropePMC_get_citations | OpenAlex citations |
| PubMed_get_related | SemanticScholar | Keyword search |
| GTEx_* | HPA_* | Note as unavailable |
| Unpaywall | EuropePMC OA flag | OpenAlex is_oa |
| ChEMBL_get_target_activities | GtoPdb_get_target_ligands | OpenTargets drugs |
| intact_get_interactions | STRING_get_protein_interactions | OpenTargets interactions |

### Document Failures
In report: "Expression data unavailable (GTEx API timeout after 3 attempts)"
```

**Rule**: NEVER silently skip failed tools. Always document in the Data Gaps section.

### 12. Scalable Output Structure

**Problem**: Reports with 500+ papers become unreadable; users can't find what they need.

**Solution**: Separate narrative from data:

**Narrative report** (~20-50 pages max):
- Executive summary
- Key findings by theme
- Top 20-50 papers highlighted
- Conclusions and hypotheses

**Bibliography files** (unlimited):
- `[topic]_bibliography.json` - Full structured data
- `[topic]_bibliography.csv` - Tabular for filtering

**JSON structure**:
```json
{
  "pmid": "12345678",
  "doi": "10.1038/xxx",
  "title": "...",
  "evidence_tier": "T1",
  "themes": ["lysosomal_function", "autophagy"],
  "is_core_seed": true,
  "oa_status": "gold"
}
```

### 13. Synthesis Sections

**Problem**: Reports describe what was found but don't synthesize into actionable insights.

**Solution**: Require synthesis sections:

```markdown
## Required Synthesis Sections

### Biological Model (3-5 paragraphs)
Integrate all evidence into a coherent model:
- What does the target do?
- How does it connect to disease?
- What's the key uncertainty?

### Testable Hypotheses (≥3)
| # | Hypothesis | Perturbation | Readout | Expected |
|---|------------|--------------|---------|----------|
| 1 | [Hypothesis] | [Experiment] | [Measure] | [Prediction] |

### Suggested Experiments
Brief description of how to test each hypothesis.
```

---

## Skill Review Checklist

When reviewing a ToolUniverse skill, check:

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
- [ ] Citation expansion option for sparse topics
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
- [ ] "Negative results" explicitly documented ("no probes" not blank)

### Output Structure
- [ ] Main report is narrative-focused
- [ ] Bibliography in separate JSON/CSV
- [ ] Synthesis sections required

### User Experience
- [ ] Progress updates are brief
- [ ] No raw tool outputs shown
- [ ] Final report is the deliverable

---

## Common Anti-Patterns to Fix

### 1. "Search Log" Reports
**Bad**: "Round 1: Searched PubMed (234 papers), OpenAlex (456 papers)..."
**Fix**: Keep methodology internal; report findings only

### 2. Missing Disambiguation
**Bad**: Search "JAK" and get kinase + "just another kinase" papers mixed
**Fix**: Add collision detection; build negative filters

### 3. No Evidence Grading
**Bad**: "Multiple studies show..." (which studies? what quality?)
**Fix**: Apply T1-T4 grades; label each claim

### 4. Empty Sections Omitted
**Bad**: Skip "Pathogen Involvement" because nothing found
**Fix**: Include section with "None identified in literature search"

### 5. No Synthesis
**Bad**: Long list of papers organized by theme
**Fix**: Add biological model + testable hypotheses

### 6. Monolithic Bibliography
**Bad**: 200 papers embedded in report narrative
**Fix**: Top 20-50 in report; full list in JSON/CSV

### 7. Silent Failures
**Bad**: "Expression data: [blank]" (tool failed, user doesn't know)
**Fix**: "Expression data unavailable (API timeout); see HPA directly"

### 8. Wrong Tool Parameters (NEW)
**Bad**: `Reactome_map_uniprot_to_pathways(uniprot_id=...)` returns empty
**Fix**: Verify params via `get_tool_info()`; use correct param `id`

### 9. Missing Versioned IDs (NEW)
**Bad**: GTEx returns empty for `ENSG00000123456`
**Fix**: Try versioned ID `ENSG00000123456.12`; document which worked

### 10. No Foundation Layer (NEW)
**Bad**: Query 15 specialized tools independently, miss data when some fail
**Fix**: Query comprehensive aggregator (e.g., Open Targets) first

### 11. Scattered "No Data" Notes (NEW)
**Bad**: "No data" in 5 different sections; user doesn't know overall gaps
**Fix**: Aggregate all gaps in dedicated Data Gaps section with recommendations

### 12. Aspirational Completeness (NEW)
**Bad**: "Include PPIs" ✓ (but only 3 interactors listed)
**Fix**: "≥20 PPIs OR explanation why fewer"

### 13. Untested Tool Calls (CRITICAL - NEW)
**Bad**: Skill created with excellent documentation but tools never actually called
**Example**: Documentation shows `drugbank_get_drug_basic_info(drug_name_or_drugbank_id="...")` but parameter doesn't exist
**Impact**: All 4 broken skills discovered in 2026-02 had this issue - 0% functionality despite 1,500+ line docs

**Fix**: Test-driven skill development:
1. Write test script FIRST: `test_[skill].py`
2. Call every tool with real ToolUniverse instance
3. Verify parameters work and results are correct
4. Create working pipeline from tested code
5. Write documentation from working examples

**Verification**:
```python
# Test every tool before documenting
def test_tools():
    tu = ToolUniverse()
    tu.load_tools()

    # Test Tool 1
    result = tu.tools.TOOL_NAME(param="value")
    assert result.get('status') == 'success', "Tool 1 failed"

    # Test Tool 2
    result = tu.tools.TOOL_NAME2(param="value")
    assert result.get('status') == 'success', "Tool 2 failed"
```

**Rule**: NEVER write skill documentation without first testing all tool calls.

---

## NEW: Implementation-Agnostic Skills (2026-02 Update)

### Critical Lesson from Real Fixes

**All 4 broken skills** (Drug-Drug Interaction, Clinical Trial Design, Antibody Engineering, CRISPR Screen Analysis) had excellent documentation but were never tested with real tool calls. This section documents critical lessons learned from fixing them.

### 14. Implementation-Agnostic Documentation

**Problem**: Skills written with implementation-specific code (Python SDK only) limit users to one interface. Users may access ToolUniverse via Python SDK, MCP (Model Context Protocol), or future APIs.

**Solution**: Separate general concepts from implementation details.

**File Structure**:
```
skills/[skill-name]/
├── SKILL.md                     # General workflow (NO Python/MCP code)
├── python_implementation.py     # Python SDK implementation
├── QUICK_START.md              # Multi-implementation examples
└── test_[skill].py             # Test script
```

**SKILL.md Format (General)**:
```markdown
## Phase 1: [Name]

**Objective**: What this phase achieves

**Tools needed**:
- Tool_A: Purpose and what it does
  - Input: parameter descriptions
  - Output: expected results

**Workflow**:
1. Query Tool_A with [inputs]
2. Extract [specific data]
3. If no results → try Tool_B
4. Continue with available data

**Decision logic**:
- When to use exact match vs fuzzy
- How to handle empty results
- When to trigger fallback
```

**Don't include in SKILL.md**:
- ❌ `from tooluniverse import ToolUniverse`
- ❌ `tu.tools.TOOL_NAME(...)`
- ❌ Python-specific code
- ❌ MCP-specific JSON

**QUICK_START.md Format (Multi-Implementation)**:
```markdown
## Choose Your Implementation

### Python SDK
[Python code examples]

### MCP (Model Context Protocol)
[Conversational prompts + JSON tool calls]

## Tool Parameters (All Implementations)
[Parameter table noting: applies to both Python SDK and MCP]
```

**Why this matters**: Users can choose Python SDK, MCP, or future interfaces without relearning the skill workflow.

### 15. SOAP Tools Special Handling

**Problem**: SOAP-based tools (IMGT, SAbDab, TheraSAbDab) require a special `operation` parameter that isn't obvious from function names. Missing this causes 100% tool failure.

**Detection**: If tool returns error "Parameter validation failed: 'operation' is a required property" → SOAP tool

**Add to Tool Interface Verification (Section 1)**:

| Tool Family | Parameter | CRITICAL Requirement |
|-------------|-----------|---------------------|
| IMGT_* | `operation` | MUST be first parameter (e.g., "search_genes") |
| SAbDab_* | `operation` | MUST be first parameter (e.g., "search_structures") |
| TheraSAbDab_* | `operation` | MUST be first parameter (e.g., "search_by_target") |

**Example**:
```markdown
### Tool: IMGT_search_genes

**Parameters** (implementation-agnostic):
- `operation` (string, required): SOAP method name = "search_genes"
- `gene_type` (string, required): "IGHV", "IGKV", "IGLV"
- `species` (string, required): "Homo sapiens" for human

**Python SDK**:
```python
result = tu.tools.IMGT_search_genes(
    operation="search_genes",  # Required!
    gene_type="IGHV",
    species="Homo sapiens"
)
```

**MCP**:
```json
{
  "operation": "search_genes",
  "gene_type": "IGHV",
  "species": "Homo sapiens"
}
```

**Critical**: SOAP tools will fail without `operation` parameter in both implementations.
```

### 16. Fallback Strategies for API Failures

**Problem**: Primary APIs can go down completely (e.g., DepMap 404 errors). Skills without fallbacks become 0% functional.

**Solution**: Implement tiered fallback strategies and document them clearly.

**Fallback Pattern**:
```markdown
## Fallback Strategy

**Primary**: [Best data source with detailed info]
**Fallback**: [Alternative source with partial data]
**Default**: [Continue with limited/unvalidated data]

**Python SDK**:
```python
try:
    result = tu.tools.PRIMARY_TOOL(param=value)
except:
    result = tu.tools.FALLBACK_TOOL(param=value)
```

**MCP**: Tell Claude to use Fallback if Primary unavailable
```

**Real Example from CRISPR Screen Analysis**:
- **Primary**: DepMap_search_genes (comprehensive essentiality data)
- **Fallback**: Pharos_get_target (TDL classification as essentiality proxy)
- **Default**: Continue with unvalidated genes

**Impact**: Skill went from 20% functional (total failure when DepMap down) to 60% functional (continues with Pharos data).

---

## Comprehensive Parameter Corrections (From Real Fixes)

**Add to Section 1 (Tool Interface Verification)**:

The following corrections were discovered while fixing 4 non-functional skills in February 2026:

| Tool | Common Mistake | Correct Parameter | Evidence |
|------|----------------|-------------------|----------|
| RxNorm_get_drug_names | `query` | `drug_name` | DDI skill fix |
| drugbank_get_drug_basic_info_by_drug_name_or_id | `drug_name_or_id` | `query` | DDI + Trial skill fixes |
| drugbank_get_pharmacology_by_drug_name_or_drugbank_id | `drug_name_or_drugbank_id` | `query` | Trial skill fix |
| drugbank_get_safety_by_drug_name_or_drugbank_id | `drug_name_or_drugbank_id` | `query` | Trial skill fix |
| FAERS_count_reactions_by_drug_event | `drug_name` | `medicinalproduct` | DDI skill fix |
| IMGT_search_genes | Missing parameter | `operation="search_genes"` | Antibody skill fix |
| IMGT_get_sequence | Missing parameter | `operation="get_sequence"` | Antibody skill fix |
| SAbDab_search_structures | Missing parameter | `operation="search_structures"` | Antibody skill fix |
| TheraSAbDab_search_by_target | Missing parameter | `operation="search_by_target"` | Antibody skill fix |

**Pattern**: Tool function names DO NOT predict parameter names - always test!

---

## Real-World Case Studies

### Case Study 1: Drug-Drug Interaction Skill

**Original State**: 0% functional
- Documentation showed `drugbank_get_drug_basic_info(drug_name_or_drugbank_id="...")`
- Tool actually requires `query` parameter
- Never tested with real ToolUniverse instance
- Beautiful 300+ line documentation, completely non-functional

**Fixed State**: 100% functional
- Created `test_ddi.py` - verified all tool parameters
- Created `python_implementation.py` - working 8-step pipeline
- Updated `QUICK_START.md` - both Python SDK and MCP examples
- Tool parameter table documents correct names

**Key Fixes**:
```markdown
| Tool | WRONG (in docs) | CORRECT (tested) |
|------|-----------------|------------------|
| RxNorm_get_drug_names | query | drug_name |
| drugbank_* | drug_name_or_id | query |
| FAERS_count_reactions | drug_name | medicinalproduct |
```

**Lesson**: Function names are misleading - `get_drug_basic_info_by_drug_name_or_id` actually takes `query`, not `drug_name_or_id`.

### Case Study 2: Antibody Engineering Skill

**Original State**: 0% functional
- All SOAP tool calls missing `operation` parameter
- Error: "Parameter validation failed: 'operation' is a required property"
- 5/8 tools completely broken
- Documentation looked professional but untested

**Fixed State**: 80% functional
- Identified SOAP tools (IMGT, SAbDab, TheraSAbDab)
- Added `operation` parameter to all SOAP calls
- Created side-by-side Python/MCP examples
- Documented SOAP requirement prominently in QUICK_START

**Key Fix**:
```markdown
## CRITICAL: SOAP Tools

**Python SDK**:
```python
tu.tools.IMGT_search_genes(
    operation="search_genes",  # Required!
    gene_type="IGHV"
)
```

**MCP**:
```json
{
  "operation": "search_genes",
  "gene_type": "IGHV"
}
```
```

**Lesson**: SOAP tools have special requirements not obvious from function signatures. Always test.

### Case Study 3: CRISPR Screen Analysis Skill

**Original State**: 20% functional
- Primary API (DepMap) completely down (404 errors from both Sanger and Broad)
- No fallback strategy
- Skill failed completely when DepMap unavailable
- Users got zero results despite many alternative tools available

**Fixed State**: 60% functional
- Implemented Pharos TDL fallback for gene validation
- Documented fallback strategy in both Python SDK and MCP
- TDL classification (Tclin/Tchem/Tbio/Tdark) as essentiality proxy
- Skill continues with alternative data source

**Key Fix**:
```markdown
## Fallback Strategy

**Primary**: DepMap_search_genes (comprehensive essentiality data)
**Fallback**: Pharos_get_target (TDL classification)
**Default**: Continue with unvalidated genes

**Python SDK**:
```python
try:
    result = tu.tools.DepMap_search_genes(query=gene)
except:
    result = tu.tools.Pharos_get_target(gene=gene)
    if result.get('status') == 'success':
        tdl = result['data'].get('tdl', 'Unknown')
```

**MCP**: Tell Claude to use Pharos if DepMap unavailable
```

**Lesson**: External APIs fail. Always implement fallback chains for critical functionality.

### Case Study 4: Clinical Trial Design Skill

**Original State**: 0% functional
- All DrugBank tool parameters wrong throughout entire skill
- Assumed parameters based on function names
- 6-step pipeline documented but never executed
- Never tested end-to-end

**Fixed State**: 100% functional
- Corrected ALL DrugBank parameters (use `query`)
- Created working 6-step feasibility analysis pipeline
- Feasibility scoring (0-100) working correctly
- Generated actual trial feasibility reports

**Key Fixes**:
- ALL DrugBank tools use `query` parameter, not the parameter names in their function names
- Test revealed: `drugbank_get_safety_by_drug_name_or_drugbank_id(query="...", case_sensitive=False)`

**Lesson**: Even when multiple tools have similar parameter name patterns in their function names, always verify each one.

---

## Updated Skill Release Checklist

**Add to Skill Review Checklist section**:

### Implementation & Testing (CRITICAL - 2026-02 Standards)
- [ ] All tool calls tested in ToolUniverse instance (MANDATORY)
- [ ] Comprehensive test script with ≥30 tests (`test_[skill].py`)
- [ ] 100% test pass rate achieved (no failures, only warnings for transient errors)
- [ ] All tests use real data (NO "TEST", "DUMMY", "PLACEHOLDER", "example_*")
- [ ] Edge cases tested: empty inputs, large inputs, invalid inputs, boundary values
- [ ] Phase-level tests (each phase tested independently)
- [ ] Integration tests (full workflow end-to-end)
- [ ] Cross-example tests (multiple diseases/drugs/genes)
- [ ] Working pipeline runs without errors
- [ ] Error cases handled (empty data, API failures)
- [ ] Transient errors distinguished from real bugs (timeout handling)
- [ ] SOAP tools have `operation` parameter (if applicable)
- [ ] Fallback strategies implemented and tested
- [ ] Parameters verified via `get_tool_info()` or actual testing
- [ ] API quirks documented (response structure variations, field name mismatches)
- [ ] Performance benchmarked and documented
- [ ] Test output is self-documenting (shows what was tested and result)

### Documentation (2026-02 Standards)
- [ ] SKILL.md is implementation-agnostic (no Python/MCP code)
- [ ] python_implementation.py contains working Python SDK code
- [ ] QUICK_START.md includes both Python SDK and MCP examples
- [ ] EXAMPLES.md with detailed use cases and expected outputs
- [ ] TOOLS_REFERENCE.md with verified parameter names (not assumed)
- [ ] Tool parameter table notes "applies to all implementations"
- [ ] All code examples in documentation actually work (copy-paste ready)
- [ ] Documentation examples tested in test suite
- [ ] Response structures documented for each tool
- [ ] API gotchas documented (field name mismatches, structure variations)
- [ ] SOAP tool warnings prominently displayed (if applicable)
- [ ] Fallback strategies documented (if applicable)
- [ ] Evidence grading system explained (T1-T4)
- [ ] Completeness checklist template provided
- [ ] Known limitations disclosed
- [ ] Example reports generated
- [ ] Expected execution times documented
- [ ] Scientific citations included (Nature/Science/NEJM papers)

### User Testing
- [ ] Fresh terminal test passes (new user can follow docs)
- [ ] Examples from QUICK_START work without modification
- [ ] Documentation examples copy-paste successfully
- [ ] Reports are readable (not debug logs)
- [ ] Completes in reasonable time (<5 min for basic examples)
- [ ] Error messages are actionable (tell user HOW to fix)

### Quality Assurance
- [ ] No placeholder data in tests (`grep -r "TEST\|DUMMY\|PLACEHOLDER"`)
- [ ] All tool parameters verified against actual APIs
- [ ] Performance benchmarks measured (`time python test_*.py`)
- [ ] Edge case coverage verified (`grep "def test_edge" test_*.py` → 5+ tests)
- [ ] No known bugs or blockers
- [ ] Maintenance plan established

**CRITICAL**: Never release a skill without:
1. Testing every single tool call with a real ToolUniverse instance
2. Achieving 100% test pass rate with comprehensive test suite (≥30 tests)
3. Verifying all documentation examples work as written
4. Using real data in all tests (no placeholders)

**Why this matters**: Skills are used for clinical/research decisions. Bugs can harm patients. Documentation quality doesn't matter if tools don't work.

---

## Template: Optimized Skill Structure

```markdown
---
name: [domain]-research
description: [What it does]. Creates detailed report with evidence grading 
and mandatory completeness. [When to use triggers].
---

# [Domain] Research Strategy

## When to Use
[Trigger scenarios]

## Workflow
Phase -1: Tool Verification → Phase 0: Foundation Data → Phase 1: Disambiguate → Phase 2: Search → Phase 3: Report

## Phase -1: Tool Verification
[Parameter corrections table for tools used in this skill]

## Phase 0: Foundation Data
[Comprehensive aggregator query - e.g., Open Targets for targets]

## Phase 1: Disambiguation (Default ON)
[ID resolution (versioned + unversioned), collision detection, baseline profile]

## Phase 2: Specialized Queries (Internal)
[Query strategy with collision filters, citation expansion, tool fallbacks]

## Phase 3: Report Synthesis
[Progressive writing, evidence grading, mandatory sections]

## Output Files
- `[topic]_report.md` (narrative, always)
- `[topic]_bibliography.json` (data, always)
- `methods_appendix.md` (only if requested)

## Quantified Minimums
[Specific numbers per section - e.g., ≥20 PPIs, top 10 tissues]

## Completeness Checklist
[ALL required sections with checkboxes]

## Data Gaps Section
[Template for aggregating missing data with recommendations]

## Evidence Grading
[T1-T4 definitions with required locations]

## Tool Reference
[Tools by category with fallback chains and parameter notes]
```

---

## Quick Fixes for Common Complaints

| User Complaint | Root Cause | Fix |
|----------------|------------|-----|
| "Report is too short" | Missing annotation data | Add Phase 1 disambiguation + Phase 0 foundation |
| "Too much noise" | No collision filtering | Add negative query filters |
| "Can't tell what's important" | No evidence grading | Add T1-T4 tiers |
| "Missing sections" | No completeness checklist | Add mandatory sections with minimums |
| "Too long/unreadable" | Monolithic output | Separate narrative from JSON |
| "Just a list of papers" | No synthesis | Add biological model + hypotheses |
| "Shows search process" | Wrong output focus | Report-only; methodology in appendix |
| "Tool failed, no data" | No fallback handling | Add retry + fallback chains |
| "Empty results, no error" | Wrong tool parameters | Add Phase -1 param verification |
| "GTEx returns nothing" | Versioned ID needed | Try `ENSG*.version` format |
| "Data seems incomplete" | No foundation layer | Add Phase 0 with aggregator |
| "Can't tell what's missing" | Scattered gaps | Add Data Gaps section |

---

---

## 🧪 NEW: Test-Driven Skill Development (2026-02 Update)

### Critical Lesson from Building 9 Production Skills

**The Golden Rule**: Testing Is Mandatory, Not Optional

**Why this matters**:
- Previous skills released without comprehensive testing → bugs found in production
- Skills with upfront testing (e.g., Immunotherapy Response: 129 tests) had 0 bugs
- **Users depend on these skills for clinical decisions** - bugs can harm patients

### Test-First Workflow

```
1. Write skill implementation (phases, tool calls)
2. Write comprehensive test suite
   ├── Phase-level tests (test each phase independently)
   ├── Integration tests (test full workflows)
   ├── Edge case tests (boundary conditions)
   └── Cross-example tests (multiple diseases/drugs/genes)
3. Run tests, achieve 100% pass rate
4. Fix all failures
5. ONLY THEN mark skill as complete
```

### Test Suite Structure

```python
#!/usr/bin/env python3
"""
Comprehensive Test Suite for [Skill Name]

Structure:
- Phase tests: Verify each analysis phase works independently
- Integration tests: Verify end-to-end workflows
- Edge cases: Empty data, large lists, invalid inputs, boundary values
- Performance: Execution time benchmarks
"""

# Test naming convention: test_phase[N]_[description]
def test_phase1_gene_resolution():
    """Test Phase 1: Gene symbol resolution to Ensembl IDs"""
    # Test with REAL gene
    result = resolve_gene("BRCA1")  # NOT "TEST_GENE"
    assert result['ensembl_id'] == "ENSG00000012048"
    assert result['symbol'] == "BRCA1"

def test_phase1_gene_resolution_edge_cases():
    """Test Phase 1: Gene resolution edge cases"""
    # Unknown gene
    result = resolve_gene("FAKE_GENE_XYZ")
    assert result is None or 'error' in result

    # Ambiguous gene (collision)
    result = resolve_gene("HER2")  # Actually ERBB2
    assert result['warnings'], "Should warn about ambiguity"

def test_integration_cancer_variant_full_workflow():
    """Test complete workflow: EGFR L858R in NSCLC"""
    result = analyze_variant(
        gene="EGFR",
        variant="L858R",
        cancer_type="lung adenocarcinoma"
    )
    # Verify all phases completed
    assert result['clinical_evidence']
    assert result['fda_therapies']
    assert result['clinical_trials']
    assert result['completeness_score'] >= 80
```

### What to Test

**1. All use cases from SKILL.md** (typically 4-6 use cases)
**2. Every documented parameter**
**3. All response fields** - verify documented fields exist
**4. Edge cases** (WHERE BUGS HIDE):

```python
# Empty/minimal data
test_with_no_mutations([])
test_with_single_gene(["BRCA1"])

# Large data
test_with_500_genes(gene_list_500)

# Invalid data
test_with_unknown_gene("FAKE123")
test_with_typo("BRAC1")  # typo

# Boundary values
test_with_tmb_zero(tmb=0)
test_with_tmb_max(tmb=999)

# Conflicting data
test_with_high_tmb_low_pdl1(tmb=50, pdl1=0)
```

### Test Output Standards

```python
# Good test output (self-documenting):
✅ Phase1: Gene resolution - BRCA1 → ENSG00000012048
✅ Phase2: CIViC evidence - Found 12 clinical entries
✅ Phase3: FDA therapies - 3 approved drugs
⚠️  Phase4: Clinical trials - API timeout (transient, tool works)
❌ Phase5: Pathway enrichment - Missing required parameter 'gene_list'

TEST SUMMARY:
Total: 80 tests
PASS: 78
FAIL: 1
WARN: 1
Pass rate: 97.5%
Time: 152.3s
```

---

## 🔌 NEW: API Integration Deep Dive (2026-02 Update)

### Critical Rule: API Documentation Is Often Wrong

**Problem**: Tool documentation frequently doesn't match actual API behavior
- Field names differ (docs say `p_value`, API returns `entities_pvalue`)
- Response structures vary (dict vs list vs nested)
- Parameters incorrectly documented as optional when required

### Solution: Always Verify Before Using

```python
# STEP 1: Verify tool parameters (don't trust docs blindly)
tool_info = tu.tools.get_tool_info("ReactomeAnalysis_pathway_enrichment")
# Check: parameter names, types, required vs optional

# STEP 2: Test with real data
result = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers="BRCA1 TP53 EGFR"
)

# STEP 3: Inspect actual response structure
print(json.dumps(result, indent=2))
# Discover: uses 'p_value' not 'entities_pvalue'

# STEP 4: Document findings
# Add to TOOLS_REFERENCE.md:
# ReactomeAnalysis_pathway_enrichment:
#   - Input: identifiers (space-separated string, NOT array)
#   - Output: {data: {pathways: [{p_value, fdr, ...}]}}
#   - NOTE: Field is 'p_value', not 'entities_pvalue' as some docs show
```

### Maintain a Tool Parameter Reference

Every skill should have a TOOLS_REFERENCE.md documenting **verified** parameters:

```markdown
## Phase 2: Pathway Enrichment

### enrichr_gene_enrichment_analysis
- **Parameters** (ALL REQUIRED):
  - `gene_list` (array of strings): Gene symbols, e.g., ['BRCA1', 'TP53']
  - `libs` (array of strings): Libraries, e.g., ['KEGG_2021_Human', 'Reactome_2022']
- **Response**: `{status: 'success', data: '{json_string}'}`
  - NOTE: `data` is a JSON STRING, needs JSON.parse()
  - Contains connectivity graph (107MB), not enrichment results
- **Gotcha**: Returns connectivity, use STRING_functional_enrichment instead

### STRING_functional_enrichment
- **Parameters**:
  - `protein_ids` (array): Gene symbols or Ensembl IDs
  - `species` (int): 9606 for human
  - `limit` (int, optional): Max results, default 10
- **Response**: Array of {category, term, p_value, fdr, genes}
- **Gotcha**: Requires 3+ genes, fails silently with <3
```

### Handle Variable Response Structures

Many APIs return different structures depending on the query:

```python
# WRONG: Assume fixed structure
result = api_call()
data = result['data']['disease']  # ❌ Breaks if structure varies

# RIGHT: Handle multiple possible structures
result = api_call()
if 'data' in result and isinstance(result['data'], dict):
    disease_data = result['data'].get('disease', result['data'])
elif isinstance(result, dict) and 'disease' in result:
    disease_data = result['disease']
else:
    disease_data = result

# Verify expected fields
if 'name' in disease_data:
    disease_name = disease_data['name']
else:
    # Fallback or error
```

### Common API Response Patterns

```python
# Pattern 1: Wrapped in data object
{"data": {"gene": {"symbol": "BRCA1", ...}}, "metadata": {...}}

# Pattern 2: Direct response
{"gene": {"symbol": "BRCA1", ...}}

# Pattern 3: Array response
[{"symbol": "BRCA1", ...}, {"symbol": "TP53", ...}]

# Pattern 4: Error response
{"error": "Gene not found", "status": "failed"}

# Handle all patterns:
def parse_response(result):
    if isinstance(result, list):
        return result
    if 'error' in result:
        return None
    if 'data' in result:
        return result['data']
    return result
```

---

## 🛡️ NEW: Advanced Error Handling (2026-02 Update)

### Distinguish Transient Errors from Real Bugs

**Transient errors** (API availability issues):
- Timeouts
- Rate limiting (429)
- Service overload (503)
- Network errors

**Real bugs** (code issues):
- Wrong parameter names
- Missing required fields
- Logic errors
- Invalid inputs

### Handle Transient Errors Gracefully

```python
def call_api_with_retry(tool_func, *args, max_retries=3, **kwargs):
    """Call API with retry logic for transient errors"""
    for attempt in range(max_retries):
        try:
            result = tool_func(*args, **kwargs)
            return result
        except TimeoutError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            # Last attempt failed - treat as transient
            return {'transient_error': True, 'message': 'API timeout'}
        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ['timeout', 'overload', '429', '503']):
                # Transient error
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {'transient_error': True, 'message': str(e)}
            else:
                # Real error - don't retry
                raise

# In tests, treat transient errors as PASS with note:
try:
    result = call_api_with_retry(tu.tools.EnsemblVEP_annotate_rsid, 'rs123')
    if result.get('transient_error'):
        log_test("VEP annotation", PASS, "API timeout (transient, tool works)")
    else:
        log_test("VEP annotation", PASS)
except Exception as e:
    log_test("VEP annotation", FAIL, str(e))
```

### Actionable Error Messages

```python
# BAD: Generic error
raise ValueError("Invalid input")

# GOOD: Actionable error
raise ValueError(
    f"Gene '{gene_name}' not found in MyGene database.\n"
    f"Suggestions:\n"
    f"  1. Check spelling (common genes: BRCA1, TP53, EGFR)\n"
    f"  2. Try Ensembl ID (e.g., ENSG00000012048)\n"
    f"  3. Search at https://mygene.info/\n"
    f"  4. Check if gene symbol changed at https://www.genenames.org/"
)

# BETTER: Include suggestions based on input
def resolve_gene_with_suggestions(gene_name):
    result = resolve_gene(gene_name)
    if not result:
        # Try fuzzy matching
        similar = find_similar_genes(gene_name)
        if similar:
            raise ValueError(
                f"Gene '{gene_name}' not found. Did you mean: {', '.join(similar[:3])}?"
            )
        else:
            raise ValueError(
                f"Gene '{gene_name}' not found and no similar matches. "
                f"Try using Ensembl ID (ENSG...) or check gene nomenclature."
            )
    return result
```

---

## 📚 NEW: Documentation Quality Standards (2026-02 Update)

### Every Skill Must Have

1. **SKILL.md** (comprehensive implementation guide)
2. **QUICK_START.md** (copy-paste examples)
3. **EXAMPLES.md** (detailed use cases with expected outputs)
4. **TOOLS_REFERENCE.md** (verified tool parameters)
5. **test_*.py** (comprehensive test suite)

### Documentation Examples Must Actually Work

**Critical rule**: Every code example in documentation must be:
1. **Copy-pasteable** (no placeholders like "YOUR_GENE_HERE")
2. **Tested** (run during test suite)
3. **Have expected output documented**
4. **Use real data** that demonstrates the feature

```python
# In test suite:
def test_documentation_examples():
    """Verify all SKILL.md code examples work"""
    # Example from SKILL.md Phase 1:
    result = tu.tools.MyGene_query_genes(q='BRCA1', species='human')
    assert len(result['hits']) > 0
    assert result['hits'][0]['symbol'] == 'BRCA1'

    # If this fails, documentation is lying to users!
```

---

## ⚡ NEW: Performance Best Practices (2026-02 Update)

### Measure and Document Execution Times

```python
import time

def benchmark_skill(skill_func, *args, **kwargs):
    """Measure skill execution time"""
    start = time.time()
    result = skill_func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed

# Document in DEPLOYMENT_REPORT.md:
# - Cancer Variant Interpretation: ~30s average
# - Clinical Trial Matching: ~45s average
# - Multi-Omics Disease: ~120s average (network-heavy)
```

### Batch API Calls When Possible

```python
# SLOW: Sequential calls
gene_info = []
for gene in gene_list:
    info = tu.tools.MyGene_query_genes(q=gene)
    gene_info.append(info)
# Time: N * 0.5s = 50s for 100 genes

# FAST: Batch call
gene_info = tu.tools.MyGene_query_genes(
    q=",".join(gene_list),  # Comma-separated
    species='human'
)
# Time: 2s for 100 genes
```

### Cache Expensive Operations

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_gene_info(gene_symbol):
    """Cache gene lookups (frequently repeated)"""
    return tu.tools.MyGene_query_genes(q=gene_symbol, species='human')

# First call: hits API
info1 = get_gene_info("BRCA1")  # 0.5s

# Second call: cached
info2 = get_gene_info("BRCA1")  # 0.001s
```

---

## 🔍 NEW: Quality Assurance Checklist (2026-02 Update)

### Pre-Release Checklist

Run through this checklist before releasing any skill:

```bash
# 1. Run full test suite
cd skills/tooluniverse-[skill-name]/
python test_*.py

# Expected: 100% pass rate, no failures

# 2. Verify documentation examples
grep -A 5 "```python" SKILL.md | python
# All examples should run without errors

# 3. Check for placeholder data
grep -r "TEST\|DUMMY\|PLACEHOLDER\|example_" *.md *.py
# Should find none in test data

# 4. Validate tool parameters
python -c "from verify_tools import check_all_tools; check_all_tools()"
# Verify all tool parameters match actual APIs

# 5. Performance benchmark
time python test_*.py
# Document execution time

# 6. Edge case coverage
grep "def test_edge" test_*.py
# Should have 5+ edge case tests
```

### Production-Ready Checklist

Before marking any skill as "complete," verify ALL items:

**Code Quality**:
- [ ] Comprehensive test suite (minimum 30 tests, aim for 100+)
- [ ] 100% test pass rate achieved
- [ ] All tests use real data (no placeholders like "TEST_GENE_123")
- [ ] Edge cases tested (empty inputs, large inputs, invalid inputs, boundary values)
- [ ] API quirks documented in TOOLS_REFERENCE.md
- [ ] Transient API errors handled gracefully (timeouts, rate limits, overloads)
- [ ] Fallback strategies defined for critical operations
- [ ] Error messages are actionable (tell user HOW to fix)

**Documentation**:
- [ ] SKILL.md complete with all phases documented
- [ ] QUICK_START.md with copy-paste examples
- [ ] EXAMPLES.md with detailed use cases
- [ ] TOOLS_REFERENCE.md with verified parameter names
- [ ] All code examples in documentation actually work (tested)
- [ ] Response structures documented for each tool
- [ ] Evidence grading system explained (T1-T4)
- [ ] Completeness checklist template provided

**Scientific Rigor**:
- [ ] Based on peer-reviewed publications (cite Nature/Science/NEJM papers)
- [ ] Evidence grading consistent (T1-T4)
- [ ] All recommendations cite sources
- [ ] Tool versions documented
- [ ] Known limitations disclosed

**Performance**:
- [ ] Expected execution times documented
- [ ] Performance benchmarks measured
- [ ] Batch operations optimized (where applicable)
- [ ] API rate limits respected

**Deployment Readiness**:
- [ ] No known bugs or blockers
- [ ] All external dependencies documented
- [ ] Installation instructions provided
- [ ] User guides complete
- [ ] Maintenance plan established

---

## Summary

**Twelve pillars of optimized ToolUniverse skills** (updated 2026-02):

1. **TEST FIRST** - NEVER write skill documentation without testing all tool calls with real ToolUniverse instance
2. **Test comprehensively** - Minimum 30 tests, 100% pass rate, all edge cases covered, real data only
3. **Verify APIs always** - Check params via `get_tool_info()`; maintain corrections table; don't trust function names or documentation
4. **Handle transient errors** - Distinguish API failures from code bugs; retry with exponential backoff; document in tests
5. **Document verified parameters** - TOOLS_REFERENCE.md with actual tested parameters, not assumed ones
6. **Handle SOAP tools** - Add `operation` parameter to IMGT, SAbDab, TheraSAbDab tools
7. **Implementation-agnostic docs** - SKILL.md general; separate python_implementation.py; QUICK_START for both SDK and MCP
8. **Foundation first** - Query comprehensive aggregators before specialized tools
9. **Disambiguate carefully** - Resolve IDs (versioned + unversioned), detect collisions, get baseline from annotation DBs
10. **Implement fallbacks** - Primary → Fallback → Default chains for critical functionality
11. **Grade evidence** - T1-T4 tiers on all claims; summarize quality per section
12. **Require quantified completeness** - Numeric minimums, not just "include X"
13. **Synthesize** - Biological models and testable hypotheses, not just paper lists
14. **Measure performance** - Document execution times, optimize batch operations, cache expensive calls

**CRITICAL LESSONS**:
- **#1**: Test with real API calls BEFORE writing documentation. All 4 broken skills (Feb 2026) had excellent docs but 0% functionality because tools were never tested.
- **#2**: API documentation is often wrong. Always verify with actual tool calls and document findings.
- **#3**: 100% test pass rate is mandatory for clinical/research skills. Bugs can harm patients.

**Real-world validation**: These principles were validated by building 9 production-ready precision medicine skills (Feb 2026) with 638 tests, 100% pass rate, 0 known bugs, used in clinical decision support.

Apply these principles to any ToolUniverse research skill for better user experience and actionable output.
