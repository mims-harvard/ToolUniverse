---
name: tooluniverse
description: Router skill for ToolUniverse tasks. First checks if specialized tooluniverse skills (105+ skills covering disease/drug/target research, gene-disease associations, clinical decision support, genomics, epigenomics, proteomics, comparative genomics, chemical safety, toxicology, systems biology, and more) can solve the problem, then falls back to general strategies for using 2300+ scientific tools. Covers tool discovery, multi-hop queries, comprehensive research workflows, disambiguation, evidence grading, and report generation. Use when users need to research any scientific topic, find biological data, or explore drug/target/disease relationships. ALSO USE for any biology, medicine, chemistry, pharmacology, or life science question — even simple factoid questions like "how many X in protein Y", "what drug interacts with Z", "what gene causes disease W", or "translate this sequence". These questions benefit from database lookups (UniProt, PubMed, ChEMBL, ClinVar, GWAS Catalog, etc.) rather than answering from memory alone. When in doubt about a scientific fact, USE THIS SKILL to verify against real databases.
---

# ToolUniverse Router

Route user questions to specialized skills. If no skill matches, use general strategies from [references/general-strategies.md](references/general-strategies.md).

## General Reasoning Protocols

When answering scientific questions:

1. **Look up, don't guess**: Use ToolUniverse tools to verify facts before answering.
2. **Compute, don't estimate**: Write and run Python code (via Bash) for any calculation. Never do mental math.
3. **Analyze, don't just retrieve**: When a question requires data analysis, download the data and run the analysis — don't just describe what you would do.
4. **Route to specialized skills**: Use the Routing Table below to find domain-specific reasoning protocols.

**You have full code execution.** For any analysis task (statistics, data wrangling, visualization), write Python and execute it. ToolUniverse tools find data and metadata; Python code does the analysis.

## Routing Workflow

1. **Extract keywords** from user's question
2. **Scan routing table** below for keyword matches
3. **Take action**:
   - **1 clear match** → invoke that skill NOW using the Skill tool
   - **Multiple matches** → ask user which they prefer (AskUserQuestion)
   - **No match** → use general strategies (load [references/general-strategies.md](references/general-strategies.md))
4. **If ambiguous** (e.g., "Tell me about aspirin") → ask user to clarify intent

**CRITICAL**: Actually INVOKE skills — don't describe them or show the routing table to the user.

**LOOK UP, DON'T GUESS**: If you are not confident about a factual claim, SEARCH for it. Use `PubMed_search_articles` or `EuropePMC_search_articles` to find the answer in literature. Use `UniProt_search` / `proteins_api_search` for protein facts. Use `NCBI_search_gene` for gene facts. Use `GBIF_search_species` for taxonomy. Use `PubChem_get_compound_by_name` for chemical facts. A tool-verified answer is always better than a guess from memory. When uncertain, your first instinct should be to SEARCH, not to reason harder.
**Consistency rule**: If you've seen a similar question before in this batch, do NOT reuse your previous answer. Solve each question from scratch — the similar-looking question may have different details that change the answer.

**For MC questions**: Before eliminating options, check if the question asks about a SPECIFIC fact (protein name, gene function, species behavior, experimental result). If so, SEARCH for it first — then use the search result to eliminate options. This is faster and more reliable than reasoning from memory.

**NEVER REFUSE**: If a question is hard, attempt it anyway. First try to look up the answer. If tools don't help, use reasoning strategies from the skill. A wrong answer is better than "this requires further analysis."

**COMPUTE, DON'T ESTIMATE**: When a problem gives numerical values and asks for a numerical answer, WRITE AND RUN Python code. Do not attempt mental arithmetic on multi-step problems.

