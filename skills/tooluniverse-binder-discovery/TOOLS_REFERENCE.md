# Tools Reference for Small Molecule Binder Discovery

Complete tool reference with verified parameters and fallback chains.

## Phase 1: Target Validation Tools

### UniProt_search
**Purpose**: Resolve protein name to UniProt accession
```python
result = tu.tools.UniProt_search(
    query="EGFR human",
    organism="human",
    limit=10
)
# Returns: list of UniProt entries with accession, protein name, gene name
```

### MyGene_query_genes
**Purpose**: Get Ensembl and NCBI gene IDs
```python
result = tu.tools.MyGene_query_genes(
    q="EGFR",
    species="human",
    fields="ensembl.gene,symbol,name"
)
# Returns: gene info with ensembl.gene, symbol, name
```

### ChEMBL_search_targets
**Purpose**: Get ChEMBL target ID
```python
result = tu.tools.ChEMBL_search_targets(
    query="EGFR",
    organism="Homo sapiens",
    limit=10
)
# Returns: targets with target_chembl_id, pref_name, target_type
```

### OpenTargets_get_target_tractability_by_ensemblID
**Purpose**: Assess small molecule tractability
```python
result = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
    ensemblId="ENSG00000146648"  # Note: camelCase
)
# Returns: tractability assessments by modality (small molecule, antibody, etc.)
```
**⚠️ Parameter**: Use `ensemblId` (camelCase), NOT `ensembl_id`

### DGIdb_get_gene_druggability
**Purpose**: Get druggability categories
```python
result = tu.tools.DGIdb_get_gene_druggability(
    genes=["EGFR"]  # List of gene symbols
)
# Returns: druggability info, drug count, categories
```

### ChEMBL_search_binding_sites
**Purpose**: Find known binding sites
```python
result = tu.tools.ChEMBL_search_binding_sites(
    target_chembl_id="CHEMBL203"
)
# Returns: binding site names, types
```

### InterPro_get_protein_domains
**Purpose**: Get domain architecture
```python
result = tu.tools.InterPro_get_protein_domains(
    accession="P00533"  # UniProt accession
)
# Returns: domains, families, sites with positions
```

---

## Thera-SAbDab Tools (NEW - Therapeutic Antibody Landscape)

Check therapeutic antibody competition for your target.

### TheraSAbDab_search_by_target
**Purpose**: Find antibodies targeting specific antigen
```python
result = tu.tools.TheraSAbDab_search_by_target(
    target="PD-1"  # Target antigen name
)
# Returns: list of therapeutic antibodies, phase, format, PDB IDs
```

### TheraSAbDab_search_therapeutics
**Purpose**: Search antibodies by name or keyword
```python
result = tu.tools.TheraSAbDab_search_therapeutics(
    query="pembrolizumab"  # Antibody name or target
)
# Returns: matching therapeutics with target, phase, format
```

### TheraSAbDab_get_all_therapeutics
**Purpose**: Get summary of all therapeutic antibodies
```python
result = tu.tools.TheraSAbDab_get_all_therapeutics()
# Returns: total count, distribution by phase, distribution by format
```

**Why Use Thera-SAbDab**:
- **Competitive intelligence**: See what antibodies already target your protein
- **Target validation**: Approved antibodies = validated target
- **Structural data**: Links to PDB structures of antibody-target complexes
- **Strategic differentiation**: Identify where small molecules offer advantages

**Example Competitive Analysis**:
```python
def assess_antibody_competition(tu, target_name):
    """Assess therapeutic antibody competitive landscape."""
    
    # Search by target
    results = tu.tools.TheraSAbDab_search_by_target(target=target_name)
    
    if results.get('status') == 'success':
        antibodies = results['data'].get('therapeutics', [])
        
        # Count by phase
        phases = {}
        for ab in antibodies:
            phase = ab.get('phase', 'Unknown')
            phases[phase] = phases.get(phase, 0) + 1
        
        return {
            'total': len(antibodies),
            'by_phase': phases,
            'has_approved': 'Approved' in phases,
            'top_antibodies': antibodies[:5]
        }
    return None
```

---

## GPCRdb Tools (for GPCR Targets)

~35% of approved drugs target GPCRs. Use GPCRdb for specialized GPCR data.

