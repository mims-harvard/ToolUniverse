---
name: tooluniverse-clinical-terminology-lookup
description: Fast autocomplete/normalization lookups against the NLM Clinical Table Search Service — resolve a partial or informal drug name to its RxTerms display name and RxCUI, autocomplete a health condition or problem-list entry to its formal name and ICD-10-CM/ICD-9-CM codes, normalize a disease mention to a UMLS CUI, look up an HCPCS Level II billing/DME code, autocomplete a pharmacogenomic star allele (e.g. CYP2D6, CYP2C19) to its nucleotide/protein change, or find a US healthcare provider/organization by name via the NPPES NPI registry. Also covers standardized coding-system lookups: search or look up ICD-10-CM diagnosis codes directly by name or code, and resolve a drug name to its full RxNorm identity — RXCUI, related brand/generic products, and NDC package-level status/properties. Use when someone gives a free-text or informal clinical term ("high blood pressure", "metfor...", "Cleveland Clinic") and needs the standardized name/code before a downstream lookup, or explicitly asks to "autocomplete", "look up the RxCUI for", "find the ICD-10 code for", "look up this star allele", "find the NPI for", "what does ICD-10 code X mean", or "look up the NDC for this drug package".
disable-model-invocation: true
---

# Clinical Terminology Lookup (NLM Clinical Tables, ICD, RxNorm)

A **fast, lightweight normalization utility** — not a research skill. Six
autocomplete-style tools from the NLM Clinical Table Search Service turn a
partial or informal clinical term into a standardized name/code, plus two
standardized-coding-system tool families (ICD-10-CM diagnosis codes, RxNorm
drug identity/NDC data) for when the input is already a known term/code and
you need its full standardized record rather than autocomplete matching.
Use this as a **supporting first step** before a deeper lookup in another
skill, not as a destination in itself.

**LOOK UP, DON'T GUESS**: RxCUIs, ICD-10-CM codes, UMLS CUIs, HCPCS codes,
and star-allele nucleotide changes are exact identifiers — never guess one
from memory or infer it from the term's spelling. Always resolve through
these tools.

---

## When to Use This Skill

Apply when someone gives a free-text/informal/partial clinical term and
needs it normalized:
- A partial or informal drug name -> standardized RxTerms display name +
  available strengths/forms + RxCUI(s) (`RxTerms_search_drugs`)
- An informal symptom/problem description (e.g. "high blood pressure") ->
  formal condition name + ICD-10-CM/ICD-9-CM codes (`HealthConditions_search`)
- A disease mention -> canonical disease name + UMLS CUI (`DiseaseNames_search`)
- A procedure/DME description -> HCPCS Level II billing code (`HCPCS_search`)
- A gene or partial star-allele designation -> matching pharmacogenomic star
  alleles with nucleotide/protein change (`StarAlleles_search`)
- A provider or organization name -> NPI, specialty/type, practice address
  (`NPIProvider_search`)
- A disease/condition name or partial ICD-10-CM code -> matching ICD-10-CM
  codes and official descriptions (`ICD10_search_codes`); a specific known
  ICD-10-CM code -> its official description (`ICD10_get_code_info`)
- A drug name -> its RxNorm identity: RXCUI(s), ingredient/brand/dose-form
  classification (`RxNorm_find_rxcui`, `RxNorm_get_drug_info`), and related
  brand/generic products (`RxNorm_get_related_drugs`)
- A specific NDC (National Drug Code) package identifier -> its current
  marketing status/history or product/package metadata
  (`RxNorm_get_ndc_status_history`, `RxNorm_get_ndc_properties`)

**NOT for** (route elsewhere once the term is resolved):
- Deep drug mechanism/interaction/regulatory research once the RxCUI/name
  is known -> `tooluniverse-drug-research`, `tooluniverse-drug-drug-interaction`
- Full pharmacogenomic dosing interpretation once a star allele/diplotype is
  identified -> `tooluniverse-pharmacogenomics` (this skill only finds the
  allele's *definition* — nucleotide/protein change — not CPIC dosing
  guidance)
