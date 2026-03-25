---
name: tooluniverse-protein-modification-analysis
description: Analyze post-translational modifications (PTMs) of proteins — modification sites, types, proteoforms, functional effects at PTM sites, and PTM-dependent protein interactions. Integrates iPTMnet, ProtVar, UniProt, and STRING databases. Use when asked about protein phosphorylation, ubiquitination, acetylation, glycosylation, methylation, SUMOylation, or other PTMs; proteoform diversity; PTM-regulated interactions; or functional impact of PTM sites.
---

# Protein Post-Translational Modification Analysis

Comprehensive analysis of protein PTMs using iPTMnet as the primary source, augmented with ProtVar functional context, UniProt baseline annotation, and STRING interaction data. Covers PTM sites, modification types, proteoform diversity, PTM-dependent protein-protein interactions, and functional interpretation.

**KEY PRINCIPLES**:
1. **Disambiguation first** — resolve protein name to UniProt accession before any iPTMnet calls
2. **iPTMnet is SOAP-style** — every call requires an `operation` parameter
3. **Site context from ProtVar** — use `ProtVar_get_function` for domain/active-site context at specific PTM residues
4. **Evidence-graded** — distinguish experimentally validated PTMs (T1) from predicted (T4)
5. **Source-referenced** — cite tool and database for every claim
6. **English-first queries** — use English terms in all tool calls; respond in the user's language

---

## When to Use

Apply when users ask:
- "What PTMs does [protein] have?" / "Where is [protein] phosphorylated?"
- "What are the functional consequences of [protein] ubiquitination at K48?"
- "Which proteins interact with [protein] in a PTM-dependent manner?"
- "What proteoforms exist for [protein]?"
- "How does phosphorylation regulate [protein] activity?"
- "What PTM sites are in the kinase domain of [protein]?"

---

## Input Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| **protein** | Yes | Protein name, gene symbol, or UniProt ID | `TP53`, `P04637`, `EGFR` |
| **ptm_type** | No | Filter for specific PTM type | `phosphorylation`, `ubiquitination`, `acetylation` |
| **site** | No | Specific residue position or site | `S15`, `K48`, `175` |

---

## Workflow Overview

```
Phase 0: Protein Disambiguation (UniProt accession resolution)
    |
Phase 1: PTM Site Inventory (iPTMnet_get_ptm_sites)
    |
Phase 2: Proteoform Analysis (iPTMnet_get_proteoforms)
    |
Phase 3: PTM-Dependent Interactions (iPTMnet_get_ptm_ppi)
    |
Phase 4: Functional Context (ProtVar_get_function at key sites)
    |
Phase 4b: Linear Motif Context (ELM_get_instances for SLiM overlap with PTM sites)
    |
Phase 4c: Experimental Data Discovery (MassIVE/ProteomeXchange for PTM datasets)
    |
Phase 5: Synthesis & Report
```

---

## Phase 0: Protein Disambiguation

**Always first** — iPTMnet requires UniProt accession IDs, not gene symbols.

### Tools

**iPTMnet_search**:
- `operation`: `"search"` (required)
- `search_term`: protein name or gene symbol (e.g., `"TP53"`)
- `role`: `"Substrate"` to find PTM targets (default), or `"Enzyme"` for kinases/ligases
- `max_results`: integer (default 10)
- Returns: list of matching proteins with UniProt IDs, names, organism

**UniProt_get_entry** (alternative disambiguation):
- `accession`: UniProt accession
- Returns: full protein entry with cross-references, function, domains

### Decision Logic

1. If user provides UniProt accession directly (e.g., `P04637`) — use it directly
2. If user provides gene symbol — call `iPTMnet_search` with `operation="search"`, `search_term=gene_symbol`
3. If multiple hits — select the human (Homo sapiens) entry; note others
4. If no hits — try `UniProt_search` with gene/protein name, then use accession for iPTMnet calls

---

## Phase 1: PTM Site Inventory

**Objective**: Retrieve all known PTM sites, modification types, enzymes, and evidence sources.

