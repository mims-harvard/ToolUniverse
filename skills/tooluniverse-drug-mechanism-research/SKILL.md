---
name: tooluniverse-drug-mechanism-research
description: >
  Drug mechanism of action research -- target identification (primary + off-targets) via ChEMBL and OpenTargets,
  pathway context via KEGG/Reactome/WikiPathways/STRING, pharmacogenomic interactions via CPIC/PharmGKB,
  clinical pharmacology from DailyMed drug labels, drug-drug interactions, and literature evidence from
  PubMed/EuropePMC. Use when users ask about how a drug works, its molecular targets, pathway involvement,
  pharmacogenomics, drug interactions, clinical pharmacology, or mechanism-based adverse effects.
triggers:
  - keywords: [mechanism of action, drug target, pharmacology, pathway, pharmacogenomics, drug interaction, DailyMed, CPIC, MOA, off-target]
  - patterns: ["how does .* work", "mechanism of action", "drug target", "pathway context", "clinical pharmacology", "drug-drug interaction", "pharmacogenomic", "off-target effect"]
---

# Drug Mechanism of Action Research

Systematic investigation of drug mechanisms: identify molecular targets and action types via ChEMBL and OpenTargets,
contextualize targets in biological pathways via KEGG/Reactome/WikiPathways, assess pharmacogenomic interactions
via CPIC/PharmGKB, extract clinical pharmacology from FDA-approved labels via DailyMed, evaluate drug-drug
interactions, and gather literature evidence from PubMed/EuropePMC.

## When to Use

- "What is the mechanism of action of metformin?"
- "What are the molecular targets of imatinib?"
- "Which pathways are affected by pembrolizumab?"
- "What pharmacogenomic interactions exist for clopidogrel?"
- "Show me drug-drug interactions for warfarin from the FDA label"
- "What are the off-targets of aspirin?"
- "Explain the clinical pharmacology of metformin"
- "Which enzymes metabolize tamoxifen?"
- "What is the pathway context for EGFR inhibitors?"
- "Compare mechanisms of metformin vs pioglitazone"

## NOT for (use other skills instead)

- Drug safety/adverse events profiling -> Use `tooluniverse-adverse-event-detection`
- Clinical trial matching -> Use `tooluniverse-clinical-trial-matching`
- Drug repurposing/new indications -> Use `tooluniverse-drug-repurposing`
- Target druggability assessment -> Use `tooluniverse-drug-target-validation`
- Chemical structure/ADMET properties -> Use `tooluniverse-chemical-safety`
- Network pharmacology/polypharmacology -> Use `tooluniverse-network-pharmacology`
- CPIC dosing guidelines specifically -> Use `tooluniverse-pharmacogenomics`

---

## Workflow Overview

```
Input (drug name / ChEMBL ID / target gene)
  |
  v
Phase 0: Drug Disambiguation (resolve name to ChEMBL ID, get synonyms)
  |
  v
Phase 1: Mechanism of Action (primary targets, action types, binding data)
  |
  v
Phase 2: Target Characterization (target details, protein function, expression)
  |
  v
Phase 3: Pathway Context (KEGG, Reactome, WikiPathways, STRING enrichment)
  |
  v
Phase 4: Pharmacogenomics (CPIC gene-drug pairs, PharmGKB annotations, FDA PGx biomarkers)
  |
  v
Phase 5: Clinical Pharmacology (DailyMed label data, PK/PD, metabolism)
  |
  v
Phase 6: Drug Interactions (DailyMed DDIs, contraindications)
  |
  v
Phase 6.5: Safety Profile (FAERS adverse events, FDA warnings, black box)
  |
  v
Phase 7: Clinical Trials (search_clinical_trials for outcomes data)
  |
  v
Phase 7.5: Literature Evidence (PubMed/EuropePMC mechanism studies)
  |
  v
Phase 8: Integration & Report (combine all evidence, confidence grading)
```

---

## Phase 0: Drug Disambiguation

Resolve drug name to canonical identifiers (ChEMBL ID, PharmGKB ID).

**OpenTargets_get_drug_id_description_by_name**: `drugName` (string, REQUIRED, e.g., "metformin").
Returns `{data: {search: {hits: [{id, name, entity, description}]}}}`.

```python
# Resolve drug name to ChEMBL ID
result = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName="metformin")
# Get chemblId from hits
```

