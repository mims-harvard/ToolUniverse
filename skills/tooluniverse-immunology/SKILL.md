---
name: tooluniverse-immunology
description: Immunology research workflows using ToolUniverse tools. Covers antibody-antigen structural analysis (SAbDab, TheraSAbDab), immune protein interactions (IntAct, BioGRID), epitope and T-cell/B-cell assay data (IEDB), immunoglobulin gene databases (IMGT), cytokine/receptor signaling (OpenTargets, GWAS), clinical safety data for immune diseases (FAERS, clinical trials), autoimmune disease genetics (Orphanet), and immune pathway analysis (KEGG, Reactome). Use when researchers ask about antibody targets, immune signaling networks, autoimmune genetics, immunotherapy safety, epitope discovery, or immune pathway enrichment.
---

# Immunology Research Skill

**KEY PRINCIPLES**: Multi-layer evidence; source every claim; use immunology-specific databases first (IEDB, IMGT, SAbDab); always use English gene/protein names in tool calls.

---

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

**For MC about immune mechanisms**: Look up the specific pathway/receptor/cytokine before answering. Use `PubMed_search_articles` with the exact terms from the question. The answer is almost always in the first few search results.

**Specific LOOK UP targets** (never guess these):
- **Immune cell markers**: CD markers for cell subsets (e.g., Treg = CD4+CD25+FOXP3+, not just "CD4+"). Query UniProt or IEDB.
- **Cytokine functions**: IL-17 is pro-inflammatory (Th17), IL-10 is anti-inflammatory (Treg) — but context matters. Verify via KEGG pathway or PubMed.
- **MHC/HLA restrictions**: Which HLA allele presents which peptide — always check IEDB MHC binding data; allele-level differences are critical (HLA-A*02:01 vs HLA-A*02:07 have different peptide repertoires).
- **Antibody Kd values**: Never estimate binding affinity; check SAbDab, IEDB, or published literature.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Reasoning Frameworks

**Immune response reasoning** — Every immune response has innate → adaptive phases. Ask: which arm is relevant to the question? Innate (neutrophils, macrophages, complement, pattern recognition) or adaptive (T cells, B cells, antibodies, memory)? Innate is fast (hours) and antigen-nonspecific; adaptive is slow (days) but specific and generates memory. The transition occurs when APCs present antigen to naive T/B cells. Targeting innate suppresses broad inflammation; targeting adaptive disrupts antigen-specific responses. This determines which databases and tools are most relevant.

**Antibody analysis reasoning** — Structure determines function. The variable region (VH/VL, CDR loops) determines antigen specificity. The Fc region determines effector function: complement activation (IgM, IgG), ADCC via FcγR (IgG), or opsonization. When analyzing antibody data, always ask: are we studying binding (Fab — use IEDB, SAbDab, IMGT) or function (Fc — use FAERS for clinical safety, OpenTargets for target biology, TheraSAbDab for therapeutic format/isotype)? Isotype switching changes effector function without changing specificity.

