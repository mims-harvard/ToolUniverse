---
name: tooluniverse-noncoding-rna
description: Analyze non-coding RNAs (miRNAs, lncRNAs, circRNAs) using miRBase, LNCipedia, RNAcentral, Rfam, and target prediction databases. Covers ncRNA identification, target prediction, disease associations, expression profiling, and functional annotation. Use when asked about microRNAs, long non-coding RNAs, RNA interference, miRNA targets, lncRNA function, or ncRNA-disease associations.
---

# Non-Coding RNA Analysis

Pipeline for identifying, annotating, and interpreting non-coding RNAs and their biological roles. Covers microRNAs (miRNAs), long non-coding RNAs (lncRNAs), and other ncRNA classes.

**Key principles**:
1. **Class determines function** — miRNAs repress mRNA translation; lncRNAs have diverse mechanisms (scaffolds, guides, decoys, enhancers); rRNAs/tRNAs are structural
2. **Targets matter more than the ncRNA itself** — for miRNAs, the regulated mRNA targets determine the phenotype
3. **Expression context is critical** — ncRNAs are highly tissue/cell-type specific
4. **Conservation indicates function** — deeply conserved ncRNAs (miR-let-7, MALAT1) have well-established roles
5. **Evidence grading** — T1: validated targets (reporter assay, CLIP-seq), T2: high-confidence computational prediction, T3: expression correlation, T4: sequence-based prediction only

---

## When to Use

- "What are the targets of miR-21?"
- "Find lncRNAs associated with breast cancer"
- "Is this lncRNA conserved across species?"
- "What miRNAs regulate TP53?"
- "Annotate these non-coding RNA IDs"
- "Which miRNAs are biomarkers for [disease]?"

**Not this skill**: For mRNA expression analysis, use `tooluniverse-rnaseq-deseq2`. For CRISPR screens, use `tooluniverse-crispr-screen-analysis`.

---

## Core Tools

| Tool | Use For |
|------|---------|
| `miRBase_search_mirna` | Search miRNAs by name, accession, or sequence |
| `miRBase_get_mirna` | Detailed miRNA info (sequence, genomic location, family) |
| `miRBase_get_mature_mirna` | Mature miRNA sequences and annotations |
| `miRBase_get_mirna_targets` | Experimentally validated and predicted miRNA targets |
| `LNCipedia_search` | Search lncRNAs by name, gene symbol, or transcript ID |
| `LNCipedia_get_transcript` | Detailed lncRNA transcript info (sequence, structure, conservation) |
| `LNCipedia_get_gene` | lncRNA gene info with all transcript variants |
| `LNCipedia_list_transcripts` | List all transcripts for a lncRNA gene |
| `LNCipedia_get_sequence` | lncRNA sequence (FASTA format) |
| `RNAcentral_search` | Search all ncRNA types across databases |
| `RNAcentral_get_rna` | Detailed ncRNA annotations from 40+ databases |
| `Rfam_get_family` | RNA family details (structure, alignment, species distribution) |
| `Rfam_search` | Search RNA families by keyword |
| `DisGeNET_search_gene` | ncRNA-disease associations |
| `PubMed_search_articles` | ncRNA literature |
| `GTEx_get_median_gene_expression` | Tissue expression of ncRNA genes |

---

## Workflow

```
Phase 0: ncRNA Identity & Classification
  Name/ID → miRBase/LNCipedia/RNAcentral → class, sequence, genomic location
    |
Phase 1: Target & Interaction Analysis
  miRNA → target mRNAs; lncRNA → interacting proteins/RNAs/chromatin
    |
Phase 2: Expression & Tissue Specificity
  GTEx/GEO → where is it expressed? Tissue-specific or ubiquitous?
    |
Phase 3: Disease Associations
  DisGeNET/PubMed/CTD → ncRNA-disease links with evidence
    |
Phase 4: Functional Interpretation
  Pathway enrichment of targets → biological role → clinical significance
```

### Phase 0: ncRNA Identity & Classification

| ncRNA Class | Size | Database | Function |
|---|---|---|---|
| **miRNA** | ~22 nt | miRBase | Post-transcriptional gene silencing via 3'UTR binding |
| **lncRNA** | >200 nt | LNCipedia | Diverse: chromatin remodeling, transcription regulation, miRNA sponges |
| **rRNA** | 120-5000 nt | RNAcentral/Rfam | Ribosome components (translation) |
| **tRNA** | ~76 nt | RNAcentral | Amino acid delivery to ribosome |
| **snoRNA** | 60-300 nt | Rfam | rRNA modification (methylation, pseudouridylation) |
| **snRNA** | ~150 nt | Rfam | Spliceosome components (mRNA splicing) |
| **piRNA** | 26-31 nt | RNAcentral | Transposon silencing in germline |
| **circRNA** | Variable | RNAcentral | miRNA sponges, protein scaffolds |

**Identification workflow**:
- Name starts with `miR-` or `hsa-mir-` → search miRBase
- Name starts with `LINC`, `MALAT`, `HOTAIR`, `XIST`, or ends in `-AS1` → search LNCipedia
- Any ncRNA type → search RNAcentral (aggregates all databases)
- RNA family question → search Rfam

