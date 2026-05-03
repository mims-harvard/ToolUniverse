---
name: tooluniverse-binder-discovery
description: Discover novel small molecule binders for protein targets using structure-based and ligand-based approaches. Creates actionable reports with candidate compounds, ADMET profiles, and synthesis feasibility. Use when users ask to find small molecules for a target, identify novel binders, perform virtual screening, or need hit-to-lead compound identification.
---

# Small Molecule Binder Discovery Strategy

Systematic discovery of novel small molecule binders using 60+ ToolUniverse tools across druggability assessment, known ligand mining, similarity expansion, ADMET filtering, and synthesis feasibility.

**LOOK UP DON'T GUESS** - Always retrieve actual data from tools before drawing conclusions. Do not assume druggability, binding sites, or compound properties based on target class alone.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Target validation FIRST** - Confirm druggability before compound searching
3. **Multi-strategy approach** - Combine structure-based and ligand-based methods
4. **ADMET-aware filtering** - Eliminate poor compounds early
5. **Evidence grading** - Grade candidates by supporting evidence
6. **Actionable output** - Provide prioritized candidates with rationale
7. **English-first queries** - Always use English terms in tool calls. Respond in the user's language

---

## Binding Site Reasoning (Start Here)

Before any tool call, reason about the target's structural biology:

**Is the binding site a well-defined pocket (small molecule accessible) or a flat protein-protein interface (needs peptide/macrocycle)?** This determines your screening strategy.

- **Enzymes with active sites** (proteases, kinases, ATPases): deep, well-defined pockets. Classic small molecule territory. Prioritize co-crystal structure search and known inhibitor scaffold analysis.
- **GPCRs and ion channels**: transmembrane pockets. Structure often available; start with GPCRdb and GtoPdb for known pharmacology.
- **Nuclear receptors**: deep hydrophobic pockets. Excellent small molecule tractability; ligand-based methods are well-powered.
- **Protein-protein interfaces**: flat, large contact surface. Small molecules rarely compete effectively unless there is a "hot spot" cavity. Check whether any allosteric pockets exist before committing to small molecule strategy. Warn the user if no pocket is found.
- **Intrinsically disordered regions**: essentially no small molecule approach. Redirect to peptide or degrader strategies.
- **Scaffolding / adaptor proteins**: assess co-crystal structures for unexpected pockets before declaring undruggable.

Use this reasoning to select phases and warn the user about challenges before executing a full workflow.

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show search process or tool outputs to the user. Instead:

1. **Create the report file FIRST** - Before any data collection:
   - File name: `[TARGET]_binder_discovery_report.md`
   - Initialize with all section headers from the template (see REPORT_TEMPLATE.md)
   - Add placeholder text: `[Researching...]` in each section

2. **Progressively update the report** - As you gather data, update each section immediately.

3. **Output separate data files**:
   - `[TARGET]_candidate_compounds.csv` - Prioritized compounds with SMILES, scores
   - `[TARGET]_bibliography.json` - Literature references (optional)

### 2. Citation Requirements (MANDATORY)

Every piece of information MUST include its source:

Example: `*Source: ChEMBL via ChEMBL_get_target_activities (CHEMBL203)*`

---

## Workflow Overview

Phases in order:
- **Phase 0**: Tool verification (check parameter names with `get_tool_info`)
- **Phase 1**: Target validation — resolve IDs, assess druggability, identify binding sites, predict structure if needed
- **Phase 2**: Known ligand mining — ChEMBL, BindingDB, GtoPdb, PubChem BioAssay, chemical probes; SAR analysis
- **Phase 3**: Structure analysis — PDB co-crystals, EMDB (membrane targets), binding pocket characterization
- **Phase 3.5**: Docking validation — dock reference inhibitor to validate pocket geometry
- **Phase 4**: Compound expansion — similarity/substructure search (seeds: 3-5 diverse actives) + de novo generation
- **Phase 5**: ADMET filtering — physicochemical, bioavailability, toxicity, CYP, structural alerts
- **Phase 6**: Candidate docking and prioritization — score and rank top 20
- **Phase 6.5**: Literature evidence — PubMed, EuropePMC, OpenAlex
- **Phase 7**: Report synthesis and delivery

---

## Phase 0: Tool Verification

**CRITICAL**: Verify tool parameters before calling unfamiliar tools.

```python
tool_info = tu.tools.get_tool_info(tool_name="ChEMBL_get_target_activities")
```

Common parameter corrections (verify with `get_tool_info` if uncertain):
- `OpenTargets_*`: `ensemblId` (camelCase); `ADMETAI_*`: `smiles` must be a list
- `NvidiaNIM_alphafold2`: `sequence` not `seq`; `NvidiaNIM_genmol`: SMILES must contain `[*{min-max}]`
- `NvidiaNIM_boltz2`: `polymers=[{"molecule_type": "protein", "sequence": "..."}]`

