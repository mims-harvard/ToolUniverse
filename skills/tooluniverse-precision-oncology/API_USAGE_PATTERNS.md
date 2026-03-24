# API Usage Patterns for Precision Oncology

Detailed code examples and parameter references for each phase of the precision oncology workflow.

---

## Phase 1: Profile Validation

### 1.1 Resolve Gene Identifiers

```python
def resolve_gene(tu, gene_symbol):
    """Resolve gene to all needed IDs."""
    ids = {}

    # Ensembl ID (for OpenTargets)
    gene_info = tu.tools.MyGene_query_genes(q=gene_symbol, species="human")
    ids['ensembl'] = gene_info.get('ensembl', {}).get('gene')

    # UniProt (for structure)
    uniprot = tu.tools.UniProt_search(query=gene_symbol, organism="human")
    ids['uniprot'] = uniprot[0].get('primaryAccession') if uniprot else None

    # ChEMBL target
    target = tu.tools.ChEMBL_search_targets(query=gene_symbol, organism="Homo sapiens")
    ids['chembl_target'] = target[0].get('target_chembl_id') if target else None

    return ids
```

### 1.2 Validate Variant Nomenclature

- **HGVS protein**: p.L858R, p.V600E
- **cDNA**: c.2573T>G
- **Common names**: T790M, G12C

---

## Phase 2: Variant Interpretation

### 2.1 CIViC Evidence Query

```python
def get_civic_evidence(tu, gene_symbol, variant_name):
    """Get CIViC evidence for variant."""
    variants = tu.tools.civic_search_variants(query=f"{gene_symbol} {variant_name}")

    evidence_items = []
    for var in variants:
        evi = tu.tools.civic_get_variant(id=var['id'])
        evidence_items.extend(evi.get('evidence_items', []))

    return {
        'predictive': [e for e in evidence_items if e['evidence_type'] == 'Predictive'],
        'prognostic': [e for e in evidence_items if e['evidence_type'] == 'Prognostic'],
        'diagnostic': [e for e in evidence_items if e['evidence_type'] == 'Diagnostic']
    }
```

### 2.2 COSMIC Somatic Mutation Analysis

```python
def get_cosmic_mutations(tu, gene_symbol, variant_name=None):
    """Get somatic mutation data from COSMIC database."""
    gene_mutations = tu.tools.COSMIC_get_mutations_by_gene(
        operation="get_by_gene",
        gene=gene_symbol,
        max_results=100,
        genome_build=38
    )

    if variant_name:
        specific = tu.tools.COSMIC_search_mutations(
            operation="search",
            terms=f"{gene_symbol} {variant_name}",
            max_results=20
        )
        return {
            'specific_variant': specific.get('results', []),
            'all_gene_mutations': gene_mutations.get('results', [])
        }

    return gene_mutations

def get_cosmic_hotspots(tu, gene_symbol):
    """Identify mutation hotspots in COSMIC."""
    mutations = tu.tools.COSMIC_get_mutations_by_gene(
        operation="get_by_gene",
        gene=gene_symbol,
        max_results=500
    )
    position_counts = Counter(m['MutationAA'] for m in mutations.get('results', []))
    return position_counts.most_common(10)
```

**Why COSMIC matters**:
- Gold standard for somatic cancer mutations
- Cancer type distribution (which cancers have this mutation)
- FATHMM pathogenicity prediction for novel variants
- Identifies hotspots vs. rare mutations

### 2.3 GDC/TCGA Pan-Cancer Analysis

```python
def get_tcga_mutation_data(tu, gene_symbol, cancer_type=None):
    """Get somatic mutations from TCGA via GDC."""
    frequency = tu.tools.GDC_get_mutation_frequency(gene_symbol=gene_symbol)

    mutations = tu.tools.GDC_get_ssm_by_gene(
        gene_symbol=gene_symbol,
        project_id=f"TCGA-{cancer_type}" if cancer_type else None,
        size=50
    )

    return {
        'frequency': frequency.get('data', {}),
        'mutations': mutations.get('data', {})
    }

def get_tcga_expression_profile(tu, gene_symbol, cancer_type):
    """Get gene expression data from TCGA."""
    project_map = {
        'lung': 'TCGA-LUAD', 'breast': 'TCGA-BRCA',
        'colorectal': 'TCGA-COAD', 'melanoma': 'TCGA-SKCM',
        'glioblastoma': 'TCGA-GBM'
    }
    project_id = project_map.get(cancer_type.lower(), f'TCGA-{cancer_type.upper()}')

    expression = tu.tools.GDC_get_gene_expression(project_id=project_id, size=20)
    return expression.get('data', {})

def get_tcga_cnv_status(tu, gene_symbol, cancer_type):
    """Get copy number status from TCGA."""
    project_map = {'lung': 'TCGA-LUAD', 'breast': 'TCGA-BRCA'}
    project_id = project_map.get(cancer_type.lower(), f'TCGA-{cancer_type.upper()}')

    cnv = tu.tools.GDC_get_cnv_data(
        project_id=project_id, gene_symbol=gene_symbol, size=20
    )
    return cnv.get('data', {})
```

