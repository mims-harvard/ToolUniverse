---
name: tooluniverse-protein-interactions
description: Protein-protein interaction (PPI) network analysis — STRING (predicted + experimental), BioGRID (curated), SASBDB (small-angle scattering), Complex Portal (curated complex membership and stoichiometry, includes CORUM data). Distinguishes physical interactions (binding) from functional associations (co-expression, co-regulation). Use for interactome queries, complex partner identification, curated complex composition lookup, and pathway-level interaction analysis.
disable-model-invocation: true
---

# Protein Interaction Network Analysis

Comprehensive protein interaction network analysis using ToolUniverse tools. Analyzes protein networks through a 4-phase workflow: identifier mapping, network retrieval, enrichment analysis, and optional structural data.

## Domain Reasoning: Interaction Type Clarification

When asked about protein interactions, ask: physical interaction (do they bind?) or functional interaction (do they affect the same pathway)? STRING combines both — a high combined_score does not mean physical binding. For physical binding evidence, check the experimental score (`escore`) specifically. A high `tscore` (text mining) or `dscore` (database) with a low `escore` suggests co-annotation or co-citation, not direct binding.

LOOK UP DON'T GUESS: protein interaction scores, experimental evidence types, and whether two specific proteins have known co-crystal structures. Use STRING `escore` and BioGRID experimental data — do not infer binding from pathway co-membership alone.

## Databases Used

| Database | Coverage | API Key | Purpose |
|----------|----------|---------|---------|
| **STRING** | 14M+ proteins, 5,000+ organisms | Not required | Primary interaction source |
| **BioGRID** | 2.3M+ interactions, 80+ organisms | Required | Fallback, curated data |
| **SASBDB** | 2,000+ SAXS/SANS entries | Not required | Solution structures |
| **Complex Portal** | Curated complexes (incl. CORUM data) | Not required | Curated complex membership/stoichiometry |

## 4-Phase Workflow

1. **Identifier Mapping** — `STRING_map_identifiers()`: validate protein names, get STRING IDs
2. **Network Retrieval** — `STRING_get_network()` (primary); `BioGRID_get_interactions()` (fallback, requires API key)
3. **Enrichment Analysis** — `STRING_functional_enrichment()` for GO/KEGG/Reactome; `STRING_ppi_enrichment()` to test functional coherence
4. **Structural Data (optional)** — `SASBDB_search_entries()` for SAXS/SANS solution structures

See `python_implementation.py` for runnable examples (`example_tp53_analysis()`, `analyze_protein_network()`).

## Complex Portal: Curated Complex Membership

STRING/BioGRID answer "do A and B interact"; Complex Portal answers a different question — "what is the full, curated membership and stoichiometry of a known biological complex." Use it when the question is about a specific named or implied multi-subunit assembly (e.g. "what's in the SAGA complex," "what regulates p53 via a complex") rather than a pairwise or network-level interaction.

```
Phase 1: ComplexPortal_search_complexes(query=..., species=..., number=...) -> ranked candidate complexes,
         each with complex_id, name, description, and a subunits[] list (identifier, name,
         interactor_type: "protein" or "small molecule" for bound cofactors like zinc)
Phase 2: ComplexPortal_get_complex(complex_id) -> full detail for one specific complex by its CPX- ID
```

**Real example** (verified live): `ComplexPortal_search_complexes(query="TP53", species="Homo sapiens")` -> real complexes including `CPX-6093` "TP53-MDM2-MDM4 transcription regulation complex" (subunits P04637/Q00987/O15151) and two SAGA-complex variants (KAT2A/KAT2B) that recruit via TP53/MYC — real multi-subunit assemblies with real UniProt-identified subunits, including small-molecule cofactors (e.g. a zinc atom, `CHEBI:27363`) alongside protein subunits.

**Gotcha (verified live)**: `ComplexPortal_get_complex` can return `complex_id: null, name: null` in its own echoed fields even on a successful lookup — use `systematic_name` and the `subunits` list to confirm you got the right complex, and keep the `complex_id` you already had from `ComplexPortal_search_complexes` rather than trusting the field echoed back by `get_complex`.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `proteins` | Required | Gene symbols or UniProt IDs |
| `species` | 9606 | NCBI taxonomy ID |
| `confidence_score` | 0.7 | Min interaction confidence (0–1) |
| `include_biogrid` | False | BioGRID fallback (requires API key) |
| `include_structure` | False | SASBDB structural data (slower) |

