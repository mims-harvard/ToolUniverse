# ToolUniverse Skills

68 pre-built research skills for AI agents. Skills are automatically available — just ask naturally.

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

### Research Skills

| Skill | Description |
|-------|-------------|
| `tooluniverse` | Router — dispatches to the right specialized skill automatically |
| `tooluniverse-adverse-event-detection` | Adverse drug event signal detection using FDA FAERS data |
| `tooluniverse-antibody-engineering` | Antibody humanization, affinity maturation, and optimization |
| `tooluniverse-binder-discovery` | Small molecule binder discovery (structure-based and ligand-based) |
| `tooluniverse-cancer-variant-interpretation` | Clinical interpretation of somatic cancer mutations |
| `tooluniverse-chemical-compound-retrieval` | Chemical compound info from PubChem and ChEMBL |
| `tooluniverse-chemical-safety` | Chemical safety and toxicology assessment (ADMET-AI, CTD, FDA) |
| `tooluniverse-clinical-guidelines` | Clinical practice guidelines from 12+ sources (NICE, WHO, ADA, etc.) |
| `tooluniverse-clinical-trial-design` | Clinical trial design feasibility assessment |
| `tooluniverse-clinical-trial-matching` | Patient-to-trial matching for precision medicine |
| `tooluniverse-crispr-screen-analysis` | CRISPR knockout/activation screen analysis |
| `tooluniverse-custom-tool` | Create and register custom tools |
| `tooluniverse-disease-research` | Comprehensive disease reports using 100+ tools |
| `tooluniverse-drug-drug-interaction` | Drug-drug interaction prediction and risk assessment |
| `tooluniverse-drug-repurposing` | Drug repurposing via target-, compound-, and disease-driven strategies |
| `tooluniverse-drug-research` | Comprehensive drug reports with evidence grading |
| `tooluniverse-drug-target-validation` | Computational drug target validation (10 dimensions) |
| `tooluniverse-epigenomics` | Epigenomics and gene regulation (ENCODE, JASPAR, methylation) |
| `tooluniverse-expression-data-retrieval` | Gene expression datasets from ArrayExpress and BioStudies |
| `tooluniverse-gene-enrichment` | Gene enrichment and pathway analysis (gseapy, PANTHER, STRING, etc.) |
| `tooluniverse-gwas-drug-discovery` | GWAS signals to drug targets and repurposing opportunities |
| `tooluniverse-gwas-finemapping` | Causal variant prioritization via statistical fine-mapping |
| `tooluniverse-gwas-snp-interpretation` | Genetic variant interpretation from GWAS studies |
| `tooluniverse-gwas-study-explorer` | GWAS study comparison and meta-analysis |
| `tooluniverse-gwas-trait-to-gene` | Gene-trait associations from GWAS Catalog and Open Targets |
| `tooluniverse-image-analysis` | Microscopy image analysis and quantitative imaging |
| `tooluniverse-immune-repertoire-analysis` | TCR/BCR immune repertoire analysis |
| `tooluniverse-immunotherapy-response-prediction` | Predict response to immune checkpoint inhibitors |
| `tooluniverse-infectious-disease` | Pathogen characterization and drug repurposing for outbreaks |
| `tooluniverse-install-skills` | Auto-detect and install missing skills |
| `tooluniverse-literature-deep-research` | Literature research with evidence grading and theme extraction |
| `tooluniverse-metabolomics` | Metabolomics research (metabolite ID, study analysis) |
| `tooluniverse-metabolomics-analysis` | Metabolomics data analysis (quantification, pathway, flux) |
| `tooluniverse-multi-omics-integration` | Multi-omics dataset integration |
| `tooluniverse-multiomic-disease-characterization` | Multi-omics disease characterization |
| `tooluniverse-network-pharmacology` | Compound-target-disease network analysis |
| `tooluniverse-pharmacovigilance` | Drug safety signal analysis from FDA reports |
| `tooluniverse-phylogenetics` | Phylogenetics and sequence analysis |
| `tooluniverse-polygenic-risk-score` | Polygenic risk score construction and interpretation |
| `tooluniverse-precision-medicine-stratification` | Patient stratification for precision medicine |
| `tooluniverse-precision-oncology` | Actionable cancer treatment recommendations from molecular profiles |
| `tooluniverse-protein-interactions` | Protein-protein interaction networks (STRING, BioGRID) |
| `tooluniverse-protein-structure-retrieval` | Protein structures from PDB, PDBe, and AlphaFold |
| `tooluniverse-protein-therapeutic-design` | AI-guided protein therapeutic design (RFdiffusion, etc.) |
| `tooluniverse-proteomics-analysis` | Mass spectrometry proteomics analysis |
| `tooluniverse-rare-disease-diagnosis` | Rare disease differential diagnosis from phenotype and genetics |
| `tooluniverse-rnaseq-deseq2` | RNA-seq differential expression with PyDESeq2 |
| `tooluniverse-sdk` | Build AI scientist systems using the Python SDK |
| `tooluniverse-sequence-retrieval` | DNA, RNA, and protein sequences from NCBI and ENA |
| `tooluniverse-single-cell` | Single-cell RNA-seq analysis (scanpy, anndata) |
| `tooluniverse-spatial-omics-analysis` | Spatial multi-omics data integration |
| `tooluniverse-spatial-transcriptomics` | Spatial transcriptomics (10x Visium, MERFISH, seqFISH) |
| `tooluniverse-statistical-modeling` | Statistical modeling and regression for biomedical data |
| `tooluniverse-structural-variant-analysis` | Structural variant analysis for clinical genomics |
| `tooluniverse-systems-biology` | Pathway analysis (Reactome, KEGG, WikiPathways) |
| `tooluniverse-target-research` | Comprehensive drug target profiling (9 research paths) |
| `tooluniverse-variant-analysis` | VCF processing, variant annotation, and SV/CNV interpretation |
| `tooluniverse-variant-interpretation` | Clinical variant interpretation with ACMG classification |

### Developer Skills

| Skill | Description |
|-------|-------------|
| `setup-tooluniverse` | Install and configure ToolUniverse (MCP, CLI, or SDK) |
| `create-tooluniverse-skill` | Create new skills with test-driven methodology |
| `devtu-auto-discover-apis` | Discover life science APIs and create tools automatically |
| `devtu-create-tool` | Create new scientific tools with proper structure and testing |
| `devtu-docs-quality` | Documentation quality validation and auditing |
| `devtu-fix-tool` | Diagnose and fix failing tools |
| `devtu-github` | GitHub workflow (push, pre-commit hooks, tests) |
| `devtu-optimize-descriptions` | Optimize tool descriptions for clarity |
| `devtu-optimize-skills` | Improve skill quality (evidence grading, disambiguation) |
| `devtu-self-evolve` | Full self-improvement cycle (discover, create, test, fix) |

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
4. See `create-tooluniverse-skill` for the full workflow
