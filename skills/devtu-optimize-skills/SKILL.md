---
name: devtu-optimize-skills
description: Optimize ToolUniverse skills for better report quality, evidence handling, and user experience. Apply patterns like tool verification, foundation data layers, disambiguation-first, evidence grading, quantified completeness, and report-only output. Use when reviewing skills, improving existing skills, or creating new ToolUniverse research skills.
---

# Optimizing ToolUniverse Skills

Best practices for high-quality research skills with evidence grading and source attribution.

## Tool Quality Standards

1. **Error messages must be actionable** — tell the user what went wrong AND what to do
2. **Schema must match API reality** — run `python3 -m tooluniverse.cli run <Tool> '<json>'` to verify
3. **Coverage transparency** — state what data is NOT included
4. **Input validation before API calls** — don't silently send invalid values
5. **Cross-tool routing** — name the correct tool when query is out-of-scope
6. **No silent parameter dropping** — if a parameter is ignored, say so

## Core Principles (13 Patterns)

Full details: [references/optimization-patterns.md](references/optimization-patterns.md)

| # | Pattern | Key Idea |
|---|---------|----------|
| 1 | Tool Interface Verification | `get_tool_info()` before first call; maintain corrections table |
| 2 | Foundation Data Layer | Query aggregator (Open Targets, PubChem) FIRST |
| 3 | Versioned Identifiers | Capture both `ENSG00000123456` and `.12` version |
| 4 | Disambiguation First | Resolve IDs, detect collisions, build negative filters |
| 5 | Report-Only Output | Narrative in report; methodology in appendix only if asked |
| 6 | Evidence Grading | T1 (mechanistic) → T2 (functional) → T3 (association) → T4 (mention) |
| 7 | Quantified Completeness | Numeric minimums per section (>=20 PPIs, top 10 tissues) |
| 8 | Mandatory Checklist | All sections exist, even if "Limited evidence" |
| 9 | Aggregated Data Gaps | Single section consolidating all missing data |
| 10 | Query Strategy | High-precision seeds → citation expansion → collision-filtered broad |
| 11 | Tool Failure Handling | Primary → Fallback 1 → Fallback 2 → document unavailable |
| 12 | Scalable Output | Narrative report + JSON/CSV bibliography |
| 13 | Synthesis Sections | Biological model + testable hypotheses, not just paper lists |

## Optimized Skill Workflow

```
Phase -1: Tool Verification (check params)
Phase  0: Foundation Data (aggregator query)
Phase  1: Disambiguation (IDs, collisions, baseline)
Phase  2: Specialized Queries (fill gaps)
Phase  3: Report Synthesis (evidence-graded narrative)
```

## Testing Standards

Full details: [references/testing-standards.md](references/testing-standards.md)

**Critical rule**: NEVER write skill docs without testing all tool calls first.

- 30+ tests per skill, 100% pass rate
- All tests use real data (no placeholders)
- Phase + integration + edge case tests
- SOAP tools (IMGT, SAbDab, TheraSAbDab) need `operation` parameter
- Distinguish transient errors (retry) from real bugs (fix)
- API docs are often wrong — always verify with actual calls

## Pattern 14: Reasoning Frameworks Over Tool Catalogs (CRITICAL)

Skills that just list tools ("call A, then B, then C") score 3-5/10 in usefulness tests. Skills that explain HOW to interpret and combine data score 7-9/10. Every skill MUST include:

### 14a. Interpretation Tables
Map raw API data to biological/clinical meaning. Don't just retrieve — explain.

| Bad (tool catalog) | Good (reasoning framework) |
|---|---|
| "Get GO terms from MGnify" | GO terms → interpretation table: butyrate genes = barrier integrity, LPS genes = inflammation |
| "Get DepMap dependency scores" | Score < -0.5 = essential, but pan-essential = bad drug target (toxicity); selective = good target |
| "Get FAERS counts" | PRR > 5 = strong signal, but signal ≠ causation (channeling bias, notoriety bias) |

### 14b. Synthesis Phases
Every multi-phase skill needs a final phase that answers "so what?" — not just collecting data:
- "What changed and why does it matter?"
- "Is this cause or consequence?"
- "What's the actionable recommendation?"

### 14c. Honest Limitations
If a tool API can't deliver what the skill promises, say so explicitly. Don't describe aspirational capabilities. Example: "DepMap_get_gene_dependencies returns gene metadata only, NOT per-cell-line CRISPR scores."

## Pattern 15: Computational Procedures When Tools Can't Help

Some scientific analyses require computation, not just API queries. When no tool exists for a capability, embed a Python code procedure directly in the skill using packages available in ToolUniverse (pandas, scipy, numpy, statsmodels, biopython, networkx).

### When to use computational procedures:
| Gap | Procedure | Packages |
|-----|-----------|----------|
| API doesn't return needed data (e.g., DepMap scores) | Download CSV + pandas analysis | pandas |
| Statistical testing (differential abundance, enrichment) | scipy.stats + FDR correction | scipy, statsmodels |
| Sequence analysis (alignment, conservation) | Biopython SeqIO + pairwise alignment | biopython |
| Chemical similarity (analog search, fingerprints) | RDKit fingerprints + Tanimoto | rdkit (visualization extra) |
| Network analysis (hub genes, clustering) | NetworkX graph metrics | networkx |
| Scoring algorithms (ACMG classification, viability scores) | Custom Python functions | built-in |
| Dose feasibility (Cmax vs IC50 comparison) | Numerical comparison + PK data | pandas, numpy |