### Confidence Score Guidelines

| Score | Use Case |
|-------|----------|
| 0.4 | Exploratory analysis (default STRING threshold) |
| 0.7 | Recommended — reliable interactions |
| 0.9 | Core interactions only |

## Network Edge Fields (STRING)

Key fields returned per interaction edge:
- `score` — combined confidence (0–1)
- `escore` — experimental score (use for physical binding evidence)
- `dscore` — database score
- `tscore` — text mining score
- `ascore` — coexpression score
- `preferredName_A`, `preferredName_B` — gene names

## Extended Analysis Tools

**Signaling Pathways:**
- `OmniPath_get_signaling_interactions` — directed, signed PPI (stimulation/inhibition)
- `Reactome_map_uniprot_to_pathways` — map proteins to Reactome pathways (param: `uniprot_id`)
- `ReactomeAnalysis_pathway_enrichment` — pathway enrichment for gene sets
- SIGNOR (causal signaling, literature-backed) — see below

### SIGNOR: Causal Signaling Interactions

STRING/BioGRID above tell you protein A and protein B interact (physically or
functionally) but not the *direction* or *effect*. SIGNOR fills that gap: it is
a manually curated database where every edge is a directional causal statement
— "A up-/down-regulates B's activity/quantity via mechanism M (phosphorylation,
ubiquitination, transcriptional regulation, binding, ...), optionally at
residue R" — each backed by a specific PMID. It's the same kind of directed,
signed edge as `OmniPath_get_signaling_interactions`, but from one curated
source with per-edge mechanism/residue/literature detail rather than an
aggregation across many databases; use both when you need convergent support
for a causal claim.

**Tools** (all real, live-verified — `entity_id`/protein identifiers should be
UniProt accessions, e.g. `P00533` for EGFR, not gene symbols):

| Tool | Purpose | Key params |
|------|---------|------------|
| `SIGNOR_get_interactions` | Upstream regulators + downstream targets of one protein | `entity_id` (UniProt acc), `organism` (taxid, default 9606), `limit` |
| `SIGNOR_list_pathways` | Browse curated signaling pathways (disease- or process-named) | `query` (optional keyword, e.g. `"apoptosis"`, `"MAPK"`) |
| `SIGNOR_get_pathway` | All causal interactions within one curated pathway | `pathway_id` (from `list_pathways`, e.g. `"SIGNOR-EGF"`), `limit` |
| `SIGNOR_connect_proteins` | Shortest curated causal sub-network linking 2+ proteins | `proteins` (array of UniProt accs, 2+), `level` (1=direct only, 2=one intermediate, 3=two intermediates), `limit` |

Each interaction returns `source_entity`/`target_entity` (+ their UniProt
`source_id`/`target_id`), `effect` (e.g. `"down-regulates activity"`,
`"up-regulates quantity by expression"`), `mechanism` (e.g.
`"phosphorylation"`, `"ubiquitination"`, `"binding"`, `"transcriptional
regulation"` — can be an empty string when unspecified), `residue` (nullable),
`pmid`, `direct` (bool — true = no known intermediate; SIGNOR's own
`connect_proteins` output can mix `direct: true` and `direct: false` edges in
one path, so check this field per-edge rather than assuming the whole path is
direct), and a confidence-adjacent `score`.

**Workflow — trace a causal path between two proteins:**
```
SIGNOR_connect_proteins(proteins=["P00533", "P28482"], level=2)  # EGFR -> ERK2(MAPK1)
```
returns the curated sub-network connecting them (verified live: real edges
include EGFR's own upstream regulators like ERRFI1 and PRKG2, and
transcriptional links such as JAK2->MYC and LCK->STAT3 that co-occur in the
2-hop neighborhood — `connect_proteins` returns the local causal graph around
the requested proteins, not only a single shortest path, so filter for edges
that actually chain from source to target if you need one specific route).

