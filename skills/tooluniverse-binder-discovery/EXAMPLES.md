# Small Molecule Binder Discovery Examples

Detailed workflow examples for common discovery scenarios.

## Example 1: Well-Characterized Target (EGFR)

**User Query**: "Find novel small molecule binders for EGFR"

### Phase 1: Target Validation

```python
# Step 1.1: Resolve identifiers
uniprot_result = tu.tools.UniProt_search(query="EGFR human", organism="human", limit=5)
# → P00533 (EGFR_HUMAN)

gene_result = tu.tools.MyGene_query_genes(q="EGFR", species="human")
# → ENSG00000146648, NCBI: 1956

chembl_result = tu.tools.ChEMBL_search_targets(query="EGFR", organism="Homo sapiens")
# → CHEMBL203

# Step 1.2: Assess druggability
tractability = tu.tools.OpenTargets_get_target_tractability_by_ensemblID(
    ensemblId="ENSG00000146648"
)
# → Small molecule: bucket 1 (approved drugs exist)

druggability = tu.tools.DGIdb_get_gene_druggability(genes=["EGFR"])
# → Categories: Kinase, Clinically Actionable, 45 drugs
```

**Report Section 1.2**:
```markdown
### 1.2 Druggability Assessment

| Factor | Assessment | Score | Source |
|--------|------------|-------|--------|
| Target class | Receptor tyrosine kinase | ★★★ | ChEMBL |
| Tractability bucket | 1 (approved drugs) | ★★★ | Open Targets |
| Known drugs | 15 approved | ★★★ | DGIdb |
| Binding site | ATP pocket (well-characterized) | ★★★ | PDB |

**Overall Druggability**: ★★★ Highly druggable

*Sources: Open Targets, DGIdb, ChEMBL*
```

### Phase 2: Known Ligand Mining

```python
# Step 2.1: Get all bioactivity data
activities = tu.tools.ChEMBL_get_target_activities(
    target_chembl_id="CHEMBL203",
    limit=500
)
# → 4,847 activity records

# Step 2.2: Filter to potent compounds
potent = [a for a in activities['activities'] 
          if a['standard_type'] in ['IC50', 'Ki'] 
          and a['standard_value'] and float(a['standard_value']) < 100]
# → 312 compounds with IC50/Ki < 100 nM

# Step 2.3: Get molecule details for top actives
top_actives = []
for activity in potent[:20]:
    mol = tu.tools.ChEMBL_get_molecule(
        molecule_chembl_id=activity['molecule_chembl_id']
    )
    top_actives.append({
        'chembl_id': activity['molecule_chembl_id'],
        'ic50': activity['standard_value'],
        'smiles': mol['molecule_structures']['canonical_smiles'],
        'max_phase': mol['max_phase']
    })

# Step 2.4: Get chemical probes
probes = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblID(
    ensemblId="ENSG00000146648"
)
```

**Report Section 2**:
```markdown
### 2.1 ChEMBL Bioactivity Summary

**Total Activity Records**: 4,847
- IC50: 2,345 | Ki: 1,234 | Kd: 456 | EC50: 812

**Potency Distribution**:
| Potency Range | Count | % |
|---------------|-------|---|
| < 10 nM | 89 | 1.8% |
| 10-100 nM | 223 | 4.6% |
| 100-1000 nM | 567 | 11.7% |
| > 1000 nM | 3,968 | 81.9% |

### 2.2 Top 10 Most Potent Compounds

| Rank | Compound | ChEMBL ID | IC50 (nM) | Phase | Scaffold |
|------|----------|-----------|-----------|-------|----------|
| 1 | Osimertinib | CHEMBL3353410 | 0.5 | 4 | Pyrimidine-amine |
| 2 | Dacomitinib | CHEMBL2110732 | 0.8 | 4 | Quinazoline |
| 3 | Afatinib | CHEMBL1173655 | 1.2 | 4 | Quinazoline |
| 4 | Erlotinib | CHEMBL553 | 2.0 | 4 | Quinazoline |
| 5 | Gefitinib | CHEMBL939 | 5.0 | 4 | Quinazoline |
| ... | ... | ... | ... | ... | ... |

*Source: ChEMBL via `ChEMBL_get_target_activities` (CHEMBL203)*
```