### GPCRdb_get_protein
**Purpose**: Get GPCR protein information
```python
result = tu.tools.GPCRdb_get_protein(
    operation="get_protein",
    protein="adrb2_human"  # Entry name format: {gene}_human
)
# Returns: GPCR family, class, species, sequence info
```

### GPCRdb_list_proteins  
**Purpose**: List GPCR families or proteins in a family
```python
# List all GPCR families
families = tu.tools.GPCRdb_list_proteins(
    operation="list_proteins"
)

# List proteins in specific family
proteins = tu.tools.GPCRdb_list_proteins(
    operation="list_proteins",
    family="001"  # Class A
)
```

### GPCRdb_get_structures
**Purpose**: Get GPCR structures with receptor state (active/inactive)
```python
result = tu.tools.GPCRdb_get_structures(
    operation="get_structures",
    protein="adrb2_human",
    state="active"  # Optional: "active", "inactive", "intermediate"
)
# Returns: PDB IDs with receptor state, resolution, ligand info
```

### GPCRdb_get_ligands
**Purpose**: Get known GPCR ligands
```python
result = tu.tools.GPCRdb_get_ligands(
    operation="get_ligands",
    protein="adrb2_human"
)
# Returns: Ligands with binding affinity, type (agonist/antagonist)
```

### GPCRdb_get_mutations
**Purpose**: Get experimental mutation data for GPCR
```python
result = tu.tools.GPCRdb_get_mutations(
    operation="get_mutations",
    protein="adrb2_human"
)
# Returns: Mutations with effect on ligand binding/signaling
```

**Why GPCRdb is Essential for GPCR Binder Discovery**:
- **Receptor state structures**: Active vs. inactive conformations
- **Ballesteros-Weinstein numbering**: Standard residue numbering across GPCRs
- **Curated ligand data**: Agonists, antagonists, allosteric modulators
- **Mutation effects**: Direct effects on ligand binding

---

## Phase 1.4: Structure Prediction (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

### NvidiaNIM_alphafold2
**Purpose**: High-accuracy structure prediction with pLDDT confidence scores
```python
result = tu.tools.NvidiaNIM_alphafold2(
    sequence="MRPSGTAGAALLALL...",  # Protein sequence
    algorithm="mmseqs2",             # MSA algorithm: "mmseqs2" or "jackhmmer"
    relax_prediction=False           # Optional: Run relaxation
)
# Returns: PDB structure string with pLDDT scores per residue
# pLDDT interpretation:
#   ≥90: Very high confidence
#   70-90: Confident
#   50-70: Low confidence
#   <50: Very low confidence
```
**⚠️ Note**: Async operation, may take 5-15 minutes. Max sequence length ~2000 AA.

### NvidiaNIM_esmfold
**Purpose**: Fast structure prediction (synchronous)
```python
result = tu.tools.NvidiaNIM_esmfold(
    sequence="MRPSGTAGAALLALL..."  # Protein sequence (max 1024 AA)
)
# Returns: PDB structure string
```
**⚠️ Note**: Fast (~30 sec) but limited to 1024 residues. No MSA, slightly lower accuracy.

### NvidiaNIM_msa_search
**Purpose**: Generate multiple sequence alignment for structure prediction
```python
result = tu.tools.NvidiaNIM_msa_search(
    sequence="MRPSGTAGAALLALL...",
    database="uniref90"  # "uniref90", "bfd", etc.
)
# Returns: MSA in A3M format
```
**Use**: Pre-generate MSA for repeated AlphaFold2 predictions.

---

## Phase 2: Known Ligand Mining Tools

### ChEMBL_get_target_activities
**Purpose**: Get all bioactivity data for target
```python
result = tu.tools.ChEMBL_get_target_activities(
    target_chembl_id="CHEMBL203",
    limit=500
)
# Returns: activities with molecule_chembl_id, standard_type, standard_value
```
**⚠️ Parameter**: Use `target_chembl_id`, NOT `chembl_target_id`

### ChEMBL_get_molecule
**Purpose**: Get detailed molecule information
```python
result = tu.tools.ChEMBL_get_molecule(
    molecule_chembl_id="CHEMBL553"
)
# Returns: molecule data including SMILES, max_phase, properties
```

