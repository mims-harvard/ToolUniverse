---
name: tooluniverse-drug-drug-interaction
description: Comprehensive drug-drug interaction (DDI) prediction and risk assessment. Analyzes interaction mechanisms (CYP450, transporters, pharmacodynamic), severity classification, clinical evidence grading, and provides management strategies. Supports single drug pairs, polypharmacy analysis (3+ drugs), and alternative drug recommendations. Use when users ask about drug interactions, medication safety, polypharmacy risks, or need DDI assessment for clinical decision support.
---

# Drug-Drug Interaction Prediction & Risk Assessment

Systematic analysis of drug-drug interactions with evidence-based risk scoring, mechanism identification, and clinical management recommendations.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create DDI_risk_report.md FIRST, then populate progressively
2. **Bidirectional analysis** - Always analyze A→B and B→A interactions (effects may differ)
3. **Evidence grading** - Grade all DDI claims by evidence quality (★★★ FDA label, ★★☆ clinical study, ★☆☆ theoretical)
4. **Risk scoring** - Multi-dimensional scoring (0-100) combining mechanism + severity + clinical evidence
5. **Patient safety focus** - Provide actionable clinical guidance, not just theoretical interactions
6. **Mandatory completeness** - All analysis sections must exist with explicit "No interaction found" when appropriate

---

## LOCAL PHARMACOLOGY REFERENCE (USE FIRST)

Before querying any external database, consult the local reference script for instant answers on CYP/UGT roles and known critical interactions:

```
scripts/pharmacology_ref.py   (no external dependencies, runs offline)

# Q927 pattern — valproate + lamotrigine:
python scripts/pharmacology_ref.py --type interaction --drug1 "valproate" --drug2 "lamotrigine"

# What does a drug do to UGT enzymes?
python scripts/pharmacology_ref.py --type ugt_inhibitor --drug "valproate"

# What enzymes metabolise a drug?
python scripts/pharmacology_ref.py --type ugt_substrate --drug "lamotrigine"
python scripts/pharmacology_ref.py --type cyp_substrate --drug "warfarin"

# Which drugs inhibit / induce a specific CYP?
python scripts/pharmacology_ref.py --type cyp_inhibitor --enzyme "CYP3A4"
python scripts/pharmacology_ref.py --type cyp_inducer  --enzyme "CYP2C9"

# Narrow therapeutic index checklist:
python scripts/pharmacology_ref.py --type narrow_ti

# All known interactions for one drug:
python scripts/pharmacology_ref.py --type all_interactions --drug "lamotrigine"
```

**Covered interactions include** (severity / mechanism):
| Pair | Severity | Key mechanism |
|------|----------|---------------|
| valproate + lamotrigine | **Major** | UGT1A4 inhibition → 2× lamotrigine levels + SJS risk |
| carbamazepine + lamotrigine | Major | UGT1A4 induction → 50% ↓ lamotrigine |
| oral contraceptives + lamotrigine | Major | UGT1A4 induction → 50% ↓ lamotrigine |
| valproate + phenytoin | Major | CYP2C9 inhibition + protein displacement |
| carbamazepine + valproate | Moderate | Epoxide hydrolase inhibition → toxic metabolite ↑ |
| simvastatin + ketoconazole | **Contraindicated** | CYP3A4 inhibition → rhabdomyolysis |
| simvastatin + clarithromycin | Contraindicated | CYP3A4 inhibition → rhabdomyolysis |
| rifampin + warfarin | Major | CYP2C9 induction → INR collapse |
| amiodarone + warfarin | Major | CYP2C9 inhibition → INR rise |
| clopidogrel + omeprazole | Moderate | CYP2C19 inhibition → reduced antiplatelet activation |
| quinidine + digoxin | Major | P-gp inhibition → 2× digoxin levels |
| lithium + NSAIDs | Major | Reduced renal clearance → lithium toxicity |
| fluoxetine + MAOIs | Contraindicated | Serotonin syndrome |

