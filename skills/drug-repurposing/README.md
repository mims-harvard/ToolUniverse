# Drug Repurposing Skill

Systematic drug repurposing using ToolUniverse - find new therapeutic uses for existing drugs.

## What This Skill Does

This skill enables you to identify, evaluate, and rank drug repurposing candidates using computational approaches. It leverages 750+ scientific tools from ToolUniverse to analyze:

- Disease-target associations
- Drug-target interactions  
- Safety profiles
- Literature evidence
- Clinical trial data
- Chemical properties
- ADMET predictions

## When to Use This Skill

Use this skill when you need to:

- Find repurposing candidates for a specific disease
- Identify new indications for an approved drug
- Evaluate repurposing feasibility
- Assess safety for new indications
- Mine literature for repurposing evidence
- Rank multiple candidates systematically

**Trigger phrases**: "drug repurposing", "drug repositioning", "new indications", "off-label uses", "repurpose drug for", "find drugs for [disease]"

## Quick Start

### Target-Based Repurposing
Start with disease → Find targets → Match to drugs

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse(use_cache=True)
tu.load_tools()

# Find drugs for Alzheimer's disease
disease_info = tu.tools.OpenTargets_get_disease_id_description_by_name(
    diseaseName="Alzheimer's disease"
)

targets = tu.tools.OpenTargets_get_associated_targets_by_disease_efoId(
    efoId=disease_info['data']['id'],
    limit=10
)

for target in targets['data'][:3]:
    drugs = tu.tools.DGIdb_get_drug_gene_interactions(
        gene_name=target['gene_symbol']
    )
    # Evaluate candidates...
```

### Compound-Based Repurposing
Start with drug → Find targets → Match to diseases

```python
# Find new uses for metformin
drug_targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    drug_name_or_drugbank_id="metformin"
)

for target in drug_targets['data'][:5]:
    diseases = tu.tools.OpenTargets_get_diseases_by_target_ensemblId(
        ensemblId=target['ensembl_id']
    )
    # Check if new indication...
```

## Files in This Skill

- **SKILL.md** - Main skill instructions and workflows
- **EXAMPLES.md** - 7 complete worked examples
- **REFERENCE.md** - Detailed tool documentation
- **README.md** - This file

## Repurposing Strategies

This skill supports multiple approaches:

### 1. Target-Based
Disease → Targets → Drugs → Validation

**Best for**: Diseases with known molecular targets

### 2. Compound-Based  
Drug → Targets → Diseases → Validation

**Best for**: Finding new uses for approved drugs

### 3. Disease-Driven
Disease → Targets → Pathways → Drugs

**Best for**: Complex/polygenic diseases

### 4. Mechanism-Based
Known MOA → Similar MOA drugs → Evaluation

**Best for**: Mechanism-validated hypotheses

### 5. Network-Based
Pathway analysis → Pathway overlap → Candidate drugs

**Best for**: Systems biology approaches

### 6. Phenotype-Based
Adverse events → Therapeutic potential → Validation

**Best for**: Mining unexpected effects

### 7. Structure-Based
Active compound → Similar structures → Approved analogs

**Best for**: SAR-driven repurposing

## Key Features

### Comprehensive Data Integration
- **10+ databases**: DrugBank, ChEMBL, OpenTargets, PubChem, FDA, FAERS, PubMed, etc.
- **Multiple evidence types**: Genetic, chemical, clinical, literature
- **Cross-validation**: Verify across multiple sources

### Systematic Scoring
- Target association strength
- Safety profile assessment  
- Literature evidence quantification
- Drug-likeness evaluation
- Overall repurposing potential (0-100)

### Safety Assessment
- FDA warnings and precautions
- FAERS adverse event analysis
- Drug-drug interactions
- Risk stratification

### Evidence Mining
- PubMed literature search
- Clinical trial identification
- Mechanism validation
- Patent landscape

## Output Format

All analyses produce ranked candidate lists:

```markdown
## Top Repurposing Candidates

1. Drug Name (Score: 87/100)
   - Target: GENE (association: 0.85)
   - Status: FDA approved
   - Evidence: 23 papers, 4 trials
   - Safety: No black box warnings
   - Recommendation: Immediate Phase II planning

2. Drug Name (Score: 79/100)
   ...
