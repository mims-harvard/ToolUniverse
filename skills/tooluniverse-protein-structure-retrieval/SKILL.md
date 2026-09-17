---
name: tooluniverse-protein-structure-retrieval
description: Protein structure retrieval from RCSB PDB, PDBe, AlphaFold, SWISS-MODEL, 3D-Beacons (cross-provider structure aggregator), and PDB-REDO (re-refined X-ray structures), with disambiguation, quality assessment (resolution, R-factor, pLDDT, coverage), and metadata. Distinguishes high-quality experimental (X-ray under 2 Angstrom) vs predicted vs homology-model vs medium-quality structures. Use for fetching protein structures, structure-quality comparison, batch model-availability checks across a gene list, checking every structure provider at once, and selecting structures for drug design or modeling.
disable-model-invocation: true
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
| No usable AlphaFold model (multi-domain protein, low pLDDT for a specific range) | `SwissModel_get_models` filtered to that residue `range` — the repository holds per-domain homology models AlphaFold's single full-length model may not resolve well |

### SWISS-MODEL Repository (Homology Models + Re-Indexed Experimental Structures)

Use `SwissModel_get_summary(uniprot_id=...)` for a one-call "does a homology model exist and how good is it" check — it returns the single best-coverage entry across everything SWISS-MODEL has for that accession. **Important**: the "best" entry it returns can be an experimental PDB structure re-indexed by UniProt residue range (verified live: for EGFR/P00533, `get_summary`'s `best_model` was an X-RAY DIFFRACTION entry, not a homology model) — check `best_model.method`, don't assume "best model" means "computed homology model."

To get genuine computed homology models specifically, call `SwissModel_get_models(uniprot_id=..., provider="swissmodel")` — `provider="pdb"` isolates the re-indexed experimental entries instead, and omitting `provider` returns both. Other filters: `range` (residue window, useful for large multi-domain proteins where one region has poor AlphaFold confidence) and `template` (a specific PDB template ID).

`SwissModel_download_pdb(uniprot_id=..., provider=...)` fetches the actual ATOM/HETATM coordinate text (not just a URL) for downstream docking/visualization — same filters as `get_models`. `SwissModel_get_models_batch(uniprot_ids=[...])` resolves up to 250 accessions in one call, useful when checking model availability across a gene list before deciding which proteins need AlphaFold/ESMFold instead.

**Quality-metric caveat (verified live)**: `qmean_global`/`qmean_z_score` were `null` on every real homology-model entry tested (EGFR's 2 SWISS-MODEL models) — QMEAN is frequently absent, not a metric you can always rely on. Use `coverage` (fraction of the UniProt sequence the model spans), `template` (which PDB structure it was built from), and `method` as the more consistently populated quality signals; treat QMEAN as a bonus when present, not a required check.

**When to reach for SWISS-MODEL vs. AlphaFold**: AlphaFold (above) is the default single-model reference for any UniProt-reviewed protein. Reach for SWISS-MODEL specifically when (a) you need multiple alternative models built from different templates to compare, (b) a large protein's AlphaFold confidence is poor in one region and a domain-specific homology model with better template coverage might do better there, or (c) you're checking many accessions at once and want batch lookup rather than N separate AlphaFold calls.

### 3D-Beacons (Meta-Aggregator Across All Structure Providers)

`ThreeDBeacons_get_structure_summary(accession=...)` is the best FIRST call when you don't yet know which structure source has the most/best coverage for a UniProt accession — it queries PDBe, SWISS-MODEL, AlphaFold DB, AlphaFill, and ModelArchive simultaneously and returns a `by_provider` count plus a `by_category` breakdown (`EXPERIMENTALLY DETERMINED` / `TEMPLATE-BASED` / `AB-INITIO`). **Real example** (verified live): EGFR/P00533 → `total_structures: 426`, `by_provider: {"PDBe": 412, "SWISS-MODEL": 2, "AlphaFold DB": 6, "AlphaFill": 1, "ModelArchive": 5}` — confirming this protein is overwhelmingly covered by experimental structures already, and that the 2 SWISS-MODEL entries (Phase above) are a small fraction of what's actually available; don't stop at SWISS-MODEL's own listing if 3D-Beacons shows a much richer PDBe count.

`ThreeDBeacons_get_structures(accession=..., category=..., provider=..., max_results=...)` returns the individual structure/model records (not just counts) — filter by `category` or `provider` to narrow down before fetching detail elsewhere. `ThreeDBeacons_get_annotations(accession=..., type=..., provider=...)` maps residue-level annotations (e.g. `type="DOMAIN"`, `type="BINDING"`) onto the protein's 3D models — real example: BRCA1/P38398 with `type="DOMAIN"` returns real domain-to-residue mappings, while a `type="BINDING"` query on P04637 can legitimately return zero annotations (`annotation_count: 0`) — an empty result here means no such annotation exists in the aggregated sources, not a broken call.

**Workflow**: use `ThreeDBeacons_get_structure_summary` as the first orientation step for any UniProt accession, before deciding whether to drill into PDBe/RCSB (Phase 2), AlphaFold, or SWISS-MODEL specifically.

### PDB-REDO (Re-Refined Experimental Structures)

PDB-REDO automatically re-refines every X-ray PDB entry with current software/parameters, often improving on the original deposition's refinement quality. `PDB_REDO_get_structure_quality(pdb_id=...)` returns detailed refinement metrics (unit cell axes, B-factors, real-space/working correlation coefficients `CCFFIN`/`CCWFIN`, resolution `DATARESH`, completeness) for the re-refined structure — real example (verified live): PDB `4hjo` (an EGFR structure) → `DATARESH: 2.75`, `CCWFIN: 0.93`, `COMPLETED: 96.9`. `PDB_REDO_get_version_info(pdb_id=...)` returns re-refinement provenance/versioning metadata for the same entry.

**When to use**: prefer PDB-REDO's re-refined metrics over the original PDB deposition's stated resolution/R-factors when precision matters for downstream drug-design decisions — re-refinement can meaningfully change R-free and even correct minor model errors from the original deposition.

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

**PDBe**: `pdbe_get_entry_summary` (overview), `pdbe_get_entry_molecules` (entities), `pdbe_get_entry_experiment` (experimental), `PDBe_KB_get_ligand_sites` (pockets)

**AlphaFold**: `alphafold_get_prediction` (get prediction), `alphafold_get_summary` (search)

**SWISS-MODEL**: `SwissModel_get_summary` (best available model, single call), `SwissModel_get_models` (list all models, filterable by `range`/`provider`/`template`), `SwissModel_download_pdb` (actual coordinate text), `SwissModel_get_models_batch` (up to 250 UniProt accessions in one call)

**3D-Beacons**: `ThreeDBeacons_get_structure_summary` (cross-provider counts, best first call), `ThreeDBeacons_get_structures` (individual structure/model records, filterable by `category`/`provider`), `ThreeDBeacons_get_annotations` (residue-level domain/binding annotations mapped onto 3D models)

**PDB-REDO**: `PDB_REDO_get_structure_quality` (re-refined X-ray metrics), `PDB_REDO_get_version_info` (re-refinement provenance)