The script also covers UGT2B7 substrates (morphine, zidovudine) inhibited by valproate, UGT1A1 induction by rifampin, and the complete narrow therapeutic index list with monitoring parameters.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first (PubMed, UniProt, ChEMBL, ClinVar, etc.) rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

## New Symptom After New Medication: First-Line Reasoning

When a patient develops NEW symptoms after starting a new medication, the FIRST question is: could the new drug be interacting with an existing medication? Specifically check: (1) Does the new drug inhibit metabolism of an existing drug? (2) Does the new drug have additive pharmacodynamic effects?

---

## When to Use This Skill

Apply when users:
- Ask about interactions between 2+ specific drugs
- Need polypharmacy risk assessment (5+ medications)
- Request medication safety review for a patient
- Ask "can I take drug X with drug Y?"
- Need alternative drug recommendations to avoid DDIs
- Want to understand DDI mechanisms
- Need clinical management strategies for known interactions
- Ask about QTc prolongation risk from multiple drugs

---

## Clinical Reasoning Framework

Before querying any database, apply this reasoning framework to predict interactions mechanistically.

### The Perpetrator-Victim Model

In every drug interaction, identify two roles:
- **PERPETRATOR**: the drug causing the change (the inhibitor, inducer, or pharmacodynamic amplifier)
- **VICTIM**: the drug being affected (the one whose levels or effects change)

For each drug pair, ask these questions in order:

1. **Does the perpetrator change how the victim is absorbed, distributed, metabolized, or eliminated?** If yes, this is a pharmacokinetic interaction. Determine which enzyme or transporter is involved (CYP450, UGT, P-gp, OATP, etc.).
2. **Is the perpetrator an inhibitor or an inducer of that pathway?**
   - Inhibitor → victim levels go UP → predict increased efficacy or toxicity
   - Inducer → victim levels go DOWN → predict reduced efficacy or therapeutic failure
3. **What happens clinically when the victim's level changes?** Predict the downstream consequence: toxicity from supratherapeutic levels, or treatment failure from subtherapeutic levels.
4. **Always check the reverse direction.** Analyze B→A as well as A→B. The perpetrator-victim relationship may be asymmetric or bidirectional.

Special case -- **Prodrugs**: If the victim is a prodrug that requires metabolic activation, inhibiting its activating enzyme reduces efficacy (not toxicity). Inducing its activating enzyme may increase efficacy or toxicity of the active metabolite.

---

### Phase II Metabolism: Glucuronidation Interactions (UGT Enzymes)

Most DDI reasoning focuses on CYP450 (Phase I metabolism), but **Phase II conjugation reactions — especially glucuronidation via UGT enzymes — cause some of the most dangerous drug interactions**. These are frequently missed because agents default to CYP-centric reasoning.

**Core principle**: UGT enzymes (UGT1A4, UGT2B7, UGT1A1, etc.) conjugate drugs with glucuronic acid for renal elimination. When a UGT inhibitor is co-administered with a UGT substrate, the substrate accumulates because its primary elimination pathway is blocked.

**The valproate + lamotrigine paradigm (IDX 927 pattern):**
1. Lamotrigine is primarily metabolized by **UGT1A4** glucuronidation (>90% of elimination).
2. Valproate is a potent **UGT1A4 inhibitor**.
3. Co-administration doubles lamotrigine levels (t1/2 increases from ~25h to ~60h).
4. Clinical consequence: **Stevens-Johnson syndrome (SJS) / toxic epidermal necrolysis (TEN)** — a life-threatening dermatologic emergency.
5. Mechanism: **inhibition of lamotrigine glucuronidation** — NOT a CYP interaction.
6. Management: When adding valproate to lamotrigine, HALVE the lamotrigine dose. Titrate slowly.

**Other critical UGT interactions:**
- **Valproate + morphine/zidovudine**: Valproate inhibits UGT2B7 → increased morphine/zidovudine levels
- **Valproate + phenytoin**: Dual mechanism — CYP2C9 inhibition + protein binding displacement → unpredictable phenytoin levels
- **Carbamazepine + lamotrigine**: Carbamazepine INDUCES UGT1A4 → lamotrigine levels DROP by ~50% (opposite direction from valproate)
- **Oral contraceptives + lamotrigine**: Ethinylestradiol induces UGT1A4 → lamotrigine levels drop; when OCP stopped (pill-free week), lamotrigine rebounds
- **Rifampin + many UGT substrates**: Rifampin induces UGT1A1, UGT2B7 → decreased levels of morphine, bilirubin conjugation increased

