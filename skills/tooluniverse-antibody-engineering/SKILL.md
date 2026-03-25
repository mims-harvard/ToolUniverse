---
name: tooluniverse-antibody-engineering
description: Comprehensive antibody engineering and optimization for therapeutic development. Covers humanization, affinity maturation, developability assessment, and immunogenicity prediction. Use when asked to optimize antibodies, humanize sequences, or engineer therapeutic antibodies from lead to clinical candidate.
---

# Antibody Engineering & Optimization

AI-guided antibody optimization pipeline from preclinical lead to clinical candidate. Covers sequence humanization, structure modeling, affinity optimization, developability assessment, immunogenicity prediction, and manufacturing feasibility.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create optimization report before analysis
2. **Evidence-graded humanization** - Score based on germline alignment and framework retention
3. **Developability-focused** - Assess aggregation, stability, PTMs, immunogenicity
4. **Structure-guided** - Use AlphaFold/PDB structures for CDR analysis
5. **Clinical precedent** - Reference approved antibodies for validation
6. **Quantitative scoring** - Developability score (0-100) combining multiple factors
7. **English-first queries** - Always use English terms in tool calls, even if user writes in another language. Respond in user's language

---

## When to Use

Apply when user asks:
- "Humanize this mouse antibody sequence"
- "Optimize antibody affinity for [target]"
- "Assess developability of this antibody"
- "Predict immunogenicity risk for [sequence]"
- "Engineer bispecific antibody against [targets]"
- "Reduce aggregation in antibody formulation"
- "Design pH-dependent binding antibody"
- "Analyze CDR sequences and suggest mutations"

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

1. **Create the report file FIRST**: `antibody_optimization_report.md`
2. **Progressively update** as analysis completes
3. **Output separate files**:
   - `optimized_sequences.fasta` - All optimized variants
   - `humanization_comparison.csv` - Before/after comparison
   - `developability_assessment.csv` - Detailed scores

See `REPORT_TEMPLATE.md` for the full report template with section formats.

### 2. Documentation Standards (MANDATORY)

Every optimization MUST include per-variant documentation with:
- Original and optimized sequences
- Humanization score (% human framework)
- CDR preservation confirmation
- Metrics table (humanness, aggregation risk, predicted KD, immunogenicity)
- Data source citations

---

## Phase 0: Tool Verification

### Required Tools

| Tool | Purpose | Category |
|------|---------|----------|
| `IMGT_search_genes` | Germline gene identification | Humanization |
| `IMGT_get_sequence` | Human framework sequences | Humanization |
| `SAbDab_search_structures` | Antibody structure precedents | Structure |
| `TheraSAbDab_search_by_target` | Clinical antibody benchmarks | Validation |
| `alphafold_get_prediction` | Structure modeling | Structure |
| `iedb_search_epitopes` | Epitope identification | Immunogenicity |
| `iedb_search_bcell` | B-cell epitope prediction | Immunogenicity |
| `UniProt_get_entry_by_accession` | Target antigen information | Target |
| `STRING_get_interactions` | Protein interaction network | Bispecifics |
| `PubMed_search_articles` | Literature precedents | Validation |

**CRITICAL**: SOAP tools (IMGT, SAbDab, TheraSAbDab) require an `operation` parameter. See `QUICK_START.md` for correct usage.

---

## Workflow Overview

```
Phase 1: Input Analysis & Characterization
├── Sequence annotation (CDRs, framework)
├── Species identification
├── Target antigen identification
├── Clinical precedent search
└── OUTPUT: Input characterization
    ↓
Phase 2: Humanization Strategy
├── Germline gene alignment (IMGT)
├── Framework selection
├── CDR grafting design
├── Backmutation identification
└── OUTPUT: Humanization plan
    ↓
Phase 3: Structure Modeling & Analysis
├── AlphaFold prediction
├── CDR conformation analysis
├── Epitope mapping
├── Interface analysis
└── OUTPUT: Structural assessment
    ↓
Phase 4: Affinity Optimization
├── In silico mutation screening
├── CDR optimization strategies
├── Interface improvement
└── OUTPUT: Affinity variants
    ↓
Phase 5: Developability Assessment
├── Aggregation propensity
├── PTM site identification
├── Stability prediction
├── Expression prediction
└── OUTPUT: Developability score
    ↓
Phase 6: Immunogenicity Prediction
├── MHC-II epitope prediction (IEDB)
├── T-cell epitope risk
├── Aggregation-related immunogenicity
└── OUTPUT: Immunogenicity risk score
    ↓
Phase 7: Manufacturing Feasibility
├── Expression level prediction
├── Purification considerations
├── Formulation stability
└── OUTPUT: Manufacturing assessment
    ↓
Phase 8: Final Report & Recommendations
├── Ranked variant list
├── Experimental validation plan
├── Next steps
└── OUTPUT: Comprehensive report
```

