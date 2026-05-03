---
name: tooluniverse-electron-microscopy
description: Search and analyze cryo-EM maps, single particle structures, tomography datasets, and raw micrograph data from EMDB, EMPIAR, and CryoET Data Portal. Cross-reference with PDB structures and AlphaFold predictions. Use for cryo-EM map discovery, structure fitting analysis, raw data access, and tomography exploration.
---

# Electron Microscopy Structure Analysis

Pipeline for discovering and analyzing electron microscopy data across the full resolution spectrum: from 3D density maps (EMDB) to fitted atomic models (PDB), raw micrograph datasets (EMPIAR), and cryo-electron tomography volumes (CryoET Data Portal). Connects EM data to structural biology context via PDB and AlphaFold.

**Guiding principles**:
1. **Resolution awareness** -- always report and interpret map resolution; sub-4A enables atomic modeling, 4-8A enables domain fitting, >8A is shape-level
2. **Map before model** -- the density map is the primary experimental data; fitted models are interpretations
3. **Method matters** -- single particle analysis, tomography, 2D crystallography, and helical reconstruction have different strengths and limitations
4. **Raw data value** -- EMPIAR raw data enables reprocessing with newer algorithms; always note availability
5. **Cross-reference structures** -- connect EMDB maps to PDB entries and AlphaFold predictions for completeness
6. **English-first queries** -- use English terms in tool calls

EM resolution determines what you can see. TEM resolves individual protein complexes (~2nm). Cryo-EM achieves near-atomic resolution (<4Å) for large complexes. SEM shows surface topology. Choose the right EM modality for the question.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Typical triggers:
- "Find cryo-EM structures of [protein/complex]"
- "What EMDB maps are available for [target]?"
- "Get raw micrograph data for [structure]"
- "Find tomography datasets for [organelle/cell type]"
- "What is the resolution of [EMDB entry]?"
- "Cross-reference this EM map with PDB models"
- "Find cryo-ET datasets for [sample]"

**Not this skill**: For X-ray crystallography or NMR structures, use PDB search tools directly. For protein structure prediction, use `tooluniverse-protein-structure`.

---

## Core Databases

| Database | Content | Best For |
|----------|---------|----------|
| **EMDB** | 3D EM density maps (>40K entries) | Finding processed maps, resolution data, fitting info |
| **EMPIAR** | Raw micrograph/tilt series datasets | Accessing original image data for reprocessing |
| **CryoET Data Portal** | Cryo-electron tomography data | Tomographic volumes, cellular context, in-situ structures |
| **PDB (RCSB)** | Atomic models fitted to EM maps | Structural models derived from EM data |
| **AlphaFold** | AI-predicted protein structures | Complementary models when EM resolution is limited |

---

## Workflow Overview

```
Phase 0: Query Parsing
  Identify target protein/complex, method preference, resolution needs
    |
Phase 1: Map & Image Search (EMDB)
  Find EM density maps, resolution, method, sample details
    |
Phase 2: Structure Fitting (EMDB + PDB)
  Identify fitted atomic models, fitting quality
    |
Phase 3: Raw Data Access (EMPIAR)
  Find raw micrographs, tilt series, particle stacks
    |
Phase 4: Tomography (CryoET Data Portal)
  Search cryo-ET datasets, reconstructed volumes
    |
Phase 5: Cross-Reference & Context (PDB + AlphaFold)
  Connect to atomic models, predicted structures, literature
    |
Phase 6: Report Synthesis
  Integrated EM data landscape for the target
```

---

## Phase Details

### Phase 0: Query Parsing

Identify from the user's request:
- **Target**: protein name, complex name, or organism
- **Method preference**: single particle, tomography, micro-ED, helical
- **Resolution needs**: atomic modeling (<4A), domain fitting (4-8A), shape (>8A)
- **Data type**: processed maps, raw data, fitted models, or all

### Phase 1: Map & Image Search (EMDB)

**Objective**: Find EM density maps matching the query.

**Tools**:
- `EMDB_search_structures` -- search EMDB by keyword, organism, resolution
  - Input: `query` (search term), optional `resolution_min`, `resolution_max`, `method`, `limit`
  - Output: entries with EMDB ID, title, resolution, method, sample
- `EMDB_get_structure` -- get full details for an EMDB entry
  - Input: `emdb_id` (e.g., "EMD-1234")
  - Output: map details, resolution, sample, processing info, citations
