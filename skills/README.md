# ToolUniverse Skills

229 skills for AI agents: 153 research skills, 11 for setup and access, 63 that install a GPU-backed model on this machine, and 2 for developing ToolUniverse itself. Skills are automatically available — just ask naturally.

```
"Find the E. coli K-12 genome"           → tooluniverse-sequence-retrieval
"What do we know about Alzheimer's?"      → tooluniverse-disease-research
"Assess EGFR as a drug target"            → tooluniverse-target-research
"Run differential expression on my data"  → tooluniverse-rnaseq-deseq2
```

## Install

```bash
npx skills add mims-harvard/ToolUniverse
```

## All Skills

### Research Skills (153)

| Skill | Description |
|-------|-------------|
| `tooluniverse-acmg-variant-classification` | Systematic ACMG/AMP germline variant classification with all 28 criteria (PVS1, PS1-4, PM1-6, PP1-5, BA1,... |
| `tooluniverse-admet-prediction` | Comprehensive ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) profiling for drug candidates |
| `tooluniverse-adverse-event-detection` | Detect and analyze adverse drug event signals using FDA FAERS reports, drug labels, and disproportionality... |
| `tooluniverse-adverse-outcome-pathway` | Map environmental and industrial chemicals to adverse outcome pathways (AOPs) — molecular initiating event to... |
| `tooluniverse-aging-senescence` | Aging biology, cellular senescence, and longevity research |
| `tooluniverse-antibody-engineering` | Therapeutic antibody engineering and optimization, lead-to-clinical-candidate |
| `tooluniverse-binder-discovery` | Discover novel small-molecule binders for protein targets using structure-based and ligand-based screening |
| `tooluniverse-bioinformatics-resource-discovery` | Discover which bioinformatics software tool, biomedical REST API, R/Bioconductor package, CRAN package, or... |
| `tooluniverse-biomedical-fact-lookup` | Answer biomedical FACTUAL / recall / multiple-choice questions by querying ToolUniverse database tools instead... |
| `tooluniverse-cancer-classification` | Translate free-text tumor descriptions to OncoTree codes and resolve cancer subtypes/tissue hierarchy |
| `tooluniverse-cancer-genomics-tcga` | TCGA/GDC cancer genomics analysis — cohort construction, clinical metadata retrieval, somatic mutation... |
| `tooluniverse-cancer-variant-interpretation` | Clinical interpretation of somatic cancer mutations for precision oncology |
| `tooluniverse-cell-line-profiling` | Cancer cell-line selection and profiling for experimental model choice |
| `tooluniverse-chemical-compound-retrieval` | Retrieve chemical compound data from PubChem and ChEMBL with disambiguation, cross-referencing, and... |
| `tooluniverse-chemical-safety` | Chemical safety and toxicology assessment integrating ADMET-AI predictions, CTD toxicogenomics, PubChemTox... |
| `tooluniverse-chemical-sourcing` | Find commercial sources for chemical compounds — PubChem/ChEMBL identity resolution then vendor catalog search... |
| `tooluniverse-clinical-data-integration` | End-to-end drug safety review integrating FDA labels, FAERS adverse event reports, PRR/ROR disproportionality,... |
| `tooluniverse-clinical-guidelines` | Search and retrieve clinical practice guidelines from 12+ authoritative sources — NICE, WHO, NCCN, AHA, ADA,... |
| `tooluniverse-clinical-risk-scoring` | Compute and interpret validated bedside clinical risk scores and pretest probabilities for an INDIVIDUAL... |
| `tooluniverse-clinical-terminology-lookup` | Fast autocomplete/normalization lookups against the NLM Clinical Table Search Service — resolve a partial or... |
| `tooluniverse-clinical-trial-design` | Strategic clinical trial design feasibility assessment |
| `tooluniverse-clinical-trial-matching` | AI-driven patient-to-trial matching for precision oncology and rare-disease care |
| `tooluniverse-clinical-trial-protocol` | Generate a full clinical trial protocol document (ICH E6(R2)/FDA-style) for a drug or medical device, including... |
| `tooluniverse-comparative-genomics` | Cross-species gene comparison and ortholog analysis |
| `tooluniverse-computational-biophysics` | Solve quantitative problems in biophysics — pharmacokinetics (PK volume of distribution, clearance, half-life),... |
| `tooluniverse-crispr-screen-analysis` | Analyze CRISPR-Cas9 genetic screens — MAGeCK gene-level scores, sgRNA count QC, replicate correlation, hit... |
| `tooluniverse-data-integration-analysis` | Integrate computed statistical results (DEGs, GWAS hits, associations) with biological context from... |
| `tooluniverse-data-wrangling` | Universal data access patterns for downloading and parsing scientific data when ToolUniverse tools don't cover... |
| `tooluniverse-dataset-discovery` | Find and evaluate research datasets for any scientific question |
| `tooluniverse-diagnostic-test-evaluation` | Diagnostic test / biomarker accuracy — sensitivity, specificity, PPV, NPV, likelihood ratios, accuracy from a... |
| `tooluniverse-disease-research` | Generate comprehensive disease research reports covering genetics (causal genes, GWAS, OMIM), pathways... |
| `tooluniverse-dose-response` | Dose-response / concentration-response curve fitting — IC50, EC50, Hill slope, Emax/Emin efficacy, and relative... |
| `tooluniverse-drug-drug-interaction` | Assess drug-drug interactions — CYP metabolic interactions (substrate/inhibitor/inducer), transporter (P-gp,... |
| `tooluniverse-drug-mechanism-research` | Trace drug mechanism of action — primary target → downstream signaling → pathway perturbation → tissue/organ... |
| `tooluniverse-drug-regulatory` | Drug regulatory and approval research — FDA substance registry, ATC/EPC classification, EMA decisions,... |
| `tooluniverse-drug-repurposing` | Identify drug repurposing candidates via target-based, compound-based, and disease-based strategies |
| `tooluniverse-drug-research` | Comprehensive drug profiling — mechanism, primary/secondary targets, drug interactions, clinical-trial status,... |
| `tooluniverse-drug-synergy` | Drug-combination synergy analysis — quantify whether two drugs together are synergistic, additive, or... |
| `tooluniverse-drug-target-validation` | Quantitative drug-target validation pipeline |
| `tooluniverse-ecology-biodiversity` | Ecology, biodiversity, and conservation biology research — species identification (GBIF, NCBI Taxonomy),... |
| `tooluniverse-electron-microscopy` | Search and analyze electron microscopy data — cryo-EM density maps (EMDB), fitted atomic models (PDB), raw... |
| `tooluniverse-enzyme-design` | De novo enzyme design by catalytic-motif scaffolding — build a transition-state motif, generate scaffolds with... |
| `tooluniverse-enzyme-kinetics` | Enzyme kinetics — Michaelis-Menten Km, Vmax, kcat (turnover), and kcat/Km (catalytic efficiency / specificity... |
| `tooluniverse-epidemiological-analysis` | End-to-end observational epidemiology analysis — from research question (PECO... |
| `tooluniverse-epigenomics` | Genomics and epigenomics analysis: DNA methylation (CpG, 5mC, 5hmC, bisulfite, RRBS), m6A RNA modification... |
| `tooluniverse-epigenomics-chromatin` | Histone-modification ChIP-seq, ATAC-seq accessibility, chromatin state, and TF binding analysis from ENCODE,... |
| `tooluniverse-expression-data-retrieval` | Retrieve gene expression and omics datasets from ArrayExpress and BioStudies with gene disambiguation and... |
| `tooluniverse-fastq-qc` | FASTQ quality control and adapter/quality-trimming decisions with local NGS tools — run FastQC on raw reads,... |
| `tooluniverse-functional-genomics-screens` | Interpret hits from CRISPR-KO/CRISPRi/shRNA screens by integrating DepMap essentiality, gnomAD constraint... |
| `tooluniverse-gene-disease-association` | Gene-disease association analysis across DisGeNET, OpenTargets, Monarch, OMIM, GenCC, Orphanet, Gene2Phenotype... |
| `tooluniverse-gene-enrichment` | Gene-set enrichment analysis — GO (Biological Process, Molecular Function, Cellular Component), KEGG, Reactome... |
| `tooluniverse-gene-liability` | Evaluate the human safety liability of knocking down, knocking out, degrading, or pharmacologically inhibiting... |
| `tooluniverse-gene-regulatory-networks` | Gene regulatory network analysis — TF-target inference (JASPAR motifs, ChIP-seq), motif scanning, eQTL... |
| `tooluniverse-glycobiology` | Glycobiology and glycomics research using GlyGen — glycan structure lookup by GlyTouCan accession, glycan... |
| `tooluniverse-gpcr-structural-pharmacology` | GPCR receptor pharmacology — agonist/antagonist/inverse-agonist/biased-agonist classification, GPCRdb... |
| `tooluniverse-gwas-drug-discovery` | Transform GWAS signals into drug targets and repurposing opportunities |
| `tooluniverse-gwas-finemapping` | Statistical fine-mapping of GWAS loci using credible sets (SuSiE, FINEMAP) and locus-to-gene scoring (Open... |
| `tooluniverse-gwas-snp-interpretation` | Interpret a single GWAS SNP across multiple databases — GWAS Catalog hits, LD/haplotype context, eQTL evidence,... |
| `tooluniverse-gwas-study-explorer` | Compare GWAS studies, perform meta-analyses across cohorts, and assess signal replication |
| `tooluniverse-gwas-trait-to-gene` | Discover causal genes for diseases/traits from GWAS data using Open Targets L2G (locus-to-gene) scoring —... |
| `tooluniverse-hla-immunogenomics` | HLA gene-family analysis and MHC-peptide binding for transplant compatibility, vaccine epitope coverage, and... |
| `tooluniverse-image-analysis` | Microscopy and quantitative imaging analysis — colony morphometry, fluorescence intensity quantification,... |
| `tooluniverse-immune-repertoire-analysis` | TCR/BCR repertoire analysis — V(D)J segment usage, CDR3 sequence diversity, clonality scoring, antigen... |
| `tooluniverse-immunology` | Immunology research workflows: antibody-antigen interactions, T/B cell repertoire, MHC/HLA binding prediction,... |
| `tooluniverse-immunotherapy-response-prediction` | Predict patient response to immune checkpoint inhibitors (ICIs) by integrating tumor mutational burden (TMB),... |
| `tooluniverse-infectious-disease` | Rapid pathogen characterization and drug repurposing for outbreaks |
| `tooluniverse-inorganic-physical-chemistry` | Inorganic chemistry, physical chemistry, and materials science — crystal structures, coordination chemistry,... |
| `tooluniverse-install-skills` | Detect and auto-install missing ToolUniverse research skills |
| `tooluniverse-kegg-disease-drug` | KEGG-based disease-drug-variant network research |
| `tooluniverse-lab-data-standardization` | Convert lab instrument output files (CSV, TSV, Excel, PDF — plate readers, spectrophotometers like NanoDrop,... |
| `tooluniverse-lab-protocols` | Find and inspect published, peer-reviewed or community lab protocols from protocols.io — search by... |
| `tooluniverse-lipidomics` | Lipid analysis and lipid-disease associations using LIPID MAPS classification, HMDB metabolite data,... |
| `tooluniverse-literature-deep-research` | Deep literature review — PubMed, EuropePMC, bioRxiv preprints, citation networks, evidence synthesis |
| `tooluniverse-medical-imaging-radiology` | Discover and characterize cancer radiology imaging cohorts from The Cancer Imaging Archive (TCIA) — list public... |
| `tooluniverse-mendelian-randomization` | Mendelian randomization (MR) causal inference — does an exposure, risk factor, or biomarker CAUSALLY affect a... |
| `tooluniverse-meta-analysis` | Meta-analysis / evidence synthesis — pool effect sizes across studies (odds ratios, risk ratios, hazard ratios,... |
| `tooluniverse-metabolomics` | Metabolomics research — metabolite identification, study analysis, and database searches across HMDB,... |
| `tooluniverse-metabolomics-analysis` | Analyze metabolomics data end-to-end — metabolite identification, quantification (TIC normalization, batch... |
| `tooluniverse-metabolomics-pathway` | Metabolomics pathway analysis — metabolite identification (HMDB, KEGG, ChEBI), pathway mapping (Reactome, KEGG,... |
| `tooluniverse-metagenomics-analysis` | Microbiome and metagenomics analysis using MGnify, GTDB taxonomy, ENA sequencing data, and EuropePMC literature |
| `tooluniverse-microbial-genome-characterization` | Genome-ASSEMBLY discovery, QC, and replicon mapping for any organism (bacteria, archaea, fungi, and beyond)... |
| `tooluniverse-microbiome-research` | Microbiome research using MGnify, GTDB, ENA, OLS (ENVO biomes), EuropePMC, BacDive (strain phenotypes),... |
| `tooluniverse-ml-inference-utility` | Generic ML/NLP/vision inference against any HuggingFace-hosted model (serverless hf-inference provider) — text... |
| `tooluniverse-model-organism-genetics` | Cross-species genetic analysis using model organism databases (MGI mouse, IMPC systematic knockout phenotyping,... |
| `tooluniverse-molecular-cloning` | Molecular cloning, in both directions |
| `tooluniverse-multi-omics-integration` | Multi-omics integration — orchestrate per-layer analysis (transcriptomics, proteomics, epigenomics, genomics,... |
| `tooluniverse-multiomic-disease-characterization` | Comprehensive disease characterization across genomics, transcriptomics, proteomics, and pathways for... |
| `tooluniverse-natural-product-dereplication` | Dereplicate a putative natural product and assign its chemical taxonomy |
| `tooluniverse-network-pharmacology` | Compound-target-disease network construction and analysis for drug repurposing, polypharmacology discovery, and... |
| `tooluniverse-neuroscience` | Neuroscience research workflows: neuroanatomy, neural circuits, neurotransmitter biology,... |
| `tooluniverse-neurosynth-meta-analysis` | Meta-analytic decoding of human fMRI coordinates using the Neurosynth coordinate database (14,371 studies,... |
| `tooluniverse-nfcore-pipelines` | Run real end-to-end bioinformatics pipelines (nf-core rnaseq, sarek, atacseq) via Nextflow +... |
| `tooluniverse-nih-funding-landscape` | Analyze NIH grant portfolios and funding history using the OpenNIH FY1985-present corpus, then connect grants... |
| `tooluniverse-noncoding-rna` | Non-coding RNA analysis — miRNAs (miRBase, miRDB targets), lncRNAs (LNCipedia, RNAcentral), circRNAs, snoRNAs,... |
| `tooluniverse-nutrition-food-composition` | Look up nutrient composition, ingredients, allergens, additives, and processing-level classification for foods... |
| `tooluniverse-organic-chemistry` | Organic chemistry reasoning guide for reaction product prediction, mechanism analysis... |
| `tooluniverse-pathway-disease-genetics` | Connect GWAS variants to biological pathways and druggable targets |
| `tooluniverse-peptide-target-deorphanization` | Find the real protein target(s) of a peptide from its sequence — peptide target deorphanization / off-target... |
| `tooluniverse-pharmacogenomics` | Pharmacogenomics (PGx) research — drug-gene interactions (CPIC, PharmGKB), CPIC dosing guidelines,... |
| `tooluniverse-pharmacokinetics` | Pharmacokinetic (PK) analysis of concentration-time data — non-compartmental analysis (NCA) for Cmax, Tmax, AUC... |
| `tooluniverse-pharmacovigilance` | Drug safety and adverse event analysis — FAERS spontaneous-report mining, FDA black-box warnings, signal... |
| `tooluniverse-phewas` | Cross-ancestry / cross-biobank phenome-wide association (PheWAS) and replication |
| `tooluniverse-phylogenetics` | Phylogenetic analysis — de novo multiple sequence alignment (Clustal Omega/MUSCLE/MAFFT via EBI_msa_align) and... |
| `tooluniverse-plant-genomics` | Plant genomics and biology research — PlantReactome pathways, Ensembl Plants gene structure, POWO species... |
| `tooluniverse-polygenic-risk-score` | Build and interpret polygenic risk scores (PRS) for complex diseases using GWAS summary statistics |
| `tooluniverse-population-genetics` | Population genetics analysis — allele frequencies (gnomAD, 1000 Genomes), Hardy-Weinberg equilibrium testing,... |
| `tooluniverse-population-genetics-1000genomes` | Population genetics using the 1000 Genomes Project (IGSR) — superpopulation/population search, sample metadata,... |
| `tooluniverse-precision-medicine-stratification` | Patient stratification for precision medicine — integrate genomic, clinical, and therapeutic data to split... |
| `tooluniverse-precision-oncology` | Cancer treatment recommendations from molecular profile (mutations + cancer type + biomarkers) — FDA-approved +... |
| `tooluniverse-primer-design` | PCR / qPCR primer and oligo design — design forward/reverse primers for a target region (SantaLucia... |
| `tooluniverse-product-safety-surveillance` | >- Post-market safety surveillance and recall/adverse-event RETRIEVAL across the full spectrum of FDA-regulated... |
| `tooluniverse-protein-design-campaign` | Run and review iterative protein binder design campaigns with multiple model families, structural and glycan... |
| `tooluniverse-protein-interactions` | Protein-protein interaction (PPI) network analysis — STRING (predicted + experimental), BioGRID (curated),... |
| `tooluniverse-protein-lof-mechanism` | Propose the mechanism by which a missense variant causes loss-of-function (LoF), synthesizing evidence from 5... |
| `tooluniverse-protein-modification-analysis` | Post-translational modification (PTM) analysis — phosphorylation, ubiquitination, acetylation, glycosylation,... |
| `tooluniverse-protein-sae-variant-interpretation` | Interpret a missense variant via ESMC-6B Sparse Autoencoder (SAE) feature activations |
| `tooluniverse-protein-structural-annotation-pdb` | Given a PDB structure, produce a per-residue annotation table: which residues sit at a binding interface (vs a... |
| `tooluniverse-protein-structure-prediction` | Protein 3D structure prediction from sequence — ESMFold de novo prediction, AlphaFold database retrieval,... |
| `tooluniverse-protein-structure-retrieval` | Protein structure retrieval from RCSB PDB, PDBe, AlphaFold, SWISS-MODEL, 3D-Beacons (cross-provider structure... |
| `tooluniverse-protein-therapeutic-design` | AI-guided de novo protein design — RFdiffusion backbone generation, ProteinMPNN sequence design, structure... |
| `tooluniverse-proteomics-analysis` | Mass-spec proteomics analysis — protein identification, quantification (LFQ, TMT, iTRAQ), differential... |
| `tooluniverse-proteomics-data-retrieval` | Find and retrieve proteomics datasets from MassIVE, ProteomeXchange, PRIDE Archive, and the NCI Proteomics Data... |
| `tooluniverse-rare-disease-diagnosis` | Rare disease differential diagnosis from patient phenotype — HPO term matching to candidate diseases (Orphanet,... |
| `tooluniverse-rare-disease-genomics` | Rare disease genomics — disease identification (Orphanet), causative gene discovery, gene-disease validity... |
| `tooluniverse-regulatory-genomics` | Transcription factor binding, cis-regulatory elements (cCREs), chromatin accessibility, and regulatory... |
| `tooluniverse-regulatory-variant-analysis` | Non-coding/regulatory variant interpretation — GWAS association lookup, eQTL evidence (GTEx), chromatin state... |
| `tooluniverse-residue-functional-mechanism-interpretation` | Given a set of residues in a protein, explain WHY they are functionally critical by combining structural... |
| `tooluniverse-rnaseq-deseq2` | RNA-seq differential expression analysis with DESeq2, edgeR, and limma-voom — DEG lists, fold changes,... |
| `tooluniverse-scientific-peer-review` | Review scientific manuscripts, abstracts, methods, statistical analyses, results, discussions, protocols, and... |
| `tooluniverse-scientific-problem-selection` | Conversational framework for choosing what scientific problem to work on, pitching a new project idea,... |
| `tooluniverse-scvi-tools` | Deep learning for single-cell omics using scvi-tools — probabilistic (VAE-based) batch correction and... |
| `tooluniverse-sdk` | Build AI scientist systems with the ToolUniverse Python SDK for scientific research |
| `tooluniverse-self-review` | > Review existing work against the user's actual goal and surface evidence-backed strengths, gaps, risks, and... |
| `tooluniverse-sequence-analysis` | Biological sequence analysis — gene/protein sequence retrieval (NCBI, Ensembl, UniProt), nucleotide/protein... |
| `tooluniverse-sequence-retrieval` | Retrieve DNA/RNA/protein sequences from NCBI and ENA with disambiguation |
| `tooluniverse-single-cell` | Single-cell RNA-seq analysis with scanpy/anndata — h5ad data loading, scRNA-seq quality control and QC gating... |
| `tooluniverse-small-molecule-discovery` | Small molecule identification, characterization, and procurement — PubChem, ChEMBL, BindingDB, ADMET-AI,... |
| `tooluniverse-spatial-omics-analysis` | Spatial multi-omics interpretation pipeline |
| `tooluniverse-spatial-transcriptomics` | Spatial transcriptomics analysis — Visium, MERFISH, seqFISH, Slide-seq |
| `tooluniverse-statistical-modeling` | Statistical modeling — linear/logistic/ordinal/Poisson regression, ANOVA, Kruskal-Wallis, chi-square,... |
| `tooluniverse-stem-cell-organoid` | Stem cell, iPSC, and organoid research — pluripotency markers, differentiation protocol pathways, lineage... |
| `tooluniverse-structural-proteomics` | Structural biology plus proteomics integration for drug target validation |
| `tooluniverse-structural-variant-analysis` | Structural variant (SV) clinical interpretation: deletions, duplications, inversions, translocations, complex... |
| `tooluniverse-synthetic-biology-parts` | Look up synthetic biology genetic parts (promoters, RBS, CDS/genes, terminators, reporters, composite devices)... |
| `tooluniverse-systems-biology` | Systems biology and pathway analysis integrating Reactome, KEGG, WikiPathways, BioCarta, NCI-Nature Pathway... |
| `tooluniverse-target-research` | Comprehensive drug-target intelligence — tissue expression (GTEx, HPA), pathways, protein interactions... |
| `tooluniverse-toxicology` | Drug and chemical toxicity assessment via adverse outcome pathways (AOPs), real-world FAERS adverse event... |
| `tooluniverse-vaccine-design` | Computational vaccine candidate design: peptide/subunit vaccines via MHC-I/MHC-II epitope prediction (IEDB),... |
| `tooluniverse-variant-analysis` | VCF and variant analysis — parsing, annotation, classification (synonymous, missense, frameshift, stop_gained),... |
| `tooluniverse-variant-functional-annotation` | Functional annotation of protein variants — ProtVar structural/functional context, ClinVar clinical... |
| `tooluniverse-variant-interpretation` | Clinical variant interpretation from raw variant calls to ACMG-classified recommendations with structural... |
| `tooluniverse-variant-predictor-dms-validation` | Validate a variant-effect predictor (AlphaMissense, ESM-C SAE, ESM logits, EVE, conservation scores, or any... |
| `tooluniverse-variant-to-mechanism` | End-to-end variant-to-mechanism analysis — trace a variant (rsID/coordinates) through regulatory context,... |

### Setup and Access (11)

Connecting to ToolUniverse, adding database logins, publishing a tool, and sharing a machine.

| Skill | Description |
|-------|-------------|
| `tooluniverse` | ToolUniverse plugin router |
| `tooluniverse-antigravity-plugin` | Install, set up, verify, update, pin, uninstall, or troubleshoot the ToolUniverse plugin on Google Antigravity... |
| `tooluniverse-claude-code-plugin` | Install the ToolUniverse Claude Code plugin in one step — provides MCP server with 2,700+ scientific tools,... |
| `tooluniverse-codex-plugin` | Install, set up, verify, update, pin, uninstall, or troubleshoot the ToolUniverse plugin on OpenAI Codex |
| `tooluniverse-connect` | How to use ToolUniverse Connect (connect.aiscientist.tools), the hosted ToolUniverse service, and when to use... |
| `tooluniverse-cs-setup` | Install or update ToolUniverse in Claude Science — create the conda env, install the tooluniverse pip package,... |
| `tooluniverse-custom-tool` | Add custom local tools to ToolUniverse alongside the 2,700+ built-in tools |
| `tooluniverse-database-logins` | Help the user add the login (API key) that a ToolUniverse tool needs for a database such as NCBI/PubMed, OMIM,... |
| `tooluniverse-publish-tool` | Help the user publish one tool from their shared computer to ToolUniverse so other scientists' AI scientists... |
| `tooluniverse-share-computer` | Share tools that live on this computer (the user's own Python function, script or notebook code, a model, a... |
| `tooluniverse-use-shared-computer` | Use tools that run on a colleague's computer (for example models on their lab GPU) or tools other scientists... |

### Remote Tool Setup (63)

Installing and registering a GPU-backed model provider on this machine.

| Skill | Description |
|-------|-------------|
| `host-and-share-remote-tool` | Host, validate, and privately share a user's own model, Python function, workflow, or existing Streamable HTTP... |
| `setup-af2ig-remote-tool` | Set up, launch, validate, and troubleshoot the AlphaFold 2 initial-guess (dl_binder_design) ToolUniverse remote... |
| `setup-af3_jax-remote-tool` | Set up, launch, validate, and troubleshoot the AlphaFold 3 (JAX fork) ToolUniverse remote tool and optionally... |
| `setup-af3_torch-remote-tool` | Set up, launch, validate, and troubleshoot the AF3-torch ToolUniverse remote tool and optionally relay it... |
| `setup-apnovo-remote-tool` | Set up, launch, validate, and troubleshoot the AlphaProtein Novo (de novo enzyme design) ToolUniverse remote tool |
| `setup-atlasfold-remote-tool` | Set up, launch, validate, and troubleshoot the AtlasFold ToolUniverse remote tool and optionally relay it... |
| `setup-bioemu2-remote-tool` | Set up, launch, validate, and troubleshoot the BioEmu-2 ToolUniverse remote tool and optionally relay it... |
| `setup-boltz-remote-tool` | Set up, launch, validate, and troubleshoot the Boltz-2 ToolUniverse remote tool and optionally relay it through... |
| `setup-boltzgen-remote-tool` | Set up, launch, validate, and troubleshoot the BoltzGen ToolUniverse remote tool and optionally relay it... |
| `setup-borzoi-remote-tool` | Set up, launch, validate, and troubleshoot the Borzoi ToolUniverse remote tool and optionally relay it through... |
| `setup-borzoi_calico-remote-tool` | Set up, launch, validate, and troubleshoot the calico/borzoi variant-scoring (SAD/logSAD/D2/logD2) ToolUniverse... |
| `setup-cell2location-remote-tool` | Set up, launch, validate, and troubleshoot the cell2location ToolUniverse remote tool and optionally relay it... |
| `setup-cellrank-remote-tool` | Set up, launch, validate, and troubleshoot the CellRank ToolUniverse remote tool and optionally relay it... |
| `setup-celltypist-remote-tool` | Set up, launch, validate, and troubleshoot the CellTypist ToolUniverse remote tool and optionally relay it... |
| `setup-chai1-remote-tool` | Set up, launch, validate, and troubleshoot the Chai-1 ToolUniverse remote tool and optionally relay it through... |
| `setup-chrombpnet-remote-tool` | Set up, launch, validate, and troubleshoot the ChromBPNet ToolUniverse remote tool and optionally relay it... |
| `setup-colabdesign-remote-tool` | Set up, launch, validate, and troubleshoot the ColabDesign (BindCraft binder design) ToolUniverse remote tool... |
| `setup-colabfold-remote-tool` | Set up, launch, validate, and troubleshoot the ColabFold (AlphaFold2-Multimer) ToolUniverse remote tool and... |
| `setup-complexa-remote-tool` | Set up, launch, validate, and troubleshoot the Proteina-Complexa ToolUniverse remote tool and optionally relay... |
| `setup-depmap-24q2-remote-tool` | Set up, launch, validate, and troubleshoot the DepMap 24Q2 ToolUniverse remote tool and optionally relay it... |
| `setup-e1-remote-tool` | Set up, launch, validate, and troubleshoot the Profluent E1 ToolUniverse remote tool and optionally relay it... |
| `setup-ef2inv-remote-tool` | Set up, launch, validate, and troubleshoot the ESMFold2-binder-design ToolUniverse remote tool and optionally... |
| `setup-enformer-remote-tool` | Set up, launch, validate, and troubleshoot the Enformer ToolUniverse remote tool and optionally relay it... |
| `setup-enformer_deepmind-remote-tool` | Set up, launch, validate, and troubleshoot the official DeepMind Enformer (TF-Hub SavedModel) genomic track... |
| `setup-esm-remote-tool` | Set up, launch, validate, and troubleshoot the ESM ToolUniverse remote tool and optionally relay it through... |
| `setup-esm_if1-remote-tool` | Set up, launch, validate, and troubleshoot the ESM-IF1 inverse-folding ToolUniverse remote tool and optionally... |
| `setup-esmc-remote-tool` | Set up, launch, validate, and troubleshoot the ESM Cambrian ToolUniverse remote tool and optionally relay it... |
| `setup-esmfold2-remote-tool` | Set up, launch, validate, and troubleshoot the ESMFold2 ToolUniverse remote tool and optionally relay it... |
| `setup-evo2-remote-tool` | Set up, launch, validate, and troubleshoot the Evo 2 ToolUniverse remote tool and optionally relay it through... |
| `setup-expert-feedback-remote-tool` | Set up, launch, validate, and troubleshoot the Human expert feedback ToolUniverse remote tool and optionally... |
| `setup-genie3-remote-tool` | Set up, launch, validate, and troubleshoot the Genie 3 ToolUniverse remote tool and optionally relay it through... |
| `setup-gpnstar-remote-tool` | Set up, launch, validate, and troubleshoot the GPN-Star ToolUniverse remote tool (single-nucleotide variant... |
| `setup-harmony-remote-tool` | Set up, launch, validate, and troubleshoot the Harmony ToolUniverse remote tool and optionally relay it through... |
| `setup-immune-compass-remote-tool` | Set up, launch, validate, and troubleshoot the immune COMPASS ToolUniverse remote tool and optionally relay it... |
| `setup-ldsc-remote-tool` | Set up, launch, validate, and troubleshoot the LDSC ToolUniverse remote tool and optionally relay it through... |
| `setup-liana-remote-tool` | Set up, launch, validate, and troubleshoot the LIANA ToolUniverse remote tool and optionally relay it through... |
| `setup-macs3-remote-tool` | Set up, launch, validate, and troubleshoot the MACS3 ToolUniverse remote tool and optionally relay it through... |
| `setup-milo-remote-tool` | Set up, launch, validate, and troubleshoot the Milo ToolUniverse remote tool and optionally relay it through... |
| `setup-mofa-remote-tool` | Set up, launch, validate, and troubleshoot the MOFA+ ToolUniverse remote tool and optionally relay it through... |
| `setup-monocle3-remote-tool` | Set up, launch, validate, and troubleshoot the Monocle 3 ToolUniverse remote tool and optionally relay it... |
| `setup-mosaic-remote-tool` | Set up, launch, validate, and troubleshoot the mosaic (Boltz-2 binder hallucination) ToolUniverse remote tool... |
| `setup-opendde-remote-tool` | Set up, launch, validate, and troubleshoot the OpenDDE ToolUniverse remote tool and optionally relay it through... |
| `setup-openfold3-remote-tool` | Set up, launch, validate, and troubleshoot the OpenFold3 ToolUniverse remote tool and optionally relay it... |
| `setup-openfold3_ob0-remote-tool` | Set up, launch, validate, and troubleshoot the OpenFold3 OpenBind-0 ToolUniverse remote tool and optionally... |
| `setup-paga-remote-tool` | Set up, launch, validate, and troubleshoot the PAGA ToolUniverse remote tool and optionally relay it through... |
| `setup-pinnacle-remote-tool` | Set up, launch, validate, and troubleshoot the PINNACLE ToolUniverse remote tool and optionally relay it... |
| `setup-progen2-remote-tool` | Set up, launch, validate, and troubleshoot the ProGen2 ToolUniverse remote tool and optionally relay it through... |
| `setup-proteinmpnn-remote-tool` | Set up, launch, validate, and troubleshoot the ProteinMPNN / SolubleMPNN fixed-backbone sequence-design... |
| `setup-protenix_v1-remote-tool` | Set up, launch, validate, and troubleshoot the Protenix ToolUniverse remote tool and optionally relay it... |
| `setup-rfd4_proteina-remote-tool` | Set up, launch, validate, and troubleshoot the RFD4-Proteina ToolUniverse remote tool and optionally relay it... |
| `setup-rfdiffusion3-remote-tool` | Set up, launch, validate, and troubleshoot the RFdiffusion3 ToolUniverse remote tool and optionally relay it... |
| `setup-rosettafold3-remote-tool` | Set up, launch, validate, and troubleshoot the RoseTTAFold3 ToolUniverse remote tool and optionally relay it... |
| `setup-scanvi-remote-tool` | Set up, launch, validate, and troubleshoot the scANVI ToolUniverse remote tool and optionally relay it through... |
| `setup-scrublet-remote-tool` | Set up, launch, validate, and troubleshoot the Scrublet ToolUniverse remote tool and optionally relay it... |
| `setup-scvelo-remote-tool` | Set up, launch, validate, and troubleshoot the scVelo ToolUniverse remote tool and optionally relay it through... |
| `setup-scvi-remote-tool` | Set up, launch, validate, and troubleshoot the scVI ToolUniverse remote tool and optionally relay it through... |
| `setup-singler-remote-tool` | Set up, launch, validate, and troubleshoot the SingleR ToolUniverse remote tool and optionally relay it through... |
| `setup-slingshot-remote-tool` | Set up, launch, validate, and troubleshoot the Slingshot ToolUniverse remote tool and optionally relay it... |
| `setup-squidpy-remote-tool` | Set up, launch, validate, and troubleshoot the Squidpy ToolUniverse remote tool and optionally relay it through... |
| `setup-tangram-remote-tool` | Set up, launch, validate, and troubleshoot the Tangram ToolUniverse remote tool and optionally relay it through... |
| `setup-tooluniverse` | Install and configure ToolUniverse for any use case — MCP server (chat-based), CLI (command line with 14... |
| `setup-transcriptformer-remote-tool` | Set up, launch, validate, and troubleshoot the TranscriptFormer ToolUniverse remote tool and optionally relay... |
| `setup-uspto-downloader-remote-tool` | Set up, launch, validate, and troubleshoot the USPTO downloader ToolUniverse remote tool and optionally relay... |

### Developer Skills (2)

| Skill | Description |
|-------|-------------|
| `create-tooluniverse-skill` | Create high-quality ToolUniverse skills following test-driven, implementation-agnostic methodology |
| `devtu-benchmark-harness` | Continuous improvement system for ToolUniverse tools, skills, and plugin |

## Skill Structure

```
skill-name/
├── SKILL.md          # Main instructions (<500 lines)
├── QUICK_START.md    # Quick reference (optional)
├── EXAMPLES.md       # Usage examples (optional)
└── references/       # Detailed reference material (optional)
```

## Contributing

1. Create `skill-name/SKILL.md` with proper frontmatter
2. Keep SKILL.md concise (<500 lines)
3. Add examples for common use cases
4. Keep canonical skills host-agnostic. Do not add client-specific metadata such
   as `agents/openai.yaml`; generate host-specific files in the corresponding
   plugin packaging layer instead.
5. See `create-tooluniverse-skill` for the full workflow
