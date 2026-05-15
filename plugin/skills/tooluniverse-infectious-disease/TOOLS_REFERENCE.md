# Infectious Disease Outbreak Intelligence - Tool Reference

## Phase 1: Pathogen Identification

### NCBI Taxonomy Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NCBI_Taxonomy_search` | Search taxonomy database | `query` |
| `NCBI_Taxonomy_get_by_id` | Get details by TaxID | `taxid` |
| `NCBI_Taxonomy_get_lineage` | Get full lineage | `taxid` |

**Example - Classify pathogen**:
```python
# Search for pathogen
tax = tu.tools.NCBI_Taxonomy_search(query="SARS-CoV-2")
# Returns: {"taxid": 2697049, "scientific_name": "...", "lineage": [...]}
```

### UniProt Protein Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `UniProt_search` | Search proteins | `query`, `organism` |
| `UniProt_get_protein_by_accession` | Get protein details | `accession` |
| `UniProt_get_protein_sequence` | Get sequence | `accession` |

**Example - Get viral proteins**:
```python
# Search for viral proteins
proteins = tu.tools.UniProt_search(
    query="organism:2697049",  # SARS-CoV-2 TaxID
    reviewed=True
)
```

---

## Phase 2: Target Identification

### ChEMBL Target Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChEMBL_search_targets` | Search targets | `query`, `organism` |
| `ChEMBL_get_target_activities` | Get bioactivity | `target_chembl_id` |
| `ChEMBL_search_drugs` | Search drugs | `query`, `max_phase` |

**Example - Find drug precedent**:
```python
# Search for protease inhibitors
drugs = tu.tools.ChEMBL_search_drugs(
    query="main protease coronavirus",
    max_phase=4  # Approved drugs only
)
```

### DGIdb Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `DGIdb_get_drug_gene_interactions` | Drug-target interactions | `genes` |
| `DGIdb_get_gene_druggability` | Druggability score | `genes` |

---

## Phase 3: Structure Prediction (NVIDIA NIM)

### Structure Prediction Tools

| Tool | Purpose | Key Parameters | Async |
|------|---------|----------------|-------|
| `NvidiaNIM_alphafold2` | High-accuracy prediction | `sequence`, `algorithm` | Yes |
| `NvidiaNIM_esmfold` | Fast prediction | `sequence` | No |
| `NvidiaNIM_openfold2` | Alternative predictor | `sequence` | Yes |

**Example - Predict target structure**:
```python
# High-accuracy prediction
structure = tu.tools.NvidiaNIM_alphafold2(
    sequence=protease_sequence,
    algorithm="mmseqs2",
    relax_prediction=False
)
# Returns: {"structure": "<PDB content>", "plddt": [...]}
```

### Structure Validation

```python
def assess_structure_quality(structure_result):
    """Assess structure quality for docking."""
    plddt = structure_result.get('plddt', [])
    
    mean_plddt = np.mean(plddt)
    high_conf = sum(1 for p in plddt if p > 90) / len(plddt)
    
    return {
        'mean_plddt': mean_plddt,
        'high_confidence_fraction': high_conf,
        'docking_suitable': mean_plddt > 70 and high_conf > 0.5
    }
```

---

## Phase 4: Drug Repurposing

### ChEMBL Drug Search

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ChEMBL_search_drugs` | Search approved drugs | `query`, `max_phase` |
| `ChEMBL_get_molecule` | Get drug details | `molecule_chembl_id` |
| `ChEMBL_get_drug_mechanisms_of_action` | Get MOA | `molecule_chembl_id` |

### DrugBank Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `drugbank_vocab_search` | Search drugs | `query` |
| `DrugBank_get_drug` | Get drug details | `drugbank_id` |
| `DrugBank_get_targets` | Get drug targets | `drugbank_id` |

### Docking Tools (NVIDIA NIM)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `NvidiaNIM_diffdock` | Blind docking | `protein`, `ligand`, `num_poses` |
| `NvidiaNIM_boltz2` | Complex prediction | `polymers`, `ligands` |

**Example - Dock drug candidates**:
```python
# Dock drug against target
result = tu.tools.NvidiaNIM_diffdock(
    protein=target_pdb_content,
    ligand=drug_smiles,
    num_poses=10
)
# Returns: {"poses": [{"confidence": 0.94, "coordinates": ...}, ...]}
```

---

## Phase 4.5: Pathway Analysis (NEW)

### KEGG Pathway Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `kegg_search_pathway` | Search pathways | `query` |
| `kegg_get_pathway_genes` | Get genes in pathway | `pathway_id` |
| `kegg_get_gene_info` | Get gene details | `gene_id` |
| `kegg_find_genes` | Find genes by keyword | `query`, `database` |

**Example - Pathogen metabolism pathways**:
```python
# Search for viral replication pathways
pathways = tu.tools.kegg_search_pathway(
    query="coronavirus replication"
)