### GtoPdb_get_target_interactions
**Purpose**: Get pharmacological interactions
```python
result = tu.tools.GtoPdb_get_target_interactions(
    target_id="1797"  # GtoPdb target ID
)
# Returns: ligands with pKi, pIC50, action type
```

### OpenTargets_get_chemical_probes_by_target_ensemblID
**Purpose**: Find validated chemical probes
```python
result = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblID(
    ensemblId="ENSG00000146648"
)
# Returns: probes with ratings, use recommendations
```

### OpenTargets_get_associated_drugs_by_target_ensemblID
**Purpose**: Get approved/clinical drugs
```python
result = tu.tools.OpenTargets_get_associated_drugs_by_target_ensemblID(
    ensemblId="ENSG00000146648"
)
# Returns: drugs with phase, mechanism of action
```

### BindingDB_get_ligands_by_uniprot (NEW)
**Purpose**: Get ligands with measured binding affinities
```python
result = tu.tools.BindingDB_get_ligands_by_uniprot(
    uniprot="P00533",  # UniProt accession
    affinity_cutoff=10000  # Max affinity in nM
)
# Returns: SMILES, affinity_type (Ki/IC50/Kd), affinity value, PMID
```
**Advantages**: Direct affinity measurements, literature links, compounds not in ChEMBL

### BindingDB_get_ligands_by_pdb (NEW)
**Purpose**: Get ligands for a PDB structure
```python
result = tu.tools.BindingDB_get_ligands_by_pdb(
    pdb_ids="1M17",  # PDB ID
    affinity_cutoff=10000,
    sequence_identity=100
)
# Returns: ligands binding to the structure's protein
```

### BindingDB_get_targets_by_compound (NEW)
**Purpose**: Find off-targets for selectivity analysis
```python
result = tu.tools.BindingDB_get_targets_by_compound(
    smiles="CC(=O)Nc1ccc(cc1)O",  # Compound SMILES
    similarity_cutoff=0.85
)
# Returns: other proteins binding similar compounds
```

### PubChem_search_assays_by_target_gene (NEW)
**Purpose**: Find HTS screening data for target
```python
result = tu.tools.PubChem_search_assays_by_target_gene(
    gene_symbol="EGFR"
)
# Returns: list of AIDs (assay IDs) for this target
```

### PubChem_get_assay_summary (NEW)
**Purpose**: Get assay statistics
```python
result = tu.tools.PubChem_get_assay_summary(aid=504526)
# Returns: active/inactive counts, target info, assay metadata
```

### PubChem_get_assay_active_compounds (NEW)
**Purpose**: Get hits from HTS screen
```python
result = tu.tools.PubChem_get_assay_active_compounds(aid=504526)
# Returns: CIDs of active compounds
```

### PubChem_get_assay_dose_response (NEW)
**Purpose**: Get IC50/EC50 curves
```python
result = tu.tools.PubChem_get_assay_dose_response(aid=1053104)
# Returns: concentration-response data
```

### PubChem_get_compound_bioactivity (NEW)
**Purpose**: Get all bioactivity for a compound
```python
result = tu.tools.PubChem_get_compound_bioactivity(cid=2244)
# Returns: all assays, targets, activity outcomes
```

**When to Use Each Source**:
| Source | Strengths | Primary Use |
|--------|-----------|-------------|
| ChEMBL | Curated, SAR-ready | Main ligand source |
| GtoPdb | Pharmacology focus | GPCRs, channels |
| BindingDB | Direct Ki/Kd values | Affinity data |
| PubChem BioAssay | HTS screens | Novel scaffolds |

---

## Phase 3: Structure Analysis Tools

### PDB_search_similar_structures
**Purpose**: Find PDB structures by sequence
```python
result = tu.tools.PDB_search_similar_structures(
    query="P00533",  # UniProt or PDB ID
    type="sequence"  # or "structure"
)
# Returns: PDB IDs with similarity scores
```

### get_protein_metadata_by_pdb_id
**Purpose**: Get structure metadata
```python
result = tu.tools.get_protein_metadata_by_pdb_id(
    pdb_id="1M17"
)
# Returns: resolution, method, deposition date, title
```

### get_binding_affinity_by_pdb_id
**Purpose**: Get co-crystallized ligand affinities
```python
result = tu.tools.get_binding_affinity_by_pdb_id(
    pdb_id="1M17"
)
# Returns: ligand codes with Kd, Ki, IC50 values
```

