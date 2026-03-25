---
name: tooluniverse-chemical-safety
description: Comprehensive chemical safety and toxicology assessment integrating ADMET-AI predictions, CTD toxicogenomics, FDA label safety data, DrugBank safety profiles, and STITCH chemical-protein interactions. Performs predictive toxicology (AMES, DILI, LD50, carcinogenicity), organ/system toxicity profiling, chemical-gene-disease relationship mapping, regulatory safety extraction, and environmental hazard assessment. Use when asked about chemical toxicity, drug safety profiling, ADMET properties, environmental health risks, chemical hazard assessment, or toxicogenomic analysis.
---

# Chemical Safety & Toxicology Assessment

Comprehensive chemical safety analysis integrating predictive AI models, curated toxicogenomics databases, regulatory safety data, and chemical-biological interaction networks.

## When to Use This Skill

**Triggers**:
- "Is this chemical toxic?" / "Assess the safety profile of [drug/chemical]"
- "What are the ADMET properties of [SMILES]?"
- "What genes does [chemical] interact with?" / "What diseases are linked to [chemical] exposure?"
- "Drug safety assessment" / "Environmental health risk" / "Chemical hazard profiling"

**Use Cases**:
1. **Predictive Toxicology**: AI-predicted endpoints (AMES, DILI, LD50, carcinogenicity, hERG) via SMILES
2. **ADMET Profiling**: Absorption, distribution, metabolism, excretion, toxicity
3. **Toxicogenomics**: Chemical-gene-disease mapping from CTD
4. **Regulatory Safety**: FDA label warnings, contraindications, adverse reactions
5. **Drug Safety**: DrugBank safety + FDA labels combined
6. **Chemical-Protein Interactions**: STITCH-based interaction networks
7. **Environmental Toxicology**: Chemical-disease associations for contaminants

---

## KEY PRINCIPLES

1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Tool parameter verification** - Verify params via `get_tool_info` before calling unfamiliar tools
3. **Evidence grading** - Grade all safety claims by evidence strength (T1-T4)
4. **Citation requirements** - Every toxicity finding must have inline source attribution
5. **Mandatory completeness** - All sections must exist with data or explicit "No data" notes
6. **Disambiguation first** - Resolve compound identity (name -> SMILES, CID, ChEMBL ID) before analysis
7. **Negative results documented** - "No toxicity signals found" is data; empty sections are failures
8. **Conservative risk assessment** - When evidence is ambiguous, flag as "requires further investigation"
9. **English-first queries** - Always use English chemical/drug names in tool calls

---

## Evidence Grading System (MANDATORY)

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|----------|
| **T1** | [T1] | Direct human evidence, regulatory finding | FDA boxed warning, clinical trial toxicity |
| **T2** | [T2] | Animal studies, validated in vitro | Nonclinical toxicology, AMES positive, animal LD50 |
| **T3** | [T3] | Computational prediction, association data | ADMET-AI prediction, CTD association |
| **T4** | [T4] | Database annotation, text-mined | Literature mention, unvalidated database entry |

Evidence grades MUST appear in: Executive Summary, Toxicity Predictions, Regulatory Safety, Chemical-Gene Interactions, Risk Assessment.

---

## Core Strategy: 8 Research Phases

```
Chemical/Drug Query
|
+-- PHASE 0: Compound Disambiguation (ALWAYS FIRST)
|   Resolve name -> SMILES, PubChem CID, ChEMBL ID, formula, weight
|
+-- PHASE 1: Predictive Toxicology (ADMET-AI)
|   AMES, DILI, ClinTox, carcinogenicity, LD50, hERG, skin reaction
|   Stress response pathways, nuclear receptor activity
|
+-- PHASE 2: ADMET Properties
|   BBB penetrance, bioavailability, clearance, CYP interactions, physicochemical
|
+-- PHASE 3: Toxicogenomics (CTD)
|   Chemical-gene interactions, chemical-disease associations
|
+-- PHASE 4: Regulatory Safety (FDA Labels)
|   Boxed warnings, contraindications, adverse reactions, nonclinical tox
|
+-- PHASE 5: Drug Safety Profile (DrugBank)
|   Toxicity data, contraindications, drug interactions
|
+-- PHASE 6: Chemical-Protein Interactions (STITCH)
|   Direct binding, off-target effects, interaction confidence
|
+-- PHASE 7: Structural Alerts (ChEMBL)
|   PAINS, Brenk, Glaxo structural alerts
|
+-- SYNTHESIS: Integrated Risk Assessment
    Risk classification, evidence summary, data gaps, recommendations
```

