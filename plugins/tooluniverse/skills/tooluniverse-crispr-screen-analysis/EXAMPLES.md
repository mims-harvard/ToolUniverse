# CRISPR Screen Analysis - Usage Examples

## Example 1: Analyze Gene List from Lung Cancer Screen

**User Query**:
```
I have CRISPR dropout screen hits from A549 lung cancer cells. Please analyze these genes:
KRAS, EGFR, WEE1, PLK1, AURKA, CDK2, CHEK1, MCM2, MCM3, MCM4, RPS6, RPL5, POLR2A, E2F1, RB1, CCNE1, CDC25A, CDC6, ORC1, HDAC1
```

**Analysis Mode**: Gene list analysis (20 genes)

**Expected Output**:
- Complete CRISPR_screen_analysis_A549_lung.md report
- Essentiality classification: 3 pan-cancer essential (RPS6, RPL5, POLR2A), 12 selective, 5 weakly essential
- Pathway enrichment: Strong enrichment in "Cell Cycle Checkpoints" (p=1.2e-8)
- Top 3 priorities: KRAS (score 95), EGFR (score 95), WEE1 (score 81)
- Validation recommendations with tool compounds

**Key Findings**:
- 12 selectively essential genes represent high-value targets
- E2F/RB pathway convergence suggests pathway-level vulnerability
- KRAS and EGFR are Tier 1 targets with approved drugs
- WEE1 shows synthetic lethality with TP53 mutations (present in A549)

---

## Example 2: Find Essential Genes for Pancreatic Cancer

**User Query**:
```
What are the top essential genes for pancreatic cancer? I'm looking for therapeutic targets.
```

**Analysis Mode**: Cancer type query

**Tool Workflow**:
1. `DepMap_get_cell_lines(cancer_type="Pancreatic Adenocarcinoma", page_size=50)`
2. Aggregate essentiality across pancreatic cancer cell lines
3. Identify selective dependencies (essential in pancreatic, not elsewhere)
4. Assess druggability with Pharos and DGIdb

**Expected Output**:
- Top 20 essential genes ranked by selectivity score
- KRAS appears as #1 (essential in 95% of pancreatic lines, mutated in 90%)
- CDK4/6, WEE1, ATR show selective essentiality
- Pathway enrichment: DNA damage response, replication stress
- Tier 1 targets: KRAS, WEE1, ATR (all have clinical compounds)

**Clinical Context**:
- KRAS G12C inhibitors (sotorasib) approved for other cancers
- KRAS G12D/V (common in pancreatic) have investigational inhibitors (MRTX1133)
- WEE1 inhibitor + chemotherapy shows synergy in PDAC models

---

## Example 3: Validate Single Gene Target

**User Query**:
```
We identified WEE1 as a hit in our CRISPR screen. Is this a good therapeutic target for TP53-mutant cancers?
```

**Analysis Mode**: Single gene validation

**Tool Workflow**:
1. `DepMap_get_gene_dependencies(gene_symbol="WEE1")`
2. Stratify by TP53 mutation status
3. `Pharos_get_target(gene="WEE1")` for druggability
4. `search_clinical_trials(intervention="WEE1 inhibitor")`
5. Literature search for WEE1 + TP53 synthetic lethality

**Expected Output**:
- WEE1 essentiality score: -0.72 in TP53-mutant lines, -0.15 in TP53-WT lines (selective!)
- Pharos TDL: Tchem (clinical compound adavosertib available)
- Clinical trials: 15 trials (Phase 2 in ovarian, lung, colorectal)
- Evidence for WEE1/TP53 synthetic lethality: ★★★ (multiple papers, Phase 2 data)

**Validation Recommendation**:
- Test adavosertib in panel of TP53-mutant vs TP53-WT cell lines
- Expected IC50: <100 nM in TP53-mutant, >1 µM in TP53-WT
- Combination with DNA damaging agents (cisplatin, gemcitabine)
- Timeline: 2-3 weeks for cell line validation

**Clinical Translation Path**:
- Adavosertib already in Phase 2 for multiple cancers
- Stratify patients by TP53 status (90% of cancers have TP53 alterations)
- Basket trial design: TP53-mutant solid tumors + WEE1 inhibitor

---

## Example 4: Synthetic Lethal Analysis

**User Query**:
```
My screen identified RB1 loss. What are potential synthetic lethal partners I can target?
```

**Analysis Mode**: Single gene + synthetic lethal discovery

**Tool Workflow**:
1. `DepMap_get_gene_dependencies(gene_symbol="RB1")` (baseline essentiality)
2. Build PPI network: `STRING_get_protein_interactions(protein_ids=["RB1"])`
3. Literature search: "RB1 synthetic lethal"
4. Check known syntheses: ARID1A, CDK4/6, E2F3, AURKA, PLK1

