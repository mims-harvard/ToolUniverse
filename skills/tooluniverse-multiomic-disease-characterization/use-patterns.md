# Use Patterns, Edge Cases & Fallback Strategies

---

## Common Use Patterns

### 1. Comprehensive Disease Profiling
```
User: "Characterize Alzheimer's disease across omics layers"
-> Run all 8 phases
-> Produce full multi-omics report
```

### 2. Therapeutic Target Discovery
```
User: "What are druggable targets for rheumatoid arthritis?"
-> Emphasize Phase 1 (genomics), Phase 6 (therapeutics), Phase 7 (integration)
-> Focus on tractability and clinical precedent
```

### 3. Biomarker Identification
```
User: "Find diagnostic biomarkers for pancreatic cancer"
-> Emphasize Phase 2 (transcriptomics), Phase 3 (proteomics), Phase 7 (biomarkers)
-> Focus on tissue-specific expression and diagnostic potential
```

### 4. Mechanism Elucidation
```
User: "What pathways are dysregulated in Crohn's disease?"
-> Emphasize Phase 4 (pathways), Phase 5 (GO), Phase 7 (mechanistic hypotheses)
-> Focus on pathway enrichment and cross-pathway connections
```

### 5. Drug Repurposing
```
User: "What existing drugs could be repurposed for ALS?"
-> Emphasize Phase 1 (genetics), Phase 6 (therapeutic landscape), Phase 7 (repurposing)
-> Focus on drugs targeting disease-associated genes
```

### 6. Systems Biology
```
User: "What are the hub genes and key pathways in type 2 diabetes?"
-> Emphasize Phase 3 (PPI network), Phase 4 (pathways), Phase 7 (network analysis)
-> Focus on hub genes and network modules
```

---

## Edge Case Handling

### Rare Diseases (limited data)
- Genomics layer may dominate (single gene)
- Limited GWAS data (monogenic)
- Focus on ClinVar variants, pathway consequences
- Confidence score will be lower (less cross-layer data)

### Common Diseases (overwhelming data)
- Thousands of GWAS associations
- Prioritize by effect size and significance
- Focus on top 20-30 genes for downstream analysis
- Use strict significance thresholds (p < 5e-8)

### Cancer
- Include somatic mutations (if CIViC/cBioPortal available)
- Check cancer prognostics via HPA
- Include tumor-specific expression patterns
- Clinical trial landscape may be extensive

### Monogenic Diseases
- Single gene dominates
- ClinVar/OMIM evidence is primary
- Pathway analysis reveals downstream effects
- Therapeutic landscape may be limited (gene therapy, enzyme replacement)

### Polygenic Diseases
- Many weak genetic signals
- GWAS provides the gene list
- Pathway enrichment reveals convergent biology
- Network analysis identifies hub genes

### Tissue Ambiguity
- Diseases affecting multiple tissues
- Query HPA for all relevant tissues
- Compare tissue-specific expression patterns
- Use tissue context from disease ontology

---

## Fallback Strategies

### If disease name not found
1. Try synonyms
2. Try broader disease category
3. Try OMIM/UMLS ID mapping
4. Report disambiguation failure and ask user

### If no GWAS data
1. Check ClinVar for rare variants
2. Use OpenTargets genetic evidence
3. Note in report as "Limited genetic data"
4. Adjust confidence score accordingly

### If no expression data
1. Try different disease name/synonym
2. Check HPA for individual gene expression
3. Use OpenTargets expression evidence
4. Note as "Limited transcriptomics data"

### If no pathway enrichment
1. Reduce gene list stringency
2. Try different pathway databases
3. Map individual genes to pathways via Reactome
4. Note as "No significant pathway enrichment"

### If no drugs found
1. Check if disease is rare/orphan
2. Look for drugs targeting individual genes
3. Check clinical trials for investigational therapies
4. Note as "No approved drugs - novel therapeutic opportunity"
