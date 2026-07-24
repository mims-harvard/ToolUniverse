# Metabolomics Analysis Report Template

## Example Report: LC-MS Disease vs Control

```markdown
# Metabolomics Analysis Report

## Dataset Summary
- **Platform**: LC-MS/MS (Orbitrap)
- **Method**: Untargeted metabolomics
- **Samples**: 40 (20 disease, 20 control)
- **Metabolites Identified**: 324 (Level 1/2 confidence)
- **Metabolites Quantified**: 298 (after QC)

## Quality Control
- **CV in QC samples**: 18% median (acceptable: <30%)
- **Blank ratios**: All metabolites > 3x blank signal
- **Missing values**: 8% average per metabolite
- **Internal standard**: Recovery 95-105% across samples

## Normalization
- **Method**: Probabilistic Quotient Normalization (PQN)
- **Transformation**: log2
- **Batch correction**: Not required (single batch)

## Exploratory Analysis
- **PCA**: Clear separation between groups (PC1: 28%, PC2: 18%)
- **PLS-DA**: Excellent discrimination (R2=0.89, Q2=0.75)
- **Outliers**: 1 sample removed (technical failure)

## Differential Metabolites
- **Significant metabolites**: 87 (adj. p < 0.05, |log2FC| > 1)
  - Increased: 52 metabolites
  - Decreased: 35 metabolites

### Top Increased Metabolites
1. **Lactate** (log2FC=3.2, p=1e-12) - Glycolysis
2. **Glutamine** (log2FC=2.8, p=1e-10) - Amino acid metabolism
3. **Palmitate** (log2FC=2.5, p=1e-9) - Fatty acid synthesis

### Top Decreased Metabolites
1. **Citrate** (log2FC=-2.9, p=1e-11) - TCA cycle
2. **ATP** (log2FC=-2.3, p=1e-9) - Energy metabolism
3. **NAD+** (log2FC=-2.1, p=1e-8) - Redox balance

## Pathway Enrichment
### Top Dysregulated Pathways
1. **Glycolysis/Gluconeogenesis** (p=1e-15)
   - 12 metabolites: glucose, pyruvate, lactate, etc.
   - Direction: Increased flux to lactate (Warburg effect)
2. **TCA Cycle** (p=1e-12)
   - 8 metabolites: citrate, succinate, malate, etc.
   - Direction: Decreased activity
3. **Glutaminolysis** (p=1e-10)
   - 6 metabolites: glutamine, glutamate, a-KG, etc.
   - Direction: Increased glutamine consumption

## Multi-Omics Integration
### Metabolite-Enzyme Correlations
- **LDHA (lactate dehydrogenase)**
  - Expression: 3.5-fold increased (RNA + protein)
  - Lactate: 3.2-fold increased
  - Correlation: r=0.85 (p<0.001) - Concordant upregulation
- **IDH1 (isocitrate dehydrogenase)**
  - Expression: 2.1-fold decreased
  - Citrate: 2.9-fold decreased
  - Correlation: r=0.78 (p<0.001) - TCA cycle suppression

### Metabolic Phenotype
Integration with RNA-seq and proteomics reveals:
- **Warburg effect**: Shift from oxidative to glycolytic metabolism
- **Glutamine addiction**: Increased glutaminolysis for anaplerosis
- **Redox imbalance**: Decreased NAD+/NADH ratio, oxidative stress

## Biomarker Discovery
### Top 10 Metabolites for Classification
Random Forest model (10-fold CV):
- **AUC**: 0.96 +/- 0.03
- **Accuracy**: 92%

**Biomarker Panel**:
1. Lactate
2. Glutamine
3. Citrate
4. ATP
5. Palmitate
6. Pyruvate
7. Succinate
8. NAD+
9. a-ketoglutarate
10. Glucose-6-phosphate

## Biological Interpretation
Metabolomics reveals fundamental metabolic reprogramming in disease state:

1. **Glycolytic switch**: Increased glycolysis with lactate accumulation despite oxygen
   availability (Warburg effect), driven by LDHA upregulation.
2. **TCA cycle suppression**: Decreased citrate and TCA intermediates, consistent with
   IDH1 downregulation. Shunts carbon to biosynthesis.
3. **Glutamine dependence**: Elevated glutamine consumption provides alternative carbon
   source for anaplerosis and NADPH for biosynthesis.
4. **Biosynthetic activation**: Increased palmitate indicates active fatty acid synthesis,
   supporting membrane production for proliferation.
5. **Energy stress**: Despite active glycolysis, ATP levels are decreased, suggesting high
   energy demand outpacing production.

## Clinical Relevance
- **Therapeutic targets**: LDHA inhibitors, glutaminase inhibitors
- **Biomarkers**: Lactate/citrate ratio as metabolic activity marker
- **Drug response**: Metabolic phenotype may predict sensitivity to metabolic inhibitors
```
