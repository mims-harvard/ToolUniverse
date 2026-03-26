---
name: tooluniverse-gwas-drug-discovery
description: Transform GWAS signals into actionable drug targets and repurposing opportunities. Performs locus-to-gene mapping, target druggability assessment, existing drug identification, safety profile evaluation, and clinical trial matching. Use when discovering drug targets from GWAS data, finding drug repurposing opportunities from genetic associations, or translating GWAS findings into therapeutic leads.
---

# GWAS-to-Drug Target Discovery

Transform genome-wide association studies (GWAS) into actionable drug targets and repurposing opportunities.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

---

## Overview

This skill bridges genetic discoveries from GWAS with drug development by:

1. **Identifying genetic risk factors** - Finding genes associated with diseases
2. **Assessing druggability** - Evaluating which genes can be targeted by drugs
3. **Prioritizing targets** - Ranking candidates by genetic evidence strength
4. **Finding existing drugs** - Discovering approved/investigational compounds
5. **Identifying repurposing opportunities** - Matching drugs to new indications

**Key insight**: Targets with genetic support have 2x higher probability of clinical approval (Nelson et al., Nature Genetics 2015).

---

## Workflow Steps

### Step 1: GWAS Gene Discovery

**Input**: Disease/trait name (e.g., "type 2 diabetes", "Alzheimer disease")

**Process**: Query GWAS Catalog for associations, filter by significance (p < 5x10^-8), map variants to genes, aggregate evidence.

**Tools**:
- `gwas_get_associations_for_trait` - Get associations by disease
- `gwas_search_associations` - Flexible search
- `gwas_get_associations_for_snp` - SNP-specific associations
- `OpenTargets_search_gwas_studies_by_disease` - Curated GWAS data
- `OpenTargets_get_variant_credible_sets` - Fine-mapped loci with L2G predictions

### Step 2: Druggability Assessment

**Input**: Gene list from Step 1

**Process**: Check target class, assess tractability, evaluate safety, check for tool compounds or structures.

**Tools**:
- `OpenTargets_get_target_tractability_by_ensemblID` - Druggability assessment
- `OpenTargets_get_target_classes_by_ensemblID` - Target classification
- `OpenTargets_get_target_safety_profile_by_ensemblID` - Safety data
- `OpenTargets_get_target_genomic_location_by_ensemblID` - Genomic context

### Step 3: Target Prioritization

**Scoring Formula**:
```
Target Score = (GWAS Score x 0.4) + (Druggability x 0.3) + (Clinical Evidence x 0.2) + (Novelty x 0.1)
```

Rank targets by composite score. Generate target dossiers.

### Step 4: Existing Drug Search

**Process**: Search drug-target associations, find approved drugs and clinical candidates, get MOA and indication data.

**Tools**:
- `OpenTargets_get_associated_drugs_by_disease_efoId` - Known drugs for disease
- `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` - Drug MOA
- `ChEMBL_get_target_activities` - Bioactivity data
- `ChEMBL_get_drug_mechanisms` / `ChEMBL_search_drugs` - Drug data

### Step 5: Clinical Evidence & Safety

**Tools**:
- `FDA_get_adverse_reactions_by_drug_name` - Safety data
- `FDA_get_active_ingredient_info_by_drug_name` - Drug composition
- `OpenTargets_get_drug_warnings_by_chemblId` - Drug warnings

### Step 6: Repurposing Opportunities

Match drug targets to new disease genes, assess mechanistic fit, check contraindications, estimate repurposing probability.

---

## Quick Start

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Step 1: Get GWAS associations (use disease_trait not trait; no p_value_threshold param)
associations = tu.tools.gwas_get_associations_for_trait(disease_trait="type 2 diabetes")

# Step 2: Assess druggability (ensemblId lowercase d)
tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(ensemblId="ENSG00000148737")

