---
name: tooluniverse-drug-regulatory
description: >
  Drug regulatory and approval research -- FDA substance registry lookup, drug classification
  by ATC/EPC/MoA via RxClass, Orange Book generic availability and patent status, DailyMed
  label parsing (adverse reactions, dosing, contraindications), and clinical trial search.
  Use when users ask about FDA-approved drugs, drug regulatory status, generic availability,
  patent expiration, drug class membership, drug labeling, or substance identification.
triggers:
  - keywords: [FDA, Orange Book, generic drug, UNII, RxClass, ATC code, drug class, NDA, ANDA, patent, exclusivity, DailyMed, drug label, adverse reactions, regulatory, approval]
  - patterns: ["FDA approved", "generic available", "patent expiration", "drug class", "ATC code", "Orange Book", "DailyMed", "drug labeling", "UNII"]
---

# Drug Regulatory Research

Regulatory intelligence for drugs: identify FDA substances, classify drugs by therapeutic
category, check approval and generic status, retrieve label sections, and find clinical trials.

## When to Use

- "What is the FDA regulatory status of semaglutide?"
- "Is there a generic for Humira?"
- "What ATC class does metformin belong to?"
- "Get adverse reactions from the ibuprofen drug label"
- "When does the patent for Eliquis expire?"
- "List all drugs in the ACE inhibitor class"
- "Find clinical trials for a biosimilar of adalimumab"

## NOT for (use other skills instead)

- Drug-drug interactions -> Use `tooluniverse-drug-drug-interaction`
- Pharmacogenomics / dosing by genotype -> Use `tooluniverse-pharmacogenomics`
- Drug mechanism of action / target binding -> Use `tooluniverse-drug-mechanism-research`
- Drug repurposing / new indications -> Use `tooluniverse-drug-repurposing`

---

## Workflow Overview

```
Input (drug name / brand name / UNII)
  |
  v
Phase 1: Substance Identification  -- FDAGSRS_search_substances, FDAGSRS_get_substance
  |
  v
Phase 2: Drug Classification       -- RxClass_get_drug_classes, RxClass_find_classes
  |
  v
Phase 3: Approval & Generic Status -- FDA_OrangeBook_search_drug, FDA_OrangeBook_check_generic_availability
  |
  v
Phase 4: Patent & Exclusivity      -- FDA_OrangeBook_get_patent_info, FDA_OrangeBook_get_exclusivity
  |
  v
Phase 5: Label Parsing             -- DailyMed_parse_adverse_reactions, DailyMed_parse_dosing, etc.
  |
  v
Phase 6: Clinical Trials           -- search_clinical_trials
  |
  v
Phase 7: Pharmacovigilance         -- FAERS_count_reactions_by_drug_event (param: medicinalproduct)
  |
  v
Phase 8: Literature & Approval     -- PubMed_search_articles, OpenFDA_get_approval_history, RxNorm_get_drug_names
```

> **Supplementary tools** (not in core phases but useful):
> - `OpenFDA_get_approval_history` — full FDA submission/approval history (requires `operation` param)
> - `FAERS_count_reactions_by_drug_event` — top adverse events by report count (param: `medicinalproduct`, ALL CAPS)
> - `RxNorm_get_drug_names` — resolve drug to RXCUI and brand names
> - `drugbank_vocab_search` — DrugBank ID, CAS, UNII lookup
> - `PubMed_search_articles` — regulatory and clinical literature

---

## Key Identifiers

| Data Type | Format | Example |
|-----------|--------|---------|
| FDA substance | UNII (10 chars) | R16CO5Y76E (aspirin) |
| RxNorm drug | RXCUI (numeric string) | "41493" (metformin) |
| ATC code | Letter-digit hierarchy | A10BA02 (metformin) |
| NDA application | NDA###### | NDA020402 |
| ANDA application | ANDA###### | ANDA078516 |
| DailyMed label | SPL Set ID (UUID) | 030d9bca-a934-6ef9-... |

---

## Phase 1: Substance Identification (FDAGSRS)

