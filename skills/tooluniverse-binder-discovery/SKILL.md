---
name: tooluniverse-binder-discovery
description: Discover novel small molecule binders for protein targets using structure-based and ligand-based approaches. Creates actionable reports with candidate compounds, ADMET profiles, and synthesis feasibility. Use when users ask to find small molecules for a target, identify novel binders, perform virtual screening, or need hit-to-lead compound identification.
---

# Small Molecule Binder Discovery Strategy

Systematic discovery of novel small molecule binders using 60+ ToolUniverse tools across druggability assessment, known ligand mining, similarity expansion, ADMET filtering, and synthesis feasibility.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Target validation FIRST** - Confirm druggability before compound searching
3. **Multi-strategy approach** - Combine structure-based and ligand-based methods
4. **ADMET-aware filtering** - Eliminate poor compounds early
5. **Evidence grading** - Grade candidates by supporting evidence
6. **Actionable output** - Provide prioritized candidates with rationale
7. **English-first queries** - Always use English terms in tool calls, even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show search process or tool outputs to the user. Instead:

1. **Create the report file FIRST** - Before any data collection:
   - File name: `[TARGET]_binder_discovery_report.md`
   - Initialize with all section headers from the template (see REPORT_TEMPLATE.md)
   - Add placeholder text: `[Researching...]` in each section

2. **Progressively update the report** - As you gather data:
   - Update each section with findings immediately
   - The user sees the report growing, not the search process

3. **Output separate data files**:
   - `[TARGET]_candidate_compounds.csv` - Prioritized compounds with SMILES, scores
   - `[TARGET]_bibliography.json` - Literature references (optional)

### 2. Citation Requirements (MANDATORY)

Every piece of information MUST include its source:

```markdown
*Source: ChEMBL via `ChEMBL_get_target_activities` (CHEMBL203)*
*Source: PDB via `get_protein_metadata_by_pdb_id` (1M17)*
*Source: ADMET-AI via `ADMETAI_predict_toxicity`*
*Source: NVIDIA NIM via `NvidiaNIM_alphafold2` (pLDDT: 90.94)*
```

---

## Workflow Overview

```
Phase 0: Tool Verification (check parameter names)
    |
Phase 1: Target Validation
    |- 1.1 Resolve identifiers (UniProt, Ensembl, ChEMBL target ID)
    |- 1.2 Assess druggability/tractability
    |   +- 1.2a GPCRdb integration (for GPCR targets)
    |   +- 1.2.5 Check therapeutic antibodies (Thera-SAbDab)
    |- 1.3 Identify binding sites
    +- 1.4 Predict structure (NvidiaNIM_alphafold2/esmfold)
    |
Phase 2: Known Ligand Mining
    |- ChEMBL bioactivity data
    |- GtoPdb interactions
    |- Chemical probes (Open Targets)
    |- BindingDB affinity data (Ki/IC50/Kd)
    |- PubChem BioAssay HTS data (screening hits)
    +- SAR analysis from known actives
    |
Phase 3: Structure Analysis
    |- PDB structures with ligands
    |- EMDB cryo-EM structures (for membrane targets)
    |- Binding pocket analysis
    +- Key interactions
    |
Phase 3.5: Docking Validation (NvidiaNIM_diffdock/boltz2)
    |- Dock reference inhibitor
    +- Validate binding pocket geometry
    |
Phase 4: Compound Expansion
    |- 4.1-4.3 Similarity/substructure search
    +- 4.4 De novo generation (NvidiaNIM_genmol/molmim)
    |
Phase 5: ADMET Filtering
    |- Physicochemical properties (Lipinski, QED)
    |- Bioavailability, toxicity, CYP interactions
    +- Structural alerts (PAINS)
    |
Phase 6: Candidate Docking & Prioritization
    |- Dock all candidates (NvidiaNIM_diffdock/boltz2)
    |- Score by docking (40%) + ADMET (30%) + similarity (20%) + novelty (10%)
    |- Assess synthesis feasibility
    +- Generate final ranked list (top 20)
    |
Phase 6.5: Literature Evidence
    |- PubMed (peer-reviewed SAR studies)
    |- EuropePMC preprints (source='PPR')
    +- OpenAlex citation analysis
    |
Phase 7: Report Synthesis & Delivery
```

