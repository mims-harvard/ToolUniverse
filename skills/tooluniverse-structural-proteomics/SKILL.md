---
name: tooluniverse-structural-proteomics
description: Integrate structural biology data with proteomics for drug target validation. Retrieves protein structures from PDB (RCSB, PDBe), AlphaFold predictions, antibody structures (SAbDab), GPCR data (GPCRdb), binding pocket analysis (ProteinsPlus), and ligand interactions (BindingDB). Use when asked to find structures for a drug target, identify binding site ligands, cross-validate drug binding with structural data, assess structural druggability, or compare experimental vs predicted structures.
---

# Structural Proteomics for Drug Target Validation

Comprehensive structural data integration using ToolUniverse tools. Retrieves and cross-references protein structures, binding pockets, ligands, and domain annotations across PDB, AlphaFold, GPCRdb, SAbDab, and proteomics databases to support drug target validation.

## When to Use

Apply when user asks:
- "Find all structures for [protein/target]"
- "What ligands bind to [protein]?"
- "Is [protein] structurally druggable?"
- "Compare experimental vs AlphaFold structure for [protein]"
- "What antibodies target [antigen]?"
- "Show binding pocket details for [PDB ID]"
- "Cross-validate drug binding with structural data"

---

## Tool Inventory (Verified Names)

### PDB Structure Retrieval (RCSB)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `RCSBAdvSearch_search_structures` | Search PDB by protein name, sequence, ligand | `query_type`, `query_value`, `rows` |
| `RCSBData_get_entry` | Get full PDB entry metadata | `entry_id` |
| `RCSBData_get_assembly` | Get biological assembly info | `entry_id`, `assembly_id` |
| `RCSBData_get_nonpolymer_entity` | Get ligand/small molecule entity | `entry_id`, `entity_id` |
| `RCSBGraphQL_get_structure_summary` | GraphQL summary (resolution, method, organism) | `pdb_id` |
| `RCSBGraphQL_get_ligand_info` | GraphQL ligand details in structure | `pdb_id` |
| `RCSBGraphQL_get_polymer_entity` | GraphQL polymer entity (sequence, taxonomy) | `pdb_id`, `entity_id` |
| `RCSB_get_chemical_component` | Get chemical component details (ligand dictionary) | `comp_id` |

### PDB Structure Retrieval (PDBe)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `pdbe_get_entry_summary` | Entry summary (title, method, resolution) | `pdb_id` |
| `pdbe_get_entry_molecules` | Molecules in entry (chains, entities) | `pdb_id` |
| `PDBe_get_structure_ligands` | Ligands bound in structure | `pdb_id` |
| `PDBe_get_bound_molecules` | Bound molecules with binding sites | `pdb_id` |
| `PDBe_get_compound_summary` | Compound/ligand summary | `compound_id` |
| `PDBe_get_compound_structures` | All structures containing a compound | `compound_id` |
| `PDBeSearch_search_structures` | Search PDBe by text/keyword | `query`, `rows` |
| `PDBeSIFTS_get_best_structures` | Best PDB structures for a UniProt ID | `uniprot_id` |
| `PDBeSIFTS_get_all_structures` | All PDB structures for a UniProt ID | `uniprot_id` |
| `PDBe_get_uniprot_mappings` | UniProt-to-PDB residue mappings | `pdb_id` |
| `PDBe_KB_get_ligand_sites` | Ligand binding sites from PDBe-KB | `pdb_id` |
| `PDBe_KB_get_interface_residues` | Protein-protein interface residues | `pdb_id` |
| `PDBeValidation_get_quality_scores` | Structure quality validation scores | `pdb_id` |

### PDBe PISA (Assembly Analysis)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `PDBePISA_get_interfaces` | Protein-protein interfaces analysis | `pdb_id` |
| `PDBePISA_get_assemblies` | Biological assembly predictions | `pdb_id` |
| `PDBePISA_get_monomer_analysis` | Monomer surface analysis | `pdb_id` |

