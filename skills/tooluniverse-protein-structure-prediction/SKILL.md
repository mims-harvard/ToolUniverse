---
name: tooluniverse-protein-structure-prediction
description: Predict and analyze protein 3D structure from amino acid sequence using ESMFold and AlphaFold. Covers de novo structure prediction (ESMFold for sequences up to ~800 residues), AlphaFold model retrieval, quality assessment (pLDDT scores), experimental structure comparison (RCSB), variant structural impact (ProtVar), and sequence physicochemical property calculation (ProtParam). Use when asked to predict protein structure from sequence, assess structure quality, compare predictions to experimental structures, or evaluate how mutations affect protein structure.
---

# Protein Structure Prediction and Analysis

End-to-end workflow for protein structure prediction starting from a sequence or UniProt accession. Combines ESMFold de novo prediction, AlphaFold database retrieval, experimental structure benchmarking from RCSB, ProtVar variant impact assessment, and ProtParam sequence property calculation.

**KEY PRINCIPLES**:
1. **Sequence first** — obtain or verify the protein sequence before prediction
2. **ESMFold for fast de novo** — works directly on sequence (up to ~800 residues); no database lookup needed
3. **AlphaFold for reference** — retrieve precomputed AlphaFold model for comparison; use `qualifier` parameter (UniProt accession)
4. **Quality before interpretation** — always report pLDDT scores; do not interpret low-confidence regions as folded
5. **Experimental validation** — compare predictions to RCSB experimental structures when available
6. **ProtVar for variants** — use when the question involves mutations or SNVs affecting structure
7. **English-first queries** — use English protein names in all tool calls; respond in the user's language

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when users ask:
- "Predict the structure of this sequence: [FASTA]"
- "What does the AlphaFold model for [protein] look like?"
- "How confident is the AlphaFold prediction for [protein]?"
- "Is there an experimental structure for [protein] and how does it compare to AlphaFold?"
- "How does mutation [variant] affect the structure of [protein]?"
- "What are the physicochemical properties of [protein] sequence?"
- "Predict the structure of this novel protein" / "I have a new sequence, can you model it?"

**Not for** (use `tooluniverse-protein-structure-retrieval` instead): retrieval-only tasks where user provides a PDB ID or wants to browse experimental structures without prediction.

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **sequence** | Yes (for ESMFold) | Amino acid sequence (single-letter FASTA) | `MVLSPADKTNVK...` |
| **uniprot_id** | Yes (for AlphaFold) | UniProt accession | `P04637`, `P69905` |
| **variant** | No | Variant notation for structural impact | `P04637 R175H`, `TP53 R175H` |
| **max_length** | No | ESMFold limit: ~800 residues recommended | — |

---

## Workflow Overview

```
Phase 0: Input preparation (sequence retrieval if needed)
    |
Phase 1: Sequence properties (ProtParam_calculate)
    |
Phase 2: De novo prediction (ESMFold_predict_structure)
    |
Phase 3: AlphaFold reference (alphafold_get_prediction + alphafold_get_summary)
    |
Phase 4: Experimental structure comparison (RCSBAdvSearch_search_structures, RCSBData_get_entry)
    |
Phase 5: Variant structural impact (ProtVar_map_variant + ProtVar_get_function) [if variant provided]
    |
Phase 6: Quality synthesis and interpretation
```

---

## Phase 0: Input Preparation

**Objective**: Obtain or verify the protein sequence needed for ESMFold prediction.

### If sequence is already provided

Use it directly for `ESMFold_predict_structure`. Check length:
- 1-400 residues: full prediction, high confidence expected
- 400-800 residues: prediction supported, may be slower
- >800 residues: ESMFold may fail or produce lower quality; recommend using AlphaFold instead

### If only protein name or UniProt ID is provided

Retrieve sequence from `UniProt_get_entry_by_accession`:
- `accession`: UniProt accession
- Extract the `sequence.value` field from the response

**Note**: If only a name is given (not accession), first resolve with `UniProt_search` or `MyGene_query_genes` to get the UniProt accession, then fetch the sequence.

---

## Phase 1: Sequence Properties

**Objective**: Calculate physicochemical properties before prediction to contextualize results.

### Tools

**ProtParam_calculate**:
- `sequence`: amino acid sequence string (single-letter code)
- Returns: molecular weight, isoelectric point (pI), extinction coefficient, instability index, GRAVY score, amino acid composition

### Key Properties to Report

- **Molecular weight** — size context
- **Isoelectric point (pI)** — charge at neutral pH
- **Instability index** — >40 suggests unstable protein; affects prediction quality
- **GRAVY score** — hydrophobicity; >0 indicates membrane association tendency
- **Length** — determines ESMFold feasibility

