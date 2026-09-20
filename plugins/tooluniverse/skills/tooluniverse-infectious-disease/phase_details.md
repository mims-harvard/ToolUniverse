# Infectious Disease Outbreak Intelligence - Phase Details

## Phase 1: Pathogen Identification

### 1.1 Taxonomic Classification

```python
def identify_pathogen(tu, pathogen_query):
    """Classify pathogen taxonomically."""
    taxonomy = tu.tools.NCBIDatasets_suggest_taxonomy(query=pathogen_query)
    return {
        'taxid': taxonomy.get('taxid'),
        'scientific_name': taxonomy.get('scientific_name'),
        'rank': taxonomy.get('rank'),
        'lineage': taxonomy.get('lineage'),
        'type': classify_type(taxonomy)  # virus, bacteria, fungus, parasite
    }
```

### 1.2 Related Pathogens (Knowledge Transfer)

```python
def find_related_pathogens(tu, taxid, relative_names):
    """Find related pathogens for drug knowledge transfer.

    ToolUniverse has no tool that lists an NCBI taxon's child taxa, so the
    caller supplies candidate relatives (organism names); the pathogen's genus
    is read from its NCBI lineage.
    """
    tax = tu.tools.NCBIDatasets_get_taxonomy(tax_id=str(taxid))['data']
    genus = next((x for x in tax['lineage_names'] if x['rank'] == 'GENUS'), None)
    related_with_drugs = []
    for name in relative_names:
        result = tu.tools.ChEMBL_search_targets(organism=name, limit=10)
        targets = result['data']['targets']
        if targets:
            related_with_drugs.append({'pathogen': name, 'targets': targets})
    return {'genus': genus, 'related_with_drugs': related_with_drugs}
```

### 1.3 Output Example

```markdown
## 1. Pathogen Profile

### 1.1 Taxonomic Classification

| Property | Value |
|----------|-------|
| **Organism** | SARS-CoV-2 |
| **Taxonomy ID** | 2697049 |
| **Type** | RNA virus (positive-sense, single-stranded) |
| **Family** | Coronaviridae |
| **Genus** | Betacoronavirus |

### 1.2 Related Pathogens with Drug Precedent

| Relative | Similarity | Approved Drugs | Relevance |
|----------|------------|----------------|-----------|
| SARS-CoV | 79% genome | Remdesivir (EUA) | High |
| MERS-CoV | 50% genome | None approved | Medium |
```

---

## Phase 2: Target Identification

### 2.1 Essential Protein Identification

```python
def identify_targets(tu, pathogen_name):
    """Identify essential druggable targets."""
    # "reviewed" is a UniProt query field, not a tool parameter
    proteins = tu.tools.UniProt_search(
        query=f"organism:{pathogen_name} AND reviewed:true"
    )['data']['results']  # [{accession, id, protein_name, gene_names, organism, length}]
    targets = []
    for protein in proteins:
        # ChEMBL_search_targets filters by target NAME (pref_name__contains), not gene symbol
        chembl_target = tu.tools.ChEMBL_search_targets(
            pref_name__contains=protein['protein_name'], limit=5
        )['data']['targets']
        targets.append({
            'uniprot': protein['accession'],
            'name': protein['protein_name'],
            'has_drug_precedent': len(chembl_target) > 0,
            'druggability': assess_druggability(protein)
        })
    return rank_targets(targets)
```

### 2.2 Target Prioritization Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Essentiality** | 30% | Required for replication/survival |
| **Conservation** | 25% | Conserved across strains/variants |
| **Druggability** | 25% | Structural features amenable to binding |
| **Drug precedent** | 20% | Existing drugs for homologous targets |

---

## Phase 3: Structure Prediction

```python
def predict_target_structure(tu, sequence, target_name):
    """Predict structure using AlphaFold2 via NVIDIA NIM."""
    structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=sequence, algorithm="mmseqs2", relax_prediction=False
    )
    plddt_scores = parse_plddt(structure)
    return {
        'structure': structure['structure'],
        'mean_plddt': np.mean(plddt_scores),
        'high_confidence_regions': get_high_confidence(plddt_scores),
        'predicted_binding_site': identify_binding_site(structure)
    }
```