---

## Phase 1: Input Analysis & Characterization

**Goal**: Annotate sequences, identify species/germline, find clinical precedents.

**Key steps**:
1. Annotate CDRs using IMGT numbering (CDR-H1: 27-38, CDR-H2: 56-65, CDR-H3: 105-117)
2. Identify closest human germline genes via `IMGT_search_genes`
3. Search clinical precedents via `TheraSAbDab_search_by_target`
4. Get target antigen info via `UniProt_get_entry_by_accession`

**Output**: Sequence information table, CDR annotation, target info, clinical precedent list.

See `WORKFLOW_DETAILS.md` Phase 1 for code examples.

---

## Phase 2: Humanization Strategy

**Goal**: Select human framework, design CDR grafting, identify backmutations.

**Key steps**:
1. Search IMGT for IGHV/IGKV human germline genes
2. Score candidate frameworks by identity, CDR compatibility, and clinical use
3. Design CDR grafting onto selected framework
4. Identify Vernier zone residues that may need backmutation (positions 2, 27-30, 47-48, 67, 69, 71, 78, 93-94)
5. Generate at least 2 variants: full humanization and with key backmutations
6. Calculate humanization score (framework humanness, CDR preservation, T-cell epitopes, aggregation risk)

**Output**: Framework selection rationale, grafting design, backmutation analysis, humanized sequences.

See `WORKFLOW_DETAILS.md` Phase 2 for code examples.

---

## Phase 3: Structure Modeling & Analysis

**Goal**: Predict structure, analyze CDR conformations, map epitope.

**Key steps**:
1. Predict Fv structure via `alphafold_get_prediction` (VH:VL)
2. Assess pLDDT scores by region (framework, CDRs, interface)
3. Classify CDR canonical structures and calculate RMSD
4. Search known epitopes via `iedb_search_epitopes`
5. Compare with clinical antibody structures via `SAbDab_search_structures`

**Output**: Structure quality table, CDR conformation analysis, epitope mapping, structural comparison.

See `WORKFLOW_DETAILS.md` Phase 3 for code examples.

---

## Phase 4: Affinity Optimization

**Goal**: Design affinity-improving mutations via computational screening.

**Key steps**:
1. Identify interface residues (distance cutoff 4.5 A)
2. Screen all amino acid substitutions at CDR interface positions
3. Rank by predicted binding energy change (ddG < -0.5 kcal/mol = favorable)
4. Design combination strategy: single -> double -> triple mutants
5. Consider CDR-H3 extension, tyrosine enrichment, salt bridge formation
6. Optional: pH-dependent binding via histidine substitutions

**Output**: Ranked mutation list, combination strategy, expected affinity improvements.

See `WORKFLOW_DETAILS.md` Phase 4 for code examples.

---

## Phase 5: Developability Assessment

**Goal**: Comprehensive developability scoring (0-100) across five dimensions.

**Key steps**:
1. **Aggregation**: Find aggregation-prone regions, calculate TANGO/AGGRESCAN scores, assess pI
2. **PTM liability**: Scan for deamidation (NG/NS), isomerization (DG/DS), oxidation (Met/Trp), N-glycosylation (N-X-S/T)
3. **Stability**: Predict thermal stability (Tm target >70C, Tonset >65C)
4. **Expression**: Predict CHO titer and soluble fraction
5. **Solubility**: Predict maximum formulation concentration

**Scoring**: Weighted average (aggregation 0.30, PTM 0.25, stability 0.20, expression 0.15, solubility 0.10).
Tiers: T1 (>75), T2 (60-75), T3 (<60).

