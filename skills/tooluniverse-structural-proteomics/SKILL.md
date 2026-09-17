---
name: tooluniverse-structural-proteomics
description: Structural biology plus proteomics integration for drug target validation. Combines PDB experimental structures, AlphaFold predictions, GPCRdb, SAbDab antibody structures, ProteinsPlus binding-site prediction, and BindingDB ligand-affinity data. Use for druggability assessment, binding-site characterization, ligand-pocket analysis, structural-confidence scoring (resolution, pLDDT), and antibody-target interface analysis.
disable-model-invocation: true
---

# Structural Proteomics for Drug Target Validation

Comprehensive structural data integration using ToolUniverse tools across PDB, AlphaFold, GPCRdb, SAbDab, and proteomics databases for drug target validation.

## LOOK UP DON'T GUESS

- PDB structures/resolutions: `PDBeSIFTS_get_best_structures` and `RCSBGraphQL_get_structure_summary`
- AlphaFold confidence: `alphafold_get_summary`
- Ligands/affinities: `PDBe_get_structure_ligands` and `BindingDB_get_ligands_by_uniprot`
- Protein-protein binding mutations (ddG): `SKEMPI_search_by_structure`/`SKEMPI_search_by_protein`/`SKEMPI_get_mutation` -- BindingDB's protein-protein equivalent, for interface-mutation affinity effects rather than small-molecule ligands
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

### BMRB (NMR data)
`BMRB_search_by_keyword` (term, database="macromolecules"|"metabolomics"), `BMRB_search_by_sequence` (sequence), `BMRB_get_entries_by_pdb_id` (pdb_id), `BMRB_get_entries_by_uniprot` (uniprot_id), `BMRB_get_entry` (entry_id), `BMRB_get_entry_citation` (entry_id), `BMRB_get_validation` (entry_id), `BMRB_search_chemical_shifts` (entry_id or search filters)

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

**Decisions**: Resolution <2.5A for drug design. X-ray > Cryo-EM > NMR > AlphaFold for binding sites. Holo > apo structures. When a target's best experimental structure IS an NMR structure (common for small/disordered proteins where crystallography fails), or when dynamics/flexibility data matters more than a single static pocket geometry, pull the underlying chemical-shift/assignment data via BMRB (Workflow 4) rather than treating the PDB coordinate file as the only NMR evidence available.

## Workflow 4: NMR Structural/Dynamics Data (BMRB)

```
Phase 1: Resolve target -> BMRB_search_by_keyword (protein name) or BMRB_search_by_sequence (exact sequence match)
         or, if you already have an NMR PDB entry -> BMRB_get_entries_by_pdb_id (cross-reference to the matching BMRB entry/entries)
         or BMRB_get_entries_by_uniprot (UniProt accession -> linked BMRB entries)
Phase 2: BMRB_get_entry(entry_id) -> full deposition: saveframes for entry_information, assigned chemical shifts,
         sample conditions, method. BMRB_get_entry_citation(entry_id) -> BibTeX citation for the deposition.
Phase 3: BMRB_get_validation(entry_id) -> AVS (assigned-value-set) analysis: per-residue/per-atom chemical-shift
         typing and assignment-quality scores -- use this before trusting a shift value, the same way
         PDBeValidation quality scores gate trust in an X-ray/cryo-EM structure.
Phase 4 (optional, slow): BMRB_search_chemical_shifts -> raw per-atom chemical-shift table for an entry
         (large response, 15-20s+ for popular entries -- only pull this when the actual shift values are
         needed, e.g. for a downstream chemical-shift-based dynamics or secondary-structure calculation).
```

**Real example** (verified live): PDB `1D3Z` (an NMR ubiquitin structure) -> `BMRB_get_entries_by_pdb_id` returns BMRB entries `11505`, `11547`, `15047`, ... (BLAST-matched by sequence, not a strict 1:1 PDB<->BMRB mapping -- expect several candidate entries and pick by title/method) -> `BMRB_get_entry("11505")` confirms title "Alternative structure of Ubiquitin" -> `BMRB_get_validation("11505")` returns the AVS chemical-shift-typing analysis for that deposition.

**Tool note**: `BMRB_search_by_keyword`'s `term` parameter accepts a plain protein/molecule name (e.g. `"ubiquitin"`, `"calmodulin"`) -- not `keyword`, despite the tool name.

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
| `BMRB_search_by_keyword` | `keyword` | `term` |

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
- BMRB: `BMRB_get_entries_by_pdb_id` is a BLAST-based sequence match, not a curated 1:1 PDB<->BMRB cross-reference -- a query can return several candidate entries (or none) for a real NMR PDB ID; `BMRB_search_chemical_shifts` is slow (15-20s+) for well-studied entries, only call it when raw shift values are actually needed
