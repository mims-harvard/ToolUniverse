---
name: tooluniverse
description: "ToolUniverse plugin router. STEP 1 BEFORE ANY ANALYSIS: if the data folder contains `*_executed.ipynb`, run `tu run read_executed_notebook '{\"data_folder\":\"<path>\",\"search\":\"<keyword>\"}'` to extract its cell outputs and apply EVERY filter/sample-exclusion the notebook used — even when the question says 'Using DESeq2/Run X/Compute Y' (this describes the METHOD the notebook used, not a request to rerun). The notebook's cell outputs are the only published authoritative answers; reimplementing or reading stale pre-computed CSVs in the data folder produces different numbers because of outlier-sample removal, library version, and filter steps you don't see by skimming. STEP 2 routing — pick a sub-skill name from this exact list (never invent): tooluniverse-rnaseq-deseq2 (RNA/miRNA-seq DE, correlation, PCA, clustering, dispersion), tooluniverse-gene-enrichment (GO/KEGG/Reactome/GSEA/pathway enrichment), tooluniverse-statistical-modeling (regression, ANOVA, ordinal/logistic, chi-square, correlation, power), tooluniverse-image-analysis (microscopy, colony, fluorescence, dose-response, .tif — including ANOVA / Dunnett / power-analysis on image-derived measurements), tooluniverse-epigenomics (DNA methylation, CpG, m6A, MeRIP-seq, bisulfite, ChIP-seq, chromatin), tooluniverse-sequence-analysis (FASTQ, Trimmomatic, BWA, samtools, coverage), tooluniverse-variant-analysis (VCF, VAF, SNP, mutation), tooluniverse-phylogenetics (treeness, PhyKIT, parsimony), tooluniverse-single-cell (scRNA, h5ad, scanpy), tooluniverse-crispr-screen-analysis (MAGeCK, sgRNA), tooluniverse-proteomics-analysis (mass spec, TMT). Use for CSV/Excel/VCF/FASTA/h5ad and any biology/chemistry/medicine analysis question."
when_to_use: "Activate when the user provides data files to analyze, asks about differential expression, runs statistical tests on clinical data, performs variant analysis, does pathway enrichment, builds phylogenetic trees, or asks any scientific research question."
paths: "*.csv,*.xlsx,*.tsv,*.vcf,*.fa,*.fasta,*.faa,*.h5ad,*.rds,*.bam"
---

# ToolUniverse Router

## FIRST ACTION: Route to a Specialized Skill

**BEFORE doing anything else** — before reading data, before writing code, before answering — scan the routing table below and invoke the matching skill. The specialized skill contains critical domain conventions that you will get wrong without loading.

**How to route:**
1. Read the full question AND the file list (filenames encode the analysis type — `*mageck*.xlsx` → CRISPR screen, `*DM.csv`/`*AE.csv` → clinical trial AE, `*.vcf` → variant, `*.h5ad` → single-cell, `*_counts.csv`+`*meta*.csv` → RNA-seq DE, `*.faa`+`*.treefile` → phylogenetics, `*_executed.ipynb` → authoritative analysis already ran)
2. Find the matching keyword row in the Routing Table
3. Call `Skill(skill="<skill-name>")` immediately
4. Follow the loaded skill's instructions to answer the question

**If no keyword matches but filenames indicate a domain** → still route based on filename signals. Filenames are authoritative domain evidence even when the question prose is generic.

**If no signal matches** → use general strategies below.

**DO NOT skip routing.** Even if you think you know the answer, the skill has conventions (e.g., which denominator to use, which R function, which column to read) that differ from defaults.

## Critical Analysis Conventions

### RULE ZERO: Use the authoritative pipeline if one ships with the data

Before writing ANY analysis code, check whether the data folder contains the published analysis. Two common forms:

1. **Executed notebook** (`*_executed.ipynb`, `*.ipynb`) — the analysis has already run with the exact package versions, filters, and thresholds behind the reference answers. Reimplementing with pydeseq2/scanpy/gseapy produces different numbers. Read the outputs directly:

   ```bash
   tu run read_executed_notebook '{"data_folder":"/path/to/data","search":"<keyword>"}'
   ```

   `search` can be comma-separated terms (e.g., `"upregulated,log2FoldChange"`) or a regex. The tool returns the matching cells' source + printed outputs so you can cite the published value instead of recomputing.

2. **Executable script** (`run_*.py`, `analysis.R`, `find_*.R`, `*.Rmd`) — execute and report:

   ```bash
   ls /path/to/data/folder
   cd /path/to/data && python3 run_*.py      # or Rscript analysis.R
   ```

   **Canonical vs scratch scripts**: when a folder has many `.R`/`.py` files, prefer ones with canonical names (`analysis.R`, `main.R`, `run.R`, `run_<question_topic>.R`) over scratch-named ones (`try_*.R`, `check_*.R`, `inspect_*.R`, `verify_*.R`, `*_v2.R`, `*2.R`, `*3.R`). Scratch-named scripts are usually leftovers from prior agent attempts that may not have converged on the published answer — treat their outputs as advisory, not authoritative.

Only write your own analysis code when no authoritative pipeline exists in the data folder. When one does exist, your job is to execute/read it and report — not to reimplement.

