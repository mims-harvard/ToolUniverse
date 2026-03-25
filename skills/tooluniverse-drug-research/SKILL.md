---
name: tooluniverse-drug-research
description: Generates comprehensive drug research reports with compound disambiguation, evidence grading, and mandatory completeness sections. Covers identity, chemistry, pharmacology, targets, clinical trials, safety, pharmacogenomics, and ADMET properties. Use when users ask about drugs, medications, therapeutics, or need drug profiling, safety assessment, or clinical development research.
---

# Drug Research Strategy

Comprehensive drug investigation using 50+ ToolUniverse tools across chemical databases, clinical trials, adverse events, pharmacogenomics, and literature.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Compound disambiguation FIRST** - Resolve identifiers before research
3. **Citation requirements** - Every fact must have inline source attribution
4. **Evidence grading** - Grade claims by evidence strength (T1-T4)
5. **Mandatory completeness** - All sections must exist, even if "data unavailable"
6. **English-first queries** - Always use English drug/compound names in tool calls, even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## Workflow Overview

### 1. Report-First Approach (MANDATORY)

**DO NOT** show the search process or tool outputs to the user. Instead:

1. **Create the report file FIRST** - `[DRUG]_drug_report.md` with all 11 section headers and `[Researching...]` placeholders. See [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) for the full template.
2. **Progressively update the report** - Replace placeholders with findings as you query each tool.
3. **Use ALL relevant tools** - Query multiple databases for each data type; cross-reference across sources.

### 2. Citation Requirements (MANDATORY)

Every piece of information MUST include its source. Use inline citations:
```markdown
*Source: PubChem via `PubChem_get_compound_properties_by_CID` (CID: 4091)*
```

### 3. Progressive Writing Workflow

```
Step 1:  Create report file with all section headers
Step 2:  Resolve compound identifiers -> Update Section 1
Step 3:  Query PubChem/ADMET-AI/DailyMed SPL -> Update Section 2 (Chemistry)
Step 4:  Query FDA Label MOA + ChEMBL + DGIdb -> Update Section 3 (Mechanism)
Step 5:  Query ADMET-AI tools -> Update Section 4 (ADMET)
Step 6:  Query ClinicalTrials.gov -> Update Section 5 (Clinical)
Step 7:  Query FAERS/DailyMed -> Update Section 6 (Safety)
Step 8:  Query PharmGKB -> Update Section 7 (Pharmacogenomics)
Step 9:  Query DailyMed/Orange Book -> Update Section 8 (Regulatory)
Step 10: Query PubMed/literature -> Update Section 9 (Literature)
Step 11: Synthesize findings -> Update Executive Summary & Section 10
Step 12: Document all sources -> Update Section 11 (Data Sources)
```

---

## Compound Disambiguation (Phase 1)

**CRITICAL**: Establish compound identity before any research.

### Identifier Resolution Chain

```
1. PubChem_get_CID_by_compound_name(compound_name)
   -> Extract: CID, canonical SMILES, formula

2. ChEMBL_search_compounds(query=drug_name)
   -> Extract: ChEMBL ID, pref_name

3. DailyMed_search_spls(drug_name)
   -> Extract: Set ID, NDC codes (if approved)

4. PharmGKB_search_drugs(query=drug_name)
   -> Extract: PharmGKB ID (PA...)
```

### Handle Naming Ambiguity

| Issue | Example | Resolution |
|-------|---------|------------|
| Salt forms | metformin vs metformin HCl | Note all CIDs; use parent compound |
| Isomers | omeprazole vs esomeprazole | Verify SMILES; separate entries if distinct |
| Prodrugs | enalapril vs enalaprilat | Document both; note conversion |
| Brand confusion | Different products same name | Clarify with user |

---

## Research Paths Summary

Each path has detailed tool chains and output examples in [REPORT_GUIDELINES.md](REPORT_GUIDELINES.md).

### PATH 1: Chemical Properties & CMC
**Tools**: PubChem properties -> ADMET-AI physicochemical -> ADMET-AI solubility -> DailyMed chemistry/description
**Output**: Physicochemical table, Lipinski assessment, QED score, salt forms, formulation comparison

### PATH 2: Mechanism & Targets
**Tools**: DailyMed MOA -> ChEMBL activities (NOT `ChEMBL_get_molecule_targets`) -> ChEMBL target details -> DGIdb -> PubChem bioactivity
**Critical**: Derive targets from activities filtered to pChEMBL >= 6.0. Avoid `ChEMBL_get_molecule_targets`.
**Output**: FDA MOA text, target table with UniProt/potency, selectivity profile

### PATH 3: ADMET Properties
**Tools**: ADMET-AI (bioavailability, BBB, CYP, clearance, toxicity)
**Fallback**: DailyMed clinical_pharmacology + pharmacokinetics + drug_interactions
**Critical**: If ADMET-AI fails, automatically use fallback. Never leave Section 4 empty.

### PATH 4: Clinical Trials
**Tools**: search_clinical_trials -> compute phase counts -> extract outcomes/AEs -> fda_pharmacogenomic_biomarkers
**Critical**: Section 5.2 must show actual counts by phase/status in table format.

### PATH 5: Post-Marketing Safety
**Tools**: FAERS (reactions, seriousness, outcomes, deaths, age) + DailyMed (DDI, dosing, warnings)
**Critical**: Include FAERS date window, seriousness breakdown, and limitations paragraph.

### PATH 6: Pharmacogenomics
**Tools**: PharmGKB (search -> details -> annotations -> guidelines)
**Fallback**: DailyMed pharmacogenomics section + PubMed literature

