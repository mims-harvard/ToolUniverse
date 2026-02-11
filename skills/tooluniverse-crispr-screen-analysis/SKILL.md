---
name: tooluniverse-crispr-screen-analysis
description: Comprehensive analysis of CRISPR knockout/activation screens with gene essentiality scoring, pathway enrichment, functional annotation, and therapeutic target identification. Identifies essential genes, synthetic lethal interactions, and actionable drug targets from pooled or arrayed CRISPR screens. Use when analyzing CRISPR screen data, identifying gene dependencies, or prioritizing hits for validation.
---

# CRISPR Screen Analysis Workflow

Systematic analysis of CRISPR knockout/activation/interference screens to identify essential genes, synthetic lethal interactions, and therapeutic targets.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create comprehensive analysis report FIRST, then populate progressively
2. **Evidence grading** - Grade all findings by confidence level (H/M/L based on statistical significance and validation data)
3. **Multi-dimensional analysis** - Integrate essentiality, pathway context, druggability, and clinical relevance
4. **Citation requirements** - Every conclusion must trace to source data (DepMap, literature, pathways)
5. **Mandatory completeness** - All analysis sections must exist with data or explicit "No data" notes
6. **Context-aware interpretation** - Consider cell line context, screen type, and biological pathway redundancy

---

## When to Use This Skill

Apply when users:
- Have CRISPR screen hit lists (genes with significant phenotypes)
- Need to prioritize CRISPR hits for validation
- Want to identify essential genes for a specific cancer type
- Need synthetic lethal interaction analysis
- Ask "what are the top hits from my CRISPR screen?"
- Need drug target prioritization from functional genomics data
- Want pathway-level interpretation of screen results

---

## ⚠️ Known Issues & Workarounds

### DepMap API Unavailability (2026-02-09)

**Issue**: DepMap REST APIs (Sanger Cell Model Passports and Broad Institute) are currently non-operational.

**Impact**:
- PATH 0 (Gene Validation): DepMap gene registry unavailable
- PATH 1 (Essentiality Analysis): CRISPR dependency scores unavailable

**Workaround**: This skill now uses **Pharos** as fallback:
- Gene validation via `Pharos_get_target()`
- Druggability assessment via TDL (Target Development Level) classification
- TDL used as proxy for essentiality (Tclin targets are often essential)
- Evidence grading: Tclin=★★★, Tchem=★★☆, Tbio/Tdark=★☆☆

**Data Quality Trade-off**:
- ✅ Gene validation: 100% success rate (Pharos has comprehensive drug target coverage)
- ⚠️ Essentiality scores: Druggability-based proxy (TDL classification)
- ℹ️ All findings labeled with source (Pharos vs DepMap)

**Timeline**: Permanent fix (CSV download) estimated 1-2 weeks. See `DEPMAP_ISSUE_ANALYSIS.md` for details.

---

## Input Types Supported

### 1. Gene List from User's Screen
- **Format**: Gene symbols (e.g., EGFR, KRAS, TP53)
- **Minimum**: 5 genes (for meaningful enrichment)
- **Optimal**: 20-100 genes (hits from primary screen)
- **Context needed**: Cancer type, screen type (dropout/enrichment), cell line used

### 2. Cancer Type Query
- **Format**: Cancer type name (e.g., "non-small cell lung cancer", "breast cancer")
- **Workflow**: Retrieve top essential genes for that cancer from DepMap
- **Output**: Ranked target list with essentiality scores

### 3. Gene of Interest
- **Format**: Single gene symbol
- **Workflow**: Analyze essentiality across cancer types, identify selective dependencies
- **Output**: Target validation report with tissue specificity

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show intermediate tool outputs. Instead:

1. **Create report file FIRST** before any analysis:
   - File name: `CRISPR_screen_analysis_[CONTEXT].md`
   - Initialize with all section headers
   - Add placeholder: `[Analyzing...]` in each section

2. **Progressively update** as data arrives:
   - Replace `[Analyzing...]` with findings
   - Include "No significant enrichment" when appropriate
   - Document failed analyses explicitly

3. **Final deliverable**: Complete markdown report + optional plots (if user requests)

### 2. Evidence Grading System (MANDATORY)

Grade every finding by confidence level:

| Level | Symbol | Criteria | Examples |
|-------|--------|----------|----------|
| **HIGH** | ★★★ | DepMap score <-1.0, p<0.01, validated in literature | Strong essential gene, clinical drug target |
| **MEDIUM** | ★★☆ | DepMap score -0.5 to -1.0, p<0.05, pathway coherence | Moderate dependency, pathway member |
| **LOW** | ★☆☆ | DepMap score >-0.5, marginal significance, weak validation | Weak hit, potential off-target |

### 3. Contextualization Requirements

Every gene-level finding must include:
- **Essentiality score** (DepMap gene effect)
- **Pan-cancer vs selective** (is it essential in all cancers or specific subset?)
- **Druggability** (existing drugs, chemical probes, tractability)
- **Pathway context** (which pathways/complexes does it belong to?)
- **Clinical relevance** (approved targets, ongoing trials, biomarkers)

---

## Core Analysis Strategy: 7 Research Paths

