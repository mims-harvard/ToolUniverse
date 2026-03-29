---
name: tooluniverse-protein-structure-retrieval
description: Retrieves protein structure data from RCSB PDB, PDBe, and AlphaFold with protein disambiguation, quality assessment, and comprehensive structural profiles. Creates detailed structure reports with experimental metadata, ligand information, and download links. Use when users need protein structures, 3D models, crystallography data, or mention PDB IDs (4-character codes like 1ABC) or UniProt accessions.
---

# Protein Structure Data Retrieval

Retrieve protein structures with disambiguation, quality assessment, and comprehensive metadata.

**IMPORTANT**: Always use English terms in tool calls. Respond in the user's language.

**LOOK UP DON'T GUESS**: Never assume PDB IDs, resolution, or availability. Always query RCSB/PDBe and AlphaFold to confirm.

## Domain Reasoning

Not all structures are equal. X-ray <2 A is high-quality for drug design. Cryo-EM 3-4 A is good for fold but not side chains. AlphaFold is excellent for well-folded domains but unreliable for disordered regions. Always check pLDDT (AlphaFold) or resolution (experimental) before drawing conclusions.

## Workflow

```
Phase 0: Clarify (if needed) → Phase 1: Disambiguate Protein → Phase 2: Retrieve Structures → Phase 3: Report
```

---

## Phase 0: Clarification (When Needed)

Ask ONLY if: protein name ambiguous (e.g., "kinase"), organism not specified, unclear if experimental vs AlphaFold needed.
Skip for: specific PDB IDs, UniProt accessions, unambiguous protein+organism.

---

## Phase 1: Protein Disambiguation

```python
# By PDB ID: direct retrieval
# By UniProt: get AlphaFold + search experimental structures
af_structure = tu.tools.alphafold_get_prediction(uniprot_id=uniprot_id)
# By protein name: search
result = tu.tools.PDBeSearch_search_structures(protein_name=protein_name)
```

### Identity Checklist
- Protein name/gene identified, organism confirmed
- UniProt accession (if available), isoform/variant specified (if relevant)

---

## Phase 2: Data Retrieval (Internal)

Retrieve silently. Do NOT narrate the process.

```python
pdb_id = "4INS"

# Search, metadata, quality, ligands, similar structures
result = tu.tools.PDBeSearch_search_structures(protein_name=name)
metadata = tu.tools.get_protein_metadata_by_pdb_id(pdb_id=pdb_id)
exp = tu.tools.RCSBData_get_entry(pdb_id=pdb_id)
quality = tu.tools.PDBeValidation_get_quality_scores(pdb_id=pdb_id)
ligands = tu.tools.PDBe_KB_get_ligand_sites(pdb_id=pdb_id)
similar = tu.tools.PDBeSIFTS_get_all_structures(pdb_id=pdb_id, cutoff=2.0)

# PDBe additional data
summary = tu.tools.pdbe_get_entry_summary(pdb_id=pdb_id)
molecules = tu.tools.pdbe_get_entry_molecules(pdb_id=pdb_id)

# AlphaFold (when no experimental structure, or for comparison)
af = tu.tools.alphafold_get_prediction(uniprot_id=uniprot_id)
```

### Fallback Chains

| Primary | Fallback |
|---------|----------|
| RCSB search | PDBe search |
| get_protein_metadata | pdbe_get_entry_summary |
| Experimental structure | AlphaFold prediction |
| get_protein_ligands | PDBe_KB_get_ligand_sites |

---

## Phase 3: Report Structure Profile

Present as a **Structure Profile Report**. Hide search process. Include:

1. **Search Summary**: query, organism, experimental + AlphaFold structure counts
2. **Best Structure**: PDB ID, UniProt, organism, method, resolution, date, quality assessment
3. **Experimental Details**: method, resolution, R-factor, R-free, space group
4. **Composition**: chains, residues (coverage%), ligands, waters, metals
5. **Bound Ligands**: ligand ID, name, type, binding site
6. **Binding Site Details** (for drug discovery): location, key residues, druggability
7. **Alternative Structures**: ranked by quality with resolution, method, ligands
8. **AlphaFold Prediction**: UniProt, model version, pLDDT confidence distribution, use cases
9. **Structure Comparison**: resolution, completeness, ligands across structures
10. **Download Links**: PDB/mmCIF/AlphaFold formats, database URLs

---

## Quality Assessment

### Experimental Structures

| Tier | Criteria |
|------|----------|
| Excellent | X-ray <1.5A, complete, R-free <0.22 |
| High | X-ray <2.0A OR Cryo-EM <3.0A |
| Good | X-ray 2.0-3.0A OR Cryo-EM 3.0-4.0A |
| Moderate | X-ray >3.0A OR NMR ensemble |
| Low | >4.0A, incomplete, or problematic |

### Resolution Use Cases
<1.5A: atomic detail, H-bond analysis. 1.5-2.0A: drug design. 2.0-2.5A: structure-based design. 2.5-3.5A: overall architecture. >3.5A: domain arrangement only.

### AlphaFold Confidence (pLDDT)
>90: very high, experimental-like. 70-90: good backbone. 50-70: uncertain/flexible. <50: likely disordered.

---

## Error Handling

| Error | Response |
|-------|----------|
| "PDB ID not found" | Verify 4-char format, check if obsoleted |
| "No structures" | Offer AlphaFold, suggest similar proteins |
| "Download failed" | Retry once, provide alternative link |
| "Resolution unavailable" | Likely NMR/model, note in assessment |

---

## Tool Reference

**RCSB PDB**: `PDBeSearch_search_structures` (search), `get_protein_metadata_by_pdb_id` (basic info), `RCSBData_get_entry` (details), `PDBeValidation_get_quality_scores` (quality), `PDBe_KB_get_ligand_sites` (ligands), `PDBeSIFTS_get_all_structures` (homologs)

**PDBe**: `pdbe_get_entry_summary` (overview), `pdbe_get_entry_molecules` (entities), `pdbe_get_experiment_info` (experimental), `PDBe_KB_get_ligand_sites` (pockets)

**AlphaFold**: `alphafold_get_prediction` (get prediction), `alphafold_get_summary` (search)
