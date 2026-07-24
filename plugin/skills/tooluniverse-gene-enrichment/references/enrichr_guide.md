# Complete Enrichr Library Guide

Comprehensive guide to all 225+ Enrichr libraries available via gseapy.

---

## Discovering Available Libraries

```python
import gseapy as gp

# List all available libraries
all_libs = gp.get_library_name(organism='human')
print(f"Total libraries: {len(all_libs)}")
print(all_libs)

# Search for specific library
matching = [lib for lib in all_libs if 'GO_Biological' in lib]
print(matching)
# Output: ['GO_Biological_Process_2021', 'GO_Biological_Process_2023', 'GO_Biological_Process_2025']
```

---

## Gene Ontology (GO) Libraries

### GO Biological Process
- `GO_Biological_Process_2021` - 17,000+ terms (recommended)
- `GO_Biological_Process_2023` - Updated version
- `GO_Biological_Process_2025` - Latest version

**Use for**: Understanding biological processes (e.g., cell cycle, apoptosis, DNA repair)

### GO Molecular Function
- `GO_Molecular_Function_2021` - 4,000+ terms (recommended)
- `GO_Molecular_Function_2023`
- `GO_Molecular_Function_2025`

**Use for**: Understanding biochemical activities (e.g., kinase activity, DNA binding, transporter activity)

### GO Cellular Component
- `GO_Cellular_Component_2021` - 1,700+ terms (recommended)
- `GO_Cellular_Component_2023`
- `GO_Cellular_Component_2025`

**Use for**: Understanding subcellular localization (e.g., nucleus, mitochondria, membrane)

---

## Pathway Databases

### KEGG Pathways
- `KEGG_2021_Human` - 327 human pathways (recommended)
- `KEGG_2019_Mouse` - Mouse pathways
- `KEGG_2026` - Latest version

**Use for**: Canonical metabolic and signaling pathways

**Examples**:
- hsa04110: Cell cycle
- hsa04151: PI3K-Akt signaling
- hsa05200: Pathways in cancer

### Reactome Pathways
- `Reactome_2022` - 2,500+ pathways
- `Reactome_Pathways_2024` - Latest version (recommended)

**Use for**: Detailed, curated pathway analysis with hierarchical structure

### WikiPathways
- `WikiPathways_2024_Human` - Community-curated pathways (recommended)
- `WikiPathways_2024_Mouse`

**Use for**: Emerging pathways, disease-specific pathways, community contributions

### BioCarta
- `BioCarta_2016` - 249 pathways

**Use for**: Signal transduction pathways (legacy database, no longer updated)

### BioPlanet
- `BioPlanet_2019` - NCI Pathway Interaction Database

**Use for**: Comprehensive pathway coverage including regulatory pathways

---

## MSigDB Collections

### Hallmark Gene Sets
- `MSigDB_Hallmark_2020` - 50 hallmark gene sets

**Use for**: Cancer research, well-defined biological states

**Examples**:
- HALLMARK_APOPTOSIS
- HALLMARK_CELL_CYCLE
- HALLMARK_INFLAMMATORY_RESPONSE
- HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION

### Computational Gene Sets
- `MSigDB_Computational` - Computational predictions

**Use for**: Predicted gene sets from computational methods

### Oncogenic Signatures
- `MSigDB_Oncogenic_Signatures` - Cancer-related signatures

**Use for**: Cancer driver pathways, oncogene/tumor suppressor signatures

---

## Disease and Phenotype Libraries

### Disease Associations
- `DisGeNET` - Gene-disease associations from text mining
- `OMIM_Disease` - Mendelian diseases from OMIM
- `OMIM_Expanded` - Extended OMIM annotations
- `ClinVar_2025` - Clinical variants and associations
- `Rare_Diseases_GeneRIF_Gene_Lists` - Rare disease gene sets

**Use for**: Disease characterization, clinical interpretation

### Human Phenotype Ontology
- `HPO_2025` - Human phenotype terms