---

## Phase 2: De Novo Structure Prediction (ESMFold)

**Objective**: Predict 3D structure from sequence using Meta's ESM-2 language model.

### Tools

**ESMFold_predict_structure**:
- `sequence`: amino acid sequence string
- Returns: predicted structure in PDB format, per-residue pLDDT confidence scores, pTM score (global fold confidence)

### Workflow

1. Call `ESMFold_predict_structure` with the sequence
2. Parse pLDDT scores:
   - Per-residue confidence array
   - Compute mean pLDDT over all residues
   - Identify low-confidence regions (pLDDT < 50)
3. Parse pTM score (predicted Template Modeling score) — overall fold quality
4. Record the PDB-format coordinate output for downstream visualization

### Quality Interpretation

| pLDDT Range | Interpretation | Reliability |
|-------------|---------------|-------------|
| >90 | Very high confidence | Equivalent to experimental quality |
| 70-90 | High confidence | Backbone reliable, side chains approximate |
| 50-70 | Low confidence | Potentially disordered or flexible region |
| <50 | Very low confidence | Likely intrinsically disordered; do not interpret |

| pTM Score | Fold Confidence |
|-----------|----------------|
| >0.8 | High confidence global fold |
| 0.5-0.8 | Moderate; some domains may be uncertain |
| <0.5 | Low global fold confidence |

### ESMFold vs AlphaFold

- ESMFold: faster, works directly on sequence, good for novel sequences, no database lookup
- AlphaFold: uses multiple sequence alignment (MSA); typically higher accuracy for well-conserved proteins
- Both predict single-chain monomer structures (not complexes in standard mode)

---

## Phase 3: AlphaFold Reference Model

**Objective**: Retrieve precomputed AlphaFold2 model for comparison and higher-accuracy reference.

### Tools

**alphafold_get_prediction**:
- `qualifier` (or alias `uniprot_id` / `uniprot_accession`): UniProt accession (e.g., `"P04637"`)
- Returns: AlphaFold model URL, pLDDT scores, model version

**alphafold_get_summary**:
- `qualifier` (or alias `uniprot_id` / `uniprot_accession`): UniProt accession
- Returns: prediction summary including confidence metrics, model quality

**alphafold_get_annotations** (optional):
- `qualifier`: UniProt accession
- Returns: functional region annotations overlaid on structure (binding sites, active sites)

### Workflow

1. Call `alphafold_get_prediction` and `alphafold_get_summary`
2. Extract mean pLDDT and per-residue confidence
3. Compare ESMFold vs AlphaFold pLDDT profiles:
   - Do they agree on low-confidence regions?
   - Large differences may indicate disordered/flexible regions
4. Note the AlphaFold model version (v1/v2/v3/v4)

### Decision Logic

- If no UniProt accession available: skip AlphaFold; use ESMFold only
- If protein is a complex or has multiple chains: note that both tools predict single chains
- If AlphaFold confidence is very high (mean pLDDT > 85): recommend using AlphaFold as primary reference

---

## Phase 4: Experimental Structure Comparison

**Objective**: Check whether experimental structures exist in PDB and how predictions compare.

### Tools

**RCSBAdvSearch_search_structures** (search by protein/gene name):
- `query`: protein name or gene symbol
- `limit`: number of results (default 10)
- Returns: list of PDB entries with resolution, method, title

**RCSBData_get_entry** (details for a specific PDB ID):
- `pdb_id`: 4-character PDB identifier
- Returns: metadata including method, resolution, chains, ligands, release date

### Workflow

1. Search for experimental structures using protein name
2. Filter for highest-resolution X-ray or cryo-EM structures
3. For the best experimental structure, retrieve entry details
4. Compare to predictions:
   - If experimental structure exists: note coverage, resolution, method
   - Flag regions predicted with high confidence but missing from experimental structure (could be disordered in crystal)
   - Flag regions in experimental structure with low pLDDT (may be crystal artifacts vs true fold)

### Fallback

- If RCSB search returns no results: note "no experimental structure found in PDB" and proceed with predictions only
- Suggest checking PDBe as secondary source

---

## Phase 5: Variant Structural Impact (When Variant Provided)

**Objective**: Assess how a specific amino acid substitution affects the predicted structure.

### Tools

**ProtVar_map_variant**:
- `variant`: string notation like `"P04637 R175H"` or HGVS notation
- Returns: mapped residue position, genomic coordinates, consequence type, variant accession

**ProtVar_get_function**:
- `accession`: UniProt accession
- `position`: integer residue position
- `variant_aa`: mutant amino acid (single letter)
- Returns: functional annotations — domain, active site, binding site, conservation score, clinical significance, predicted pathogenicity