**Reasoning algorithm for UGT interactions:**
1. Is the victim drug primarily cleared by glucuronidation? (Check: lamotrigine, morphine, lorazepam, zidovudine, bilirubin)
2. Is the perpetrator a UGT inhibitor (valproate, probenecid, atazanavir) or inducer (carbamazepine, rifampin, phenytoin, OCP)?
3. Predict direction: inhibitor → victim levels UP; inducer → victim levels DOWN
4. Assess clinical significance: narrow therapeutic index victims (lamotrigine, morphine) are HIGH risk

Use `scripts/pharmacology_ref.py --type ugt_inhibitor --drug "[drug]"` and `--type ugt_substrate --drug "[drug]"` for rapid UGT lookup.

### Enzyme Induction and Inhibition: Cascading Effects

When a patient is on 3+ drugs, interactions can cascade. A common pattern:

**Scenario**: Patient on Drug A (CYP3A4 substrate) + Drug B (CYP3A4 inducer) at steady state. Drug C (CYP3A4 inhibitor) is added.
- Drug B was keeping Drug A levels LOW (via induction).
- Drug C now inhibits CYP3A4 → Drug A levels RISE, but the magnitude depends on whether Drug C overcomes Drug B's induction.
- If Drug B is later STOPPED, Drug A levels rise FURTHER (induction wears off over 1-2 weeks while inhibition persists).

**Key reasoning principles for cascading effects:**
1. **Induction takes days to weeks to develop** (requires new enzyme protein synthesis) and **days to weeks to resolve** (enzyme protein must degrade). Plan dose adjustments PROSPECTIVELY.
2. **Inhibition is typically immediate** (competitive binding at enzyme active site). Dose adjustment needed at the time of co-administration.
3. **When an inducer is stopped**, all drugs that were dose-adjusted upward to compensate for the induction now become SUPRATHERAPEUTIC. This is when toxicity appears — often 1-2 weeks after stopping the inducer.
4. **Multiple inhibitors of the same enzyme are NOT simply additive** — the strongest inhibitor dominates. But multiple inhibitors of DIFFERENT enzymes affecting the same victim drug can be synergistic.

### ADR Attribution: Which Mechanism Caused the Problem?

When a patient on multiple medications develops an adverse drug reaction:

1. **Timeline**: When did the ADR appear relative to the newest medication change? (hours = PK inhibition or PD; weeks = induction offset)
2. **Which drug is the likely VICTIM?** The victim is the drug whose toxicity profile matches the ADR. Seizures → check anticonvulsant levels. Bleeding → check anticoagulant levels.
3. **Which drug is the likely PERPETRATOR?** The perpetrator is the most recently added/changed drug, OR a recently STOPPED inducer.
4. **What is the mechanism?** Look up the victim's metabolic pathway (CYP? UGT? renal?). Then check if the perpetrator affects that pathway.
5. **Validate**: Does the predicted mechanism match the clinical magnitude? A moderate CYP inhibitor should cause a 2-3x level increase; a strong inhibitor 5x+. If the observed effect is much larger or smaller, reconsider the mechanism.

**Example (IDX 927)**: Elderly patient on lamotrigine develops seizures and rash after adding valproate.
- Victim = lamotrigine (the drug causing toxicity — SJS/rash, and paradoxical seizures from toxicity)
- Perpetrator = valproate (the newly added drug)
- Mechanism = UGT1A4 inhibition → lamotrigine glucuronidation blocked → 2x lamotrigine levels → SJS
- Answer: "Inhibition of lamotrigine glucuronidation" — NOT phenytoin hypersensitivity or CYP interaction

### Timeline Reasoning

Use the temporal pattern of symptoms to narrow the mechanism:

