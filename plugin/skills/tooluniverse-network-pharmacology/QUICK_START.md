# Network Pharmacology - Quick Start Guide

Build compound-target-disease networks for drug repurposing, polypharmacology, and systems pharmacology using 60+ ToolUniverse tools.

## Setup

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()
```

---

## Use Case 1: Drug Repurposing via Network Analysis

**Question**: "Can metformin be repurposed for Alzheimer's disease?"

```python
# Step 1: Resolve entities
drug_info = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="metformin")
chembl_id = drug_info['data']['search']['hits'][0]['id']  # CHEMBL1431

disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="Alzheimer disease"
)
disease_id = disease_info['data']['search']['hits'][0]['id']  # MONDO_0004975

# Step 2: Get drug targets
drug_moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(
    chemblId=chembl_id
)
drug_targets = drug_moa['data']['drug']['mechanismsOfAction']['rows']
drug_target_genes = []
for mech in drug_targets:
    for t in mech.get('targets', []):
        drug_target_genes.append(t['approvedSymbol'])

# Step 3: Get disease genes
disease_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_id, limit=30
)
disease_genes = [
    t['target']['approvedSymbol']
    for t in disease_targets['data']['disease']['associatedTargets']['rows']
]

# Step 4: Build PPI network between drug targets and disease genes
combined_genes = list(set(drug_target_genes[:10] + disease_genes[:10]))
ppi_network = tu.tools.STRING_get_interaction_partners(
    protein_ids=combined_genes, species=9606, limit=50
)

# Step 5: Calculate proximity (shared interactions)
drug_set = set(drug_target_genes)
disease_set = set(disease_genes)
direct_overlap = drug_set & disease_set
print(f"Direct target-disease gene overlap: {direct_overlap}")

# Step 6: Get pathway enrichment
pathways = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers=" ".join(combined_genes)
)

# Step 7: Check clinical evidence
trials = tu.tools.search_clinical_trials(
    query_term="metformin", condition="Alzheimer", pageSize=10
)

# Step 8: Literature co-mentions
papers = tu.tools.PubMed_search_articles(
    query="metformin Alzheimer disease repurposing", max_results=20
)
print(f"Found {len(papers)} supporting publications")
```

---

## Use Case 2: Indication Expansion

**Question**: "What other diseases could sorafenib treat?"

```python
# Step 1: Resolve sorafenib
drug_info = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="sorafenib")
chembl_id = drug_info['data']['search']['hits'][0]['id']

# Step 2: Get ALL targets of sorafenib
drug_targets = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(
    chemblId=chembl_id, size=50
)

# Step 3: Get current indications
current_indications = tu.tools.OpenTargets_get_drug_indications_by_chemblId(
    chemblId=chembl_id, size=50
)

# Step 4: Get ALL diseases linked to drug (investigations + trials)
all_diseases = tu.tools.OpenTargets_get_associated_diseases_by_drug_chemblId(
    chemblId=chembl_id, size=100
)

# Step 5: For each drug target, find additional diseases
new_indications = []
for target in drug_targets['data']['drug']['linkedTargets']['rows'][:15]:
    target_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
        ensemblId=target['id'], size=20
    )
    # Add to new_indications if not in current_indications

# Step 6: Rank by network proximity (shared pathway analysis)
target_symbols = [t.get('approvedSymbol', '') for t in
                  drug_targets['data']['drug']['linkedTargets']['rows'][:15]]
enrichment = tu.tools.enrichr_gene_enrichment_analysis(
    gene_list=[s for s in target_symbols if s],
    libs=["KEGG_2021_Human", "Reactome_2022"]
)

# Step 7: Safety check for each new indication
drug_ae = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId=chembl_id)
```

---

## Use Case 3: Target-Driven Compound Discovery

**Question**: "What compounds modulate EGFR and related pathways?"

```python
# Step 1: Resolve EGFR
target_info = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="EGFR")
ensembl_id = target_info['data']['search']['hits'][0]['id']

