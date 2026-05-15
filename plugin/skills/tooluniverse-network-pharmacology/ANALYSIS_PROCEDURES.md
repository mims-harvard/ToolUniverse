# Network Pharmacology - Detailed Analysis Procedures

Detailed code examples for each phase of the network pharmacology pipeline.

---

## Phase 0: Entity Disambiguation and Report Setup

**Step 0.1**: Create the report file immediately.

```python
report_path = "[entity]_network_pharmacology_report.md"
# Write header and placeholder sections
```

**Step 0.2**: Resolve the input entity to all required identifiers.

```python
from tooluniverse import ToolUniverse
tu = ToolUniverse(use_cache=True)
tu.load_tools()

# === COMPOUND DISAMBIGUATION ===
drug_info = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="metformin")
# Returns: {data: {search: {hits: [{id: "CHEMBL1431", name: "METFORMIN", ...}]}}}
chembl_id = drug_info['data']['search']['hits'][0]['id']

drug_desc = tu.tools.OpenTargets_get_drug_id_description_by_name(drugName="metformin")

drugbank_info = tu.tools.drugbank_get_drug_basic_info_by_drug_name_or_id(
    query="metformin", case_sensitive=False, exact_match=True, limit=1
)
# Returns: {status: "success", data: {drug_name: ..., drugbank_id: ..., ...}}

pubchem_cid = tu.tools.PubChem_get_CID_by_compound_name(name="metformin")
# Returns: {IdentifierList: {CID: [4091]}}
cid = pubchem_cid['IdentifierList']['CID'][0]

pubchem_props = tu.tools.PubChem_get_compound_properties_by_CID(cid=cid)
# Returns: {CID: ..., MolecularWeight: ..., ConnectivitySMILES: ..., IUPACName: ...}

# === TARGET DISAMBIGUATION ===
target_info = tu.tools.OpenTargets_get_target_id_description_by_name(targetName="PSEN1")
# Returns: {data: {search: {hits: [{id: "ENSG00000080815", name: "PSEN1", ...}]}}}
ensembl_id = target_info['data']['search']['hits'][0]['id']

gene_details = tu.tools.ensembl_lookup_gene(gene_id=ensembl_id, species='homo_sapiens')
mygene = tu.tools.MyGene_query_genes(query="PSEN1")

# === DISEASE DISAMBIGUATION ===
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(diseaseName="Alzheimer disease")
# Returns: {data: {search: {hits: [{id: "MONDO_0004975", name: "Alzheimer disease", ...}]}}}
disease_id = disease_info['data']['search']['hits'][0]['id']

disease_desc = tu.tools.OpenTargets_get_disease_description_by_efoId(efoId=disease_id)
disease_ids = tu.tools.OpenTargets_get_disease_ids_by_efoId(efoId=disease_id)
```

---

## Phase 1: Network Node Identification

**Step 1.1**: Identify compound nodes.

```python
# Drug targets and mechanism of action
drug_moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
# Returns: {data: {drug: {mechanismsOfAction: {rows: [{mechanismOfAction, actionType, targetName, targets: [{id, approvedSymbol}]}]}}}}

drug_targets_ot = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(chemblId=chembl_id, size=50)
drug_targets_db = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    query="metformin", case_sensitive=False, exact_match=True, limit=1
)

dgidb_interactions = tu.tools.DGIdb_get_drug_gene_interactions(genes=["PSEN1", "APP", "BACE1"])
ctd_genes = tu.tools.CTD_get_chemical_gene_interactions(input_terms="Metformin")

stitch_id = tu.tools.STITCH_resolve_identifier(identifier="metformin", species=9606)
stitch_interactions = tu.tools.STITCH_get_chemical_protein_interactions(
    identifiers=["CIDm000004091"], species=9606
)

drug_indications = tu.tools.OpenTargets_get_drug_indications_by_chemblId(chemblId=chembl_id, size=50)
fda_approval = tu.tools.OpenTargets_get_drug_approval_status_by_chemblId(chemblId=chembl_id)
drug_diseases = tu.tools.OpenTargets_get_associated_diseases_by_drug_chemblId(chemblId=chembl_id, size=50)
```