# Get essential genes
genes = tu.tools.kegg_get_pathway_genes(
    pathway_id="ko03030"  # DNA replication
)
```

### Reactome Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `Reactome_search_pathway` | Search pathways | `query`, `species` |
| `Reactome_get_pathway_participants` | Get pathway entities | `pathway_id` |
| `Reactome_get_hierarchy` | Get pathway tree | `pathway_id` |

**Example - Host-pathogen interaction pathways**:
```python
# Host response to infection
pathways = tu.tools.Reactome_search_pathway(
    query="viral infection response",
    species="Homo sapiens"
)
```

---

## Phase 5: Literature Intelligence (ENHANCED)

### PubMed Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PubMed_search_articles` | Search articles | `query`, `limit` |
| `PubMed_get_article_details` | Get article | `pmid` |

**Example - Search outbreak literature**:
```python
papers = tu.tools.PubMed_search_articles(
    query="SARS-CoV-2 treatment drug",
    limit=50,
    sort="date"
)
```

### Preprint Servers (CRITICAL for Outbreaks)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `EuropePMC_search_articles` | Search preprints (bioRxiv, medRxiv) | `query`, `source='PPR'`, `pageSize` |
| `ArXiv_search_papers` | Physics/ML preprints | `query`, `category` |
| `BioRxiv_get_preprint` | Get preprint by DOI | `doi`, `server='biorxiv'` |
| `MedRxiv_get_preprint` | Get preprint by DOI | `doi`, `server='medrxiv'` |

**⚠️ Preprints are NOT peer-reviewed but critical for emerging outbreaks!**