### AlphaFold Predictions
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `alphafold_get_prediction` | Get AlphaFold predicted structure | `qualifier` (UniProt accession) |
| `alphafold_get_summary` | Get AlphaFold prediction summary/confidence | `qualifier` (UniProt accession) |
| `alphafold_get_annotations` | Get AlphaFold functional annotations | `qualifier` |

### Binding Site Analysis
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ProteinsPlus_predict_binding_sites` | Predict druggable binding pockets (DoGSiteScorer) | `pdb_id`, `chain` |
| `BindingDB_get_ligands_by_uniprot` | Known ligands by UniProt ID | `uniprot_id` |
| `BindingDB_get_ligands_by_pdb` | Known ligands by PDB ID | `pdb_id` |
| `BindingDB_get_targets_by_compound` | Find targets for a compound | `smiles` |

### Structural Similarity
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `Foldseek_search_structure` | Structure similarity search | `sequence`, `mode` (default: "tmalign") |
| `Foldseek_get_result` | Get Foldseek search results | `ticket` |

### GPCR Structures (GPCRdb)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `GPCRdb_get_protein` | GPCR protein details | `protein` (entry name or gene symbol) |
| `GPCRdb_get_structures` | All PDB structures for a GPCR | `protein` |
| `GPCRdb_get_ligands` | Ligands for a GPCR | `protein` |
| `GPCRdb_get_mutations` | Known GPCR mutations | `protein` |

**GPCRdb parameter notes:**
- `protein` accepts entry names (e.g., `adrb2_human`), gene symbols (auto-converted to `{symbol.lower()}_human`), or UniProt accessions (uses `/protein/accession/{id}/` fallback)
- HTML entities may appear in ligand/protein name fields -- strip before display
- `nan` DOI values are normalized to `None`
- Use `GPCRdb_list_proteins(protein_class=...)` with family slug or human-readable name (e.g., "chemokine receptors")

### Antibody Structures (SAbDab)
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `SAbDab_search_structures` | Search antibody structures | `query` or `antigen` (alias) |
| `SAbDab_get_structure` | Get antibody structure details | `pdb_id` |
| `SAbDab_get_summary` | Get antibody summary stats | `pdb_id` |
| `TheraSAbDab_search_therapeutics` | Search therapeutic antibodies | `query` |
| `TheraSAbDab_search_by_target` | Therapeutic antibodies by target | `target` |

### Domain & Function Annotation
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `InterPro_get_protein_domains` | Domain annotations for a protein | `uniprot_id` |
| `InterPro_get_entries_for_protein` | All InterPro entries for a protein | `uniprot_id` |
| `Pfam_get_protein_annotations` | Pfam domain annotations | `uniprot_id` |
| `Pfam_get_family_detail` | Pfam family details | `family_id` |
| `UniProt_get_entry_by_accession` | Full UniProt entry | `accession` |
| `UniProt_get_function_by_accession` | Protein function description | `accession` |

### Proteomics Data
| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `ProteomeXchange_search_datasets` | Search proteomics datasets | `query` |
| `ProteomeXchange_get_dataset` | Get proteomics dataset details | `dataset_id` |

**ProteomeXchange notes:**
- `title` is a plain string (not dict)
- Instruments use `{name, accession}` format (not nested terms)

---

## Workflow 1: Find All Structures for a Drug Target

```
Phase 0: Resolve Protein Identity
  -> UniProt_get_entry_by_accession OR MyGene_query_genes
  -> Get: UniProt ID, gene symbol, organism

Phase 1: Experimental Structures (PDB)
  -> PDBeSIFTS_get_best_structures(uniprot_id=...)  [ranked by resolution]
  -> PDBeSIFTS_get_all_structures(uniprot_id=...)    [comprehensive]
  -> For each PDB ID:
     -> RCSBGraphQL_get_structure_summary(pdb_id=...)  [method, resolution, ligands]
     -> PDBeValidation_get_quality_scores(pdb_id=...)   [R-free, clashscore]

Phase 2: Predicted Structures (AlphaFold)
  -> alphafold_get_prediction(qualifier=<uniprot_id>)
  -> alphafold_get_summary(qualifier=<uniprot_id>)
  -> Compare pLDDT confidence regions with experimental coverage