**Autoimmunity reasoning** — Autoimmunity = loss of self-tolerance. Ask: is the attack cell-mediated (T cells destroying tissue → Type 1 diabetes, MS) or antibody-mediated (autoantibodies → SLE, myasthenia gravis, Graves')? Cell-mediated disease implicates MHC class I/II and TCR repertoire; antibody-mediated implicates B cell activation, affinity maturation, and complement. This determines the disease mechanism, the relevant genetic loci (HLA alleles dominate both, but TCR genes matter more for T-cell diseases), and the therapeutic approach (biologics targeting T cells vs. B cells vs. complement).

**Antibody-antigen interaction reasoning** — Binding strength has two axes: affinity (Kd of single binding site, typically nM–pM for therapeutic mAbs) and avidity (combined strength of all binding sites — IgM pentamer has low affinity but high avidity). When analyzing binding data: Kd < 1 nM = very high affinity; 1–100 nM = moderate; > 100 nM = weak. Epitope mapping strategy depends on the question: linear epitopes → peptide arrays or IEDB linear epitope search; conformational epitopes → HDX-MS, cryo-EM, or cross-linking MS. For therapeutic antibodies, check SAbDab for co-crystal structures and TheraSAbDab for clinical-stage format/engineering details.

**Immune signaling cascade reasoning** — When asked "what happens when cytokine X activates cell Y", trace the full pathway: receptor (which subunits?) → proximal kinase (JAK1/2/3, TYK2, Src family?) → transcription factor (STAT1/3/4/5/6, NF-kB, NFAT?) → effector genes (cytokines, cytotoxic molecules, survival factors). Example: IL-12 + T cell → IL-12R (IL12RB1+IL12RB2) → JAK2/TYK2 → STAT4 → IFN-gamma production (Th1 differentiation). Use KEGG pathway hsa04630 (JAK-STAT) and Reactome R-HSA-1280215 (Cytokine Signaling) to verify. Key signaling modules: JAK-STAT (most cytokines), NF-kB (TNF, TLRs, TCR/BCR co-stimulation), MAPK/ERK (growth factors, TCR), PI3K-AKT (co-stimulation, survival).

**Complement system reasoning** — Three activation pathways converge on C3 convertase: Classical (C1q binds antibody-antigen complexes — IgM or IgG → C4b2a), Lectin (MBL binds mannose on pathogens → C4b2a), Alternative (spontaneous C3 hydrolysis + factor B/D → C3bBb, amplification loop). All converge on C5 convertase → MAC (C5b-9). When to check which: suspected immune complex disease (SLE) → classical pathway (C1q, C4); recurrent bacterial infections → alternative or lectin (factor B, MBL); paroxysmal nocturnal hemoglobinuria → terminal pathway (CD55/CD59 deficiency). Therapeutic targets: eculizumab blocks C5; avacopan blocks C5aR.

**Evidence grading** — A (strong): GWAS p < 5e-8 + functional data + clinical signal. B (moderate): genetics or pathway evidence, limited functional data. C (preliminary): single-database hit only. Converging genetic (GWAS/Orphanet) + protein interaction (IntAct/BioGRID) + pathway data raises confidence. FAERS PRR > 2 with IC025 > 0 is a signal, not causal proof. TIMER2 deconvolution estimates require orthogonal validation.

---

## Tool Reference

### Antibody / Structural (SAbDab, TheraSAbDab)

| Tool | Key Parameters |
|------|---------------|
| `SAbDab_get_structure` | `pdb_id` (str) — structure details and chain info |
| `SAbDab_get_summary` | `pdb_id` (str) — CDR and chain summary |
| `SAbDab_search_structures` | `query` (str) — returns browse URL only, not JSON |
| `TheraSAbDab_search_therapeutics` | `query` (str, e.g. "pembrolizumab") — INN, target, format, phase |
| `TheraSAbDab_search_by_target` | `target` (str) — all therapeutics for an antigen |
| `TheraSAbDab_get_all_therapeutics` | (none) — full therapeutic antibody list |

### Epitope and Immune Assays (IEDB)

All search tools accept `limit`, `offset`, `filters` (PostgREST dict).

| Tool | Extra Parameters |
|------|-----------------|
| `iedb_search_epitopes` | `sequence_contains`, `structure_type` |
| `iedb_search_tcell_assays` | `sequence_contains`, `mhc_class`, `qualitative_measure` |
| `iedb_search_bcell` | filters only |
| `iedb_search_mhc` | filters only |
| `iedb_search_tcr_sequences` / `iedb_search_bcr_sequences` | filters only |

Detail tools by `structure_id`: `iedb_get_epitope_antigens`, `iedb_get_epitope_mhc`, `iedb_get_epitope_tcell_assays`, `iedb_get_epitope_references`.

### Immunoglobulin Genes (IMGT)

`IMGT_search_genes`, `IMGT_get_gene_info`, `IMGT_get_sequence` — all take `gene_name` (e.g. "IGHV1-2").

### Protein Interactions (IntAct, BioGRID)

| Tool | Key Parameters |
|------|---------------|
| `intact_get_interaction_network` | `identifier` (UniProt accession — gene symbols return 0 results), `limit` |
| `intact_search_interactions` | `query` (keyword), `limit` |
| `BioGRID_get_interactions` | `gene_names` (list), `organism` ("9606" string), `limit` |
| `BioGRID_get_chemical_interactions` | `gene_names` (list), `chemical_names` (list), `organism` (int) |

Weight interaction evidence: co-IP and two-hybrid = direct; co-expression or text-mining = hypothesis-generating.

### Cytokine / Signaling (OpenTargets, GWAS)

| Tool | Key Parameters |
|------|---------------|
| `OpenTargets_get_target_id_description_by_name` | `targetName` — resolves gene symbol to Ensembl ID (required before ensemblId tools) |
| `OpenTargets_get_target_interactions_by_ensemblID` | `ensemblId`, `size` |
| `OpenTargets_get_target_gene_ontology_by_ensemblID` | `ensemblId` |
| `OpenTargets_get_target_safety_profile_by_ensemblID` | `ensemblId` |
| `OpenTargets_get_associated_diseases_by_drug_chemblId` | `chemblId` |
| `gwas_search_associations` | `query` (disease name) |
| `gwas_get_snps_for_gene` | `gene_symbol` (mapped gene symbol) |

### Clinical / Safety (FAERS, Clinical Trials)

| Tool | Key Parameters |
|------|---------------|
| `FAERS_calculate_disproportionality` | `drug_name` (generic), `adverse_event` → PRR, ROR, IC |
| `FAERS_filter_serious_events` | `drug_name`, `seriousness_type` |
| `FAERS_stratify_by_demographics` | `drug_name`, `stratify_by` (sex/age/country) |
| `FAERS_compare_drugs` | `drug1`, `drug2`, `adverse_event` |
| `search_clinical_trials` | `condition`, `intervention`, `pageSize` |

### Autoimmune Genetics (Orphanet)

`Orphanet_search_diseases(query)` → ORPHAcode. Then: `Orphanet_get_genes`, `Orphanet_get_phenotypes`, `Orphanet_get_epidemiology`, `Orphanet_get_natural_history` (all take `orpha_code`). `Orphanet_get_gene_diseases(gene_symbol)` for reverse lookup.

### Immune Pathways (KEGG, Reactome)

| Tool | Key Parameters |
|------|---------------|
| `kegg_search_pathway` | `keyword` |
| `KEGG_get_disease` / `KEGG_get_disease_genes` | `disease_id` (e.g. "H00080" for SLE) |
| `KEGG_get_pathway_genes` | `pathway_id` (e.g. "hsa04060") |
| `Reactome_get_pathway` | `stId` (e.g. "R-HSA-168256") — NOT `pathway_id` |
| `ReactomeAnalysis_pathway_enrichment` | `identifiers` (space-separated STRING, not array) |
| `Reactome_map_uniprot_to_pathways` | `uniprot_id` |

Key pathway IDs — Reactome: R-HSA-168256 (Immune System), R-HSA-168249 (Innate), R-HSA-1280218 (Adaptive), R-HSA-1280215 (Cytokine Signaling), R-HSA-202403 (TCR), R-HSA-983705 (BCR), R-HSA-166658 (Complement). KEGG: hsa04060 (Cytokine-receptor), hsa04660 (TCR), hsa04662 (BCR), hsa04620 (TLR), hsa04630 (JAK-STAT), hsa05322 (SLE), hsa05323 (RA).

### Tumor Immune Microenvironment

`TIMER2_immune_estimation` — `operation="immune_estimation"`, `cancer` (TCGA code e.g. "luad_tcga"), `gene` (symbol). Returns deconvolution estimates; validate with orthogonal methods.

---

## Parameter Gotchas

| Issue | Wrong | Correct |
|-------|-------|---------|
| Reactome param name | `pathway_id=` | `stId=` |
| ReactomeAnalysis identifiers | list `["STAT4","IRF5"]` | space-separated string `"STAT4 IRF5"` |
| OpenTargets target lookup | `query="IL6"` | `targetName="IL6"` |
| IntAct identifier | gene symbol `"CD274"` | UniProt accession `"Q9NZQ7"` |
| BioGRID organism | `"human"` | `"9606"` (string taxon ID) |
| BioGRID gene param | `gene_name="CD274"` | `gene_names=["CD274"]` (list) |
| FAERS drug name | brand name `"Keytruda"` | generic `"pembrolizumab"` |
| SAbDab search | expect JSON | `SAbDab_search_structures` returns URL only; use `SAbDab_get_structure` with PDB ID |
| TheraSAbDab by target | `search_by_target` for common names | Use `search_therapeutics(query=drug_name)` instead; target requires exact registry string |
| KEGG disease ID | `"lupus"` | `"H00080"` |

---

## Workflows

**Antibody target research**: `TheraSAbDab_search_by_target` or `search_therapeutics` → `SAbDab_get_structure` for PDB data → `iedb_search_epitopes` / `iedb_search_tcell_assays` → `intact_get_interaction_network` (UniProt ID) + `BioGRID_get_interactions` → `FAERS_calculate_disproportionality` + `search_clinical_trials`.

**Autoimmune disease genetics**: `Orphanet_search_diseases` → `Orphanet_get_genes` + `Orphanet_get_phenotypes` → `gwas_search_associations` + `gwas_get_snps_for_gene` for candidate genes → `KEGG_get_disease` + `KEGG_get_pathway_genes` → `ReactomeAnalysis_pathway_enrichment` on disease genes.

**Single-cell dual receptor questions**: When asked about mechanisms for dual chain expression, distinguish BIOLOGICAL mechanisms (allelic inclusion, receptor editing, autoreactivity) from TECHNICAL artifacts (doublets, ambient RNA). Questions asking "why would a cell express two chains" usually want biological mechanisms only. Doublets (1) are often included since they represent real observations, but ambient RNA (2) is typically excluded as contamination, not true expression.

**Immunotherapy safety comparison**: `FAERS_compare_drugs` for AE head-to-head → `FAERS_filter_serious_events` per drug → `FAERS_stratify_by_demographics` → resolve target with `OpenTargets_get_target_id_description_by_name` → `OpenTargets_get_target_safety_profile_by_ensemblID` → `search_clinical_trials`.