### PATH 7: Regulatory & Patents
**Tools**: FDA Orange Book (search, approval history, exclusivity, patents, generics) + DailyMed (special populations via LOINC codes)
**Note**: US-only data; document EMA/PMDA limitation.

### PATH 8: Real-World Evidence
**Tools**: ClinicalTrials.gov (OBSERVATIONAL studies) + PubMed (real-world, registry, surveillance)

### PATH 9: Comparative Analysis
**Tools**: Abbreviated tool chains for each comparator + head-to-head trial search + PubMed meta-analyses

---

## FDA Label Core Fields

For approved drugs, retrieve these DailyMed sections early (after getting set_id):

| Batch | Sections | Maps to Report |
|-------|----------|---------------|
| Phase 1 | mechanism_of_action, pharmacodynamics, chemistry | Sections 2-3 |
| Phase 2 | clinical_pharmacology, pharmacokinetics, drug_interactions | Sections 4, 6.5 |
| Phase 3 | warnings_and_cautions, adverse_reactions, dosage_and_administration | Sections 6, 8.2 |
| Phase 4 | pharmacogenomics, clinical_studies, description, inactive_ingredients | Sections 5, 7 |

---

## Fallback Chains

| Primary Tool | Fallback | Use When |
|--------------|----------|----------|
| `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` | Name not in PubChem |
| `ChEMBL_get_molecule_targets` | **Use `ChEMBL_search_activities` instead** | Always avoid this tool |
| `ChEMBL_get_activity` | `PubChem_get_bioactivity_summary_by_CID` | No ChEMBL ID |
| `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` | DailyMed timeout |
| `PharmGKB_search_drugs` | DailyMed PGx sections + PubMed | PharmGKB unavailable |
| `PharmGKB_get_dosing_guidelines` | DailyMed pharmacogenomics section | PharmGKB API error |
| `FAERS_count_reactions_by_drug_event` | Document "FAERS unavailable" + use label AEs | API error |
| `ADMETAI_*` (all tools) | DailyMed clinical_pharmacology + pharmacokinetics | Invalid SMILES or API error |

---

## Quick Reference: Tools by Use Case

| Use Case | Primary Tool | Fallback | Evidence |
|----------|--------------|----------|----------|
| Name -> CID | `PubChem_get_CID_by_compound_name` | `ChEMBL_search_drugs` | T1 |
| Properties | `PubChem_get_compound_properties_by_CID` | ADMET-AI physicochemical | T1/T2 |
| FDA MOA | `DailyMed_parse_clinical_pharmacology` (mechanism_of_action) | - | T1 |
| Targets | `ChEMBL_search_activities` -> `ChEMBL_get_target` | `DGIdb_get_drug_info` | T1 |
| ADMET | `ADMETAI_predict_*` (5 tools) | DailyMed PK sections | T2/T1 |
| Trials | `search_clinical_trials` | - | T1 |
| Trial outcomes | `extract_clinical_trial_outcomes` | - | T1 |
| FAERS | `FAERS_count_reactions_by_drug_event` | Label adverse_reactions | T1 |
| Dose mods | `DailyMed_parse_clinical_pharmacology` (dosage, warnings) | - | T1 |
| PGx | `PharmGKB_search_drugs` | DailyMed PGx + PubMed | T2/T1 |
| Label | `DailyMed_search_spls` | `PubChem_get_drug_label_info_by_CID` | T1 |
| Literature | `PubMed_search_articles` | `EuropePMC_search_articles` | Varies |
| Regulatory | `FDA_OrangeBook_*` tools | DailyMed label data | T1 |

See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for the complete tool listing with parameters and input format requirements.

---

## Type Normalization

Many tools require **string** inputs. Always convert IDs before API calls:
- ChEMBL IDs, PubMed IDs, NCT IDs: convert int -> str
- SMILES for ADMET-AI: pass as list `["SMILES_STRING"]`
- FAERS drug names: use UPPERCASE (e.g., `"METFORMIN"`)
- ChEMBL IDs: full format `"CHEMBL1431"` not `"1431"`
- PharmGKB IDs: PA prefix `"PA450657"` not `"450657"`

---

## Common Use Cases

| Use Case | Primary Sections | Light Sections |
|----------|------------------|----------------|
| Approved Drug Profile | All 11 sections | None |
| Investigational Compound | 1, 2, 3, 4, 9 | 5, 6, 7, 8 |
| Safety Review | 1, 5, 6, 7, 9 | 2, 3, 4, 8 |
| ADMET Assessment | 1, 2, 4 | 3, 5, 6, 7, 8, 9 |
| Clinical Development Landscape | 1, 5, 9 | 2, 3, 4, 6, 7, 8 |

Always maintain all section headers but adjust depth based on query focus and data availability.

---

## When NOT to Use This Skill

- **Target research** -> Use target-intelligence-gatherer skill
- **Disease research** -> Use disease-research skill
- **Literature-only** -> Use literature-deep-research skill
- **Single property lookup** -> Call tool directly
- **Structure similarity search** -> Use `PubChem_search_compounds_by_similarity` directly

---

## Additional Resources

- **Report template**: [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Initial file template, citation format, evidence grading, scorecard, audit template
- **Report guidelines**: [REPORT_GUIDELINES.md](REPORT_GUIDELINES.md) - Detailed section-by-section instructions with output examples
- **Tool reference**: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - Complete tool listing with parameters and input formats
- **Verification checklist**: [CHECKLIST.md](CHECKLIST.md) - Section-by-section pre-delivery verification
- **Examples**: [EXAMPLES.md](EXAMPLES.md) - Detailed workflow examples for different use cases