**Step 1.2**: Identify target nodes (disease-associated targets).

```python
disease_targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(efoId=disease_id, limit=50)

for target in disease_targets['data']['disease']['associatedTargets']['rows'][:10]:
    evidence = tu.tools.OpenTargets_target_disease_evidence(
        efoId=disease_id, ensemblId=target['target']['id']
    )

gwas_studies = tu.tools.OpenTargets_search_gwas_studies_by_disease(diseaseIds=[disease_id], size=20)
ctd_diseases = tu.tools.CTD_get_gene_diseases(input_terms="PSEN1")

for gene in ["PSEN1", "APP", "BACE1"]:
    pharos = tu.tools.Pharos_get_target(target_name=gene)
```

**Step 1.3**: Identify disease nodes and related conditions.

```python
related_diseases = tu.tools.OpenTargets_get_similar_entities_by_disease_efoId(efoId=disease_id, size=10, threshold=0.5)
disease_children = tu.tools.OpenTargets_get_disease_descendants_children_by_efoId(efoId=disease_id)
disease_parents = tu.tools.OpenTargets_get_disease_ancestors_parents_by_efoId(efoId=disease_id)
disease_phenotypes = tu.tools.OpenTargets_get_associated_phenotypes_by_disease_efoId(efoId=disease_id, size=20)
disease_areas = tu.tools.OpenTargets_get_disease_therapeutic_areas_by_efoId(efoId=disease_id)
```

---

## Phase 2: Network Edge Construction

**Step 2.1**: Compound-target edges (bioactivity data).

```python
chembl_activities = tu.tools.ChEMBL_get_target_activities(target_chembl_id__exact="CHEMBL2111455", limit=50)
all_mechanisms = tu.tools.ChEMBL_search_mechanisms(query="metformin", limit=50)

db_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    query="metformin", case_sensitive=False, exact_match=True, limit=1
)
db_pharmacology = tu.tools.drugbank_get_pharmacology_by_drug_name_or_drugbank_id(
    query="metformin", case_sensitive=False, exact_match=True, limit=1
)
```

**Step 2.2**: Target-disease edges (genetic and functional associations).

```python
for target in top_disease_targets[:10]:
    td_evidence = tu.tools.OpenTargets_target_disease_evidence(
        efoId=disease_id, ensemblId=target['target']['id']
    )

for gene_symbol in ["PSEN1", "APP", "APOE"]:
    gwas_assoc = tu.tools.GWAS_search_associations_by_gene(gene_name=gene_symbol)

ctd_gene_diseases = tu.tools.CTD_get_gene_diseases(input_terms="PSEN1")
pharmgkb_gene = tu.tools.PharmGKB_get_gene_details(gene_symbol="PSEN1")
```

**Step 2.3**: Compound-disease edges (clinical evidence).

```python
trials = tu.tools.search_clinical_trials(query_term="metformin", condition="Alzheimer", pageSize=20)
trials2 = tu.tools.clinical_trials_search(query="metformin Alzheimer disease", limit=20)

ctd_chem_diseases = tu.tools.CTD_get_chemical_diseases(input_terms="Metformin")

pubmed_results = tu.tools.PubMed_search_articles(query="metformin Alzheimer disease", max_results=50)
europepmc_results = tu.tools.EuropePMC_search_articles(query="metformin Alzheimer disease", limit=50)
```

**Step 2.4**: Target-target edges (PPI network).

```python
string_ppi = tu.tools.STRING_get_interaction_partners(
    protein_ids=["PSEN1", "APP", "APOE", "BACE1", "MAPT"], species=9606, limit=20
)
string_network = tu.tools.STRING_get_network(
    protein_ids=["PSEN1", "APP", "APOE", "BACE1", "MAPT"], species=9606
)
intact_results = tu.tools.intact_search_interactions(query="PSEN1", max=20)

ot_interactions = tu.tools.OpenTargets_get_target_interactions_by_ensemblID(
    ensemblId="ENSG00000080815", size=20
)

humanbase_ppi = tu.tools.humanbase_ppi_analysis(
    gene_list=["PSEN1", "APP", "APOE", "BACE1", "MAPT"],
    tissue="brain", max_node=50, interaction="sn", string_mode="physical"
)
```