**Expected Output**:
- RB1 itself is non-essential in most contexts (tumor suppressor, often deleted)
- Synthetic lethal candidates:
  1. **CDK4/6** (★★★ evidence) - RB1-deficient cells rely on alternative CDK4/6-independent proliferation. Wait, this is backwards...
  2. **ARID1A** (★★★ evidence) - Chromatin remodeling synthetic lethality
  3. **AURKA** (★★☆ evidence) - Mitotic checkpoint bypass
  4. **E2F** targets (★★☆) - Pathway addiction

**Corrected Interpretation**:
- RB1 loss cells are hyperdependent on:
  - AURKA (mitotic progression)
  - PLK1 (mitotic entry)
  - E2F transcription factors (cannot be suppressed by RB1)
- CDK4/6 inhibitors are LESS effective in RB1-null cells (no functional RB1 to dephosphorylate)

**Validation Strategy**:
- Test AURKA inhibitor (alisertib) in RB1-null vs RB1-WT cell line pairs
- Test PLK1 inhibitor (volasertib) in same panel
- Expected: Selective killing of RB1-null cells

---

## Example 5: Pathway-Level Analysis

**User Query**:
```
My CRISPR screen hit multiple DNA repair genes (ATR, CHK1, WEE1, RAD51, BRCA2). What does this mean and how should I prioritize?
```

**Analysis Mode**: Gene list + pathway-focused interpretation

**Tool Workflow**:
1. Validate genes: `DepMap_search_genes(query=gene)` for each
2. Essentiality: `DepMap_get_gene_dependencies(gene_symbol=gene)` for each
3. Pathway enrichment: `enrichr_gene_enrichment_analysis(gene_list=[...], libs=["Reactome_2024"])`
4. PPI network: `STRING_get_protein_interactions(protein_ids=[...])`
5. Assess druggability for each

**Expected Output**:
- **Pathway Enrichment**: "DNA Damage Response" (p < 1e-10), "Homologous Recombination Repair" (p < 1e-8)
- **Network Analysis**: All genes in same functional module (STRING score >0.7)
- **Essentiality Pattern**:
  - ATR: -1.2 (strongly essential)
  - CHK1: -0.9 (moderately essential)
  - WEE1: -0.7 (context-dependent, TP53 synthetic lethal)
  - RAD51: -0.4 (weakly essential in most lines)
  - BRCA2: +0.1 (non-essential; HR-deficiency is therapeutic opportunity, not liability)

**Key Insight**:
- Screen identified DNA damage response pathway as vulnerability
- This makes sense if:
  1. Cell line has high replication stress (oncogene-driven)
  2. Cell line has pre-existing DNA repair defects (e.g., TP53 mutation)
  3. Combined with DNA damaging agents in screen

**Prioritization**:
1. **ATR** (Tier 1) - Tchem, clinical compounds (ceralasertib, elimusertib), Phase 2 trials
2. **CHK1** (Tier 1) - Tchem, clinical compounds (prexasertib), Phase 2 trials
3. **WEE1** (Tier 1) - Tchem, clinical compound (adavosertib), multiple Phase 2 trials
4. **RAD51** (Tier 3) - Weak essentiality, no direct inhibitors
5. **BRCA2** (Not a target) - Loss-of-function; instead use PARP inhibitors for BRCA2-deficient cells

**Therapeutic Strategy**:
- ATR/CHK1/WEE1 inhibitors + DNA damaging chemotherapy (cisplatin, gemcitabine)
- Exploit replication stress and DNA damage response addiction
- Clinical precedent: WEE1i + carboplatin in ovarian cancer (Phase 2)

---

## Example 6: Cancer Type Comparison

**User Query**:
```
Compare essential genes between lung cancer and breast cancer. What are the differences?
```

**Analysis Mode**: Multi-cancer comparison

**Tool Workflow**:
1. `DepMap_get_cell_lines(tissue="Lung", page_size=100)`
2. `DepMap_get_cell_lines(tissue="Breast", page_size=100)`
3. Aggregate essentiality data across each cancer type
4. Calculate differential essentiality (lung-selective vs breast-selective)
5. Druggability assessment for selective dependencies

**Expected Output**:

| Gene | Lung Essentiality | Breast Essentiality | Selectivity | Druggability |
|------|-------------------|---------------------|-------------|--------------|
| **EGFR** | -0.85 | -0.15 | Lung-selective | Tclin (multiple approved drugs) |
| **KRAS** | -0.78 | -0.20 | Lung-selective | Tchem (G12C inhibitors approved) |
| **ESR1** | -0.05 | -0.68 (ER+ only) | Breast-selective | Tclin (tamoxifen, fulvestrant) |
| **ERBB2** | -0.12 | -0.72 (HER2+ only) | Breast-selective | Tclin (trastuzumab, T-DM1) |
| **STK11/LKB1** | -0.65 (KRAS-mutant) | -0.18 | Lung-selective | Tbio (not directly druggable) |