**Use for**: Phenotype enrichment, clinical feature analysis

---

## Drug and Chemical Libraries

### Drug-Gene Interactions
- `DGIdb_Drug_Targets_2024` - Drug-gene interaction database
- `DrugMatrix` - Toxicogenomics database

**Use for**: Drug mechanism, target identification, toxicity prediction

### Drug Perturbations
- `Drug_Perturbations_from_GEO_down` - Genes down-regulated by drugs
- `Drug_Perturbations_from_GEO_up` - Genes up-regulated by drugs

**Use for**: Drug effect prediction, mechanism of action

---

## Cell Type and Tissue Libraries

### Cell Type Markers
- `CellMarker_2024` - Cell type marker genes (recommended)
- `Azimuth_2023` - Single-cell reference-based cell type markers
- `Descartes_Cell_Types_and_Tissue_2021` - Human developmental cell types
- `Allen_Brain_Atlas_10x_scRNA_2021` - Brain cell types

**Use for**: Cell type identification from single-cell or bulk RNA-seq

### Tissue Expression
- `GTEx_Tissues_V8_2023` - Tissue-specific expression from GTEx
- `ARCHS4_Tissues` - Tissue signatures from ARCHS4
- `Human_Gene_Atlas` - Gene expression across tissues

**Use for**: Tissue specificity analysis

---

## Transcription Factor Libraries

### TF ChIP-seq
- `ChEA_2022` - Transcription factor targets (recommended)
- `ENCODE_TF_ChIP-seq_2015` - ENCODE TF binding sites
- `ENCODE_and_ChEA_Consensus_TFs_from_ChIP-X` - Consensus TF targets

**Use for**: Upstream regulator analysis, transcription factor binding

### TF-Target Predictions
- `TRANSFAC_and_JASPAR_PWMs` - TF binding motifs
- `TRRUST_Transcription_Factors_2019` - Human TF regulatory relationships

**Use for**: Motif analysis, regulatory network reconstruction

---

## Epigenomics Libraries

### Histone Modifications
- `ENCODE_Histone_Modifications_2015` - ENCODE histone ChIP-seq
- `Epigenomics_Roadmap_HM_ChIP-seq` - Roadmap Epigenomics histone marks

**Use for**: Chromatin state analysis, epigenetic regulation

---

## Protein Interaction and Complex Libraries

### Protein Complexes
- `CORUM` - Comprehensive Resource of Mammalian protein complexes

**Use for**: Protein complex enrichment, functional module identification

### Subcellular Localization
- `COMPARTMENTS_Curated_2025` - Curated protein localization
- `COMPARTMENTS_Experimental_2025` - Experimental protein localization
- `COMPARTMENTS_Text_Mining_2025` - Text-mined protein localization

**Use for**: Subcellular localization analysis

---

## Specialized Libraries

### Synaptic Gene Ontology
- `SynGO_2022` - Synaptic gene ontology
- `SynGO_2024` - Latest version

**Use for**: Neuroscience, synaptic function analysis

### Cancer Dependencies
- `DepMap_CRISPR_GeneDependency_CellLines_2023` - Cancer cell line gene dependencies

**Use for**: Cancer target identification, synthetic lethality

### Elsevier Pathway Collection
- `Elsevier_Pathway_Collection` - Comprehensive pathway collection

**Use for**: Broad pathway coverage

---

## Library Selection Guide

### For General Analysis
```python
# Standard enrichment panel
standard_libraries = [
    'GO_Biological_Process_2021',
    'GO_Molecular_Function_2021',
    'GO_Cellular_Component_2021',
    'KEGG_2021_Human',
    'Reactome_Pathways_2024',
]
```

### For Cancer Research
```python
cancer_libraries = [
    'MSigDB_Hallmark_2020',
    'MSigDB_Oncogenic_Signatures',
    'Reactome_Pathways_2024',
    'DepMap_CRISPR_GeneDependency_CellLines_2023',
]
```