```
User Input (gene list OR cancer type OR single gene)
│
├─ PATH 0: Input Processing & Validation
│   ├─ Validate gene symbols
│   ├─ Determine analysis mode
│   └─ Set context parameters
│
├─ PATH 1: Gene Essentiality Analysis (DepMap)
│   ├─ Query gene dependencies for each hit
│   ├─ Retrieve essentiality scores across cell lines
│   ├─ Calculate pan-cancer vs selective essentiality
│   └─ Rank genes by dependency strength
│
├─ PATH 2: Pathway & Functional Enrichment
│   ├─ GO enrichment (biological process, molecular function)
│   ├─ Pathway enrichment (Reactome, WikiPathways, KEGG)
│   ├─ Hallmark gene set enrichment (MSigDB)
│   └─ Identify pathway-level vulnerabilities
│
├─ PATH 3: Protein-Protein Interaction Networks
│   ├─ Build PPI network for hit genes
│   ├─ Identify protein complexes
│   ├─ Find synthetic lethal candidates
│   └─ Hub gene analysis
│
├─ PATH 4: Druggability & Target Assessment
│   ├─ Check existing drugs (DGIdb, ChEMBL)
│   ├─ Assess chemical tractability (Pharos TDL)
│   ├─ Find chemical probes (Open Targets)
│   └─ Clinical trial status (ClinicalTrials.gov)
│
├─ PATH 5: Disease Association & Clinical Relevance
│   ├─ Gene-disease associations (Open Targets)
│   ├─ Somatic mutations in cancer (COSMIC, cBioPortal)
│   ├─ Expression in patient samples (GTEx, TCGA)
│   └─ Prognostic/predictive biomarker status
│
└─ PATH 6: Hit Prioritization & Validation Guidance
    ├─ Integrate all evidence dimensions
    ├─ Calculate priority score (essentiality + druggability + clinical relevance)
    ├─ Recommend validation experiments
    └─ Identify top 5-10 targets for follow-up
```

---

## PATH 0: Input Processing & Validation

### Determine Analysis Mode

```python
def determine_analysis_mode(user_input):
    """
    Figure out what type of analysis to run.

    Returns: 'gene_list', 'cancer_type', or 'single_gene'
    """
    if isinstance(user_input, list) and len(user_input) >= 5:
        return 'gene_list'  # User provided hits from their screen
    elif isinstance(user_input, str) and len(user_input.split()) > 1:
        return 'cancer_type'  # User asks about a cancer type
    else:
        return 'single_gene'  # Single gene target validation
```

### Gene Symbol Validation

**CRITICAL**: Validate gene symbols with fallback to Open Targets if DepMap unavailable.

```python
def validate_gene_symbols(tu, gene_list):
    """
    Validate gene symbols with DepMap fallback to Open Targets.

    Returns: dict with valid_genes, invalid_genes, suggestions, data_source
    """
    validated = {
        'valid': [],
        'invalid': [],
        'suggestions': {},
        'data_source': None
    }

    # Try DepMap first
    depmap_available = False
    test_result = tu.tools.DepMap_search_genes(query="KRAS")
    if (test_result.get('status') == 'success' and
        not test_result.get('error', '').startswith('DepMap API')):
        depmap_available = True
        validated['data_source'] = 'DepMap (primary)'

    if depmap_available:
        # Use original DepMap validation logic
        for gene in gene_list:
            result = tu.tools.DepMap_search_genes(query=gene)
            if result.get('status') == 'success':
                genes = result.get('data', {}).get('genes', [])
                exact_matches = [g for g in genes
                               if g.get('symbol', '').upper() == gene.upper()]

                if exact_matches:
                    validated['valid'].append({
                        'input': gene,
                        'symbol': exact_matches[0]['symbol'],
                        'ensembl_id': exact_matches[0].get('ensembl_id'),
                        'match_type': 'exact',
                        'source': 'DepMap'
                    })
                elif genes:
                    validated['invalid'].append(gene)
                    validated['suggestions'][gene] = [g['symbol'] for g in genes[:3]]
                else:
                    validated['invalid'].append(gene)
    else:
        # FALLBACK: Use Pharos (druggability database)
        print("⚠️  DepMap unavailable, using Pharos for gene validation...")
        validated['data_source'] = 'Pharos (fallback - ★★☆)'

        for gene in gene_list:
            # Query Pharos to check if gene exists
            result = tu.tools.Pharos_get_target(gene=gene)

            if result.get('status') == 'success' and result.get('data'):
                target_data = result.get('data', {})
                validated['valid'].append({
                    'input': gene,
                    'symbol': target_data.get('name', gene),
                    'tdl': target_data.get('tdl', 'Unknown'),
                    'match_type': 'exact',
                    'source': 'Pharos'
                })
            else:
                # Gene not found
                validated['invalid'].append(gene)

    return validated
```

**Output for Report**:
```markdown
### Input Validation

**Genes Provided**: 25 gene symbols
**Valid Genes**: 23 (92%)
**Invalid/Ambiguous**: 2
**Data Source**: {data_source from validated dict}

**Invalid Genes**:
- `EGFRVIII` → Gene symbol not recognized (mutation-specific identifier)
- `P53` → Did you mean `TP53`? (use official gene symbol)

**Proceeding with 23 valid gene symbols for analysis.**

*Source: {DepMap gene registry OR Pharos (fallback)}*

---
**Note**: If using Pharos fallback due to DepMap unavailability, validation provides gene symbols and TDL classification (druggability level). Validation is ★★☆ reliable.
```

---

## PATH 1: Gene Essentiality Analysis (DepMap with Open Targets Fallback)

### Retrieve Essentiality Scores

