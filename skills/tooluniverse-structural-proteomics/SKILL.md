---
name: tooluniverse-structural-proteomics
description: Integrate structural biology data with proteomics for drug target validation. Retrieves protein structures from PDB (RCSB, PDBe), AlphaFold predictions, antibody structures (SAbDab), GPCR data (GPCRdb), binding pocket analysis (ProteinsPlus), and ligand interactions (BindingDB). Use when asked to find structures for a drug target, identify binding site ligands, cross-validate drug binding with structural data, assess structural druggability, or compare experimental vs predicted structures.
---

# Structural Proteomics for Drug Target Validation

Comprehensive structural data integration using ToolUniverse tools across PDB, AlphaFold, GPCRdb, SAbDab, and proteomics databases for drug target validation.

## LOOK UP DON'T GUESS

- PDB structures/resolutions: `PDBeSIFTS_get_best_structures` and `RCSBGraphQL_get_structure_summary`
- AlphaFold confidence: `alphafold_get_summary`
- Ligands/affinities: `PDBe_get_structure_ligands` and `BindingDB_get_ligands_by_uniprot`
- Druggability: `ProteinsPlus_predict_binding_sites`

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Domain Reasoning

Resolution determines valid conclusions: <2A = atom positions visible; 2-3A = side chains reliable, drug design supported; >3A = backbone only, binding site unreliable. Do not over-interpret low-resolution structures.

---

## Tool Inventory

### PDB (RCSB)
`RCSBAdvSearch_search_structures` (query_type, query_value, rows), `RCSBData_get_entry` (entry_id), `RCSBGraphQL_get_structure_summary` (pdb_id), `RCSBGraphQL_get_ligand_info` (pdb_id), `RCSB_get_chemical_component` (comp_id)

### PDB (PDBe)
`pdbe_get_entry_summary` (pdb_id), `PDBe_get_structure_ligands` (pdb_id), `PDBe_get_bound_molecules` (pdb_id), `PDBeSearch_search_structures` (query, rows), `PDBeSIFTS_get_best_structures` (uniprot_id), `PDBeSIFTS_get_all_structures` (uniprot_id), `PDBe_KB_get_ligand_sites` (pdb_id), `PDBe_KB_get_interface_residues` (pdb_id), `PDBeValidation_get_quality_scores` (pdb_id)

### PDBe PISA
`PDBePISA_get_interfaces` (pdb_id), `PDBePISA_get_assemblies` (pdb_id)

### AlphaFold
`alphafold_get_prediction` (qualifier=UniProt), `alphafold_get_summary` (qualifier), `alphafold_get_annotations` (qualifier)

### Binding Sites
`ProteinsPlus_predict_binding_sites` (pdb_id, chain), `BindingDB_get_ligands_by_uniprot` (uniprot_id), `BindingDB_get_ligands_by_pdb` (pdb_id), `BindingDB_get_targets_by_compound` (smiles)

### Foldseek
`Foldseek_search_structure` (sequence, mode="tmalign"), `Foldseek_get_result` (ticket)

### GPCRdb
`GPCRdb_get_protein` (protein), `GPCRdb_get_structures` (protein), `GPCRdb_get_ligands` (protein), `GPCRdb_get_mutations` (protein). Accepts entry names, gene symbols (auto-converted to `{symbol.lower()}_human`), or UniProt accessions.

### SAbDab
`SAbDab_search_structures` (query/antigen), `SAbDab_get_structure` (pdb_id), `TheraSAbDab_search_therapeutics` (query), `TheraSAbDab_search_by_target` (target)

### Domains
`InterPro_get_protein_domains` (uniprot_id), `Pfam_get_protein_annotations` (uniprot_id), `UniProt_get_entry_by_accession` (accession)

### Proteomics
`ProteomeXchange_search_datasets` (query), `ProteomeXchange_get_dataset` (dataset_id)

---

## Workflow 1: Find All Structures for a Drug Target

```
Phase 0: Resolve protein → UniProt ID, gene symbol, organism
Phase 1: PDBeSIFTS_get_best_structures → RCSBGraphQL_get_structure_summary → PDBeValidation
Phase 2: alphafold_get_prediction/summary → compare pLDDT with experimental coverage
Phase 3: IF GPCR → GPCRdb; IF antibody target → SAbDab/TheraSAbDab
Phase 4: InterPro/Pfam domain mapping → identify unresolved regions
Phase 5: Summary table (PDB ID, method, resolution, ligands, coverage, quality)
```

**Decisions**: Resolution <2.5A for drug design. X-ray > Cryo-EM > NMR > AlphaFold for binding sites. Holo > apo structures.

## Workflow 2: Identify Binding Pocket Ligands

```
Phase 1: PDBe_get_structure_ligands + RCSBGraphQL_get_ligand_info + PDBe_KB_get_ligand_sites
Phase 2: ProteinsPlus_predict_binding_sites → druggability score, pocket residues
Phase 3: BindingDB_get_ligands_by_pdb/uniprot → Ki, Kd, IC50
Phase 4: RCSB_get_chemical_component for key ligands
```

**Filter artifacts**: GOL, EDO, SO4, PEG, ACT, CL, NA. Keep cofactors (ATP, NAD, HEM) and catalytic metals (ZN, MG) if relevant.

## Workflow 3: Cross-Validate Drug Binding

```
Phase 1: Find co-crystal structures → filter for drug/analogs
Phase 2: BindingDB affinity data (Ki, Kd, IC50)
Phase 3: ProteinsPlus + PDBe-KB binding site characterization
Phase 4: PDBeValidation quality → binding site well-resolved?
Phase 5: AlphaFold + Foldseek structural comparison
Phase 6: GPCR-specific (if applicable) → active/inactive states, pharmacology, resistance mutations
Phase 7: Antibody-specific (if applicable) → epitope mapping
Phase 8: Evidence integration
```

---

## Tool Parameter Gotchas

| Tool | Mistake | Correct |
|------|---------|---------|
| `alphafold_get_prediction/summary` | `uniprot_id` | `qualifier` |
| `GPCRdb_get_protein` | `gene_name` | `protein` |
| `PDBeSIFTS_get_best_structures` | gene symbol | `uniprot_id` (e.g., "P04637") |
| `Foldseek_search_structure` | `mode="3diaa"` | `mode="tmalign"` |
| `SAbDab_search_structures` | `name` | `query` or `antigen` |
| `RCSB_get_chemical_component` | `ligand_id` | `comp_id` |

---

## Evidence Grading

| Tier | Confidence |
|------|------------|
| T1 | Co-crystal (<2.5A) + binding affinity data |
| T2 | Experimental structure + computational prediction |
| T3 | AlphaFold + pocket analysis + known ligand analogs |
| T4 | Homology model or low-resolution only |

## Interpretation

| Metric | High | Acceptable | Caution |
|--------|------|-----------|---------|
| Resolution | <2.0A (X-ray) / <3.0A (cryo-EM) | 2.0-2.5A / 3.0-4.0A | >3.0A / >4.5A |
| R-free | <0.25 | 0.25-0.30 | >0.30 |
| AlphaFold pLDDT | >90 | 70-90 | <70 (disordered) |

DoGSiteScorer >0.6 = druggable; <0.4 = unlikely druggable. PISA assemblies should be cross-validated with SEC-MALS/native MS.

## Limitations

- BindingDB: 60s+ for popular targets
- AlphaFold: lacks ligand context
- GPCRdb: Class A-F GPCRs only
- PDBePISA: `operation` is internal, not a public parameter