### For Disease Research
```python
disease_libraries = [
    'DisGeNET',
    'OMIM_Disease',
    'ClinVar_2025',
    'HPO_2025',
]
```

### For Drug Discovery
```python
drug_libraries = [
    'DGIdb_Drug_Targets_2024',
    'Drug_Perturbations_from_GEO_down',
    'Drug_Perturbations_from_GEO_up',
    'DrugMatrix',
]
```

### For Single-Cell Analysis
```python
scrnaseq_libraries = [
    'CellMarker_2024',
    'Azimuth_2023',
    'Allen_Brain_Atlas_10x_scRNA_2021',
    'Descartes_Cell_Types_and_Tissue_2021',
]
```

### For Regulatory Analysis
```python
regulatory_libraries = [
    'ChEA_2022',
    'ENCODE_TF_ChIP-seq_2015',
    'ENCODE_Histone_Modifications_2015',
]
```

---

## Library Version Selection

### When to Use Older Versions (2021-2022)
- More citations in literature
- Better validated
- More stable results
- Recommended for publication

### When to Use Latest Versions (2024-2025)
- More comprehensive (newer annotations)
- Latest disease/drug associations
- More cell types (from recent atlases)
- For exploratory analysis

### Recommendation
**Default to 2021-2022 versions for primary analysis, validate with 2024-2025 versions**

---

## Usage Examples

### Single Library
```python
import gseapy

result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets='GO_Biological_Process_2021',
    organism='human',
    outdir=None,
    no_plot=True,
)
```

### Multiple Libraries
```python
result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets=[
        'GO_Biological_Process_2021',
        'KEGG_2021_Human',
        'Reactome_Pathways_2024',
        'MSigDB_Hallmark_2020',
    ],
    organism='human',
    outdir=None,
    no_plot=True,
)

# Results combined in single DataFrame
# Use 'Gene_set' column to distinguish libraries
go_results = result.results[result.results['Gene_set'] == 'GO_Biological_Process_2021']
kegg_results = result.results[result.results['Gene_set'] == 'KEGG_2021_Human']
```

### All GO Categories at Once
```python
result = gseapy.enrichr(
    gene_list=gene_symbols,
    gene_sets=[
        'GO_Biological_Process_2021',
        'GO_Molecular_Function_2021',
        'GO_Cellular_Component_2021',
    ],
    organism='human',
    outdir=None,
    no_plot=True,
)
```

---

## Library Update Frequency

| Library | Update Frequency | Latest Version |
|---------|------------------|----------------|
| GO (BP, MF, CC) | Annual | 2025 |
| KEGG | Every 2-3 years | 2026 |
| Reactome | Annual | 2024 |
| WikiPathways | Annual | 2024 |
| MSigDB Hallmark | Every 3-5 years | 2020 |
| DisGeNET | Annual | 2024 |
| CellMarker | Annual | 2024 |
| ChEA | Every 2-3 years | 2022 |

---

## Best Practices

1. **Start with standard panel** (GO + KEGG + Reactome)
2. **Use consistent library versions** across analyses
3. **Document library versions** in methods
4. **Validate with multiple libraries** (cross-database confirmation)
5. **Check library date** relative to your experiment date
6. **Use organism-specific libraries** when available
7. **Report library in results** (not just "GO enrichment")
8. **Compare 2021 vs latest** for robustness

---

## Organism-Specific Libraries

### Human
- All libraries available
- Use `organism='human'` or `organism='Human'`

### Mouse
- `KEGG_2019_Mouse`
- `WikiPathways_2024_Mouse`
- `GO_*_2021` (use organism='mouse')

### Other Organisms
```python
# Supported organisms
supported = ['human', 'mouse', 'fly', 'yeast', 'worm', 'fish', 'rat']

# For other organisms, use human libraries with ortholog conversion
```

---

See also:
- ora_workflow.md - How to use these libraries with ORA
- gsea_workflow.md - How to use these libraries with GSEA
- cross_validation.md - Multi-library validation strategies