- Disease biology, mechanism, or treatment research once the disease/CUI is
  resolved -> `tooluniverse-disease-research`
- Provider network analysis, credentialing, or payment-history investigation
  beyond a basic NPI lookup — `NPIProvider_search`'s returned `NPI` is what
  `CMSOpenPayments_search_payments` expects as its `npi` filter, so use this
  skill only to *resolve* who a provider is, then hand off

This skill's job ends at "here is the standardized name/code." It does not
interpret clinical significance, dosing, or billing eligibility.

---

## Tools

All six take a required `terms` string (partial or full text) and an
optional `max_results` (default 20, max 500). None require an API key.
Matching is **prefix/substring on the underlying term, not exact-match
only** — e.g. `"metfor"` matches "metFORMIN (Oral Pill)", and an informal
phrase like `"high blood pressure"` correctly resolves to the formal
condition "Hypertension" via `HealthConditions_search`'s consumer-name
crosswalk (verified live, see below) — but the tools do not do full
semantic/synonym expansion beyond what's indexed, so a very colloquial or
misspelled term may return zero hits even when a formal synonym exists;
retry with a shorter or more standard fragment before concluding no match.

| Tool | Resolves | Key output fields |
|---|---|---|
| `RxTerms_search_drugs` | partial drug name -> prescribable display name | `DISPLAY_NAME`, `STRENGTHS_AND_FORMS[]`, `RXCUIS[]` |
| `HealthConditions_search` | informal condition/symptom -> formal condition | `primary_name`, `consumer_name`, `icd10cm_codes`, `term_icd9_code` |
| `DiseaseNames_search` | disease mention -> UMLS-linked disease name | `primary_name`, `code` (UMLS CUI) |
| `HCPCS_search` | procedure/DME description -> billing code | `code` (HCPCS), `display` |
| `StarAlleles_search` | gene/allele prefix -> star allele definition | `code`/`allele`, `nucleotide_change`, `protein_change`, `alternate_name` |
| `NPIProvider_search` | provider/org name -> NPI registry entry | `NPI`, `name.full`, `provider_type`, `addr_practice.full`, `is_organization` |

Every result set also includes `total_count` (matches available on the
server, which can exceed `count`/the returned page — raise `max_results` or
note truncation rather than silently treating `count` as the full match
list) and `search_terms` (echoes the query).

`NPIProvider_search` takes an additional optional `organization` boolean
(default false) to search organizations/hospitals instead of individual
providers — confirmed live: `{"terms": "Cleveland Clinic", "organization":
true}` returns hospital/clinic entries with `is_organization: true`, not
individual physicians named "Cleveland" or "Clinic".

See `references/clinical_tables_tool_reference.md` for the full parameter
table and real captured example responses for all six tools.

## Standardized Coding Systems: ICD-10-CM and RxNorm

Two more tool families for when the input is a term/code you want the
*full standardized record* for (not just autocomplete matching against a
partial string).

### ICD-10-CM (`src/tooluniverse/data/icd_tools.json`)

| Tool | Resolves | Auth |
|---|---|---|
| `ICD10_search_codes` | disease name, partial name, or partial code -> matching ICD-10-CM codes + descriptions | none (NLM Clinical Tables) |
| `ICD10_get_code_info` | one exact ICD-10-CM code -> its official description | none (NLM Clinical Tables) |
| `ICD11_search_diseases` | disease/symptom term -> WHO ICD-11 entities (id, title, code, chapter) | **requires `ICD_CLIENT_ID` + `ICD_CLIENT_SECRET`** (free registration at icd.who.int/icdapi) |
| `ICD11_get_entity` | ICD-11 entity ID -> full definition, inclusions/exclusions, parent/child | same as above |
| `ICD11_browse_hierarchy` | parent ICD-11 entity ID -> its child categories | same as above |

