# Small Molecule Binder Discovery Checklist

Pre-delivery verification checklist for binder discovery reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created with correct naming: `[TARGET]_binder_discovery_report.md`
- [ ] All 9 main sections present
- [ ] Executive summary completed (not `[Researching...]`)
- [ ] Data sources section populated

### Phase 1: Target Validation
- [ ] UniProt accession documented
- [ ] ChEMBL target ID obtained (or "Not in ChEMBL" noted)
- [ ] Ensembl gene ID resolved
- [ ] Druggability assessed from ≥2 sources
- [ ] Druggability scorecard included
- [ ] Binding site information present (or "No structural data available")
- [ ] Target class identified (kinase, GPCR, enzyme, etc.)

### Phase 1.4: Structure Prediction (NVIDIA NIM)
- [ ] NVIDIA_API_KEY availability checked and documented
- [ ] Structure prediction method stated (AlphaFold2/ESMFold/PDB)
- [ ] pLDDT confidence scores reported (if NvidiaNIM_alphafold2 used)
- [ ] Confidence breakdown table included (Very High/Confident/Low/Very Low)
- [ ] Key binding residue pLDDT values documented
- [ ] Mean pLDDT interpretation provided
- [ ] Structure source attributed (NvidiaNIM_alphafold2, NvidiaNIM_esmfold, or PDB)

### Phase 2: Known Ligands
- [ ] ChEMBL bioactivity data queried
- [ ] Activity statistics table included (count, potency distribution)
- [ ] Top 10 most potent compounds listed with IC50/Ki values
- [ ] Chemical probes identified (or "None available" stated)
- [ ] SAR insights summarized (scaffolds, key modifications)
- [ ] Approved drugs for target listed (or "None approved")

### Phase 3: Structure
- [ ] PDB structures listed with resolution (or "No experimental structure")
- [ ] Best structure for docking identified and justified
- [ ] Binding pocket described (residues, volume, character)
- [ ] Key interaction points documented
- [ ] AlphaFold structure noted if no experimental

### Phase 3.5: Docking Validation (NVIDIA NIM)
- [ ] Reference compound selected for docking validation
- [ ] Reference compound docked (NvidiaNIM_diffdock or NvidiaNIM_boltz2)
- [ ] Docking method documented (DiffDock vs Boltz2)
- [ ] Best pose confidence score reported
- [ ] Steric clash assessment included
- [ ] Validation status stated (✓ binding pocket captured or ✗ issues)
- [ ] Docking tool source attributed

### Phase 4: Compound Expansion
- [ ] ≥3 diverse seed compounds used for similarity search
- [ ] Similarity threshold documented (typically 70-85%)
- [ ] Total compounds from similarity search reported
- [ ] Substructure search completed (if scaffolds identified)
- [ ] Cross-database mining results included
- [ ] Deduplication performed and counts reported
- [ ] Source attribution for each search

### Phase 4.4: De Novo Generation (NVIDIA NIM) - Optional
- [ ] Seed scaffolds identified from top actives
- [ ] Masked SMILES designed (if NvidiaNIM_genmol used)
- [ ] Mask positions and purpose documented
- [ ] Number of molecules generated reported
- [ ] Lipinski pass rate documented
- [ ] Mean QED score reported
- [ ] Unique scaffolds count noted
- [ ] Top generated compounds listed with SMILES, QED, LogP
- [ ] Generation tool attributed (NvidiaNIM_genmol or NvidiaNIM_molmim)
- [ ] Generated compounds passed to ADMET filtering

### Phase 5: ADMET Filtering
- [ ] Physicochemical filters applied (Lipinski, QED)
- [ ] Filter thresholds documented
- [ ] Bioavailability predictions included
- [ ] Toxicity predictions included (AMES, hERG, DILI minimum)
- [ ] CYP interaction flags noted
- [ ] Structural alert check completed
- [ ] Filter funnel table with pass/fail counts at each stage
- [ ] Common failure reasons documented

### Phase 6: Candidate Docking & Prioritization
- [ ] All candidates docked (NvidiaNIM_diffdock or NvidiaNIM_boltz2)
- [ ] Docking scores compared to reference compound
- [ ] Scoring methodology explained (docking + ADMET + novelty)
- [ ] All scoring dimensions documented with weights
- [ ] ≥20 candidates ranked (or all available if fewer)
- [ ] Top 20 table includes: ID, SMILES, Docking vs Ref, ADMET score, overall score
- [ ] Synthesis feasibility assessed (SA score or commercial availability)
- [ ] Scaffold diversity noted (number of distinct scaffolds)
- [ ] Evidence tier assigned to each candidate (T0-T5 scale)