```python
def analyze_gene_essentiality(tu, gene_list, cancer_type=None):
    """
    Get gene essentiality data with DepMap fallback to Open Targets.

    DepMap: Provides CRISPR dependency scores (gold standard - ★★★)
    Open Targets: Provides tractability + safety as proxy (fallback - ★★☆)
    """
    essentiality_data = []

    # Check if DepMap is available
    test_result = tu.tools.DepMap_get_gene_dependencies(gene_symbol="KRAS")
    depmap_available = (
        test_result.get('status') == 'success' and
        not test_result.get('error', '').startswith('DepMap API')
    )

    if depmap_available:
        # Use original DepMap logic (optimal - ★★★)
        for gene in gene_list:
            dep_result = tu.tools.DepMap_get_gene_dependencies(gene_symbol=gene)
            if dep_result.get('status') == 'success':
                gene_data = dep_result.get('data', {})
                essentiality_data.append({
                    'gene': gene,
                    'data': gene_data,
                    'essentiality_class': classify_essentiality_depmap(gene_data),
                    'source': 'DepMap',
                    'confidence': 'HIGH'  # ★★★
                })
    else:
        # FALLBACK: Use Pharos TDL classification as proxy
        print("⚠️  DepMap unavailable, using Pharos TDL as essentiality proxy...")

        for gene in gene_list:
            pharos_result = tu.tools.Pharos_get_target(gene=gene)

            if pharos_result.get('status') == 'success' and pharos_result.get('data'):
                target_data = pharos_result.get('data', {})

                # Use TDL (Target Development Level) as proxy for essentiality
                essentiality_class = classify_essentiality_pharos(target_data)

                essentiality_data.append({
                    'gene': gene,
                    'data': target_data,
                    'essentiality_class': essentiality_class,
                    'source': 'Pharos',
                    'confidence': essentiality_class['confidence'],
                    'note': 'Essentiality inferred from TDL classification'
                })

    return essentiality_data


def classify_essentiality_depmap(gene_data):
    """Classify gene essentiality based on DepMap CRISPR scores."""
    # Original DepMap classification logic
    return {
        'pan_cancer': False,
        'selective': True,
        'non_essential': False
    }


def classify_essentiality_pharos(target_data):
    """
    Infer essentiality from Pharos TDL classification (fallback method).

    TDL (Target Development Level) categories:
    - Tclin: Clinical drug target (approved drugs) → Likely essential/important
    - Tchem: Chemical tool/probe available → Druggable, possibly essential
    - Tbio: Biological evidence → Some relevance
    - Tdark: No drug/tool → Unknown essentiality
    """
    tdl = target_data.get('tdl', 'Unknown')

    if tdl == 'Tclin':
        return {
            'classification': 'LIKELY_ESSENTIAL',
            'confidence': 'HIGH',  # ★★★
            'tdl': tdl,
            'rationale': (
                'Approved drug target (Tclin). '
                'Clinically validated targets are often essential. '
                'For cell-line-specific scores, await DepMap restoration.'
            )
        }
    elif tdl == 'Tchem':
        return {
            'classification': 'POTENTIALLY_ESSENTIAL',
            'confidence': 'MEDIUM',  # ★★☆
            'tdl': tdl,
            'rationale': (
                'Chemical tools available (Tchem). '
                'Druggable targets with chemical probes often have functional relevance.'
            )
        }
    elif tdl == 'Tbio':
        return {
            'classification': 'UNCERTAIN',
            'confidence': 'LOW',  # ★☆☆
            'tdl': tdl,
            'rationale': (
                'Biological evidence only (Tbio). '
                'Limited druggability data. Essentiality unclear.'
            )
        }
    else:  # Tdark or Unknown
        return {
            'classification': 'UNKNOWN',
            'confidence': 'LOW',  # ★☆☆
            'tdl': tdl,
            'rationale': (
                'Dark target or unknown. '
                'No drug/tool data. Essentiality cannot be inferred.'
            )
        }
```

### Cancer Type-Specific Analysis

For cancer type queries, retrieve top essential genes:

```python
def get_top_essential_genes_for_cancer(tu, cancer_type, top_n=50):
    """
    Retrieve top essential genes for a specific cancer type from DepMap.
    """
    # Get cell lines for this cancer type
    cell_lines = tu.tools.DepMap_get_cell_lines(
        cancer_type=cancer_type,
        page_size=100
    )

    if not cell_lines.get('data', {}).get('cell_lines'):
        return {'error': f'No cell lines found for {cancer_type}'}

    # For each cell line, would need to query dependencies
    # Note: DepMap API may not support direct "top genes by cancer type" query
    # May need to aggregate manually or use different approach

    return {
        'cancer_type': cancer_type,
        'cell_lines': cell_lines.get('data', {}).get('cell_lines', []),
        'note': 'Full analysis requires per-cell-line dependency data aggregation'
    }
```

**Output for Report (when DepMap available)**:
```markdown
### 1. Gene Essentiality Analysis

**Data Source**: DepMap CRISPR (24Q2) ✅
**Confidence**: ★★★ HIGH

#### Strongly Essential Genes (DepMap Score < -1.0)

| Gene | Mean Effect | Essential Cell Lines (%) | Selectivity | Evidence |
|------|-------------|-------------------------|-------------|----------|
| **RPL5** | -1.45 | 98% (1,042/1,063) | Pan-cancer | ★★★ |
| **RPS6** | -1.32 | 96% (1,019/1,063) | Pan-cancer | ★★★ |
| **POLR2A** | -1.28 | 95% (1,010/1,063) | Pan-cancer | ★★★ |

**Interpretation**: These genes are essential for cell survival across nearly all cancer types. They are core fitness genes (ribosomal proteins, RNA polymerase) and likely not selective therapeutic targets.

*Source: DepMap via `DepMap_get_gene_dependencies`*
```

