# Binder Discovery Workflow Details

Detailed procedures, code patterns, and screening protocols for each phase.

## Phase 0: Tool Verification

**CRITICAL**: Verify tool parameters before calling unfamiliar tools.

```python
# Check tool params to prevent silent failures
tool_info = tu.tools.get_tool_info(tool_name="ChEMBL_get_target_activities")
```

### Known Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_get_target_tractability_by_ensemblID` | `ensembl_id` | `ensemblId` |
| `ChEMBL_get_target_activities` | `chembl_target_id` | `target_chembl_id` |
| `ChEMBL_search_similar_molecules` | `smiles` | `molecule` (accepts SMILES, ChEMBL ID, or name) |
| `alphafold_get_prediction` | `uniprot` | `accession` |
| `ADMETAI_*` | `smiles="..."` | `smiles=["..."]` (must be list) |
| `NvidiaNIM_alphafold2` | `seq` | `sequence` |
| `NvidiaNIM_genmol` | `smiles="C..."` | `smiles="C...[*{1-3}]..."` (must have mask regions) |
| `NvidiaNIM_boltz2` | `sequence="..."` | `polymers=[{"molecule_type": "protein", "sequence": "..."}]` |

---

## Phase 1: Target Validation Details

### 1.1 Identifier Resolution Chain

```
1. UniProt_search(query=target_name, organism="human")
   -> Extract: UniProt accession, gene name, protein name

2. MyGene_query_genes(q=gene_symbol, species="human")
   -> Extract: Ensembl gene ID, NCBI gene ID

3. ChEMBL_search_targets(query=target_name, organism="Homo sapiens")
   -> Extract: ChEMBL target ID, target type

4. GtoPdb_get_targets(query=target_name)
   -> Extract: GtoPdb target ID (if GPCR/ion channel/enzyme)
```

**Store all IDs for downstream queries**:
```
ids = {
    'uniprot': 'P00533',
    'ensembl': 'ENSG00000146648',
    'chembl_target': 'CHEMBL203',
    'gene_symbol': 'EGFR',
    'gtopdb': '1797'  # if available
}
```

### 1.2 Druggability Assessment

**Multi-Source Triangulation**:

```
1. OpenTargets_get_target_tractability_by_ensemblID(ensemblId)
   -> Extract: Small molecule tractability score, bucket

2. DGIdb_get_gene_druggability(genes=[gene_symbol])
   -> Extract: Druggability categories, known drug count

3. OpenTargets_get_target_classes_by_ensemblID(ensemblId)
   -> Extract: Target class (kinase, GPCR, etc.)

4. GPCRdb_get_protein(protein=entry_name)  # for GPCRs
   -> Extract: GPCR family, receptor state, ligand binding data
```

### 1.2a GPCRdb Integration (for GPCR Targets)

~35% of all approved drugs target GPCRs. For GPCR targets, use specialized data:

```python
def check_if_gpcr_and_enrich(tu, target_name, uniprot_id):
    """Check if target is GPCR and get specialized data."""

    entry_name = f"{target_name.lower()}_human"

    gpcr_info = tu.tools.GPCRdb_get_protein(
        operation="get_protein",
        protein=entry_name
    )

    if gpcr_info.get('status') == 'success':
        structures = tu.tools.GPCRdb_get_structures(
            operation="get_structures",
            protein=entry_name
        )
        ligands = tu.tools.GPCRdb_get_ligands(
            operation="get_ligands",
            protein=entry_name
        )
        mutations = tu.tools.GPCRdb_get_mutations(
            operation="get_mutations",
            protein=entry_name
        )

        return {
            'is_gpcr': True,
            'gpcr_family': gpcr_info['data'].get('family'),
            'gpcr_class': gpcr_info['data'].get('receptor_class'),
            'structures': structures['data'].get('structures', []),
            'ligands': ligands['data'].get('ligands', []),
            'mutation_data': mutations['data'].get('mutations', [])
        }

    return {'is_gpcr': False}
```

### 1.2.5 Therapeutic Antibody Landscape

Check Thera-SAbDab for therapeutic antibodies against target:

```python
def check_therapeutic_antibodies(tu, target_name):
    results = tu.tools.TheraSAbDab_search_by_target(target=target_name)

    if results.get('status') == 'success':
        antibodies = results['data'].get('therapeutics', [])
        by_phase = {'Approved': [], 'Phase 3': [], 'Phase 2': [], 'Phase 1': [], 'Preclinical': []}
        for ab in antibodies:
            phase = ab.get('phase', 'Unknown')
            for key in by_phase.keys():
                if key.lower() in phase.lower():
                    by_phase[key].append(ab)
                    break

        return {
            'total_antibodies': len(antibodies),
            'by_phase': by_phase,
            'antibodies': antibodies[:10],
            'competitive_alert': len(by_phase.get('Approved', [])) > 0
        }
    return None
```

### 1.3 Binding Site Analysis

```
1. ChEMBL_search_binding_sites(target_chembl_id)
   -> Extract: Binding site names, types

2. get_binding_affinity_by_pdb_id(pdb_id)  # For each PDB with ligand
   -> Extract: Kd, Ki, IC50 values for co-crystallized ligands

3. InterPro_get_protein_domains(uniprot_accession)
   -> Extract: Domain architecture, active sites
```

### 1.4 Structure Prediction (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

**Option A: AlphaFold2 (High accuracy, async)**
```
NvidiaNIM_alphafold2(
    sequence=kinase_domain_sequence,
    algorithm="mmseqs2",
    relax_prediction=False
)
-> Returns: PDB structure with pLDDT confidence scores
-> Use when: Accuracy is critical, time is available (~5-15 min)
```

**Option B: ESMFold (Fast, synchronous)**
```
NvidiaNIM_esmfold(sequence=kinase_domain_sequence)
-> Returns: PDB structure (max 1024 AA)
-> Use when: Quick assessment needed (~30 sec)
```

---

## Phase 2: Known Ligand Mining Details

### 2.1 ChEMBL Bioactivity Data

```
1. ChEMBL_get_target_activities(target_chembl_id, limit=500)
   -> Filter: standard_type in ["IC50", "Ki", "Kd", "EC50"]
   -> Filter: standard_value < 10000 nM
   -> Extract: ChEMBL molecule IDs, SMILES, potency values

2. ChEMBL_get_molecule(molecule_chembl_id)  # For top actives
   -> Extract: Full molecular data, max_phase, oral flag
```

### 2.5 BindingDB Affinity Data

```python
def get_bindingdb_ligands(tu, uniprot_id, affinity_cutoff=10000):
    """Get ligands from BindingDB with measured affinities."""

    result = tu.tools.BindingDB_get_ligands_by_uniprot(
        uniprot=uniprot_id,
        affinity_cutoff=affinity_cutoff
    )

    if result:
        ligands = []
        for entry in result:
            ligands.append({
                'smiles': entry.get('smile'),
                'affinity_type': entry.get('affinity_type'),
                'affinity_nM': entry.get('affinity'),
                'pmid': entry.get('pmid'),
                'monomer_id': entry.get('monomerid')
            })
        ligands.sort(key=lambda x: float(x['affinity_nM']) if x['affinity_nM'] else 1e6)
        return ligands[:50]
    return []

def find_compound_polypharmacology(tu, smiles, similarity_cutoff=0.85):
    """Find off-target interactions for selectivity analysis."""
    return tu.tools.BindingDB_get_targets_by_compound(
        smiles=smiles,
        similarity_cutoff=similarity_cutoff
    )
```

### 2.6 PubChem BioAssay Screening Data

```python
def get_pubchem_assays_for_target(tu, gene_symbol):
    """Get bioassays and active compounds from PubChem."""

    assays = tu.tools.PubChem_search_assays_by_target_gene(
        gene_symbol=gene_symbol
    )

    results = {'assays': [], 'total_active_compounds': 0}

    if assays.get('data', {}).get('aids'):
        for aid in assays['data']['aids'][:10]:
            summary = tu.tools.PubChem_get_assay_summary(aid=aid)
            actives = tu.tools.PubChem_get_assay_active_compounds(aid=aid)
            active_cids = actives.get('data', {}).get('cids', [])

            results['assays'].append({
                'aid': aid,
                'summary': summary.get('data', {}),
                'active_count': len(active_cids)
            })
            results['total_active_compounds'] += len(active_cids)
    return results
```

**When to Use Each Source**:
| Source | Strengths | Primary Use |
|--------|-----------|-------------|
| **ChEMBL** | Curated, standardized, SAR data | Primary ligand source |
| **BindingDB** | Direct affinity measurements | Ki/Kd values, PMIDs |
| **PubChem BioAssay** | HTS data, NIH screens | Novel scaffolds, broad coverage |