See **phase-procedures-detailed.md** for complete tool parameters, decision logic, output templates, and fallback strategies for each phase.

---

## Tool Summary by Phase

### Phase 0: Compound Disambiguation
- `PubChem_get_CID_by_compound_name` (`name`: str)
- `PubChem_get_compound_properties_by_CID` (`cid`: int)
- `ChEMBL_get_molecule` (if ChEMBL ID available)

### Phase 1: Predictive Toxicology
> **Dependency**: ADMET-AI tools require `pip install tooluniverse[ml]`. If unavailable, skip to Phase 3 and use CTD + PubChemTox as alternatives.

- `ADMETAI_predict_toxicity` (`smiles`: list[str]) - AMES, DILI, ClinTox, LD50, hERG, etc.
- `ADMETAI_predict_stress_response` (`smiles`: list[str])
- `ADMETAI_predict_nuclear_receptor_activity` (`smiles`: list[str])

### Phase 2: ADMET Properties
- `ADMETAI_predict_BBB_penetrance` / `_bioavailability` / `_clearance_distribution` / `_CYP_interactions` / `_physicochemical_properties` / `_solubility_lipophilicity_hydration` (all take `smiles`: list[str])

### Phase 3: Toxicogenomics
- `CTD_get_chemical_gene_interactions` (`input_terms`: str) — chemical name, returns gene interactions across species
- `CTD_get_chemical_diseases` (`input_terms`: str) — chemical-disease associations with evidence type

### Phase 3.5: PubChem Toxicity Data
- `PubChemTox_get_toxicity_values` (`cid`: int) — LD50, LC50, NOAEL reference values
- `PubChemTox_get_ghs_classification` (`cid`: int) — GHS hazard classification and pictograms
- `PubChemTox_get_carcinogen_classification` (`cid`: int) — NTP/IARC carcinogenicity assessments
- `PubChemTox_get_acute_effects` (`cid`: int) — acute toxicity by route/species
- `PubChemTox_get_toxicity_summary` (`cid`: int) — integrated toxicity overview

### Phase 3.6: Adverse Outcome Pathways
- `AOPWiki_list_aops` (`keyword`: str) — search for relevant AOPs by chemical/mechanism
- `AOPWiki_get_aop` (`aop_id`: int) — full AOP detail: MIE, key events, adverse outcome

### Phase 4: Regulatory Safety (for pharmaceuticals only)
> **Environmental chemicals**: Skip Phases 4-5 (no FDA labels/DrugBank). Use CTD + PubChemTox + AOPWiki instead.

- `FDA_get_boxed_warning_info_by_drug_name` / `_contraindications_` / `_adverse_reactions_` / `_warnings_` (all take `drug_name`: str)

### Phase 5: Drug Safety (for pharmaceuticals only)
- `drugbank_get_safety_by_drug_name_or_drugbank_id` (`query`, `case_sensitive`, `exact_match`, `limit` - all 4 required)

### Phase 6: Chemical-Protein Interactions
- `STITCH_get_chemical_protein_interactions` (`identifiers`: list[str], `species`: int)
- **Fallback** (if STITCH fails for industrial chemicals): `STRING_get_interaction_partners` for key target genes (e.g., ESR1 for endocrine disruptors)
- `DGIdb_get_drug_gene_interactions` (`genes`: list[str]) — for target druggability context

### Phase 7: Structural Alerts
- `ChEMBL_search_compound_structural_alerts` (`molecule_chembl_id`: str)

---

## Risk Classification Matrix

| Risk Level | Criteria |
|-----------|----------|
| **CRITICAL** | FDA boxed warning OR multiple [T1] toxicity findings OR active DILI + active hERG |
| **HIGH** | FDA warnings OR [T2] animal toxicity OR multiple active ADMET endpoints |
| **MEDIUM** | Some [T3] predictions positive OR CTD disease associations OR structural alerts |
| **LOW** | All ADMET endpoints negative AND no FDA/DrugBank flags AND no CTD concerns |
| **INSUFFICIENT DATA** | Fewer than 3 phases returned data |