### Template for computational procedures in skills:
```markdown
**Computational procedure: [Name]**
[When to use this: explain the gap it fills]

\`\`\`python
# [What this computes]
# Requires: [packages] (included in ToolUniverse dependencies)
import pandas as pd
from scipy.stats import mannwhitneyu

# Input: [describe expected input format]
# Output: [describe output]
# [Full working code with example data]
\`\`\`

[Interpretation guidance for the output]
```

### Key rules for computational procedures:
1. **Only use packages in ToolUniverse dependencies** (pyproject.toml): pandas, scipy, numpy, networkx, requests, biopython (optional extra)
2. **Include example data** so the procedure is immediately testable
3. **Explain the output** — a code block without interpretation is useless
4. **Note when external data download is needed** (e.g., DepMap CSV from depmap.org)

### Pattern 15b: Download-and-Process for Datasets Without REST APIs

Many critical scientific datasets have NO REST API but provide bulk download files. Skills should include concrete download-and-process instructions when this is the only path to essential data.

**Template for download-and-process procedures:**

```markdown
**Step 1: Download data files**
- URL: [exact download page URL]
- Files needed: [filename] (~[size]) — [what it contains]
- Registration: [required/not required]
- Update frequency: [quarterly/annually/etc.]

**Step 2: Process with Python**
[Working code with pandas/scipy that loads the CSV and produces the analysis]

**Step 3: Interpret results**
[Table mapping output values to biological/clinical meaning]

**When files are not available**: [Fallback strategy using API tools]
```

**Known download-only datasets that skills reference:**

| Dataset | Download URL | Files | Used By |
|---------|-------------|-------|---------|
| **DepMap CRISPR** | depmap.org/portal/download/all/ | CRISPRGeneEffect.csv (~300MB), Model.csv (~2MB) | functional-genomics, cell-line-profiling |
| **TCGA clinical** | portal.gdc.cancer.gov | Clinical + mutation TSVs | cancer-genomics-tcga |
| **GTEx expression** | gtexportal.org/home/downloads | GTEx_Analysis_v8_Annotations.csv | expression-data-retrieval |
| **ClinGen gene-disease** | clinicalgenome.org/docs/ | gene_curation_list.tsv | variant-interpretation |
| **gnomAD constraint** | gnomad.broadinstitute.org/downloads | constraint metrics TSV | functional-genomics |

**Critical rule**: Always include a fallback for when the download is unavailable (user may not have registration, file may be too large, etc.). The fallback should use available API tools even if they provide less complete data.

## Common Anti-Patterns

| Anti-Pattern | Fix |
|-------------|-----|
| "Search Log" reports | Keep methodology internal; report findings only |
| Missing disambiguation | Add collision detection; build negative filters |
| No evidence grading | Apply T1-T4 grades; label each claim |
| Empty sections omitted | Include with "None identified" |
| No synthesis | Add biological model + hypotheses |
| Silent failures | Document in Data Gaps; implement fallbacks |
| Wrong tool parameters | Verify via `get_tool_info()` before calling |
| GTEx returns nothing | Try versioned ID `ENSG*.version` |
| No foundation layer | Query aggregator first |
| Untested tool calls | Test-driven: test script FIRST |
| **Tool catalog without interpretation** | **Add interpretation tables explaining what data means** |
| **Aspirational capabilities** | **Be honest when APIs can't deliver; add computational procedure instead** |
| **Missing statistical analysis** | **Add scipy/pandas code procedure for computation the tools can't do** |

## Quick Fixes for User Complaints

| Complaint | Fix |
|-----------|-----|
| "Report too short" | Add Phase 0 foundation + Phase 1 disambiguation |
| "Too much noise" | Add collision filtering |
| "Can't tell what's important" | Add T1-T4 evidence tiers |
| "Missing sections" | Add mandatory checklist with minimums |
| "Too long/unreadable" | Separate narrative from JSON |
| "Just a list of papers" | Add synthesis sections |
| "Tool failed, no data" | Add retry + fallback chains |

## Skill Template

```markdown
---
name: [domain]-research
description: [What + when triggers]
---

# [Domain] Research

## Workflow
Phase -1: Tool Verification → Phase 0: Foundation → Phase 1: Disambiguate
→ Phase 2: Search → Phase 3: Report

## Phase -1: Tool Verification
[Parameter corrections table]

## Phase 0: Foundation Data
[Aggregator query]

## Phase 1: Disambiguation
[IDs, collisions, baseline]

## Phase 2: Specialized Queries
[Query strategy, fallbacks]

## Phase 3: Report Synthesis
[Evidence grading, mandatory sections]

## Output Files
- [topic]_report.md, [topic]_bibliography.json

## Quantified Minimums
[Numbers per section]

## Completeness Checklist
[Required sections with checkboxes]
```

## Additional References

- **Detailed patterns**: [references/optimization-patterns.md](references/optimization-patterns.md)
- **Testing standards**: [references/testing-standards.md](references/testing-standards.md)
- **Case studies** (4 real fixes): [references/case-studies.md](references/case-studies.md)
- **Checklists** (review + release): [references/checklists.md](references/checklists.md)