- **Symptoms within hours of adding the new drug** → Think pharmacokinetic inhibition (competitive, immediate onset) or direct pharmacodynamic interaction (additive receptor effects)
- **Symptoms emerging over 1-2 weeks** → Think enzyme induction (requires new protein synthesis, slow onset, slow offset)
- **Symptoms that appear regardless of timing** → Think pharmacodynamic interaction (both drugs independently act on the same receptor, pathway, or organ system)
- **Symptoms appearing days after stopping a drug** → Think inducer offset (enzyme levels returning to baseline, victim drug levels rising)

---

### The Three Questions

For any suspected drug interaction, classify it by asking:

**1. Is this pharmacokinetic?** (One drug changes the LEVEL of another)
- Mechanism: absorption changes, enzyme inhibition/induction, transporter competition, protein binding displacement, altered renal elimination
- Clue: measurable change in drug plasma concentration
- Action: check which metabolic enzymes and transporters are involved

**2. Is this pharmacodynamic?** (Both drugs act on the SAME SYSTEM)
- Additive/synergistic: both drugs push the same physiological effect in the same direction (e.g., sedation, bleeding, QTc prolongation, serotonin activity, hypoglycemia)
- Antagonistic: drugs push in opposite directions on the same target (e.g., a blocker vs. an agonist at the same receptor)
- Synergistic toxicity: different mechanisms converging on the same organ (e.g., one drug raises levels via PK while another damages the same tissue via PD)
- Electrolyte-mediated: one drug shifts electrolyte balance, sensitizing the patient to another drug's toxicity
- Clue: no change in plasma levels, but exaggerated or blunted clinical effect

**3. Is this pharmaceutical?** (Drugs interact BEFORE reaching the body)
- IV line incompatibility, chelation in the GI tract, pH-dependent degradation
- Clue: problem occurs at the point of administration, not after absorption

Most clinically significant interactions are pharmacokinetic, pharmacodynamic, or both simultaneously. Always consider mixed PK+PD interactions, which tend to be the most dangerous.

---

### Severity Reasoning

Assess severity by reasoning about the victim drug's properties, not by memorizing lists:

**Therapeutic index determines risk tolerance:**
- Narrow therapeutic index drugs (e.g., warfarin, lithium, digoxin, phenytoin, theophylline, cyclosporine, aminoglycosides) → even small level changes are clinically dangerous. Any PK interaction with these drugs is at least moderate severity.
- Wide therapeutic index drugs → moderate level changes (2-3x) are often tolerable. Severity depends on the magnitude of the change and the specific toxicity profile.

**Prodrug logic inverts the prediction:**
- Inhibiting activation of a prodrug = loss of efficacy, not toxicity. This is dangerous when the prodrug treats a life-threatening condition (e.g., antiplatelet therapy, cancer treatment).

**Severity classification process:**
- **Contraindicated**: Documented life-threatening toxicity. The combination should not be used.
- **Major**: High risk of serious harm or permanent damage. Avoid when alternatives exist; if unavoidable, requires intensive monitoring and dose adjustment with documented rationale.
- **Moderate**: May worsen the patient's condition or require additional treatment. Manageable with dose adjustment and increased monitoring frequency.
- **Minor**: Nuisance-level effects with limited clinical significance. Usually no dose change required.

**Management follows directly from the mechanism:**
- If the perpetrator is an inhibitor → reduce the victim's dose proportionally to inhibition strength, or substitute the perpetrator with a non-inhibiting alternative
- If the perpetrator is an inducer → increase the victim's dose (guided by therapeutic drug monitoring), or substitute the perpetrator; remember to readjust when the inducer is stopped
- If the interaction is pharmacodynamic → neither drug's dose fixes the problem; substitute one drug or add protective monitoring (e.g., ECG for QTc, INR for bleeding)

---

## Critical Workflow Requirements

### 1. Report-First Approach (MANDATORY)

**DO NOT** show intermediate tool outputs or search processes. Instead:

1. **Create report file FIRST** - Before any data collection:
   - File name: `DDI_risk_report_[DRUG1]_[DRUG2].md` (or `_polypharmacy.md` for 3+)
   - Initialize with all section headers
   - Add placeholder: `[Analyzing...]` in each section

