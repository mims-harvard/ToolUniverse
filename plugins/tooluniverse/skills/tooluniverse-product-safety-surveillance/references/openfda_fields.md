# openFDA Field Reference — Product Safety Surveillance

Per-endpoint searchable fields and verified query patterns. All tools take
`search` (Lucene string), optional `limit`, optional `skip`. Combine terms with a
literal space-separated ` AND ` (NOT `+AND+`). Read the hit count from
`data.meta.results.total`.

---

## Device adverse events — `OpenFDA_search_device_adverse_events` (`/device/event.json`)

Key searchable fields:
- `event_type` — `Death`, `Injury`, `Malfunction`, `No answer provided`
- `device.generic_name`, `device.brand_name`, `device.manufacturer_d_name`
- `device.openfda.device_class` (`1`/`2`/`3`), `product_problem_flag`
- `date_received` (`YYYYMMDD`), `date_of_event` (`YYYYMMDD`)
- `report_number`, `report_to_fda`, `mdr_text.text_type_code`

Example queries (verified):
- `event_type:Death` → total 226190
- `device.generic_name:infusion+pump` → first record `event_type: Malfunction`
- `device.generic_name:pacemaker AND event_type:Death` → total 16619

Caveat: duplicate / follow-up reports of the same event are common; report count ≠ event count.

---

## Device recalls — `OpenFDA_search_device_recalls` (`/device/recall.json`)

Key fields:
- `product_description`, `recalling_firm`, `recall_status` (`Open`/`Terminated`)
- `product_code`, `k_numbers`, `root_cause_description`
- `event_date_initiated` (`YYYY-MM-DD`)

Example (verified): `recalling_firm:Medtronic` → total 1896; first record
`recall_status: Terminated`, `product_code: HAW`, `k_numbers: ["K990214"]`,
`root_cause_description: Labeling design`.

---

## Device 510(k) — `OpenFDA_search_device_510k` (`/device/510k.json`)

Key fields: `device_name`, `applicant`, `k_number`, `decision_description`,
`product_code`, `clearance_type`, `decision_date`.

Example (verified): `device_name:pacemaker` → total 185; first record
`decision_description: Substantially Equivalent`, `k_number: K780776`.

---

## Device / Drug / Food enforcement — `OpenFDA_search_device_enforcement`, `OpenFDA_search_drug_enforcement`, `OpenFDA_search_food_enforcement` (`/.../enforcement.json`)

Shared fields:
- `classification` (`Class I` / `Class II` / `Class III`)
- `status` (`Ongoing` / `Terminated` / `Completed`)
- `reason_for_recall`, `product_description`, `recalling_firm`
- `recall_initiation_date` (`YYYY-MM-DD`), `state`, `country`, `voluntary_mandated`

Examples (verified):
- device: `recalling_firm:Medtronic` → total 1248; first `classification: Class II`, `status: Ongoing`
- food: `reason_for_recall:listeria` → total 7467; first `classification: Class I`, `status: Terminated`
- drug: `reason_for_recall:contamination` → total 2057; first `classification: Class II`, `status: Ongoing`

---

## Food / supplement / cosmetic CAERS — `OpenFDA_search_food_adverse_events` (`/food/event.json`)

Key fields:
- `reactions` (MedDRA, British spelling: `Nausea`, `Diarrhoea`, `Hypersensitivity`)
- `outcomes` (`Hospitalization`, `Life Threatening`, `Disability`, `Death`, `Visited an ER`, `Other Serious or Important Medical Event`)
- `products.industry_name` (`Cosmetics`, `Dietary Conventional Foods/Meal Replacements`, `Milk/Butter/Dried Milk Prod`, …)
- `products.role` (`SUSPECT` / `CONCOMITANT`), `products.name_brand`, `products.industry_code`
- `consumer.age`, `consumer.gender`

Examples (verified):
- `reactions:NAUSEA` → total 16015
- `products.industry_name:Cosmetics` → total 52214; `products.role: SUSPECT`
- `products.industry_name:Dietary` → total 2189; `industry_name: Dietary Conventional Foods/Meal Replacements`
- `outcomes:Hospitalization` → total 23433

Caveat: avoid special chars (`/`, `(`, `)`) in values — use a single simple token
like `Dietary` rather than the full industry-name string.

---

## Veterinary adverse events — `OpenFDA_search_animalvet_adverse_events` (`/animalandveterinary/event.json`)

Key fields:
- `animal.species` (`Dog`, `Cat`, `Horse`, …), `animal.gender`, `animal.breed.breed_component`
- `number_of_animals_affected`, `number_of_animals_treated`
- `reaction.veddra_term_name` (VeDDRA clinical signs: `Vomiting`, `Diarrhoea`, …)
- `drug.brand_name`, `drug.active_ingredients.name`, `drug.route`
- `drug.used_according_to_label`, `drug.off_label_use`

Examples (verified):
- `animal.species:Dog` → total 974175
- `drug.active_ingredients.name:carprofen` → success
- `drug.active_ingredients.name:carprofen AND animal.species:Dog` → total 46469; VeDDRA terms `Leucocytosis NOS`, `Neutrophilia`, `Depression`, `Elevated alanine aminotransferase (ALT)`

---

## Drug shortages — `OpenFDA_search_drug_shortages` (`/drug/shortages.json`)

Key fields:
- `status` (`Current` / `Resolved`), `availability` (`Unavailable`, `Limited`)
- `generic_name`, `shortage_reason`, `dosage_form`, `presentation`
- `therapeutic_category`, `company_name`, `package_ndc`
- `update_type`, `initial_posting_date`, `update_date`, `related_info`

Examples (verified):
- `status:Current` → total 1146
- `dosage_form:Injection AND status:Current` → total 799; first `generic_name: Ketorolac Tromethamine Injection`, `status: Current`, `availability: Unavailable`, `shortage_reason: Delay in shipping of the drug`

---

## Drug events / labels (raw, no signal stats) — `OpenFDA_search_drug_events` (`/drug/event.json`), `OpenFDA_search_drug_labels` (`/drug/label.json`)

For raw FAERS record / label retrieval only. For drug-AE disproportionality
(PRR/ROR/IC) use `tooluniverse-pharmacovigilance` / `tooluniverse-adverse-event-detection`.

- events: `patient.drug.medicinalproduct:metformin` → total 425796
- labels: `openfda.generic_name:metformin` → total 380