**OpenTargets_get_drug_chembId_by_generic_name**: `drugName` (string, REQUIRED). Returns ChEMBL ID.

**PharmGKB_search_drugs**: `query` (string, REQUIRED, e.g., "metformin").
Returns `{status: "success", data: [{id, name, inChi, smiles, types}]}`.

```python
# Get PharmGKB drug ID
result = tu.tools.PharmGKB_search_drugs(query="metformin")
# result["data"][0]["id"] -> "PA450395"
```

**ChEMBL_get_drug**: Get drug details by ChEMBL ID. Returns structure, properties, clinical phase.

### Key Drug ChEMBL IDs (verified)

| Drug | ChEMBL ID |
|------|-----------|
| Metformin | CHEMBL1431 |
| Imatinib | CHEMBL941 |
| Aspirin | CHEMBL25 |
| Pembrolizumab | CHEMBL3137343 |
| Nivolumab | CHEMBL2108738 |
| Clopidogrel | CHEMBL1771 |
| Warfarin | CHEMBL1464 |
| Tamoxifen | CHEMBL83 |

---

## Phase 1: Mechanism of Action

### OpenTargets drug mechanisms

**OpenTargets_get_drug_mechanisms_of_action_by_chemblId**: `chemblId` (string, REQUIRED, e.g., "CHEMBL1431").
Returns `{status: "success", data: {drug: {id, name, mechanismsOfAction: {rows: [{mechanismOfAction, actionType, targetName, targets: [{id, approvedSymbol}]}]}}}}`.

```python
# Get MOA for metformin
result = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL1431")
moa = result["data"]["drug"]["mechanismsOfAction"]["rows"]
for m in moa:
    print(f"{m['mechanismOfAction']} ({m['actionType']}) -> {m['targetName']}")
    for t in m.get("targets", []):
        print(f"  Target: {t['approvedSymbol']} ({t['id']})")
```

### ChEMBL drug mechanisms (detailed)

**ChEMBL_get_drug_mechanisms**: `drug_chembl_id__exact` (string, REQUIRED, e.g., "CHEMBL1431").
Returns `{status: "success", data: {mechanisms: [{action_type, mechanism_of_action, mechanism_comment, mechanism_refs: [{ref_id, ref_type, ref_url}], target_chembl_id, direct_interaction, disease_efficacy, max_phase, molecular_mechanism}]}}`.

```python
# Get detailed mechanisms with literature references
result = tu.tools.ChEMBL_get_drug_mechanisms(drug_chembl_id__exact="CHEMBL1431")
for mech in result["data"]["mechanisms"]:
    print(f"MOA: {mech['mechanism_of_action']}")
    print(f"  Action: {mech['action_type']}, Direct: {mech['direct_interaction']}")
    print(f"  References: {[r['ref_id'] for r in mech.get('mechanism_refs', [])]}")
```

### OpenTargets drug-target associations

**OpenTargets_get_associated_targets_by_drug_chemblId**: `chemblId` (string, REQUIRED).
- KNOWN ISSUE: This tool may fail with GraphQL error (`linkedTargets` field removed from OpenTargets API schema).
- WORKAROUND: Extract targets from `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` results instead -- each mechanism row has a `targets` array with `{id, approvedSymbol}`.
- Alternative: Use `ChEMBL_get_drug_mechanisms` to get `target_chembl_id` for each mechanism, then `ChEMBL_get_target` for details.

### ChEMBL target activities (binding data)

**ChEMBL_get_target_activities**: `target_chembl_id__exact` (string, REQUIRED, double underscore).
Returns bioactivity data (IC50, Ki, EC50) for a target. Use after identifying target ChEMBL ID from mechanisms.

---

## Phase 2: Target Characterization

### ChEMBL target details

**ChEMBL_get_target**: Get target details by ChEMBL target ID. Returns organism, target type, components.

### STRING functional annotations

**STRING_get_functional_annotations**: `identifiers` (string, gene name), `species` (int, 9606).
Returns GO terms (Process, Function, Component), KEGG pathways, Reactome, InterPro, HPO.

```python
# Get functional context for a drug target
result = tu.tools.STRING_get_functional_annotations(identifiers="AMPK", species=9606)
```

### Gene details via PharmGKB

**PharmGKB_search_genes**: `query` (string, gene symbol). Returns gene IDs and cross-references.

**PharmGKB_get_gene_details**: `gene_id` (string, PharmGKB gene ID, e.g., "PA24356"). Returns detailed gene info.