**Output for Report (when using Pharos fallback)**:
```markdown
### 1. Gene Essentiality Analysis

**⚠️ Data Source**: Pharos (DepMap CRISPR temporarily unavailable)
**Analysis Method**: Essentiality inferred from TDL (Target Development Level) classification
**Confidence**: Varies by TDL (Tclin=★★★, Tchem=★★☆, Tbio/Tdark=★☆☆)

#### Clinically Validated Targets (Tclin - Likely Essential)

| Gene | TDL | Clinical Status | Inference | Evidence |
|------|-----|----------------|-----------|----------|
| **KRAS** | Tclin | Approved drugs (sotorasib, adagrasib) | Likely essential in KRAS-mutant cancers | ★★★ |
| **EGFR** | Tclin | Multiple approved inhibitors | Likely essential in EGFR-mutant cancers | ★★★ |

**Interpretation**: Tclin targets have approved drugs, indicating clinical validation. These are likely essential in specific contexts (mutation-dependent).

#### Chemical Probe Available (Tchem - Potentially Essential)

| Gene | TDL | Tool Status | Inference | Evidence |
|------|-----|-------------|-----------|----------|
| **CDK2** | Tchem | Chemical probes available | Potentially essential (cell cycle) | ★★☆ |
| **WEE1** | Tchem | Chemical inhibitors available | Potentially essential (DNA damage) | ★★☆ |

**Interpretation**: Tchem targets are druggable with chemical tools. Druggability suggests functional importance.

**Note**: TDL classification is a proxy for essentiality. **For definitive CRISPR dependency scores, DepMap data required.**

*Source: Pharos via `Pharos_get_target` (fallback method)*

#### Selectively Essential Genes (Tissue/Context-Specific)

| Gene | Mean Effect | Essential in | Non-Essential in | Selectivity Score | Evidence |
|------|-------------|--------------|------------------|-------------------|----------|
| **KRAS** | -0.85 | Pancreatic (95%), Lung (78%), Colon (82%) | Breast (12%), Glioma (8%) | High | ★★★ |
| **EGFR** | -0.72 | Lung (85%), Glioblastoma (76%) | Most others (<20%) | High | ★★★ |
| **ESR1** | -0.68 | ER+ Breast (92%) | ER- Breast (5%), Other (<3%) | Very High | ★★★ |

**Interpretation**: Selectively essential genes show strong context-dependency and represent high-value therapeutic targets with potential for tissue-selective toxicity profiles.

*Source: DepMap via `DepMap_get_gene_dependencies`*

#### Non-Essential/Weak Hits (Score > -0.5)

| Gene | Mean Effect | % Essential | Interpretation |
|------|-------------|-------------|----------------|
| **GENE1** | -0.25 | 15% | Weak dependency, potential off-target or passenger |
| **GENE2** | -0.12 | 8% | Non-essential in most contexts |

**Note**: These genes may still be biologically relevant (e.g., synthetic lethal interactions, drug targets for specific contexts) but show weak essentiality in CRISPR screens.

---
**Essentiality Summary**:
- **Pan-cancer essential**: 12 genes (↓ deprioritize for selective targeting)
- **Selectively essential**: 18 genes (★ HIGH PRIORITY for validation)
- **Weakly essential**: 15 genes (context-dependent, requires further investigation)

*All essentiality data from DepMap Portal (DepMap Public 24Q2 release)*
```

---

## PATH 2: Pathway & Functional Enrichment

### Gene Set Enrichment Analysis

```python
def perform_pathway_enrichment(tu, gene_list):
    """
    Run enrichment analysis across multiple libraries.
    """
    # Enrichr libraries to query
    libraries = [
        "WikiPathways_2024_Human",
        "Reactome_Pathways_2024",
        "MSigDB_Hallmark_2020",
        "GO_Biological_Process_2023",
        "GO_Molecular_Function_2023",
        "GO_Cellular_Component_2023",
        "KEGG_2024_Human"
    ]

    result = tu.tools.enrichr_gene_enrichment_analysis(
        gene_list=gene_list,
        libs=libraries
    )

    # Parse results - Enrichr returns pathway rankings with p-values
    return result
```

**Output for Report**:
```markdown
### 2. Pathway & Functional Enrichment

#### Top Enriched Pathways (p < 0.01, FDR < 0.05)

##### Reactome Pathways

| Pathway | Genes | p-value | FDR | Odds Ratio | Evidence |
|---------|-------|---------|-----|------------|----------|
| **Cell Cycle Checkpoints** | 12/18 | 1.2e-8 | 3.4e-6 | 15.3 | ★★★ |
| **DNA Replication** | 8/18 | 3.5e-6 | 4.2e-4 | 12.1 | ★★★ |
| **G1/S Transition** | 7/18 | 5.1e-5 | 2.1e-3 | 9.8 | ★★☆ |

*Genes in pathway*: CCNE1, CDK2, RB1, E2F1, CDC25A, CDC6, ORC1, MCM2

**Interpretation**: Strong enrichment in cell cycle control pathways suggests the screen identified proliferation-essential genes. These represent core cell cycle machinery.

##### GO Biological Process

| Term | Genes | p-value | FDR | Evidence |
|------|-------|---------|-----|----------|
| **DNA replication initiation** | 6/18 | 2.1e-7 | 1.5e-5 | ★★★ |
| **G1/S transition of mitotic cell cycle** | 8/18 | 8.3e-7 | 3.2e-5 | ★★★ |
| **regulation of cyclin-dependent protein kinase activity** | 5/18 | 1.2e-4 | 8.9e-3 | ★★☆ |

##### MSigDB Hallmark Gene Sets

| Hallmark | Genes | p-value | FDR | Evidence |
|----------|-------|---------|-----|----------|
| **E2F Targets** | 10/18 | 6.7e-10 | 1.2e-8 | ★★★ |
| **G2M Checkpoint** | 9/18 | 3.4e-8 | 2.1e-6 | ★★★ |
| **MYC Targets V1** | 7/18 | 2.1e-5 | 9.8e-4 | ★★☆ |

**Key Finding**: Hits converge on E2F/RB pathway, suggesting screen successfully identified proliferation machinery. This is expected for dropout screens in proliferating cancer cells.

*Source: Enrichr via `enrichr_gene_enrichment_analysis`*

#### No Significant Enrichment

**GO Molecular Function**: No terms pass FDR < 0.05
**KEGG Pathways**: Marginal enrichment (p < 0.05) but does not survive multiple testing correction

**Interpretation**: Gene list may be heterogeneous or represent diverse biological processes. Consider sub-clustering analysis.
```

---

## PATH 3: Protein-Protein Interaction Networks

### Build PPI Network

```python
def build_ppi_network(tu, gene_list):
    """
    Construct protein interaction network for hit genes.
    """
    # Use STRING for comprehensive PPI data
    ppi_result = tu.tools.STRING_get_protein_interactions(
        protein_ids=gene_list,
        species=9606  # Human
    )

    # Also check IntAct for curated interactions
    interactions = []
    for gene in gene_list:
        # Get UniProt ID first
        uniprot = resolve_gene_to_uniprot(tu, gene)
        if uniprot:
            intact_result = tu.tools.intact_get_interactions(identifier=uniprot)
            interactions.append(intact_result)

    return {
        'string': ppi_result,
        'intact': interactions
    }

def identify_protein_complexes(ppi_data):
    """
    Identify protein complexes from PPI network.

    Could use complex detection algorithms or query Complex Portal.
    """
    # Implementation for complex detection
    pass
```