**Example - Search preprints** (bioRxiv/medRxiv don't have search APIs, use EuropePMC):
```python
# Search for newest preprint findings
preprints = tu.tools.EuropePMC_search_articles(
    query=f"{pathogen_name} mechanism resistance",
    source="PPR",  # PPR = Preprints (bioRxiv, medRxiv, etc.)
    pageSize=20
)

# If you have a specific DOI, retrieve full metadata:
if doi_from_search.startswith('10.1101/'):
    full_preprint = tu.tools.BioRxiv_get_preprint(doi=doi_from_search)

# Alternative: Use web search for bioRxiv
web_results = tu.tools.web_search(
    query=f"{pathogen_name} clinical trial effectiveness",
    limit=20
)

# Computational papers
arxiv = tu.tools.ArXiv_search_papers(
    query=f"{pathogen_name} drug discovery",
    category="q-bio",
    limit=10
)
```

### Citation Analysis Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `openalex_search_works` | Search with citations | `query`, `limit` |
| `SemanticScholar_search` | AI-ranked search | `query`, `limit` |

**Example - Find high-impact papers**:
```python
# Get citation counts
papers = tu.tools.openalex_search_works(
    query="remdesivir COVID-19 trial",
    limit=20
)
# Returns: {"cited_by_count": 5234, ...}

# AI-ranked papers
ranked = tu.tools.SemanticScholar_search(
    query="SARS-CoV-2 drug resistance",
    limit=20
)
```

### Clinical Trials Tools

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `search_clinical_trials` | Search trials | `condition`, `intervention`, `status` |
| `get_clinical_trial_by_nct_id` | Get trial details | `nct_id` |

**Example - Find active trials**:
```python
trials = tu.tools.search_clinical_trials(
    condition="COVID-19",
    intervention="antiviral",
    status="Recruiting"
)
```

---

## Workflow Code Examples

### Example 1: Complete Outbreak Analysis

```python
def analyze_outbreak(tu, pathogen_name):
    """Complete outbreak intelligence workflow."""
    
    # Phase 1: Identify pathogen
    taxonomy = tu.tools.NCBI_Taxonomy_search(query=pathogen_name)
    taxid = taxonomy['taxid']
    
    # Phase 2: Get target proteins
    proteins = tu.tools.UniProt_search(
        query=f"organism:{taxid}",
        reviewed=True
    )
    
    # Phase 3: Predict structures for top targets
    structures = {}
    for protein in proteins[:3]:  # Top 3 targets
        seq = tu.tools.UniProt_get_protein_sequence(
            accession=protein['accession']
        )
        struct = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
        structures[protein['name']] = struct
    
    # Phase 4: Find repurposing candidates
    candidates = tu.tools.ChEMBL_search_drugs(
        query=f"{pathogen_name} OR broad spectrum antiviral",
        max_phase=4
    )
    
    # Dock top candidates
    docking_results = []
    for drug in candidates[:20]:
        result = tu.tools.NvidiaNIM_diffdock(
            protein=structures['main_protease']['structure'],
            ligand=drug['smiles'],
            num_poses=5
        )
        docking_results.append({
            'drug': drug,
            'score': result['poses'][0]['confidence']
        })
    
    # Phase 5: Literature search
    papers = tu.tools.PubMed_search_articles(
        query=f"{pathogen_name} treatment",
        limit=50
    )
    
    return {
        'taxonomy': taxonomy,
        'targets': proteins,
        'structures': structures,
        'drug_candidates': sorted(docking_results, 
                                  key=lambda x: x['score'], 
                                  reverse=True),
        'literature': papers
    }
```

### Example 2: Rapid Drug Screen

```python
def rapid_drug_screen(tu, target_sequence, drug_smiles_list):
    """Rapid docking screen for drug repurposing."""
    
    # Quick structure prediction
    structure = tu.tools.NvidiaNIM_esmfold(sequence=target_sequence)
    
    # Dock all candidates
    results = []
    for smiles in drug_smiles_list:
        docking = tu.tools.NvidiaNIM_diffdock(
            protein=structure['structure'],
            ligand=smiles,
            num_poses=3
        )
        results.append({
            'smiles': smiles,
            'score': docking['poses'][0]['confidence']
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)
```

### Example 3: Knowledge Transfer from Related Pathogen

```python
def transfer_knowledge(tu, novel_pathogen, reference_pathogen):
    """Transfer drug knowledge from related pathogen."""
    
    # Get drugs approved for reference pathogen
    ref_drugs = tu.tools.ChEMBL_search_drugs(
        query=reference_pathogen,
        max_phase=4
    )
    
    # Get target from novel pathogen
    novel_proteins = tu.tools.UniProt_search(
        query=f"organism:{novel_pathogen}"
    )
    
    # Find homologous targets
    homologs = []
    for protein in novel_proteins:
        # BLAST against reference
        blast = tu.tools.BLAST_protein_search(
            sequence=protein['sequence'],
            database="refseq_protein",
            organism=reference_pathogen
        )
        if blast and blast[0]['identity'] > 70:
            homologs.append({
                'novel_target': protein,
                'reference_homolog': blast[0],
                'identity': blast[0]['identity']
            })
    
    # Match drugs to homologous targets
    candidates = []
    for drug in ref_drugs:
        for homolog in homologs:
            if drug['target'] == homolog['reference_homolog']['accession']:
                candidates.append({
                    'drug': drug,
                    'target_homology': homolog['identity'],
                    'expected_activity': 'High' if homolog['identity'] > 90 else 'Medium'
                })
    
    return candidates
```

---

## Fallback Chains

### Taxonomy
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NCBI_Taxonomy_search` | `UniProt_taxonomy` | Manual NCBI query |

### Structure Prediction
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_alphafold2` | `NvidiaNIM_esmfold` | `alphafold_get_prediction` |
| `alphafold_get_prediction` | `NvidiaNIM_openfold2` | PDB homolog |

### Docking
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_diffdock` | `NvidiaNIM_boltz2` | Literature docking |

### Drug Search
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `ChEMBL_search_drugs` | `drugbank_vocab_search` | PubChem BioAssay |

### Pathway Analysis (NEW)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `kegg_search_pathway` | `Reactome_search_pathway` | `WikiPathways_search` |
| `kegg_get_pathway_genes` | `Reactome_get_pathway_participants` | Gene list extraction |

### Literature (ENHANCED)
| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `PubMed_search_articles` | `openalex_search_works` | Google Scholar |
| `EuropePMC_search_articles` (source='PPR') | `web_search` (site:biorxiv.org) | ArXiv q-bio |
| `openalex_search_works` | `SemanticScholar_search` | Manual citation |

---

## Common Parameter Mistakes

| Tool | Wrong | Correct |
|------|-------|---------|
| `NCBI_Taxonomy_search` | `name="virus"` | `query="virus"` |
| `UniProt_search` | `name="protease"` | `query="protease"` |
| `ChEMBL_search_targets` | `target="Mpro"` | `query="Mpro"` |
| `NvidiaNIM_diffdock` | `protein_file=path` | `protein=content` |
| `NvidiaNIM_alphafold2` | `seq="MVLS..."` | `sequence="MVLS..."` |

---

## NVIDIA NIM Requirements

**API Key**: `NVIDIA_API_KEY` environment variable required

**Rate limits**: 40 RPM (1.5 second minimum between calls)

**Async operations**: 
- AlphaFold2 may return 202, requiring polling
- ESMFold is synchronous (faster for rapid screening)

### Check Availability
```python
import os

nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))
if not nvidia_available:
    print("Warning: NVIDIA NIM tools unavailable, using fallbacks")
```

---

## Speed Optimization

### For Urgent Outbreaks

1. **Use ESMFold first** for rapid structure (30 sec vs 5-15 min)
2. **Dock FDA-approved only** initially (fastest to deploy)
3. **Parallelize docking** if possible
4. **Cache structures** for repeated queries

### Prioritization Order

```python
def prioritize_candidates(candidates):
    """Prioritize by speed to clinical use."""
    return sorted(candidates, key=lambda x: (
        -x['fda_approved'],      # FDA approved first
        -x['phase'],             # Higher phase next
        -x['docking_score']      # Then by score
    ))
```