Phase 3: Specialized Structures
  -> IF GPCR: GPCRdb_get_structures(protein=<gene_symbol>)
  -> IF antibody target: SAbDab_search_structures(antigen=<target_name>)
  -> IF antibody: TheraSAbDab_search_by_target(target=<target_name>)

Phase 4: Domain & Coverage Analysis
  -> InterPro_get_protein_domains(uniprot_id=...)
  -> Pfam_get_protein_annotations(uniprot_id=...)
  -> Map structural coverage against domain architecture
  -> Identify unresolved regions (potential flexibility or disorder)

Phase 5: Summary
  -> Tabulate: PDB ID, method, resolution, ligands, coverage, quality
  -> Highlight best structure per use case (drug design, mechanism, complex)
```

### Key Decision Points

- **Resolution filter**: For drug design, prefer structures < 2.5 A resolution
- **Method priority**: X-ray > Cryo-EM > NMR > AlphaFold (for binding sites)
- **Ligand-bound preferred**: Holo structures (with ligand) over apo structures
- **Coverage gaps**: AlphaFold fills regions without experimental structures

---

## Workflow 2: Identify Binding Pocket Ligands

```
Phase 0: Get PDB ID(s)
  -> From Workflow 1, or user provides directly

Phase 1: Ligand Extraction
  -> PDBe_get_structure_ligands(pdb_id=...)         [all ligands in structure]
  -> RCSBGraphQL_get_ligand_info(pdb_id=...)        [detailed ligand properties]
  -> PDBe_get_bound_molecules(pdb_id=...)           [binding site context]
  -> PDBe_KB_get_ligand_sites(pdb_id=...)           [curated binding sites]

Phase 2: Binding Pocket Prediction
  -> ProteinsPlus_predict_binding_sites(pdb_id=..., chain=...)
  -> Returns: pocket volume, druggability score, pocket residues
  -> Cross-reference predicted pockets with bound ligands

Phase 3: Known Ligands from Binding Databases
  -> BindingDB_get_ligands_by_pdb(pdb_id=...)
  -> BindingDB_get_ligands_by_uniprot(uniprot_id=...)  [can be slow for popular targets]
  -> Returns: Ki, Kd, IC50 values for known binders

Phase 4: Compound Details
  -> For key ligands: RCSB_get_chemical_component(comp_id=<ligand_3letter_code>)
  -> PDBe_get_compound_summary(compound_id=<ligand_code>)
  -> Get: molecular weight, formula, SMILES, InChI

Phase 5: Cross-Structure Ligand Comparison
  -> PDBe_get_compound_structures(compound_id=...)   [all structures with this ligand]
  -> Compare binding poses across structures
  -> Identify conserved interactions vs crystal contacts/artifacts
```

### Filtering Artifacts

Common non-drug ligands to filter out:
- Buffer/crystallization: GOL (glycerol), EDO (ethylene glycol), SO4, PEG, ACT (acetate), CL, NA
- Cofactors (keep if relevant): ATP, ADP, NAD, FAD, HEM
- Metals (keep if catalytic): ZN, MG, CA, MN, FE

---

## Workflow 3: Cross-Validate Drug Binding with Structural Data

```
Phase 0: Identify Drug and Target
  -> Drug: name/SMILES/ChEMBL ID
  -> Target: gene symbol/UniProt ID

Phase 1: Find Co-crystal Structures
  -> PDBeSIFTS_get_all_structures(uniprot_id=...)
  -> Filter structures containing the drug or close analogs
  -> RCSBGraphQL_get_ligand_info(pdb_id=...) for each candidate

Phase 2: Binding Affinity Data
  -> BindingDB_get_ligands_by_uniprot(uniprot_id=...)
  -> Filter for drug of interest
  -> Collect: Ki, Kd, IC50 measurements

