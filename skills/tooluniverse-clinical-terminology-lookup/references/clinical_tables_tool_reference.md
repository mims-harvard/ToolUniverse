# Clinical Tables Tool Reference

Source: `src/tooluniverse/data/clinical_tables_tools.json`. All six tools are
type `ClinicalTablesTool`, wrap NLM's Clinical Table Search Service, and
require no API key. Live-tested (`tu test` + `tu run` with custom params);
every field below was actually observed in a live response, not assumed
from the JSON schema alone. Fields present live but absent from the JSON
`return_schema` are flagged explicitly.

## RxTerms_search_drugs

- **Parameters:** `terms` (string, required), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS (`{"terms": "metformin", "max_results": 5}`).
- **Custom call:** `{"terms": "metfor", "max_results": 3}`
  ```json
  {
    "total_count": 20, "count": 3, "search_terms": "metfor",
    "results": [
      {"code": "metFORMIN (Oral Pill)", "DISPLAY_NAME": "metFORMIN (Oral Pill)",
       "STRENGTHS_AND_FORMS": ["  500 mg Tab", "  625 mg Tab", "  750 mg Tab", "  850 mg Tab", "1,000 mg Tab"],
       "RXCUIS": ["861007", "861021", "2703582", "861010", "861004"]},
      {"code": "metFORMIN XR (Oral Pill)", "...": "..."},
      {"code": "glyBURIDE/metFORMIN (Oral Pill)", "...": "..."}
    ]
  }
  ```
  Note `STRENGTHS_AND_FORMS[i]` corresponds positionally to `RXCUIS[i]` (same
  index = same strength/form's RxCUI) — confirmed by array length matching
  in every result. `code` and `DISPLAY_NAME` are identical in every observed
  result — `code` is not a separate opaque ID here, it's the display name
  used as the lookup key.

## HealthConditions_search

- **Parameters:** `terms` (string, required), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS (`{"terms": "diabetes", "max_results": 5}`).
- **Custom call:** `{"terms": "high blood pressure", "max_results": 3}` —
  confirms informal-phrase -> formal-condition resolution works, not just
  prefix match on the formal name:
  ```json
  {
    "total_count": 13, "count": 3, "search_terms": "high blood pressure",
    "results": [
      {"code": "374", "primary_name": "Hypertension",
       "consumer_name": "High blood pressure (hypertension (HTN))",
       "icd10cm_codes": "I10", "term_icd9_code": null},
      {"code": "3850", "primary_name": "Hypertension - essential",
       "consumer_name": "Hypertension - essential",
       "icd10cm_codes": "I10", "term_icd9_code": "401.9"},
      {"code": "11185", "primary_name": "Hypertension - benign essential",
       "consumer_name": "Hypertension - benign essential",
       "icd10cm_codes": "I10", "term_icd9_code": "401.1"}
    ]
  }
  ```
  `term_icd9_code` is frequently `null` (ICD-9 retired 2015; not every
  condition has a legacy mapping) — treat as optional, not always present.

## DiseaseNames_search

- **Parameters:** `terms` (string, required), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS (`{"terms": "cystic fibrosis", "max_results": 5}`).
- **Custom call:** `{"terms": "lupus", "max_results": 3}`
  ```json
  {
    "total_count": 62, "count": 3, "search_terms": "lupus",
    "results": [
      {"code": "C4551515", "primary_name": "Chilblain lupus"},
      {"code": "C4321325", "primary_name": "Lupus anticoagulant"},
      {"code": "C0409974", "primary_name": "Lupus erythematosus"}
    ]
  }
  ```
  `code` is the UMLS CUI (format `C\d{7}`). A broad term like "lupus" has
  62 total matches spanning related-but-distinct concepts (an anticoagulant
  test, several lupus subtypes) — do not assume the first/top result is the
  one meant; disambiguate with the user if the term is ambiguous.

## HCPCS_search

- **Parameters:** `terms` (string, required), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS (`{"terms": "wheelchair", "max_results": 5}`).
- **Custom call:** `{"terms": "ambulance", "max_results": 3}`
  ```json
  {
    "total_count": 22, "count": 3, "search_terms": "ambulance",
    "results": [
      {"code": "A0424", "display": "Extra ambulance attendant"},
      {"code": "A0888", "display": "Noncovered ambulance mileage"},
      {"code": "A0998", "display": "Ambulance response/treatment"}
    ]
  }
  ```
  Matches on words anywhere in the description, not just a leading prefix
  (all three results have "ambulance" as a non-first word or standalone).

## StarAlleles_search

- **Parameters:** `terms` (string, required), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS (`{"terms": "CYP2D6", "max_results": 5}`).
- **Custom call:** `{"terms": "CYP2C19", "max_results": 3}`
  ```json
  {
    "total_count": 49, "count": 3, "search_terms": "CYP2C19",
    "results": [
      {"code": "CYP2C19*1A", "allele": "CYP2C19*1A", "unused": "None",
       "nucleotide_change": "None", "alternate_name": "", "protein_change": "None"},
      {"code": "CYP2C19*1B", "allele": "CYP2C19*1B", "unused": "99C>T; 991A>G",
       "nucleotide_change": "99C>T; 80161A>G", "alternate_name": "", "protein_change": "I331V"},
      {"code": "CYP2C19*1C", "allele": "CYP2C19*1C", "unused": "991A>G",
       "nucleotide_change": "80161A>G", "alternate_name": "", "protein_change": "I331V"}
    ]
  }
  ```
  **Live-observed field not in the JSON `return_schema`:** every result also
  includes an `unused` field (a secondary/legacy nucleotide-change notation
  that differs from `nucleotide_change`'s values in the examples above —
  cause of the discrepancy not determined; prefer `nucleotide_change` as the
  documented field, but don't discard `unused` if the user's question hinges
  on matching a specific historical notation). `"None"`/`""` are used
  interchangeably as "no value" across different fields — check for both
  when testing for presence/absence.
- 49 total matches for "CYP2C19" alone — this table is allele-definition
  granular (one row per named star allele), so a whole-gene query returns
  many rows; narrow with a specific allele (`"CYP2C19*17"`) if only one
  definition is needed.

## NPIProvider_search

- **Parameters:** `terms` (string, required), `organization` (boolean,
  nullable, default false), `max_results` (int, default 20, max 500).
- **`tu test` result:** PASS, 2 examples (`{"terms": "Smith", "max_results": 5}`
  and `{"terms": "Mayo Clinic", "organization": true, "max_results": 5}`).
- **Custom call:** `{"terms": "Cleveland Clinic", "organization": true, "max_results": 3}`
  ```json
  {
    "total_count": 1216, "count": 3, "search_terms": "Cleveland Clinic",
    "results": [
      {"code": "1447487616", "name.full": "CLEVELAND CLINIC- CLEVELAND-OH", "NPI": "1447487616",
       "provider_type": "Hospital-General", "addr_practice.full": "9500 EUCLID AVENUE, CLEVELAND, OH 44195",
       "is_organization": true},
      {"code": "1548430275", "name.full": "CLEVELAND CLINIC", "NPI": "1548430275",
       "provider_type": "Hospital-General", "addr_practice.full": "A30 9500 EUCLID AVENUE, CLEVELAND, OH 44195",
       "is_organization": true},
      {"code": "1992990618", "name.full": "CLEVELAND CLINIC", "NPI": "1992990618",
       "provider_type": "Clinic or Group Practice", "addr_practice.full": "29800 BAINBRIDGE RD, SOLON, OH 44139",
       "is_organization": true}
    ]
  }
  ```
  `code` and `NPI` are identical in every observed result (redundant, both
  present). `total_count` of 1216 for "Cleveland Clinic" confirms this is a
  large, multi-site health system in the registry — a name search alone
  will not uniquely identify one facility; use `addr_practice.full` or the
  specific NPI to disambiguate a single location. **Downstream link (from
  the tool's own JSON description, not independently verified here):** the
  `NPI` value returned is what `CMSOpenPayments_search_payments` expects as
  its `npi` filter — use this tool to resolve a provider name to an NPI
  before querying payment history there.

---

# ICD and RxNorm Tool Reference

Source: `src/tooluniverse/data/icd_tools.json` (5 tools, type `ICDTool`/
`ICD10Tool`) and `src/tooluniverse/data/rxnorm_extended_tools.json` (5
tools). Live-tested (`tu test` + `tu run`); every field below was actually
observed live except where noted as schema-only.

## ICD10_search_codes

- **Parameters:** `query` (string, required), `limit` (int, default 20, max 100).
- **`tu test` result:** PASS, 4/4 examples.
- **Custom call:** `{"query": "type 2 diabetes", "limit": 3}`
  ```json
  {"data": {"total": 94, "results": [
    {"code": "E11.65", "name": "Type 2 diabetes mellitus with hyperglycemia"},
    {"code": "E11.9", "name": "Type 2 diabetes mellitus without complications"},
    {"code": "E10.A2", "name": "Type 1 diabetes mellitus, presymptomatic, Stage 2"}
  ]}, "metadata": {"source": "NLM Clinical Tables - ICD-10-CM",
    "version": "2026 ICD-10-CM codes"}}
  ```
  No API key. `query` also accepts a partial code (e.g. `"E11"`), per the
  tool's own test examples.

## ICD10_get_code_info

- **Parameters:** `code` (string, required, e.g. `"E11.9"`).
- **`tu test` result:** PASS, 3/3 examples.
- **Custom call:** `{"code": "E11.9"}` -> `{"data": {"total": 1, "results":
  [{"code": "E11.9", "name": "Type 2 diabetes mellitus without
  complications"}]}}`. One exact code in, one (or zero, if invalid) result
  out — this is a lookup, not a search.

## ICD11_search_diseases / ICD11_get_entity / ICD11_browse_hierarchy

- **Parameters (per schema):** `query`/`entity_id` (required), plus
  `linearization` (`mms`/`icf`/`ichi`, default `mms`), `flatResults`,
  `useFlexisearch`, `language`.
- **Live status: all 3 currently fail without setup.** `tu test
  ICD11_search_diseases` -> 3/3 failed, every one returning `{"status":
  "error", "error": "ICD API authentication required. Set ICD_CLIENT_ID
  and ICD_CLIENT_SECRET environment variables. Register at:
  https://icd.who.int/icdapi"}`. Same for `ICD11_get_entity` (2/2 failed)
  and `ICD11_browse_hierarchy` (1/1 failed). This matches the tool's own
  declared `required_api_keys`, so it's expected behavior, not a bug — but
  note these 3 tools still appear in `tu list`/load normally (unlike, e.g.,
  Addgene's tools elsewhere in this repo, which are excluded from `tu list`
  entirely until their key is set) because `required_api_keys` is declared
  inside this tool's `parameter` block rather than at the top level of the
  tool config — ToolUniverse's loader-level key gate only reads the
  top-level field, so it doesn't catch this case; the tool's own `run()`
  code still correctly refuses to call out without the keys. Net effect
  for a user is the same either way (a clear error, no fabricated data),
  just via a different code path than the more common gating pattern.
  Register free at https://icd.who.int/icdapi to use these.

## RxNorm_find_rxcui

- **Parameters:** `drug_name` (string, required).
- **`tu test` result:** PASS, 3/3 examples.
- **Custom call:** `{"drug_name": "metformin"}` -> `{"data": {"drug_name":
  "metformin", "rxcuis": ["6809"], "primary_rxcui": "6809", "found":
  true}}`.

## RxNorm_get_drug_info

- **Parameters:** `rxcui` (string) or `drug_name` (string) — at least one.
- **`tu test` result:** PASS, 3/3 examples.
- **Custom call:** `{"rxcui": "6809"}` -> `{"data": {"rxcui": "6809",
  "name": "metformin", "synonym": null, "term_type": "IN",
  "term_type_label": "Ingredient (generic)", "language": "ENG"}}`.
  `term_type` is an RxNorm TTY abbreviation — the response's own
  `metadata.tty_key` (see `RxNorm_get_related_drugs` below) maps every
  abbreviation to its full label, so no separate reference is needed.

## RxNorm_get_related_drugs

- **Parameters:** `rxcui` and/or `drug_name`, optional `tty` (filter to
  one term-type, e.g. `"BN"` for brand name).
- **`tu test` result:** PASS, 3/3 examples.
- **Custom call:** `{"rxcui": "6809", "tty": "BN"}` -> 14 real branded
  products containing metformin (`Janumet`, `Glucophage`, `Kombiglyze`,
  `Jentadueto`, `Kazano`, `Invokamet`, `Xigduo`, `Synjardy`, `Segluromet`,
  `Trijardy`, `Zituvimet`, `Riomet`, `Actoplus Met`, `Glumetza`), each with
  its own `rxcui`. Response includes `metadata.tty_key`, a live-observed
  field not in the JSON schema — a full label map for every TTY code
  (`IN`=Ingredient generic, `PIN`=Precise Ingredient, `BN`=Brand Name,
  `SCD`=Semantic Clinical Drug, `SBD`=Semantic Branded Drug, `GPCK`/`BPCK`
  =Generic/Branded Pack, `SCDF`/`SBDF`=Clinical/Branded Drug Form,
  `SCDC`=Semantic Drug Component, `MIN`=Multiple Ingredients, `DF`=Dose
  Form).

## RxNorm_get_ndc_status_history

- **Parameters:** `ndc` (string, required, 11-digit NDC).
- **`tu test` result:** PASS, 2/2 examples. Real observed shape (from
  `tu test`): `{"ndc": "00093005801", "found": true, "ndc11":
  "00093005801", "status": "ACTIVE", "active": ...}` — includes historical
  RxCUI remapping timeline per the tool's description; confirm exact
  remapping-field names against a live call before depending on them, only
  `ndc`/`ndc11`/`status`/`active`/`found` were directly inspected here.

## RxNorm_get_ndc_properties

- **Parameters:** `ndc` (string, required — accepts common NDC formats,
  e.g. `"0781-1506-10"`, not just the bare 11-digit form).
- **`tu test` result:** PASS, 1/1 example. Real observed shape: `{"ndc":
  "0781-1506-10", "found": true, "products": [{"ndc_item":
  "00781150610", "ndc10": ...}]}` — note the response normalizes the input
  format into `ndc_item`/`ndc10` fields inside each product entry.
