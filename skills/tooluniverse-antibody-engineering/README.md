# Antibody Engineering & Optimization

Comprehensive antibody optimization skill for therapeutic development. From mouse antibody to clinical candidate in one workflow.

## Quick Start

### Basic Usage

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Example 1: Humanize a mouse antibody
result = tu.chat("""
Humanize this mouse anti-PD-L1 antibody:

VH: EVQLVESGGGLVQPGGSLRLSCAASGYTFTSYYMHWVRQAPGKGLEWVSGIIPIFGTANYAQKFQGRVTISADTSKNTAYLQMNSLRAEDTAVYYCARDDGSYSPFDYWGQGTLVTVSS

VL: DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKLLIYAASSLQSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQSYSTPLTFGQGTKVEIK

Target: PD-L1 (Q9NZQ7)
""")
```

**Output**: Humanized sequences with 85-90% human framework, CDR preservation, developability assessment, and recommendations.

---

## What This Skill Does

### Core Capabilities

1. **Humanization** (Example 1)
   - Identify germline genes (IMGT)
   - Design CDR grafting strategy
   - Identify backmutations for CDR support
   - Predict affinity retention

2. **Affinity Maturation** (Example 2)
   - Analyze binding interface
   - Design affinity-improving mutations
   - In silico screening for optimal variants
   - Balance affinity vs. developability

3. **Developability Assessment** (Example 3)
   - Identify aggregation-prone regions
   - Detect PTM liability sites
   - Predict stability and expression
   - Calculate comprehensive developability score (0-100)

4. **Immunogenicity Prediction** (Example 6)
   - Predict T-cell epitopes (IEDB)
   - Calculate immunogenicity risk score
   - Design deimmunization strategy
   - Compare to clinical precedents

5. **Manufacturing Assessment** (Example 7)
   - Expression optimization (CHO cells)
   - Purification strategy design
   - Formulation recommendations
   - CMC timeline and cost estimates

6. **Advanced Engineering**
   - Bispecific antibodies (Example 4)
   - pH-dependent binding (Example 5)
   - Aggregation mitigation (Example 3)
   - CDR optimization strategies

---

## Key Features

### Report-First Approach
Creates `antibody_optimization_report.md` with progressive updates throughout analysis.

### Comprehensive Scoring
- **Humanization Score**: % framework identity to human germline
- **Developability Score**: 0-100 combining aggregation, PTM, stability, expression
- **Immunogenicity Risk**: Low/Medium/High based on T-cell epitopes
- **Evidence Grading**: T1-T4 tiers for variant ranking

### Evidence-Based Design
- Uses IMGT germline database for humanization
- Benchmarks against approved antibodies (TheraSAbDab)
- Validates with clinical precedents
- Structural modeling (AlphaFold)

---

## Input Requirements

### Minimum Input
```
- Antibody sequence (VH and/or VL)
- Target antigen (UniProt ID or name)
- Optimization goal (humanization, affinity, developability)
```

### Optional Input
```
- Current affinity (KD)
- Known issues (aggregation, immunogenicity)
- Species (if not mouse)
- Epitope information
- Clinical development stage
```

---

## Output Files

### 1. Main Report
**File**: `antibody_optimization_report.md`

Contains:
- Input characterization
- Humanization strategy (if applicable)
- Structure modeling & analysis
- Affinity optimization (if requested)
- Developability assessment
- Immunogenicity prediction
- Manufacturing feasibility
- Final recommendations

### 2. Sequence Files
**File**: `optimized_sequences.fasta`

All designed variants in FASTA format with annotations:
```fasta
>VH_Humanized_v2 | 85% human | KD=2.1nM | Dev=79/100
EVQLVQSGAEVKKPGASVKVSCKASGYAFTSYYMHWVRQAPGQGLEWMV...
```

### 3. Comparison Tables
**File**: `humanization_comparison.csv` or `developability_assessment.csv`

Detailed metrics for all variants.

---

## Common Use Cases

### Use Case 1: Mouse to Human (Humanization)

**Query**: "Humanize this mouse antibody"

**Process**:
1. CDR annotation (IMGT numbering)
2. Germline gene search (IMGT)
3. Framework selection (identity + clinical use)
4. CDR grafting design
5. Backmutation analysis
6. Structure validation (AlphaFold)
7. Developability scoring

**Output**: 2-3 humanized variants (85-90% human) with recommendations

**Timeline**: ~30 minutes for full analysis

---

### Use Case 2: Affinity Improvement

**Query**: "Improve affinity from 15 nM to <5 nM"

**Process**:
1. Interface analysis
2. Hotspot identification
3. In silico mutation screening
4. Combination variant design
5. Developability impact assessment
6. Testing strategy

**Output**: 5-10 affinity variants ranked by predicted improvement

**Timeline**: ~20 minutes for full analysis

---

### Use Case 3: Aggregation Reduction

**Query**: "This antibody aggregates at >50 mg/mL. Fix it."

**Process**:
1. Aggregation-prone region (APR) identification
2. Hydrophobic patch analysis
3. Charge distribution assessment
4. Mutation design (disrupt APRs)
5. Formulation recommendations
6. Validation plan

**Output**: 3-5 aggregation-mitigated variants with predicted max concentration

**Timeline**: ~25 minutes for full analysis

---

### Use Case 4: Complete Optimization Pipeline

**Query**: "Take this mouse antibody to clinical candidate"

**Process** (all phases):
1. Humanization (Phase 2)
2. Structure modeling (Phase 3)
3. Affinity optimization (Phase 4)
4. Developability assessment (Phase 5)
5. Immunogenicity prediction (Phase 6)
6. Manufacturing assessment (Phase 7)

**Output**: Comprehensive 1000+ line report with top candidate recommendation

**Timeline**: ~45-60 minutes for full pipeline

---

## Tool Dependencies

### Required Tools

| Tool Category | Tools Used | Purpose |
|--------------|------------|---------|
| **Immunogenetics** | IMGT_search_genes, IMGT_get_sequence | Germline identification |
| **Antibody Databases** | SAbDab, TheraSAbDab | Structural & clinical precedents |
| **Structure** | AlphaFold_get_prediction | Structure modeling |
| **Immunogenicity** | iedb_search_epitopes, iedb_search_bcell | Epitope prediction |
| **Target Info** | UniProt_get_protein_by_accession | Target characterization |
| **Literature** | PubMed_search | Clinical precedents |

### Optional Tools
- STRING (for bispecifics - protein interaction networks)
- EMDB (if target has cryo-EM structures)
- PDB (for experimental structures)

---

## Validation & Quality Control

### Automatic Checks

1. **CDR Preservation**: Warns if humanization changes CDR sequences
2. **Vernier Zone**: Identifies residues affecting CDR conformation
3. **PTM Sites**: Flags deamidation (NG, NS), isomerization (DG, DS), oxidation (M, W)
4. **Aggregation**: TANGO scores, hydrophobic patches
5. **pI Range**: Checks for extreme values (<4 or >10)
6. **Canonical Classes**: Validates CDR conformations

### Evidence Grading

| Tier | Criteria | Recommendation |
|------|----------|----------------|
| **T1** | Humanness >85%, Dev score >75, Low immunogenicity | Advance to development |
| **T2** | Humanness 70-85%, Dev score 60-75, Medium immunogenicity | Acceptable, monitoring needed |
| **T3** | Humanness <70%, Dev score <60, or High immunogenicity | Requires optimization |
| **T4** | Failed validation or major liabilities | Do not advance |

---

## Best Practices

### 1. Start with Complete Information
Provide as much context as possible:
- Current affinity (if known)
- Known issues (aggregation, immunogenicity, stability)
- Development stage (discovery, preclinical, clinical)
- Target indication and therapeutic modality

### 2. Review Recommendations Carefully
The skill provides computational predictions. Always:
- Validate top candidates experimentally
- Test multiple variants (don't rely on single prediction)
- Consider backup options
- Monitor for unexpected issues

### 3. Iterative Optimization
Use results to guide next steps:
- If humanization reduces affinity → Test backmutations
- If aggregation persists → Try alternative formulations
- If immunogenicity high → Apply deimmunization strategy

### 4. Balance Metrics
Optimal candidate balances multiple factors:
- Affinity (target: <10 nM for most applications)
- Humanization (target: >85% for low immunogenicity)
- Developability (target: >75 for clinical success)
- Manufacturing (target: Expression >1 g/L, formulation >100 mg/mL)

---

## Limitations

### 1. Computational Predictions
- Affinity predictions: ±2-3x accuracy
- Structure predictions: CDR-H3 may have lower confidence
- Aggregation: In silico scores are estimates (require validation)

### 2. Experimental Validation Required
Always validate computationally designed variants:
- Binding affinity (SPR, BLI)
- Expression and stability
- Functional activity
- In vivo PK (for final candidate)

### 3. Species Considerations
- Primarily optimized for human therapeutics
- Mouse → Human humanization most common
- Other species may require custom germline databases

### 4. Complex Formats
- Bispecifics require additional manufacturing development
- Non-IgG formats (scFv, Fab) have different considerations
- Antibody-drug conjugates (ADCs) need separate conjugation site engineering

---

## Troubleshooting

### Issue 1: Low Humanization Score (<80%)
**Solutions**:
- Try alternative germline frameworks
- Accept lower score if affinity critical (clinical monitoring)
- Consider fully human antibody (phage display, transgenic mice)

### Issue 2: Affinity Loss After Humanization
**Solutions**:
- Introduce backmutations at Vernier zone positions
- Test multiple humanization versions
- Combine humanization with affinity maturation

### Issue 3: High Aggregation Risk
**Solutions**:
- Apply aggregation mitigation mutations (disrupt APRs)
- Optimize formulation (pH, excipients, concentration)
- Consider alternative framework (lower pI)

### Issue 4: Immunogenicity Concerns
**Solutions**:
- Apply deimmunization (remove T-cell epitopes)
- Increase humanization level
- Consider fully human framework

---

## References & Resources

### Key Databases
- **IMGT**: http://www.imgt.org/ (germline genes, numbering)
- **SAbDab**: http://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/ (antibody structures)
- **TheraSAbDab**: http://opig.stats.ox.ac.uk/webapps/newsabdab/ (therapeutic antibodies)
- **IEDB**: http://www.iedb.org/ (epitope database)

### Recommended Reading
- Antibody humanization: Almagro & Fransson, Front. Biosci. 2008
- CDR grafting: Queen et al., PNAS 1989
- Developability: Jain et al., mAbs 2017
- pH-dependent binding: Igawa et al., Nat. Biotechnol. 2010

### Clinical Precedents
- Use TheraSAbDab to search approved antibodies
- >100 approved therapeutic antibodies as of 2026
- Most use IGHV1-69, IGHV3-23, IGKV1-39 germlines

---

## Example Queries

### Simple Queries

```
"Humanize this mouse anti-PD-L1 antibody"