### Phase 3: Structure Analysis

```python
# Step 3.1: Find PDB structures
pdb_list = tu.tools.PDB_search_similar_structures(
    query="P00533",
    type="sequence"
)
# → 156 structures

# Step 3.2: Get metadata for key structures
key_pdbs = ["1M17", "4HJO", "5UG9", "6JX4"]
for pdb_id in key_pdbs:
    metadata = tu.tools.get_protein_metadata_by_pdb_id(pdb_id=pdb_id)
    affinity = tu.tools.get_binding_affinity_by_pdb_id(pdb_id=pdb_id)
```

**Report Section 3**:
```markdown
### 3.1 Available Structures

**Total PDB Structures**: 156
- With small molecule ligand: 89
- Apo structures: 34
- With peptide/protein: 33

| PDB ID | Resolution | Ligand | Affinity | Conformation |
|--------|------------|--------|----------|--------------|
| 1M17 | 2.6 Å | Erlotinib | Ki=0.4 nM | Active |
| 4HJO | 2.1 Å | Lapatinib | Ki=3 nM | Inactive |
| 5UG9 | 1.9 Å | Osimertinib | Ki=0.5 nM | Active/C797S |
| 6JX4 | 2.2 Å | Compound X | IC50=12 nM | Active |

**Best Structure for Novel Binder Design**: 5UG9 (highest resolution, relevant mutation)
```

### Phase 4: Compound Expansion

```python
# Step 4.1: Select diverse seeds
seeds = [
    ("CHEMBL553", "COc1cc2ncnc(Nc3ccc(C#C)c(c3)C#C)c2cc1OCCOCCOC"),  # Erlotinib scaffold
    ("CHEMBL3353410", "COc1cc(N2CCC(CC2)n2cc(nc2c2ccc(NC(=O)C=C)c(Nc3nc(ccn3)c3cccnc3)c2)C)ccc1NC(=O)C=C"),  # Osimertinib
    ("CHEMBL1779", "Fc1ccc(Nc2ncnc3cc(OCCCN4CCOCC4)c(OC)cc23)cc1Cl"),  # Gefitinib-like
]

# Step 4.2: Similarity search
all_similar = []
for seed_id, seed_smiles in seeds:
    similar = tu.tools.ChEMBL_search_similar_molecules(
        molecule=seed_smiles,
        similarity=75
    )
    all_similar.extend(similar['molecules'])
# → 892 similar compounds

# Step 4.3: PubChem expansion
pubchem_similar = tu.tools.PubChem_search_compounds_by_similarity(
    smiles=seeds[0][1],
    threshold=0.75
)
# → 456 additional compounds

# Step 4.4: Substructure search for quinazoline
substructure = tu.tools.ChEMBL_search_substructure(
    smiles="c1ccc2ncncc2c1"  # Quinazoline core
)
# → 234 quinazoline-containing compounds

# Step 4.5: Deduplicate
unique_candidates = deduplicate_by_smiles(all_similar + pubchem_similar + substructure)
# → 1,247 unique candidates
```

### Phase 5: ADMET Filtering

