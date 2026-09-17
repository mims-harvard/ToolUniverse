---
name: tooluniverse-structural-proteomics
description: Structural biology plus proteomics integration for drug target validation. Combines PDB experimental structures, AlphaFold predictions, GPCRdb, SAbDab antibody structures, ProteinsPlus binding-site prediction, BindingDB ligand-affinity data, BMRB NMR data, CATH/InterPro fold classification, intrinsic-disorder prediction (MobiDB/DisProt/IUPred3), membrane-protein topology (OPM/TopDB/PDBTM/ChannelsDB), and enzyme catalytic-site data (M-CSA). Use for druggability assessment, binding-site characterization, ligand-pocket analysis, structural-confidence scoring (resolution, pLDDT), antibody-target interface analysis, disordered-region assessment, membrane-protein topology, and catalytic-mechanism lookup.
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

### Fold/Domain Classification (CATH + InterPro member databases)
`CATH_get_superfamily` (superfamily_id), `CATH_get_domain_summary` (domain_id), `CATH_list_funfams` (superfamily_id), `CATH_get_funfam` (superfamily_id, funfam_number), `InterPro_list_member_databases` (no params), `InterPro_list_member_signatures` (member_database, page_size), `InterPro_get_member_signature` (member_database, accession), `InterPro_get_structures_for_entry` (interpro_id, page_size)

### Proteomics
`ProteomeXchange_search_datasets` (query), `ProteomeXchange_get_dataset` (dataset_id)

### BMRB (NMR data)
`BMRB_search_by_keyword` (term, database="macromolecules"|"metabolomics"), `BMRB_search_by_sequence` (sequence), `BMRB_get_entries_by_pdb_id` (pdb_id), `BMRB_get_entries_by_uniprot` (uniprot_id), `BMRB_get_entry` (entry_id), `BMRB_get_entry_citation` (entry_id), `BMRB_get_validation` (entry_id), `BMRB_search_chemical_shifts` (entry_id or search filters)

### Intrinsic Disorder (MobiDB, DisProt, IUPred3)
`MobiDB_get_protein` (accession), `MobiDB_get_consensus` (accession) — **currently unreachable, see Limitations**. `DisProt_search` (query, page_size), `DisProt_get_entry` (accession — DisProt ID or UniProt accession). `IUPred3_predict_disorder` (accession, iupred_type="long"|"short"|"anchor")

### Membrane Protein Structure (OPM, TopDB, PDBTM, ChannelsDB)
`OPM_search_structures` (query, limit), `TopDB_get_topology` (identifier), `PDBTM_get_topology` (pdb_id), `ChannelsDB_get_channels_pdb` (pdb_id), `ChannelsDB_get_channels_cofactor` (pdb_id)

### Catalytic Site Atlas (M-CSA)
`MCSA_get_entry` (mcsa_id), `MCSA_search_enzymes` (enzyme_name, ec_number, uniprot_id, max_pages, limit)

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

## Workflow 5: Fold and Domain-Signature Classification (CATH + InterPro Member Databases)

CATH classifies a protein *domain*'s 3D fold (Class/Architecture/Topology/Homologous-superfamily) and further groups domains into functionally-coherent FunFams within a superfamily. This is complementary to, not a replacement for, `InterPro_get_protein_domains`/`Pfam_get_protein_annotations` above: those two answer "what domains does *this protein* have," while CATH and the InterPro member-database tools here let you go the other direction — starting from a fold/superfamily/signature and finding everything that belongs to it (structures, domains, or the raw per-database signature catalog behind InterPro's integrated entries).

```
Phase 1: CATH_get_domain_summary(domain_id) -> C.A.T.H classification + residue count for one PDB-chain-domain
         (domain_id format: <pdb_id><chain><domain_number>, e.g. "1cukA01")
Phase 2: CATH_get_superfamily(superfamily_id) -> homologous-superfamily name + domain/family counts across all of CATH
Phase 3: CATH_list_funfams(superfamily_id) -> functional sub-families within that superfamily, ranked by member count
Phase 4: CATH_get_funfam(superfamily_id, funfam_number) -> detail for one specific FunFam
```