"Improve affinity of this antibody to <5 nM"

"Assess developability of this sequence"

"Reduce aggregation in this antibody"

"Predict immunogenicity risk"
```

### Advanced Queries

```
"Humanize this mouse antibody, optimize affinity, and assess developability"

"Design a bispecific antibody targeting PD-L1 and TIM-3"

"Engineer pH-dependent binding into this anti-HER2 antibody for improved PK"

"Take this mouse antibody through complete optimization to clinical candidate"
```

### Specific Goals

```
"Humanize to >85% while maintaining affinity within 2x"

"Reduce aggregation to enable >150 mg/mL formulation"

"Improve affinity from 15 nM to <5 nM without compromising developability"

"Deimmunize this humanized antibody to reduce T-cell epitopes"
```

---

## Support

For issues, questions, or feature requests:
1. Check EXAMPLES.md for detailed use cases
2. Review SKILL.md for complete workflow documentation
3. Consult ToolUniverse documentation for tool-specific questions

---

## Version History

- **v1.0** (2026-02-09): Initial release
  - Humanization pipeline
  - Affinity maturation
  - Developability assessment
  - Immunogenicity prediction
  - Manufacturing assessment
  - Bispecific antibody design
  - pH-dependent binding engineering

---

## License

This skill is part of the ToolUniverse project. See main repository for license information.