# Step 2: Get compounds targeting EGFR
egfr_drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId=ensembl_id, size=50
)

# Step 3: Get PPI partners of EGFR
egfr_ppi = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
    ensemblId=ensembl_id, size=30
)
ppi_genes = [
    row['targetB']['approvedSymbol']
    for row in egfr_ppi['data']['target']['interactions']['rows']
]

# Step 4: Get drugs for PPI partners (expanding to pathway)
for neighbor_gene in ppi_genes[:5]:
    neighbor_drugs = tu.tools.DGIdb_get_drug_gene_interactions(genes=[neighbor_gene])

# Step 5: Get pathway context
egfr_pathways = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers=f"EGFR {' '.join(ppi_genes[:10])}"
)

# Step 6: Druggability assessment
druggability = tu.tools.DGIdb_get_gene_druggability(genes=["EGFR"])
tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
    ensemblId=ensembl_id
)
```

---

## Use Case 4: Disease-Driven Drug Discovery

**Question**: "Find FDA-approved drugs that could treat lupus"

```python
# Step 1: Resolve lupus
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="systemic lupus erythematosus"
)
disease_id = disease_info['data']['search']['hits'][0]['id']

# Step 2: Get disease targets
disease_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_id, limit=30
)

# Step 3: Get drugs already investigated for lupus
lupus_drugs = tu.tools.OpenTargets_get_associated_drugs_by_disease_efoId(
    efoId=disease_id, size=50
)

# Step 4: Find NEW drugs for disease targets via DGIdb
disease_gene_symbols = [
    t['target']['approvedSymbol']
    for t in disease_targets['data']['disease']['associatedTargets']['rows'][:15]
]

new_drug_candidates = tu.tools.DGIdb_get_drug_gene_interactions(
    genes=disease_gene_symbols[:10]
)

# Step 5: Build disease PPI network
string_ppi = tu.tools.STRING_get_interaction_partners(
    protein_ids=disease_gene_symbols[:15], species=9606, limit=30
)

# Step 6: Check CTD for chemical-disease links
ctd_chemicals = tu.tools.CTD_get_disease_chemicals(
    input_terms="Lupus Erythematosus, Systemic"
)

# Step 7: Filter to FDA-approved only
for drug_candidate in new_drug_candidates['data']['genes']['nodes']:
    for interaction in drug_candidate.get('interactions', []):
        drug_name = interaction['drug']['name']
        # Check FDA approval status
        fda_info = tu.tools.ChEMBL_search_drugs(query=drug_name, limit=1)
```

---

## Use Case 5: Polypharmacology Analysis

**Question**: "What are the multi-target effects of aspirin?"

```python
# Step 1: Resolve aspirin
drug_info = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="aspirin")
chembl_id = drug_info['data']['search']['hits'][0]['id']

# Step 2: Get ALL targets from multiple sources
# OpenTargets mechanisms
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)

# OpenTargets linked targets
all_targets = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(
    chemblId=chembl_id, size=100
)

# DrugBank targets
db_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    query="aspirin", case_sensitive=False, exact_match=True, limit=1
)

# CTD chemical-gene interactions
ctd_genes = tu.tools.CTD_get_chemical_gene_interactions(input_terms="Aspirin")

# Step 3: Classify targets (primary vs off-target)
primary_targets = [row for row in moa['data']['drug']['mechanismsOfAction']['rows']]
all_target_genes = [t.get('approvedSymbol', '') for t in
                    all_targets['data']['drug']['linkedTargets']['rows']]

# Step 4: Map targets to diseases
for gene in all_target_genes[:10]:
    target_info = tu.tools.OpenTargets_get_target_id_description_by_name(targetName=gene)
    if target_info['data']['search']['hits']:
        eid = target_info['data']['search']['hits'][0]['id']
        diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
            ensemblId=eid, size=10
        )

# Step 5: Pathway coverage analysis
enrichment = tu.tools.enrichr_gene_enrichment_analysis(
    gene_list=[g for g in all_target_genes[:20] if g],
    libs=["KEGG_2021_Human", "GO_Biological_Process_2023"]
)