2. **Apply clinical reasoning FIRST** - Before running tools, reason through:
   - CYP roles of each drug (substrate/inhibitor/inducer)
   - PD overlap (same receptor, same organ toxicity)
   - Flag high-risk combinations from the reference table

3. **Progressively update** - As database data is gathered:
   - Replace `[Analyzing...]` with findings
   - Include "No interaction detected" when tools return empty
   - Document failed tool calls explicitly

4. **Final deliverable** - Complete markdown report with recommendations

---

## Tool Workflow

### Phase 1: Drug Identification

1. Resolve generic names, ChEMBL IDs, DrugBank IDs
2. Identify drug class and mechanism of action for each drug
3. Apply CYP450 reasoning framework above BEFORE database queries

### Phase 2: PK Interaction Analysis

Query tools in this order:
1. `ChEMBL_get_drug_mechanisms` or `KEGG_get_drug` for CYP substrate/inhibitor/inducer data
2. `drugbank_get_drug_interactions_by_drug_name_or_id` for known transporter interactions (P-gp, OATP, OAT, OCT)
3. Cross-reference with PharmGKB for pharmacogenomic context

**Transporter interactions** (check when CYP analysis incomplete):
- P-glycoprotein (P-gp / ABCB1): substrates (digoxin, dabigatran, fexofenadine); inhibitors (amiodarone, cyclosporine, quinidine, verapamil); inducers (rifampin)
- OATP1B1: substrates (statins, methotrexate); inhibitors (cyclosporine, gemfibrozil)

### Phase 3: PD Interaction Analysis

1. Identify receptor targets for each drug
2. Check for overlapping receptor activity (additive/synergistic)
3. Check for opposing receptor activity (antagonistic)
4. Assess shared organ toxicity pathways

### Phase 4: Clinical Evidence Assessment

1. FDA label review via `DailyMed_get_spl_by_setid` - highest evidence tier
2. Clinical study data via `PubMed_search_articles` - second tier
3. Theoretical/mechanistic - flag clearly as ★☆☆

### Phase 5: Risk Scoring

Risk Score (0-100):
- Base score from severity: Major=60, Moderate=35, Minor=10
- Evidence modifier: FDA label +20, clinical study +10, theoretical +0
- Frequency modifier: Common (>10%) +10, Uncommon (1-10%) +5, Rare (<1%) +0
- Patient factor modifier: +5 per applicable high-risk factor

### Phase 6: Alternatives and Monitoring

For each Major/Contraindicated interaction:
1. Suggest specific alternative drugs that avoid the interaction mechanism
2. Provide dose adjustment recommendations if substitution not possible
3. Define monitoring parameters: which labs, which symptoms, how often

---

## Output Report Structure

1. Executive Summary (interaction severity, key risk)
2. Drug Profiles (class, mechanism, CYP roles)
3. PK Interactions (CYP, transporters, mechanisms)
4. PD Interactions (additive, synergistic, antagonistic)
5. Clinical Evidence (FDA label, studies, case reports)
6. Risk Score (0-100 with breakdown)
7. Management Recommendations (avoid / dose adjust / monitor)
8. Monitoring Plan (labs, timeline, thresholds)
9. Alternative Drugs (mechanism-free alternatives)
10. Patient Counseling Points

---

## Success Criteria

Before finalizing DDI report:

- All drug names resolved to standard identifiers
- CYP450 reasoning applied before database queries
- Bidirectional analysis completed (A→B and B→A)
- All mechanism types assessed (CYP, transporters, PD)
- FDA label warnings extracted
- Clinical literature searched
- Evidence grades assigned (★★★, ★★☆, ★☆☆)
- Risk score calculated (0-100)
- Severity classified (Contraindicated/Major/Moderate/Minor)
- Primary management recommendation provided
- Alternative drugs suggested
- Monitoring parameters defined
- Patient counseling points included
- All sections completed (no [Analyzing...] placeholders)
- Data sources cited throughout