---

## Phase 3: Structure Analysis Details

### 3.1 PDB Structure Retrieval

```
1. PDB_search_similar_structures(query=uniprot_accession, type="sequence")
   -> Extract: PDB IDs with ligands

2. get_protein_metadata_by_pdb_id(pdb_id)
   -> Extract: Resolution, method, ligand codes

3. alphafold_get_prediction(accession=uniprot_accession)
   -> Extract: Predicted structure (if no experimental)
```

### 3.1b EMDB Cryo-EM Structures

**Prioritize for**: Membrane proteins (GPCRs, ion channels), large complexes.

```python
def get_cryoem_structures(tu, target_name, uniprot_accession):
    """Get cryo-EM structures for membrane targets."""
    emdb_results = tu.tools.emdb_search(
        query=f"{target_name} membrane receptor"
    )

    structures = []
    for entry in emdb_results[:5]:
        details = tu.tools.emdb_get_entry(entry_id=entry['emdb_id'])
        pdb_models = details.get('pdb_ids', [])
        structures.append({
            'emdb_id': entry['emdb_id'],
            'resolution': entry.get('resolution', 'N/A'),
            'title': entry.get('title', 'N/A'),
            'conformational_state': details.get('state', 'Unknown'),
            'pdb_models': pdb_models
        })
    return structures
```

**When to use cryo-EM over X-ray**:
| Target Type | Prefer cryo-EM? | Reason |
|-------------|-----------------|--------|
| GPCR | Yes | Native membrane conformation |
| Ion channel | Yes | Multiple functional states |
| Receptor-ligand complex | Yes | Physiological state |
| Kinase | Usually X-ray | Higher resolution typically |

---

## Phase 3.5: Docking Validation (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

### Reference Compound Docking

**Option A: DiffDock (Blind docking, PDB + SDF input)**
```
NvidiaNIM_diffdock(
    protein=pdb_content,
    ligand=reference_sdf,
    num_poses=10
)
-> Returns: Docking poses with confidence scores
-> Use: When you have PDB structure and ligand SDF file
```

**Option B: Boltz2 (From sequence + SMILES)**
```
NvidiaNIM_boltz2(
    polymers=[{"molecule_type": "protein", "sequence": kinase_sequence}],
    ligands=[{"smiles": "COc1cc2ncnc(Nc3ccc(C#C)cc3)c2cc1OCCOC"}],
    sampling_steps=50,
    diffusion_samples=1
)
-> Returns: Protein-ligand complex structure
-> Use: When starting from SMILES, no SDF needed
```

### Docking Score Interpretation

| Score vs Reference | Priority | Symbol |
|--------------------|----------|--------|
| Higher than reference | Top priority | (T0) |
| Within 5% of reference | High priority | (T2) |
| Within 20% of reference | Moderate priority | (T3) |
| >20% lower | Low priority | (T4) |

---

## Phase 4: Compound Expansion Details

### 4.1 Similarity Search

```
1. ChEMBL_search_similar_molecules(molecule=top_active_smiles, similarity=70)
   -> Extract: Similar compounds not yet tested on target

2. PubChem_search_compounds_by_similarity(smiles, threshold=0.7)
   -> Extract: PubChem CIDs with similar structures
```

**Strategy**:
- Use 3-5 diverse actives as seeds
- Similarity threshold: 70-85% (balance novelty vs. activity)
- Prioritize compounds NOT in ChEMBL bioactivity for target

### 4.2 Substructure Search

```
1. ChEMBL_search_substructure(smiles=core_scaffold)
2. PubChem_search_compounds_by_substructure(smiles=core_scaffold)
```

### 4.3 Cross-Database Mining

```
1. STITCH_get_chemical_protein_interactions(identifier=target_gene)
2. DGIdb_get_drug_gene_interactions(genes=[gene_symbol])
```

### 4.4 De Novo Molecule Generation (NVIDIA NIM)

**Option A: GenMol (Scaffold Hopping with Masked Regions)**
```
NvidiaNIM_genmol(
    smiles="COc1cc2ncnc(Nc3ccc([*{3-8}])c([*{1-3}])c3)c2cc1OCCCN1CCOCC1",
    num_molecules=100,
    temperature=2.0,
    scoring="QED"
)
```

