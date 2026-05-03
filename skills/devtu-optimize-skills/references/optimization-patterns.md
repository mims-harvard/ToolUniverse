# Optimization Patterns

Detailed patterns for improving ToolUniverse skill quality.

## Table of Contents
- [Tool Interface Verification](#1-tool-interface-verification)
- [Foundation Data Layer](#2-foundation-data-layer)
- [Versioned Identifier Handling](#3-versioned-identifier-handling)
- [Disambiguation Before Research](#4-disambiguation-before-research)
- [Report-Only Output](#5-report-only-output)
- [Evidence Grading](#6-evidence-grading)
- [Quantified Completeness](#7-quantified-completeness)
- [Mandatory Completeness Checklist](#8-mandatory-completeness-checklist)
- [Aggregated Data Gaps](#9-aggregated-data-gaps)
- [Query Strategy Optimization](#10-query-strategy-optimization)
- [Tool Failure Handling](#11-tool-failure-handling)
- [Scalable Output Structure](#12-scalable-output-structure)
- [Synthesis Sections](#13-synthesis-sections)

---

## 1. Tool Interface Verification

Verify tool parameters before calling unfamiliar tools:
```python
tool_info = tu.tools.get_tool_info(tool_name="Reactome_map_uniprot_to_pathways")
# Reveals: takes `id` not `uniprot_id`
```

**Known corrections table**:

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` | `id` |
| `ensembl_get_xrefs` | `gene_id` | `id` |
| `GTEx_get_median_gene_expression` | `gencode_id` only | `gencode_id` + `operation="median"` |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |
| `RxNorm_get_drug_names` | `query` | `drug_name` |
| `drugbank_*` | `drug_name_or_id` | `query` |
| `FAERS_count_reactions_by_drug_event` | `drug_name` | `medicinalproduct` |
| SOAP tools (IMGT, SAbDab, TheraSAbDab) | missing | `operation` (required first param) |

**Rule**: Before calling any tool for the first time, verify params via `get_tool_info()`.

## 2. Foundation Data Layer

Query a comprehensive aggregator FIRST before specialized tools:

| Domain | Foundation Source | What It Provides |
|--------|-------------------|------------------|
| Drug targets | Open Targets | Diseases, tractability, safety, drugs, GO, publications |
| Chemicals | PubChem | Properties, bioactivity, patents, literature |
| Diseases | Open Targets / OMIM | Genes, drugs, phenotypes, literature |
| Genes | MyGene / Ensembl | Annotations, cross-refs, GO, pathways |

**Pattern**: Phase 0 (aggregator) → Phase 1 (disambiguate) → Phase 2 (specialized) → Phase 3 (report)

## 3. Versioned Identifier Handling

Capture BOTH versioned and unversioned forms during ID resolution:
```python
ids = {
    'ensembl': 'ENSG00000123456',              # Most APIs
    'ensembl_versioned': 'ENSG00000123456.12'   # GTEx, GENCODE
}
```
Fallback: try unversioned first → versioned if empty → document which worked.

## 4. Disambiguation Before Research

Add disambiguation phase before literature search:
1. Resolve official identifiers (UniProt, Ensembl, NCBI Gene, ChEMBL)
2. Gather synonyms and aliases
3. Detect naming collisions (search `"[SYMBOL]"[Title]`, check if >20% off-topic)
4. Build negative filters for collisions
5. Get baseline profile from annotation DBs (not literature)

## 5. Report-Only Output

| File | Content | When |
|------|---------|------|
| `[topic]_report.md` | Narrative findings only | Always |
| `[topic]_bibliography.json` | Full deduplicated papers | Always |
| `methods_appendix.md` | Search methodology | Only if requested |

DO: "The literature reveals three main therapeutic approaches..."
DON'T: "I searched PubMed, OpenAlex, and EuropePMC, finding 342 papers..."

## 6. Evidence Grading

| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | three stars | Mechanistic study with direct evidence |
| T2 | two stars | Functional study (knockdown, overexpression) |
| T3 | one star | Association (screen hit, GWAS, correlation) |
| T4 | no stars | Mention (review, text-mined, peripheral) |

Required in: Executive Summary, Disease Associations, Key Papers table, Recommendations.

## 7. Quantified Completeness

| Section | Minimum Data | If Not Met |
|---------|--------------|------------|
| PPIs | >=20 interactors | Explain why fewer |
| Expression | Top 10 tissues with values | Note "limited data" |
| Disease | Top 10 associations with scores | Note if fewer |
| Variants | All 4 constraint scores | Note which unavailable |
| Literature | Total + 5-year trend + 3-5 key papers | Note if sparse |

## 8. Mandatory Completeness Checklist

All sections must exist, even if "Limited evidence":
- Identity: IDs resolved, synonyms, collisions
- Biology: architecture, localization, expression (>=10 tissues), pathways (>=10)
- Mechanism: core function with evidence, model organisms, key assays
- Disease/Clinical: variants, constraint scores (all 4), disease links (>=10)
- Druggability: tractability, known drugs, probes, clinical pipeline
- Synthesis: themes (>=3 papers each), open questions, biological model, hypotheses (>=3)

## 9. Aggregated Data Gaps

Consolidate all gaps into one section:
```markdown
## Data Gaps & Limitations
| Section | Expected | Actual | Reason | Alternative |
|---------|----------|--------|--------|-------------|
| PPIs | >=20 | 8 | Novel target | Literature review |
| Expression | GTEx TPM | None | ID not recognized | HPA data |
```

## 10. Query Strategy Optimization

Three-step collision-aware strategy:
1. **High-precision seeds** (15-30 papers): `"[SYMBOL]"[Title] AND mechanism`
2. **Citation expansion**: forward (cited_by), related, backward (references)
3. **Collision-filtered broad**: apply negative filters for known collisions

## 11. Tool Failure Handling

| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| PubMed_get_cited_by | EuropePMC_get_citations | OpenAlex |
| GTEx_* | HPA_* | Note unavailable |
| ChEMBL_get_target_activities | GtoPdb_get_target_ligands | OpenTargets |

NEVER silently skip failed tools. Document in Data Gaps section.

## 12. Scalable Output Structure

Narrative report (~20-50 pages): executive summary, key findings by theme, top 20-50 papers, conclusions.
Bibliography files (unlimited): JSON + CSV with evidence tiers, themes, OA status.

## 13. Synthesis Sections

Required:
- **Biological Model** (3-5 paragraphs): integrate all evidence
- **Testable Hypotheses** (>=3): hypothesis, perturbation, readout, expected result
- **Suggested Experiments**: how to test each hypothesis