### Tools

**iPTMnet_get_ptm_sites**:
- `operation`: `"get_ptm_sites"` (required)
- `uniprot_id`: UniProt accession (e.g., `"P04637"`)
- Returns: list of PTM sites with position, residue, modification type, enzyme, evidence type, source database

### Workflow

1. Call `iPTMnet_get_ptm_sites` with the resolved UniProt accession
2. Group results by modification type (phosphorylation, ubiquitination, acetylation, etc.)
3. Count sites per modification type
4. Identify the most-studied sites (highest evidence count)
5. If `ptm_type` filter requested — filter to matching modification type
6. If `site` requested — extract the specific site entry

### Report Format for PTM Sites

For each modification type, table of:
- Position + residue (e.g., S15, K48)
- Modification type
- Enzyme (kinase, E3 ligase, acetyltransferase, etc.) if known
- Evidence type (experimental / predicted)
- Source databases

### Decision Logic

- **Empty results**: protein may not be in iPTMnet; note that and proceed with UniProt PTM annotations
- **Fallback**: `UniProt_get_entry` returns PTM/processing section with experimentally annotated sites

---

## Phase 2: Proteoform Analysis

**Objective**: Characterize distinct proteoforms arising from PTM combinations.

### Tools

**iPTMnet_get_proteoforms**:
- `operation`: `"get_proteoforms"` (required)
- `uniprot_id`: UniProt accession
- Returns: proteoform records — each proteoform is a specific combination of PTMs; includes position, modification, source

### Workflow

1. Call `iPTMnet_get_proteoforms`
2. Count total distinct proteoforms
3. Identify unique PTM combinations
4. Highlight proteoforms with functional annotations
5. Note if proteoforms have different interaction partners (connects to Phase 3)

### Decision Logic

- **Many proteoforms** (>20): focus on those with functional or disease annotations
- **Few or no proteoforms**: note that proteoform data is limited; single-site PTMs more relevant

---

## Phase 3: PTM-Dependent Protein Interactions

**Objective**: Identify protein interactions that are mediated or regulated by PTMs.

### Tools

**iPTMnet_get_ptm_ppi**:
- `operation`: `"get_ptm_ppi"` (required)
- `uniprot_id`: UniProt accession
- Returns: PTM-dependent PPI records — interacting protein, PTM site, modification type, interaction effect (enables/disrupts), source

**STRING_get_interaction_partners** (supplemental general PPI context):
- `identifiers`: gene symbol or STRING ID (string, not array)
- `species`: 9606 for human
- `required_score`: 700 for high confidence
- Returns: interaction network with confidence scores

### Workflow

1. Call `iPTMnet_get_ptm_ppi` to get PTM-specific interactions
2. For each PTM-PPI: record the PTM site, interacting protein, and regulatory effect
3. Optionally call `STRING_get_interaction_partners` for broader PPI context
4. Cross-reference: which general STRING partners also appear in PTM-PPI list?

### Report Format

- Table: PTM site | Interacting protein | Effect (enables/disrupts) | Evidence
- Highlight interactions with clinical or mechanistic significance

---

## Phase 4: Functional Context at PTM Sites

**Objective**: Interpret PTM sites in their structural and functional context using ProtVar.

### Tools

**ProtVar_get_function**:
- `accession`: UniProt accession
- `position`: residue position (integer)
- `variant_aa`: amino acid for variant context (can use wild-type AA for domain lookup)
- Returns: functional annotations — domain, active site, binding site, conservation score, clinical significance

**ProtVar_map_variant** (alternative, for HGVS or protein variant notation):
- `variant`: string like `"P04637 S15A"` or HGVS notation
- Returns: mapped position, genomic coordinates, consequence

### Workflow

1. Select the top 5-10 most important PTM sites (highest evidence, known functional role)
2. For each: call `ProtVar_get_function` with the UniProt accession and site position
3. Extract: which protein domain does the site fall in? Is it at an active site, binding site, or interface?
4. Grade the functional importance: active-site PTM > domain-core PTM > disordered region PTM