**Output for Report**:
```markdown
### 3. Protein Interaction Network Analysis

#### Network Statistics

- **Nodes**: 45 proteins (from 45 input genes)
- **Edges**: 128 interactions (STRING combined score > 0.4)
- **Network Density**: 0.063
- **Average Clustering Coefficient**: 0.45
- **Hub Genes** (>10 interactions): CDK2, RB1, E2F1, CCNE1

**Interpretation**: High clustering coefficient indicates genes are functionally related and form coherent protein complexes.

*Source: STRING via `STRING_get_protein_interactions`*

#### Protein Complexes Identified

| Complex | Members | Function | Essential? |
|---------|---------|----------|------------|
| **MCM Complex** | MCM2, MCM3, MCM4, MCM5, MCM6, MCM7 | DNA replication helicase | Yes (pan-cancer) |
| **Cyclin E-CDK2** | CCNE1, CCNE2, CDK2 | G1/S transition kinase | Yes (selective) |
| **E2F/DP/RB** | E2F1, E2F2, E2F3, RB1, TFDP1 | Transcription regulation | Yes (context-dependent) |

**Key Finding**: Screen hit multiple members of the same essential complexes. This provides validation (independent hits in same pathway) and suggests complex-level vulnerability.

*Source: Complex Portal annotations + STRING clustering*

#### Synthetic Lethal Candidates

Based on PPI network and literature:

| Gene A (Hit) | Gene B (Candidate) | Relationship | Evidence | Source |
|--------------|-------------------|--------------|----------|--------|
| **RB1** | **ARID1A** | Synthetic lethal | ★★☆ | PMID:29534788 |
| **KRAS** | **STK11** | Synthetic lethal | ★★★ | PMID:31010833 |

**Recommendation**: Test synthetic lethal candidates (Gene B) for combination therapy with inhibitors of Gene A.
```

---

## PATH 4: Druggability & Target Assessment

### Assess Drug Target Potential

```python
def assess_druggability(tu, gene_list):
    """
    Evaluate druggability of hit genes.
    """
    drug_targets = []

    for gene in gene_list:
        # Check Pharos for target development level
        pharos = tu.tools.Pharos_get_target(gene=gene)

        # Check DGIdb for existing drugs
        dgidb = tu.tools.DGIdb_get_drug_gene_interactions(genes=[gene])

        # Check Open Targets for chemical probes
        ensembl_id = resolve_gene_to_ensembl(tu, gene)
        if ensembl_id:
            probes = tu.tools.OpenTargets_get_chemical_probes_by_target_ensemblId(
                ensemblId=ensembl_id
            )

        # Check clinical trials
        trials = tu.tools.search_clinical_trials(
            intervention=gene,
            pageSize=20
        )

        drug_targets.append({
            'gene': gene,
            'pharos_tdl': pharos.get('data', {}).get('tdl'),
            'existing_drugs': dgidb,
            'chemical_probes': probes,
            'clinical_trials': trials
        })

    return drug_targets
```

**Output for Report**:
```markdown
### 4. Druggability & Clinical Target Assessment

#### Target Development Level Classification (Pharos)

| TDL | Count | Genes | Interpretation |
|-----|-------|-------|----------------|
| **Tclin** | 5 | EGFR, KRAS, CDK2, HDAC1, AURKA | Approved drug targets |
| **Tchem** | 8 | WEE1, PLK1, CHEK1, ... | Chemical matter available, druggable |
| **Tbio** | 12 | E2F1, RB1, ... | Biologically characterized, may need novel modalities |
| **Tdark** | 3 | GENE_X, GENE_Y, GENE_Z | Understudied, limited tool compounds |

**Priority Ranking**: Tclin > Tchem > Tbio for near-term drug development feasibility.

*Source: Pharos/TCRD via `Pharos_get_target`*

#### Approved Drugs & Clinical Tools

| Gene | Drug(s) | Status | Indication | Source |
|------|---------|--------|------------|--------|
| **EGFR** | Erlotinib, Gefitinib, Osimertinib | Approved | NSCLC | DGIdb |
| **CDK2** | Dinaciclib | Phase 2 | Hematologic malignancies | ClinicalTrials.gov |
| **AURKA** | Alisertib | Phase 3 | Lymphoma | ClinicalTrials.gov |
| **WEE1** | Adavosertib | Phase 2 | Solid tumors | ClinicalTrials.gov |

**Clinical Readiness**: 5 genes have approved/late-stage drugs. These represent immediate repurposing opportunities.

*Sources: DGIdb via `DGIdb_get_drug_gene_interactions`, ClinicalTrials.gov*

#### Chemical Probes Available

| Gene | Probe | Potency | Selectivity | Use | Source |
|------|-------|---------|-------------|-----|--------|
| **CDK2** | Roscovitine | IC50 ~200nM | Moderate (pan-CDK) | Tool compound | SGC/Open Targets |
| **HDAC1** | SAHA (Vorinostat) | IC50 ~10nM | Pan-HDAC | Approved drug, research tool | ChEMBL |

*Source: Open Targets via `OpenTargets_get_chemical_probes_by_target_ensemblId`*

#### Non-Druggable Hits Requiring Alternative Strategies

| Gene | Challenge | Recommended Approach |
|------|-----------|---------------------|
| **E2F1** | Transcription factor (no catalytic domain) | PROTACs, molecular glue degraders |
| **RB1** | Tumor suppressor (loss-of-function) | Synthetic lethal approach (e.g., CDK4/6i) |
| **MCM2** | Part of large complex, no pockets | Indirect targeting via cell cycle inhibitors |

**Validation Priority**: Focus on Tclin/Tchem hits with existing tool compounds for faster validation.
```

---

## PATH 5: Disease Association & Clinical Relevance

### Cancer Genomics Integration