---

## Phase 3: Network Analysis

**Step 3.1**: Network topology analysis (computed from collected data).

```
Compute from Phase 2 data:

1. Node Degree: Count connections per node from STRING + IntAct + OpenTargets interactions
2. Hub Identification: Nodes with degree > mean + 2*SD are hubs
3. Betweenness Centrality: Nodes on shortest paths between drug targets and disease genes
4. Network Modules: Disease module vs drug module clusters; overlap = direct relevance
5. Shortest Paths:
   - Path length < 2 = direct interaction
   - Path length 2-3 = close proximity
   - Path length > 4 = distant, weaker association
```

**Step 3.2**: Network proximity calculation.

```
Network Proximity Z-score:
1. Collect drug target set T_d and disease gene set G_d
2. For each pair (t, g): find shortest path d(t,g) in PPI network
3. Compute closest proximity: d_c = mean of min distances
4. Compare against random: Z = (d_c - mean_random) / sd_random
5. Score: Z < -2 (35pts), Z < -1 (20pts), Z < -0.5 (10pts), else 0pts

Practical computation from STRING/OpenTargets PPI data:
- Count direct interactions between drug targets and disease genes
- Count shared PPI partners (second-degree connections)
- Calculate overlap coefficient = shared_partners / min(degree_t, degree_d)
- Use shared pathways as additional proximity metric
```

**Step 3.3**: Functional enrichment analysis.

```python
disease_gene_symbols = [t['target']['approvedSymbol']
                        for t in disease_targets['data']['disease']['associatedTargets']['rows'][:20]]

string_enrichment = tu.tools.STRING_functional_enrichment(protein_ids=disease_gene_symbols, species=9606)
string_ppi_enrich = tu.tools.STRING_ppi_enrichment(protein_ids=disease_gene_symbols, species=9606)

enrichr_results = tu.tools.enrichr_gene_enrichment_analysis(
    gene_list=disease_gene_symbols,
    libs=["KEGG_2021_Human", "Reactome_2022", "GO_Biological_Process_2023"]
)

reactome_enrichment = tu.tools.ReactomeAnalysis_pathway_enrichment(
    identifiers=" ".join(disease_gene_symbols)
)
```

---

## Phase 4: Drug Repurposing Predictions

**Step 4.1**: Identify and rank repurposing candidates.

```python
# Disease-to-compound mode: Find drugs targeting disease genes
for target in disease_targets['data']['disease']['associatedTargets']['rows'][:20]:
    gene_symbol = target['target']['approvedSymbol']
    ensembl_id = target['target']['id']

    target_drugs = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(ensemblId=ensembl_id, size=20)
    dgidb_drugs = tu.tools.DGIdb_get_drug_gene_interactions(genes=[gene_symbol])
    drugbank_drugs = tu.tools.drugbank_get_drug_name_and_description_by_target_name(
        query=gene_symbol, case_sensitive=False, exact_match=False, limit=20
    )

# Compound-to-disease mode: Find diseases for each drug target
for target in drug_targets:
    target_diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensembl(
        ensemblId=target['id'], size=20
    )
```

**Step 4.2**: Mechanism prediction for repurposing candidates.

```python
drug_moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=candidate_chembl_id)

drug_target_genes = [t['approvedSymbol'] for t in drug_moa_targets]
combined_genes = list(set(drug_target_genes + disease_gene_symbols[:10]))

combined_pathways = tu.tools.ReactomeAnalysis_pathway_enrichment(identifiers=" ".join(combined_genes))
drug_pathways = tu.tools.drugbank_get_pathways_reactions_by_drug_or_id(
    query=drug_name, case_sensitive=False, exact_match=True, limit=1
)
```

---

## Phase 5: Polypharmacology Analysis

**Step 5.1**: Multi-target profiling.

