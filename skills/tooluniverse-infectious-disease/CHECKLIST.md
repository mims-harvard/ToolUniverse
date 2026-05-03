# Infectious Disease Outbreak Intelligence Checklist

Pre-delivery verification checklist for outbreak intelligence reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `[PATHOGEN]_outbreak_intelligence.md`
- [ ] All 8 main sections present
- [ ] Executive summary completed (not `[Analyzing...]`)
- [ ] Data sources section populated

### Phase 1: Pathogen Identification
- [ ] Scientific name documented
- [ ] Taxonomy ID (NCBI) provided
- [ ] Pathogen type classified (virus/bacteria/fungus/parasite)
- [ ] Family and genus identified
- [ ] Full taxonomic lineage shown
- [ ] Related pathogens with drug precedent identified
- [ ] Genome/proteome reference noted

### Phase 2: Target Identification
- [ ] ≥5 druggable targets identified
- [ ] Each target has UniProt accession
- [ ] Protein function described
- [ ] Essentiality justified
- [ ] Conservation across strains noted
- [ ] Drug precedent checked (related pathogens)
- [ ] Targets ranked by druggability score
- [ ] Top 3 targets have detailed profiles

### Phase 3: Structure Prediction
- [ ] NVIDIA_API_KEY availability documented
- [ ] Structures predicted for top 3 targets (minimum)
- [ ] Method stated (AlphaFold2/ESMFold)
- [ ] Mean pLDDT reported for each structure
- [ ] pLDDT distribution by region included
- [ ] Binding site regions identified
- [ ] Active site residue confidence documented
- [ ] Docking suitability assessed

### Phase 4: Drug Repurposing Screen
- [ ] ≥20 candidate drugs identified
- [ ] Sources documented (related pathogen, broad-spectrum, target class)
- [ ] FDA approval status for each drug
- [ ] Docking performed for top candidates
- [ ] Docking scores reported with confidence
- [ ] Top 5-10 candidates ranked
- [ ] Mechanism of action described
- [ ] Clinical evidence level assigned

### Phase 5: Literature Intelligence
- [ ] Recent publications searched (<6 months)
- [ ] Key findings summarized
- [ ] Active clinical trials listed
- [ ] Resistance data noted (if available)
- [ ] Previous treatment outcomes summarized

### Phase 6: Recommendations
- [ ] ≥3 immediate actions listed
- [ ] Clinical trial opportunities identified
- [ ] Research priorities outlined
- [ ] Timeframe/urgency noted

---

## Citation Requirements

### Every Section Must Include
- [ ] Source database name
- [ ] Tool used (in backticks)
- [ ] Specific identifiers (UniProt, NCBI, NCT, etc.)

### Format Examples
```markdown
*Source: NCBI Taxonomy via `NCBI_Taxonomy_search` (TaxID: 2697049)*
*Source: UniProt via `UniProt_search` (P0DTD1)*
*Source: NVIDIA NIM via `NvidiaNIM_alphafold2` (pLDDT: 91.2)*
*Source: NVIDIA NIM via `NvidiaNIM_diffdock` (score: 0.92)*
*Source: ChEMBL via `ChEMBL_search_drugs`*
```

---

## Evidence Grading

### All Drug Candidates Must Have
- [ ] Evidence tier assigned (★★★ to ☆☆☆)
- [ ] Docking score (if docked)
- [ ] Clinical evidence level
- [ ] Rationale for ranking

### Tier Definitions
| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | ★★★ | FDA approved for this pathogen |
| T2 | ★★☆ | Clinical trial data OR approved for related pathogen |
| T3 | ★☆☆ | In vitro activity OR strong docking + mechanism |
| T4 | ☆☆☆ | Computational prediction only |

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Related pathogens | ≥3 with drug precedent |
| Druggable targets | ≥5 ranked targets |
| Target details | Top 3 with full profiles |
| Structure predictions | ≥3 targets predicted |
| Drug candidates | ≥20 screened |
| Docking results | Top 10 docked |
| Clinical trials | All active trials listed |
| Recommendations | ≥3 immediate actions |

---

## Pathogen-Specific Checks

### Viral Pathogens
- [ ] Genome type noted (DNA/RNA, ss/ds, +/-)
- [ ] Polymerase identified as target
- [ ] Protease(s) identified
- [ ] Entry mechanism proteins noted
- [ ] Polymerase inhibitors screened
- [ ] Protease inhibitors screened

### Bacterial Pathogens
- [ ] Gram stain classification
- [ ] Essential metabolic pathways identified
- [ ] Antibiotic resistance genes checked
- [ ] Cell wall synthesis targets noted
- [ ] Protein synthesis targets noted
- [ ] DNA replication targets noted

### Drug-Resistant Pathogens
- [ ] Resistance mechanisms documented
- [ ] Drugs avoiding resistance prioritized
- [ ] Novel mechanism drugs highlighted
- [ ] Combination strategies considered

---

## Docking Quality Checks

### Structure Quality
- [ ] Mean pLDDT >70 for docking
- [ ] Active site pLDDT >80
- [ ] No major clashes in structure
- [ ] Binding pocket well-defined

### Docking Results
- [ ] Reference drug docked for validation
- [ ] Score interpretation provided
- [ ] Pose quality assessed
- [ ] Binding mode plausible

---

## Output Files

### Required
- [ ] `[PATHOGEN]_outbreak_intelligence.md` - Main report

### Recommended
- [ ] `[PATHOGEN]_drug_candidates.csv` - All candidates with scores
- [ ] `[PATHOGEN]_target_proteins.csv` - Target list with properties

### CSV Column Requirements
**drug_candidates.csv**:
```
Drug_Name,ChEMBL_ID,Indication,FDA_Status,Docking_Score,Evidence_Tier,Mechanism
```

**target_proteins.csv**:
```
Target_Name,UniProt_ID,Function,Essentiality,Conservation,Druggability_Score,Drug_Precedent
```

---

## Urgent Findings Protocol

If any of these found, flag prominently:
- [ ] No approved drugs available
- [ ] All existing drugs ineffective (docking)
- [ ] High mortality/transmission
- [ ] Drug resistance detected
- [ ] Novel pathogen (no related drugs)

### Urgent Flag Format
```markdown
⚠️ **URGENT: [Finding]** ⚠️

[Description of critical finding]

**Recommended Action**: [Immediate step]
```

---

## Final Review

### Before Delivery
- [ ] No `[Analyzing...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] Executive summary synthesizes key findings
- [ ] Top drug candidate clearly stated
- [ ] Recommendations are actionable and specific
- [ ] Appropriate urgency conveyed

### Common Issues to Avoid
- [ ] Targets without UniProt IDs
- [ ] Structures without pLDDT confidence
- [ ] Drugs without FDA status
- [ ] Docking without reference compound
- [ ] Recommendations without evidence support
- [ ] Missing pathogen classification

---

## Speed Optimization

For outbreak scenarios, prioritize:
1. FDA-approved drugs first (fastest to deploy)
2. Drugs in phase 3 trials second
3. Novel candidates last (longest timeline)

### Parallel Processing
- Run taxonomy AND protein searches in parallel
- Run multiple structure predictions in parallel
- Dock multiple candidates simultaneously