- `EMDB_get_map_info` -- get map-specific info (resolution, contour, dimensions)
  - Input: `emdb_id`
- `EMDB_get_sample_info` -- get sample preparation details
  - Input: `emdb_id`

**Workflow**:
1. Search EMDB for the target protein/complex
2. Sort results by resolution (best first)
3. For top entries, get full details including sample preparation and processing
4. Note the EM method used (single particle, tomography, helical, etc.)
5. Record associated PDB and EMPIAR accessions

**Resolution interpretation**:
- < 2.5A: near-atomic; side chains visible
- 2.5-4.0A: atomic; backbone and large side chains traceable
- 4.0-8.0A: domain level; secondary structure elements visible
- > 8.0A: shape; overall architecture only

### Phase 2: Structure Fitting (EMDB + PDB)

**Objective**: Find atomic models fitted into EM maps and assess fitting quality.

**Tools**:
- `EMDB_get_validation` -- get fitting/validation data for an EMDB entry
  - Input: `emdb_id`
  - Output: fitted PDB models, fitting statistics, validation scores
- `RCSBData_get_entry` -- get PDB entry details
  - Input: `entry_id` (PDB ID)
  - Output: structure details, resolution, method, citation
- `RCSBAdvSearch_search_structures` -- advanced PDB search
  - Input: `query` (search term), optional `experimental_method`, `resolution_max`, `limit`
  - Output: PDB entries matching criteria

**Workflow**:
1. For each EMDB entry from Phase 1, check for fitted atomic models
2. Get fitting statistics (cross-correlation, real-space R-factor if available)
3. Retrieve the PDB entry for structural details
4. If no model is fitted, search PDB for related structures by name

**Fitting quality indicators**:
- Cross-correlation coefficient > 0.7 suggests reasonable fit
- Multiple independently fitted models increase confidence
- Map-model FSC consistency check validates the fit

### Phase 3: Raw Data Access (EMPIAR)

**Objective**: Locate raw micrograph data for potential reprocessing.

**Tools**:
- `EMPIAR_search_entries` -- search EMPIAR archive
  - Input: `query` (search term), optional `limit`
  - Output: entries with EMPIAR ID, title, data type, size
- `EMPIAR_get_entry` -- get detailed entry information
  - Input: `empiar_id` (e.g., "EMPIAR-10028")
  - Output: data description, file formats, associated EMDB entries, download links

**Workflow**:
1. Search EMPIAR for entries related to the target
2. Cross-reference with EMDB entries found in Phase 1 (many EMDB entries link to EMPIAR)
3. Note data types: micrographs, particle stacks, tilt series, gain references
4. Record dataset size (can be 100s of GB to TBs)

**Data types in EMPIAR**:
- **Micrographs**: raw detector frames or motion-corrected images
- **Particle stacks**: extracted particle images
- **Tilt series**: serial images at different tilt angles (for tomography)
- **Reconstructed volumes**: 3D volumes from tomographic reconstruction

### Phase 4: Tomography (CryoET Data Portal)

**Objective**: Find cryo-electron tomography datasets for cellular and in-situ structural biology.

**Tools**:
- `CryoET_list_datasets` -- search CryoET Data Portal
  - Input: `query` (search term), optional `organism`, `limit`
  - Output: datasets with ID, title, organism, sample type
- `CryoET_get_dataset` -- get dataset details
  - Input: `dataset_id`
  - Output: sample details, tilt series parameters, tomogram info
- `CryoET_list_runs` -- search individual tomography runs
  - Input: `dataset_id` or `query`, optional `limit`
  - Output: run details, tilt parameters, voxel spacing

**Workflow**:
1. Search CryoET Data Portal for the target organism/structure
2. Get dataset details including sample preparation and imaging parameters
3. Explore individual runs for tilt series specifications
4. Note voxel spacing and tomogram dimensions

**Tomography vs single particle**: Tomography preserves cellular context (in situ) but typically achieves lower resolution. Single particle gives higher resolution but requires purified samples.

### Phase 5: Cross-Reference & Context

**Objective**: Connect EM data to broader structural biology context.

**Tools**:
- `alphafold_get_prediction` -- get AlphaFold predicted structure
  - Input: `qualifier` (UniProt accession)
  - Output: predicted structure coordinates, confidence scores (pLDDT)
