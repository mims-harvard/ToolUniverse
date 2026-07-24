# Literature Deep Research - Quick Reference

**Enhanced strategy with target disambiguation, evidence grading, and mandatory completeness.**

---

## Workflow Summary

```
1. CLARIFY → Target type? Scope? Aliases? Methods appendix needed?
2. DISAMBIGUATE → Resolve IDs, find collisions, gather baseline profile
3. SEARCH → High-precision seeds → Citation expansion → Collision-filtered broad
4. GRADE → Apply evidence tiers (T1-T4) to all claims
5. REPORT → Mandatory sections, biological model, testable hypotheses
```

---

## Phase 1: Target Disambiguation (Default ON)

### Tools to Use

| Data Type | Primary Tool | Fallback |
|-----------|--------------|----------|
| UniProt ID | `UniProt_search` | `proteins_api_get_protein` |
| Ensembl ID | `UniProt_id_mapping` | `ensembl_lookup_gene` |
| Domains | `InterPro_get_protein_domains` | UniProt features |
| Expression | `GTEx_get_median_gene_expression` | `HPA_get_rna_expression_by_source` |
| GO Terms | `GO_get_annotations_for_gene` | `OpenTargets_get_target_gene_ontology_by_ensemblID` |
| Pathways | `Reactome_map_uniprot_to_pathways` | `kegg_get_gene_info` |
| Location | `HPA_get_subcellular_location` | UniProt localization |

### Collision Detection

```
1. Search: "[SYMBOL]"[Title] in PubMed (first 20 results)
2. If >20% off-topic → identify collision terms
3. Build filter: NOT [collision1] NOT [collision2]
```

---

## Phase 2: Query Strategy

### Step 1: High-Precision Seeds
```
"[GENE_SYMBOL]"[Title] AND (mechanism OR function OR structure)
"[FULL_PROTEIN_NAME]"[Title]
```

### Step 2: Citation Expansion (especially for sparse targets)
```
PubMed_get_cited_by(pmid) → Forward citations
EuropePMC_get_citations(pmid) → Fallback for forward
PubMed_get_related(pmid) → Related papers
EuropePMC_get_references(pmid) → Backward citations
```

### Step 3: Collision-Filtered Broad
```
"[GENE]" AND ([pathway] OR [function]) NOT [collision_term]
```

---

## Evidence Grading (Apply to ALL Claims)

| Tier | Label | Criteria |
|------|-------|----------|
| **T1** | ★★★ Mechanistic | Direct experimental evidence on target |
| **T2** | ★★☆ Functional | Knockdown/overexpression phenotype |
| **T3** | ★☆☆ Association | Screen hit, GWAS, correlation |
| **T4** | ☆☆☆ Mention | Review, text-mining, peripheral |

**In report**:
```markdown
Target X regulates pathway Y [★★★: PMID:12345678] through direct 
phosphorylation [★★☆: PMID:23456789].
```

---

## Mandatory Report Sections (ALL Required)

| # | Section | Must Include |
|---|---------|--------------|
| 1 | Identity/Aliases | IDs, synonyms, collisions |
| 2 | Protein Architecture | Domains, isoforms, sites |
| 3 | Complexes/Partners | Interactors with evidence |
| 4 | Subcellular Localization | Locations with confidence |
| 5 | Expression | Top tissues, specificity |
| 6 | Core Mechanisms | Function with evidence grades |
| 7 | Model Organism Evidence | KO phenotypes or "none found" |
| 8 | Human Genetics/Variants | Constraints, ClinVar, GWAS |
| 9 | Disease Links | With evidence strength |
| 10 | Pathogens | Or "none identified" |
| 11 | Key Assays/Readouts | Biochemical, cellular, in vivo |
| 12 | Research Themes | ≥3 papers/theme or "limited" |
| 13 | Open Questions/Gaps | What's unknown |
| 14 | Biological Model | + 3-5 testable hypotheses |
| 15 | Conclusions | Confidence assessment |

---

## Theme Extraction

| Papers | Status |
|--------|--------|
| ≥10 | Major theme (full section) |
| 3-9 | Minor theme (subsection) |
| <3 | Note as "limited evidence" |

**Standard themes** (adapt to target):
- Core function / Mechanism
- Disease relevance
- Signaling / Pathways
- Trafficking / Localization
- Genetics / Variants
- Infection / Immunity
- Methodology / Tools

---

## Output Files

1. **`[topic]_report.md`** - Main narrative (DEFAULT)
2. **`[topic]_bibliography.json`** - Full deduplicated papers (ALWAYS)
3. **`methods_appendix.md`** - Methodology (ONLY if requested)

---

## Tool Failure Handling

```
Attempt 1 → fails → wait 2s → Attempt 2 → fails → wait 5s → Fallback tool
```

| Primary | Fallback |
|---------|----------|
| `PubMed_get_cited_by` | `EuropePMC_get_citations` |
| `PubMed_get_related` | `SemanticScholar_search_papers` |
| `GTEx_*` | `HPA_*` |
| `Unpaywall_check_oa_status` | Europe PMC/OpenAlex OA flags |

---

## OA Handling

**With Unpaywall email**: Full OA check for all DOIs
**Without**: Best-effort using:
- Europe PMC `isOpenAccess` field
- PMC papers (all OA)
- OpenAlex `is_oa` field

Label: `*OA Status: Best-effort*`

---

## Completeness Checklist

Before delivery, verify ALL:

### Identity
- [ ] UniProt, Ensembl, NCBI, ChEMBL IDs
- [ ] All synonyms documented
- [ ] Collisions handled

### Biology
- [ ] Domains + architecture
- [ ] Localization
- [ ] Expression profile
- [ ] GO terms + pathways
- [ ] Interactors

### Mechanism
- [ ] Core function (with evidence grades)
- [ ] Model organism data (or "none")
- [ ] Assays described

### Disease
- [ ] Constraint scores + interpretation
- [ ] Variants (ClinVar, gnomAD)
- [ ] Disease links (graded by evidence)
- [ ] Pathogens (or "none")

### Synthesis
- [ ] Themes with ≥3 papers each
- [ ] Open questions listed
- [ ] Biological model written
- [ ] ≥3 testable hypotheses
- [ ] Conclusions + confidence

### Technical
- [ ] All claims have sources
- [ ] Evidence grades applied
- [ ] Bibliography file created
- [ ] Limitations noted

---

## DO vs DON'T

| DO | DON'T |
|----|-------|
| Resolve IDs first | Jump straight to literature |
| Grade all evidence | Treat all papers equally |
| State "limited evidence" | Leave sections blank |
| Generate hypotheses | Stop at description |
| Keep methodology internal | Show search process |
| Use fallback tools | Give up on first failure |
| Check for collisions | Assume gene name is unambiguous |

---

## Communication Style

**Brief progress updates**:
- "Resolving target identifiers..."
- "Building core paper set..."
- "Grading evidence and clustering themes..."

**Never expose**:
- Raw tool outputs
- Deduplication stats
- Round-by-round search details
- Database failure logs

**Report = Deliverable (not search log)**