```python
# Step 5.1: Batch ADMET prediction
smiles_list = [c['smiles'] for c in unique_candidates]

# Physicochemical
physchem = tu.tools.ADMETAI_predict_physicochemical_properties(smiles=smiles_list)
# Filter: Lipinski ≤ 1, QED > 0.3
passed_physchem = [c for c in physchem if c['Lipinski_violations'] <= 1 and c['QED'] > 0.3]
# → 987 pass

# Bioavailability
bioavail = tu.tools.ADMETAI_predict_bioavailability(smiles=[c['smiles'] for c in passed_physchem])
# Filter: Oral bioavailability > 0.3
passed_bioavail = [c for c in bioavail if c['Bioavailability_Ma'] > 0.3]
# → 834 pass

# Toxicity
toxicity = tu.tools.ADMETAI_predict_toxicity(smiles=[c['smiles'] for c in passed_bioavail])
# Filter: AMES < 0.5, hERG < 0.5
passed_tox = [c for c in toxicity if c['AMES'] < 0.5 and c['hERG'] < 0.5]
# → 723 pass

# Structural alerts
final_candidates = []
for c in passed_tox:
    alerts = tu.tools.ChEMBL_search_compound_structural_alerts(smiles=c['smiles'])
    if not alerts.get('pains', []):
        final_candidates.append(c)
# → 678 pass all filters
```

**Report Section 5**:
```markdown
### 5.4 Filter Summary

| Filter Stage | Input | Passed | Failed | Pass Rate |
|--------------|-------|--------|--------|-----------|
| Initial candidates | 1,247 | - | - | - |
| Physicochemical | 1,247 | 987 | 260 | 79% |
| Drug-likeness (QED) | 987 | 892 | 95 | 90% |
| Bioavailability | 892 | 834 | 58 | 93% |
| Toxicity (AMES/hERG) | 834 | 723 | 111 | 87% |
| Structural alerts | 723 | 678 | 45 | 94% |
| **Final Candidates** | **1,247** | **678** | **569** | **54%** |

**Top Failure Reasons**:
1. MW > 600 Da: 156 compounds (12.5%)
2. hERG liability (>0.5): 78 compounds (6.3%)
3. Low bioavailability (<0.3): 58 compounds (4.7%)
4. PAINS alerts: 32 compounds (2.6%)
```

### Phase 6: Final Prioritization

**Report Section 6.3**:
```markdown
### 6.3 Top 20 Candidate Compounds

| Rank | ID | Evidence | Sim. | ADMET | Novelty | Score | Rationale |
|------|-----|----------|------|-------|---------|-------|-----------|
| 1 | CPD-001 | ★★★ | 0.87 | 4.6 | Novel R-group | 4.5 | 87% to osimertinib, clean ADMET |
| 2 | CPD-002 | ★★☆ | 0.82 | 4.4 | Untested | 4.3 | Quinazoline analog, available |
| 3 | CPD-003 | ★★☆ | 0.79 | 4.5 | Novel core | 4.2 | Pyridine replacement |
| 4 | CPD-004 | ★★☆ | 0.81 | 4.2 | Untested | 4.1 | Improved solubility |
| 5 | CPD-005 | ★☆☆ | 0.76 | 4.3 | Novel scaffold | 4.0 | New chemotype |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Scaffold Diversity**: 8 distinct scaffolds in top 20
**Commercial Availability**: 14/20 available (Enamine, MolPort)
**Estimated Hit Rate**: 20-35% based on similarity to approved drugs

*Scoring: Evidence (25%) + Similarity (25%) + ADMET (25%) + Novelty (15%) + Availability (10%)*
```

---

## Example 2: Novel Target (Limited Data)

**User Query**: "Find small molecules for SLC7A11 (xCT transporter)"

### Key Differences for Novel Targets

1. **Phase 2 will yield limited data** - Few or no known ligands
2. **Rely more on structure-based** - AlphaFold if no experimental structure
3. **Consider similar targets** - Related transporters may have ligands
4. **Lower evidence tiers** - Most candidates will be ★☆☆ or ☆☆☆

### Modified Workflow

