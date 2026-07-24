---
name: tooluniverse-product-safety-surveillance
description: >-
  Post-market safety surveillance and recall/adverse-event RETRIEVAL across the
  full spectrum of FDA-regulated products that are NOT covered by the drug-AE
  signal skills: medical devices, food / dietary supplements / cosmetics,
  veterinary drugs, and drug supply (shortages). Orchestrates openFDA endpoints
  (MAUDE device adverse events + device recalls + 510(k), CAERS food/supplement/
  cosmetic adverse events, veterinary adverse events, drug shortages, and
  cross-product enforcement/recall reports). USE WHEN the user asks: "are there
  adverse events for [device / pacemaker / infusion pump / insulin pump]",
  "device recalls for [firm/product]", "supplement / vitamin / cosmetic adverse
  reactions", "is [drug] in shortage", "what injectables are on shortage",
  "veterinary / animal adverse events for [drug] in [dog/cat/horse]", "food
  recall for listeria", "MAUDE report for [device]", "CAERS reactions for [brand]".
  DO NOT USE for drug adverse-event SIGNAL detection or disproportionality
  (PRR / ROR / IC) or drug-AE association scoring — that is
  `tooluniverse-pharmacovigilance` / `tooluniverse-adverse-event-detection`.
  This skill is multi-product surveillance and retrieval, not drug-AE
  statistical signal mining.
disable-model-invocation: true
---

# Product Safety Surveillance (multi-product, openFDA)

Retrieve and interpret post-market safety records across **every FDA-regulated
product class except drug-AE signal mining**: medical devices, food / dietary
supplements / cosmetics, veterinary drugs, and drug supply (shortages), plus
cross-product enforcement/recall reports.

**KEY PRINCIPLES**
1. **Decide the product class first.** Device? Food/supplement/cosmetic? Vet drug? Drug shortage? Recall? The class picks the tool.
2. **Build a valid Lucene query.** openFDA uses field-scoped `field:value` terms; combine with a space-separated `AND`. Phrases and special characters need care (see Query Grammar).
3. **Retrieve, then interpret.** These are spontaneous/voluntary reports. Report the records and their fields; never assert causation or rates.
4. **Cite every record** with the tool name, the openFDA endpoint, the query used, and the `total` hit count from `meta.results.total`.
5. **Stay in scope.** If the request is drug-AE signal detection (PRR/ROR/IC), STOP and point to `tooluniverse-pharmacovigilance` / `tooluniverse-adverse-event-detection`.

---

## When to Use vs When NOT to Use

**USE for:**
- Device adverse events (MAUDE): "adverse events / malfunctions / deaths for [device]"
- Device recalls & enforcement: "device recalls for [firm]", "Class I device recalls"
- Device clearance context: "510(k) clearances for [device type]"
- Food / dietary-supplement / cosmetic adverse events (CAERS): "supplement reactions", "cosmetic adverse events for [brand]"
- Food recalls/enforcement: "food recall for listeria / undeclared allergen"
- Veterinary drug adverse events: "adverse events for [drug] in dogs"
- Drug shortages: "is [drug] in shortage", "injectables on current shortage"
- Drug recalls/enforcement: "drug recalls for contamination"

**DO NOT USE for** (point elsewhere):
- Drug adverse-event SIGNAL detection / disproportionality (PRR, ROR, IC) → `tooluniverse-pharmacovigilance` or `tooluniverse-adverse-event-detection`
- Drug-AE association strength scoring, demographic risk stratification of drug AEs → same two skills
- Drug efficacy, mechanism, pharmacogenomics → other tooluniverse-* skills

This skill **retrieves and interprets multi-product safety records**. It does not compute drug-AE signal statistics.

---

## Tool Map (which tool for which question)

