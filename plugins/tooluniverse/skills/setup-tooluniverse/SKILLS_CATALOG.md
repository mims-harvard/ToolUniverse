# ToolUniverse Skills Catalog

65+ pre-built research workflows. Skills activate automatically when the AI detects a relevant request, or trigger them explicitly (e.g., "Use the tooluniverse skill to research the drug aspirin").

## Research Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse` | General strategies for using 1000+ tools effectively |
| `tooluniverse-drug-research` | Comprehensive drug profiling (identity, pharmacology, safety, ADMET) |
| `tooluniverse-target-research` | Drug target intelligence (structure, interactions, druggability) |
| `tooluniverse-disease-research` | Systematic disease analysis across 10 research dimensions |
| `tooluniverse-literature-deep-research` | Thorough literature reviews with evidence grading |
| `tooluniverse-drug-repurposing` | Find new therapeutic uses for existing drugs |
| `tooluniverse-precision-oncology` | Mutation-based treatment recommendations for cancer |
| `tooluniverse-rare-disease-diagnosis` | Phenotype-to-diagnosis for suspected rare diseases |
| `tooluniverse-pharmacovigilance` | Drug safety signal analysis from FDA adverse event data |
| `tooluniverse-infectious-disease` | Rapid pathogen characterization & drug repurposing |

## Data Retrieval Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-protein-structure-retrieval` | Protein 3D structure retrieval & quality assessment |
| `tooluniverse-sequence-retrieval` | DNA/RNA/protein sequence retrieval from NCBI/ENA |
| `tooluniverse-chemical-compound-retrieval` | Chemical compound data from PubChem/ChEMBL |
| `tooluniverse-expression-data-retrieval` | Gene expression & omics datasets |

## Clinical Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-variant-interpretation` | Genetic variant clinical interpretation |
| `tooluniverse-cancer-variant-interpretation` | Cancer somatic variant clinical interpretation |
| `tooluniverse-clinical-guidelines` | Clinical guideline retrieval and synthesis |
| `tooluniverse-clinical-trial-design` | Clinical trial design and protocol analysis |
| `tooluniverse-clinical-trial-matching` | Patient-to-trial matching based on eligibility |
| `tooluniverse-precision-medicine-stratification` | Patient stratification for precision medicine |
| `tooluniverse-drug-drug-interaction` | Drug-drug interaction analysis |
| `tooluniverse-adverse-event-detection` | Drug adverse event signal detection |
| `tooluniverse-immunotherapy-response-prediction` | Immunotherapy response biomarker analysis |

## Drug Discovery Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-drug-target-validation` | Target validation for drug discovery |
| `tooluniverse-binder-discovery` | Small molecule binder discovery via virtual screening |
| `tooluniverse-antibody-engineering` | Antibody design and optimization |
| `tooluniverse-protein-therapeutic-design` | AI-guided protein therapeutic design |
| `tooluniverse-chemical-safety` | Chemical safety and toxicity assessment |
| `tooluniverse-network-pharmacology` | Network-based drug-target-disease analysis |

## Genomics & Omics Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-variant-analysis` | Genomic variant analysis workflows |
| `tooluniverse-gwas-drug-discovery` | GWAS-driven drug target discovery |
| `tooluniverse-gwas-finemapping` | GWAS fine-mapping to causal variants |
| `tooluniverse-gwas-snp-interpretation` | GWAS SNP functional interpretation |
| `tooluniverse-gwas-study-explorer` | GWAS study discovery and comparison |
| `tooluniverse-gwas-trait-to-gene` | Trait-to-gene mapping from GWAS |
| `tooluniverse-polygenic-risk-score` | Polygenic risk score calculation and interpretation |
| `tooluniverse-structural-variant-analysis` | Structural variant detection and annotation |
| `tooluniverse-crispr-screen-analysis` | CRISPR screen hit identification and analysis |
| `tooluniverse-epigenomics` | Epigenomic data analysis (ChIP-seq, ATAC-seq) |
| `tooluniverse-gene-enrichment` | Gene set enrichment and pathway analysis |

## Transcriptomics & Proteomics Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-rnaseq-deseq2` | RNA-seq differential expression with DESeq2 |
| `tooluniverse-single-cell` | Single-cell RNA-seq analysis workflows |
| `tooluniverse-spatial-transcriptomics` | Spatial transcriptomics analysis |
| `tooluniverse-spatial-omics-analysis` | Spatial omics data analysis |
| `tooluniverse-proteomics-analysis` | Proteomics data analysis and interpretation |
| `tooluniverse-metabolomics` | Metabolomics data analysis and annotation |
| `tooluniverse-metabolomics-analysis` | Advanced metabolomics pathway analysis |
| `tooluniverse-multi-omics-integration` | Multi-omics data integration workflows |
| `tooluniverse-multiomic-disease-characterization` | Disease characterization across omics layers |

## Systems Biology & Other Skills

| Skill | What It Does |
|-------|-------------|
| `tooluniverse-protein-interactions` | Protein-protein interaction network analysis |
| `tooluniverse-systems-biology` | Systems biology network modeling |
| `tooluniverse-phylogenetics` | Phylogenetic analysis and tree building |
| `tooluniverse-statistical-modeling` | Statistical modeling for biological data |
| `tooluniverse-image-analysis` | Biomedical image analysis workflows |
| `tooluniverse-immune-repertoire-analysis` | Immune repertoire (BCR/TCR) analysis |
| `tooluniverse-sdk` | Build research pipelines with the Python SDK |
| `setup-tooluniverse` | This setup guide |

## How to Install

```bash
npx skills add mims-harvard/ToolUniverse --all
```

Or manually clone and copy to your client's skills directory:

| Client | Skills Directory |
|--------|----------------|
| Cursor | `.cursor/skills/` |
| Windsurf | `.windsurf/skills/` |
| Claude Code | `.claude/skills/` |
| Gemini CLI | `.gemini/skills/` |
| Qwen Code | `.qwen/skills/` |
| Codex (OpenAI) | `.agents/skills/` |
| OpenCode | `.opencode/skills/` |
| Trae | `.trae/skills/` |
| Cline / VS Code | `.skills/` |