```python
# Phase 1: Target validation
# SLC7A11: P60880 (UniProt), ENSG00000151012, limited ChEMBL data

# Phase 2: Known ligands - limited
activities = tu.tools.ChEMBL_get_target_activities(target_chembl_id="CHEMBL4523582")
# → Only 23 activity records, best IC50 = 2.5 µM

# Phase 2b: Check related targets (SLC7 family)
related_targets = ["SLC7A1", "SLC7A5", "SLC7A8"]  # Similar transporters
for target in related_targets:
    activities = tu.tools.ChEMBL_search_targets(query=target)
    # Look for ligands that might cross-react

# Phase 3: Structure - AlphaFold only
structure = tu.tools.alphafold_get_prediction(accession="P60880")
# → AF-P60880-F1 (predicted, pLDDT varies)

# Phase 4: Expand from weak actives AND related target ligands
# Use lower similarity threshold (60-70%) to find more chemotypes

# Phase 5-6: Same ADMET filtering and prioritization
```

**Report Note for Novel Targets**:
```markdown
### Data Gaps & Limitations

| Gap | Impact | Mitigation |
|-----|--------|------------|
| Limited bioactivity data (23 records) | Low confidence in actives | Used related SLC7 family ligands |
| No experimental structure | Binding site uncertain | AlphaFold structure (moderate confidence) |
| Best known IC50 = 2.5 µM | Weak starting point | Prioritize diverse chemotypes |

**Recommended Strategy**: Broader screening campaign with multiple scaffolds
**Estimated Hit Rate**: 5-10% (lower confidence than well-characterized targets)
```

---

## Example 3: Lead Optimization

**User Query**: "Find analogs of compound X (CHEMBL12345) for target Y with improved ADMET"

### Focus on Narrow Expansion

```python
# Step 1: Get reference compound
ref_compound = tu.tools.ChEMBL_get_molecule(molecule_chembl_id="CHEMBL12345")
ref_smiles = ref_compound['molecule_structures']['canonical_smiles']
ref_admet = tu.tools.ADMETAI_predict_toxicity(smiles=[ref_smiles])
# Known issue: hERG = 0.72 (liability)

# Step 2: Tight similarity search (85-95%)
similar = tu.tools.ChEMBL_search_similar_molecules(molecule=ref_smiles, similarity=85)
# → 156 close analogs

# Step 3: Predict ADMET for all
all_smiles = [m['smiles'] for m in similar['molecules']]
admet_results = tu.tools.ADMETAI_predict_toxicity(smiles=all_smiles)

# Step 4: Filter for improved hERG
improved = [m for m, a in zip(similar['molecules'], admet_results) 
            if a['hERG'] < 0.5]  # Improved from 0.72
# → 34 analogs with improved hERG

# Step 5: Check if activity maintained
# Query ChEMBL for any existing bioactivity on these compounds
```

**Report Focus**:
```markdown
### Lead Optimization Summary

**Reference Compound**: CHEMBL12345
- IC50 = 45 nM (target Y)
- hERG liability = 0.72 (CONCERN)
- CYP3A4 inhibitor = 0.65 (moderate)

**Optimization Goal**: Reduce hERG while maintaining potency

### Improved Analogs

| Analog | Sim. | hERG | CYP3A4 | Modification | Activity Status |
|--------|------|------|--------|--------------|-----------------|
| CPD-A | 0.91 | 0.34 | 0.42 | N-methyl→N-H | Untested |
| CPD-B | 0.88 | 0.28 | 0.51 | Remove basic N | Untested |
| CPD-C | 0.92 | 0.41 | 0.38 | Add hydroxyl | IC50=67 nM (similar) |

**Recommended**: CPD-C (proven activity retention, improved hERG)
```

---

## Example 4: NVIDIA NIM-Enhanced Workflow (CDK4 Kinase)

**User Query**: "Discover novel CDK4 inhibitors using all available structure prediction and docking"

### Check NVIDIA NIM Availability

```python
import os
nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))
print(f"NVIDIA NIM tools: {'Available' if nvidia_available else 'Unavailable'}")
```

### Phase 1: Target Validation + Structure Prediction