---

## Phase 0: Tool Verification

**CRITICAL**: Verify tool parameters before calling unfamiliar tools.

```python
tool_info = tu.tools.get_tool_info(tool_name="ChEMBL_get_target_activities")
```

### Known Parameter Corrections

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `OpenTargets_*` | `ensembl_id` | `ensemblId` (camelCase) |
| `ChEMBL_get_target_activities` | `target_chembl_id` | `target_chembl_id__exact` |
| `ChEMBL_search_similar_molecules` | `smiles` | `molecule` (accepts SMILES, ChEMBL ID, or name) |
| `alphafold_get_prediction` | `uniprot` | `qualifier` |
| `ADMETAI_*` | `smiles="..."` | `smiles=["..."]` (must be list) |
| `NvidiaNIM_alphafold2` | `seq` | `sequence` |
| `NvidiaNIM_genmol` | `smiles="C..."` | `smiles="C...[*{1-3}]..."` (must have mask) |
| `NvidiaNIM_boltz2` | `sequence="..."` | `polymers=[{"molecule_type": "protein", "sequence": "..."}]` |

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

**Decision Point**: If druggability < 2 stars, warn user about challenges.

### 1.3 Binding Site Analysis

- `ChEMBL_search_binding_sites(target_chembl_id)`
- `get_binding_affinity_by_pdb_id(pdb_id)` for co-crystallized ligands
- `InterPro_get_protein_domains(accession)` for domain architecture

### 1.4 Structure Prediction (NVIDIA NIM)

Requires `NVIDIA_API_KEY`. Two options:
- **AlphaFold2**: `NvidiaNIM_alphafold2(sequence, algorithm="mmseqs2")` - high accuracy, 5-15 min
- **ESMFold**: `NvidiaNIM_esmfold(sequence)` - fast (~30s), max 1024 AA

Always report pLDDT confidence scores (>=90 very high, 70-90 confident, <70 caution).

---

## Phase 2: Known Ligand Mining

### Tools (in order of priority)

| Source | Tool | Strengths |
|--------|------|-----------|
| ChEMBL | `ChEMBL_get_target_activities` | Curated, SAR-ready |
| BindingDB | `BindingDB_get_ligands_by_uniprot` | Direct Ki/Kd, literature links |
| GtoPdb | `GtoPdb_search_ligands` | Pharmacology focus (GPCRs, channels) |
| PubChem | `PubChem_search_assays_by_target_gene` | HTS screens, novel scaffolds |
| Open Targets | `OpenTargets_get_chemical_probes_by_target_ensemblID` | Validated probes |

### Key Steps

1. Get all bioactivities: filter to IC50/Ki/Kd < 10 uM
2. Get molecule details for top actives: `ChEMBL_get_molecule`
3. Identify chemical probes and approved drugs
4. Analyze SAR: common scaffolds, key modifications
5. Check off-target selectivity: `BindingDB_get_targets_by_compound`

---

## Phase 3: Structure Analysis

### Tools

- `PDB_search_similar_structures(query=uniprot, type="sequence")` - find PDB entries
- `get_protein_metadata_by_pdb_id(pdb_id)` - resolution, method
- `get_binding_affinity_by_pdb_id(pdb_id)` - co-crystal ligand affinities
- `get_ligand_smiles_by_chem_comp_id(chem_comp_id)` - ligand SMILES from PDB
- `emdb_search(query)` - cryo-EM structures (prefer for GPCRs, ion channels)
- `alphafold_get_prediction(qualifier)` - AlphaFold DB fallback

### Phase 3.5: Docking Validation (NVIDIA NIM)

| Situation | Tool | Input |
|-----------|------|-------|
| Have PDB + SDF | `NvidiaNIM_diffdock` | protein=PDB, ligand=SDF, num_poses=10 |
| Have sequence + SMILES | `NvidiaNIM_boltz2` | polymers=[...], ligands=[...] |

Dock a known reference inhibitor first to validate the binding pocket.

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
Mask syntax: `[*{min-max}]` specifies atom count range.

**MolMIM** - controlled analog generation:
```
NvidiaNIM_molmim(smi=reference_smiles, num_molecules=50, algorithm="CMA-ES")
```