| Product class | Question | Tool | openFDA endpoint |
|---|---|---|---|
| Device | Adverse events / malfunctions / deaths (MAUDE) | `OpenFDA_search_device_adverse_events` | `/device/event.json` |
| Device | Recalls | `OpenFDA_search_device_recalls` | `/device/recall.json` |
| Device | Enforcement / recall reports | `OpenFDA_search_device_enforcement` | `/device/enforcement.json` |
| Device | 510(k) clearances (context) | `OpenFDA_search_device_510k` | `/device/510k.json` |
| Food/supplement/cosmetic | Adverse events (CAERS) | `OpenFDA_search_food_adverse_events` | `/food/event.json` |
| Food | Enforcement / recall reports | `OpenFDA_search_food_enforcement` | `/food/enforcement.json` |
| Veterinary | Animal drug adverse events | `OpenFDA_search_animalvet_adverse_events` | `/animalandveterinary/event.json` |
| Drug supply | Shortages | `OpenFDA_search_drug_shortages` | `/drug/shortages.json` |
| Drug | Enforcement / recall reports | `OpenFDA_search_drug_enforcement` | `/drug/enforcement.json` |
| Drug | Adverse events (raw FAERS records) | `OpenFDA_search_drug_events` | `/drug/event.json` |
| Drug | Labels | `OpenFDA_search_drug_labels` | `/drug/label.json` |

All tools take a Lucene `search` string plus optional `limit` and `skip`. All are keyless and verified live.

---

## openFDA Query Grammar (CRITICAL — read before querying)

- **Field-scoped term:** `field:value` (e.g. `event_type:Death`, `status:Current`).
- **Nested fields use dot paths:** `device.generic_name:pacemaker`, `products.industry_name:Cosmetics`, `animal.species:Dog`, `reaction.veddra_term_name:Vomiting`, `drug.active_ingredients.name:carprofen`.
- **Combine terms with a SPACE-separated `AND`** (verified working): `device.generic_name:pacemaker AND event_type:Death`.
  - **Do NOT use `+AND+`** — the `+`-joined boolean form errors through these tools. Use a literal space around `AND`.
- **Multi-word values:** join with `+` only for adjacency within a single field value (e.g. `device.generic_name:infusion+pump`). This is matched as tokens, not an exact phrase.
- **Avoid raw special characters** (`(`, `)`, `/`, leading `+`) inside values — they break the query. Pick a simpler token (e.g. `products.industry_name:Dietary` instead of the full `Dietary Conventional Foods/Meal Replacements`).
- **Dates** are strings: device AE/MAUDE use `YYYYMMDD` (e.g. `date_received`); recalls/enforcement use `YYYY-MM-DD` (e.g. `event_date_initiated`, `recall_initiation_date`).
- **Result envelope:** every successful call returns `{status:"success", data:{meta:{results:{total, skip, limit}}, results:[...]}}`. Read the hit count from `data.meta.results.total`.
- **Counts/aggregations:** native openFDA supports `&count=<field>`; these TU wrappers center on `search`. To rank terms, retrieve a batch (e.g. `limit:100`) and tally the field yourself in Python.

---

## Interpretation Tables (raw openFDA field → meaning)

### Medical devices — MAUDE adverse events (`/device/event.json`)
| Field | Meaning |
|---|---|
| `event_type` | `Death`, `Injury`, `Malfunction`, or `No answer provided`. Death/Injury = patient harm; Malfunction = device failure without (reported) harm. |
| `device[].generic_name` / `device[].brand_name` | Device category / trade name. |
| `device[].manufacturer_d_name` | Device manufacturer. |
| `patient[]` | Patient-level outcome data (may be sparse). |
| `mdr_text[].text` | Narrative; `text_type_code` distinguishes event description vs manufacturer narrative. |
| `report_number` | MAUDE report id. **Duplicate / follow-up reports of the same event are common** — do not count reports as distinct events. |
| `date_received` | `YYYYMMDD` FDA received date. |

### Medical devices — recalls (`/device/recall.json`)
| Field | Meaning |
|---|---|
| `product_description` | What was recalled. |
| `recalling_firm` | Firm issuing the recall. |
| `recall_status` | e.g. `Open`, `Terminated`. Terminated = FDA closed the action. |
| `product_code` | FDA device product code. |
| `k_numbers[]` | Associated 510(k) clearance numbers. |
| `root_cause_description` | FDA root-cause category (e.g. `Labeling design`). |
| `event_date_initiated` | `YYYY-MM-DD` recall start. |