**Output**: Component scores, overall score, tier classification, mitigation recommendations.

See `WORKFLOW_DETAILS.md` Phase 5 and `CHECKLISTS.md` for scoring details.

---

## Phase 6: Immunogenicity Prediction

**Goal**: Predict immunogenicity risk and design deimmunization strategy.

**Key steps**:
1. Scan 9-mer peptides against IEDB for MHC-II binding epitopes
2. Count non-human residues in framework regions
3. Assess aggregation-related immunogenicity
4. Calculate total risk score (0-100, lower is better): Low <30, Medium 30-60, High >60
5. Propose deimmunization mutations (remove T-cell epitopes while preserving CDRs)
6. Compare with clinical precedent ADA rates

**Output**: T-cell epitope list, risk score breakdown, deimmunization strategy, clinical comparison.

See `WORKFLOW_DETAILS.md` Phase 6 for code examples.

---

## Phase 7: Manufacturing Feasibility

**Goal**: Assess expression, purification, formulation, and CMC feasibility.

**Key steps**:
1. Assess codon optimization for CHO, identify rare codons
2. Design signal peptide
3. Plan 3-step purification: Protein A capture -> cation exchange polishing -> viral nanofiltration
4. Recommend formulation (buffer, pH, stabilizer, tonicity)
5. Define analytical characterization panel (SEC-MALS, CEX, CE-SDS, SPR, DSF)
6. Estimate CMC timeline and costs (typically 18-24 months, $1.65-2.65M to IND)

**Output**: Expression assessment, purification strategy, formulation recommendation, CMC timeline.

See `MANUFACTURING.md` for detailed manufacturing content and `WORKFLOW_DETAILS.md` Phase 7 for code.

---

## Phase 8: Final Report & Recommendations

**Goal**: Compile all findings into a ranked recommendation with validation plan.

**Key outputs**:
1. **Top candidate** with key metrics (humanness, affinity, developability, immunogenicity, stability, expression)
2. **Key improvements** table comparing original vs. optimized
3. **Experimental validation plan**: In vitro (3-4 months) -> Lead optimization (2-3 months) -> Preclinical (6-12 months)
4. **Backup variants** with profiles and recommendations
5. **IP considerations**: FTO analysis, CDR novelty, patentability
6. **Next steps**: Immediate (month 1-3), short-term (4-6), long-term (7-24)

See `REPORT_TEMPLATE.md` for the full report template.

---

## Tool Reference

### IMGT Tools
- `IMGT_search_genes`: Search germline genes (IGHV, IGKV, etc.)
- `IMGT_get_sequence`: Get germline sequences
- `IMGT_get_gene_info`: Database information

### Antibody Databases
- `SAbDab_search_structures`: Search antibody structures
- `SAbDab_get_structure`: Get structure details
- `TheraSAbDab_search_therapeutics`: Search by name
- `TheraSAbDab_search_by_target`: Search by target antigen

### Immunogenicity
- `iedb_search_epitopes`: Search epitopes
- `iedb_search_bcell`: B-cell epitopes
- `iedb_search_mhc`: MHC-II epitopes
- `iedb_get_epitope_references`: Citations

### Structure & Target
- `alphafold_get_prediction`: Structure prediction
- `UniProt_get_entry_by_accession`: Target info
- `PDB_get_structure`: Experimental structures

### Systems Biology (for Bispecifics)
- `STRING_get_interactions`: Protein interactions
- `STRING_get_enrichment`: Pathway analysis

---

## Reference Files

| File | Contents |
|------|----------|
| `QUICK_START.md` | Getting started guide, SOAP tool parameters, Python SDK and MCP usage |
| `WORKFLOW_DETAILS.md` | Code examples for all 8 phases |
| `REPORT_TEMPLATE.md` | Full report template with section formats and example tables |
| `MANUFACTURING.md` | Detailed manufacturing content (expression, purification, formulation, CMC) |
| `EXAMPLES.md` | Complete clinical scenario examples (humanization, affinity, bispecific) |
| `CHECKLISTS.md` | Evidence grading, completeness checklists, scoring details, special considerations |