Phase 3: Binding Site Characterization
  -> ProteinsPlus_predict_binding_sites(pdb_id=..., chain=...)
  -> PDBe_KB_get_ligand_sites(pdb_id=...)
  -> PDBe_KB_get_interface_residues(pdb_id=...)  [for biologic drugs]
  -> Map drug binding site residues

Phase 4: Structural Quality Assessment
  -> PDBeValidation_get_quality_scores(pdb_id=...)
  -> PDBeValidation_get_outlier_residues(pdb_id=...)
  -> Check: Are binding site residues well-resolved?
  -> Flag structures with poor electron density at binding site

Phase 5: Structural Comparison
  -> If AlphaFold available: alphafold_get_prediction(qualifier=<uniprot_id>)
  -> Compare predicted vs experimental binding site conformation
  -> Foldseek_search_structure() for structural homologs with similar binding

Phase 6: GPCR-Specific (if applicable)
  -> GPCRdb_get_structures(protein=...) [active/inactive states]
  -> GPCRdb_get_ligands(protein=...)    [pharmacology data]
  -> GPCRdb_get_mutations(protein=...)  [resistance mutations]

Phase 7: Antibody-Specific (if applicable)
  -> SAbDab_search_structures(antigen=<target>)
  -> TheraSAbDab_search_therapeutics(query=<drug_name>)
  -> Epitope mapping from crystal structures

Phase 8: Evidence Integration
  -> Cross-reference: co-crystal structure + binding affinity + pocket druggability
  -> Confidence assessment:
     - HIGH: Co-crystal + sub-uM binding + druggable pocket
     - MEDIUM: Binding data without co-crystal, or co-crystal without affinity
     - LOW: Computational prediction only (AlphaFold, docking)