**Real example** (verified live): `CATH_get_domain_summary(domain_id="1cukA01")` -> `cath_id: "2.40.50.140.116.1.1.1.1"`, superfamily `2.40.50.140` ("Nucleic acid-binding proteins", Mainly Beta) -> `CATH_get_superfamily("2.40.50.140")` -> 2,879 total domains in this superfamily -> `CATH_list_funfams("2.40.50.140")` -> 1,285 FunFams, top one "30S ribosomal protein S12" (6,057 members).

**Tool note**: `CATH_get_superfamily` takes `superfamily_id`, not `cath_id` — passing `cath_id` fails parameter validation even though the tool's own response echoes a `cath_id` field.

```
Phase 1: InterPro_list_member_databases() -> catalog of all 14 member databases (pfam, cathgene3d, ssf, panther,
         cdd, profile, smart, ncbifam, prosite, prints, hamap, pirsf, sfld, antifam) with entry counts
Phase 2: InterPro_list_member_signatures(member_database, page_size) -> browse that database's raw signature catalog,
         each entry showing its `integrated_interpro` cross-reference if InterPro has folded it into an integrated entry
Phase 3: InterPro_get_member_signature(member_database, accession) -> full detail for one signature (name, GO terms,
         protein/structure/taxa counts)
Phase 4: InterPro_get_structures_for_entry(interpro_id, page_size) -> real PDB structures (with experiment type and
         resolution) whose chains carry a given *integrated* InterPro entry
```

**Real example** (verified live): `InterPro_get_member_signature(member_database="pfam", accession="PF00069")` -> "Protein kinase domain", `integrated_interpro: "IPR000719"`, 1,364,822 proteins / 5,477 structures / 36,542 taxa carry this signature -> `InterPro_get_structures_for_entry(interpro_id="IPR000719")` -> real PDB hits including kinase-inhibitor co-crystals (e.g. `10dj`, Fyn kinase + saracatinib, 2.22Å) — a direct bridge from "this protein has a kinase domain" to "here are solved structures of that domain, several already in complex with a drug."

**Tool note**: `InterPro_get_member_signature` requires BOTH `member_database` and `accession` — the accession alone (e.g. `PF00069`) is not sufficient because the same-shaped accession could theoretically collide across member databases.

## Workflow 6: Intrinsic Disorder Assessment (MobiDB + DisProt + IUPred3)

These three tools answer the same underlying question — "is this region of the protein structured or disordered?" — with different evidence quality, from highest to lowest confidence:

```
Tier 1 (curated experimental evidence): DisProt_search(query) -> DisProt_get_entry(accession)
         -> real, literature-curated disordered-region boundaries with the experimental method that
            established them (NMR, circular dichroism, limited proteolysis, etc.)
Tier 2 (aggregated predictions + curation): MobiDB_get_protein(accession) / MobiDB_get_consensus(accession)
         -> merges DisProt curation with multiple computational predictors into one consensus view
            **currently unreachable, see Limitations below**
Tier 3 (single fast predictor, sequence-only): IUPred3_predict_disorder(accession, iupred_type=...)
         -> a real-time computed disorder score per residue; "long" = long disordered regions,
            "short" = short disordered segments, "anchor" = disorder that becomes ordered upon binding
            a partner (protein-binding-induced folding)
```

**Real example** (verified live): p53/P04637 — `DisProt_get_entry("P04637")` confirms curated disordered regions (DP00086, "Cellular tumor antigen p53"); `IUPred3_predict_disorder(accession="P04637", iupred_type="long")` returns a real per-residue disorder-score profile independently, useful for a quick check even without DisProt curation existing for a given protein.

**When to use which**: check DisProt first if you need citable, experimentally-validated boundaries. Use IUPred3 for any protein (curated or not) when you just need a fast disorder profile. Reach for MobiDB only once it is confirmed reachable again (see Limitations) — do not report a "no disorder data" conclusion based on a MobiDB timeout; that is a connectivity failure, not evidence of an ordered protein.

## Workflow 7: Membrane Protein Structure (OPM + TopDB + PDBTM + ChannelsDB)

