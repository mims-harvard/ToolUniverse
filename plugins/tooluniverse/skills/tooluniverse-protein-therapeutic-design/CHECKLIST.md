# Therapeutic Protein Designer Checklist

Pre-delivery verification checklist for protein design reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `[TARGET]_protein_design_report.md`
- [ ] All 8 main sections present
- [ ] Executive summary completed (not `[Designing...]`)
- [ ] Data sources section populated

### Phase 1: Target Characterization
- [ ] Target protein identified with UniProt ID
- [ ] Target structure obtained (PDB ID or predicted)
- [ ] Structure source documented (PDB/AlphaFold/NvidiaNIM)
- [ ] Binding epitope defined (residue range)
- [ ] Existing binders/therapeutics noted
- [ ] Target function described

### Phase 2: Backbone Generation
- [ ] NVIDIA_API_KEY availability confirmed
- [ ] Design mode specified (unconditional/binder/motif)
- [ ] Diffusion steps documented
- [ ] ≥5 backbones generated
- [ ] Backbone topologies described
- [ ] Quality assessment for each backbone
- [ ] Top 3-5 selected with rationale

### Phase 3: Sequence Design
- [ ] ProteinMPNN parameters documented
- [ ] Temperature setting stated
- [ ] ≥8 sequences per backbone
- [ ] Total sequence count reported
- [ ] MPNN scores for all sequences
- [ ] Top 10 sequences ranked
- [ ] Full sequences provided (FASTA format)

### Phase 4: Structure Validation
- [ ] All sequences validated by ESMFold/AlphaFold
- [ ] pLDDT reported for each design
- [ ] pTM reported for each design
- [ ] RMSD to designed backbone (if applicable)
- [ ] Pass/fail criteria applied (pLDDT >70, pTM >0.7)
- [ ] Regional confidence breakdown for top designs
- [ ] ≥3 designs pass validation

### Phase 5: Developability Assessment
- [ ] Aggregation propensity scored
- [ ] Isoelectric point calculated
- [ ] Cysteine count and pairing noted
- [ ] Expression prediction (E. coli/mammalian)
- [ ] Hydrophobic patch analysis
- [ ] Overall developability rating

### Phase 6: Final Deliverables
- [ ] Ranked candidate list with all metrics
- [ ] FASTA file with designed sequences
- [ ] CSV with candidate metrics
- [ ] Evidence tier assigned to each design

---

## Citation Requirements

### Every Design Must Include
- [ ] Design method (RFdiffusion → ProteinMPNN → ESMFold)
- [ ] Tool names in backticks
- [ ] All numerical metrics

### Format Examples
```markdown
*Design Method: RFdiffusion backbone → ProteinMPNN sequence → ESMFold validation*
*Source: NVIDIA NIM via `NvidiaNIM_rfdiffusion` (50 diffusion steps)*
*Source: NVIDIA NIM via `NvidiaNIM_proteinmpnn` (T=0.1, 8 sequences)*
*Source: NVIDIA NIM via `NvidiaNIM_esmfold` (pLDDT: 88.5, pTM: 0.85)*
```

---

## Evidence Grading

### All Designs Must Have
- [ ] Evidence tier assigned (★★★ to ☆☆☆)
- [ ] All quality metrics documented
- [ ] Developability assessment complete

### Tier Definitions
| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | ★★★ | pLDDT >85, pTM >0.8, aggregation <0.5, neutral pI |
| T2 | ★★☆ | pLDDT >75, pTM >0.7, acceptable developability |
| T3 | ★☆☆ | pLDDT >70, pTM >0.65, some concerns |
| T4 | ☆☆☆ | Failed validation or major issues |

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Backbones generated | ≥5 |
| Backbones selected | ≥3 |
| Sequences per backbone | ≥8 |
| Total sequences | ≥24 |
| Validated designs | ≥10 |
| Passing designs | ≥3 |
| Final candidates | ≥3 ranked |

---

## Design Quality Metrics