**Workflow — browse a disease/process pathway then inspect one protein's role in it:**
```
SIGNOR_list_pathways(query="cancer")          # -> pathway_id, e.g. "SIGNOR-EGF" (EGFR Signaling)
SIGNOR_get_pathway(pathway_id="SIGNOR-EGF")   # -> all curated edges in that pathway (metadata.total_interactions gives the true count if limit truncates)
SIGNOR_get_interactions(entity_id="P00533")   # -> zoom into EGFR specifically: e.g. real edges show VCB-Cul2 ubiquitinating/destabilizing EGFR (PMID:15590694) and EGFR phosphorylating IKBKE (PMID:27287717)
```

**Druggability & Clinical Context:**
- `DGIdb_get_drug_gene_interactions` — drug interactions for hub proteins (param: `genes` as array)
- `DGIdb_get_gene_druggability` — druggability categories
- `gnomad_get_gene_constraints` — gene essentiality metrics (pLI, oe_lof)
- `civic_search_evidence_items` — clinical evidence for mutations in network proteins
- `UniProt_get_function_by_accession` — protein function annotation

## Tool-Specific Notes

### IntAct Interaction Data

`interaction_ids` are in the `metadata` field of the response, NOT at the top level:
```python
interaction_ids = result.get("metadata", {}).get("interaction_ids", [])
```

### BioGRID Chemical Interactions

`BioGRID_get_chemical_interactions` always includes a limitation note — chemical interaction coverage may be incomplete. Defaults to `taxId=9606` (human) when no organism is provided.

### IntAct `protein_name` Alias

IntAct tools accept `protein_name` as an alias parameter in addition to the original identifier parameter.

### EBI Proteins-Gateway IntAct Access