### alphafold_get_prediction
**Purpose**: Get AlphaFold predicted structure
```python
result = tu.tools.alphafold_get_prediction(
    accession="P00533"  # UniProt accession
)
# Returns: structure prediction with pLDDT scores
```
**⚠️ Parameter**: Use `accession`, NOT `uniprot`

### get_ligand_smiles_by_chem_comp_id
**Purpose**: Get ligand structure from PDB
```python
result = tu.tools.get_ligand_smiles_by_chem_comp_id(
    chem_comp_id="AQ4"  # 3-letter ligand code from PDB
)
# Returns: SMILES, name, formula
```

### emdb_search (NEW)
**Purpose**: Search EMDB for cryo-EM structures
```python
result = tu.tools.emdb_search(
    query="EGFR membrane receptor"
)
# Returns: EMDB entries with emdb_id, resolution, title
```
**When to use**: Membrane proteins (GPCRs, ion channels), large complexes, targets where conformational states matter.

### emdb_get_entry (NEW)
**Purpose**: Get details for EMDB entry including associated PDB models
```python
result = tu.tools.emdb_get_entry(
    entry_id="EMD-12345"
)
# Returns: entry details including pdb_ids (associated atomic models)
```

**Cryo-EM vs X-ray Decision**:
| Target Type | Prefer | Reason |
|-------------|--------|--------|
| GPCR | Cryo-EM | Native membrane conformation |
| Ion channel | Cryo-EM | Multiple functional states |
| Kinase | X-ray | Higher resolution typically |
| Large complex | Cryo-EM | Better for macromolecular assembly |

---

## Phase 3.5: Docking Validation (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

### NvidiaNIM_diffdock
**Purpose**: Blind molecular docking (no predefined binding site needed)
```python
result = tu.tools.NvidiaNIM_diffdock(
    protein=pdb_content,      # PDB file content as string
    ligand=ligand_sdf,        # Ligand in SDF or MOL2 format
    num_poses=10              # Number of poses to generate
)
# Returns: Docked poses with confidence scores
# Confidence interpretation:
#   >0.9: Excellent, high-confidence pose
#   0.7-0.9: Good, reliable binding mode
#   0.5-0.7: Moderate, consider alternatives
#   <0.5: Low confidence, may not bind
```
**Use**: When you have PDB structure and ligand SDF file.

### NvidiaNIM_boltz2
**Purpose**: Protein-ligand complex from sequence + SMILES
```python
result = tu.tools.NvidiaNIM_boltz2(
    polymers=[{
        "molecule_type": "protein",
        "sequence": "MRPSGTAGAALLALL..."
    }],
    ligands=[{
        "smiles": "COc1cc2ncnc(Nc3ccc(C#C)cc3)c2cc1OCCOC"
    }],
    sampling_steps=50,       # Default: 50, higher = better quality
    diffusion_samples=1      # Number of complex samples
)
# Returns: Protein-ligand complex structure
# Metrics: aggregate_score, pTM, ipTM
#   pTM: Protein structure confidence
#   ipTM: Interface prediction confidence (protein-ligand contact)
```
**Use**: When starting from SMILES only, no SDF file needed.

### Docking Method Selection

| Situation | Use | Reason |
|-----------|-----|--------|
| Have PDB + SDF file | NvidiaNIM_diffdock | Faster, validated inputs |
| Have sequence + SMILES only | NvidiaNIM_boltz2 | End-to-end prediction |
| Quick screening many compounds | NvidiaNIM_diffdock | Faster per ligand |
| Need high-confidence complex | NvidiaNIM_boltz2 | Better at interface prediction |

---

## Phase 4: Compound Expansion Tools

### ChEMBL_search_similar_molecules
**Purpose**: Similarity search in ChEMBL
```python
result = tu.tools.ChEMBL_search_similar_molecules(
    molecule="CC(C)Cc1ccc(cc1)C(C)C(O)=O",  # SMILES, ChEMBL ID, or name
    similarity=70  # Tanimoto threshold (0-100)
)
# Returns: similar molecules with similarity score
```
**⚠️ Parameter**: Use `molecule`, NOT `smiles`