```
Phase 1: OPM_search_structures(query, limit) -> solved membrane-protein structures positioned in a lipid
         bilayer, with geometric/energetic properties: hydrophobic thickness, tilt angle, and
         transfer_energy_kcal_per_mol (more negative = more favorable membrane insertion)
Phase 2: TopDB_get_topology(identifier) -> curated per-segment topology (Inside/Membrane/Outside regions)
         for a named protein, cross-species; identifier is typically a TopDB/UniProt-style ID
         (e.g. "OPSD_HUMAN"), not a bare gene symbol
Phase 3: PDBTM_get_topology(pdb_id) -> structure-derived per-chain topology for one specific PDB entry:
         tm_type ("alpha"/"beta"/"non_tm"), num_tm_segments, is_membrane_embedded
Phase 4: ChannelsDB_get_channels_pdb(pdb_id) / ChannelsDB_get_channels_cofactor(pdb_id) -> detected
         channels/tunnels/pores through the structure (general access tunnels vs. cofactor-specific
         access tunnels) for a given PDB entry
```

**Real example** (verified live, cross-validated across all four tools on rhodopsin): `OPM_search_structures(query="rhodopsin")` finds real bacteriorhodopsin/archaerhodopsin family members with thickness/tilt data; `TopDB_get_topology("OPSD_HUMAN")` -> 7 transmembrane segments, reliability score 92.81; `PDBTM_get_topology("1f88")` -> chain A, `tm_type: "alpha"`, `num_tm_segments: 7` — the same helix count TopDB reported independently, a useful cross-check between curated (TopDB) and structure-derived (PDBTM) topology. `ChannelsDB_get_channels_pdb` on a real ion channel (`1bl8`, KcsA potassium channel) returns real annotated pore/tunnel data; **not every PDB entry has ChannelsDB coverage** — `1f88` (rhodopsin) returned "Protein with ID '1f88' not found in ChannelsDB" even though OPM/TopDB/PDBTM all have data for it, so a ChannelsDB miss does not mean the protein lacks a real pore.

## Workflow 8: Enzyme Catalytic Mechanism (M-CSA)

M-CSA (Mechanism and Catalytic Site Atlas) curates the actual catalytic residues and reaction mechanism for enzymes with solved structures — distinct from BRENDA/kinetics data (rates/constants) and from generic active-site predictions (ProteinsPlus above, which is pocket-geometry-based, not mechanism-curated).

```
Phase 1: MCSA_search_enzymes(enzyme_name=... | ec_number=... | uniprot_id=...) -> candidate M-CSA entries
Phase 2: MCSA_get_entry(mcsa_id) -> full catalytic machinery: catalytic residues, mechanism steps,
         EC number(s), reference structure
```

**Real example** (verified live): `MCSA_search_enzymes(enzyme_name="lysozyme")` -> `mcsa_id: 203`, "lysozyme (glycosyl hydrolase 22 family)", EC 3.2.1.17, reference UniProt P00698 -> `MCSA_get_entry(203)` for the full mechanism detail.

---

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
| `CATH_get_superfamily` | `cath_id` | `superfamily_id` |
| `InterPro_get_member_signature` | `accession` alone | `member_database` + `accession` (both required) |
| `TopDB_get_topology` | bare gene symbol | a TopDB/UniProt-style identifier (e.g. `"OPSD_HUMAN"`) |

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
- MobiDB: `MobiDB_get_protein` and `MobiDB_get_consensus` were verified live (repeatedly, with a 90s timeout) to hang indefinitely against their configured endpoint (`https://mobidb.org/api/download`) -- confirmed independently via direct `curl` to the same host (20s with no response). This is an upstream connectivity issue, not a query-parameter mistake. Use DisProt (curated) or IUPred3 (fast predictor) instead until this is confirmed working again -- do not retry MobiDB with a longer timeout expecting it to resolve.
- ChannelsDB: coverage is per-PDB-entry, not universal -- a real membrane protein with confirmed topology elsewhere (OPM/TopDB/PDBTM) can still return "not found in ChannelsDB" for that specific PDB ID (verified live: `1f88` rhodopsin)