---

## Phase 5: ADMET Filtering

Apply filters sequentially (all take `smiles=[list]`):

| Step | Tool | Filter Criteria |
|------|------|----------------|
| Physicochemical | `ADMETAI_predict_physicochemical_properties` | Lipinski <= 1, QED > 0.3, MW 200-600 |
| Bioavailability | `ADMETAI_predict_bioavailability` | Oral bioavailability > 0.3 |
| Toxicity | `ADMETAI_predict_toxicity` | AMES < 0.5, hERG < 0.5, DILI < 0.5 |
| CYP | `ADMETAI_predict_CYP_interactions` | Flag CYP3A4 inhibitors |
| Alerts | `ChEMBL_search_compound_structural_alerts` | No PAINS |

Include a filter funnel table in the report showing pass/fail counts at each stage.

---

## Phase 6: Candidate Docking & Prioritization

### Scoring Framework

| Dimension | Weight | Source |
|-----------|--------|--------|
| Docking confidence | 40% | NvidiaNIM_diffdock/boltz2 |
| ADMET score | 30% | ADMETAI predictions |
| Similarity to known active | 20% | Tanimoto coefficient |
| Novelty | 10% | Not in ChEMBL + novel scaffold bonus |

### Evidence Tiers

| Tier | Criteria |
|------|----------|
| T0 (4 stars) | Docking score > reference inhibitor |
| T1 (3 stars) | Experimental IC50/Ki < 100 nM |
| T2 (2 stars) | Docking within 5% of reference OR IC50 100-1000 nM |
| T3 (1 star) | >80% similarity to T1 compound |
| T4 (0 stars) | 70-80% similarity, scaffold match |
| T5 (empty) | Generated molecule, ADMET-passed, no docking |

Deliver top 20 candidates with: Rank, ID, SMILES, Docking score, ADMET score, overall score, source, evidence tier.

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
Docking:       NvidiaNIM_diffdock -> NvidiaNIM_boltz2 -> similarity-based scoring
Generation:    NvidiaNIM_genmol -> NvidiaNIM_molmim -> similarity search only
Literature:    PubMed -> EuropePMC (preprints) -> OpenAlex
GPCR data:     GPCRdb_get_protein -> GtoPdb_get_targets
```

---

## NVIDIA NIM Runtime Reference

| Tool | Runtime | Notes |
|------|---------|-------|
| `NvidiaNIM_alphafold2` | 5-15 min | Async, max ~2000 AA |
| `NvidiaNIM_esmfold` | ~30 sec | Max 1024 AA |
| `NvidiaNIM_diffdock` | ~1-2 min | Per ligand |
| `NvidiaNIM_boltz2` | ~2-5 min | End-to-end complex |
| `NvidiaNIM_genmol` | ~1-3 min | Depends on num_molecules |
| `NvidiaNIM_molmim` | ~1-2 min | Close analog generation |

Always check: `import os; nvidia_available = bool(os.environ.get("NVIDIA_API_KEY"))`

---

## Rate Limiting

| Database | Limit | Strategy |
|----------|-------|----------|
| ChEMBL | ~10 req/sec | Batch queries |
| PubChem | ~5 req/sec | Batch endpoints |
| ADMET-AI | No strict limit | Batch SMILES in lists |
| NVIDIA NIM | API key quota | Cache results |

For large expansions (>500 compounds): batch in chunks of 100, prioritize top candidates for docking.

---

## Reference Files

For detailed protocols, examples, and templates, see:

| File | Contents |
|------|----------|
| [WORKFLOW_DETAILS.md](./WORKFLOW_DETAILS.md) | Phase-by-phase procedures, code patterns, screening protocols, fallback chain details |
| [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) | Complete tool reference with parameters, usage examples, and fallback chains |
| [REPORT_TEMPLATE.md](./REPORT_TEMPLATE.md) | Report file template, evidence grading system, section formatting examples |
| [EXAMPLES.md](./EXAMPLES.md) | End-to-end workflow examples (EGFR, novel target, lead optimization, NVIDIA NIM) |
| [CHECKLIST.md](./CHECKLIST.md) | Pre-delivery verification checklist for report quality |