---

## Phase 3: Pathway Context

### KEGG pathways for a gene

**KEGG_get_gene_pathways**: `gene_id` (string, REQUIRED, format "hsa:<entrez_id>", e.g., "hsa:367").
Returns `{status: "success", data: {gene_id, pathway_count, pathways: [{pathway_id, pathway_name}]}}`.

**kegg_find_genes**: `keyword` (string), `organism` (string, e.g., "hsa").
Returns genes matching keyword. Use to find KEGG gene IDs from gene symbols.

```python
# Find KEGG gene ID for BRCA1
genes = tu.tools.kegg_find_genes(keyword="BRCA1", organism="hsa")
# Then get pathways
pathways = tu.tools.KEGG_get_gene_pathways(gene_id="hsa:672")
```

**kegg_search_pathway**: `query` (string). Search KEGG pathways by keyword.

**kegg_get_pathway_info**: Get detailed pathway info by KEGG pathway ID.

**KEGG_get_pathway_genes**: `pathway_id` (string). Get all genes in a pathway.

### KEGG drug-specific tools (new)

**KEGG_search_drug**: `keyword` (string). Search KEGG drug database by name or keyword.
Returns drug entries with KEGG drug IDs (e.g., "D00123").

**KEGG_get_drug**: `drug_id` (string, e.g., "D00123"). Get detailed drug info including targets, pathways, metabolism.

**KEGG_get_drug_targets**: `drug_id` (string). Get molecular targets for a KEGG drug with target gene IDs.

```python
# Find KEGG drug entry for metformin
drugs = tu.tools.KEGG_search_drug(keyword="metformin")
# Get drug targets
targets = tu.tools.KEGG_get_drug_targets(drug_id="D04966")
```

### Reactome pathways

**Reactome_map_uniprot_to_pathways**: `uniprot_id` (string, REQUIRED). Maps a protein to all Reactome pathways.
Returns `{status: "success", data: [{dbId, displayName, stId, speciesName, hasDiagram, ...}]}`.

```python
# Map target protein to Reactome pathways
result = tu.tools.Reactome_map_uniprot_to_pathways(uniprot_id="P11309")
for p in result["data"][:10]:
    print(f"{p['stId']}: {p['displayName']}")
```

**Reactome_get_pathway**: Get pathway details by stable ID (e.g., "R-HSA-6785807").

**ReactomeContent_search**: Free-text search of Reactome content.

**ReactomeAnalysis_pathway_enrichment**: `identifiers` (string, SPACE-separated gene/protein list, NOT array).
Returns pathway enrichment analysis results.

```python
# Pathway enrichment for a set of drug targets
result = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers="NDUFA10 NDUFS8 MT-ND1 MT-ND6")
```

### WikiPathways

**WikiPathways_find_pathways_by_gene**: `gene` (string, gene symbol).
Returns `{status: "success", data: {gene, total_pathways, pathways: [{id, name, species, url}]}}`.

```python
# Find pathways involving BRCA1
result = tu.tools.WikiPathways_find_pathways_by_gene(gene="BRCA1")
```

**WikiPathways_search**: Free-text search of WikiPathways.

**WikiPathways_get_pathway_genes**: Get all genes in a WikiPathway.

### STRING network enrichment

**STRING_functional_enrichment**: `identifiers` (string), `species` (int, 9606).
Returns enriched GO terms, KEGG pathways for a set of proteins.

**STRING_get_interaction_partners**: `identifiers` (string), `species` (int, 9606).
Returns protein-protein interaction network.

---

## Phase 4: Pharmacogenomics

### CPIC gene-drug pairs

**CPIC_search_gene_drug_pairs**: `gene_symbol` (string), `cpiclevel` (string, "A"/"B"/"C"/"D"), `limit` (int).
Returns `{status: "success", data: [{genesymbol, drugid, cpiclevel, guidelineid, usedforrecommendation, clinpgxlevel, pgxtesting}]}`.
- Auto-normalizes gene symbols (no `eq.` prefix needed).

**CPIC_get_gene_drug_pairs**: `genesymbol` (string, REQUIRED). Returns ALL pairs for a gene including drug names.

**CPIC_get_drug_info**: `name` (string, REQUIRED, lowercase). Returns drug identifiers and guideline links.

**CPIC_list_pgx_genes**: No params. Returns all PGx genes curated by CPIC.