```python
# Step 1.1: Standard identifier resolution
uniprot_result = tu.tools.UniProt_search(query="CDK4 human", organism="human", limit=5)
# → P11802 (CDK4_HUMAN)

gene_result = tu.tools.MyGene_query_genes(q="CDK4", species="human")
# → ENSG00000135446

chembl_result = tu.tools.ChEMBL_search_targets(query="CDK4", organism="Homo sapiens")
# → CHEMBL3116

# Step 1.2: Get protein sequence
uniprot_details = tu.tools.UniProt_get_entry(accession="P11802")
cdk4_sequence = uniprot_details['sequence']

# Step 1.3: Check for existing PDB structures
pdb_structures = tu.tools.PDB_search_similar_structures(query="P11802", type="sequence")
# → 25 structures, best: 2W9Z (2.0 Å, with palbociclib)

# Step 1.4: Predict structure with NVIDIA NIM for comparison
if nvidia_available:
    predicted_structure = tu.tools.NvidiaNIM_alphafold2(
        sequence=cdk4_sequence,
        algorithm="mmseqs2",
        relax_prediction=False
    )
    # → PDB content with pLDDT scores
    # Mean pLDDT: 88.5 (high confidence)
```

**Report Section 1.4**:
```markdown
### 1.4 Structure Prediction Quality

**Method**: AlphaFold2 via NVIDIA NIM
**Mean pLDDT**: 88.5 (high confidence)

| Confidence Level | Range | Fraction | Interpretation |
|------------------|-------|----------|----------------|
| Very High | ≥90 | 65.2% | Highly reliable |
| Confident | 70-90 | 28.1% | Reliable |
| Low | 50-70 | 5.8% | Use caution |
| Very Low | <50 | 0.9% | Unreliable |

**Key Binding Residue Confidence** (ATP pocket):
| Residue | Function | pLDDT |
|---------|----------|-------|
| K35 | ATP binding | 92.4 |
| E51 | Salt bridge | 89.1 |
| D99 | Catalytic | 94.2 |
| D158 | DFG motif | 91.8 |

**Recommendation**: Use experimental structure 2W9Z (2.0 Å) for docking,
predicted structure validates binding pocket geometry.

*Source: NVIDIA NIM via `NvidiaNIM_alphafold2`*
```

### Phase 3.5: Docking Validation

```python
# Step 3.5.1: Get reference compound (palbociclib) for validation
ref_compound = tu.tools.ChEMBL_get_molecule(molecule_chembl_id="CHEMBL1906")
palbociclib_smiles = ref_compound['molecule_structures']['canonical_smiles']

# Step 3.5.2: Get PDB structure content
pdb_content = tu.tools.get_pdb_structure_file(pdb_id="2W9Z", format="pdb")

# Step 3.5.3: Dock reference compound to validate binding pocket
if nvidia_available:
    # Option A: DiffDock (with PDB + SDF)
    validation_result = tu.tools.NvidiaNIM_diffdock(
        protein=pdb_content,
        ligand=palbociclib_sdf,  # SDF content
        num_poses=10
    )
    reference_confidence = validation_result['poses'][0]['confidence']
    # → 0.92 (excellent)
    
    # Option B: Boltz2 (from sequence + SMILES)
    boltz_result = tu.tools.NvidiaNIM_boltz2(
        polymers=[{"molecule_type": "protein", "sequence": cdk4_sequence}],
        ligands=[{"smiles": palbociclib_smiles}],
        sampling_steps=50,
        diffusion_samples=1
    )
    # → Complex structure with pTM=0.85, ipTM=0.78
```