**GDC Tools Summary**:
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `GDC_get_mutation_frequency` | Pan-cancer mutation stats | `gene_symbol` |
| `GDC_get_ssm_by_gene` | Specific mutations | `gene_symbol`, `project_id` |
| `GDC_get_gene_expression` | RNA-seq data | `project_id` |
| `GDC_get_cnv_data` | Copy number | `project_id`, `gene_symbol` |
| `GDC_list_projects` | Find TCGA projects | `program="TCGA"` |

### 2.4 DepMap Target Validation

```python
def assess_target_essentiality(tu, gene_symbol, cancer_type=None):
    """Is this gene essential in cancer cell lines?"""
    dependencies = tu.tools.DepMap_get_gene_dependencies(gene_symbol=gene_symbol)

    if cancer_type:
        cell_lines = tu.tools.DepMap_get_cell_lines(
            cancer_type=cancer_type, page_size=20
        )
        return {
            'gene': gene_symbol,
            'dependencies': dependencies.get('data', {}),
            'cell_lines': cell_lines.get('data', {}),
            'interpretation': 'Negative scores = gene is essential for cell survival'
        }
    return dependencies

def get_depmap_drug_sensitivity(tu, drug_name, cancer_type=None):
    """Get drug sensitivity data from DepMap."""
    drugs = tu.tools.DepMap_get_drug_response(drug_name=drug_name)
    return drugs.get('data', {})
```

**DepMap Tools Summary**:
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DepMap_get_gene_dependencies` | CRISPR essentiality | `gene_symbol` |
| `DepMap_get_cell_lines` | Cell line metadata | `cancer_type`, `tissue` |
| `DepMap_search_cell_lines` | Search by name | `query` |
| `DepMap_get_drug_response` | Drug sensitivity | `drug_name` |

### 2.5 OncoKB Actionability Assessment

```python
def get_oncokb_annotations(tu, gene_symbol, variant_name, tumor_type=None):
    """Get OncoKB actionability annotations."""
    annotation = tu.tools.OncoKB_annotate_variant(
        operation="annotate_variant",
        gene=gene_symbol,
        variant=variant_name,
        tumor_type=tumor_type  # OncoTree code e.g., "MEL", "LUAD"
    )

    result = {
        'oncogenic': annotation.get('data', {}).get('oncogenic'),
        'mutation_effect': annotation.get('data', {}).get('mutationEffect'),
        'highest_sensitive_level': annotation.get('data', {}).get('highestSensitiveLevel'),
        'treatments': annotation.get('data', {}).get('treatments', [])
    }

    gene_info = tu.tools.OncoKB_get_gene_info(
        operation="get_gene_info", gene=gene_symbol
    )
    result['is_oncogene'] = gene_info.get('data', {}).get('oncogene', False)
    result['is_tumor_suppressor'] = gene_info.get('data', {}).get('tsg', False)

    return result

def get_oncokb_cnv_annotation(tu, gene_symbol, alteration_type, tumor_type=None):
    """Get OncoKB annotation for copy number alterations."""
    annotation = tu.tools.OncoKB_annotate_copy_number(
        operation="annotate_copy_number",
        gene=gene_symbol,
        copy_number_type=alteration_type,  # "AMPLIFICATION" or "DELETION"
        tumor_type=tumor_type
    )
    return {
        'oncogenic': annotation.get('data', {}).get('oncogenic'),
        'treatments': annotation.get('data', {}).get('treatments', [])
    }
```

### 2.6 cBioPortal Cross-Study Analysis

```python
def get_cbioportal_mutations(tu, gene_symbols, study_id="brca_tcga"):
    """Get mutation data from cBioPortal across cancer studies."""
    mutations = tu.tools.cBioPortal_get_mutations(
        study_id=study_id,
        gene_list=",".join(gene_symbols)
    )

    results = []
    for mut in mutations or []:
        results.append({
            'gene': mut.get('gene', {}).get('hugoGeneSymbol'),
            'protein_change': mut.get('proteinChange'),
            'mutation_type': mut.get('mutationType'),
            'sample_id': mut.get('sampleId'),
            'validation_status': mut.get('validationStatus')
        })
    return results

