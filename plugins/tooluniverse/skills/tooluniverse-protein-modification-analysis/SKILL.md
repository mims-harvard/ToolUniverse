---

name: tooluniverse-protein-modification-analysis
description: "Post-translational modification (PTM) analysis — phosphorylation, ubiquitination, acetylation, glycosylation, methylation. Uses iPTMnet (sites + enzymes), ProtVar (functional consequences), UniProt (baseline), STRING, ELM (linear motifs), MassIVE/ProteomeXchange (experimental), and the EBI Proteins API (mutagenesis, MS-proteomics/HPP peptide evidence, antigenic regions, genomic coordinates, protein-level variant lookup by accession/dbSNP/HGVS) as a cross-validation source. Use for PTM site annotation, kinase-substrate identification, and PTM-disease associations."
---

# Protein Post-Translational Modification Analysis

Comprehensive PTM analysis using iPTMnet (primary), ProtVar (functional context), UniProt (baseline), STRING (interactions), ELM (linear motifs), and MassIVE/ProteomeXchange (experimental data).

## LOOK UP DON'T GUESS

- PTM sites/enzymes: `iPTMnet_get_ptm_sites`
- Functional consequence: `ProtVar_get_function` + `iPTMnet_get_ptm_ppi`
- Proteoforms: `iPTMnet_get_proteoforms`
- Linear motifs: `ELM_get_instances`

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Domain Reasoning

PTMs are context-dependent: same phosphorylation site can activate or inhibit depending on kinase and effectors. Always check: which enzyme, what functional consequence, in what cell context.

---

## KEY PRINCIPLES

1. **Disambiguation first** -- resolve to UniProt accession before iPTMnet calls
2. **iPTMnet is SOAP-style** -- every call requires `operation` parameter
3. **Evidence-graded** -- distinguish experimental (T1) from predicted (T4)
4. **English-first queries**

---

## Workflow

```
Phase 0: Protein Disambiguation → UniProt accession
Phase 1: PTM Site Inventory → iPTMnet_get_ptm_sites
Phase 2: Proteoform Analysis → iPTMnet_get_proteoforms
Phase 3: PTM-Dependent Interactions → iPTMnet_get_ptm_ppi
Phase 4: Functional Context → ProtVar_get_function at key sites
Phase 4b: Linear Motif Context → ELM_get_instances for SLiM overlap
Phase 4c: Experimental Data → MassIVE/ProteomeXchange
Phase 5: Synthesis & Report
```

---

## Phase 0: Disambiguation

- `iPTMnet_search(operation="search", search_term="TP53", role="Substrate")` -- find UniProt IDs
- If user provides UniProt accession directly, use it
- Select human entry if multiple hits

## Phase 1: PTM Sites

`iPTMnet_get_ptm_sites(operation="get_ptm_sites", uniprot_id="P04637")` -- returns position, residue, modification type, enzyme, evidence. Group by modification type. Fallback: `UniProt_get_entry_by_accession` PTM annotations.

## Phase 2: Proteoforms

`iPTMnet_get_proteoforms(operation="get_proteoforms", uniprot_id=...)` -- distinct PTM combinations. Focus on those with functional/disease annotations if >20.

## Phase 3: PTM-Dependent Interactions

`iPTMnet_get_ptm_ppi(operation="get_ptm_ppi", uniprot_id=...)` -- interacting protein, PTM site, effect (enables/disrupts). Supplement with `STRING_get_interaction_partners(identifiers=gene, species=9606, required_score=700)`.

## Phase 4: Functional Context

`ProtVar_get_function(accession=..., position=N, variant_aa=AA)` -- domain, active site, binding site, conservation. Grade: active-site PTM > domain-core > disordered region.

## Phase 4b: Linear Motifs (ELM)

`ELM_get_instances(operation="get_instances", uniprot_id=..., motif_type="MOD")` -- MOD = modification sites, DEG = degradation signals. Cross-reference with Phase 1 PTM positions. `ELM_list_classes(operation="list_classes")` for motif details.

## Phase 4c: Experimental Data

`MassIVE_search_datasets(species="9606")`, `MassIVE_get_dataset(accession="MSV...")` for public MS datasets.

## Phase 4d: EBI Proteins Cross-Validation (Structural, Antigenic, MS-Peptide Evidence)

`src/tooluniverse/data/ebi_proteins_ext_tools.json` provides 11 UniProt-accession-keyed tools from the EBI Proteins API — a second, independent evidence source to corroborate or extend the iPTMnet/ProtVar findings above, not a replacement for them:

