---
name: tooluniverse-clinical-guidelines
description: Search and retrieve clinical practice guidelines across 12+ authoritative sources including NICE, WHO, ADA, AHA/ACC, NCCN, SIGN, CPIC, CMA, CTFPHC, GIN, MAGICapp, PubMed, EuropePMC, TRIP, and OpenAlex. Use when users ask about clinical guidelines, treatment recommendations, standard of care, evidence-based medicine, or drug-gene dosing recommendations.
---

# Clinical Guidelines Search & Retrieval

## Guideline Hierarchy

Not all guidelines carry equal weight. Evaluate sources in this order:

1. **NICE and WHO** — Evidence-graded, regularly updated, rigorous systematic review process. NICE guidelines include explicit recommendation strength (e.g., "offer" vs "consider").
2. **Society guidelines (AHA, ADA, NCCN, SIGN)** — Expert-consensus panels within a specialty. May lag behind the latest evidence by 1-3 years. Strong within their domain but narrower scope.
3. **Aggregator databases (GIN, TRIP, OpenAlex)** — Index guidelines from multiple societies. Good for breadth and discovery, but you must verify the original source.
4. **Literature databases (PubMed, EuropePMC)** — Return guideline-related publications, not curated guideline text. Useful as a fallback, not a primary source.

**Always check publication date.** A 2015 guideline may be superseded by a 2024 update. When presenting results, include the year prominently and note if newer guidance may exist.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Search Strategy

### Step 1: Start Narrow, Then Broaden

1. Search the **condition name + "guideline"** in NICE, TRIP, and GIN simultaneously (parallel calls).
2. If the question targets a specialty, add the society tool: AHA for cardiology, ADA for diabetes, NCCN for oncology, CPIC for pharmacogenomics.
3. If initial searches return nothing, broaden to the disease category (e.g., "heart failure" instead of "HFpEF with SGLT2 inhibitors").
4. If society-specific tools fail, fall back to PubMed/EuropePMC with `[condition] guideline [year]`.

### Step 2: Search at Least 3 Sources

Always query a minimum of 3 databases to catch guidelines that one source may miss. Prioritize: **NICE > GIN > TRIP > Society-specific > Literature databases**.

### Step 3: Retrieve Full Text When Available

After identifying relevant guidelines from search results, use full-text tools to get recommendation details before synthesizing.

---

## Diagnostic Test Selection Reasoning

When a clinical question asks "which test should be ordered?" or "what is the most appropriate next diagnostic step?", apply this reasoning framework BEFORE searching guidelines.

### Step 1: What Is the Clinical Question Actually Asking?

Diagnostic tests serve different purposes. Identify which one the question demands:
- **Screening**: Detect disease in an asymptomatic population. Prioritize SENSITIVITY (minimize false negatives). Example: ANA for SLE screening.
- **Confirmation**: Confirm a suspected diagnosis. Prioritize SPECIFICITY (minimize false positives). Example: anti-dsDNA or anti-Smith for SLE confirmation.
- **Differentiation**: Distinguish between two diagnoses that look similar. Choose the test that is POSITIVE in one and NEGATIVE in the other. Example: ASO titers to distinguish PSGN from SLE nephritis (both have low complement and hematuria, but only PSGN has elevated ASO).
- **Staging/Prognosis**: Determine disease severity after diagnosis is established. Example: renal biopsy ISN/RPS class for lupus nephritis.
- **Monitoring**: Track response to treatment. Example: anti-dsDNA titers and complement levels in SLE.

### Step 2: Match the Test to the Diagnostic Gap

Ask: "What piece of information am I MISSING that would change management?"

### Step 3: Sensitivity vs Specificity Decision Matrix

| Scenario | Prioritize | Reasoning |
|----------|-----------|-----------|
| Ruling OUT a dangerous condition | High sensitivity | A negative result reliably excludes the disease |
| Confirming before invasive treatment | High specificity | A positive result reliably confirms the disease |
| Differentiating two similar conditions | Test unique to one | Choose marker present in condition A but absent in condition B |
| Emergency with life-threatening DDx | Fastest available test | Speed trumps perfect accuracy in acute settings |

### Step 4: Common Test Selection Pitfalls