### Phase 1: Target & Interaction Analysis

**For miRNAs** — the targets determine the biology:

```python
miRBase_get_mirna_targets(accession="MIMAT0000076")  # miR-21 targets
# Returns validated targets with evidence type (reporter assay, Western blot, qPCR)
```

**Target interpretation framework**:

| Evidence Level | Method | Confidence | Use |
|---|---|---|---|
| **Validated** | Luciferase reporter, CLIP-seq, degradome-seq | High (T1) | Base conclusions on these |
| **High-confidence prediction** | TargetScan (conserved sites), DIANA-microT (score>0.9) | Medium (T2) | Support validated findings |
| **Prediction only** | miRanda, PicTar, RNA22 | Low (T3-T4) | Hypothesis generation only |

**For lncRNAs** — the mechanism varies:

| lncRNA Mechanism | Example | How to Investigate |
|---|---|---|
| **Chromatin modifier** | HOTAIR, XIST | Check interacting proteins (PRC2, LSD1) via PubMed |
| **Transcription regulator** | NEAT1, MEG3 | Check nearby genes (cis-regulation) via genomic location |
| **miRNA sponge** | MALAT1, circRNAs | Search for miRNA binding sites |
| **Scaffold** | NKILA, BCAR4 | Check protein interactions |
| **Enhancer RNA** | eRNAs | Check ENCODE enhancer annotations |

### Phase 2: Expression & Tissue Specificity

```python
GTEx_get_median_gene_expression(gene="MIR21")  # miRNA host gene expression
# Note: GTEx measures RNA-seq; miRNA expression may need miRNA-seq data from GEO
```

**Interpretation**: Tissue-restricted ncRNAs are often functionally important in that tissue. Ubiquitous ncRNAs (like MALAT1) tend to have housekeeping roles.

### Phase 3: Disease Associations

```python
DisGeNET_search_gene(query="MIR21")  # miR-21 disease associations
PubMed_search_articles(query="miR-21 biomarker cancer")
```

**Key ncRNA-disease associations** (well-established):

| ncRNA | Disease | Role | Evidence |
|---|---|---|---|
| miR-21 | Multiple cancers | OncomiR; targets PTEN, PDCD4, TPM1 | T1 (hundreds of studies) |
| miR-155 | B-cell lymphoma, inflammation | Immune regulation | T1 |
| miR-122 | Hepatitis C, liver disease | HCV replication cofactor; therapeutic target (miravirsen) | T1 |
| let-7 family | Lung cancer, stem cell differentiation | Tumor suppressor; targets RAS, HMGA2 | T1 |
| HOTAIR | Breast, colorectal cancer | Recruits PRC2; metastasis | T1 |
| MALAT1 | Lung cancer, metastasis | Splicing regulation, transcription | T1 |
| XIST | X-inactivation, cancer | Chromatin silencing | T1 |
| NEAT1 | Paraspeckle formation, cancer | Nuclear body scaffold | T2 |
| H19 | Beckwith-Wiedemann, cancer | Imprinted lncRNA; miR-675 host | T1 |
| ANRIL | CVD, diabetes, cancer | CDKN2A/B locus regulation | T1 (GWAS) |

### Phase 4: Functional Interpretation

After identifying miRNA targets (Phase 1), run pathway enrichment:

```python
# Collect validated target gene symbols
targets = ["PTEN", "PDCD4", "TPM1", "RECK", "SPRY1"]  # miR-21 targets

# Pathway enrichment
ReactomeAnalysis_pathway_enrichment(identifiers="PTEN PDCD4 TPM1 RECK SPRY1")
STRING_get_network(identifiers="PTEN\rPDCD4\rTPM1\rRECK\rSPRY1", species=9606)
```

**Interpretation**: If miR-21 targets are enriched in apoptosis and PI3K-AKT signaling → miR-21 is an oncomiR that promotes survival by simultaneously suppressing multiple tumor suppressors.

**Report structure**:
1. **ncRNA Identity** — class, sequence, genomic location, conservation
2. **Targets/Interactions** — validated targets with evidence grades
3. **Expression Profile** — tissue specificity, disease-specific expression changes
4. **Disease Associations** — evidence-graded disease links
5. **Pathway Analysis** — enriched pathways among targets
6. **Mechanistic Model** — how this ncRNA contributes to disease biology
7. **Clinical Potential** — biomarker utility, therapeutic target potential (antagomirs, ASOs)

---

## Limitations

- **miRNA target prediction is noisy** — even the best algorithms have >50% false positive rates; always prioritize experimentally validated targets
- **lncRNA function is poorly characterized** — only ~5% of annotated lncRNAs have known functions
- **Expression measurement varies** — miRNA-seq, RNA-seq, and microarray capture different ncRNA classes; check the assay type
- **Species differences** — miRNAs are often conserved but lncRNAs are frequently species-specific; cross-species lncRNA comparisons are unreliable
