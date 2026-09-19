---
name: tooluniverse-toxicology
description: Drug and chemical toxicity assessment via adverse outcome pathways (AOPs), real-world FAERS adverse event signals, FDA labels, toxicogenomic associations, and EPA CompTox quantitative hazard/high-throughput bioactivity data. Triangulates molecular initiating event to cellular outcome to organ-level toxicity to clinical adverse event. Use for hepatotoxicity/cardiotoxicity/nephrotoxicity prediction and toxicology reports.
disable-model-invocation: true
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
- EPA CompTox hazard values and ToxCast/Tox21 bioactivity: query `CompTox_get_hazard_data` and `CompTox_get_bioactivity_summary`/`CompTox_get_bioactivity_assays`; never estimate an LD50, a hazard classification, or an assay hit-call rate from memory — this is exactly the kind of chemical-specific quantitative data that must come from the database.

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
| T3 | [T3] | CTD inferred association, AOP annotation with moderate plausibility, screening-level CompTox ToxVal |
| T4 | [T4] | Text-mined CTD entry, early-stage AOP annotation, isolated ToxCast/Tox21 assay hit with no cross-source corroboration |

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
+-- PHASE 4c: Quantitative Hazard & HTS Bioactivity (EPA CompTox)
|   Curated dose-based hazard values (ToxVal); ToxCast/Tox21 assay hit rates
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

## Phase 4c: Quantitative Hazard & HTS Bioactivity (EPA CompTox)

**Objective**: Get curated, dose-based hazard values and quantitative high-throughput screening (HTS) bioactivity data — the kind of numeric, assay-level evidence AOPWiki (mechanism) and FAERS (real-world signal) don't provide.

Requires `EPA_COMPTOX_API_KEY` (free; request by emailing `ccte_api@epa.gov`). Without the key, these tools are excluded from `tu list` entirely (same gating pattern as Addgene/USPTO) rather than failing loudly — check for their presence before relying on this phase.

### Tools

**CompTox_search_chemical** (`word`: str — name, CASRN, or InChIKey):
- **Output**: Matching `dtxsid`/`dtxcid`/`casrn`/`preferredName` records
- **Use**: Resolve chemical identity to a DTXSID — required input for every other CompTox call. Run this immediately after Phase 0's PubChem/ChEMBL disambiguation; DTXSID is a separate identifier space from PubChem CID / ChEMBL ID.

**CompTox_get_hazard_data** (`dtxsid`: str):
- **Output**: ToxVal records — points of departure (NOAEL/LOAEL/BMDL), lethality effect levels (LD50/LC50), reference doses, exposure limits, each tagged with source, species, and study type
- **Use**: The quantitative dose-response counterpart to AOPWiki's qualitative mechanism and DailyMed's label text — grade as T1/T2 per source (regulatory sources like EPA IRIS/ECOTOX rank higher than screening-level estimates; check the `source` field per record)

**CompTox_get_bioactivity_summary** (`dtxsid`: str):
- **Output**: Aggregate ToxCast/Tox21 hit counts (`activeMc`/`totalMc`, `activeSc`/`totalSc`) and cytotoxicity burst point (`cytotoxMedianUm`)
- **Use**: A fast "how promiscuous and how cytotoxic does this chemical look across ~700+ HTS assays" check before deciding whether per-assay drill-down is worth it

**CompTox_get_bioactivity_assays** (`dtxsid`: str):
- **Output**: Per-assay hit-call records (`aeid`, `hitCall`, `ac50`) — which specific biological targets/pathways the chemical activated
- **Use**: Drill into which assay endpoints (`aeid`) drove the summary hit count; cross-reference specific `aeid`s against Phase 1's AOP key events when a mechanistic link is claimed — do not assume an HTS hit implies the AOP mechanism without checking the assay's actual target

### Workflow

1. `CompTox_search_chemical` on the compound name to get its DTXSID
2. `CompTox_get_hazard_data` for curated dose-based hazard values; note source/species per record
3. `CompTox_get_bioactivity_summary` for the HTS overview; if `activeMc`/`totalMc` shows meaningful activity, drill into `CompTox_get_bioactivity_assays`
4. Cross-reference high-hit-rate assay targets against Phase 1's AOP key events and Phase 4's CTD gene targets — convergent evidence across three independent sources (AOP mechanism, CTD gene interaction, ToxCast assay target) is much stronger than any one alone

### Decision Logic

- **No DTXSID match**: The compound may not be in the CompTox universe (common for very new drugs or non-registered mixtures) — document as "not in CompTox" rather than treating it as zero hazard
- **Hazard records but no bioactivity**: Chemical has traditional tox study data but hasn't been through ToxCast/Tox21 screening — do not infer bioactivity from hazard data or vice versa, they measure different things
- **High assay hit rate with low `cytotoxMedianUm`**: A large fraction of "hits" may just reflect general cytotoxicity (cell stress triggers many unrelated assays) rather than a specific mechanism — check whether hit `aeid`s cluster around one pathway or are scattered, and flag a low cytotoxicity burst point as a reason to discount isolated hits

---

## Phase 4b: Toxin Reference Lookup (T3DB) — currently broken upstream, verified

**Objective**: Cross-reference a chemical/toxin against T3DB's curated toxin profiles (mechanism of toxicity, health effects, routes of exposure) via `T3DB_search_toxins` (`query`: str) and `T3DB_get_toxin` (`toxin_id`: str, e.g. `T3D0001`).

**Live-verified status: both tools currently fail with HTTP 403** on every attempt (confirmed on multiple retries, both the search endpoint and a direct `get_toxin` call by known ID) — t3db.ca appears to be blocking the underlying request pattern entirely, not a transient outage tied to a specific query. **Do not fabricate a toxin profile, mechanism, or health-effect list if this 403s** — report T3DB as unavailable and fall back to CTD (Phase 4) and AOPWiki (Phase 1) for mechanistic toxicology instead, or DailyMed (Phase 3) if the chemical is also an FDA-approved drug. Re-check T3DB's live status with a cheap call before assuming this is still broken — it may be fixed by the time you read this.

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
| `CompTox_get_hazard_data` | `CTD_get_chemical_diseases` | AOPWiki apical outcome only |

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
- **T3DB**: Both tools verified returning HTTP 403 as of this writing (upstream request-blocking, not a per-query issue) — treat as unavailable until re-verified live
- **EPA CompTox**: requires a free API key (`EPA_COMPTOX_API_KEY`, request via `ccte_api@epa.gov`) — schemas verified against the live production OpenAPI specs, but full response shapes were not live-tested end-to-end in this environment since no real key was available; DTXSID coverage skews toward chemicals with US regulatory/environmental relevance and may be sparse for newer or purely investigational drugs
- **DailyMed**: FDA-approved drugs only; no environmental chemical coverage
- **Environmental chemicals**: Primarily Phase 1 (AOP) + Phase 4 (CTD) data available

---

## References

- AOPWiki: https://aopwiki.org
- FAERS: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers
- CTD: http://ctdbase.org
- DailyMed: https://dailymed.nlm.nih.gov
- OpenFDA: https://open.fda.gov
- EPA CompTox: https://comptox.epa.gov/dashboard/ (API docs: https://comptox.epa.gov/ctx-api/docs/)