### Enforcement reports (device / drug / food `/.../enforcement.json`)
| Field | Meaning |
|---|---|
| `classification` | Recall severity: `Class I` (serious/fatal hazard), `Class II` (temporary/reversible), `Class III` (unlikely to cause harm). |
| `status` | `Ongoing` / `Terminated` / `Completed`. |
| `reason_for_recall` | Why recalled. |
| `product_description` | Recalled product. |
| `recalling_firm` | Firm. |

### Food / supplement / cosmetic — CAERS adverse events (`/food/event.json`)
| Field | Meaning |
|---|---|
| `reactions[]` | MedDRA reaction terms (British spelling, e.g. `Diarrhoea`, `Nausea`). |
| `outcomes[]` | e.g. `Hospitalization`, `Life Threatening`, `Disability`, `Death`, `Other Serious or Important Medical Event`, `Visited an ER`. |
| `products[].industry_name` | Product category (`Cosmetics`, `Dietary Conventional Foods/Meal Replacements`, `Milk/Butter/Dried Milk Prod`, …). |
| `products[].role` | `SUSPECT` (implicated) vs `CONCOMITANT` (also consumed). |
| `products[].name_brand` | Brand name. |
| `consumer` | `age`, `gender` of the consumer (often sparse). |

### Veterinary — animal drug adverse events (`/animalandveterinary/event.json`)
| Field | Meaning |
|---|---|
| `animal.species` | `Dog`, `Cat`, `Horse`, … |
| `animal.gender` | Animal sex. |
| `number_of_animals_affected` | Count in the report. |
| `reaction[].veddra_term_name` | VeDDRA clinical sign (e.g. `Vomiting`, `Diarrhoea`). |
| `drug[].brand_name` / `drug[].active_ingredients[].name` | Implicated product / active. |
| `drug[].used_according_to_label` / `off_label_use` | Label vs off-label use. |

### Drug shortages (`/drug/shortages.json`)
| Field | Meaning |
|---|---|
| `status` | `Current` or `Resolved`. |
| `availability` | e.g. `Unavailable`, `Limited`. |
| `generic_name` | Drug in shortage. |
| `shortage_reason` | e.g. `Delay in shipping of the drug`, `Demand increase for the drug`. |
| `dosage_form` | e.g. `Injection`, `Tablet`. |
| `therapeutic_category[]` | Clinical category. |
| `company_name` | Manufacturer. |
| `update_type` / `initial_posting_date` / `update_date` | Posting metadata. |

---

## Workflow

1. **Classify the product** from the request (device / food-supplement-cosmetic / vet / drug shortage / recall).
2. **Pick the tool** from the Tool Map.
3. **Build the Lucene query** following Query Grammar (single field for a first pass; add ` AND ` for combinations). Keep values simple; avoid special characters.
4. **Run it** and read `data.meta.results.total` and `data.results[]`.
5. **Interpret** the fields with the table above. For severity: device `event_type:Death`; enforcement `classification:Class I`; CAERS `outcomes:Death`/`Hospitalization`; shortage `status:Current`.
6. **Summarize and cite.** Report counts, key fields, the query used, and the LIMITATIONS caveat. To rank terms, pull `limit:100` and tally in Python (no `count` aggregation in these wrappers).
7. **If out of scope** (drug-AE signal/PRR/ROR), stop and route to the pharmacovigilance skills.

---

## Worked Examples (verified live)

### Example 1 — Device deaths for a device type (MAUDE)
> "Are there any reported deaths in adverse-event reports for pacemakers?"

```
OpenFDA_search_device_adverse_events {"search":"device.generic_name:pacemaker AND event_type:Death","limit":1}
```
Real output (abbrev): `status:success`, `meta.results.total = 16619`; first record `event_type = Death`, `device.generic_name = DEFIBRILLATOR/PACEMAKER`.
Interpretation: 16,619 MAUDE reports match a pacemaker device with a `Death` event type. These are spontaneous reports — duplicates likely, and "Death" means a death was reported in temporal association, not that the device caused it.

### Example 2 — Device recalls for a firm
> "What device recalls has Medtronic Navigation issued?"