### PharmGKB annotations

**PharmGKB_get_clinical_annotations**: `annotation_id` (string, REQUIRED, e.g., "1447954390").
Returns detailed clinical annotation for a specific PGx variant-drug pair.
- NOTE: Requires specific annotation ID. Use CPIC tools to find relevant gene-drug pairs first.

**PharmGKB_get_dosing_guidelines**: `query` (string). Returns dosing guideline data.

### FDA pharmacogenomic biomarkers

**fda_pharmacogenomic_biomarkers**: `drug_name` (string, optional), `biomarker` (string, optional), `limit` (int, default 10 -- use 1000 for all).
Returns `{count, shown, results: [{drug_name, biomarker, affected_subgroup, description_of_pgx_in_labeling}]}`.

```python
# Find FDA PGx biomarkers for a drug
result = tu.tools.fda_pharmacogenomic_biomarkers(drug_name="clopidogrel", limit=100)
# Or find all drugs for a biomarker gene
result = tu.tools.fda_pharmacogenomic_biomarkers(biomarker="CYP2D6", limit=100)
```

---

## Phase 5: Clinical Pharmacology

### DailyMed label sections (two-step process)

DailyMed parse tools require a `setid` (not `drug_name`). First search, then parse:

```python
# Step 1: Get setid via search
spls = tu.tools.DailyMed_search_spls(drug_name="metformin")
setid = spls["data"][0]["setid"]

# Step 2: Parse specific sections using setid
pharmacology = tu.tools.DailyMed_parse_clinical_pharmacology(
    operation="parse_clinical_pharmacology", setid=setid)
adverse = tu.tools.DailyMed_parse_adverse_reactions(
    operation="parse_adverse_reactions", setid=setid)
interactions = tu.tools.DailyMed_parse_drug_interactions(
    operation="parse_drug_interactions", setid=setid)
```

**Available parse tools** (all require `operation` + `setid`):
- `DailyMed_parse_clinical_pharmacology` — MOA, PK/PD, metabolism
- `DailyMed_parse_adverse_reactions` — adverse reaction tables
- `DailyMed_parse_drug_interactions` — DDI information
- `DailyMed_parse_contraindications` — contraindications
- `DailyMed_parse_dosing` — dosing and administration

**DailyMed_search_drug_classes**: Search by pharmacologic class.

### OpenTargets drug details

**OpenTargets_get_drug_description_by_chemblId**: `chemblId`. Returns drug description.

**OpenTargets_get_drug_indications_by_chemblId**: `chemblId`. Returns approved/investigational indications.

**OpenTargets_get_drug_approval_status_by_chemblId**: `chemblId`. Returns approval phase and status.

---

## Phase 6: Drug Interactions

### DailyMed drug interactions

**DailyMed_parse_drug_interactions**: `drug_name` (string, REQUIRED).
Returns `{status: "success", data: {interactions: [{type, data}]}}`.
- Extracts the "Drug Interactions" section from FDA labels.
- Structured as table rows with Clinical Impact, Intervention, Examples.

```python
# Get drug interactions for metformin
result = tu.tools.DailyMed_parse_drug_interactions(drug_name="metformin")
for interaction in result["data"]["interactions"]:
    if interaction["type"] == "table_row":
        print(" | ".join(interaction["data"]))
```

### DailyMed contraindications

**DailyMed_parse_contraindications**: `drug_name` (string, REQUIRED).
Returns `{status: "success", data: {contraindications: [{type, description}]}}`.

### OpenTargets drug warnings

**OpenTargets_get_drug_warnings_by_chemblId**: `chemblId`. Returns safety warnings and withdrawn drug info.

**OpenTargets_get_drug_adverse_events_by_chemblId**: `chemblId`. Returns FAERS-derived adverse events with logLR scores.

---

## Phase 7: Literature Evidence

### PubMed

**PubMed_search_articles**: `query` (string, REQUIRED), `limit` (int, default 10).
Returns list of article dicts (NOT wrapped in `{articles: [...]}`).

```python
# Search for mechanism studies
result = tu.tools.PubMed_search_articles(query="metformin mechanism of action AMPK", limit=10)
# result is a plain list of dicts
for article in result[:5]:
    print(f"{article.get('title', 'No title')} - {article.get('pmid', '')}")
```

### EuropePMC

**EuropePMC_search_articles**: `query` (string, REQUIRED), `limit` or `page_size` (int).
Returns `{status: "success", data: [...], metadata: {...}}`.