**MULTIPLE CHOICE STRATEGY**: When the question has answer choices (A, B, C, D...):
1. Read the question CAREFULLY — identify exactly what is being asked
2. Read ALL answer choices before reasoning — don't stop at the first plausible one
3. ELIMINATE clearly wrong options first (usually 2-3 can be ruled out immediately)
4. For the remaining options, reason through each: WHY would this be correct? WHY would this be wrong?
5. If you have two similar-sounding options, look for the KEY DIFFERENCE between them
6. Your final answer MUST be a single letter — nothing else
7. COMMON ERROR: reasoning correctly but reporting the wrong letter. After choosing, re-read your choice letter and verify it matches your reasoning.
8. **MC traps**: "All/None of the above" is correct only ~25% of the time — don't default to it. Options with absolute language ("always", "never", "only") are usually wrong. The longest/most detailed option is correct more often. When two options are opposites, one of them is usually correct.
9. **Quantitative MC**: When an MC question involves a number, COMPUTE the answer first (use Python), THEN match to the closest option. Do not let the listed choices bias your calculation.
10. For scored MC questions, run `mc_analyzer.py` (in `skills/tooluniverse-computational-biophysics/scripts/`) to enforce systematic elimination before committing to an answer.

**CRITICAL FOR BATCH PROCESSING**: When answering multiple MC questions in sequence, do NOT rush. Apply the FULL elimination process to EVERY question. Common batch error: answering based on first impression without elimination. For each MC question, you MUST:
- Write out at least 2 eliminated options with reasons BEFORE selecting your answer
- If you cannot eliminate any options, that's a sign you need to LOOK UP information

**VERIFY BEFORE ANSWERING**: Before giving your final answer, run these checks:
- If your answer is a number: does it have the right order of magnitude? (A drug dose of 500 kg is wrong. A pH of 15 is wrong. A percentage > 100% is wrong.)
- If your answer is a letter choice: re-read the question and ALL choices. Are you sure your reasoning matches the choice letter you picked? A common error is reasoning correctly but picking the wrong letter.
- If your answer involves a protein or gene: did you look up the CORRECT one? (GABRA1 ≠ GABRR1. BRCA1 ≠ BRCA2. TP53 ≠ TP63.)
- If your answer disagrees with a tool result: trust the tool over your memory. Databases are updated; your training data has a cutoff.
- If answering MC in a batch: SLOW DOWN. Apply elimination to each question individually. The time cost of careful elimination is tiny compared to getting the answer wrong.

**BATCH PROCESSING PROTOCOL** — when answering multiple questions in sequence:
1. For EACH question independently: read the question, identify the domain, invoke the relevant skill
2. NEVER carry assumptions from one question to the next
3. For EVERY MC question: write "Eliminating: [letter] because [reason]" for at least 2 options BEFORE giving your answer
4. For EVERY numerical question: write and execute Python code — report the computed result, not a mental estimate
5. For EVERY "what protein/gene/species" question: search a database FIRST, then answer
6. Between questions: mentally reset. Each question is independent.

**Answer Format Rules** (numerical answers):
- If the question says "find the number", give JUST the number — no units unless asked.
- Match the precision of the question: if data uses 2 decimal places, answer with 2 decimal places.
- For large numbers (>10^6): use scientific notation. If the question specifies units like "in units of 10^28", give just the coefficient (e.g., 1.86).
- For small numbers: match the format shown in the question (e.g., "1.776 × 10^-3" not "1.8e-3").
- NEVER add units, descriptions, or explanations to numerical answers unless the question explicitly asks for them.
- When a question asks for a pure number (e.g., "how many days"), give ONLY the number (e.g., "350" not "350 days").

**Language**: If the user writes in a non-English language, extract keywords for routing but respond in their language. All tool calls use English terms.

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

### 3. Clinical Decision Support