def get_cbioportal_cancer_studies(tu, cancer_type=None):
    """Get available cancer studies from cBioPortal."""
    studies = tu.tools.cBioPortal_get_cancer_studies(limit=50)
    if cancer_type:
        studies = [s for s in studies if cancer_type.lower() in s.get('cancerTypeId', '').lower()]
    return studies

def analyze_co_mutations(tu, gene_symbol, study_id):
    """Find frequently co-mutated genes."""
    profiles = tu.tools.cBioPortal_get_molecular_profiles(study_id=study_id)
    mutations = tu.tools.cBioPortal_get_mutations(
        study_id=study_id, gene_list=gene_symbol
    )
    return {'profiles': profiles, 'mutations': mutations, 'study_id': study_id}
```

**cBioPortal Use Cases**:
| Use Case | Tool | Parameters |
|----------|------|------------|
| Find mutation frequency | `cBioPortal_get_mutations` | `study_id`, `gene_list` |
| List available studies | `cBioPortal_get_cancer_studies` | `limit` |
| Get molecular profiles | `cBioPortal_get_molecular_profiles` | `study_id` |

### 2.7 Human Protein Atlas Expression

```python
def get_hpa_expression(tu, gene_symbol):
    """Get protein expression data from Human Protein Atlas."""
    gene_info = tu.tools.HPA_search_genes_by_query(search_query=gene_symbol)
    if not gene_info:
        return None

    cell_line_data = tu.tools.HPA_get_comparative_expression_by_gene_and_cellline(
        gene_name=gene_symbol,
        cell_line="a549"  # Lung cancer cell line
    )
    return {'gene_info': gene_info, 'cell_line_expression': cell_line_data}

def check_tumor_specific_expression(tu, gene_symbol, cancer_type):
    """Check if target has tumor-specific expression pattern."""
    cancer_to_cellline = {
        'lung': 'a549', 'breast': 'mcf7', 'liver': 'hepg2',
        'cervical': 'hela', 'prostate': 'pc3'
    }
    cell_line = cancer_to_cellline.get(cancer_type.lower(), 'a549')

    return tu.tools.HPA_get_comparative_expression_by_gene_and_cellline(
        gene_name=gene_symbol, cell_line=cell_line
    )
```

---

## Phase 2.5: Tumor Expression Context (CELLxGENE)

```python
def get_tumor_expression_context(tu, gene_symbol, cancer_type):
    """Get cell-type specific expression in tumor microenvironment."""
    expression = tu.tools.CELLxGENE_get_expression_data(
        gene=gene_symbol, tissue=cancer_type
    )
    cell_metadata = tu.tools.CELLxGENE_get_cell_metadata(gene=gene_symbol)

    tumor_expression = [c for c in expression if 'tumor' in c.get('cell_type', '').lower()]
    normal_expression = [c for c in expression if 'normal' in c.get('cell_type', '').lower()]

    return {
        'tumor_expression': tumor_expression,
        'normal_expression': normal_expression,
        'ratio': calculate_tumor_normal_ratio(tumor_expression, normal_expression)
    }
```

**Why it matters**:
- Confirms target is expressed in tumor cells (not just stroma)
- Identifies potential resistance from tumor heterogeneity
- Supports drug selection based on expression patterns

---

## Phase 3: Treatment Options

### Query Order
1. `OpenTargets_get_associated_drugs_by_target_ensemblId` -> Approved drugs
2. `DailyMed_search_spls` -> FDA label details
3. `ChEMBL_get_drug_mechanisms_of_action_by_chemblId` -> Mechanism

### Treatment Output Example

```markdown
## Treatment Recommendations

### First-Line Options
**1. Osimertinib (Tagrisso)** (Tier 1)
- FDA-approved for EGFR T790M+ NSCLC
- Evidence: AURA3 trial (ORR 71%, mPFS 10.1 mo)
- Source: FDA label, PMID:27959700

