---
name: tooluniverse-toxicology
description: >
  Assess chemical and drug toxicity via adverse outcome pathways, real-world adverse event signals,
  and toxicogenomic evidence. Integrates AOPWiki (AOPWiki_list_aops, AOPWiki_get_aop) for mechanism-
  level pathway tracing, FAERS for post-market adverse event quantification, OpenFDA for label mining,
  and CTD for chemical-gene-disease evidence. Produces structured toxicity reports with evidence
  grading (T1-T4). Use when asked about toxicity mechanisms, adverse outcome pathways, AOP mapping,
  FAERS signal detection, or chemical-disease relationships for drugs or environmental chemicals.
---

# Toxicology Assessment via Adverse Outcome Pathways & Signal Detection

Systematic toxicology analysis that links molecular initiating events (MIEs) through adverse outcome
pathways (AOPs) to apical adverse outcomes, then triangulates with real-world FAERS signals, FDA
label data, and toxicogenomic associations.

## Domain Reasoning

Toxicity has many mechanisms, and the first interpretive question is temporal: is this acute toxicity (immediate effect from a high dose) or chronic toxicity (cumulative damage from long-term low-dose exposure)? Acute and chronic toxicity operate through different mechanisms — acute hepatotoxicity may reflect direct mitochondrial damage, while chronic hepatotoxicity may involve fibrosis from repeated low-level inflammation. They also have different regulatory frameworks: acute toxicity is captured by LD50 and emergency protocols, while chronic toxicity requires long-term carcinogenicity and repeat-dose studies.

## LOOK UP DON'T GUESS

- Adverse outcome pathways for a chemical: query `AOPWiki_list_aops` and `AOPWiki_get_aop`; do not describe mechanisms from memory.
- FAERS adverse event signals: retrieve from `FAERS_count_reactions_by_drug_event` and `FAERS_calculate_disproportionality`; never estimate PRR values.
- FDA label warnings: call `DailyMed_parse_adverse_reactions` and related tools; do not state boxed warnings from memory.
- CTD chemical-gene and chemical-disease associations: query `CTD_get_chemical_gene_interactions` and `CTD_get_chemical_diseases`; do not infer gene targets without database evidence.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use This Skill

**Triggers**:
- "What are the toxicity mechanisms for [drug/chemical]?"
- "Find adverse outcome pathways for [chemical]"
- "What AOPs are relevant to [target/organ/effect]?"
- "FAERS signal analysis for [drug]"
- "Toxicogenomic profile for [chemical]"
- "What is the mechanism of hepatotoxicity / cardiotoxicity / neurotoxicity for [drug]?"

**Use Cases**:
1. **AOP Tracing**: Map chemical MIE through key events to apical outcome using AOPWiki
2. **Real-World Signal Detection**: Quantify FAERS adverse event signals with PRR/ROR
3. **Label Safety Mining**: Extract FDA boxed warnings, contraindications, nonclinical toxicology
4. **Toxicogenomics**: Chemical-gene-disease associations from CTD
5. **Integrated Mechanism Report**: Combine AOP pathway + real-world signals into unified narrative

---

## KEY PRINCIPLES

1. **AOP-first thinking** - Frame all toxicity in terms of MIE → Key Events → Adverse Outcome
2. **Report-first approach** - Create report file FIRST, update progressively
3. **Evidence grading mandatory** - T1 (regulatory/clinical) through T4 (computational/AOP annotation)
4. **Distinguish mechanism from signal** - AOPWiki = mechanism; FAERS = real-world signal
5. **Disambiguation first** - Resolve drug/chemical identity before any queries
6. **English-first queries** - Always use English names in tool calls

---

## Evidence Grading

| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | [T1] | FDA boxed warning, clinical trial toxicity finding, regulatory label |
| T2 | [T2] | FAERS signal PRR > 2, AOP with high biological plausibility, CTD curated |
| T3 | [T3] | CTD inferred association, AOP annotation with moderate plausibility |
| T4 | [T4] | Text-mined CTD entry, early-stage AOP annotation |

---

## Workflow Overview

