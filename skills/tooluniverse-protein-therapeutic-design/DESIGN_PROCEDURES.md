# Therapeutic Protein Designer - Design Procedures

Detailed code examples and procedures for each design phase.

---

## Phase 1: Target Characterization

```python
def get_target_structure(tu, target_id):
    """Get target structure: PDB first, then EMDB cryo-EM, then AlphaFold."""
    # Try PDB (X-ray/NMR)
    # PDBeSIFTS_get_best_structures maps a UniProt accession to PDB entries
    sifts = tu.tools.PDBeSIFTS_get_best_structures(uniprot_accession=target_id)
    pdb_results = sifts.get('data', {}).get('structures', []) if sifts.get('status') == 'success' else []
    if pdb_results:
        best_pdb = sorted(pdb_results, key=lambda x: x.get('resolution') or 99)[0]
        return {'source': 'PDB', 'pdb_id': best_pdb['pdb_id']}

    # Try EMDB (cryo-EM, good for membrane proteins)
    protein_info = tu.tools.UniProt_get_entry_by_accession(accession=target_id)
    emdb_results = tu.tools.EMDB_search_structures(query=protein_info['proteinDescription']['recommendedName']['fullName']['value'])
    emdb_hits = emdb_results.get('data', []) if emdb_results.get('status') == 'success' else []
    if emdb_hits:
        best_emdb = emdb_hits[0]  # records carry emdb_id but no top-level resolution
        emdb_details = tu.tools.EMDB_get_structure(emdb_id=best_emdb['emdb_id'])
        # Only some maps cross-reference a fitted PDB model
        pdb_refs = emdb_details.get('data', {}).get('crossreferences', {}).get('pdb_list', {}).get('pdb_reference', [])
        if pdb_refs:
            return {'source': 'EMDB cryo-EM', 'emdb_id': best_emdb['emdb_id'], 'pdb_id': pdb_refs[0]['pdb_id']}

    # Fallback: AlphaFold prediction
    sequence = tu.tools.UniProt_get_sequence_by_accession(accession=target_id)
    structure = tu.tools.NvidiaNIM_alphafold2(sequence=sequence['sequence'], algorithm="mmseqs2")
    return {'source': 'AlphaFold2 (predicted)', 'structure': structure}
```

---

## Phase 2-3: Backbone + Sequence Design

```python
# Phase 2: RFdiffusion backbone generation
backbones = tu.tools.NvidiaNIM_rfdiffusion(diffusion_steps=50)

# Phase 3: ProteinMPNN sequence design
sequences = tu.tools.NvidiaNIM_proteinmpnn(pdb_string=backbone_pdb, num_sequences=8, temperature=0.1)
```

### Sampling Parameters

| Setting | Temperature | Sequences/backbone | Use case |
|---------|-------------|-------------------|----------|
| Conservative | 0.1 | 4 | Validated scaffold |
| Moderate | 0.2 | 8 | Exploration |
| Diverse | 0.5 | 16 | Maximum diversity |

**Design modes**: Unconditional (de novo scaffold), Binder design (target-guided), Motif scaffolding (functional motif embedding).

---

## Phase 4: Structure Validation

```python
predicted = tu.tools.NvidiaNIM_esmfold(sequence=sequence)
plddt = extract_plddt(predicted)
ptm = extract_ptm(predicted)
passes = np.mean(plddt) > 70 and ptm > 0.7
```

| Metric | Threshold | Interpretation |
|--------|-----------|----------------|
| Mean pLDDT | >70 | Confident fold |
| pTM | >0.7 | Good global topology |
| RMSD to backbone | <2 A | Design recapitulated |

---

## Phase 5: Developability Assessment

| Metric | Favorable | Marginal | Unfavorable |
|--------|-----------|----------|-------------|
| Aggregation score | <0.5 | 0.5-0.7 | >0.7 |
| Isoelectric point | 5-9 | 4-5 or 9-10 | <4 or >10 |
| Hydrophobic patches | <3 | 3-5 | >5 |
| Cysteine count | 0 or even | Odd | Multiple unpaired |

---

## Fallback Chains

| Primary | Fallback 1 | Fallback 2 |
|---------|------------|------------|
| `NvidiaNIM_rfdiffusion` | Manual backbone | Scaffold from PDB |
| `NvidiaNIM_proteinmpnn` | Rosetta ProteinMPNN | Manual sequence |
| `NvidiaNIM_esmfold` | `NvidiaNIM_alphafold2` | AlphaFold DB |
| PDB structure | EMDB cryo-EM + PDB | `NvidiaNIM_alphafold2` |
| `EMDB_search_structures` + PDB model | PDB_search_similar_structures | `NvidiaNIM_alphafold2` |