**FDAGSRS_search_substances**: `query` (string REQUIRED -- drug name, UNII, InChIKey, or formula), `substance_class` (string, optional: "chemical"/"protein"/"nucleic acid"/"polymer"/"mixture"), `limit` (int, 1-50, default 10).
Returns `{status, data: {substances: [{unii, name, substance_class, status, cross_references: [{type, value}]}]}}`.
- `cross_references` contains DrugBank IDs, WHO-ATC codes, CAS numbers, CFR citations.
- Use to get the official UNII identifier before calling `FDAGSRS_get_substance`.

**FDAGSRS_get_substance**: `unii` (string REQUIRED, 10-char FDA UNII code).
Returns complete substance record including all synonyms, names, structure, and cross-references.
- Provides definitive list of all registered names (INN, USAN, brand, chemical).

**FDAGSRS_get_structure**: `unii` (string REQUIRED).
Returns `{status, data: {smiles, formula, inchikey, molfile, molecular_weight, stereochemistry, optical_activity}}`.
- Only works for chemical substances; returns error for biologics, mixtures, polymers.

```python
# Full substance lookup workflow
search = tu.tools.FDAGSRS_search_substances(query="semaglutide")
unii = search["data"]["substances"][0]["unii"]
full = tu.tools.FDAGSRS_get_substance(unii=unii)
```

---

## Phase 2: Drug Classification (RxClass)

**RxClass_get_drug_classes**: `drug_name` (string, drug name), `rxcui` (string, RxNorm RXCUI -- alternative to drug_name), `rela_source` (string, optional: "ATC"/"FDASPL"/"MESH"/"VA"), `limit` (int, default 20).
Returns `{status, data: {classes: [{class_id, class_name, class_type, rela}]}}`.
- Returns ALL classification systems unless `rela_source` filters to one.
- `class_type` values: "ATC1-4", "EPC" (FDA Established Pharmacologic Class), "MoA", "VA", "MESH".
- Use to find a drug's ATC code, pharmacological class, mechanism of action label.

**RxClass_find_classes**: `query` (string REQUIRED, keyword e.g., "beta blocker"), `class_type` (string, optional: "ATC1-4"/"EPC"/"MoA"), `limit` (int, default 20).
Returns matching drug classes with class IDs.
- Use when you need to find a class ID before calling `RxClass_get_class_members`.

**RxClass_get_class_members**: `class_id` (string REQUIRED, e.g., "M01AE"), `rela_source` (string, optional: "ATC"/"FDASPL"), `ttys` (string, optional: "IN" for ingredients), `limit` (int, default 50).
Returns all drug ingredients in the class with RXCUIs and names.
- `ttys="IN"` restricts to active ingredient-level entries (recommended).

```python
# Find all proton pump inhibitors
classes = tu.tools.RxClass_find_classes(query="proton pump inhibitor", class_type="EPC")
class_id = classes["data"]["classes"][0]["class_id"]
members = tu.tools.RxClass_get_class_members(class_id=class_id, ttys="IN")
```

---

## Phase 3: Approval & Generic Status (FDA Orange Book)

**FDA_OrangeBook_search_drug**: `brand_name` (string), `generic_name` (string), `application_number` (string), `limit` (int, default 10).
Returns `{status, data: {products: [{brand_name, generic_name, dosage_form, strength, te_code, application_number, approval_date}]}}`.
- Use brand name (UPPERCASE) or generic name to find NDA/ANDA numbers and approval info.
- `te_code`: Therapeutic Equivalence code (e.g., "AB" = therapeutically equivalent).

**FDA_OrangeBook_check_generic_availability**: `brand_name` (string), `generic_name` (string).
Returns `{status, data: {reference_listed_drug, generics_available: bool, generics_count, generic_products: [...]}}`.
- Primary tool for "is there a generic?" questions.

**FDA_OrangeBook_get_te_code**: No special params beyond `brand_name`/`application_number`.
Returns therapeutic equivalence codes for substitutability assessment.