| Keywords | Action |
|----------|--------|
| "**drug safety**", "adverse events", "side effects", "pharmacovigilance", "pharmacogenomics", "FAERS", "black box warning" | `Skill(skill="tooluniverse-pharmacovigilance")` |
| "**adverse event signal**", "safety signal detection", "disproportionality", "PRR", "ROR" | `Skill(skill="tooluniverse-adverse-event-detection")` |
| "**drug safety profile**", "drug safety assessment", "comprehensive safety" | `Skill(skill="tooluniverse-drug-safety-profiling")` |
| "**chemical safety**", "ADMET", "chemical toxicity", "environmental toxicity", "toxic effects" | `Skill(skill="tooluniverse-chemical-safety")` |
| "**cancer treatment**", "precision oncology", "tumor mutation", "targeted therapy", "EGFR", "KRAS", "BRAF" | `Skill(skill="tooluniverse-precision-oncology")` |
| "**cancer driver**", "driver gene", "driver mutation", "IntOGen", "cBioPortal" | `Skill(skill="tooluniverse-cancer-driver-analysis")` |
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
| "**VCF**", "variant calling", "mutation analysis", "variant annotation pipeline" | `Skill(skill="tooluniverse-variant-analysis")` |
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
| "**CRISPR screen**", "genetic screen", "screen hits", "essential genes" | `Skill(skill="tooluniverse-crispr-screen-analysis")` |
| "**drug-drug interaction**", "DDI", "drug combination", "polypharmacy" | `Skill(skill="tooluniverse-drug-drug-interaction")` |
| "**differential expression**", "DESeq2", "RNA-seq analysis", "DE genes", "fold change" | `Skill(skill="tooluniverse-rnaseq-deseq2")` |
| "**proteomics**", "mass spectrometry", "protein quantification", "TMT", "iTRAQ", "label-free" | `Skill(skill="tooluniverse-proteomics-analysis")` |
| "**immune repertoire**", "TCR", "BCR", "T-cell receptor", "B-cell receptor", "clonotype" | `Skill(skill="tooluniverse-immune-repertoire-analysis")` |
| "**spatial transcriptomics**", "Visium", "MERFISH", "seqFISH", "Slide-seq", "spatial gene expression" | `Skill(skill="tooluniverse-spatial-transcriptomics")` |
| "**spatial omics**", "spatial proteomics", "spatial multi-omics" | `Skill(skill="tooluniverse-spatial-omics-analysis")` |
| "**microscopy**", "image analysis", "cell counting", "colony morphometry", "fluorescence quantification" | `Skill(skill="tooluniverse-image-analysis")` |
| "**electron microscopy**", "cryo-EM", "TEM", "SEM", "EMPIAR", "EMDB" | `Skill(skill="tooluniverse-electron-microscopy")` |
| "**cell line**", "cell line profiling", "DepMap", "CCLE", "cell line sensitivity" | `Skill(skill="tooluniverse-cell-line-profiling")` |
| "**clinical data integration**", "clinical phenotype", "EHR analysis", "clinical cohort" | `Skill(skill="tooluniverse-clinical-data-integration")` |
| "**phylogenetics**", "phylogenetic tree", "sequence alignment", "evolutionary analysis" | `Skill(skill="tooluniverse-phylogenetics")` |
| "**statistical modeling**", "regression analysis", "logistic regression", "survival analysis", "Cox" | `Skill(skill="tooluniverse-statistical-modeling")` |
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
| "**setup**", "install", "configure", "API keys", "upgrade", "**how to use**", "**get started**", "**CLI**", "**tu command**", "MCP vs CLI vs SDK", "**what is ToolUniverse**", "**what can this do**", "**what databases**", "**demo**", "**tutorial**", "**quickstart**", "**I'm new**" | `Skill(skill="setup-tooluniverse")` |
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

2. **Specificity Rule**: More specific beats general.
   - "cancer treatment" → precision-oncology (not disease-research)

3. **Data Type Rule**: "get/retrieve/fetch" → retrieval skills.
   - "get compound structure" → chemical-compound-retrieval (not drug-research)

4. **Still ambiguous**: Ask user with AskUserQuestion.

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