```python
# Search EuropePMC for mechanism studies
result = tu.tools.EuropePMC_search_articles(query="metformin mechanism action mitochondrial", limit=10)
```

**EuropePMC_get_citations**: Get articles that cite a given paper.

**EuropePMC_get_references**: Get references from a paper.

---

## Phase 8: Integration & Report

### Evidence Grading

- **T1 (Regulatory/Clinical)**: FDA label (DailyMed), CPIC Level A, FDA PGx biomarker, Phase 4 approval
- **T2 (Experimental)**: ChEMBL mechanisms with literature refs, ChIP-seq/binding data, clinical trial data
- **T3 (Computational/Database)**: OpenTargets MOA, STRING/KEGG/Reactome pathways, PharmGKB annotations
- **T4 (Literature/Annotation)**: PubMed articles, EuropePMC, WikiPathways

### Report Template

```
## Drug Mechanism of Action Report: [Drug Name]

### Drug Identity
- Name: [generic name]
- ChEMBL ID: [CHEMBL####]
- PharmGKB ID: [PA######]
- Approval status: [phase/status]
- Indications: [list]

### 1. Primary Mechanism of Action
- Action type: [INHIBITOR/AGONIST/ANTAGONIST/etc.]
- Target: [target name] ([gene symbol], [Ensembl ID])
- Mechanism: [description from ChEMBL/OpenTargets]
- Direct interaction: [yes/no]
- Clinical pharmacology: [from DailyMed]

### 2. Additional Targets / Off-Targets
- [Target 2]: [action type, evidence]
- [Target 3]: [action type, evidence]

### 3. Pathway Context
- KEGG: [pathways]
- Reactome: [pathways]
- WikiPathways: [pathways]
- Functional annotations: [GO terms, protein interactions]

### 4. Pharmacogenomics
- CPIC gene-drug pairs: [gene, level, recommendation]
- FDA PGx biomarkers: [gene, labeling description]
- PharmGKB annotations: [variant-drug pairs]

### 5. Drug Interactions
- Key interactions: [from DailyMed]
- Contraindications: [from DailyMed]
- Mechanism-based interactions: [enzyme inhibition/induction]

### 6. Literature Evidence
- Key references: [PMIDs with titles]

### Evidence Summary
| Evidence Layer | Source | Confidence |
|---|---|---|
| Primary MOA | ChEMBL + DailyMed | T1 |
| Off-targets | OpenTargets | T3 |
| Pathways | KEGG/Reactome | T3 |
| PGx | CPIC/PharmGKB | T1/T3 |
| DDI | DailyMed label | T1 |
| Literature | PubMed | T2/T4 |
```

---

## Common Use Patterns

### Pattern 1: Complete mechanism profile for a drug

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

drug_name = "metformin"
chembl_id = "CHEMBL1431"

# Phase 0: Disambiguation
drug_info = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName=drug_name)
pgkb = tu.tools.PharmGKB_search_drugs(query=drug_name)

# Phase 1: MOA
ot_moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
chembl_moa = tu.tools.ChEMBL_get_drug_mechanisms(drug_chembl_id__exact=chembl_id)
all_targets = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(chemblId=chembl_id)

# Phase 5: Clinical pharmacology
clin_pharm = tu.tools.DailyMed_parse_clinical_pharmacology(drug_name=drug_name)

# Phase 6: Drug interactions
ddi = tu.tools.DailyMed_parse_drug_interactions(drug_name=drug_name)
contra = tu.tools.DailyMed_parse_contraindications(drug_name=drug_name)
```

### Pattern 2: Pathway context for drug targets

```python
# Get targets from MOA
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId="CHEMBL1431")
target_genes = []
for row in moa["data"]["drug"]["mechanismsOfAction"]["rows"]:
    for t in row.get("targets", []):
        target_genes.append(t["approvedSymbol"])

# Get pathways for each target
for gene in target_genes[:5]:  # limit to top 5
    wp = tu.tools.WikiPathways_find_pathways_by_gene(gene=gene)
    print(f"{gene}: {wp['data']['total_pathways']} WikiPathways")

    # STRING functional annotations
    annot = tu.tools.STRING_get_functional_annotations(identifiers=gene, species=9606)
```

### Pattern 3: PGx profile for a drug

```python
drug_name = "clopidogrel"