### pLDDT Quality Assessment

| pLDDT Range | Confidence | Use for Docking |
|-------------|------------|-----------------|
| >90 | Very High | Excellent |
| 70-90 | High | Good |
| 50-70 | Medium | Use caution |
| <50 | Low | Not recommended |

---

## Phase 4: Drug Repurposing Screen

### 4.1 Identify Candidates

```python
def get_repurposing_candidates(tu, target_name, pathogen_family):
    """Find approved drugs to repurpose."""
    candidates = []
    # 1. Drugs approved for related pathogens
    candidates.extend(tu.tools.ChEMBL_search_drugs(
        query=pathogen_family, max_phase=4))
    # 2. Broad-spectrum antivirals
    candidates.extend(tu.tools.ChEMBL_search_drugs(
        query="broad spectrum antiviral", max_phase=4))
    # 3. Drugs with known activity against target class
    candidates.extend(tu.tools.DGIdb_get_drug_gene_interactions(
        genes=[target_name]))
    return deduplicate(candidates)
```

### 4.2 Docking Screen (NVIDIA NIM)

```python
def dock_candidates(tu, target_structure, candidate_smiles_list):
    """Dock candidate drugs against target."""
    results = []
    for smiles in candidate_smiles_list:
        docking = tu.tools.NvidiaNIM_diffdock(
            protein=target_structure, ligand=smiles, num_poses=5
        )
        results.append({
            'smiles': smiles,
            'top_score': docking['poses'][0]['confidence'],
            'poses': docking['poses']
        })
    return sorted(results, key=lambda x: x['top_score'], reverse=True)
```

---

## Phase 4.5: Pathway Analysis

```python
def analyze_pathogen_pathways(tu, pathogen_name, pathogen_type):
    """Identify druggable metabolic pathways in pathogen."""
    # Returns data: [{pathway_id, description}]
    pathways = tu.tools.kegg_search_pathway(keyword=f"{pathogen_name} metabolism")['data']
    essential_genes = tu.tools.KEGG_get_pathway_genes(
        pathway_id=pathways[0]['pathway_id'])
    host_pathogen = tu.tools.kegg_search_pathway(
        keyword=f"{pathogen_name} host interaction")['data']
    return {
        'metabolic_pathways': pathways,
        'essential_genes': essential_genes,
        'host_interaction': host_pathogen
    }
```

---

## Phase 5: Literature Intelligence

```python
def comprehensive_outbreak_literature(tu, pathogen_name):
    """Search all literature sources for outbreak intelligence."""
    pubmed = tu.tools.PubMed_search_articles(
        query=f"{pathogen_name} AND (outbreak OR treatment OR drug)",
        limit=50, sort="date")
    # bioRxiv/medRxiv tools have no keyword search (BioRxiv_list_recent_preprints needs a
    # start/end date range; MedRxiv_get_preprint needs a DOI) - search preprints via Europe PMC
    biorxiv = tu.tools.EuropePMC_search_articles(
        query=f"SRC:PPR AND {pathogen_name} treatment mechanism", limit=20)['data']
    medrxiv = tu.tools.EuropePMC_search_articles(
        query=f"SRC:PPR AND {pathogen_name} clinical trial", limit=20)['data']
    # ArXiv_search_papers has no category filter; put "q-bio" terms in the query if needed
    arxiv = tu.tools.ArXiv_search_papers(
        query=f"{pathogen_name} drug discovery", limit=10)['result']
    trials = tu.tools.search_clinical_trials(
        condition=pathogen_name, status="Recruiting")

    key_papers = pubmed[:10]
    for paper in key_papers:
        citation = tu.tools.openalex_search_works(query=paper['title'], limit=1)
        paper['citations'] = citation[0].get('cited_by_count', 0) if citation else 0

    return {
        'pubmed': pubmed, 'biorxiv': biorxiv, 'medrxiv': medrxiv,
        'arxiv': arxiv, 'trials': trials, 'key_papers': key_papers
    }
```

**Note**: Preprints (BioRxiv/MedRxiv) are NOT peer-reviewed but CRITICAL for outbreak intelligence. Always note this caveat in reports.