**FDA_OrangeBook_get_approval_history**: `application_number` (string, e.g., "NDA020402").
Returns chronological approval history including supplemental approvals and label changes.

```python
# Check generic availability
result = tu.tools.FDA_OrangeBook_check_generic_availability(brand_name="LIPITOR")
# result["data"]["generics_available"] -> True
# result["data"]["generics_count"] -> N
```

---

## Phase 4: Patent & Exclusivity

**FDA_OrangeBook_get_patent_info**: `application_number` (string), `brand_name` (string).
Returns patent information. Note: Full patent numbers and expiration dates require Orange Book data files.

**FDA_OrangeBook_get_exclusivity**: `application_number` (string), `brand_name` (string).
Returns `{status, data: {exclusivities: [{exclusivity_code, exclusivity_date, description}]}}`.
- `exclusivity_code` values: "NCE" (New Chemical Entity, 5 years), "ODE" (Orphan Drug, 7 years), "PED" (Pediatric, 6 months), "NP" (New Product), "M" (new formulation).

---

## Phase 5: Label Parsing (DailyMed)

All DailyMed parse tools accept either `setid` (SPL Set ID UUID) OR `drug_name` (auto-lookup).
Using `drug_name` is recommended when the setid is unknown.

**DailyMed_parse_adverse_reactions**: `setid` or `drug_name`. Returns structured adverse reaction table with frequencies and severity.

**DailyMed_parse_dosing**: `setid` or `drug_name`. Returns dosage and administration section (doses, schedules, renal/hepatic adjustments).

**DailyMed_parse_contraindications**: `setid` or `drug_name`. Returns contraindications section.

**DailyMed_parse_drug_interactions**: `setid` or `drug_name`. Returns drug-drug interaction section with clinical management guidance.

**DailyMed_parse_clinical_pharmacology**: `setid` or `drug_name`. Returns PK/PD data (Cmax, AUC, half-life, protein binding, metabolism pathway).

**DailyMed_search_spls**: `drug_name` (string), returns SPL Set IDs for that drug. Use to find `setid` when needed explicitly.

```python
# Parse adverse reactions for apixaban
ae = tu.tools.DailyMed_parse_adverse_reactions(drug_name="apixaban")
```

---

## Phase 6: Clinical Trials

**search_clinical_trials**: `condition` (string), `intervention` (string), `query_term` (string), `pageSize` (int, alias: `max_results`/`limit`), `overall_status` (array, alias: `status`).
Returns `{status, data: {studies: [{NCT ID, brief_title, brief_summary, overall_status, phase}], total_count}}`.
- Use `intervention` for drug name, `condition` for disease.
- Filter `overall_status=["RECRUITING"]` for active enrollment.
- `total_count` may be None even when results exist; check `len(studies) > 0`.

```python
# Find recruiting trials for a biosimilar
trials = tu.tools.search_clinical_trials(
    intervention="adalimumab biosimilar",
    overall_status=["RECRUITING"],
    pageSize=10
)
```

---

## Tool Quick Reference

| Tool | Key Params | Returns |
|------|-----------|---------|
| FDAGSRS_search_substances | `query`, `substance_class`, `limit` | UNII + substance class + cross-refs |
| FDAGSRS_get_substance | `unii` | All names, references, structure |
| FDAGSRS_get_structure | `unii` | SMILES, InChIKey, MW, stereochemistry |
| RxClass_get_drug_classes | `drug_name` or `rxcui`, `rela_source` | ATC/EPC/MoA/VA classifications |
| RxClass_find_classes | `query`, `class_type` | Class IDs + names |
| RxClass_get_class_members | `class_id`, `rela_source`, `ttys` | Drug ingredients in class |
| FDA_OrangeBook_search_drug | `brand_name`/`generic_name`/`application_number` | Products + NDA + TE codes |
| FDA_OrangeBook_check_generic_availability | `brand_name` or `generic_name` | Generic status + count |
| FDA_OrangeBook_get_exclusivity | `application_number` or `brand_name` | Exclusivity codes + dates |
| FDA_OrangeBook_get_approval_history | `application_number` | Chronological approval events |
| DailyMed_parse_adverse_reactions | `drug_name` or `setid` | AE table with frequencies |
| DailyMed_parse_dosing | `drug_name` or `setid` | Dosage and administration |
| DailyMed_parse_contraindications | `drug_name` or `setid` | Contraindications list |
| DailyMed_parse_drug_interactions | `drug_name` or `setid` | DDI section |
| DailyMed_parse_clinical_pharmacology | `drug_name` or `setid` | PK/PD data |
| search_clinical_trials | `condition`, `intervention`, `pageSize`, `overall_status` | NCT studies |