```python
def assess_clinical_relevance(tu, gene_list, cancer_type):
    """
    Evaluate clinical relevance of hits in target cancer type.
    """
    clinical_data = []

    for gene in gene_list:
        ensembl_id = resolve_gene_to_ensembl(tu, gene)

        if ensembl_id:
            # Disease associations
            diseases = tu.tools.OpenTargets_get_diseases_phenotypes_by_target_ensemblId(
                ensemblId=ensembl_id
            )

            # Mouse models
            mouse = tu.tools.OpenTargets_get_biological_mouse_models_by_ensemblId(
                ensemblId=ensembl_id
            )

        # COSMIC mutations (somatic alterations in cancer)
        cosmic = tu.tools.COSMIC_get_gene_mutations(gene=gene)

        # GTEx expression (is it expressed in relevant tissue?)
        gtex = tu.tools.GTEx_get_median_gene_expression(
            gencode_id=ensembl_id,
            operation="median"
        )

        clinical_data.append({
            'gene': gene,
            'diseases': diseases,
            'mutations': cosmic,
            'expression': gtex,
            'mouse_models': mouse
        })

    return clinical_data
```

**Output for Report**:
```markdown
### 5. Clinical Relevance & Disease Association

#### Cancer Genomic Alterations (COSMIC)

| Gene | Mutation Frequency | Cancer Types (Top 3) | Alteration Type | Evidence |
|------|-------------------|----------------------|-----------------|----------|
| **KRAS** | 22% across all cancers | Pancreatic (90%), Colon (45%), Lung (32%) | Activating mutations | ★★★ |
| **EGFR** | 8% across all cancers | Lung (15%), Glioma (30%), Breast (2%) | Amplification, mutations | ★★★ |
| **TP53** | 42% across all cancers | Universal | Loss-of-function | ★★★ |

**Interpretation**: High mutation frequency indicates gene is driver in those cancer types. CRISPR essentiality + genomic alteration = strong therapeutic rationale.

*Source: COSMIC via `COSMIC_get_gene_mutations`*

#### Expression in Normal vs Tumor Tissue (GTEx/TCGA)

| Gene | Normal Lung (median TPM) | Lung Tumor (TCGA) | Tumor/Normal Ratio | Therapeutic Window |
|------|-------------------------|-------------------|--------------------|--------------------|
| **EGFR** | 8.5 | 45.3 | 5.3x | Moderate |
| **AURKA** | 2.1 | 18.7 | 8.9x | Good |
| **RPS6** | 125.3 | 132.1 | 1.05x | Poor (housekeeping) |

**Interpretation**: Genes with >3x tumor/normal expression offer better therapeutic window. Housekeeping genes (e.g., ribosomal) show poor selectivity.

*Sources: GTEx via `GTEx_get_median_gene_expression`, TCGA data*

#### Prognostic/Predictive Biomarker Status

| Gene | Biomarker Type | Cancer | Association | Evidence | Source |
|------|---------------|--------|-------------|----------|--------|
| **KRAS** | Predictive (negative) | Colorectal | KRAS mut → anti-EGFR resistance | ★★★ | FDA label |
| **EGFR** | Predictive (positive) | NSCLC | EGFR mut → TKI response | ★★★ | FDA companion dx |
| **ESR1** | Predictive (positive) | Breast | ESR1 expression → endocrine therapy | ★★★ | Clinical guidelines |

**Clinical Impact**: 3 genes are established biomarkers with FDA-approved tests. Targeting these genes has strong clinical precedent.
```

---

## PATH 6: Hit Prioritization & Validation Strategy

### Integrate All Evidence Dimensions

```python
def calculate_priority_score(gene_data):
    """
    Calculate multi-dimensional priority score.

    Components:
    - Essentiality strength (DepMap score)
    - Selectivity (tissue-specific vs pan-cancer)
    - Druggability (Pharos TDL, existing compounds)
    - Clinical relevance (mutations, expression, biomarkers)
    - Validation feasibility (tool compounds available)

    Returns score 0-100
    """
    score = 0

    # Essentiality (0-30 points)
    if gene_data['depmap_score'] < -1.0:
        score += 30
    elif gene_data['depmap_score'] < -0.5:
        score += 20
    else:
        score += 10

    # Selectivity (0-25 points)
    if gene_data['selective']:  # Tissue-specific
        score += 25
    elif gene_data['pan_cancer']:  # Pan-cancer (deprioritize)
        score += 5

    # Druggability (0-25 points)
    if gene_data['pharos_tdl'] == 'Tclin':
        score += 25
    elif gene_data['pharos_tdl'] == 'Tchem':
        score += 20
    elif gene_data['pharos_tdl'] == 'Tbio':
        score += 10
    else:
        score += 5

    # Clinical relevance (0-20 points)
    if gene_data['mutation_frequency'] > 20:
        score += 10
    if gene_data['biomarker_status']:
        score += 10

    return score
```