```
OpenFDA_search_device_recalls {"search":"recalling_firm:Medtronic","limit":1}
```
Real output (abbrev): `total = 1896`; first record `recall_status = Terminated`, `product_code = HAW`, `root_cause_description = Labeling design`, `k_numbers = ["K990214"]`, `event_date_initiated = 2011-01-20`, `product_description` = a tactile probe for spine surgery.
Interpretation: 1,896 recall records match firms containing "Medtronic". `recall_status: Terminated` means FDA has closed this action; the root cause was a labeling-design issue.

### Example 3 — Drug shortage lookup for an injectable
> "Is ketorolac injection in shortage right now?"

```
OpenFDA_search_drug_shortages {"search":"dosage_form:Injection AND status:Current","limit":1}
```
Real output (abbrev): `total = 799`; first record `generic_name = Ketorolac Tromethamine Injection`, `status = Current`, `shortage_reason = Delay in shipping of the drug`, `availability = Unavailable`, `company_name = Fresenius Kabi USA, LLC`.
Interpretation: 799 current shortage records are injectables; ketorolac tromethamine injection is currently in shortage (status `Current`, availability `Unavailable`) due to a shipping delay.

### Example 4 — Supplement / cosmetic CAERS reactions
> "Are there CAERS adverse-event reports implicating cosmetics?"

```
OpenFDA_search_food_adverse_events {"search":"products.industry_name:Cosmetics","limit":1}
```
Real output (abbrev): `total = 52214`; first record `products[].industry_name = Cosmetics`, `products[].role = SUSPECT`, `outcomes = ["Hospitalization","Other Serious or Important Medical Event"]`.
Interpretation: 52,214 CAERS reports name a cosmetic product as `SUSPECT`. CAERS is voluntary; a `SUSPECT` role reflects the reporter's attribution, not a verified causal link.

### Example 5 — Veterinary adverse events for a drug in a species
> "What adverse events are reported for carprofen in dogs?"

```
OpenFDA_search_animalvet_adverse_events {"search":"drug.active_ingredients.name:carprofen AND animal.species:Dog","limit":1}
```
Real output (abbrev): `total = 46469`; first record `animal.species = Dog`, `reaction[].veddra_term_name` includes `Leucocytosis NOS`, `Neutrophilia`, `Depression`, `Elevated alanine aminotransferase (ALT)`.
Interpretation: 46,469 veterinary reports match carprofen-containing products in dogs. VeDDRA terms describe reported clinical signs; counts reflect reporting, not incidence.

---

## Limitations (state these in every report)

- **Spontaneous / voluntary reports.** MAUDE (device), CAERS (food/supplement/cosmetic), FAERS (drug), and the animal/vet system are passive surveillance. Reports are **unverified** and a report is not a confirmed causal event.
- **No causation, no denominator.** Counts (`meta.results.total`) are report counts, not incidence or rates. There is no exposure denominator, so you cannot compute risk.
- **Reporting bias.** Serious events, new products, recalls, and media/regulatory attention drive reporting spikes (Weber effect). High counts may reflect usage volume or attention, not hazard.
- **Duplicate reports.** MAUDE in particular contains follow-up/duplicate reports of the same event; do not treat report counts as event counts.
- **CAERS voluntary & sparse.** Consumer/age/gender fields are often missing; `SUSPECT` role is reporter attribution.
- **This skill does not compute signal statistics** (PRR/ROR/IC). For drug-AE disproportionality use `tooluniverse-pharmacovigilance` / `tooluniverse-adverse-event-detection`.
- **Data currency:** each response carries a `meta.last_updated` date; openFDA lags real-world events.

See `references/openfda_fields.md` for the full per-endpoint field reference and additional query examples.

---

## References

- openFDA: https://open.fda.gov
- MAUDE (device adverse events): https://www.fda.gov/medical-devices/mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities
- Device recalls / 510(k): https://www.fda.gov/medical-devices
- CAERS (food/supplement/cosmetic): https://www.fda.gov/food/compliance-enforcement/cfsan-adverse-event-reporting-system-caers
- Drug shortages: https://www.fda.gov/drugs/drug-shortages
- Recall classifications: https://www.fda.gov/safety/industry-guidance-recalls