**Use `ICD10_search_codes`/`ICD10_get_code_info` by default** — no setup
needed, and this JSON file itself notes it serves "2026 ICD-10-CM codes"
(the current US clinical-modification standard). Only reach for the three
`ICD11_*` tools when the user specifically needs WHO's international
ICD-11 classification (e.g. non-US context, or ICD-11's finer clinical
hierarchy) — verified live: without the two API keys set, all three fail
at call time with a clear `"ICD API authentication required..."` error
(they still appear in `tu list` since the key requirement is declared
inside this tool's `parameter` block rather than at the top level the way
most other gated ToolUniverse tools declare it — a minor registration
inconsistency, not something to work around, just don't assume "listed"
means "usable without setup" for these three).

Real example (`ICD10_search_codes {"query": "type 2 diabetes", "limit": 3}`):
returns 94 total matches including `{"code": "E11.9", "name": "Type 2
diabetes mellitus without complications"}`; feeding that code into
`ICD10_get_code_info {"code": "E11.9"}` returns the same single official
description — use the search tool to find a code from a name, the
get-info tool to confirm/expand a code you already have.

### RxNorm (`src/tooluniverse/data/rxnorm_extended_tools.json`)

| Tool | Resolves | Key output |
|---|---|---|
| `RxNorm_find_rxcui` | drug name -> RxNorm Concept Unique Identifier(s) | `rxcuis[]`, `primary_rxcui` |
| `RxNorm_get_drug_info` | RXCUI or drug name -> full RxNorm properties | `name`, `term_type` (e.g. `IN`=ingredient, `BN`=brand, `SCD`=clinical drug), `term_type_label` |
| `RxNorm_get_related_drugs` | RXCUI (+ optional `tty` filter) -> related brand/generic/dose-form products | `related_drugs` keyed by relation type, `total_related` |
| `RxNorm_get_ndc_status_history` | 11-digit NDC -> marketing status timeline | `status` (e.g. `ACTIVE`), `active`, historical RxCUI remapping |
| `RxNorm_get_ndc_properties` | NDC (any common format) -> package/product identification metadata | per-package product details |

This is a **different job than `RxTerms_search_drugs` above**: RxTerms is
prefix/substring autocomplete on prescribable display names (good for "the
user typed part of a drug name"); `RxNorm_find_rxcui` +
`RxNorm_get_drug_info` resolve a name to its stable normalized identifier
and full RxNorm classification (ingredient vs. brand vs. specific dose
form), and `RxNorm_get_related_drugs`/the NDC tools go further into the
RxNorm relationship graph and specific packaged-product data that RxTerms
doesn't expose. Reach for RxTerms when autocompleting a partial user
string; reach for RxNorm here once you have (or need) a specific RXCUI or
NDC to work with downstream.

Real example chain (`metformin`): `RxNorm_find_rxcui {"drug_name":
"metformin"}` -> `primary_rxcui: "6809"` -> `RxNorm_get_drug_info
{"rxcui": "6809"}` -> `term_type: "IN"` (the generic ingredient concept,
not a specific product) -> `RxNorm_get_related_drugs {"rxcui": "6809",
"tty": "BN"}` -> 14 real branded combination products (Janumet, Glucophage,
Kombiglyze, etc.) that contain metformin as an ingredient.

See `references/clinical_tables_tool_reference.md` for full parameter
tables and real captured example responses for all 10 of these tools.

## Workflow

1. Identify which of the six normalization needs applies.
2. Call the matching tool with the user's free-text term as `terms`.
3. If `total_count` is 0, retry with a shorter/simpler fragment (e.g. drop a
   qualifying word) before concluding there's no match — do not fabricate a
   plausible-sounding code when the search genuinely returns nothing.
4. Report the resolved standardized name/code(s), noting `total_count` if it
   exceeds what was returned, and hand off to the appropriate downstream
   skill (see "NOT for" above) rather than attempting deeper analysis here.

## Output

State the exact term searched, the resolved standardized name/code, and
which tool produced it. Never present a code or identifier that wasn't
actually returned by one of these six tools.