### Workflow

1. Call `ProtVar_map_variant` to resolve the variant and confirm position
2. Call `ProtVar_get_function` with wild-type position to get domain context
3. Assess: is the mutated residue in a critical structural region?
   - Active site / binding site: likely high functional impact
   - Buried hydrophobic core: likely destabilizes fold
   - Surface-exposed, disordered region: less likely to affect overall fold
4. Compare pLDDT at that position (from ESMFold/AlphaFold) to assess if the region is well-predicted

### Evidence Grading for Variant Impact

| Tier | Evidence |
|------|----------|
| T1 | Clinical/functional data for this exact variant (from ProtVar) |
| T2 | Variant at experimentally characterized active site or binding interface |
| T3 | Computational pathogenicity prediction (PolyPhen, SIFT from ProtVar) |
| T4 | Position in predicted structured region only |

---

## Phase 6: Quality Synthesis and Report

### Required Report Sections

1. **Protein summary** — name, length, pI, stability index (from ProtParam)
2. **Structure prediction summary table**:
   | Method | Mean pLDDT | pTM/Global Score | Coverage | Notes |
   |--------|-----------|------------------|----------|-------|
   | ESMFold | X.X | X.X | 100% (full seq) | — |
   | AlphaFold | X.X | — | 100% | version vN |
   | Experimental (best) | N/A | N/A | XX% | PDB: XXXX, Xray, X.X A |

3. **Confidence map** — regions of high vs low confidence; highlight disordered regions
4. **Experimental structure comparison** — does PDB have coverage? How does prediction align?
5. **Variant impact** (if applicable) — domain context, pathogenicity, structural consequence
6. **Recommendations**:
   - Which model to use for downstream applications (docking, design, etc.)
   - Regions to treat as unreliable
   - Suggested experimental validation approaches

### Quality Minimums

- Report mean pLDDT for both ESMFold and AlphaFold
- Identify all low-confidence regions (pLDDT < 50) by residue range
- Check PDB for experimental structures (at minimum 1 search query)
- Compare at least 2 prediction sources when UniProt accession is available

---

## Tool Parameter Reference

| Tool | Key Parameter | Notes |
|------|--------------|-------|
| `ESMFold_predict_structure` | `sequence` | Raw amino acid string, no spaces, no FASTA header |
| `alphafold_get_prediction` | `qualifier` or `uniprot_id` | UniProt accession (e.g., `"P04637"`) |
| `alphafold_get_summary` | `qualifier` or `uniprot_id` | Same UniProt accession |
| `ProtParam_calculate` | `sequence` | Same sequence string |
| `ProtVar_map_variant` | `variant` | Format: `"<UniProt_ID> <AA><pos><AA>"` e.g., `"P04637 R175H"` |
| `ProtVar_get_function` | `position` | Integer residue number |

---

## Fallback Strategies

| Situation | Fallback |
|-----------|----------|
| ESMFold fails (sequence too long > 800 aa) | Use AlphaFold model only; note length limitation |
| AlphaFold no entry for UniProt ID | Use ESMFold prediction only |
| RCSB search returns no results | Note no experimental structure; proceed with predictions |
| No UniProt accession available | Use ESMFold from raw sequence; skip AlphaFold |
| ProtVar variant not found | Manually assess position from domain annotation in Phase 4 |

---

## Databases Integrated

| Database | Coverage | What it provides |
|----------|----------|-----------------|
| **ESMFold** | Any protein sequence (up to ~800 aa) | De novo structure prediction from sequence alone |
| **AlphaFold DB** | UniProt reviewed proteins (>200M entries) | Precomputed predictions with per-residue pLDDT |
| **RCSB PDB** | ~220,000 experimental structures | Ground-truth experimental coordinates for comparison |
| **ProtVar** | All UniProt proteins | Variant impact, domain context, clinical annotations |
| **ProtParam** | Any sequence | Physicochemical sequence properties |

---

## Limitations

- **ESMFold length limit**: sequences longer than ~800 residues may fail or have reduced quality
- **Single-chain only**: both ESMFold and standard AlphaFold predict monomers; complex prediction requires AlphaFold-Multimer (not available via these tools)
- **Disordered regions**: pLDDT < 50 indicates intrinsically disordered regions (IDRs) — do not interpret these as structured
- **No dynamics**: predicted structures are static; do not represent conformational flexibility or allosteric changes
- **Novel folds**: ESMFold may struggle with proteins having no homologs in training data
- **AlphaFold DB coverage**: some recently characterized proteins may not yet be in the AlphaFold database
