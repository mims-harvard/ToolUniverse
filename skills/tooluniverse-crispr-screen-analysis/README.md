# CRISPR Screen Analysis Skill

## Overview

Comprehensive analysis workflow for CRISPR knockout/activation/interference screens. Integrates gene essentiality data from DepMap, pathway enrichment analysis, protein interaction networks, druggability assessment, and clinical relevance to prioritize hits for experimental validation and therapeutic targeting.

## Quick Start

### Input Format

Provide gene list from your screen:
```
Analyze these CRISPR hits: KRAS, EGFR, WEE1, PLK1, AURKA, CDK2, CHEK1, MCM2, E2F1, RB1
```

Or ask about a specific cancer type:
```
What are the top essential genes for pancreatic cancer?
```

Or validate a single gene:
```
Is WEE1 a good therapeutic target for TP53-mutant cancers?
```

### Output

Complete markdown report with:
- **Essentiality Analysis**: DepMap scores, pan-cancer vs selective classification
- **Pathway Enrichment**: GO, Reactome, KEGG, MSigDB hallmarks
- **PPI Networks**: Protein complexes, hub genes, synthetic lethal candidates
- **Druggability**: Pharos TDL, approved drugs, clinical compounds, chemical probes
- **Clinical Relevance**: COSMIC mutations, expression, biomarkers, trials
- **Hit Prioritization**: Top 10 targets with multi-dimensional scores (0-100)
- **Validation Strategy**: Recommended experiments, tool compounds, timelines

## Key Features

✅ **Multi-dimensional prioritization** - Integrates essentiality + selectivity + druggability + clinical relevance
✅ **Validation recommendations** - Specific experiments, tool compounds, expected outcomes
✅ **Tier-based ranking** - Tier 1 (immediate) > Tier 2 (medium-term) > Tier 3 (long-term)
✅ **Pathway-level interpretation** - Identifies convergent pathways and protein complexes
✅ **Synthetic lethal discovery** - Finds combination therapy opportunities
✅ **Evidence grading** - ★★★ (high) to ★☆☆ (low) based on data quality

## Analysis Modes

### 1. Gene List Analysis (Most Common)
- **Input**: 5-100 gene symbols from your CRISPR screen
- **Use case**: Prioritize hits from pooled/arrayed screen
- **Output**: Comprehensive report with prioritization

### 2. Cancer Type Query
- **Input**: Cancer type name (e.g., "lung cancer", "breast cancer")
- **Use case**: Find essential genes for specific cancer
- **Output**: Top 20-50 essential genes for that cancer

### 3. Single Gene Validation
- **Input**: One gene symbol
- **Use case**: Deep dive on specific target, validate essentiality
- **Output**: Target validation report with selectivity analysis

## Supported Screens

- ✅ **CRISPR knockout** (Cas9, dropout/depletion screens)
- ✅ **CRISPR activation** (CRISPRa, enrichment screens)
- ✅ **CRISPR interference** (CRISPRi, knockdown screens)
- ✅ **shRNA screens** (similar workflow)

## Examples

See [EXAMPLES.md](EXAMPLES.md) for detailed walkthroughs:
- Example 1: Lung cancer A549 cell line screen (20 genes)
- Example 2: Pancreatic cancer essentiality query
- Example 3: WEE1 target validation (TP53 synthetic lethal)
- Example 4: RB1 synthetic lethal analysis
- Example 5: DNA repair pathway analysis
- Example 6: Lung vs breast cancer comparison
- Example 7: Prioritizing 100 hits down to 10 for validation

## Tools Used

### Core Tools
- **DepMap**: Gene essentiality data from 1000+ cancer cell lines
- **Enrichr**: Pathway and GO enrichment analysis
- **STRING**: Protein-protein interaction networks
- **Pharos**: Target development level (Tclin/Tchem/Tbio/Tdark)
- **DGIdb**: Drug-gene interaction database
- **Open Targets**: Chemical probes, tractability, safety
- **ClinicalTrials.gov**: Clinical trial status
- **COSMIC**: Somatic mutations in cancer

### Supporting Tools
- GTEx: Gene expression in normal tissues
- TCGA: Gene expression in tumors
- IntAct: Curated protein interactions
- ChEMBL: Bioactivity data for tool compounds
- PubMed: Literature validation

## Limitations

⚠ **Not designed for**:
- RNA-seq differential expression analysis (different workflow)
- ChIP-seq or epigenomics screens (different context)
- Metabolic screens (requires different tools)
- Morphology screens (requires image analysis)

⚠ **Data limitations**:
- DepMap represents cell lines, not patient tumors (may not reflect in vivo)
- Tool compounds may not perfectly phenocopy genetic knockout
- Selectivity in cell lines may differ from patient-level selectivity

⚠ **Biological limitations**:
- CRISPR artifacts (off-target effects, toxicity of Cas9 cutting)
- Pathway redundancy not captured in single-gene knockout
- Context-dependency (nutrient conditions, 2D vs 3D culture)

## Validation Recommendations

### Tier 1 Targets (High Priority)
- Existing approved/late-stage drugs available
- Strong selective essentiality (tissue-specific)
- Validation timeline: 2-3 weeks
- Success rate: 80-100%

### Tier 2 Targets (Medium Priority)
- Chemical probes or early-stage compounds available
- Moderate essentiality, good druggability
- Validation timeline: 4-8 weeks
- Success rate: 60-80%

### Tier 3 Targets (Lower Priority)
- Novel mechanisms, no tool compounds
- Requires alternative strategies (PROTACs, genetic validation only)
- Validation timeline: 8-16 weeks
- Success rate: 20-50%

## Resources Required

### Computational
- ToolUniverse installation with API keys:
  - DepMap (no key required, public API)
  - Enrichr (no key required)
  - STRING (no key required)
  - Pharos (no key required)
  - ClinicalTrials.gov (no key required)

### Experimental Validation
- **Budget**: $15-30K for full validation (10 targets)
  - Compounds: $5-10K
  - Cell culture: $5-10K
  - Assays: $5-10K
- **Personnel**: 1 postdoc + 1 technician for 3-4 months
- **Equipment**: Standard cell culture, plate readers, flow cytometry

## Quality Control

Before considering analysis complete, verify:
- [ ] All input genes validated against DepMap registry
- [ ] Essentiality scores retrieved for 100% of valid genes
- [ ] Pathway enrichment completed (GO + Reactome + Hallmarks minimum)
- [ ] Druggability assessed for all hits (Pharos TDL)
- [ ] Top 10 priority list generated with scores
- [ ] Validation recommendations provided for Tier 1 targets
- [ ] Evidence grades assigned (★★★/★★☆/★☆☆)
- [ ] All findings cited to source tools/databases

## Citation

When using this skill, cite the underlying databases:
- DepMap: Broad Institute DepMap Portal (https://depmap.org/)
- Enrichr: Chen et al., BMC Bioinformatics 2013
- STRING: Szklarczyk et al., Nucleic Acids Res 2021
- Pharos: Nguyen et al., Nucleic Acids Res 2021

## Support

For issues or questions:
- Check [EXAMPLES.md](EXAMPLES.md) for common use cases
- See [SKILL.md](SKILL.md) for detailed methodology
- Report bugs via ToolUniverse GitHub issues

