---
name: tooluniverse-infectious-disease
description: Rapid pathogen characterization and drug repurposing analysis for infectious disease outbreaks. Identifies pathogen taxonomy, essential proteins, predicts structures, and screens existing drugs via docking. Use when facing novel pathogens, emerging infections, or needing rapid therapeutic options during outbreaks.
---

# Infectious Disease Outbreak Intelligence

Rapid response system for emerging pathogens using taxonomy analysis, target identification, structure prediction, and computational drug repurposing.

**KEY PRINCIPLES**:
1. **Speed is critical** - Optimize for rapid actionable intelligence
2. **Target essential proteins** - Focus on conserved, essential viral/bacterial proteins
3. **Leverage existing drugs** - Prioritize FDA-approved compounds for repurposing
4. **Structure-guided** - Use NvidiaNIM for rapid structure prediction and docking
5. **Evidence-graded** - Grade repurposing candidates by evidence strength
6. **Actionable output** - Prioritized drug candidates with rationale
7. **English-first queries** - Always use English terms in tool calls; respond in user's language

---

## When to Use

Apply when user asks:
- "New pathogen detected - what drugs might work?"
- "Emerging virus [X] - therapeutic options?"
- "Drug repurposing candidates for [pathogen]"
- "What do we know about [novel coronavirus/bacteria]?"
- "Essential targets in [pathogen] for drug development"
- "Can we repurpose [drug] against [pathogen]?"

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

1. Create `[PATHOGEN]_outbreak_intelligence.md` FIRST with section headers
2. Progressively update as data is gathered
3. Output separate files: `[PATHOGEN]_drug_candidates.csv`, `[PATHOGEN]_target_proteins.csv`

### 2. Citation Requirements (MANDATORY)

Every finding must have inline source attribution:
```markdown
### Target: RNA-dependent RNA polymerase (RdRp)
- **UniProt**: P0DTD1 (NSP12)
- **Essentiality**: Required for replication
*Source: UniProt via `UniProt_search`, literature review*
```

---

## Phase 0: Tool Verification

### Known Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `NCBIDatasets_get_taxonomy` | `name` | `tax_id` (integer) or use `BVBRC_search_taxonomy` for keyword search |
| `UniProt_search` | `name` | `query` |
| `ChEMBL_search_targets` | `query`, `target` | `pref_name__contains` (substring match) |
| `NvidiaNIM_diffdock` | `protein_file` | `protein` (content) |
| `drugbank_full_search` | _(may fail)_ | Use `drugbank_vocab_search` as primary DrugBank lookup |

> **PubMed tip**: Use `sort="relevance"` (default) not `sort="pub_date"` — date-sorted queries can return empty for narrow topics. Tool name: `PubMed_search_articles`.
> **FDA labels**: Use `FDA_get_drug_label_info_by_field_value` with targeted `return_fields` to avoid oversized responses from `OpenFDA_search_drug_labels`.

---

## Workflow Overview

```
Phase 1: Pathogen Identification
├── Taxonomic classification (NCBI Taxonomy)
├── Closest relatives (for knowledge transfer)
├── Genome/proteome availability
└── OUTPUT: Pathogen profile
    |
Phase 2: Target Identification
├── Essential genes/proteins (UniProt)
├── Conservation across strains
├── Druggability assessment (ChEMBL)
└── OUTPUT: Prioritized target list (scored by essentiality/conservation/druggability/precedent)
    |
Phase 3: Structure Prediction (NvidiaNIM)
├── AlphaFold2/ESMFold for targets
├── Binding site identification
├── Quality assessment (pLDDT)
└── OUTPUT: Target structures (docking-ready if pLDDT > 70)
    |
Phase 4: Drug Repurposing Screen
├── Approved drugs for related pathogens (ChEMBL)
├── Broad-spectrum antivirals/antibiotics
├── Docking screen (NvidiaNIM_diffdock)
└── OUTPUT: Ranked candidate drugs
    |
Phase 4.5: Pathway Analysis
├── KEGG: Pathogen metabolism pathways
├── Essential metabolic targets
├── Host-pathogen interaction pathways
└── OUTPUT: Pathway-based drug targets
    |
Phase 5: Literature Intelligence
├── PubMed: Published outbreak reports
├── BioRxiv/MedRxiv: Recent preprints (CRITICAL for outbreaks)
├── ArXiv: Computational/ML preprints
├── OpenAlex: Citation tracking
├── ClinicalTrials.gov: Active trials
└── OUTPUT: Evidence synthesis
    |
Phase 6: Report Synthesis
├── Top drug candidates with evidence grades
├── Clinical trial opportunities
├── Recommended immediate actions
└── OUTPUT: Final report
```