```
Chemical/Drug Query
|
+-- PHASE 0: Disambiguation
|   Resolve name -> identifiers (ChEMBL, PubChem CID, SMILES)
|
+-- PHASE 1: Adverse Outcome Pathway Mapping (AOPWiki)
|   List AOPs by keyword; retrieve key events, MIEs, and biological plausibility scores
|
+-- PHASE 2: Real-World Adverse Event Signals (FAERS)
|   Top reactions by drug; disproportionality (PRR); serious event filter
|
+-- PHASE 3: FDA Label Safety Mining
|   Boxed warnings, contraindications, nonclinical toxicology, adverse reactions
|
+-- PHASE 4: Toxicogenomics (CTD)
|   Chemical-gene interactions; chemical-disease associations
|
+-- SYNTHESIS: Integrated Toxicology Report
    AOP-linked mechanism + FAERS signal + CTD gene targets + Risk classification
```

---

## Phase 0: Disambiguation

**Objective**: Establish compound identity before any database queries.

Tools:
- `PubChem_get_CID_by_compound_name` (`name`: str) — get CID + SMILES
- `ChEMBL_search_drugs` (`query`: str) — get ChEMBL ID and max phase

Capture: generic name, SMILES, PubChem CID, ChEMBL ID, drug class.

---

## Phase 1: Adverse Outcome Pathway Mapping

**Objective**: Find AOPs relevant to the chemical's known or suspected toxicity mechanisms.

### Tools

**AOPWiki_list_aops**:
- **Input**: `keyword` (str) — e.g., organ ("liver", "kidney"), effect ("apoptosis", "inflammation"), or target ("AhR", "PPARalpha")
- **Output**: List of AOP IDs, titles, and short descriptions
- **Use**: Discovery scan to identify candidate AOPs

**AOPWiki_get_aop**:
- **Input**: `aop_id` (int) — ID from list_aops result
- **Output**: Full AOP details including MIE, key events (KEs), key event relationships (KERs), biological plausibility, and weight-of-evidence
- **Use**: Retrieve mechanistic pathway details for selected AOPs

### Workflow

1. Query `AOPWiki_list_aops` with organ-level keyword (e.g., "hepatotoxicity", "nephrotoxicity")
2. Query again with mechanism-level keyword (e.g., "oxidative stress", "mitochondria")
3. Select top 3-5 most relevant AOPs by title relevance
4. Call `AOPWiki_get_aop` for each selected AOP
5. Extract: MIE (molecular initiating event), key events in order, apical adverse outcome, biological plausibility score

### Decision Logic

- **AOP found**: Extract full pathway; note plausibility level (high/moderate/low)
- **No direct AOP match**: Try broader organ or mechanism terms; document as "no AOP directly mapped"
- **Multiple AOPs**: Report all; highlight shared key events as high-confidence mechanisms

### AOP Table Format

| AOP ID | Title | MIE | Apical Outcome | Plausibility |
|--------|-------|-----|----------------|-------------|
| 123 | ... | ... | ... | High |

---

## Phase 2: Real-World Adverse Event Signals (FAERS)

**Objective**: Quantify observed adverse events with statistical signal measures.

### Tools

**FAERS_count_reactions_by_drug_event**:
- **Input**: `drug_name` (str), `limit` (int, default 50)
- **Output**: Top adverse reactions with counts
- **Note**: param is `drug_name` not `drug`

**FAERS_calculate_disproportionality**:
- **Input**: `drug_name` (str), `reaction_meddra_pt` (str)
- **Output**: PRR, ROR, IC with confidence intervals

**FAERS_filter_serious_events**:
- **Input**: `drug_name` (str), `serious_type` (str: "death", "hospitalization", "life-threatening")
- **Output**: Serious event count and case details

**FAERS_stratify_by_demographics**:
- **Input**: `drug_name` (str), `reaction_meddra_pt` (str)
- **Output**: Age/sex breakdown for specific reaction

### Workflow

1. Get top 25 reactions via `FAERS_count_reactions_by_drug_event`
2. Filter to organ-system clusters matching the AOP outcomes from Phase 1
3. Calculate PRR for top 10 reactions via `FAERS_calculate_disproportionality`
4. Check serious events (deaths, hospitalizations) for highest-PRR reactions

### Signal Thresholds

| Signal Strength | PRR | Case Count |
|----------------|-----|------------|
| Strong | > 3.0 | >= 5 |
| Moderate | 2.0-3.0 | >= 3 |
| Weak | 1.5-2.0 | >= 3 |
| None | < 1.5 | any |

---

## Phase 3: FDA Label Safety Mining

**Objective**: Extract regulatory safety findings from approved drug labels.

### Tools