**Report Section 3.5**:
```markdown
### 3.5 Docking Validation Results

**Reference Compound**: Palbociclib (CHEMBL1906)
**Known IC50**: 11 nM

**DiffDock Validation**:
| Metric | Value | Interpretation |
|--------|-------|----------------|
| Best Pose Confidence | 0.92 | Excellent |
| Poses in ATP pocket | 10/10 | Correct binding mode |
| RMSD to crystal pose | 1.2 Å | Good agreement |

**Boltz2 Validation**:
| Metric | Value | Interpretation |
|--------|-------|----------------|
| pTM | 0.85 | High structure confidence |
| ipTM | 0.78 | Good interface prediction |
| Aggregate Score | 0.81 | Reliable complex |

**Validation Status**: ✓ Binding pocket correctly captured by both methods

*Source: NVIDIA NIM via `NvidiaNIM_diffdock`, `NvidiaNIM_boltz2`*
```

### Phase 4.4: De Novo Molecule Generation

```python
# Step 4.4.1: Identify seed scaffolds from top actives
# Palbociclib scaffold: pyrido[2,3-d]pyrimidin-7-one core
seed_smiles = "CC(=O)c1c(C)c2cnc(Nc3ccc(N4CCNCC4)cn3)nc2n(C2CCCC2)c1=O"

# Step 4.4.2: Design masked SMILES for scaffold hopping
# Vary the piperazine tail and add positions on pyridine
masked_smiles = "CC(=O)c1c(C)c2cnc(Nc3ccc([*{4-10}])c([*{1-3}])n3)nc2n(C2CCCC2)c1=O"

# Step 4.4.3: Generate with GenMol
if nvidia_available:
    genmol_result = tu.tools.NvidiaNIM_genmol(
        smiles=masked_smiles,
        num_molecules=100,
        temperature=2.0,
        scoring="QED"
    )
    # → 100 generated molecules with QED scores
    generated_mols = genmol_result['molecules']
    
    # Filter by basic criteria
    good_qed = [m for m in generated_mols if m['QED'] > 0.5]
    # → 78 pass QED filter

# Step 4.4.4: Alternative with MolMIM (close analogs)
if nvidia_available:
    molmim_result = tu.tools.NvidiaNIM_molmim(
        smi=seed_smiles,
        num_molecules=50,
        algorithm="CMA-ES"
    )
    # → 50 optimized analogs
```

**Report Section 4.4**:
```markdown
### 4.4 De Novo Generation Results

**Seed Scaffold**: Pyrido[2,3-d]pyrimidin-7-one (from palbociclib)
**Method**: GenMol via NVIDIA NIM

**Masked Positions**:
- Position 1: Piperazine tail region `[*{4-10}]`
- Position 2: Pyridine substituent `[*{1-3}]`

| Metric | GenMol | MolMIM |
|--------|--------|--------|
| Molecules Generated | 100 | 50 |
| Passing QED > 0.5 | 78 (78%) | 42 (84%) |
| Mean QED Score | 0.62 | 0.68 |
| Unique Scaffolds | 8 | 3 |
| Mean LogP | 3.8 | 4.1 |

**Top Generated Compounds (GenMol)**:
| ID | SMILES (abbreviated) | QED | LogP | Modification |
|----|---------------------|-----|------|--------------|
| GEN-001 | ...Nc3ccc(N4CCN(C)CC4)c(F)n3... | 0.74 | 3.2 | Methyl-piperazine + F |
| GEN-002 | ...Nc3ccc(N4CCOCC4)c(Cl)n3... | 0.71 | 3.5 | Morpholine + Cl |
| GEN-003 | ...Nc3ccc(NC4CCNCC4)cn3... | 0.69 | 2.9 | Piperidine amine |

**Next Step**: Pass all 120 generated molecules to Phase 5 (ADMET filtering)

*Source: NVIDIA NIM via `NvidiaNIM_genmol`, `NvidiaNIM_molmim`*
```

### Phase 6: Candidate Docking