| Tool | Returns | When to use |
|------|---------|-------------|
| `EBIProteins_get_mutagenesis` | Experimentally characterized point-mutation effects (gain/loss of function, binding/structural impact), UniProtKB-curated with literature evidence | Corroborate a PTM-adjacent residue's functional importance with direct mutagenesis evidence, independent of iPTMnet |
| `EBIProteins_get_proteomics_ptm` | MS-evidence-backed PTM sites from PeptideAtlas/ProteomicsDB/MaxQB/EPD | Cross-check an iPTMnet PTM call against raw MS detection evidence — **this is detection evidence, not curated/annotated PTM biology**, so treat a hit here as "observed by MS" not "known to be functional" |
| `EBIProteins_get_features` | Consolidated UniProt features by category (`DOMAINS_AND_SITES`, `MOLECULE_PROCESSING`, `PTM`, `STRUCTURAL`, `TOPOLOGY`, `VARIANTS`, `MUTAGENESIS`; default `DOMAINS_AND_SITES`) | Get all UniProt-curated PTM annotations in one call via `category="PTM"` — a faster alternative to browsing full UniProt when only PTM feature rows are needed |
| `EBIProteins_get_antigen` | Predicted antigenic regions with match-confidence scores | PTM sites near/inside an antigenic region can affect antibody binding — relevant when a PTM study feeds into antibody or immunoassay design |
| `EBIProteins_get_coordinates` | UniProt protein -> Ensembl gene/transcript ID, chromosome, strand, exon count | Map a PTM residue position back to genomic coordinates for genome-browser cross-referencing |
| `EBIProteins_get_proteomics_peptides` | Generic MS peptide-level detection evidence (position, uniqueness, source DB) | Confirm a PTM-bearing region of the protein has actually been observed by mass spec at all, before trusting a PTM call there |
| `EBIProteins_get_hpp_peptides` | Human Proteome Project peptide evidence — a stringent, typically larger evidence set than `get_proteomics_peptides` for the same accession | Prefer this over `get_proteomics_peptides` when the strongest available MS confirmation is needed (human proteins only) |

**Known broken (verified live, not a guess):** `EBIProteins_get_rna_editing` returns HTTP 404 directly from `https://www.ebi.ac.uk/proteins/api/rna_editing/...` for both of its own documented example accessions (P42262, P28335), while the sibling `mutagenesis` endpoint on the same API returns 200 for the same host. This looks like EBI deprecated/removed the endpoint rather than a transient outage — re-verify with a direct `tu run EBIProteins_get_rna_editing '{"accession": "..."}'` before relying on it, and do not present RNA-editing results from this tool as available without that check.