- `DailyMed_parse_adverse_reactions` (`drug_name`: str)
- `DailyMed_parse_contraindications` (`drug_name`: str)
- `DailyMed_parse_clinical_pharmacology` (`drug_name`: str)
- `DailyMed_parse_drug_interactions` (`drug_name`: str)

**Note**: These tools apply to FDA-approved drugs only. Environmental chemicals will have no label data — document explicitly.

### Workflow

1. Extract adverse reactions and note which match FAERS signals
2. Extract contraindications (highest evidence tier [T1])
3. Note pharmacological mechanism from clinical pharmacology section

---

## Phase 4: Toxicogenomics (CTD)

**Objective**: Map chemical-gene interactions and chemical-disease associations.

### Tools

**CTD_get_chemical_gene_interactions**:
- **Input**: `input_terms` (str) — chemical name or MeSH ID
- **Output**: Gene targets with interaction type (increases/decreases expression)
- **Use**: Find molecular targets mediating toxicity

**CTD_get_chemical_diseases**:
- **Input**: `input_terms` (str) — chemical name or MeSH ID
- **Output**: Disease associations with evidence type (curated/inferred)
- **Use**: Find downstream disease endpoints

### Workflow

1. Query CTD with compound name; note curated (higher confidence) vs inferred entries
2. Cross-reference gene targets with Phase 1 AOP key events
3. Note which CTD disease endpoints match AOP apical outcomes

---

## Synthesis: Integrated Toxicology Report

**Structure**:

```
# Toxicology Report: [Compound Name]
**Generated**: YYYY-MM-DD

## Executive Summary
Risk tier: CRITICAL / HIGH / MEDIUM / LOW / INSUFFICIENT DATA
Key finding summary (2-3 sentences)

## 1. Compound Identity
(disambiguation table)

## 2. Adverse Outcome Pathways [T3-T4]
(AOP table; pathway diagrams in text form)

## 3. Real-World Adverse Event Signals [T1-T2]
(FAERS top reactions + PRR table + serious events)

## 4. FDA Label Safety [T1]
(boxed warnings, contraindications, adverse reactions)

## 5. Toxicogenomics [T2-T4]
(CTD gene targets + disease associations)

## 6. Mechanistic Integration
(How AOP key events map to observed FAERS signals and CTD gene targets)

## 7. Risk Classification
(Final tier with rationale)

## Data Gaps & Limitations
(Missing data, confidence caveats)
```

### Risk Classification

| Tier | Criteria |
|------|----------|
| CRITICAL | FDA boxed warning OR FAERS PRR > 5 with deaths OR multiple T1 findings |
| HIGH | FAERS PRR 3-5 serious events OR FDA warning (non-boxed) OR high-plausibility AOP |
| MEDIUM | FAERS PRR 2-3 OR CTD curated associations OR moderate-plausibility AOP |
| LOW | All signals < PRR 2; no regulatory warnings; low-plausibility AOP only |
| INSUFFICIENT DATA | Fewer than 3 phases returned usable data |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `AOPWiki_list_aops` | Broaden keyword | Search by organ system |
| `FAERS_count_reactions_by_drug_event` | `OpenFDA_search_drug_events` | Literature search |
| `DailyMed_parse_adverse_reactions` | `OpenFDA_search_drug_events` | FAERS serious events |
| `CTD_get_chemical_diseases` | `CTD_get_chemical_gene_interactions` | PubMed search |

---

## Tool Parameter Reference (Critical)

| Tool | WRONG | CORRECT |
|------|-------|---------|
| `FAERS_count_reactions_by_drug_event` | `drug` | `drug_name` |
| `AOPWiki_list_aops` | `query` | `keyword` |
| `CTD_get_chemical_gene_interactions` | `chemical` | `input_terms` |
| `CTD_get_chemical_diseases` | `chemical` | `input_terms` |

---

## Limitations

- **AOPWiki**: AOPs are in development; many lack high plausibility scores
- **FAERS**: Observational data; confounding by indication; underreporting bias
- **CTD**: Inferred associations have high false-positive rate
- **DailyMed**: FDA-approved drugs only; no environmental chemical coverage
- **Environmental chemicals**: Primarily Phase 1 (AOP) + Phase 4 (CTD) data available

---

## References

- AOPWiki: https://aopwiki.org
- FAERS: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers
- CTD: http://ctdbase.org
- DailyMed: https://dailymed.nlm.nih.gov
- OpenFDA: https://open.fda.gov