1. **Ordering a test that is positive in BOTH conditions on the differential** — C3/C4 is low in both SLE and PSGN; it does not differentiate. Always ask: "Would this test result change my differential?"
2. **Ordering a screening test when a confirmatory test is needed** — ANA is sensitive but not specific for SLE. If you already suspect SLE, order anti-dsDNA or anti-Smith (specific).
3. **Skipping the simple test for the exotic one** — ASO titers are cheap and fast. Do not jump to renal biopsy before checking whether streptococcal infection explains the presentation.
4. **Forgetting temporal context** — PSGN complement normalizes in 6-8 weeks; SLE complement stays persistently low. A single complement level is less useful than a trend.
5. **Ignoring pre-test probability** — A test with 95% specificity still has a 50% false-positive rate if the pre-test probability is only 5%. Consider the clinical picture first.

---

## Lab Test Interpretation Strategy

- Always consider **pre-test probability** before interpreting any result. A positive test in a low-prevalence population has a high false-positive rate regardless of test accuracy.
- **SnNOut**: A highly **Se**nsitive test, when **N**egative, rules **Out** the disease. Use sensitive tests for screening.
- **SpPIn**: A highly **Sp**ecific test, when **P**ositive, rules **In** the disease. Use specific tests for confirmation.
- For **conflicting results** (e.g., one test positive, another negative): repeat the discordant test, order a different confirmatory test, or re-evaluate the clinical picture and pre-test probability.
- **Likelihood ratios** trump sensitivity/specificity alone. LR+ >10 or LR- <0.1 meaningfully shift post-test probability.

---

## Surgical Decision Making

- **Indications**: Determine whether surgery is necessary. Absolute indications (e.g., perforated viscus, acute limb ischemia) require immediate action; relative indications (e.g., symptomatic gallstones) allow shared decision-making.
- **Timing**: Emergent (within minutes-hours, life/limb threat), urgent (within 24-72 hours, deterioration risk), elective (scheduled, optimized pre-operatively).
- **Approach**: Choose the least invasive option that achieves the therapeutic goal. Laparoscopic before open, endovascular before surgical, unless contraindicated by anatomy or urgency.

---

## Applying Guidelines to Patients

Guidelines give **population-level recommendations**. When presenting findings:

1. **Cite the source explicitly** — "Per the 2024 ADA Standards of Care, Section 9..." not "guidelines recommend..."
2. **Note patient-specific modifiers** — Comorbidities, drug interactions, renal/hepatic function, age, pregnancy, and patient preferences may all change the recommendation.
3. **Flag when evidence is weak** — Grade D / expert consensus recommendations should be presented differently from Grade A / high-confidence ones.
4. **Identify conflicts between guidelines** — When NICE and ADA disagree, present both positions and note the discrepancy.
5. **State limitations** — If the patient's scenario falls outside the guideline's studied population, say so explicitly.

---

## Tool Workflow

### General Guideline Search (Parallel Calls)

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `NICE_Clinical_Guidelines_Search` | `query`, `limit` (both required) | Best general source; returns list directly |
| `GIN_Guidelines_Search` | `query`, `limit` (both required) | Best multi-society aggregator |
| `TRIP_Database_Guidelines_Search` | `query`, `limit`, `search_type='guidelines'` (all required) | Must include search_type |
| `WHO_Guidelines_Search` | `query`, `limit` | Limited topic filtering; may return unrelated WHO docs |
| `CMA_Guidelines_Search` | `query`, `limit` | Canadian guidelines |
| `SIGN_search_guidelines` | `query` (NOT `q`), `limit` | Scottish/UK |
| `CTFPHC_search_guidelines` | `query` (NOT `q`), `limit` | Canadian prevention |
| `OpenAlex_Guidelines_Search` | `query`, `limit`, optional `year_from`/`year_to` | Academic publications |
| `EuropePMC_Guidelines_Search` | `query`, `limit` | Loosely relevant; use for discovery |
| `PubMed_Guidelines_Search` | `query`, `limit`, optional `api_key` | Literature fallback |

All general search tools return **lists directly** — access as `result[0]['title']`.

### Society-Specific Tools

**ADA (Diabetes)**
- `ADA_list_standards_sections()` — No params. Lists all sections of ADA Standards of Care.
- `ADA_search_standards(query, limit)` — Use broad medical terms, not specific drug names.
- `ADA_get_standards_section(section_number)` — Returns section abstract only.

**AHA/ACC (Cardiology)**
- `AHA_ACC_search_guidelines(query, limit)` — Search AHA/ACC guidelines.
- `AHA_list_guidelines(limit)` / `ACC_list_guidelines(limit)` — List recent.
- `AHA_ACC_get_guideline(pmid)` — Full text via PMC.