---

## Example Workflows

### Workflow 1: Full Regulatory Profile for a Drug

```
1. FDAGSRS_search_substances(query="apixaban")
   -> UNII, substance class, ATC/DrugBank cross-refs

2. RxClass_get_drug_classes(drug_name="apixaban", rela_source="ATC")
   -> ATC code B01AF02 (direct factor Xa inhibitor)

3. FDA_OrangeBook_search_drug(brand_name="ELIQUIS")
   -> NDA206518, approval date, TE code

4. FDA_OrangeBook_check_generic_availability(brand_name="ELIQUIS")
   -> Generic availability status

5. FDA_OrangeBook_get_exclusivity(brand_name="ELIQUIS")
   -> Exclusivity codes and expiration dates

6. DailyMed_parse_adverse_reactions(drug_name="apixaban")
   -> Bleeding rates and other AEs from label
```

### Workflow 2: List All Drugs in a Therapeutic Class

```
1. RxClass_find_classes(query="ACE inhibitor", class_type="EPC")
   -> class_id for "Angiotensin-Converting Enzyme Inhibitor"

2. RxClass_get_class_members(class_id=<id>, ttys="IN")
   -> All ACE inhibitors (enalapril, lisinopril, ramipril, etc.)

3. For each drug: RxClass_get_drug_classes(drug_name=drug)
   -> Confirm ATC code and additional classifications
```

### Workflow 3: Drug Label Review

```
1. DailyMed_parse_adverse_reactions(drug_name="metformin")
   -> AE frequencies (GI: lactic acidosis, nausea, diarrhea)

2. DailyMed_parse_contraindications(drug_name="metformin")
   -> eGFR thresholds, renal impairment contraindications

3. DailyMed_parse_drug_interactions(drug_name="metformin")
   -> Iodinated contrast, carbonic anhydrase inhibitor interactions

4. DailyMed_parse_clinical_pharmacology(drug_name="metformin")
   -> Half-life, renal clearance, bioavailability
```

---

## Common Mistakes to Avoid

| Mistake | Correction |
|---------|-----------|
| Using lowercase for Orange Book `brand_name` | Use UPPERCASE (e.g., "LIPITOR" not "lipitor") |
| Passing drug name to FDAGSRS_get_substance | Requires UNII code; use FDAGSRS_search_substances first |
| Expecting full patent numbers from FDA_OrangeBook_get_patent_info | Only metadata available via API; full data needs Orange Book file download |
| Using `FDAGSRS_get_structure` for biologics | Returns error; only works for chemical substances |
| Not passing `ttys="IN"` to RxClass_get_class_members | May return branded products; "IN" restricts to active ingredients |
| Using `overall_status` as string in search_clinical_trials | Must be array: `["RECRUITING"]` not `"RECRUITING"` |

---

## Limitations

- `FDA_OrangeBook_get_patent_info` does not return specific patent numbers or expiration dates via API.
- `FDAGSRS_get_structure` returns error for proteins, nucleic acids, polymers, and mixtures.
- `DailyMed_parse_*` tools require valid drug name or SPL Set ID; some drugs have multiple labels.
- `RxClass` covers FDA-marketed drugs only; experimental or foreign-only drugs may not appear.
- `FDA_OrangeBook_*` covers FDA-approved drugs only; does not include OTC monograph products.
- `search_clinical_trials` `total_count` may be None; check `len(studies)` instead.