```python
all_drug_targets = tu.tools.OpenTargets_get_associated_targets_by_drug_chemblId(chemblId=chembl_id, size=100)

db_full_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    query=drug_name, case_sensitive=False, exact_match=True, limit=1
)
ctd_interactions = tu.tools.CTD_get_chemical_gene_interactions(input_terms=drug_name)

# Disease module coverage
drug_target_set = set(drug_target_genes)
disease_gene_set = set(disease_gene_symbols[:50])
overlap = drug_target_set & disease_gene_set
coverage = len(overlap) / len(disease_gene_set) if disease_gene_set else 0

# Target family analysis
for gene in drug_target_genes[:10]:
    target_class = tu.tools.OpenTargets_get_target_classes_by_ensemblID(ensemblId=gene_ensembl_id)
```

**Step 5.2**: Selectivity analysis.

```python
for gene in drug_target_genes[:10]:
    druggability = tu.tools.DGIdb_get_gene_druggability(genes=[gene])
    pharos_info = tu.tools.Pharos_get_target(target_name=gene)
    tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(ensemblId=gene_ensembl_id)
```

---

## Phase 6: Safety and Toxicity Context

**Step 6.1**: Adverse event profiling.

```python
faers_ae = tu.tools.FAERS_search_reports_by_drug_and_reaction(drug_name=drug_name, limit=100)
faers_serious = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events", drug_name=drug_name, seriousness_type="all"
)
faers_death = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct=drug_name)

faers_signal = tu.tools.FAERS_calculate_disproportionality(
    operation="calculate_disproportionality", drug_name=drug_name, adverse_event="lactic acidosis"
)

fda_warnings = tu.tools.FDA_get_warnings_and_cautions_by_drug_name(drug_name=drug_name)
bbox_warning = tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId=chembl_id)
ot_ae = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId=chembl_id)
drug_warnings = tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId=chembl_id)
```

**Step 6.2**: Target safety profiling.

```python
for target_ensembl_id in drug_target_ensembl_ids[:10]:
    safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(ensemblId=target_ensembl_id)
    constraints = tu.tools.gnomad_get_gene_constraints(gene_symbol=gene_symbol)
    # High pLI (>0.9) = loss-of-function intolerant = essential gene = safety concern
    expression = tu.tools.HPA_get_rna_expression_by_source(
        gene_name=gene_symbol, source_type="tissue", source_name="brain"
    )
```

---

## Phase 7: Validation Evidence

**Step 7.1**: Clinical precedent.

```python
trials = tu.tools.search_clinical_trials(query_term=drug_name, condition=disease_name, pageSize=20)

for trial in trials.get('studies', [])[:5]:
    nct_id = trial['NCT ID']
    trial_details = tu.tools.clinical_trials_get_details(nct_id=nct_id)
    trial_outcomes = tu.tools.extract_clinical_trial_outcomes(nct_id=nct_id)
    trial_ae = tu.tools.extract_clinical_trial_adverse_events(nct_id=nct_id)

approved = tu.tools.OpenTargets_get_approved_indications_by_drug_chemblId(chemblId=chembl_id)
```

**Step 7.2**: Literature evidence.

```python
pubmed_evidence = tu.tools.PubMed_search_articles(
    query=f"{drug_name} {disease_name} repurposing OR repositioning OR network pharmacology",
    max_results=50
)
europepmc_evidence = tu.tools.EuropePMC_search_articles(query=f"{drug_name} {disease_name}", limit=50)
ot_drug_pubs = tu.tools.OpenTargets_get_publications_by_drug_chemblId(chemblId=chembl_id, size=20)
ot_disease_pubs = tu.tools.OpenTargets_get_publications_by_disease_efoId(efoId=disease_id, size=20)
guidelines = tu.tools.PubMed_Guidelines_Search(query=f"{drug_name} {disease_name}")
```

**Step 7.3**: Experimental evidence.

```python
chembl_bioactivity = tu.tools.ChEMBL_search_drugs(query=drug_name, limit=10)

if smiles:
    admet = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
    bbb = tu.tools.ADMETAI_predict_BBB_penetrance(smiles=[smiles])
    bioavail = tu.tools.ADMETAI_predict_bioavailability(smiles=[smiles])

pharmgkb_drug = tu.tools.PharmGKB_get_drug_details(drug_name=drug_name)
pharmgkb_clin = tu.tools.PharmGKB_get_clinical_annotations(query=drug_name)
```