`EBIProteins_get_interactions(accession, limit=50)` and `EBIProteins_get_interaction_details(accession)` are a second, concrete access path into the same IntAct-sourced interaction data referenced above (via the EBI Proteins API rather than IntAct's own endpoint) — use these when a plain UniProt-accession-in, ranked-partners-out call is more convenient than mapping identifiers through STRING/IntAct first.

| Tool | Returns |
|------|---------|
| `EBIProteins_get_interactions` | Binary interaction partners sorted by supporting-experiment count, each with `partner_accession`, `gene_name`, `experiments` (count), `organism_differ` (bool) |
| `EBIProteins_get_interaction_details` | The query protein's own record (name, existence evidence, organism, disease associations, subcellular locations) plus its top interaction partners in one call — useful when you need protein context and its network in a single request instead of two |

Real example (verified live): `EBIProteins_get_interactions(accession="P04637")` (TP53) → 198 partners incl. MDM2 (Q00987), ABL1, AIMP2 (6 experiments), EP300 (8 experiments). `EBIProteins_get_interaction_details(accession="P04637")` → same interaction data plus real disease associations (e.g. Li-Fraumeni syndrome) and subcellular locations in one response — skip the separate `UniProt_get_function_by_accession` call above when disease/localization context is the only extra thing needed.

## Domain Reasoning: Multimeric Assemblies & Binding Valency

LOOK UP DON'T GUESS: oligomeric state, subunit stoichiometry, and binding valency. Use RCSB PDB (`RCSBAdvSearch_search_structures`, `RCSBData_get_entry`) or UniProt (`UniProt_get_function_by_accession`) to confirm whether a protein is a monomer, dimer, trimer, etc. Do not assume from gene name alone.

### Calculating Multimer Valency from Binding Data

**Valency** = number of independent binding sites on a multimeric complex. A homodimer with one binding site per subunit has valency 2. A pentamer (e.g., IgM) with 2 Fab arms each has valency 10.

Key reasoning steps:
1. **Determine oligomeric state**: Look up quaternary structure in PDB/UniProt. A "dimer" in solution may be a dimer-of-dimers (tetramer) crystallographically.
2. **Count binding sites per subunit**: Each subunit contributes independently unless the binding site spans the interface (then the complex itself is the functional unit).
3. **Valency = subunits x sites_per_subunit** (only if sites are independent). If binding at one site affects another, you have cooperativity, not simple valency.
4. **Avidity vs affinity**: A multivalent complex binds more tightly than a single site (avidity effect). Apparent Kd_multivalent << Kd_monovalent. The enhancement depends on linker flexibility and target geometry.

### Statistical Factors in Multimeric Binding

When a symmetric multimer binds a ligand, **statistical factors** affect the apparent rate constants:
- **First ligand binding**: kon_apparent = n x kon_intrinsic (n equivalent sites available)
- **First ligand dissociation**: koff_apparent = koff_intrinsic (only one ligand to dissociate)
- **General rule**: For a multimer with n identical sites, binding to the i-th site has forward statistical factor (n - i + 1) and reverse statistical factor i.
- **Macroscopic vs microscopic Kd**: Kd_macro(1st site) = Kd_micro / n. Kd_macro(last site) = n x Kd_micro. The ratio Kd_last / Kd_first = n^2 for non-cooperative binding.

If measured Kd values deviate from these statistical predictions, the protein shows **positive cooperativity** (Kd decreases more than expected) or **negative cooperativity** (Kd increases more than expected).

### When to Use Binding Curve Analysis vs Stoichiometry

| Approach | Use when | What it tells you |
|----------|----------|-------------------|
| **Stoichiometry** (ITC, AUC, SEC-MALS) | You need the number of binding partners per complex | n (sites), not affinity |
| **Binding curves** (SPR, FP, ELISA) | You need Kd and kinetics | Affinity, but apparent Kd conflates valency and cooperativity |
| **Hill plot** (log-log binding curve) | You suspect cooperativity | Hill coefficient nH: nH=1 non-cooperative, nH>1 positive, nH<1 negative |
| **Scatchard plot** (bound/free vs bound) | Classic approach, now less common | Curved = multiple site classes or cooperativity; linear = single Kd |

**Obligate vs facultative multimers**: An obligate dimer (e.g., many kinases) has NO monomeric activity. If your "purified protein" shows no activity, check if dimer formation is required. Use SEC or native PAGE to confirm oligomeric state. Low protein concentration, high salt, or wrong pH can dissociate obligate multimers.

## Domain Reasoning: Coiled-Coil Oligomeric State Prediction

- **Heptad repeat**: (abcdefg)n where positions a and d are hydrophobic core residues.
- **Oligomeric state from packing**: dimer (leucine zipper, Leu at d), trimer (Ile/Val at a, Leu at d), tetramer (Leu at both a+d), pentamer (complex mixed packing, e.g., Trp or polar residues at a).
- **Heptad net diagram**: map residues onto helical wheel; a+d form the hydrophobic core interface. The identity of a/d residues determines packing geometry and thus oligomeric state.
- **Polar residues at a/d** (Asn, Gln) specify parallel vs antiparallel orientation and can select for specific oligomeric states.
- LOOK UP: search PubMed for "[sequence motif] coiled coil oligomeric state" and check CC+ or SOCKET databases before predicting oligomeric state from sequence alone.

## Domain Reasoning: Detergent Effects on Membrane Proteins

- **Mild detergents** (DDM, LMNG, CHAPS, digitonin) preserve native oligomeric state and lipid interactions; preferred for structural studies.
- **Harsh detergents** (SDS, OG at high concentration above CMC) can dissociate native complexes and strip stabilizing lipids.
- **Native MS in different detergents** reveals whether specific lipids stabilize oligomeric assemblies; comparing CHAPS vs OG results distinguishes detergent-stable from lipid-dependent oligomers.

## Protein Identification Questions

For "what protein does X" questions: ALWAYS search UniProt and PubMed first — do not guess from memory. Key pathways to know:
- **Amyloid clearance**: collagen degradation by matrix metalloproteinases is required to expose amyloid deposits, allowing macrophage engulfment. The answer is collagen, not serum amyloid P (SAP) or other amyloid-binding proteins.
- When a question asks "what protein", give JUST the protein name — no abbreviations, descriptions, or qualifications.

## Troubleshooting

- **No interactions found**: verify protein names (case-sensitive), try `confidence_score=0.4`
- **BioGRID not working**: set `BIOGRID_API_KEY` in environment; STRING works without a key
- **Verbose output**: filter with `2>&1 | grep -v "Error loading tools"` (see KNOWN_ISSUES.md)

## References

- STRING: https://string-db.org/
- BioGRID: https://thebiogrid.org/ (register for free API key)
- SASBDB: https://www.sasbdb.org/
- Complex Portal: https://www.ebi.ac.uk/complexportal/
- ToolUniverse: https://github.com/mims-harvard/ToolUniverse