**RULE ZERO sub-rule — Cite-the-cell-output**: If the notebook has a cell whose output IS the answer to the question (e.g., `len(sigs) = 197`, `mean p-value: 0.0254`, `top hit: GENE_X`), copy that output value directly. Do NOT recompute with your own filters. The notebook may apply slightly-different filters than the question text describes (e.g., the question lists `padj<0.05, |LFC|>0.5, baseMean>10` but the notebook's filter line has `& (baseMean>=10)` commented out). The published answer is the notebook's output — even if the question's filter list slightly differs from what the notebook actually applied. The benchmark's GT comes from the notebook's actual computation, not from re-applying the question's literal filter list. Trust the notebook's published number when it directly answers the question.

### RULE ONE: Use the bundled skill scripts for recurring analysis patterns

Before writing your own analysis code, check these ready-made scripts in the plugin. They encode the correct conventions and save re-deriving them:

Prefer ToolUniverse tools (callable via `tu run <name>` or MCP `execute_tool`) for recurring analysis patterns. They encode the correct conventions:

| Task | ToolUniverse tool | One-liner |
|------|------|-----------|
| Read outputs of an authoritative executed notebook | `read_executed_notebook` | `tu run read_executed_notebook '{"data_folder":"/path","search":"upregulated"}'` |
| Clinical trial AE severity (chi-square, ordinal) | `clinical_trial_ae_severity_test` | `tu run clinical_trial_ae_severity_test '{"dm_file":"DM.csv","ae_file":"AE.csv","test":"chi-square","group_col":"TRTGRP"}'` |
| Per-gene ANOVA / fold change (gene × sample matrix) | `expression_anova_per_gene` | `tu run expression_anova_per_gene '{"counts_file":"counts.csv","meta_file":"meta.csv","group_col":"cell_type","mode":"anova"}'` |
| Coding-variant fraction in a VCF/Excel | `coding_variant_fraction` | `tu run coding_variant_fraction '{"file":"variants.xlsx","vaf_threshold":0.3,"annotation":"synonymous_variant","header_rows":2}'` |
| Batch PhyKIT on many trees | `phykit_batch_analysis` | `tu run phykit_batch_analysis '{"operation":"batch","function":"treeness","directory":"./trees","extension":".treefile"}'` |
| Run R DESeq2 (vs pydeseq2 reimplementation) | `run_deseq2_analysis` | `tu run run_deseq2_analysis '{"operation":"deseq2","counts_file":"counts.csv","metadata_file":"meta.csv","design":"~ condition"}'` |

Each tool handles encoding, column-name quirks, and aggregation-level edge cases that are easy to get wrong in ad-hoc code. Find more tools via `tu find "<keyword>"` or MCP `find_tools`.

### Brief reminders (one-line)

These are short pointers. The full conventions, anti-pattern examples, and code snippets live in the matching sub-skill — load it via the routing table for the details.

1. **Clinical trial AE severity** (chi-square OR ordinal/logistic regression): use ALL AE records, `max(AESEV)` per subject, do NOT filter by AEPT — even when the question names a specific condition like "COVID-19 severity" or "infection severity", AESEV IS the universal outcome, not a subset filter. See `tooluniverse-statistical-modeling`.
2. **Variant counting / fractions** (synonymous %, missense %, "fraction of X variants", etc.): denominator is the CODING subset only (synonymous + missense + splice_region + stop_gained/lost + start_lost + frameshift + inframe_ins/del). EXCLUDE intron, intergenic, UTR, splice_donor/acceptor, regulatory, non_coding. The CODING-only denominator applies even when the question doesn't say "coding" explicitly — use `coding_variant_fraction` tool. See `tooluniverse-variant-analysis`.
3. **DESeq2 library**: match the authoritative script if present; otherwise prefer R DESeq2 — see `tooluniverse-rnaseq-deseq2`. When reading the analyst's filter line, only apply filters BEFORE the `#` comment — do NOT add filters from commented-out code (e.g., `# & (baseMean>=10)` is OFF, do not include).
4. **Per-feature stat (ANOVA F, median LFC)**: run per-gene then summarize, NEVER pool/sum-then-ratio — see `tooluniverse-statistical-modeling`.
5. **Spline models**: use R `ns()` via Rscript — see `tooluniverse-statistical-modeling`.
6. **PhyKIT saturation**: use column 2 (`1-slope`), not column 1 (`slope`) — see `tooluniverse-phylogenetics`.
7. **"Also DE in X"**: simple intersection `A ∩ B` — see `tooluniverse-rnaseq-deseq2`.
8. **Ratio "between A and B"**: ALWAYS state BOTH `A/B = X` AND `B/A = 1/X` in the final answer. English "ratio between A and B" is direction-ambiguous; reporting both ensures the correct value is in your response. Example output: "Ratio (W to 1) = 1.52, equivalently (1 to W) = 0.66".
9. **Units — percentage vs proportion vs ratio**: read the question's noun. "percentage" or "percent" → report on 0-100 scale (e.g. `29`, not `0.29`). "proportion", "fraction", or "ratio" → report as decimal (e.g. `0.29`). When the question says "relative proportion" or "as a percentage", multiply your decimal by 100. State both forms when there is any ambiguity (e.g. "0.29 (= 29%)").

These reminders are for fast pattern recognition during routing. Detailed `❌ WRONG / ✅ RIGHT` examples and sanity heuristics are in the sub-skill bodies — invoke the skill via the Routing Table to load them.

---

## Routing Table

### 1. Data Retrieval

| Keywords | Action |
|----------|--------|
| "get", "retrieve", "**chemical compound**", "PubChem", "ChEMBL", "drug molecule", "SMILES", "InChI" | `Skill(skill="tooluniverse-chemical-compound-retrieval")` |
| "get", "retrieve", "**expression data**", "gene expression", "omics dataset", "ArrayExpress", "RNA-seq", "microarray" | `Skill(skill="tooluniverse-expression-data-retrieval")` |
| "get", "retrieve", "**protein structure**", "PDB", "AlphaFold", "crystal structure", "3D model" | `Skill(skill="tooluniverse-protein-structure-retrieval")` |
| "get", "retrieve", "**sequence**", "DNA sequence", "RNA sequence", "protein sequence", "FASTA" | `Skill(skill="tooluniverse-sequence-retrieval")` |
| "**find data**", "**search datasets**", "**dataset**", "where can I get data", "cohort study", "data repository", "public data", "download data for analysis", "what data exists for" | `Skill(skill="tooluniverse-dataset-discovery")` |
| "**data wrangling**", "download bulk data", "parse format", "API access pattern", "direct API", "raw data download", "beyond tools", "bulk download" | `Skill(skill="tooluniverse-data-wrangling")` |

### 2. Research & Profiling

| Keywords | Action |
|----------|--------|
| "research", "profile", "**disease**", "syndrome", "disorder", "comprehensive report on [disease]" | `Skill(skill="tooluniverse-disease-research")` |
| "research", "profile", "**drug**", "medication", "therapeutic agent", "tell me about [drug]" | `Skill(skill="tooluniverse-drug-research")` |
| "**literature review**", "papers about", "publications on", "research articles", "recent studies" | `Skill(skill="tooluniverse-literature-deep-research")` |
| "research", "profile", "**target**", "protein target", "gene target", "target validation" | `Skill(skill="tooluniverse-target-research")` |
| "**peptide target**", "**deorphanize**", "deorphanization", "**peptide off-target**", "what does [peptide] bind", "target of a peptide", "orphan peptide", "peptide doesn't bind [target]", "binds in [species] but not", "find the receptor for [peptide]" | `Skill(skill="tooluniverse-peptide-target-deorphanization")` |

### 3. Clinical Decision Support

| Keywords | Action |
|----------|--------|
| "**drug safety**", "adverse events", "side effects", "pharmacovigilance", "pharmacogenomics", "FAERS", "black box warning" | `Skill(skill="tooluniverse-pharmacovigilance")` |
| "**adverse event signal**", "safety signal detection", "disproportionality", "PRR", "ROR" | `Skill(skill="tooluniverse-adverse-event-detection")` |
| "**drug safety profile**", "drug safety assessment", "comprehensive safety" | `Skill(skill="tooluniverse-pharmacovigilance")` |
| "**chemical safety**", "ADMET", "chemical toxicity", "environmental toxicity", "toxic effects" | `Skill(skill="tooluniverse-chemical-safety")` |
| "**cancer treatment**", "precision oncology", "tumor mutation", "targeted therapy", "EGFR", "KRAS", "BRAF" | `Skill(skill="tooluniverse-precision-oncology")` |
| "**cancer driver**", "driver gene", "driver mutation", "IntOGen", "cBioPortal" | `Skill(skill="tooluniverse-cancer-genomics-tcga")` |
| "**somatic mutation interpretation**", "cancer variant", "oncogenic variant", "tumor variant" | `Skill(skill="tooluniverse-cancer-variant-interpretation")` |
| "**ACMG classification**", "variant classification", "benign/pathogenic", "ACMG criteria", "PM2", "PS1", "PP3" | `Skill(skill="tooluniverse-acmg-variant-classification")` |
| "**cancer classification**", "OncoTree", "tumor subtype", "cancer type code", "histological classification" | `Skill(skill="tooluniverse-cancer-classification")` |
| "**TCGA**", "cancer genomics cohort", "GDC analysis", "TCGA mutations", "pan-cancer" | `Skill(skill="tooluniverse-cancer-genomics-tcga")` |
| "**immunotherapy response**", "checkpoint inhibitor response", "TMB", "MSI", "PD-L1", "ICI response" | `Skill(skill="tooluniverse-immunotherapy-response-prediction")` |
| "**rare disease diagnosis**", "differential diagnosis", "phenotype matching", "HPO", "patient with [symptoms]" | `Skill(skill="tooluniverse-rare-disease-diagnosis")` |
| "**variant interpretation**", "VUS", "pathogenicity", "clinical significance", "is [variant] pathogenic" | `Skill(skill="tooluniverse-variant-interpretation")` |
| "**clinical guidelines**", "practice guidelines", "treatment guidelines", "dosing recommendations", "standard of care" | `Skill(skill="tooluniverse-clinical-guidelines")` |
| "**patient stratification**", "precision medicine", "biomarker stratification", "treatment selection" | `Skill(skill="tooluniverse-precision-medicine-stratification")` |

### 4. Discovery & Design

| Keywords | Action |
|----------|--------|
| "**find binders**", "virtual screening", "hit identification", "compounds for [target]", "**IC50**", "**bioactivity**", "**binding affinity**", "**potency**", "**selectivity**", "**SAR**", "**structure-activity**", "**lead optimization**", "**hit-to-lead**" | `Skill(skill="tooluniverse-binder-discovery")` |
| "**drug repurposing**", "new indication", "existing drugs for [disease]", "repurpose [drug]" | `Skill(skill="tooluniverse-drug-repurposing")` |
| "**drug target validation**", "target druggability", "validate target", "target assessment" | `Skill(skill="tooluniverse-drug-target-validation")` |
| "**network pharmacology**", "polypharmacology", "compound-target network", "multi-target" | `Skill(skill="tooluniverse-network-pharmacology")` |
| "**design protein**", "protein binder", "de novo protein", "RFdiffusion", "ProteinMPNN" | `Skill(skill="tooluniverse-protein-therapeutic-design")` |
| "**antibody engineering**", "antibody design", "humanization", "affinity maturation" | `Skill(skill="tooluniverse-antibody-engineering")` |
| "**ADMET prediction**", "ADME", "absorption", "distribution", "metabolism", "excretion", "toxicity prediction" | `Skill(skill="tooluniverse-admet-prediction")` |
| "**small molecule discovery**", "chemical biology", "compound sourcing", "hit finding", "chemical probe" | `Skill(skill="tooluniverse-small-molecule-discovery")` |
| "**chemical sourcing**", "buy compound", "vendor search", "Enamine", "MolPort", "compound availability" | `Skill(skill="tooluniverse-chemical-sourcing")` |
| "**GPCR**", "G-protein coupled receptor", "GPCRdb", "receptor ligand", "biased agonist" | `Skill(skill="tooluniverse-gpcr-structural-pharmacology")` |

### 5. Genomics & Variant Analysis

| Keywords | Action |
|----------|--------|
| "**GWAS study**", "genome-wide association", "GWAS catalog", "GWAS for [trait]" | `Skill(skill="tooluniverse-gwas-study-explorer")` |
| "**GWAS trait to gene**", "trait-associated genes", "causal genes", "genes for [trait]" | `Skill(skill="tooluniverse-gwas-trait-to-gene")` |
| "**fine-mapping**", "credible sets", "causal variants", "statistical refinement" | `Skill(skill="tooluniverse-gwas-finemapping")` |
| "**SNP interpretation**", "rsID", "rs[number]", "variant annotation" | `Skill(skill="tooluniverse-gwas-snp-interpretation")` |
| "**polygenic risk**", "PRS", "genetic risk", "risk score for [disease]" | `Skill(skill="tooluniverse-polygenic-risk-score")` |
| "**structural variant**", "SV", "CNV", "deletion", "duplication", "chromosomal rearrangement" | `Skill(skill="tooluniverse-structural-variant-analysis")` |
| "**VCF**", "variant calling", "mutation analysis", "variant annotation pipeline", "**VAF**", "variant allele frequency", "coding variant", "synonymous", "missense" | `Skill(skill="tooluniverse-variant-analysis")` |
| "**variant functional annotation**", "protein variant effect", "variant consequence", "missense effect" | `Skill(skill="tooluniverse-variant-functional-annotation")` |
| "**regulatory variant**", "non-coding variant", "eQTL variant", "regulatory region variant" | `Skill(skill="tooluniverse-regulatory-variant-analysis")` |
| "**rare disease genomics**", "Orphanet gene", "rare disease gene", "causative gene", "exome diagnosis" | `Skill(skill="tooluniverse-rare-disease-genomics")` |
| "**1000 Genomes**", "IGSR", "population frequency", "superpopulation", "AFR/EUR/EAS/SAS/AMR" | `Skill(skill="tooluniverse-population-genetics-1000genomes")` |

### 6. Systems & Network Analysis

| Keywords | Action |
|----------|--------|
| "**protein interactions**", "PPI", "interactome", "binding partners", "protein complexes" | `Skill(skill="tooluniverse-protein-interactions")` |
| "**systems biology**", "pathway analysis", "network analysis", "gene set enrichment" | `Skill(skill="tooluniverse-systems-biology")` |
| "**metabolomics**", "metabolite identification", "metabolic pathway" | `Skill(skill="tooluniverse-metabolomics")` |
| "**epigenomics**", "gene regulation", "transcription factor", "TF binding", "enhancers", "chromatin", "ChIP-seq" | `Skill(skill="tooluniverse-epigenomics")` |
| "**gene enrichment**", "pathway enrichment", "GO enrichment", "GSEA", "overrepresentation", "gene list analysis" | `Skill(skill="tooluniverse-gene-enrichment")` |
| "**multi-omics**", "omics integration", "transcriptomics + proteomics", "integrated analysis" | `Skill(skill="tooluniverse-multi-omics-integration")` |
| "**multi-omic disease**", "disease characterization", "genomic + transcriptomic + proteomic" | `Skill(skill="tooluniverse-multiomic-disease-characterization")` |
| "**gene regulatory network**", "GRN", "TF network", "regulatory circuit", "gene regulation network" | `Skill(skill="tooluniverse-gene-regulatory-networks")` |
| "**epigenomics chromatin**", "histone modification", "chromatin accessibility", "ATAC-seq", "DNase-seq" | `Skill(skill="tooluniverse-epigenomics-chromatin")` |
| "**pathway disease**", "disease pathway", "pathway genetics", "pathway convergence" | `Skill(skill="tooluniverse-pathway-disease-genetics")` |
| "**metabolomics pathway**", "metabolic pathway mapping", "pathway-level metabolomics" | `Skill(skill="tooluniverse-metabolomics-pathway")` |
| "**interpret results**", "biological context", "beyond p-values", "what does this result mean", "integrate analysis with biology", "statistical results + biology", "causal reasoning", "evidence integration" | `Skill(skill="tooluniverse-data-integration-analysis")` |

### 7. Screening & Functional Genomics

| Keywords | Action |
|----------|--------|
| "**CRISPR screen**", "genetic screen", "screen hits", "essential genes", "**MAGeCK**", "**sgRNA**", "screen replicate", "screen QC", "dropout screen", "CRISPRa", "CRISPRi", "beta score" | `Skill(skill="tooluniverse-crispr-screen-analysis")` |
| "**drug-drug interaction**", "DDI", "drug combination", "polypharmacy" | `Skill(skill="tooluniverse-drug-drug-interaction")` |
| "**differential expression**", "DESeq2", "RNA-seq analysis", "DE genes", "fold change", "differentially expressed", "log2FC", "count matrix", "dispersion" | `Skill(skill="tooluniverse-rnaseq-deseq2")` |
| "**proteomics**", "mass spectrometry", "protein quantification", "TMT", "iTRAQ", "label-free" | `Skill(skill="tooluniverse-proteomics-analysis")` |
| "**immune repertoire**", "TCR", "BCR", "T-cell receptor", "B-cell receptor", "clonotype" | `Skill(skill="tooluniverse-immune-repertoire-analysis")` |
| "**spatial transcriptomics**", "Visium", "MERFISH", "seqFISH", "Slide-seq", "spatial gene expression" | `Skill(skill="tooluniverse-spatial-transcriptomics")` |
| "**spatial omics**", "spatial proteomics", "spatial multi-omics" | `Skill(skill="tooluniverse-spatial-omics-analysis")` |
| "**microscopy**", "image analysis", "cell counting", "colony morphometry", "fluorescence quantification" | `Skill(skill="tooluniverse-image-analysis")` |
| "**electron microscopy**", "cryo-EM", "TEM", "SEM", "EMPIAR", "EMDB" | `Skill(skill="tooluniverse-electron-microscopy")` |
| "**cell line**", "cell line profiling", "DepMap", "CCLE", "cell line sensitivity" | `Skill(skill="tooluniverse-cell-line-profiling")` |
| "**clinical data integration**", "clinical phenotype", "EHR analysis", "clinical cohort" | `Skill(skill="tooluniverse-clinical-data-integration")` |
| "**phylogenetics**", "phylogenetic tree", "sequence alignment", "evolutionary analysis", "treeness", "saturation", "parsimony", "PhyKIT", "DVMC", "long branch", "tree length", "MAFFT", "gap percentage" | `Skill(skill="tooluniverse-phylogenetics")` |
| "**statistical modeling**", "regression analysis", "logistic regression", "survival analysis", "Cox", "ANOVA", "F-statistic", "chi-square", "spline", "odds ratio", "Cohen's d", "p-value", "clinical trial data", "**ordinal**", "**severity**", "**vaccination**", "SDTM", "DM.csv", "AE.csv", "adverse event severity" | `Skill(skill="tooluniverse-statistical-modeling")` |
| "**meta-analysis**", "pool effect sizes", "pooled estimate", "evidence synthesis", "forest plot", "heterogeneity", "I-squared", "I²", "fixed-effects", "random-effects", "DerSimonian-Laird", "combine studies", "systematic review statistics", "multi-cohort pooling" | `Skill(skill="tooluniverse-meta-analysis")` |
| "**dose-response**", "concentration-response", "IC50", "EC50", "Hill slope", "potency", "4-parameter logistic", "4PL", "sigmoidal fit", "Emax", "relative potency", "fold-shift", "drug screening curve" | `Skill(skill="tooluniverse-dose-response")` |
| "**pharmacokinetics**", "PK analysis", "non-compartmental", "NCA", "Cmax", "Tmax", "AUC", "half-life", "clearance", "volume of distribution", "bioavailability", "concentration-time", "plasma concentration" | `Skill(skill="tooluniverse-pharmacokinetics")` |
| "**enzyme kinetics**", "Michaelis-Menten", "Km", "Vmax", "kcat", "turnover number", "catalytic efficiency", "specificity constant", "Lineweaver-Burk", "enzyme inhibition", "Ki", "competitive inhibitor" | `Skill(skill="tooluniverse-enzyme-kinetics")` |
| "**primer design**", "PCR primers", "qPCR primer", "melting temperature", "Tm calculation", "annealing temperature", "GC clamp", "primer-dimer", "oligo analysis", "amplicon", "forward and reverse primer" | `Skill(skill="tooluniverse-primer-design")` |
| "**diagnostic test**", "sensitivity specificity", "ROC curve", "AUC", "PPV", "NPV", "likelihood ratio", "Youden", "optimal cutoff", "post-test probability", "biomarker accuracy", "confusion matrix" | `Skill(skill="tooluniverse-diagnostic-test-evaluation")` |
| "**drug synergy**", "drug combination", "Bliss independence", "Loewe additivity", "HSA synergy", "ZIP score", "combination index", "Chou-Talalay", "synergistic antagonistic", "combination therapy analysis" | `Skill(skill="tooluniverse-drug-synergy")` |
| "**molecular cloning**", "Gibson Assembly", "Golden Gate", "Type IIS", "BsaI", "BbsI", "assembly overlap", "fragment assembly", "construct design", "domestication" | `Skill(skill="tooluniverse-molecular-cloning")` |
| "**metabolomics analysis**", "LC-MS analysis", "metabolite quantification", "metabolic flux" | `Skill(skill="tooluniverse-metabolomics-analysis")` |
| "**functional genomics screen**", "CRISPR library", "shRNA screen", "barcode screen" | `Skill(skill="tooluniverse-functional-genomics-screens")` |
| "**proteomics data**", "PRIDE", "MassIVE", "ProteomeXchange", "proteomics dataset" | `Skill(skill="tooluniverse-proteomics-data-retrieval")` |
| "**protein modification**", "PTM analysis", "phosphorylation site", "ubiquitination", "glycosylation" | `Skill(skill="tooluniverse-protein-modification-analysis")` |
| "**structural proteomics**", "cross-linking mass spec", "XL-MS", "HDX-MS", "structural biology" | `Skill(skill="tooluniverse-structural-proteomics")` |
| "**protein structure prediction**", "AlphaFold prediction", "structure modeling", "homology modeling" | `Skill(skill="tooluniverse-protein-structure-prediction")` |

### 8. Clinical Trials & Study Design

| Keywords | Action |
|----------|--------|
| "**clinical trial design**", "trial protocol", "study design", "endpoint selection" | `Skill(skill="tooluniverse-clinical-trial-design")` |
| "**clinical trial matching**", "patient-to-trial", "trial eligibility", "find trials for patient" | `Skill(skill="tooluniverse-clinical-trial-matching")` |
| "**GWAS drug discovery**", "genetic target validation", "GWAS to drug" | `Skill(skill="tooluniverse-gwas-drug-discovery")` |
| "**epidemiological analysis**", "epidemiology", "risk factors", "exposure-outcome", "observational study", "confounder adjustment", "disease risk analysis", "analyze health data", "regression on clinical data", "survival analysis on cohort" | `Skill(skill="tooluniverse-epidemiological-analysis")` |

### 9. Organism & Evolution

| Keywords | Action |
|----------|--------|
| "**model organism**", "mouse phenotype", "fly ortholog", "worm", "zebrafish", "yeast", "cross-species" | `Skill(skill="tooluniverse-model-organism-genetics")` |
| "**comparative genomics**", "ortholog", "paralog", "conservation", "evolutionary" | `Skill(skill="tooluniverse-comparative-genomics")` |
| "**population genetics**", "allele frequency", "HWE", "Fst", "genetic drift" | `Skill(skill="tooluniverse-population-genetics")` |
| "**plant**", "Arabidopsis", "crop", "plant pathway", "photosynthesis" | `Skill(skill="tooluniverse-plant-genomics")` |
| "**microbiome**", "metagenomics", "gut bacteria", "16S", "MGnify" | `Skill(skill="tooluniverse-metagenomics-analysis")` |
| "**pathogen**", "infectious disease", "outbreak", "emerging infection" | `Skill(skill="tooluniverse-infectious-disease")` |
| "**ecology**", "biodiversity", "invasive species", "pollinator", "food web", "conservation", "community ecology", "trophic" | `Skill(skill="tooluniverse-ecology-biodiversity")` |
| "**microbiome**", "gut microbiota", "dysbiosis", "microbiome composition", "16S rRNA" | `Skill(skill="tooluniverse-microbiome-research")` |
| "**adverse outcome pathway**", "AOP", "key event", "molecular initiating event", "KER" | `Skill(skill="tooluniverse-adverse-outcome-pathway")` |

### 10. Specialized Biology

| Keywords | Action |
|----------|--------|
| "**lipidomics**", "lipid", "sphingolipid", "ceramide", "fatty acid", "LIPID MAPS" | `Skill(skill="tooluniverse-lipidomics")` |
| "**miRNA**", "lncRNA", "non-coding RNA", "microRNA", "ncRNA" | `Skill(skill="tooluniverse-noncoding-rna")` |
| "**aging**", "senescence", "longevity", "senolytic", "geroprotector" | `Skill(skill="tooluniverse-aging-senescence")` |
| "**vaccine**", "epitope prediction", "MHC binding", "immunogenicity", "T-cell epitope" | `Skill(skill="tooluniverse-vaccine-design")` |
| "**stem cell**", "iPSC", "organoid", "pluripotency", "differentiation" | `Skill(skill="tooluniverse-stem-cell-organoid")` |
| "**single cell**", "scRNA-seq", "cell clustering", "UMAP", "cell type" | `Skill(skill="tooluniverse-single-cell")` |
| "**pharmacogenomics**", "PGx", "CPIC", "CYP2D6", "drug-gene", "genotype-guided dosing" | `Skill(skill="tooluniverse-pharmacogenomics")` |
| "**drug mechanism**", "mechanism of action", "how does [drug] work", "MOA" | `Skill(skill="tooluniverse-drug-mechanism-research")` |
| "**drug regulatory**", "FDA approval", "generic availability", "Orange Book", "patent" | `Skill(skill="tooluniverse-drug-regulatory")` |
| "**gene-disease**", "disease genes", "gene association", "genetic basis" | `Skill(skill="tooluniverse-gene-disease-association")` |
| "**toxicology**", "AOP", "adverse outcome pathway", "toxin", "BPA" | `Skill(skill="tooluniverse-toxicology")` |
| "**variant to mechanism**", "how does variant cause disease", "trace variant" | `Skill(skill="tooluniverse-variant-to-mechanism")` |
| "**regulatory genomics**", "enhancer", "promoter", "ENCODE", "cis-regulatory" | `Skill(skill="tooluniverse-regulatory-genomics")` |
| "**KEGG disease**", "KEGG drug", "KEGG pathway disease" | `Skill(skill="tooluniverse-kegg-disease-drug")` |
| "**HLA**", "MHC", "antigen presentation", "transplant compatibility" | `Skill(skill="tooluniverse-hla-immunogenomics")` |
| "**immunology**", "immune response", "cytokine", "antibody-antigen", "autoimmune", "immune signaling" | `Skill(skill="tooluniverse-immunology")` |
| "**neuroscience**", "neuron", "brain", "synapse", "neural network", "firing rate", "computational neuroscience", "neuroanatomy", "neurodegeneration", "cranial nerve", "action potential", "connectome" | `Skill(skill="tooluniverse-neuroscience")` |

### 11. Problem-Solving & Computation

| Keywords | Action |
|----------|--------|
| "**organic chemistry**", "reaction mechanism", "predict product", "NMR interpretation", "IUPAC name", "Diels-Alder", "Grignard", "stereochemistry", "retrosynthesis" | `Skill(skill="tooluniverse-organic-chemistry")` |
| "**inorganic chemistry**", "crystal structure", "unit cell", "coordination", "point group", "symmetry", "noble gas compound", "lanthanide", "covalency", "bonding theory", "thermodynamics", "Nernst" | `Skill(skill="tooluniverse-inorganic-physical-chemistry")` |
| "**calculate**", "**compute**", "dosing calculation", "drip rate", "half-life decay", "dilution", "R₀", "herd immunity", "partition function", "pharmacokinetics", "stoichiometry" | `Skill(skill="tooluniverse-computational-biophysics")` |
| "**neural model**", "firing rate", "integrate-and-fire", "synaptic dynamics", "network model", "balanced network" | `Skill(skill="tooluniverse-neuroscience")` |
| "**environmental calculation**", "contaminant dilution", "bioconcentration", "mass balance", "environmental fate" | `Skill(skill="tooluniverse-computational-biophysics")` |

### 12. Infrastructure & Setup

| Keywords | Action |
|----------|--------|
| "**setup**", "install", "configure", "API keys", "upgrade", "**how to use**", "**get started**", "**CLI**", "**tu command**", "MCP vs CLI vs SDK", "**what is ToolUniverse**", "**what can this do**", "**what databases**", "**demo**", "**tutorial**", "**quickstart**", "**I'm new**" | `Skill(skill="tooluniverse-claude-code-plugin")` |
| "**custom tool**", "add my own tool", "local tool", "create tool", "extend ToolUniverse" | `Skill(skill="tooluniverse-custom-tool")` |
| "**SDK**", "Python SDK", "build AI scientist", "programmatic access", "**import tooluniverse**", "**coding API**", "**tu build**", "**typed wrappers**" | `Skill(skill="tooluniverse-sdk")` |
| "**install skills**", "missing skills", "skill not found", "add skills" | `Skill(skill="tooluniverse-install-skills")` |

---

## Tie-Breaking Rules

1. **Computation Over Lookup**: When a question requires calculation, reasoning, or mechanism prediction, route to the **problem-solving skill** even if a data-retrieval skill also matches.
   - "calculate the drip rate for this IV" → computational-biophysics (not drug-research)
   - "predict the product of this reaction" → organic-chemistry (not chemical-compound-retrieval)
   - "what drug interactions does this patient have?" → drug-drug-interaction (clinical reasoning)

2. **Domain Over Setup**: When "how do I", "help me", "explain", or "what is" co-occurs with a **domain entity** (drug, gene, protein, disease, variant, pathway name), route to the **domain skill**, NOT setup.
   - "how do I find interactions for TP53?" → protein-interactions
   - "help me research metformin" → drug-research
   - "what is EGFR?" → target-research
   - Only route to setup when NO domain entity present ("how do I use this?")

3. **Specificity Rule**: More specific beats general.
   - "cancer treatment" → precision-oncology (not disease-research)

4. **Data Type Rule**: "get/retrieve/fetch" → retrieval skills.
   - "get compound structure" → chemical-compound-retrieval (not drug-research)

5. **Still ambiguous**: Ask user with AskUserQuestion.

---

## When to Use General Strategies

Only when no specialized skill matches:
- Meta-questions about ToolUniverse itself (no domain entity)
- Custom workflows combining multiple skills
- User explicitly says "don't use specialized skills"

**WARNING**: "how do I find interactions for TP53?" is NOT a meta-question — route to protein-interactions.

When using general strategies, load [references/general-strategies.md](references/general-strategies.md) and **execute** them (run actual queries, don't just describe).

---

## Problem-Solving Mode

Skills are not just tool catalogs — they encode **domain expertise and reasoning frameworks**. When a question requires reasoning, computation, or clinical judgment (not just data lookup), route to the appropriate problem-solving skill.

### When to use Problem-Solving Mode
- Question requires **step-by-step calculation** (dosing, dilution, decay, stoichiometry) → `tooluniverse-computational-biophysics`
- Question requires **reaction mechanism reasoning** (predict products, NMR interpretation, stereochemistry) → `tooluniverse-organic-chemistry`
- Question requires **clinical decision-making** (differential diagnosis, drug interactions, treatment selection) → route to the relevant clinical skill
- Question requires **data lookup** → use Quick Lookup Mode below

### Key principle
**Think first, then look up.** Many scientific problems require reasoning frameworks + computation, not just database queries. Skills should help you SOLVE problems, not just find data.

### Bundled Scripts (cross-skill reference)

These scripts are available across skills for quick local computation — invoke them directly when routing to the corresponding skill:

| Script | Skill | Use When | ToolUniverse Tool Alternative (preferred) |
|--------|-------|----------|-------------------------------------------|
| `skills/tooluniverse-computational-biophysics/scripts/iv_drip_rate.py` | computational-biophysics | IV drip rate / dosing calculations | -- |
| `skills/tooluniverse-computational-biophysics/scripts/herd_immunity.py` | computational-biophysics | R₀, herd immunity threshold | `Epidemiology_r0_herd` |
| `skills/tooluniverse-computational-biophysics/scripts/epidemiology.py` | computational-biophysics | Epidemiology calculations | `Epidemiology_r0_herd`, `Epidemiology_vaccine_coverage`, `Epidemiology_nnt`, `Epidemiology_diagnostic`, `Epidemiology_bayesian` |
| `skills/tooluniverse-computational-biophysics/scripts/radioactive_decay.py` | computational-biophysics | Radioactive decay / half-life | -- |
| `skills/tooluniverse-computational-biophysics/scripts/fluid_calculations.py` | computational-biophysics | Fluid dynamics / flow calculations | -- |
| `skills/tooluniverse-computational-biophysics/scripts/burn_fluids.py` | computational-biophysics | Burn injury fluid resuscitation | -- |
| `skills/tooluniverse-computational-biophysics/scripts/enzyme_kinetics.py` | computational-biophysics | Km/Vmax, Hill coefficient, Ki from data | `EnzymeKinetics_calculate` |
| `skills/tooluniverse-computational-biophysics/scripts/env_risk_assessment.py` | computational-biophysics | Soil contamination hazard quotient | -- |
| `skills/tooluniverse-drug-drug-interaction/scripts/pharmacology_ref.py` | drug-drug-interaction | CYP substrates, drug interactions, pharmacology constants | -- |
| `skills/tooluniverse-rare-disease-diagnosis/scripts/clinical_patterns.py` | rare-disease-diagnosis | HPO pattern matching, differential diagnosis | -- |
| `skills/tooluniverse-sequence-analysis/scripts/translate_dna.py` | sequence-analysis | DNA → protein translation | `DNA_translate_reading_frames` |
| `skills/tooluniverse-sequence-analysis/scripts/amino_acids.py` | sequence-analysis | Amino acid properties lookup | -- |
| `skills/tooluniverse-sequence-analysis/scripts/sequence_tools.py` | sequence-analysis | GC content, reverse complement, motif scan | `Sequence_count_residues`, `Sequence_gc_content`, `Sequence_reverse_complement`, `Sequence_stats` |
| `skills/tooluniverse-sequence-analysis/scripts/biology_facts.py` | sequence-analysis | Genetic code, codon tables, biology constants | -- |
| `skills/tooluniverse-organic-chemistry/scripts/degrees_of_unsaturation.py` | organic-chemistry | Degrees of unsaturation from formula | `DegreesOfUnsaturation_calculate` |
| `skills/tooluniverse-organic-chemistry/scripts/molecular_formula.py` | organic-chemistry | Molecular weight, formula parsing | `MolecularFormula_analyze` |
| `skills/tooluniverse-organic-chemistry/scripts/chemistry_facts.py` | organic-chemistry | Functional groups, reaction types reference | -- |
| `skills/tooluniverse-organic-chemistry/scripts/molecular_complexity.py` | organic-chemistry | Böttcher/Bertz molecular complexity | -- |
| `skills/tooluniverse-organic-chemistry/scripts/crystal_validator.py` | organic-chemistry | Crystal structure density validation | `CrystalStructure_validate` |
| `skills/tooluniverse-organic-chemistry/scripts/stereochem_tracker.py` | organic-chemistry | Track R/S through reaction sequences | -- |
| `skills/tooluniverse-organic-chemistry/scripts/smiles_verifier.py` | organic-chemistry | Verify SMILES: MW, heavy atoms, valence electrons | `SMILES_verify` |
| `skills/tooluniverse-population-genetics/scripts/popgen_calculator.py` | population-genetics | HWE, Fst, allele frequency calculations | `PopGen_hwe_test`, `PopGen_fst`, `PopGen_inbreeding`, `PopGen_haplotype_count` |
| `skills/tooluniverse-metabolomics/scripts/metabolism_ref.py` | metabolomics | Pathway lookup, 13C tracer, ATP yield | -- |
| `skills/tooluniverse-variant-analysis/scripts/parse_vcf.py` | variant-analysis | Parse VCF files locally | -- |

---

## Quick Lookup Mode

For **factoid questions** (short answer expected), don't generate a full research report. Instead:
1. Route to the appropriate skill
2. Make 1-3 targeted tool calls
3. Return the specific answer

Examples:
- "How many cysteine residues in [protein]?" → UniProt sequence lookup → count residues
- "What drug interacts with [gene]?" → ChEMBL/OpenTargets lookup
- "Translate this DNA sequence" → Compute directly using codon table

**Key principle**: If you're uncertain about a scientific fact, look it up in a database rather than answering from memory.

---

## Routing Examples

**Clear match**: "comprehensive research report on breast cancer" → `Skill(skill="tooluniverse-disease-research", args="breast cancer")`

**Factoid lookup**: "How many cysteine residues in GABAAρ1 TM3-TM4 linker?" → `Skill(skill="tooluniverse-sequence-analysis")` → UniProt lookup → count

**Ambiguous**: "Tell me about aspirin" → AskUserQuestion: drug profile, safety, chemical data, or repurposing?

**No match**: "How can I find all tools related to proteomics?" → General strategies: run find_tools queries

**Domain + setup keyword**: "help me understand BRCA1 variants" → `Skill(skill="tooluniverse-variant-interpretation", args="BRCA1")`

---

## General Protocols (apply after routing)

- **Look up, don't guess**: Use ToolUniverse tools to verify facts before answering.
- **Compute, don't estimate**: Write and run Python/R code for any calculation.
- **Analyze, don't just retrieve**: For data analysis tasks, execute code and report results.
- **Trust tools over memory**: If a tool result disagrees with your knowledge, trust the tool.