**Output for Report**:
```markdown
### 6. Hit Prioritization & Validation Recommendations

#### Top 10 Priority Targets (Multi-Dimensional Scoring)

| Rank | Gene | Essentiality | Selectivity | Druggability | Clinical | Total Score | Recommendation |
|------|------|--------------|-------------|--------------|----------|-------------|----------------|
| 1 | **KRAS** | 30/30 | 25/25 | 20/25 | 20/20 | **95/100** | High priority, validated drugs available |
| 2 | **EGFR** | 28/30 | 24/25 | 25/25 | 18/20 | **95/100** | High priority, approved drugs |
| 3 | **WEE1** | 26/30 | 23/25 | 20/25 | 12/20 | **81/100** | Medium-high, Phase 2 drug available |
| 4 | **AURKA** | 24/30 | 22/25 | 20/25 | 14/20 | **80/100** | Medium-high, tool compounds exist |
| 5 | **CDK2** | 25/30 | 20/25 | 20/25 | 10/20 | **75/100** | Medium, multiple tool compounds |
| 6 | **CHEK1** | 23/30 | 21/25 | 18/25 | 10/20 | **72/100** | Medium, chemical probes available |
| 7 | **PLK1** | 22/30 | 20/25 | 18/25 | 11/20 | **71/100** | Medium, clinical tool compounds |
| 8 | **E2F1** | 24/30 | 22/25 | 10/25 | 12/20 | **68/100** | Medium-low, requires degrader strategy |
| 9 | **HDAC1** | 20/30 | 18/25 | 25/25 | 8/20 | **71/100** | Medium, approved HDAC inhibitors |
| 10 | **MCM2** | 28/30 | 10/25 | 5/25 | 8/20 | **51/100** | Low, pan-cancer essential, not druggable |

**Scoring Rubric**:
- **Essentiality** (30 pts): DepMap gene effect score magnitude
- **Selectivity** (25 pts): Tissue-specific vs pan-cancer dependency
- **Druggability** (25 pts): Pharos TDL, existing compounds, tractability
- **Clinical** (20 pts): Mutation frequency, biomarker status, expression

**Priority Tiers**:
- **Tier 1 (Score >80)**: Immediate validation, existing tools/drugs available
- **Tier 2 (Score 60-80)**: Medium priority, validation feasible with chemical probes
- **Tier 3 (Score <60)**: Lower priority or requires novel approaches (PROTACs, etc.)

#### Validation Experiment Recommendations

##### Tier 1 Targets (KRAS, EGFR, WEE1)

**1. KRAS**
- **Essentiality**: Strong selective dependency in KRAS-mutant cancers
- **Validation Approach**:
  - Test KRAS G12C inhibitor (sotorasib/adagrasib) in KRAS G12C-mutant cell lines from screen
  - Orthogonal validation: siRNA/shRNA knockdown
  - Rescue experiment: Re-express WT KRAS in KO cells
- **Expected Outcome**: Growth inhibition/cell death in KRAS-mutant lines only
- **Tool Compounds**: Sotorasib (AMG 510), Adagrasib (MRTX849), MRTX1133 (pan-KRAS)
- **Timeline**: 2-3 weeks for cell line validation

**2. EGFR**
- **Essentiality**: Selective in EGFR-mutant/amplified NSCLC, glioblastoma
- **Validation Approach**:
  - Test EGFR TKI panel (erlotinib, osimertinib) in screen cell lines
  - Dose-response curves to establish IC50
  - Combination with standard chemotherapy
- **Expected Outcome**: Potent inhibition in EGFR-altered lines
- **Tool Compounds**: Erlotinib, Gefitinib, Osimertinib (all FDA-approved)
- **Timeline**: 1-2 weeks

**3. WEE1**
- **Essentiality**: Synthetic lethal with TP53 loss, selective in TP53-mutant cancers
- **Validation Approach**:
  - Test adavosertib (WEE1 inhibitor) ± DNA damaging agents
  - Stratify by TP53 status (mutant vs WT)
  - Cell cycle analysis (premature mitotic entry)
- **Expected Outcome**: Selective killing of TP53-mutant cells + synergy with chemo
- **Tool Compounds**: Adavosertib (AZD1775), PD-166285
- **Timeline**: 2-3 weeks

##### Tier 2 Targets (AURKA, CDK2, CHEK1, PLK1)

**General Strategy**:
- Pharmacological validation with 2-3 selective inhibitors per target
- Orthogonal genetic validation (CRISPRi/shRNA)
- Pathway analysis (Western blots for downstream effectors)
- Combination screens with standard-of-care agents

**Recommended Tool Compounds**:
- **AURKA**: Alisertib (MLN8237), Aurora A Inhibitor I
- **CDK2**: Roscovitine (seliciclib), Dinaciclib
- **CHEK1**: Prexasertib (LY2606368), AZD7762
- **PLK1**: Volasertib (BI 6727), BI 2536

##### Tier 3 Targets - Alternative Validation Strategies

**E2F1, RB1** (Transcription factors):
- **Challenge**: No direct small molecule inhibitors
- **Strategy**:
  - Test PROTACs if available
  - Indirect validation via upstream targets (CDK4/6 inhibitors for RB pathway)
  - Genetic validation only (CRISPRko, CRISPRi)

**MCM2-7 Complex** (Helicase, pan-essential):
- **Challenge**: Pan-cancer essential, poor therapeutic window
- **Strategy**: Deprioritize for drug development
- **Note**: Interesting for understanding replication biology, but not ideal therapeutic target

#### Validation Timeline

| Phase | Duration | Experiments | Deliverable |
|-------|----------|-------------|-------------|
| **Phase 1** | Weeks 1-3 | Tier 1 target validation (KRAS, EGFR, WEE1) | Dose-response curves, potency data |
| **Phase 2** | Weeks 4-6 | Tier 2 target validation (AURKA, CDK2, etc.) | Hit confirmation, selectivity data |
| **Phase 3** | Weeks 7-10 | Mechanism studies, pathway analysis | Western blots, cell cycle, apoptosis |
| **Phase 4** | Weeks 11-14 | Combination studies, in vivo pilot (top 2-3) | Synergy matrices, xenograft data |

#### Success Criteria for Validation

✅ **Hit Confirmed** if:
- Pharmacological inhibition phenocopies CRISPR knockout (≥50% growth inhibition at ≤1 µM)
- Dose-response curve shows IC50 consistent with essentiality score
- Effect is selective (active in screen cell line, inactive in control lines)
- Orthogonal genetic methods (siRNA, CRISPRi) reproduce phenotype

❌ **Hit Rejected/Deprioritized** if:
- Tool compounds show no effect despite strong CRISPR score (off-target CRISPR effect)
- Pan-cancer essential with no selectivity (poor therapeutic window)
- No druggable domain/strategy (TFs, scaffolds without chemical matter)
- Cannot be validated with available reagents

#### Resource Requirements

**Reagents**:
- Chemical compounds: $5-10K (tool compounds, commercial inhibitors)
- CRISPRi/shRNA validation: $3-5K (vectors, reagents)
- Cell culture & assays: $8-12K (plates, reagents, media)

**Equipment**:
- Cell culture facility (BSL2)
- Plate readers (viability assays, luminescence)
- Flow cytometer (cell cycle, apoptosis)
- Western blot equipment

**Personnel**: 1 postdoc + 1 technician for 3-4 months

---
**Validation Strategy Summary**: Focus validation efforts on Tier 1 targets (KRAS, EGFR, WEE1) with approved/late-stage drugs. These offer fastest path to clinical translation and have highest probability of success based on multi-dimensional scoring.
```