### Structure Prediction Quality
| Metric | Excellent | Good | Acceptable | Fail |
|--------|-----------|------|------------|------|
| pLDDT | >90 | >80 | >70 | <70 |
| pTM | >0.85 | >0.75 | >0.65 | <0.65 |

### ProteinMPNN Score
| Score | Interpretation |
|-------|----------------|
| < -2.5 | Excellent (rare) |
| -2.5 to -2.0 | Very good |
| -2.0 to -1.5 | Good |
| -1.5 to -1.0 | Acceptable |
| > -1.0 | Consider alternatives |

### Developability
| Factor | Favorable | Marginal | Unfavorable |
|--------|-----------|----------|-------------|
| Aggregation | <0.5 | 0.5-0.7 | >0.7 |
| pI | 5-9 | 4-5, 9-10 | <4, >10 |
| MW | <50 kDa | 50-100 kDa | >100 kDa |
| Cysteines | 0 or paired | Odd number | Multiple unpaired |

---

## Output Files

### Required
- [ ] `[TARGET]_protein_design_report.md` - Main report

### Required Data Files
- [ ] `[TARGET]_designed_sequences.fasta` - All sequences
- [ ] `[TARGET]_top_candidates.csv` - Ranked candidates

### FASTA Format
```
>Design_001 | pLDDT=88.5 | pTM=0.85 | MPNN=-1.89 | Tier=T1
MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH
GSAQVKGHGKKVADALTNAVAHVDDMPNALSALSDLHAHKL
>Design_002 | pLDDT=82.3 | pTM=0.79 | MPNN=-1.95 | Tier=T2
...
```

### CSV Column Requirements
```
Rank,Design_ID,Sequence,Length,Backbone,MPNN_Score,pLDDT,pTM,Aggregation,pI,Tier
```

---

## Design-Specific Checks

### For Binder Design
- [ ] Target structure used in design
- [ ] Epitope/hotspot residues specified
- [ ] Interface quality assessed
- [ ] Binding mode predicted

### For Scaffold Design
- [ ] Topology specified (alpha/beta/mixed)
- [ ] Size constraints met
- [ ] Functional sites preserved

### For Enzyme Design
- [ ] Active site geometry maintained
- [ ] Catalytic residues in place
- [ ] Substrate access verified

---

## Experimental Recommendations

### Must Include
- [ ] Expression system recommendation
- [ ] Purification strategy
- [ ] Characterization assays
- [ ] Expected challenges

### Expression Systems
| Design Type | Recommended | Alternative |
|-------------|-------------|-------------|
| Simple scaffold | E. coli | Insect |
| Disulfide-containing | Mammalian | Insect |
| Glycosylated | Mammalian | - |
| Toxic | Cell-free | Insect |

---

## Final Review

### Before Delivery
- [ ] No `[Designing...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] Executive summary synthesizes key findings
- [ ] Top 3 candidates clearly identified
- [ ] Sequences ready for ordering
- [ ] Experimental plan outlined

### Common Issues to Avoid
- [ ] Missing pLDDT/pTM values
- [ ] Sequences without MPNN scores
- [ ] Incomplete developability assessment
- [ ] Missing FASTA file
- [ ] Unclear ranking criteria
- [ ] No experimental recommendations

---

## NVIDIA NIM Tool Checklist

### Pre-Run Verification
- [ ] NVIDIA_API_KEY environment variable set
- [ ] Rate limit awareness (40 RPM)
- [ ] Async handling for AlphaFold2

### Post-Run Validation
- [ ] All tool calls succeeded
- [ ] Reasonable output values
- [ ] No error responses in data
- [ ] Fallbacks used if needed

---

## Iteration Notes

If initial designs don't meet criteria:
1. [ ] Adjust RFdiffusion steps (try 75-100)
2. [ ] Lower ProteinMPNN temperature (try 0.05)
3. [ ] Generate more backbones
4. [ ] Try different design mode
5. [ ] Document iterations in report