---

## Report Structure

```
# Chemical Safety & Toxicology Report: [Compound Name]
**Generated**: YYYY-MM-DD | **SMILES**: [...] | **CID**: [...]

## Executive Summary (risk classification + key findings, all graded)
## 1. Compound Identity (disambiguation table)
## 2. Predictive Toxicology (ADMET-AI endpoints)
## 3. ADMET Profile (absorption, distribution, metabolism, excretion)
## 4. Toxicogenomics (CTD chemical-gene-disease)
## 5. Regulatory Safety (FDA label data)
## 6. Drug Safety Profile (DrugBank)
## 7. Chemical-Protein Interactions (STITCH network)
## 8. Structural Alerts (ChEMBL)
## 9. Integrated Risk Assessment (classification, evidence summary, gaps, recommendations)
## Appendix: Methods and Data Sources
```

See **report-templates.md** for full section templates with example tables.

---

## Mandatory Completeness Checklist

- [ ] Phase 0: Compound disambiguated (SMILES + CID minimum)
- [ ] Phase 1: At least 5 toxicity endpoints or "prediction unavailable"
- [ ] Phase 2: ADMET A/D/M/E sections or "not available"
- [ ] Phase 3: CTD queried; results or "no data in CTD"
- [ ] Phase 4: FDA labels queried; results or "not FDA-approved"
- [ ] Phase 5: DrugBank queried; results or "not found"
- [ ] Phase 6: STITCH queried; results or "no data available"
- [ ] Phase 7: Structural alerts checked or "ChEMBL ID not available"
- [ ] Synthesis: Risk classification with evidence summary
- [ ] Evidence Grading: All findings have [T1]-[T4] annotations
- [ ] Data Gaps: Explicitly listed

---

## Common Use Patterns

1. **Novel Compound**: SMILES -> Phase 0 (resolve) -> Phase 1 (toxicity) -> Phase 2 (ADMET) -> Phase 7 (structural alerts) -> Synthesis
2. **Approved Drug Review**: Drug name -> All phases (0-7) -> Complete safety dossier
3. **Environmental Chemical**: Chemical name -> Phase 0 -> Phase 1-2 -> Phase 3 (CTD, key) -> Phase 6 (STITCH) -> Synthesis
4. **Batch Screening**: Multiple SMILES -> Phase 0 -> Phase 1-2 (batch) -> Comparative table -> Synthesis
5. **Toxicogenomic Deep-Dive**: Chemical + gene/disease interest -> Phase 0 -> Phase 3 (expanded CTD) -> Literature -> Synthesis

---

## Limitations

- **ADMET-AI**: Computational [T3]; should not replace experimental testing
- **CTD**: May lag behind latest literature by 6-12 months
- **FDA**: Only covers FDA-approved drugs; not applicable to environmental chemicals
- **DrugBank**: Primarily drugs; limited industrial chemical coverage
- **STITCH**: Lower score thresholds increase false positives
- **ChEMBL**: Structural alerts require ChEMBL ID; not all compounds have one
- **Novel compounds**: May only have ADMET-AI predictions (no database evidence)
- **SMILES validity**: Invalid SMILES cause ADMET-AI failures

---

## Reference Files

- **phase-procedures-detailed.md** - Complete tool parameters, decision logic, output templates, fallback strategies per phase
- **evidence-grading.md** - Evidence grading details and examples
- **report-templates.md** - Full report section templates with example tables
- **phase-details.md** - Additional phase context
- **test_skill.py** - Test suite

---

## Summary

**Total tools integrated**: 25+ tools across 6 databases (ADMET-AI, CTD, FDA, DrugBank, STITCH, ChEMBL)

**Best for**: Drug safety assessment, chemical hazard profiling, environmental toxicology, ADMET characterization, toxicogenomic analysis

**Outputs**: Structured markdown report with risk classification (Critical/High/Medium/Low), evidence grading [T1-T4], and actionable recommendations