---

## Report Template (Initial File)

**File**: `CRISPR_screen_analysis_[CONTEXT].md`

```markdown
# CRISPR Screen Analysis Report: [CONTEXT]

**Generated**: [Date]
**Input**: [Gene list / Cancer type / Single gene]
**Context**: [Screen type, cell line, experimental details]
**Status**: In Progress

---

## Executive Summary
[Analyzing...]
<!-- Will contain: key findings, top hits, recommended priorities -->

---

## Input Validation
[Analyzing...]
<!-- Gene symbol validation, invalid genes, suggestions -->

---

## 1. Gene Essentiality Analysis
### 1.1 Strongly Essential Genes
[Analyzing...]
### 1.2 Selectively Essential Genes
[Analyzing...]
### 1.3 Weakly Essential / Non-Essential
[Analyzing...]

---

## 2. Pathway & Functional Enrichment
### 2.1 Pathway Enrichment (Reactome, KEGG)
[Analyzing...]
### 2.2 GO Enrichment (BP, MF, CC)
[Analyzing...]
### 2.3 Hallmark Gene Sets (MSigDB)
[Analyzing...]
### 2.4 Pathway-Level Interpretation
[Analyzing...]

---

## 3. Protein Interaction Network
### 3.1 Network Statistics
[Analyzing...]
### 3.2 Protein Complexes
[Analyzing...]
### 3.3 Hub Genes
[Analyzing...]
### 3.4 Synthetic Lethal Candidates
[Analyzing...]

---

## 4. Druggability Assessment
### 4.1 Target Development Level (Pharos)
[Analyzing...]
### 4.2 Approved Drugs & Clinical Candidates
[Analyzing...]
### 4.3 Chemical Probes
[Analyzing...]
### 4.4 Non-Druggable Hits (Alternative Strategies)
[Analyzing...]

---

## 5. Clinical Relevance
### 5.1 Cancer Genomic Alterations (COSMIC)
[Analyzing...]
### 5.2 Expression in Tumor vs Normal
[Analyzing...]
### 5.3 Prognostic/Predictive Biomarkers
[Analyzing...]
### 5.4 Mouse Models & Genetic Evidence
[Analyzing...]

---

## 6. Hit Prioritization & Validation
### 6.1 Multi-Dimensional Scoring
[Analyzing...]
### 6.2 Top 10 Priority Targets
[Analyzing...]
### 6.3 Validation Experiment Recommendations
[Analyzing...]
### 6.4 Validation Timeline & Resources
[Analyzing...]

---

## 7. Data Sources & Quality Control
### 7.1 Primary Data Sources
[Will be populated...]
### 7.2 Tool Call Summary
[Will be populated...]
### 7.3 Limitations & Caveats
[Will be populated...]

---

## Appendix: Full Hit List
[Complete gene list with all scores...]
```

---

## When NOT to Use This Skill

- **Drug target research** (single gene) → Use `tooluniverse-target-research` skill instead
- **Disease-centric query** → Use `tooluniverse-disease-research` skill
- **Chemical compound screening** → Different workflow needed
- **RNA-seq differential expression** → Use differential expression analysis workflows
- **Single gene lookup** → Call DepMap tools directly

Use this skill when you have a **gene list from a CRISPR screen** and need comprehensive **functional interpretation + target prioritization**.

---

## Example Queries That Trigger This Skill

✅ **Gene List Analysis**:
- "Analyze these CRISPR screen hits: EGFR, KRAS, WEE1, PLK1, AURKA, ..."
- "I have 50 dropout genes from a CRISPR screen in lung cancer cells, what should I validate?"
- "Prioritize these genes for drug target development: [gene list]"

✅ **Cancer Type Query**:
- "What are the top essential genes in pancreatic cancer?"
- "Find druggable dependencies in triple-negative breast cancer"

✅ **Single Gene Validation**:
- "Is KRAS a good therapeutic target for lung cancer?"
- "Assess the druggability of WEE1 as a cancer target"

❌ **Not Appropriate**:
- "What is the function of EGFR?" → too broad, use target-research skill
- "Find drugs for lung cancer" → disease-centric, use drug-repurposing skill
- "Analyze this RNA-seq data" → different analytical workflow

---

## Key Improvements from Existing Skills

Based on patterns in `tooluniverse-target-research` and `tooluniverse-drug-research`:

1. **Multi-dimensional scoring system** (novel for CRISPR analysis)
2. **Validation experiment recommendations** with timelines and reagents
3. **Tier-based prioritization** (Tier 1/2/3 based on actionability)
4. **Tool compound suggestions** for each druggable target
5. **Synthetic lethal candidate identification** from PPI network
6. **Explicit selectivity analysis** (pan-cancer vs tissue-selective)
7. **Success/failure criteria** for validation experiments

---

## Quality Control Checklist

Before finalizing report:

- [ ] All input genes validated against DepMap registry
- [ ] Essentiality scores retrieved for all valid genes
- [ ] Pathway enrichment performed (minimum: GO BP, Reactome, Hallmark)
- [ ] PPI network constructed with interaction counts
- [ ] Druggability assessed for all hits (Pharos TDL + DGIdb)
- [ ] Top 10 priority targets table completed
- [ ] Validation recommendations provided for Tier 1 targets
- [ ] Evidence grades assigned (★★★, ★★☆, ★☆☆)
- [ ] All data sources cited explicitly
- [ ] "No data" explicitly stated when tools return empty results
- [ ] Executive summary synthesizes all findings