### PubChem_search_compounds_by_similarity
**Purpose**: Similarity search in PubChem
```python
result = tu.tools.PubChem_search_compounds_by_similarity(
    smiles="CC(C)Cc1ccc(cc1)C(C)C(O)=O",
    threshold=0.7  # Tanimoto (0-1)
)
# Returns: CIDs with similarity scores
```

### ChEMBL_search_substructure
**Purpose**: Substructure search in ChEMBL
```python
result = tu.tools.ChEMBL_search_substructure(
    smiles="c1ccc2ncncc2c1"  # Quinazoline core
)
# Returns: molecules containing substructure
```

### PubChem_search_compounds_by_substructure
**Purpose**: Substructure search in PubChem
```python
result = tu.tools.PubChem_search_compounds_by_substructure(
    smiles="c1ccc2ncncc2c1"
)
# Returns: CIDs containing substructure
```

### STITCH_get_chemical_protein_interactions
**Purpose**: Cross-database chemical-protein links
```python
result = tu.tools.STITCH_get_chemical_protein_interactions(
    identifier="EGFR",
    species=9606  # Human
)
# Returns: chemicals with confidence scores
```

---

## Phase 4.4: De Novo Molecule Generation (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

### NvidiaNIM_genmol
**Purpose**: Scaffold hopping with masked regions
```python
result = tu.tools.NvidiaNIM_genmol(
    smiles="COc1cc2ncnc(Nc3ccc([*{3-8}])c([*{1-3}])c3)c2cc1OCCCN1CCOCC1",
    num_molecules=100,       # Number to generate
    temperature=2.0,         # Diversity: 0.5=conservative, 2.0=diverse
    scoring="QED"            # "QED" or "logP"
)
# Returns: Generated molecules with QED/LogP scores
# Mask syntax: [*{min-max}] specifies atom count range
```

**Mask Design Guidelines**:
| Position Type | Mask Example | Typical Use |
|---------------|--------------|-------------|
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

### NvidiaNIM_molmim
**Purpose**: Controlled generation from reference molecule
```python
result = tu.tools.NvidiaNIM_molmim(
    smi="COc1cc2ncnc(Nc3ccc(Cl)cc3)c2cc1OCCN1CCOCC1",
    num_molecules=50,        # Number to generate
    algorithm="CMA-ES"       # Optimization algorithm
)
# Returns: Optimized analogs with property scores
# Generates molecules similar to reference but with optimized properties
```
**Use**: Generate close analogs of top actives with improved properties.

### Generation Strategy

```
1. Identify seeds: Top 3-5 actives from Phase 2
         ↓
2. Design approach:
   ├─ Know specific positions to vary? → NvidiaNIM_genmol (with masks)
   └─ Want general optimization? → NvidiaNIM_molmim
         ↓
3. Generate: 50-100 molecules per seed
         ↓
4. Filter: Pass to Phase 5 (ADMET)
         ↓
5. Dock: Score survivors in Phase 6
```

---

## Phase 5: ADMET Tools

### ADMETAI_predict_physicochemical_properties
**Purpose**: Drug-likeness assessment
```python
result = tu.tools.ADMETAI_predict_physicochemical_properties(
    smiles=["CC(C)Cc1ccc(cc1)C(C)C(O)=O"]  # List of SMILES
)
# Returns: MW, logP, HBD, HBA, Lipinski violations, QED, TPSA
```
**⚠️ Parameter**: `smiles` must be a LIST, even for single compound

### ADMETAI_predict_bioavailability
**Purpose**: Oral absorption prediction
```python
result = tu.tools.ADMETAI_predict_bioavailability(
    smiles=["CC(C)Cc1ccc(cc1)C(C)C(O)=O"]
)
# Returns: Bioavailability_Ma, HIA_Hou, PAMPA, Caco2, Pgp_substrate
```

### ADMETAI_predict_toxicity
**Purpose**: Toxicity endpoint predictions
```python
result = tu.tools.ADMETAI_predict_toxicity(
    smiles=["CC(C)Cc1ccc(cc1)C(C)C(O)=O"]
)
# Returns: AMES, hERG, DILI, ClinTox, LD50, Carcinogens
```