```

## Examples Overview

The skill includes 7 comprehensive examples:

1. **Target-Based for Alzheimer's** - Complete workflow from disease to candidates
2. **Compound-Based for Metformin** - Finding new indications for approved drug
3. **Disease-Driven for COVID-19** - Emergency repurposing rapid screening
4. **Network-Based Pathway Analysis** - Using pathway overlap
5. **Structure-Based Repurposing** - Finding approved analogs
6. **Adverse Event Mining** - Converting AEs to therapeutic uses
7. **Multi-Database Integration** - Comprehensive scoring system

Each example is fully executable with ToolUniverse.

## Prerequisites

### Installation
```bash
pip install tooluniverse
```

### Optional Features
```bash
pip install tooluniverse[ml]  # For ADMET predictions
```

### Environment
```bash
export OPENAI_API_KEY="sk-..."  # For LLM-based tool search
export NCBI_API_KEY="..."       # For higher PubMed rate limits
```

## Performance Tips

1. **Enable caching**: `tu = ToolUniverse(use_cache=True)`
2. **Limit initial searches**: Start with top 10-20 results
3. **Use batch operations**: Parallel queries when possible
4. **Filter early**: Apply approval status filter first
5. **Validate top candidates**: Deep dive on highest scorers only

## Common Workflows

### Quick Screening (15 minutes)
1. Get disease targets (top 10)
2. Find drugs for each target
3. Filter to FDA approved
4. Rank by evidence count
5. Report top 5

### Comprehensive Analysis (2-4 hours)  
1. Disease and target analysis
2. Multi-database drug discovery
3. Safety assessment (FDA + FAERS)
4. Literature mining (PubMed + trials)
5. ADMET predictions
6. Scoring and ranking
7. Detailed report with recommendations

### Emergency Repurposing (1 hour)
1. Rapid target identification
2. Approved drug screening
3. Safety filtering
4. Evidence scoring
5. Priority recommendations

## Integration with Other Skills

This skill works well with:

- **disease-intelligence-gatherer** - Comprehensive disease analysis first
- **chemical-compound-retrieval** - Detailed compound property analysis
- **literature-deep-research** - Systematic literature reviews
- **protein-structure-retrieval** - Target structure for rational design

## Validation Checklist

Before recommending repurposing candidate:

- [ ] Target-disease association validated (score > 0.7)
- [ ] Drug approval status confirmed
- [ ] Safety profile acceptable for indication
- [ ] Literature evidence reviewed
- [ ] Mechanism biologically plausible
- [ ] No contraindications for patient population
- [ ] Patent landscape checked
- [ ] Market need assessed
- [ ] Clinical trial feasibility considered
- [ ] Regulatory pathway identified

## Success Metrics

**High Potential Candidates** (Score ≥70):
- Strong target association (>0.8)
- FDA approved status
- Substantial literature (>20 papers)
- Clinical trials ongoing/completed
- Favorable safety profile

**Moderate Potential** (Score 50-69):
- Moderate target association (0.5-0.8)
- Phase II/III status acceptable
- Some literature evidence (5-20 papers)
- Manageable safety concerns

**Low Potential** (Score <50):
- Weak association (<0.5)
- Limited evidence (<5 papers)
- Safety concerns
- Requires more validation

## Limitations

1. **Computational predictions**: Not clinical proof
2. **Database coverage**: Not all drugs/targets included
3. **Literature bias**: Publication bias affects evidence
4. **Safety data**: Historical, may not reflect all risks
5. **Mechanism assumptions**: Computational models have limits

**Always**: Validate top candidates through clinical trials

## Citation

When using this skill, cite:

- ToolUniverse: https://github.com/mims-harvard/ToolUniverse
- Relevant databases: DrugBank, OpenTargets, ChEMBL, etc.
- Primary literature for specific findings

## Support

- **ToolUniverse Docs**: https://zitniklab.hms.harvard.edu/ToolUniverse/
- **Slack Community**: https://join.slack.com/t/tooluniversehq/shared_invite/zt-3dic3eoio-5xxoJch7TLNibNQn5_AREQ
- **GitHub Issues**: https://github.com/mims-harvard/ToolUniverse/issues

## Version

- **Version**: 1.0.0
- **Last Updated**: February 2026
- **Compatible with**: ToolUniverse 0.5+

## License

This skill follows ToolUniverse licensing. Check individual database terms of use for commercial applications.