---

## Phase 1: Target Validation

### 1.1 Identifier Resolution

Resolve all IDs upfront and store for downstream queries:

```
1. UniProt_search(query=target_name, organism="human") -> UniProt accession
2. MyGene_query_genes(q=gene_symbol, species="human") -> Ensembl gene ID
3. ChEMBL_search_targets(query=target_name, organism="Homo sapiens") -> ChEMBL target ID
4. GtoPdb_get_targets(query=target_name) -> GtoPdb ID (if GPCR/channel/enzyme)
```

### 1.2 Druggability Assessment

Use multi-source triangulation:
- `OpenTargets_get_target_tractability_by_ensemblID(ensemblId)` - tractability bucket
- `DGIdb_get_gene_druggability(genes=[gene_symbol])` - druggability categories
- `OpenTargets_get_target_classes_by_ensemblID(ensemblId)` - target class
- For GPCRs: `GPCRdb_get_protein` + `GPCRdb_get_ligands` + `GPCRdb_get_structures`
- For antibody landscape: `TheraSAbDab_search_by_target(target=target_name)`

**Decision Point**: If no tractability data and binding site reasoning suggests PPI or disordered region, explicitly warn the user before proceeding.

### 1.3 Binding Site Analysis

- `ChEMBL_search_binding_sites(target_chembl_id)`
- `get_binding_affinity_by_pdb_id(pdb_id)` for co-crystallized ligands
- `InterPro_get_protein_domains(accession)` for domain architecture

### 1.4 Structure Prediction (NVIDIA NIM)

Requires `NVIDIA_API_KEY`. Two options:
- **AlphaFold2**: `NvidiaNIM_alphafold2(sequence, algorithm="mmseqs2")` - high accuracy, 5-15 min
- **ESMFold**: `ESMFold_predict_structure(sequence)` - fast (~30s), max 1024 AA

pLDDT guidance: >=90 very high confidence, 70-90 confident, <70 use with caution. Low pLDDT in the putative binding region undermines docking reliability.

---

## Phase 2: Known Ligand Mining

Priority order for bioactivity data:
1. `ChEMBL_get_target_activities` - curated, SAR-ready
2. `BindingDB_get_ligands_by_uniprot` - direct Ki/Kd with literature links
3. `GtoPdb_search_ligands` - pharmacology focus (GPCRs, channels)
4. `PubChem_search_assays_by_target_gene` - HTS screens, novel scaffolds
5. `OpenTargets_get_chemical_probes_by_target_ensemblID` - validated probes

Key steps:
1. Filter to IC50/Ki/Kd < 10 uM; retrieve molecule details for top actives
2. Identify chemical probes and approved drugs
3. Analyze SAR: common scaffolds, key modifications
4. Check off-target selectivity: `BindingDB_get_targets_by_compound`

---

## Phase 3: Structure Analysis

Tools:
- `PDB_search_similar_structures(query=uniprot, type="sequence")` - find PDB entries
- `get_protein_metadata_by_pdb_id(pdb_id)` - resolution, method
- `get_binding_affinity_by_pdb_id(pdb_id)` - co-crystal ligand affinities
- `get_ligand_smiles_by_chem_comp_id(chem_comp_id)` - ligand SMILES from PDB
- `emdb_search(query)` - cryo-EM structures (prefer for GPCRs, ion channels)
- `alphafold_get_prediction(qualifier)` - AlphaFold DB fallback

### Phase 3.5: Docking Validation (NVIDIA NIM)

If PDB + SDF available: use `get_diffdock_info(protein=PDB, ligand=SDF, num_poses=10)`.
If only sequence + SMILES: use `NvidiaNIM_boltz2(polymers=[...], ligands=[...])`.

Dock a known reference inhibitor first to validate the binding pocket geometry before running candidates.

---

## Phase 4: Compound Expansion

### 4.1-4.3 Search-Based Expansion

Use 3-5 diverse actives as seeds, similarity threshold 70-85%:
- `ChEMBL_search_similar_molecules(molecule=SMILES, similarity=70)`
- `PubChem_search_compounds_by_similarity(smiles, threshold=0.7)`
- `ChEMBL_search_substructure(smiles=core_scaffold)`
- `STITCH_get_chemical_protein_interactions(identifier=gene, species=9606)`

### 4.4 De Novo Generation (NVIDIA NIM)

**GenMol** - scaffold hopping with masked regions:
```
NvidiaNIM_genmol(smiles="...core...[*{3-8}]...tail...[*{1-3}]...", num_molecules=100, temperature=2.0, scoring="QED")
```

**MolMIM** - controlled analog generation:
```
NvidiaNIM_molmim(smi=reference_smiles, num_molecules=50, algorithm="CMA-ES")
```

---

## Phase 5: ADMET Filtering

Apply sequentially (all tools accept `smiles=[list]`):