### ADMETAI_predict_CYP_interactions
**Purpose**: CYP enzyme interactions
```python
result = tu.tools.ADMETAI_predict_CYP_interactions(
    smiles=["CC(C)Cc1ccc(cc1)C(C)C(O)=O"]
)
# Returns: CYP1A2, CYP2C9, CYP2C19, CYP2D6, CYP3A4 substrate/inhibitor
```

### ADMETAI_predict_clearance_distribution
**Purpose**: PK predictions
```python
result = tu.tools.ADMETAI_predict_clearance_distribution(
    smiles=["CC(C)Cc1ccc(cc1)C(C)C(O)=O"]
)
# Returns: Clearance, Half_Life, VDss, PPB
```

### ChEMBL_search_compound_structural_alerts
**Purpose**: PAINS and toxicophore detection
```python
result = tu.tools.ChEMBL_search_compound_structural_alerts(
    smiles="CC(C)Cc1ccc(cc1)C(C)C(O)=O"
)
# Returns: structural alerts, PAINS flags
```

---

## Phase 6: Candidate Docking (NVIDIA NIM)

**Requires**: `NVIDIA_API_KEY` environment variable

### Batch Docking Strategy

After ADMET filtering, dock all candidates against the target structure.

```python
# Batch docking workflow
candidates = admet_passed_compounds  # From Phase 5

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

# Sort by confidence
ranked = sorted(docking_results, key=lambda x: x['confidence'], reverse=True)
```

### Scoring Integration

| Score Component | Weight | Source |
|-----------------|--------|--------|
| Docking confidence | 40% | NvidiaNIM_diffdock |
| ADMET score | 30% | ADMETAI_predict_* |
| Similarity to known active | 20% | ChEMBL_search_similar_molecules |
| Novelty bonus | 10% | Structural uniqueness |

---

## Phase 6.5: Literature Evidence (NEW)

### PubMed_search_articles
**Purpose**: Search published SAR studies
```python
result = tu.tools.PubMed_search_articles(
    query="EGFR inhibitor SAR structure-activity",
    limit=30
)
# Returns: articles with pmid, title, abstract, publication date
```

### EuropePMC_search_articles (for Preprints)
**Purpose**: Search preprints from bioRxiv, medRxiv, and other sources (latest findings, not peer-reviewed)
```python
# Search preprints using EuropePMC (bioRxiv/medRxiv don't have search APIs)
result = tu.tools.EuropePMC_search_articles(
    query="EGFR small molecule discovery",
    source="PPR",  # PPR = Preprints only
    pageSize=15
)

# If you have a DOI, get full bioRxiv metadata:
full_metadata = tu.tools.BioRxiv_get_preprint(doi="10.1101/2023.12.01.569554")
# Returns: preprints with doi, title, posted date
```
**⚠️ Note**: Preprints NOT peer-reviewed. Use for emerging compounds/methods.

### MedRxiv_get_preprint
**Purpose**: Get medRxiv preprint by DOI (for search, use EuropePMC with source='PPR')
```python
# Get preprint by DOI
result = tu.tools.MedRxiv_get_preprint(doi="10.1101/2021.04.29.21256344")

# For searching clinical preprints, use EuropePMC:
search = tu.tools.EuropePMC_search_articles(
    query="EGFR inhibitor clinical trial",
    source="PPR",
    pageSize=10
)
# Returns: preprints with doi, title, abstract, etc.
```

### openalex_search_works
**Purpose**: Search with citation analysis
```python
result = tu.tools.openalex_search_works(
    query="EGFR kinase inhibitor structure",
    limit=20
)
# Returns: works with cited_by_count, publication_year
```
**Use**: Identify high-impact papers and validate compound importance.

### SemanticScholar_search
**Purpose**: AI-ranked paper search
```python
result = tu.tools.SemanticScholar_search(
    query="EGFR small molecule binder",
    limit=20
)
# Returns: papers with relevance ranking, citations
```

---

## Fallback Chains

### Target ID Resolution
```
Primary: ChEMBL_search_targets
├─ Success → Use target_chembl_id
└─ Fail → GtoPdb_get_targets (for GPCR/ion channel/enzyme)
         └─ Fail → Document "Target not in databases"
```

### GPCR-Specific Data (NEW)
```
If target is GPCR:
    Primary: GPCRdb_get_protein
    ├─ Success → Get GPCR family, class
    │   ├─ GPCRdb_get_structures → Active/inactive state structures
    │   ├─ GPCRdb_get_ligands → Known agonists/antagonists
    │   └─ GPCRdb_get_mutations → Mutation effects on binding
    └─ Fail (not in GPCRdb) → Use GtoPdb_get_targets
```