---

## Phase Summaries

### Phase 1: Pathogen Identification
Classify via NCBI Taxonomy (query param). Identify related pathogens with existing drugs for knowledge transfer. Determine genome/proteome availability.

### Phase 2: Target Identification
Search UniProt for pathogen proteins (reviewed). Check ChEMBL for drug precedent. Score targets by: Essentiality (30%), Conservation (25%), Druggability (25%), Drug precedent (20%). Aim for 5+ targets.

### Phase 3: Structure Prediction
Use NvidiaNIM AlphaFold2 for top 3 targets. Assess pLDDT confidence. Only dock structures with pLDDT > 70 (active site > 90 preferred). Fallback: alphafold_get_prediction or NvidiaNIM_esmfold.

### Phase 4: Drug Repurposing Screen
Source candidates from: related pathogen drugs, broad-spectrum antivirals, target class drugs (DGIdb). Dock top 20+ candidates via NvidiaNIM_diffdock. Rank by docking score and evidence tier.

### Phase 4.5: Pathway Analysis
Use KEGG to identify essential metabolic pathways. Map host-pathogen interaction points. Identify pathway-based drug targets beyond direct protein inhibition.

### Phase 5: Literature Intelligence
Search PubMed (peer-reviewed), BioRxiv/MedRxiv (preprints - critical for outbreaks), ArXiv (computational), ClinicalTrials.gov (active trials). Track citations via OpenAlex. Note: preprints are NOT peer-reviewed.

### Phase 6: Report Synthesis
Aggregate all findings into final report. Grade every candidate. Provide 3+ immediate actions, clinical trial opportunities, and research priorities.

---

## Evidence Grading

| Tier | Symbol | Criteria | Example |
|------|--------|----------|---------|
| **T1** | [T1] | FDA approved for this pathogen | Remdesivir for COVID |
| **T2** | [T2] | Clinical trial evidence OR approved for related pathogen | Favipiravir |
| **T3** | [T3] | In vitro activity OR strong docking + mechanism | Sofosbuvir |
| **T4** | [T4] | Computational prediction only | Novel docking hits |

---

## Completeness Checklist

### Phase 1: Pathogen ID
- [ ] Taxonomic classification complete
- [ ] Related pathogens identified
- [ ] Genome/proteome availability noted

### Phase 2: Targets
- [ ] 5+ targets identified
- [ ] Essentiality documented
- [ ] Conservation assessed
- [ ] Drug precedent checked

### Phase 3: Structures
- [ ] Structures predicted for top 3 targets
- [ ] pLDDT confidence reported
- [ ] Binding sites identified

### Phase 4: Drug Screen
- [ ] 20+ candidates screened
- [ ] FDA-approved drugs prioritized
- [ ] Docking scores reported
- [ ] Top 5 candidates detailed

### Phase 5: Literature
- [ ] Recent papers summarized
- [ ] Active trials listed
- [ ] Resistance data noted

### Phase 6: Recommendations
- [ ] 3+ immediate actions
- [ ] Clinical trial opportunities
- [ ] Research priorities

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `NvidiaNIM_alphafold2` | `alphafold_get_prediction` | `NvidiaNIM_esmfold` |
| `NvidiaNIM_diffdock` | `NvidiaNIM_boltz2` | Manual docking |
| `NCBI_Taxonomy_search` | `UniProt_taxonomy` | Manual classification |
| `ChEMBL_search_drugs` | `drugbank_vocab_search` | PubChem bioassays |

---

## References

| File | Contents |
|------|----------|
| [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) | Complete tool documentation |
| [phase_details.md](phase_details.md) | Detailed code examples and procedures for each phase |
| [report_template.md](report_template.md) | Report template with section headers, checklist, and evidence grading |
| [CHECKLIST.md](CHECKLIST.md) | Pre-delivery verification checklist (quality, citations, docking) |
| [EXAMPLES.md](EXAMPLES.md) | Full worked examples (coronavirus, CRKP, limited-info scenarios) |