### Phase 7: Recommendations
- [ ] ≥3 immediate actions listed
- [ ] Experimental validation plan outlined
- [ ] Backup strategies identified
- [ ] Timeline/priority suggestions included

### Phase 8: Data Gaps
- [ ] All data gaps aggregated in one section
- [ ] Reason for each gap documented
- [ ] Alternative approaches suggested for gaps

### Phase 10: Methods Summary
- [ ] Methods summary table included
- [ ] All tools used listed with purpose
- [ ] Key tools documented:
  - [ ] Sequence retrieval (UniProt_search)
  - [ ] Structure prediction (NvidiaNIM_alphafold2/esmfold if used)
  - [ ] Docking validation (NvidiaNIM_diffdock/boltz2 if used)
  - [ ] Known ligands (ChEMBL_get_target_activities)
  - [ ] Similarity search (ChEMBL_search_similar_molecules)
  - [ ] De novo generation (NvidiaNIM_genmol/molmim if used)
  - [ ] ADMET filtering (ADMETAI_predict_*)
  - [ ] Candidate docking (NvidiaNIM_diffdock/boltz2 if used)

### Data Output Files
- [ ] `[TARGET]_candidate_compounds.csv` created with prioritized list
- [ ] CSV includes: Rank, ID, SMILES, Similarity, ADMET_Score, Overall_Score, Source
- [ ] All candidates have valid SMILES

## Citation Requirements

### Every Section Must Include
- [ ] Source attribution for data (database name + tool used)
- [ ] Specific identifiers used (ChEMBL ID, PDB ID, etc.)
- [ ] Date of data retrieval (for dynamic databases)

### Format Examples
```markdown
*Source: ChEMBL via `ChEMBL_get_target_activities` (CHEMBL203)*
*Source: PDB via `get_protein_metadata_by_pdb_id` (1M17)*
*Source: ADMET-AI via `ADMETAI_predict_toxicity`*
*Source: NVIDIA NIM via `NvidiaNIM_alphafold2` (pLDDT: 90.94)*
*Source: NVIDIA NIM via `NvidiaNIM_diffdock` (confidence: 0.906)*
*Source: NVIDIA NIM via `NvidiaNIM_genmol` (100 molecules)*
```

## Evidence Grading

### All Candidates Must Have
- [ ] Evidence tier assigned (★★★★ to ○○○)
- [ ] Rationale for tier documented
- [ ] Docking comparison to reference (if docking performed)

### Tier Definitions Applied
| Tier | Symbol | Criteria |
|------|--------|----------|
| T0 | ★★★★ | Docking score > reference inhibitor |
| T1 | ★★★ | Experimental IC50/Ki < 100 nM from ChEMBL |
| T2 | ★★☆ | Docking within 5% of reference OR IC50 100-1000 nM |
| T3 | ★☆☆ | >80% similarity to T1 compound |
| T4 | ☆☆☆ | 70-80% similarity, scaffold match only |
| T5 | ○○○ | Generated molecule, ADMET-passed, no docking |

### Docking-Enhanced Grading
- [ ] If docking performed, apply upgrade/downgrade rules
- [ ] Docking > reference → T0 (★★★★)
- [ ] Docking within 5% → T2 (★★☆)
- [ ] Docking >20% worse → downgrade one tier

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Known actives | Top 10 listed with potency |
| Structures | All available listed (≥1 or explicit "none") |
| Structure prediction | pLDDT reported if NvidiaNIM used |
| Expansion seeds | ≥3 diverse compounds |
| Similarity results | ≥100 compounds or exhausted |
| De novo generation | ≥50 molecules if GenMol/MolMIM used |
| Docked candidates | All top 20 docked if NvidiaNIM available |
| Final candidates | ≥20 ranked (or all if fewer) |
| Methods summary | All tools listed with purpose |
| Immediate actions | ≥3 specific recommendations |

## Final Review

### Before Delivery
- [ ] No `[Researching...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] No empty sections (use "Not available" with explanation)
- [ ] Executive summary synthesizes key findings
- [ ] Recommendations are actionable and specific
- [ ] Report is self-contained (user doesn't need external context)

### Common Issues to Avoid
- [ ] Missing evidence tiers on candidates
- [ ] Unattributed data (no source citation)
- [ ] Empty ADMET predictions (tool may have failed silently)
- [ ] Inconsistent compound identifiers
- [ ] Missing SMILES in candidate list
- [ ] Recommendations without supporting data