**NCCN (Oncology)**
- `NCCN_list_patient_guidelines(limit)` — Field is `cancer_type`, NOT `title`.
- `NCCN_search_guidelines(query, limit)` — Returns JNCCN abstracts, not proprietary text.
- `NCCN_get_patient_guideline(url)` — Pass full URL string, NOT an integer ID.

**MAGICapp (Living Guidelines)**
- `MAGICapp_list_guidelines(limit)` — Returns **dict**: use `r.get('data', [])`. Field is `name`, NOT `title`.
- `MAGICapp_get_guideline(guideline_id)` / `MAGICapp_get_recommendations(guideline_id)` / `MAGICapp_get_sections(guideline_id)`

**NCI** — Catalogs research tools/datasets, NOT clinical guidelines. Use `q` (not `query`), `size` (not `limit`). Access: `r.get('data',{}).get('results',[])`.

### Pharmacogenomics (CPIC)

All CPIC tools return **dict-wrapped**: use `r.get('data', [])`.

**Workflow:**
1. `CPIC_get_gene_info(genesymbol='CYP2D6')` — Gene overview
2. `CPIC_get_gene_drug_pairs(genesymbol='CYP2D6')` — All drugs with CPIC levels (A=strongest)
3. `CPIC_list_guidelines(limit=50)` — Find `guidelineId` for target gene+drug pair
4. `CPIC_get_recommendations(guideline_id=N)` — Dosing recommendations (deduplicate by phenotype)
5. `CPIC_get_alleles(genesymbol='CYP2D6')` — Use `clinicalfunctionalstatus` (NOT `functionalstatus`)

**Gotchas:**
- `CPIC_get_recommendations` takes `guideline_id` (integer), NOT `genesymbol`
- `CPIC_search_gene_drug_pairs` requires PostgREST syntax: `genesymbol='eq.CYP2D6'`
- Deduplicate recommendations by phenotype before presenting (many duplicate records per allele combo)

### Full-Text Retrieval

| Source | Tool | Input |
|--------|------|-------|
| NICE | `NICE_Guideline_Full_Text(url)` | URL from search results; try `.../chapter/Recommendations` |
| WHO | `WHO_Guideline_Full_Text(url)` | May return PDF link, not full text |
| AHA/ACC | `AHA_ACC_get_guideline(pmid)` | PMID from search results |
| NCCN | `NCCN_get_patient_guideline(url)` | Full URL from list results |

---

## Evidence Grading Quick Reference

| System | Strong | Moderate | Weak/Expert Opinion |
|--------|--------|----------|-------------------|
| ADA | Grade A | Grade B/C | Grade E (consensus) |
| AHA/ACC | Class I | Class IIa/IIb | Class III |
| SIGN | Strong | Conditional | Good practice point |
| CPIC | Level A | Level B | Level C/D |
| NICE | "Offer" (strong) | "Consider" (weaker) | Research recommendation |

---

## Fallback Strategy

- NICE returns empty -> try TRIP or GIN
- ADA returns 0 results -> broaden terms (`'pharmacologic approaches'` not `'metformin first-line'`)
- WHO returns irrelevant results -> skip WHO, use GIN or EuropePMC
- CPIC returns no recommendations -> present gene-drug pairs with CPIC levels as proxy
- TRIP returns 403/gated PDFs -> note limited access, try alternative sources

---

## Synthesis Template

```
# Clinical Guidelines: [Topic]

## Summary
[2-3 sentences: what do the guidelines agree on? Where do they diverge?]

## Key Recommendations
### [Source 1 — Organization, Year]
- Recommendation text [Evidence grade]
- URL

### [Source 2 — Organization, Year]
- Recommendation text [Evidence grade]

## Patient-Specific Considerations
[Comorbidities, interactions, or population factors that modify these recommendations]

## Pharmacogenomics (if applicable)
[CPIC phenotype-to-dosing table, deduplicated]

## References
[All source URLs]
```

---

## Known Limitations

- **WHO_Guidelines_Search**: Unreliable topic filtering; supplement with GIN for international guidelines.
- **NCI_search_cancer_resources**: Research tool catalog, NOT clinical guidelines.
- **NICE_Guideline_Full_Text**: Overview page only; sub-pages may need direct URL.
- **SIGN**: No full-text tool; PDFs only.
- **ADA_get_standards_section**: Abstract only, not full PMC text.
- **NCCN_search_guidelines**: JNCCN abstracts, not proprietary NCCN guideline content.

---

## Clinical MCQ Reasoning Framework

### 1. Systematic Differential Diagnosis Protocol