```

---

## Tool Parameter Gotchas

| Tool | Common Mistake | Correct Usage |
|------|---------------|---------------|
| `alphafold_get_prediction` | Using `uniprot_id` | Use `qualifier` param |
| `alphafold_get_summary` | Using `uniprot_id` | Use `qualifier` param |
| `GPCRdb_get_protein` | Using `gene_name` | Use `protein` param (entry name or symbol) |
| `ProteinsPlus_predict_binding_sites` | Missing `chain` | Include `chain` param for specificity |
| `BindingDB_get_ligands_by_uniprot` | Expecting fast response | Can take 60s+ for popular targets (e.g., EGFR) |
| `PDBeSIFTS_get_best_structures` | Using gene symbol | Use `uniprot_id` (e.g., "P04637") |
| `RCSBAdvSearch_search_structures` | Wrong `query_type` | Check valid types: "full_text", "sequence", etc. |
| `Foldseek_search_structure` | Using `mode="3diaa"` | Use `mode="tmalign"` (default corrected) |
| `SAbDab_search_structures` | Using `name` | Use `query` or `antigen` (alias) |
| `RCSB_get_chemical_component` | Using `ligand_id` | Use `comp_id` (3-letter code, e.g., "ATP") |

---

## Response Format Notes

| Tool | Response Structure |
|------|-------------------|
| `RCSBGraphQL_get_structure_summary` | `{data: {entry: {rcsb_id, exptl, cell, ...}}}` |
| `PDBeSIFTS_get_best_structures` | `{<uniprot_id>: [{pdb_id, chain_id, resolution, ...}]}` |
| `alphafold_get_prediction` | `{data: {pdbUrl, cifUrl, ...}}` or direct structure data |
| `ProteinsPlus_predict_binding_sites` | Binding pocket list with volume, druggability, residues |
| `BindingDB_get_ligands_by_uniprot` | `{bdb.affinities: [...]}` (NOT `{affinities: [...]}`) |
| `GPCRdb_get_structures` | List of structure dicts with PDB IDs, ligands, states |
| `PDBe_get_structure_ligands` | `{<pdb_id>: [{chem_comp_id, ...}]}` |
| `PDBePISA_get_interfaces` | Interface data (operation is read from config, NOT a public param) |

---

## Evidence Grading

| Tier | Source | Confidence |
|------|--------|------------|
| T1 | Co-crystal structure with drug (< 2.5 A) + binding affinity data | Highest |
| T2 | Experimental structure + computational docking/binding prediction | High |
| T3 | AlphaFold prediction + pocket analysis + known ligand analogs | Medium |
| T4 | Homology model or low-resolution structure only | Low |

---

## Completeness Checklist

- [ ] Protein identity resolved (UniProt ID, gene symbol, organism)
- [ ] Experimental structures retrieved from PDB (RCSB + PDBe)
- [ ] AlphaFold prediction checked for coverage gaps
- [ ] Binding pockets analyzed (ProteinsPlus or PDBe-KB)
- [ ] Known ligands retrieved (BindingDB or PDBe ligands)
- [ ] Domain architecture mapped (InterPro/Pfam)
- [ ] Structure quality validated (resolution, R-free, clashscore)
- [ ] GPCR-specific tools used if applicable
- [ ] Antibody-specific tools used if applicable
- [ ] Evidence tier assigned for each structural finding
- [ ] Artifact ligands filtered (GOL, EDO, SO4, etc.)
- [ ] Summary table with PDB ID, method, resolution, ligands, coverage

---

## Interpretation Framework

| Quality Metric | High Confidence | Acceptable | Caution |
|----------------|-----------------|------------|---------|
| **Resolution** | < 2.0 A (X-ray) or < 3.0 A (cryo-EM) | 2.0-2.5 A (X-ray) or 3.0-4.0 A (cryo-EM) | > 3.0 A (X-ray) or > 4.5 A (cryo-EM) |
| **Validation (R-free)** | < 0.25 | 0.25-0.30 | > 0.30 or not reported |
| **AlphaFold pLDDT** | > 90 (very high) | 70-90 (confident) | < 70 (low -- treat as disordered) |

**Interpreting structural data:**
- Cross-linking mass spectrometry distance constraints are reliable when the crosslinker-specific distance threshold is met (e.g., BS3 < 30 A Ca-Ca); violations above 1.5x the threshold suggest conformational heterogeneity or false-positive crosslinks.
- Binding pocket druggability scores from ProteinsPlus (DoGSiteScorer) above 0.6 indicate a likely druggable site; scores below 0.4 suggest the pocket is too shallow or hydrophilic for conventional small-molecule binding.
- Stoichiometry assignments from PDBePISA should be cross-validated with experimental methods (SEC-MALS, native MS); PISA assemblies are predictions based on buried surface area and may over-call oligomeric states for crystal contacts.

**Synthesis questions to address in the report:**
1. Does the binding site geometry remain consistent across multiple crystal forms and cryo-EM reconstructions, or is it sensitive to crystal packing?
2. For regions modeled only by AlphaFold (pLDDT 70-90): are these regions functionally relevant, and would their flexibility affect drug binding?
3. Do BindingDB affinity measurements correlate with the structural binding mode -- i.e., do tighter binders make more contacts in the co-crystal structure?

---

## Limitations

1. **BindingDB latency**: Queries for popular targets (EGFR, kinases) can take 60+ seconds
2. **AlphaFold binding sites**: Predicted structures lack ligand context; pocket geometry may differ from holo structures
3. **GPCRdb coverage**: Only covers Class A-F GPCRs; non-GPCR membrane proteins not included
4. **SAbDab coverage**: Primarily covers antibody-antigen complexes with PDB structures
5. **ProteinsPlus availability**: External service; may have occasional downtime
6. **PDBePISA**: `operation` is internal (read from fields config), not a public parameter

---

## References

- **PDB/RCSB**: https://www.rcsb.org/
- **PDBe**: https://www.ebi.ac.uk/pdbe/
- **AlphaFold DB**: https://alphafold.ebi.ac.uk/
- **GPCRdb**: https://gpcrdb.org/
- **SAbDab**: http://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab/
- **BindingDB**: https://www.bindingdb.org/
- **ProteinsPlus**: https://proteins.plus/
- **InterPro**: https://www.ebi.ac.uk/interpro/
- **Pfam**: https://www.ebi.ac.uk/interpro/entry/pfam/
- **ProteomeXchange**: http://www.proteomexchange.org/