1. **Physicochemical**: `ADMETAI_predict_physicochemical_properties` - Lipinski violations <= 1, QED > 0.3, MW 200-600
2. **Bioavailability**: `ADMETAI_predict_bioavailability` - oral bioavailability > 0.3
3. **Toxicity**: `ADMETAI_predict_toxicity` - AMES < 0.5, hERG < 0.5, DILI < 0.5
4. **CYP**: `ADMETAI_predict_CYP_interactions` - flag CYP3A4 inhibitors
5. **Alerts**: `ChEMBL_search_compound_structural_alerts` - no PAINS

Include a filter funnel summary in the report showing pass/fail counts at each stage.

---

## Phase 6: Candidate Docking & Prioritization

Composite score: docking confidence (40%) + ADMET score (30%) + similarity to known active (20%) + novelty (10%, not in ChEMBL + novel scaffold bonus).

Evidence tiers for candidates:
- T1 (3 stars): Experimental IC50/Ki < 100 nM
- T2 (2 stars): Docking within 5% of reference OR IC50 100-1000 nM
- T3 (1 star): >80% similarity to T1 compound
- T4 (0 stars): 70-80% similarity, scaffold match only
- T5 (no stars): Generated molecule, ADMET-passed, no docking

Deliver top 20 candidates with: Rank, ID, SMILES, docking score, ADMET score, overall score, source, evidence tier.

---

## Phase 6.5: Literature Evidence

- `PubMed_search_articles(query="[TARGET] inhibitor SAR")` - peer-reviewed
- `EuropePMC_search_articles(query, source="PPR")` - preprints (not peer-reviewed)
- `openalex_search_works(query)` - citation analysis

---

## Fallback Chains

```
Target ID:     ChEMBL_search_targets -> GtoPdb_get_targets -> "Not in databases"
Druggability:  OpenTargets tractability -> DGIdb druggability -> target class proxy
Bioactivity:   ChEMBL -> BindingDB -> GtoPdb -> PubChem BioAssay -> "No data"
Structure:     PDB -> EMDB (membrane) -> NvidiaNIM_alphafold2 -> NvidiaNIM_esmfold -> AlphaFold DB -> "None"
Similarity:    ChEMBL similar -> PubChem similar -> "Search failed"
Docking:       get_diffdock_info -> NvidiaNIM_boltz2 -> similarity-based scoring
Generation:    NvidiaNIM_genmol -> NvidiaNIM_molmim -> similarity search only
Literature:    PubMed -> EuropePMC (preprints) -> OpenAlex
GPCR data:     GPCRdb_get_protein -> GtoPdb_get_targets
```

---

## Programmatic Access (Beyond Tools)

When ToolUniverse tools return limited compound sets, access chemical databases directly:

```python
import requests, pandas as pd

# PubChem batch property retrieval (up to 100 CIDs per call)
cids = "2244,5988,3672"
url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/property/MolecularWeight,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount/JSON"
props = pd.DataFrame(requests.get(url).json()["PropertyTable"]["Properties"])

# ChEMBL bioactivity bulk download for a target
target_id = "CHEMBL203"  # EGFR
url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id={target_id}&pchembl_value__gte=5&limit=1000"
activities = requests.get(url).json()["activities"]
df = pd.DataFrame(activities)[["molecule_chembl_id", "canonical_smiles", "pchembl_value", "standard_type"]]

# Lipinski Rule of 5 filtering (no RDKit needed)
lipinski = props[(props["MolecularWeight"] <= 500) & (props["XLogP"] <= 5) &
                 (props["HBondDonorCount"] <= 5) & (props["HBondAcceptorCount"] <= 10)]

# SDF download from PubChem (for docking input)
sdf_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/SDF"
sdf_content = requests.get(sdf_url).text
```

See `tooluniverse-data-wrangling` skill for format cookbook and pagination patterns.

---

## NVIDIA NIM Runtime Notes

AlphaFold2: 5-15 min (async, max ~2000 AA). ESMFold: ~30 sec (max 1024 AA). DiffDock: ~1-2 min/ligand. Boltz2: ~2-5 min. GenMol/MolMIM: ~1-3 min.

Always check: `import os; nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))`

For large expansions (>500 compounds): batch in chunks of 100, prioritize top candidates for docking.

---

## Reference Files

- [WORKFLOW_DETAILS.md](./WORKFLOW_DETAILS.md) - Phase-by-phase procedures, code patterns, screening protocols
- [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) - Complete tool reference with parameters and fallback chains
- [REPORT_TEMPLATE.md](./REPORT_TEMPLATE.md) - Report file template and evidence grading system
- [EXAMPLES.md](./EXAMPLES.md) - End-to-end workflow examples (EGFR, novel target, lead optimization)
- [CHECKLIST.md](./CHECKLIST.md) - Pre-delivery verification checklist