**Key Insights**:
- **Lung cancer dependencies**: EGFR, KRAS, STK11 (driven by specific mutations)
- **Breast cancer dependencies**: ESR1, ERBB2/HER2, PIK3CA (driven by receptor status)
- **Shared dependencies**: Cell cycle (CDKs), DNA damage response (WEE1, ATR)
- **Therapeutic implication**: Tissue-selective targets offer better therapeutic windows

---

## Example 7: Multi-Hit Validation Strategy

**User Query**:
```
I have 100 hits from my CRISPR screen. I can only validate 10 genes experimentally. Which ones should I choose?
```

**Analysis Mode**: Hit prioritization with resource constraints

**Prioritization Workflow**:
1. Calculate multi-dimensional score (essentiality + selectivity + druggability + clinical relevance)
2. Filter to Tier 1 (score >80) and Tier 2 (score 60-80)
3. Within Tier 1, prioritize by:
   - Tool compound availability (for fast validation)
   - Clinical stage (approved > Phase 3 > Phase 2)
   - Selectivity (tissue-specific > pan-cancer)
4. Group by pathway (don't validate 5 genes from same pathway)
5. Balance risk (include 1-2 novel Tbio targets alongside safe Tclin targets)

**Recommended Validation Set (10 genes)**:

**Tier 1 Targets (5 genes) - High confidence, existing tools**:
1. **KRAS** (Score 95) - G12C inhibitors available, approved in NSCLC
2. **WEE1** (Score 81) - Adavosertib in Phase 2, TP53 synthetic lethal
3. **AURKA** (Score 80) - Alisertib in Phase 3 lymphoma
4. **CHEK1** (Score 77) - Prexasertib in Phase 2, DDR pathway
5. **HDAC1** (Score 76) - Approved HDAC inhibitors (vorinostat, romidepsin)

**Tier 2 Targets (3 genes) - Medium confidence, chemical probes available**:
6. **PLK1** (Score 71) - Volasertib tool compound, mitotic target
7. **ATR** (Score 69) - Ceralasertib in Phase 2, DDR pathway
8. **CDK2** (Score 68) - Multiple tool compounds, G1/S transition

**Tier 2 Novel (2 genes) - Higher risk, but high impact if validated**:
9. **GENE_X** (Score 65) - Tbio target, novel mechanism, selective
10. **GENE_Y** (Score 62) - Tdark target, no tool compounds (genetic validation only)

**Validation Timeline**:
- Weeks 1-4: Tier 1 targets (compounds readily available)
- Weeks 5-8: Tier 2 targets (may need to order compounds)
- Weeks 9-12: Novel targets (genetic validation, longer lead time)

**Success Metrics**:
- Expect 4-5/5 Tier 1 targets to validate (80-100% success rate)
- Expect 2-3/3 Tier 2 targets to validate (67-100% success rate)
- Expect 0-1/2 novel targets to validate (0-50% success rate, but high impact)

---

## Common Pitfalls & How to Avoid Them

### Pitfall 1: Pan-Cancer Essential Genes Prioritized Over Selective

**Problem**: Ribosomal proteins (RPS6, RPL5) score high in essentiality but are pan-cancer essential.

**Solution**: Multi-dimensional scoring explicitly penalizes pan-cancer genes. Check essentiality in normal cells.

**Red Flags**:
- Gene is essential in >90% of cell lines across all cancer types
- Gene is core housekeeping function (ribosome, proteasome, RNA pol II)
- Poor therapeutic window (tumor/normal expression ratio <2)

### Pitfall 2: Off-Target CRISPR Effects

**Problem**: Gene scores high in CRISPR screen but tool compounds show no effect.

**Solution**: Orthogonal validation required (siRNA, CRISPRi, multiple sgRNAs).

**Red Flags**:
- Single sgRNA hit (other sgRNAs negative)
- No pathway coherence with other hits
- Tool compounds inactive despite strong essentiality score

### Pitfall 3: Non-Druggable Hits

**Problem**: Transcription factors (E2F1, MYC) are highly essential but lack catalytic domains.

**Solution**: Flag as "alternative strategy needed" and suggest PROTACs or indirect targeting.

**Workarounds**:
- PROTACs (if E3 ligase binding site known)
- Molecular glue degraders
- Indirect targeting (upstream kinases, downstream effectors)

### Pitfall 4: Ignoring Biological Context

**Problem**: Assuming essentiality = good target without considering pathway redundancy.

**Solution**: Assess in network context; check if backup pathways exist.

**Example**:
- Knocking out single CDK (e.g., CDK2) may be compensated by CDK1/4/6
- Requires multi-target inhibition or combination therapy