### Druggability Assessment
```
Primary: OpenTargets_get_target_tractability_by_ensemblID
├─ Success → Use tractability data
└─ Fail → DGIdb_get_gene_druggability
         └─ Fail → Use target class as proxy
```

### Bioactivity Data
```
Primary: ChEMBL_get_target_activities
├─ Success → Use ChEMBL data
└─ Fail → BindingDB_get_ligands_by_uniprot (NEW)
         ├─ Success → Use BindingDB data
         └─ Fail → GtoPdb_get_target_interactions
                  ├─ Success → Use GtoPdb data
                  └─ Fail → PubChem_search_assays_by_target_gene (NEW)
                           └─ Fail → Document "No bioactivity data"
```

### Similarity Search
```
Primary: ChEMBL_search_similar_molecules
├─ Success → Process results
└─ Fail → PubChem_search_compounds_by_similarity
         └─ Fail → Document "Similarity search failed"
```

### Structure Retrieval
```
Primary: get_protein_metadata_by_pdb_id (for each PDB)
├─ Success → Use experimental structure
└─ Fail (no PDB) → emdb_search (for membrane proteins)
         ├─ Success → Get PDB model via emdb_get_entry
         └─ Fail → NvidiaNIM_alphafold2
                 └─ Fail (API error) → NvidiaNIM_esmfold
                         └─ Fail → alphafold_get_prediction (AlphaFold DB)
                                 └─ Fail → Document "No structural information"
```

### Literature Search (NEW)
```
Primary: PubMed_search_articles (peer-reviewed)
├─ Success → Use published literature
└─ Supplement with:
         ├─ EuropePMC_search_articles (source='PPR' for preprints)
         └─ openalex_search_works (citation analysis)
```

### Docking
```
Primary: NvidiaNIM_diffdock (have PDB + SDF)
├─ Success → Use docking scores
└─ Fail → NvidiaNIM_boltz2 (from sequence + SMILES)
         └─ Fail → Skip docking, use similarity-based scoring
```

### De Novo Generation
```
Primary: NvidiaNIM_genmol (specific position variation)
├─ Success → Process generated molecules
└─ Fail → NvidiaNIM_molmim (general analog generation)
         └─ Fail → Use similarity search only (no generation)
```

### ADMET Prediction
```
Primary: ADMETAI_predict_* (all endpoints)
├─ Success → Use predictions
└─ Fail (invalid SMILES) → Skip compound, document reason
└─ Fail (API error) → Document "ADMET unavailable"
```

---

## Common Parameter Errors

| Tool | Wrong | Correct | Notes |
|------|-------|---------|-------|
| `OpenTargets_*` | `ensembl_id` | `ensemblId` | CamelCase for OpenTargets |
| `ChEMBL_get_target_activities` | `chembl_target_id` | `target_chembl_id` | Underscore style |
| `ChEMBL_search_similar_molecules` | `smiles` | `molecule` | Accepts SMILES, ID, or name |
| `alphafold_get_prediction` | `uniprot` | `accession` | Just the accession |
| `ADMETAI_*` | `smiles="..."` | `smiles=["..."]` | Must be list |
| `NvidiaNIM_alphafold2` | `seq` | `sequence` | Full parameter name |
| `NvidiaNIM_genmol` | `smiles="C..."` | `smiles="C...[*{1-3}]..."` | Must have mask regions |
| `NvidiaNIM_boltz2` | `sequence="..."` | `polymers=[{"molecule_type": "protein", "sequence": "..."}]` | Use polymers list |

---

## Batch Processing Pattern

For efficiency, batch similar operations:

```python
# Define calls
calls = [
    {"name": "ChEMBL_get_molecule", "arguments": {"molecule_chembl_id": id}}
    for id in chembl_ids[:50]  # Batch of 50
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

### NVIDIA NIM Specific Notes

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
    # Fall back to non-NIM alternatives
```

For large expansions (>500 compounds):
1. Use batch endpoints
2. Add small delays between batches
3. Cache results for reuse
4. For docking: prioritize top 50-100 candidates only