**Mask Design Strategy**:
| Position | Mask | Purpose |
|----------|------|---------|
| Small substituent | `[*{1-3}]` | Halogen, methyl, hydroxyl |
| Medium group | `[*{3-6}]` | Linkers, small rings |
| Solubilizing tail | `[*{5-12}]` | Morpholine, piperazine |
| Core modification | `[*{6-10}]` | Ring replacements |

**Temperature Selection**:
| Temperature | Effect | When to Use |
|-------------|--------|-------------|
| 0.5-1.0 | Conservative, close analogs | Early optimization |
| 1.5-2.0 | Balanced diversity | General exploration |
| 2.5-3.0 | High diversity, more novelty | Scaffold hopping |

**Option B: MolMIM (Controlled Generation from Reference)**
```
NvidiaNIM_molmim(
    smi="COc1cc2ncnc(Nc3ccc(Cl)cc3)c2cc1OCCN1CCOCC1",
    num_molecules=50,
    algorithm="CMA-ES"
)
```

**Generation Workflow**:
1. Identify top 3-5 actives from Phase 2
2. Design masked SMILES for GenMol OR use as reference for MolMIM
3. Generate 50-100 molecules per seed
4. Pass generated molecules to Phase 5 (ADMET filtering)
5. Dock survivors in Phase 6 for final ranking

---

## Phase 5: ADMET Filtering Details

### 5.1 Physicochemical Properties

```
ADMETAI_predict_physicochemical_properties(smiles=[compound_list])
-> Filter: Lipinski violations <= 1
-> Filter: QED > 0.3
-> Filter: MW 200-600
```

### 5.2 ADMET Endpoints

```
1. ADMETAI_predict_bioavailability(smiles=[compound_list])
   -> Filter: Oral bioavailability > 0.3

2. ADMETAI_predict_toxicity(smiles=[compound_list])
   -> Filter: AMES < 0.5, hERG < 0.5, DILI < 0.5

3. ADMETAI_predict_CYP_interactions(smiles=[compound_list])
   -> Flag: CYP3A4 inhibitors (drug interaction risk)
```

### 5.3 Structural Alerts

```
ChEMBL_search_compound_structural_alerts(smiles=compound_smiles)
-> Flag: PAINS, reactive groups, toxicophores
```

---

## Phase 6: Candidate Docking & Prioritization Details

### Batch Docking Workflow

```python
candidates = admet_passed_compounds

# Get reference score first
reference_result = tu.tools.NvidiaNIM_diffdock(
    protein=pdb_content,
    ligand=reference_ligand_sdf,
    num_poses=10
)
reference_confidence = reference_result['best_pose_confidence']

# Dock all candidates
docking_results = []
for compound in candidates:
    result = tu.tools.NvidiaNIM_diffdock(
        protein=pdb_content,
        ligand=compound['sdf'],
        num_poses=5
    )
    docking_results.append({
        'id': compound['id'],
        'confidence': result['best_pose_confidence'],
        'vs_reference': (result['best_pose_confidence'] / reference_confidence - 1) * 100
    })

ranked = sorted(docking_results, key=lambda x: x['confidence'], reverse=True)
```

### Scoring Framework

| Dimension | Weight | Scoring Criteria |
|-----------|--------|------------------|
| **Docking confidence** (if available) | 40% | NvidiaNIM_diffdock score |
| **Structural Similarity** | 25% (or 25% without docking) | Tanimoto to actives (0.7-1.0 -> 1-5) |
| **ADMET Score** | 25% (or 30%) | Composite of property predictions |
| **Novelty** | 20% (or 15%) | Not in ChEMBL = +2; Novel scaffold = +3 |
| **Synthesis Feasibility** | 15% | SA score (1-10), commercial availability |
| **Scaffold Diversity** | 15% | Cluster representative bonus |

### Synthesis Feasibility

**SA Score Interpretation**:
- 1-3: Easy synthesis
- 3-5: Moderate complexity
- 5-10: Challenging synthesis

---

## Phase 6.5: Literature Evidence

### Literature Search for Validation