**Protein-level variant lookup (distinct from Phase 1-4 PTM tools, not duplicative of `tooluniverse-variant-analysis`'s SPDI/HGVS/rsID *notation conversion*):**

| Tool | Returns | When to use |
|------|---------|-------------|
| `EBIProteins_get_variation` | All known variants for a UniProt accession, merged from COSMIC/ClinVar/gnomAD/ExAC/UniProt, with clinical significance and disease associations; filterable by `source_type` and `disease_only` | Want every reported variant on a protein with disease context in one call |
| `EBIProteins_get_variation_by_dbsnp` | Reverse lookup: given a dbSNP rsID, every UniProt entry (incl. isoforms) carrying that variant, with the mapped protein-level consequence | Have an rsID, need to know which protein(s)/isoform(s) it affects and how — `tooluniverse-variant-analysis`'s `NCBIVariation_*` tools convert rsID<->SPDI<->HGVS notation but do not resolve to a UniProt protein consequence the way this does |
| `EBIProteins_get_variation_by_hgvs` | Reverse lookup: given an HGVS genomic expression (`NC_...:g....`), every overlapping UniProt entry with the resulting protein-level consequence | Have a genomic HGVS change, need its amino-acid consequence across all affected isoforms in one call, rather than converting notation first and then looking up each protein separately |

All 3 return multiple UniProt entries per query (isoforms, paralogs sharing the position) — always check `total_entries`/`total_variants` and report which specific entry/isoform a finding came from, don't assume the first entry is the canonical one.

**Single-category shortcuts (verified identical data to `EBIProteins_get_features`):** `EBIProteins_get_domains_sites`, `EBIProteins_get_molecule_processing`, and `EBIProteins_get_structural_features` each take a plain `accession` and return exactly the same feature list as `EBIProteins_get_features(accession, category="DOMAINS_AND_SITES"|"MOLECULE_PROCESSING"|"STRUCTURAL")` respectively — confirmed live on P04637, byte-for-byte the same 31 `DOMAINS_AND_SITES` features (minor field-naming difference only: the dedicated tool flattens `evidences[].source`/`.id`, the generic one nests `source_name`/`source_id`). Use the dedicated tool when you already know which single category you want (one fewer parameter); use `EBIProteins_get_features` when browsing multiple categories in a loop. `EBIProteins_get_molecule_processing` is the one to reach for on precursor proteins that get cleaved into a mature form — e.g. P01308 (insulin) returns signal peptide (1-24), B chain (25-54), C peptide (57-87), A chain (90-110).

**Protein-to-genome coordinate mapping (two tools, more detail than the existing `EBIProteins_get_coordinates` summary above):**

| Tool | Direction | Returns |
|------|-----------|---------|
| `EBIProteins_get_coordinate_mapping` | protein → genome | Per-*exon* residue-to-genomic-coordinate mapping across all transcript isoforms (chromosome, strand, exon boundaries) — exon-level detail that `EBIProteins_get_coordinates` (chromosome/strand/exon *count* only) doesn't give you |
| `EBIProteins_get_proteins_by_genomic_loc` | genome → protein | Reverse lookup: given `taxonomy` + `location` (`"17:7676154"`, 1-based) or `chromosome`+`position`, every UniProt protein whose coding sequence overlaps that position, with the exact affected residue |

Real example (verified live): `EBIProteins_get_coordinate_mapping(accession="P04637")` → TP53 maps to 6 transcripts on chromosome 17 (reverse strand), 10 exons, positions 7669612-7676594. The reverse direction confirms it: `EBIProteins_get_proteins_by_genomic_loc(taxonomy="9606", location="17:7676154")` → TP53 (P04637) at protein residue 72 (Pro) on transcript ENST00000923569 — use this when you have a chromosomal variant position and need to know which protein(s)/residue it hits, before running any PTM/functional analysis on that residue.

**Epitopes (experimental, IEDB-sourced — distinct from `EBIProteins_get_antigen`'s *predicted* antigenic regions):** `EBIProteins_get_epitopes(accession)` returns experimentally-mapped immune epitope regions with sequence, PubMed evidence, and IEDB IDs — e.g. P04637 (TP53) has 62 mapped epitopes. Use this over `EBIProteins_get_antigen` when the question is "has this region actually been shown to trigger an immune response" rather than "does this region look antigenic by sequence pattern" — relevant for vaccine/antibody design questions that land in this skill via a PTM-and-antigenicity angle.

---

## Evidence Grading

| Tier | Criteria |
|------|----------|
| T1 | PTM at validated active/binding site with functional data |
| T2 | PTM in structured domain with ProtVar annotation |
| T3 | Correlation data only (mass spec detection) |
| T4 | Predicted, no experimental validation |

---

## Tool Parameter Reference

| Tool | Key Params |
|------|-----------|
| `iPTMnet_search` | `operation="search"`, `search_term`, `role` |
| `iPTMnet_get_ptm_sites` | `operation="get_ptm_sites"`, `uniprot_id` |
| `iPTMnet_get_proteoforms` | `operation="get_proteoforms"`, `uniprot_id` |
| `iPTMnet_get_ptm_ppi` | `operation="get_ptm_ppi"`, `uniprot_id` |
| `ELM_get_instances` | `operation="get_instances"`, `uniprot_id`, `motif_type` |
| `ELM_list_classes` | `operation="list_classes"` |
| `MassIVE_search_datasets` | `page_size`, `species` |
| `EBIProteins_get_mutagenesis` / `_get_proteomics_ptm` / `_get_antigen` / `_get_coordinates` / `_get_proteomics_peptides` / `_get_hpp_peptides` / `_get_domains_sites` / `_get_molecule_processing` / `_get_structural_features` / `_get_epitopes` | `accession` (UniProt) |
| `EBIProteins_get_features` | `accession`, `category` (default `DOMAINS_AND_SITES`) |
| `EBIProteins_get_coordinate_mapping` | `accession` (UniProt) |
| `EBIProteins_get_proteins_by_genomic_loc` | `taxonomy` (default 9606), `location` ("chr:pos") or `chromosome`+`position` |
| `EBIProteins_get_variation` | `accession`, optional `source_type`, `disease_only` |
| `EBIProteins_get_variation_by_dbsnp` | `dbsnp_id` (rsID) |
| `EBIProteins_get_variation_by_hgvs` | `hgvs` (genomic, `NC_...:g....`) |

**Critical**: All iPTMnet and ELM tools require `operation` as first parameter (SOAP-style). EBI Proteins tools take a plain `accession`/`dbsnp_id`/`hgvs` string, no `operation` wrapper.

---

## Fallbacks

| Situation | Fallback |
|-----------|----------|
| Not in iPTMnet | UniProt PTM/processing annotations |
| No PTM-PPI data | STRING general PPI |
| No ProtVar data | UniProt domain annotations |
| No ELM data | Proceed with iPTMnet/UniProt only |
| `EBIProteins_get_rna_editing` 404s | Verified broken as of this writing (EBI-side, not a request bug) — skip, do not retry-loop on it |

## Limitations

- iPTMnet biased toward well-studied proteins
- Proteoform data covers observed combinations only
- PTM-PPI: only PTM-specific evidence; more PPIs exist in STRING
- `EBIProteins_get_proteomics_ptm`/`_get_proteomics_peptides`/`_get_hpp_peptides` are MS *detection* evidence, not curated PTM biology — a hit means "seen by mass spec," not "known functional PTM"
- `EBIProteins_get_rna_editing` is currently non-functional (HTTP 404 from EBI on both of its own documented example accessions, confirmed live) — do not rely on it until re-verified