- `PubMed_search_articles` -- find publications describing the EM work
  - Input: `query` (search term), optional `limit`
  - Output: articles with title, abstract, PMID

**Workflow**:
1. For proteins with EM structures, get AlphaFold predictions for comparison
2. Note regions where AlphaFold confidence is low (pLDDT < 70) -- these may be flexible and harder to resolve by EM
3. Search PubMed for methodological papers and biological insights from the EM studies
4. Cross-reference EMDB/PDB/EMPIAR accessions in publications

### Phase 6: Interpretation & Recommendations

Don't just list maps — help the user choose the RIGHT map for their purpose.

**Decision matrix: Which map should I use?**

| Purpose | Best Resolution | Method | Priority Criteria |
|---------|----------------|--------|-------------------|
| **Atomic model building** | < 3.5A | Single particle | Highest resolution with fitted PDB model |
| **Drug binding site analysis** | < 3.0A | Single particle | Must resolve side chains in binding pocket |
| **Domain architecture** | 4-8A | Single particle or subtomogram avg | Large complexes where domains need fitting |
| **Conformational states** | < 4.5A | Single particle (multiple classes) | Look for entries with multiple maps from same dataset |
| **Cellular context** | 15-40A | Cryo-ET | Tomographic datasets showing in-situ arrangement |
| **Reprocessing** | Any | Any | Must have EMPIAR raw data; prefer recent datasets (better detectors) |

**Quality assessment checklist**:
- Resolution reported is the "gold standard" FSC 0.143 cutoff? (some older entries use 0.5 cutoff — inflates resolution)
- Map sharpened appropriately? (over-sharpened maps can look better but contain artifacts)
- Fitting statistics available? (cross-correlation > 0.7 is acceptable)
- Multiple maps from same sample? (suggests conformational heterogeneity — important for drug design)

**Resolution trend analysis**: If multiple maps exist over time, note the resolution trajectory. Improvement from 6A (2015) to 2.8A (2023) suggests the sample is amenable to high-resolution single particle analysis with modern hardware.

### Phase 7: Report Synthesis

Assemble findings into an actionable report:

1. **Target Overview** -- protein/complex identity, biological significance
2. **EM Map Landscape** -- available maps with resolution, method, and year
3. **Best Available Structures** -- highest resolution maps with fitted models, with quality assessment
4. **Recommendation** -- which specific map/model to use for the user's purpose (with reasoning)
5. **Raw Data Availability** -- EMPIAR datasets for reprocessing, with dataset sizes
6. **Tomography Data** -- cellular context datasets if available
7. **Structural Context** -- comparison with X-ray/NMR/AlphaFold structures
8. **Key Publications** -- methods papers, biological discoveries
9. **Data Gaps** -- missing conformational states, unresolved regions, need for higher resolution

---

## Common Analysis Patterns

| Pattern | Description | Key Phases |
|---------|-------------|------------|
| **Structure Discovery** | Find all EM data for a protein | 0, 1, 2, 5 |
| **Reprocessing Prep** | Find raw data for re-analysis | 0, 1, 3 |
| **Tomography Survey** | Explore in-situ structural data | 0, 4 |
| **Resolution Comparison** | Track resolution improvements over time | 0, 1, 2 |
| **Map-Model Validation** | Assess quality of fitted atomic models | 0, 1, 2, 5 |

---

## Edge Cases & Fallbacks

- **No EMDB entries**: The complex may only have X-ray or NMR structures. Search PDB via `RCSBAdvSearch_search_structures` with method filter
- **EMDB entry without PDB model**: Common for lower-resolution maps. Note the gap; suggest AlphaFold for approximate modeling
- **No EMPIAR data**: Raw data deposition is newer and not universal. The processed map in EMDB may be the only available data
- **Large complexes**: Ribosomes, viruses, etc. may have hundreds of EMDB entries. Use resolution filters to narrow results

---

## Limitations

- **No map visualization**: This skill retrieves metadata and statistics, not 3D renderings. Use UCSF ChimeraX or IMOD for visualization
- **No reprocessing**: Finding raw data is supported; actual cryo-EM data processing requires specialized software (RELION, cryoSPARC)
- **Resolution is not accuracy**: A 3A map processed with errors may be less reliable than a well-validated 4A map. Fitting statistics matter
- **Deposition lag**: Structures may be published months before EMDB deposition, or vice versa