# CPIC gene-drug pairs
cpic_drug = tu.tools.CPIC_get_drug_info(name=drug_name.lower())

# Find all CPIC pairs for the drug's PGx genes
cyp2c19_pairs = tu.tools.CPIC_search_gene_drug_pairs(gene_symbol="CYP2C19", cpiclevel="A", limit=20)

# FDA PGx biomarkers
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(drug_name=drug_name, limit=100)

# PharmGKB gene details
pgkb_gene = tu.tools.PharmGKB_search_genes(query="CYP2C19")
```

### Pattern 4: Drug-drug interaction analysis

```python
drug_name = "warfarin"

# DailyMed DDIs
ddi = tu.tools.DailyMed_parse_drug_interactions(drug_name=drug_name)

# Contraindications
contra = tu.tools.DailyMed_parse_contraindications(drug_name=drug_name)

# OpenTargets warnings
warnings = tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId="CHEMBL1464")

# Literature on specific interactions
lit = tu.tools.PubMed_search_articles(query=f"{drug_name} drug interaction CYP2C9", limit=10)
```

### Pattern 5: Compare mechanisms of two drugs

```python
drugs = [
    {"name": "metformin", "chembl": "CHEMBL1431"},
    {"name": "pioglitazone", "chembl": "CHEMBL595"},
]

for drug in drugs:
    print(f"\n=== {drug['name']} ===")
    moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=drug["chembl"])
    for row in moa["data"]["drug"]["mechanismsOfAction"]["rows"]:
        print(f"  {row['mechanismOfAction']} ({row['actionType']})")

    clin = tu.tools.DailyMed_parse_clinical_pharmacology(drug_name=drug["name"])
    for section in clin["data"]["pharmacology"][:2]:
        if section["type"] == "pharmacology_text":
            print(f"  PK: {section['content'][:200]}...")