- List ALL findings (vital signs, labs, imaging, history)
- For each answer choice, score how many findings it explains
- The correct answer usually explains the MOST findings
- Diagnose from the symptom cluster FIRST, then check if ancillary findings (imaging, incidental labs) are consistent or incidental
- Don't anchor on the most dramatic finding -- consider the full picture

### 2. Critical Clinical Decision Rules

**Spine triage -- use TLICS scoring, not gestalt:**
- TLICS dimensions: Morphology (compression=1, burst=2, translation/rotation=3, distraction=4) + PLC integrity (intact=0, suspected=2, injured=3) + Neurologic status (intact=0, root=2, cord complete=2, cord incomplete=3, cauda equina=3)
- Neurologic deficit is the HIGHEST priority component -- always triaged first
- When a named scoring system exists (TLICS, CURB-65, Wells, etc.), always apply it instead of intuitive severity ranking

**Hemorrhagic shock -- fluid selection:**
- IV crystalloid (NS or LR) is first-line for ALL classes
- Class III-IV: add blood products, but crystalloid still comes first

**Brown-Sequard -- lesion level determination:**
- Lesion level = the HIGHEST level of ipsilateral motor/sensory loss, NOT the level where contralateral pain/temp loss begins
- Contralateral pain/temp loss starts 1-2 segments BELOW the lesion (fibers ascend in Lissauer's tract before crossing)

**Post-valve surgery monitoring:**
- Mechanical valves: lifelong warfarin (INR 2.5-3.5 mitral, 2.0-3.0 aortic)
- When answer choices include both "prescribe anticoagulant" and "monitor PT/INR": monitoring PT/INR is MORE specific because it implies ongoing anticoagulation management, not just prescribing
- Verify pharmacological terminology in answer choices -- if a conceptually correct answer uses a non-existent drug class name, consider whether "none of the above" is more appropriate

**Incidental findings:**
- Do not let an incidental imaging finding override a coherent clinical syndrome. When the clinical picture fits one diagnosis and the imaging finding is commonly benign (e.g., vertebral hemangiomas found on 10-12% of CTs), prioritize the clinical syndrome.

**Post-surgical complications:**
- Always include perioperative MI in the differential for post-surgical hypoxemia, especially after major surgery with blood loss
- Complications can present days to weeks post-op — do not assume only acute reactions

### 3. Answer Verification Checklist

- Does my answer explain ALL abnormal findings?
- Is there an answer choice that explains findings my choice doesn't?
- Am I choosing based on the most common condition, or the condition that best fits THIS patient?
- Have I re-read the question stem for qualifiers like "most likely", "next best step", "initial"?
- If I calculated a specific value (lesion level, score), is it actually among the choices? If not, consider "none of the above"
- Are all pharmacological terms in my chosen answer real and correctly named?

### 4. Treatment Protocol Verification

- Before recommending a specific drug: check contraindications, drug interactions, and patient-specific factors (renal/hepatic function, age, pregnancy, allergies)
- For infectious disease: verify the organism-drug sensitivity -- not all antibiotics work for all organisms. Geographic endemic patterns matter (e.g., Coccidioidomycosis in SW US, not Melioidosis)
- For emergency medicine: follow ATLS/ACLS protocols step by step. Do not skip crystalloid resuscitation for pharmacologic interventions
- For oncology: verify NCCN category and specific biomarker requirements before recommending targeted therapy
- For cardiovascular risk: high-dose statin is first-line for established ASCVD -- do not discontinue metformin or other agents as a substitute for lipid management
- For psychiatric pharmacotherapy: check herb-drug and supplement-drug interactions
- For seizure management: distinguish dietary causes from drug interaction causes -- breakthrough seizures on ketogenic diet may require medication change, not diet adjustment
- When multiple interventions are listed: verify the correct SEQUENCE (e.g., stabilize airway before pharmacotherapy, rule out reversible causes before chronic management)

### 5. Pediatric Medicine Traps

- Fluid calculations: use Holliday-Segar formula (100/50/20 mL/kg/day for first 10/next 10/each subsequent kg)
- Dehydration correction: deficit volume = weight (kg) x % dehydration x 10 (mL)
- Neonatal presentations: consider congenital vs acquired causes first
- BSA-based dosing: verify BSA calculation (Mosteller: sqrt(height_cm x weight_kg / 3600)), then dose = mg/m2 x BSA. Always multiply by number of treatment days for total dose
- Double-check arithmetic: pediatric dosing errors are the most common clinical MCQ trap (e.g., 25 mg/m2 x 0.8 m2 = 20 mg/day, NOT 43 mg)