```python
def search_binder_literature(tu, target_name, compound_scaffolds):
    """Search literature for compound and target evidence."""

    # PubMed: Published SAR studies
    sar_papers = tu.tools.PubMed_search_articles(
        query=f"{target_name} inhibitor SAR structure-activity",
        limit=30
    )

    # EuropePMC: Preprints (bioRxiv/medRxiv)
    preprints = tu.tools.EuropePMC_search_articles(
        query=f"{target_name} small molecule discovery",
        source="PPR",
        pageSize=15
    )

    # Citation analysis
    key_papers = sar_papers[:10]
    for paper in key_papers:
        citation = tu.tools.openalex_search_works(
            query=paper['title'],
            limit=1
        )
        paper['citations'] = citation[0].get('cited_by_count', 0) if citation else 0

    return {
        'published_sar': sar_papers,
        'preprints': preprints,
        'high_impact_papers': sorted(key_papers, key=lambda x: x.get('citations', 0), reverse=True)
    }
```

---

## Fallback Chains

### Target ID Resolution
```
Primary: ChEMBL_search_targets
-> Fail -> GtoPdb_get_targets (for GPCR/ion channel/enzyme)
         -> Fail -> Document "Target not in databases"
```

### Druggability Assessment
```
Primary: OpenTargets_get_target_tractability_by_ensemblID
-> Fail -> DGIdb_get_gene_druggability
         -> Fail -> Use target class as proxy
```

### Bioactivity Data
```
Primary: ChEMBL_get_target_activities
-> Fail -> BindingDB_get_ligands_by_uniprot
         -> Fail -> GtoPdb_get_target_interactions
                  -> Fail -> PubChem_search_assays_by_target_gene
                           -> Fail -> Document "No bioactivity data"
```

### Similarity Search
```
Primary: ChEMBL_search_similar_molecules
-> Fail -> PubChem_search_compounds_by_similarity
         -> Fail -> Document "Similarity search failed"
```

### Structure Retrieval
```
Primary: get_protein_metadata_by_pdb_id
-> Fail (no PDB) -> emdb_search (for membrane proteins)
         -> Fail -> NvidiaNIM_alphafold2
                 -> Fail -> NvidiaNIM_esmfold
                         -> Fail -> alphafold_get_prediction
                                 -> Fail -> Document "No structural information"
```

### Docking
```
Primary: NvidiaNIM_diffdock (have PDB + SDF)
-> Fail -> NvidiaNIM_boltz2 (from sequence + SMILES)
         -> Fail -> Skip docking, use similarity-based scoring
```

### De Novo Generation
```
Primary: NvidiaNIM_genmol (specific position variation)
-> Fail -> NvidiaNIM_molmim (general analog generation)
         -> Fail -> Use similarity search only (no generation)
```

### Literature Search
```
Primary: PubMed_search_articles (peer-reviewed)
-> Supplement: EuropePMC_search_articles (source='PPR' for preprints)
-> Supplement: openalex_search_works (citation analysis)
```

---

## Batch Processing Pattern

```python
# Define calls
calls = [
    {"name": "ChEMBL_get_molecule", "arguments": {"molecule_chembl_id": id}}
    for id in chembl_ids[:50]
]

# Execute in parallel
results = tu.run_batch(calls)

# Process results
for result in results:
    if result and 'molecule_structures' in result:
        process_molecule(result)
```

---

## Rate Limiting Awareness

| Database | Rate Limit | Recommendation |
|----------|------------|----------------|
| ChEMBL | ~10 req/sec | Batch queries when possible |
| PubChem | ~5 req/sec | Use batch endpoints |
| ADMET-AI | No strict limit | Batch SMILES in lists |
| OpenTargets | GraphQL, lenient | Single complex queries preferred |
| UniProt | ~10 req/sec | Batch search preferred |
| NVIDIA NIM | API key quota | Check quota, cache results |

### NVIDIA NIM Runtimes

| Tool | Typical Runtime | Notes |
|------|-----------------|-------|
| `NvidiaNIM_alphafold2` | 5-15 min | Async, check status |
| `NvidiaNIM_esmfold` | ~30 sec | Fast, max 1024 AA |
| `NvidiaNIM_diffdock` | ~1-2 min | Per ligand |
| `NvidiaNIM_boltz2` | ~2-5 min | Includes structure prediction |
| `NvidiaNIM_genmol` | ~1-3 min | Depends on num_molecules |
| `NvidiaNIM_molmim` | ~1-2 min | Fast analog generation |

**API Key Check**:
```python
import os
if not os.environ.get("NVIDIA_API_KEY"):
    print("Warning: NVIDIA_API_KEY not set. NvidiaNIM tools unavailable.")
```