### Second-Line Options
**2. Combination: Osimertinib + [Agent]** (Tier 2)
- Evidence: Phase 2 data
- Source: NCT04487080
```

---

## Phase 3.5: Pathway & Network Analysis

### Pathway Context (KEGG/Reactome)

```python
def get_pathway_context(tu, gene_symbols, cancer_type):
    """Get pathway context for drug combinations and resistance."""
    pathway_map = {}
    for gene in gene_symbols:
        kegg_gene = tu.tools.kegg_find_genes(query=f"hsa:{gene}")
        if kegg_gene:
            pathways = tu.tools.kegg_get_gene_info(gene_id=kegg_gene[0]['id'])
            pathway_map[gene] = pathways.get('pathways', [])

        reactome = tu.tools.reactome_disease_target_score(
            disease=cancer_type, target=gene
        )
        pathway_map[f"{gene}_reactome"] = reactome
    return pathway_map
```

### Protein Interaction Network (IntAct)

```python
def get_resistance_network(tu, drug_target, bypass_candidates):
    """Find protein interactions that may mediate resistance."""
    network = tu.tools.intact_get_interaction_network(
        gene=drug_target, depth=2
    )
    bypass_in_network = [
        node for node in network['nodes']
        if node['gene'] in bypass_candidates
    ]
    return {
        'network': network,
        'bypass_connections': bypass_in_network,
        'total_interactors': len(network['nodes'])
    }
```

---

## Phase 4: Resistance Analysis

### Known Mechanisms (Literature + CIViC)

```python
def analyze_resistance(tu, drug_name, gene_symbol):
    """Find known resistance mechanisms."""
    resistance = tu.tools.civic_search_evidence_items(
        drug=drug_name,
        evidence_type="Predictive",
        clinical_significance="Resistance"
    )
    papers = tu.tools.PubMed_search_articles(
        query=f'"{drug_name}" AND "{gene_symbol}" AND resistance',
        limit=20
    )
    return {'civic': resistance, 'literature': papers}
```

### Structure-Based Analysis (NvidiaNIM)

```python
def model_resistance_mechanism(tu, gene_ids, mutation, drug_smiles):
    """Model structural impact of resistance mutation."""
    structure = tu.tools.NvidiaNIM_alphafold2(sequence=wild_type_sequence)
    wt_docking = tu.tools.NvidiaNIM_diffdock(
        protein=structure['structure'],
        ligand=drug_smiles,
        num_poses=5
    )
    # Compare binding site changes
    # Report: "T790M introduces bulky methionine, steric clash with erlotinib"
```

---

## Phase 5: Clinical Trial Matching

```python
def find_trials(tu, condition, biomarker, location=None):
    """Find matching clinical trials."""
    trials = tu.tools.search_clinical_trials(
        condition=condition,
        intervention=biomarker,
        status="Recruiting",
        pageSize=50
    )
    nct_ids = [t['nct_id'] for t in trials[:20]]
    eligibility = tu.tools.get_clinical_trial_eligibility_criteria(nct_ids=nct_ids)
    return trials, eligibility
```

---

## Phase 5.5: Literature Evidence

### Published Literature (PubMed)

```python
def search_treatment_literature(tu, cancer_type, biomarker, drug_name):
    """Search for treatment evidence in literature."""
    drug_papers = tu.tools.PubMed_search_articles(
        query=f'"{drug_name}" AND "{biomarker}" AND "{cancer_type}"',
        limit=20
    )
    resistance_papers = tu.tools.PubMed_search_articles(
        query=f'"{drug_name}" AND resistance AND mechanism',
        limit=15
    )
    return {'treatment_evidence': drug_papers, 'resistance_literature': resistance_papers}
```

### Preprints (BioRxiv/MedRxiv)

```python
def search_preprints(tu, cancer_type, biomarker):
    """Search preprints for cutting-edge findings."""
    biorxiv = tu.tools.BioRxiv_list_recent_preprints(
        query=f"{cancer_type} {biomarker} treatment", limit=10
    )
    medrxiv = tu.tools.MedRxiv_get_preprint(
        query=f"{cancer_type} {biomarker}", limit=10
    )
    return {'biorxiv': biorxiv, 'medrxiv': medrxiv}
```

### Citation Analysis (OpenAlex)

```python
def analyze_key_papers(tu, key_papers):
    """Get citation metrics for key evidence papers."""
    analyzed = []
    for paper in key_papers[:10]:
        work = tu.tools.openalex_search_works(query=paper['title'], limit=1)
        if work:
            analyzed.append({
                'title': paper['title'],
                'citations': work[0].get('cited_by_count', 0),
                'year': work[0].get('publication_year'),
                'open_access': work[0].get('is_oa', False)
            })
    return analyzed
```