```python
# After ADMET filtering (Phase 5), dock all candidates
admet_passed = 67  # Compounds passing all ADMET filters

if nvidia_available:
    # Get reference score
    reference_confidence = 0.92  # From Phase 3.5
    
    # Dock all candidates
    docking_results = []
    for compound in admet_passed_compounds:
        result = tu.tools.NvidiaNIM_diffdock(
            protein=pdb_content,
            ligand=compound['sdf'],
            num_poses=5
        )
        
        best_confidence = result['poses'][0]['confidence']
        vs_reference = (best_confidence / reference_confidence - 1) * 100
        
        docking_results.append({
            'id': compound['id'],
            'smiles': compound['smiles'],
            'confidence': best_confidence,
            'vs_reference_pct': vs_reference,
            'evidence_tier': assign_tier(best_confidence, reference_confidence)
        })
    
    # Sort by confidence
    ranked = sorted(docking_results, key=lambda x: x['confidence'], reverse=True)
```

**Report Section 6 (Final)**:
```markdown
### 6. Final Candidate Ranking

**Scoring Method**: Docking (40%) + ADMET (30%) + Similarity (20%) + Novelty (10%)
**Reference**: Palbociclib (confidence: 0.92)

| Rank | ID | Evidence | Docking | vs Ref | ADMET | Score | Source |
|------|-----|----------|---------|--------|-------|-------|--------|
| 1 | GEN-001 | ★★★★ | 0.95 | +3.3% | 4.5 | 4.7 | GenMol |
| 2 | CPD-042 | ★★★ | 0.91 | -1.1% | 4.6 | 4.5 | ChEMBL (IC50=18nM) |
| 3 | GEN-002 | ★★★★ | 0.94 | +2.2% | 4.2 | 4.4 | GenMol |
| 4 | CPD-108 | ★★☆ | 0.89 | -3.3% | 4.4 | 4.2 | PubChem |
| 5 | GEN-015 | ★★☆ | 0.90 | -2.2% | 4.3 | 4.1 | MolMIM |

**Key Findings**:
- 2 de novo generated compounds outperform reference (★★★★)
- 3/5 top candidates from AI generation
- GEN-001 shows novel modification with improved docking score

**Methods Summary**:
| Step | Tool | Purpose |
|------|------|---------|
| Sequence retrieval | UniProt_search | Get CDK4 sequence |
| Structure prediction | NvidiaNIM_alphafold2 | Validate binding pocket |
| Docking validation | NvidiaNIM_diffdock | Confirm pose accuracy |
| Known ligands | ChEMBL_get_target_activities | Mining actives |
| De novo generation | NvidiaNIM_genmol | Novel scaffold exploration |
| ADMET filtering | ADMETAI_predict_* | Drug-likeness |
| Candidate docking | NvidiaNIM_diffdock | Final scoring |

*Full methods and parameters available in appendix*
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Silent Tool Failures

**Problem**: ChEMBL returns empty for wrong parameter name
```python
# WRONG - returns empty
tu.tools.ChEMBL_get_target_activities(chembl_target_id="CHEMBL203")

# CORRECT
tu.tools.ChEMBL_get_target_activities(target_chembl_id="CHEMBL203")
```

**Solution**: Always verify tool parameters before first use.

### Pitfall 2: ADMET Batch Size

**Problem**: Sending 1000+ SMILES crashes or times out
```python
# WRONG - too many at once
tu.tools.ADMETAI_predict_toxicity(smiles=all_1000_smiles)

# CORRECT - batch in chunks
for i in range(0, len(all_smiles), 100):
    batch = all_smiles[i:i+100]
    results = tu.tools.ADMETAI_predict_toxicity(smiles=batch)
    process_results(results)
```

### Pitfall 3: Missing Deduplication

**Problem**: Same compound from multiple sources counted multiple times
```python
# Track by canonical SMILES or InChIKey
seen_inchikeys = set()
unique_candidates = []
for compound in all_candidates:
    inchikey = get_inchikey(compound['smiles'])  # Or use canonical SMILES
    if inchikey not in seen_inchikeys:
        seen_inchikeys.add(inchikey)
        unique_candidates.append(compound)