# Step 6: Safety from polypharmacology
aspirin_ae = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId=chembl_id)
```

---

## Use Case 6: Mechanism Elucidation

**Question**: "How might rapamycin affect longevity?"

```python
# Step 1: Resolve rapamycin (sirolimus)
drug_info = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="sirolimus")
chembl_id = drug_info['data']['search']['hits'][0]['id']

# Step 2: Get mechanism of action
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)

# Step 3: Get all drug targets
drug_targets = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(
    chemblId=chembl_id, size=50
)
target_genes = [t.get('approvedSymbol', '') for t in
                drug_targets['data']['drug']['linkedTargets']['rows']]

# Step 4: Build mTOR pathway network
mtor_ppi = tu.tools.STRING_get_interaction_partners(
    protein_ids=["MTOR", "RPTOR", "RICTOR", "TSC1", "TSC2"],
    species=9606, limit=30
)

# Step 5: Pathway analysis for mTOR signaling
mtor_pathways = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers="MTOR RPTOR RICTOR TSC1 TSC2 RPS6KB1 EIF4EBP1 AKT1 ULK1"
)

# Step 6: Link to aging-related processes
# Get GO biological process enrichment
aging_enrichment = tu.tools.enrichr_gene_enrichment_analysis(
    gene_list=["MTOR", "RPTOR", "RPS6KB1", "EIF4EBP1", "ULK1", "BECN1", "ATG13"],
    libs=["GO_Biological_Process_2023"]
)

# Step 7: Literature evidence for rapamycin + aging
papers = tu.tools.PubMed_search_articles(
    query="rapamycin sirolimus aging longevity mTOR",
    max_results=30
)

# Step 8: Clinical trials
trials = tu.tools.search_clinical_trials(
    query_term="sirolimus", condition="aging", pageSize=10
)

# Step 9: Drug indications (approved + investigational)
indications = tu.tools.OpenTargets_get_drug_indications_by_chemblId(
    chemblId=chembl_id, size=50
)

# Step 10: Pharmacology
pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    query="sirolimus", case_sensitive=False, exact_match=True, limit=1
)
```

---

## Output Format

The skill generates a comprehensive markdown report with:

1. **Executive Summary** - Key findings in 2-3 sentences
2. **Network Pharmacology Score** (0-100) with component breakdown
3. **Network Topology** - Nodes, edges, hubs, modules
4. **Top 10 Repurposing Candidates** - Ranked with scores
5. **Mechanism Predictions** - Network paths explaining drug-disease connection
6. **Polypharmacology Profile** - Multi-target analysis
7. **Safety Considerations** - AE data, target safety
8. **Clinical Precedent** - Trials, approvals, literature
9. **Evidence Summary** - All findings with T1-T4 grading
10. **Completeness Checklist** - Analysis coverage tracking

---

## Key Tool Count by Phase

| Phase | Tools | Primary Sources |
|-------|-------|----------------|
| Entity Disambiguation | 8 | OpenTargets, DrugBank, PubChem, Ensembl |
| Network Node ID | 12 | OpenTargets, DrugBank, DGIdb, CTD, Pharos |
| Network Edges | 10 | STRING, OpenTargets, IntAct, HumanBase |
| Drug-Target Edges | 8 | ChEMBL, DrugBank, DGIdb, CTD, STITCH |
| Target-Disease Edges | 6 | OpenTargets, GWAS, CTD, PharmGKB |
| Drug-Disease Edges | 5 | OpenTargets, CTD, ClinicalTrials, PubMed |
| Pathway Analysis | 4 | Reactome, Enrichr, STRING, DrugBank |
| Safety | 10 | FAERS, FDA, OpenTargets, gnomAD, HPA |
| Clinical Evidence | 6 | ClinicalTrials, PubMed, EuropePMC, OpenTargets |
| **Total unique** | **60+** | **15+ databases** |