```

---

## Tool Parameter Quick Reference

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| OpenTargets_get_drug_id_description_by_name | drugName | Drug name to ChEMBL ID |
| OpenTargets_get_drug_chembId_by_generic_name | drugName | Same as above |
| OpenTargets_get_drug_mechanisms_of_action_by_chemblId | chemblId | Primary MOA with targets |
| OpenTargets_get_associated_targets_by_drug_chemblId | chemblId | ALL linked targets |
| OpenTargets_get_drug_description_by_chemblId | chemblId | Drug description |
| OpenTargets_get_drug_indications_by_chemblId | chemblId | Approved indications |
| OpenTargets_get_drug_warnings_by_chemblId | chemblId | Safety warnings |
| OpenTargets_get_drug_adverse_events_by_chemblId | chemblId | FAERS adverse events |
| ChEMBL_get_drug_mechanisms | drug_chembl_id__exact | Detailed MOA with refs |
| ChEMBL_get_drug | (chembl_id) | Drug structure/properties |
| ChEMBL_get_target | (target_chembl_id) | Target details |
| ChEMBL_get_target_activities | target_chembl_id__exact | Bioactivity data (IC50, Ki) |
| DailyMed_parse_clinical_pharmacology | drug_name | FDA label pharmacology |
| DailyMed_parse_drug_interactions | drug_name | FDA label DDIs |
| DailyMed_parse_contraindications | drug_name | FDA label contraindications |
| DailyMed_parse_dosing | drug_name | FDA label dosing |
| DailyMed_parse_adverse_reactions | drug_name | FDA label ADRs |
| DailyMed_search_spls | (search params) | Search SPL documents |
| CPIC_search_gene_drug_pairs | gene_symbol, cpiclevel, limit | CPIC pairs by gene |
| CPIC_get_drug_info | name (lowercase) | Drug CPIC info |
| CPIC_get_gene_drug_pairs | genesymbol | All pairs for gene |
| CPIC_list_pgx_genes | (none) | All CPIC PGx genes |
| PharmGKB_search_drugs | query | PharmGKB drug search |
| PharmGKB_search_genes | query | PharmGKB gene search |
| PharmGKB_get_drug_details | drug_id (PA######) | Detailed drug info |
| PharmGKB_get_clinical_annotations | annotation_id | PGx annotations (needs ID) |
| fda_pharmacogenomic_biomarkers | drug_name, biomarker, limit | FDA PGx label info |
| KEGG_get_gene_pathways | gene_id (hsa:####) | Gene to KEGG pathways |
| kegg_find_genes | keyword, organism | Find KEGG gene IDs |
| kegg_search_pathway | query | Search KEGG pathways |
| KEGG_search_drug | keyword | Search KEGG drug DB |
| KEGG_get_drug | drug_id (D#####) | KEGG drug details |
| KEGG_get_drug_targets | drug_id (D#####) | Drug molecular targets |
| KEGG_get_pathway_genes | pathway_id | Genes in a pathway |
| Reactome_map_uniprot_to_pathways | uniprot_id | Protein to Reactome pathways |
| ReactomeAnalysis_pathway_enrichment | identifiers (space-separated) | Pathway enrichment |
| ReactomeContent_search | (query) | Free-text Reactome search |
| WikiPathways_find_pathways_by_gene | gene | Gene to WikiPathways |
| WikiPathways_search | (query) | Free-text WikiPathways search |
| STRING_get_functional_annotations | identifiers, species | GO/KEGG/Reactome annotations |
| STRING_functional_enrichment | identifiers, species | Enrichment analysis |
| STRING_get_interaction_partners | identifiers, species | PPI network |
| PubMed_search_articles | query, limit | Returns plain list (NOT wrapped) |
| EuropePMC_search_articles | query, limit/page_size | Returns {status, data, metadata} |

---

## Action Type Reference (ChEMBL/OpenTargets)

| Action Type | Meaning |
|-------------|---------|
| INHIBITOR | Blocks target activity |
| AGONIST | Activates target |
| ANTAGONIST | Blocks receptor activation |
| PARTIAL AGONIST | Partial receptor activation |
| MODULATOR | Modifies target activity (non-specific) |
| OPENER | Opens ion channel |
| BLOCKER | Blocks ion channel |
| POSITIVE ALLOSTERIC MODULATOR | Enhances activity via allosteric site |
| NEGATIVE ALLOSTERIC MODULATOR | Reduces activity via allosteric site |
| SUBSTRATE | Metabolized by target enzyme |

---

## MetaCyc Alternatives

MetaCyc requires a paid account and is not available through ToolUniverse. Use these alternatives:
- **KEGG**: `KEGG_get_gene_pathways`, `kegg_search_pathway`, `KEGG_get_pathway_genes`
- **Reactome**: `Reactome_map_uniprot_to_pathways`, `ReactomeContent_search`
- **WikiPathways**: `WikiPathways_find_pathways_by_gene`, `WikiPathways_search`

---

## Fallback Strategies

| Phase | Primary Tool | Fallback |
|-------|-------------|----------|
| Drug ID | OpenTargets_get_drug_id_description_by_name | PharmGKB_search_drugs |
| MOA | OpenTargets_get_drug_mechanisms_of_action_by_chemblId | ChEMBL_get_drug_mechanisms |
| Targets | OpenTargets_get_associated_targets_by_drug_chemblId | ChEMBL_get_target_activities |
| Pathways (KEGG) | KEGG_get_gene_pathways | kegg_search_pathway |
| Pathways (Reactome) | Reactome_map_uniprot_to_pathways | ReactomeContent_search |
| Pathways (WikiPathways) | WikiPathways_find_pathways_by_gene | WikiPathways_search |
| PGx (CPIC) | CPIC_search_gene_drug_pairs | CPIC_get_gene_drug_pairs |
| PGx (FDA) | fda_pharmacogenomic_biomarkers | DailyMed_parse_clinical_pharmacology |
| Clinical pharmacology | DailyMed_parse_clinical_pharmacology | OpenTargets_get_drug_description_by_chemblId |
| DDI | DailyMed_parse_drug_interactions | PubMed_search_articles (DDI query) |
| Literature | PubMed_search_articles | EuropePMC_search_articles |

---

## Completeness Checklist

Before delivering a report, verify:
- [ ] Drug name resolved to ChEMBL ID and PharmGKB ID
- [ ] Primary mechanism of action identified with action type
- [ ] All known targets listed (primary + off-targets)
- [ ] At least one pathway database queried (KEGG/Reactome/WikiPathways)
- [ ] PGx interactions checked (CPIC + FDA biomarkers)
- [ ] Clinical pharmacology extracted from DailyMed (if approved drug)
- [ ] Drug interactions documented (DailyMed DDI section)
- [ ] Literature evidence gathered (PubMed/EuropePMC)
- [ ] Evidence graded by tier (T1-T4)
- [ ] Report includes both mechanism description and target gene symbols/IDs