# Step 3: Find existing drugs per target via DGIdb (OpenTargets drug query may return HTTP 400)
drugs = tu.tools.DGIdb_get_drug_gene_interactions(genes=["TCF7L2"])
```

---

## All Tools by Category

**GWAS & Genetics**:
- `gwas_get_associations_for_trait` / `gwas_search_associations` / `gwas_get_associations_for_snp`
- `OpenTargets_search_gwas_studies_by_disease` / `OpenTargets_get_variant_credible_sets`

**Target Assessment**:
- `OpenTargets_get_target_tractability_by_ensemblID` / `OpenTargets_get_target_classes_by_ensemblID`
- `OpenTargets_get_target_safety_profile_by_ensemblID` / `OpenTargets_get_target_genomic_location_by_ensemblID`

**Drug Discovery**:
- `OpenTargets_get_associated_drugs_by_disease_efoId` / `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`
- `ChEMBL_get_target_activities` / `ChEMBL_get_drug_mechanisms` / `ChEMBL_search_drugs`

**Safety & Clinical**:
- `FDA_get_adverse_reactions_by_drug_name` / `FDA_get_active_ingredient_info_by_drug_name`
- `OpenTargets_get_drug_warnings_by_chemblId`

**Literature**:
- `PubMed_search_articles` / `EuropePMC_search_articles` / `ClinicalTrials_search_studies`

---

## Best Practices

1. **Multi-ancestry GWAS**: Include trans-ethnic meta-analyses for robust signals
2. **Functional validation**: Confirm with eQTL, pQTL, colocalization analysis
3. **Network analysis**: Group GWAS hits by pathway (KEGG, Reactome)
4. **Safety assessment**: Check gnomAD pLI, GTEx expression, PharmaGKB
5. **Batch operations**: Use `tu.run_batch()` for parallel queries across targets

---

## Parameter Gotchas

| Issue | Wrong | Correct |
|-------|-------|---------|
| GWAS trait param | `gwas_get_associations_for_trait(trait=...)` | `disease_trait=...` (no `trait` param exists) |
| GWAS p-value filter | `p_value_threshold=5e-8` | No such param; filter client-side after fetching results |
| OpenTargets ensembl case | `ensemblID="ENSG..."` | `ensemblId="ENSG..."` (lowercase 'd') |
| ClinicalTrials tool name | `ClinicalTrials_search(...)` | `ClinicalTrials_search_studies(...)` |
| DGIdb tool name | `DGIdb_get_interactions(...)` | `DGIdb_get_drug_gene_interactions(genes=[...])` |
| OpenTargets disease drugs | `OpenTargets_get_associated_drugs_by_disease_efoId` may return HTTP 400 | Fall back to `DGIdb_get_drug_gene_interactions` per gene |
| GWAS study search param | `gwas_search_studies(disease_trait=...)` | Use `efo_trait=...` for studies (disease_trait works for associations only) |

## Interpretation: From GWAS Hit to Drug Target

### GWAS Signal Strength Assessment

| Signal Quality | Criteria | Drug Discovery Value |
|---------------|---------|---------------------|
| **Gold standard** | Genome-wide significant (p < 5e-8), replicated across ancestries, L2G > 0.5, eQTL colocalized | Highest priority — genetic causality established |
| **Strong** | Genome-wide significant, L2G > 0.3, biological plausibility | High priority — pursue with functional validation |
| **Moderate** | Suggestive (p < 1e-5), or significant but no fine-mapping | Medium — needs additional evidence before investment |
| **Weak** | Single study, no replication, low L2G, no functional support | Low — hypothesis generating only |

### Target Prioritization Decision Tree

After identifying GWAS-linked genes, rank them by answering:

1. **Is the gene druggable?** (DGIdb category: kinase/GPCR/ion channel = yes; transcription factor/scaffold = harder)
   - If approved drug exists → **REPURPOSING** opportunity (fastest path)
   - If druggable but no drug → **NOVEL TARGET** (standard drug discovery)
   - If not druggable → consider antisense/PROTAC/genetic medicine

2. **Is the genetic direction clear?**
   - LOF variants increase disease risk → need an AGONIST or gene therapy
   - GOF variants increase disease risk → need an INHIBITOR (typical small molecule)
   - Direction unclear → need functional studies before drug design

3. **What's the effect size?** (Odds ratio from GWAS)
   - OR > 2.0: strong effect, likely penetrant → Mendelian-like, high confidence
   - OR 1.2-2.0: moderate, common in complex disease → validate with independent data
   - OR < 1.2: small effect → may not be clinically meaningful alone

4. **Is there clinical precedent?**
   - Drug for same target approved for ANY disease → safety data exists → lower risk
   - Drug in clinical trials → partial de-risking
   - No precedent → full de novo development risk

### Evidence Integration Table

For the final report, score each GWAS-to-target candidate:

| Criterion | Score 3 | Score 2 | Score 1 |
|-----------|---------|---------|---------|
| GWAS signal | Replicated, multi-ancestry | Single study, significant | Suggestive only |
| L2G / fine-mapping | L2G > 0.5, credible set < 5 variants | L2G 0.2-0.5 | L2G < 0.2 or no fine-mapping |
| Druggability | Approved drug or probe exists | Tractable (binding site known) | Not classically druggable |
| Direction of effect | Clear LOF/GOF with consistent direction | Ambiguous | Unknown |
| Safety | pLI < 0.5, not expressed in heart/brain | pLI 0.5-0.9 | pLI > 0.9 (essential gene) |

**Max score 15**: 12-15 = priority target; 8-11 = worth investigating; <8 = deprioritize.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No GWAS hits for disease | Try broader trait name, check synonyms, use OpenTargets |
| Gene not in druggable class | Consider antibody/antisense modalities, check pathway neighbors |
| No existing drugs for target | Target may be novel - check tool compounds in ChEMBL |
| Low L2G score | Variants may be regulatory - check eQTL/pQTL evidence |

---

## Reference Files

- **REFERENCE.md** - Detailed concepts, druggability tiers, clinical translation, limitations, ethics
- **EXAMPLES.md** - Use cases (Huntington's, Alzheimer's, diabetes) with success stories
- **REPORT_TEMPLATE.md** - Output report template with scoring criteria
- **PROCEDURES.md** - Step-by-step implementation procedures
- **QUICK_START.md** - Quick start guide
- Related skills: tooluniverse-drug-repurposing, disease-intelligence-gatherer, tooluniverse-sdk