```

### Pitfall 4: Not Checking Existing Data

**Problem**: Recommending "novel" compounds that are already tested
```python
# Check if compound already has bioactivity for target
for candidate in candidates:
    existing = tu.tools.ChEMBL_search_activities(
        molecule_chembl_id=candidate['chembl_id'],
        target_chembl_id=target_id
    )
    if existing['activities']:
        candidate['status'] = 'ALREADY_TESTED'
        candidate['known_ic50'] = existing['activities'][0]['standard_value']
    else:
        candidate['status'] = 'NOVEL'
```

### Pitfall 5: NVIDIA NIM API Key Not Set

**Problem**: Tools fail silently or return errors
```python
# WRONG - No fallback when NIM unavailable
result = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
# → Error: NVIDIA_API_KEY not set

# CORRECT - Check availability first
import os
nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))

if nvidia_available:
    result = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
else:
    print("NVIDIA NIM unavailable, using AlphaFold DB")
    result = tu.tools.alphafold_get_prediction(accession=uniprot_id)
```

### Pitfall 6: GenMol Mask Syntax Errors

**Problem**: Invalid mask syntax causes generation failure
```python
# WRONG - Missing mask or wrong syntax
tu.tools.NvidiaNIM_genmol(smiles="CCCc1ccc(O)cc1")  # No mask
tu.tools.NvidiaNIM_genmol(smiles="CCCc1ccc([*])cc1")  # No size range
tu.tools.NvidiaNIM_genmol(smiles="CCCc1ccc([*{1,3}])cc1")  # Wrong separator

# CORRECT - Proper mask syntax with dash separator
tu.tools.NvidiaNIM_genmol(
    smiles="CCCc1ccc([*{1-3}])cc1",  # [*{min-max}] format
    num_molecules=50,
    temperature=2.0
)
```

### Pitfall 7: Boltz2 Polymer Format Errors

**Problem**: Wrong input format for protein-ligand complex
```python
# WRONG - Direct sequence input
tu.tools.NvidiaNIM_boltz2(sequence="MKTAYIAK...", smiles="CCO")

# CORRECT - Use polymers and ligands lists
tu.tools.NvidiaNIM_boltz2(
    polymers=[{"molecule_type": "protein", "sequence": "MKTAYIAK..."}],
    ligands=[{"smiles": "CCO"}],
    sampling_steps=50,
    diffusion_samples=1
)
```

### Pitfall 8: Over-relying on Docking Scores

**Problem**: Ranking by docking alone ignores ADMET and novelty
```python
# WRONG - Rank by docking only
ranked = sorted(candidates, key=lambda x: x['docking_score'], reverse=True)

# CORRECT - Multi-factor scoring
def calculate_score(c):
    return (
        c['docking_score'] * 0.40 +      # Docking
        c['admet_score'] * 0.30 +         # ADMET
        c['similarity_score'] * 0.20 +    # Evidence
        c['novelty_score'] * 0.10         # Novelty
    )

ranked = sorted(candidates, key=calculate_score, reverse=True)
```

### Pitfall 9: Not Reporting pLDDT for Predicted Structures

**Problem**: Using predicted structure without confidence assessment
```python
# WRONG - Use structure without quality check
structure = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
# Immediately use for docking...

# CORRECT - Parse and report confidence
structure = tu.tools.NvidiaNIM_alphafold2(sequence=seq)
plddt_scores = parse_plddt_from_pdb(structure['pdb_content'])
mean_plddt = sum(plddt_scores) / len(plddt_scores)

# Report in output
print(f"Mean pLDDT: {mean_plddt:.1f}")
if mean_plddt < 70:
    print("WARNING: Low confidence structure, binding site predictions may be unreliable")
    
# Check binding residue confidence specifically
binding_residues = [10, 15, 50, 80]  # Known binding site residues
for res in binding_residues:
    if plddt_scores[res-1] < 70:
        print(f"WARNING: Binding residue {res} has low confidence ({plddt_scores[res-1]:.1f})")
```