### Evidence Grading for PTM Sites

| Evidence Tier | Criteria |
|--------------|----------|
| T1 | PTM at experimentally validated active site or binding interface with functional data |
| T2 | PTM in structured domain with ProtVar domain annotation |
| T3 | PTM with only correlation data (e.g., mass spec detection) |
| T4 | Predicted PTM site without experimental validation |

---

## Phase 4b: Linear Motif Context (ELM)

**Objective**: Identify short linear motifs (SLiMs) that overlap with or contextualize PTM sites. MOD-type motifs in ELM correspond to modification sites (phosphorylation, ubiquitination, etc.), while DEG-type motifs indicate degradation signals that may be PTM-regulated.

### Tools

**ELM_get_instances** (SOAP-style -- requires `operation`):
- `operation`: `"get_instances"` (required)
- `uniprot_id`: UniProt accession (e.g., `"P04637"`)
- `motif_type`: Optional filter -- `MOD` (modification sites), `DEG` (degradation/degrons), `CLV` (cleavage), `DOC` (docking), `LIG` (ligand binding), `TRG` (targeting)
- Returns: List of motif instances with ELM identifiers, positions (start/end), functional types, experimental methods, PubMed references

**ELM_list_classes** (SOAP-style -- requires `operation`):
- `operation`: `"list_classes"` (required)
- `motif_type`: Optional type filter
- `query`: Optional keyword (e.g., `"kinase"`, `"ubiquitin"`, `"phosphorylation"`)
- `max_results`: Integer (default 50, max 400)
- Returns: Motif class definitions with regex patterns and descriptions

### Workflow

1. Call `ELM_get_instances` with `operation="get_instances"`, `uniprot_id=<accession>`, and optionally `motif_type="MOD"` for modification-related motifs
2. Cross-reference ELM motif positions with PTM sites from Phase 1 (iPTMnet):
   - PTM at ELM MOD motif = experimentally validated modification context
   - PTM at ELM DEG motif = potential degradation signal
   - PTM at ELM DOC motif = docking-dependent modification
3. For motifs of interest, use `ELM_list_classes` with the ELM identifier to get the motif regex pattern and biological description
4. Report which PTM sites fall within known linear motif contexts

### Decision Logic

- **Many MOD motifs overlap with PTM sites**: Strong validation of PTM function
- **PTM at DEG motif**: Flag as potential degradation regulation (e.g., phosphodegron)
- **No ELM data**: Note that ELM coverage is biased toward well-studied proteins; proceed with Phase 5

---

## Phase 4c: Experimental Data Discovery (MassIVE/ProteomeXchange)

**Objective**: Find publicly available proteomics datasets that contain experimental evidence for PTMs on the protein of interest.

### Tools

**MassIVE_search_datasets**:
- `page_size`: Number of results (max 100)
- `species`: NCBI taxonomy ID (e.g., `"9606"` for human)
- Returns: Dataset list with accessions, titles, summaries, instruments, keywords

**MassIVE_get_dataset**:
- `accession`: Dataset accession (MSV or PXD format)
- Returns: Full metadata including contacts, publications, modifications

### Workflow

1. Search MassIVE for datasets related to the protein or PTM type: `MassIVE_search_datasets(species="9606")`
2. Review titles/summaries for relevance to the protein or PTM type under study
3. Get detailed metadata for relevant datasets: `MassIVE_get_dataset(accession="MSV...")`
4. Report dataset accessions, publications, and instrument types for experimental context

### Decision Logic

- **Relevant datasets found**: Include as supporting experimental evidence in report
- **No relevant datasets**: Note data gap; PTM evidence relies on iPTMnet and UniProt annotations only

---

## Phase 5: Synthesis and Report

Generate a comprehensive PTM analysis report covering:

1. **Protein identity** — confirmed UniProt accession, gene, organism
2. **PTM inventory** — total sites, types, most-studied modifications
3. **Proteoform diversity** — number of distinct proteoforms, key combinations
4. **PTM-dependent interactions** — interactions regulated by specific PTMs
5. **Functional hotspots** — PTM sites in active sites, binding sites, key domains
6. **Regulatory model** — how PTMs regulate the protein (activation, degradation, localization, complex formation)
7. **Data gaps** — what is not covered or where evidence is limited

### Required Report Sections

- Executive summary (top 3-5 most important PTMs and their roles)
- PTM site table (all sites with evidence)
- Proteoform summary
- PTM-dependent interaction table
- Functional context for key sites
- Evidence grading legend
- Data sources cited

---

## Tool Parameter Reference

| Tool | Key Parameter | Value |
|------|--------------|-------|
| `iPTMnet_search` | `operation` | `"search"` (required) |
| `iPTMnet_get_ptm_sites` | `operation` | `"get_ptm_sites"` (required) |
| `iPTMnet_get_proteoforms` | `operation` | `"get_proteoforms"` (required) |
| `iPTMnet_get_ptm_ppi` | `operation` | `"get_ptm_ppi"` (required) |
| `ProtVar_get_function` | `position` | integer residue number |
| `STRING_get_interaction_partners` | `required_score` | 700 for high confidence |
| `ELM_get_instances` | `operation` | `"get_instances"` (required, SOAP-style) |
| `ELM_get_instances` | `uniprot_id` | UniProt accession (required) |
| `ELM_get_instances` | `motif_type` | Optional: CLV/DEG/DOC/LIG/MOD/TRG |
| `ELM_list_classes` | `operation` | `"list_classes"` (required, SOAP-style) |
| `MassIVE_search_datasets` | `page_size` | Integer (max 100) |
| `MassIVE_search_datasets` | `species` | NCBI taxonomy ID string (e.g., `"9606"`) |
| `MassIVE_get_dataset` | `accession` | MSV or PXD format string |

**Critical**: All iPTMnet and ELM tools require `operation` as the first parameter — these are SOAP-style tools.

---

## Fallback Strategies

| Situation | Fallback |
|-----------|----------|
| Protein not in iPTMnet | Use `UniProt_get_entry` PTM/processing annotations |
| No PTM-PPI data | Use `STRING_get_interaction_partners` for general PPI context |
| No ProtVar function data | Use `UniProt_get_entry` domain/active-site annotations |
| Ambiguous protein name | Use `iPTMnet_search` with `role="Substrate"` to find all matching entries |
| No ELM motif data | Note ELM coverage gap; rely on iPTMnet and UniProt for PTM site context |
| No proteomics datasets | Note no public MS data available; report iPTMnet evidence only |

---

## Databases Integrated

| Database | Coverage | What it provides |
|----------|----------|-----------------|
| **iPTMnet** | 1M+ PTM sites, 11+ organisms | PTM sites, proteoforms, PTM-dependent PPIs, enzyme-substrate relationships |
| **ProtVar** | All UniProt proteins | Domain context, active-site proximity, conservation, clinical variants at PTM positions |
| **UniProt** | All reviewed proteins | Experimentally annotated PTMs, protein domains, function |
| **STRING** | 14M+ proteins | General PPI network for broader interaction context |
| **ELM** | 353 motif classes, 3,700+ instances | Short linear motifs (SLiMs) including modification sites, degradation signals, docking motifs |
| **MassIVE** | 10,000+ proteomics datasets | Public MS datasets for experimental PTM evidence |
| **ProteomeXchange** | Aggregates PRIDE, MassIVE, PeptideAtlas, jPOST, iProX | Central hub for proteomics data discovery |

---

## Limitations

- **iPTMnet coverage**: biased toward well-studied proteins (TP53, histones, kinase substrates); rare proteins may have limited PTM data
- **Proteoform combinatorics**: iPTMnet reports observed proteoforms; not all theoretical combinations are present
- **PTM-PPI completeness**: only interactions with PTM-specific evidence are in iPTMnet; many more general PPIs exist in STRING
- **Species**: iPTMnet covers human, mouse, rat, yeast, and others; always confirm organism in results
