---
name: tooluniverse-clinical-terminology-lookup
description: Fast autocomplete/normalization lookups against the NLM Clinical Table Search Service — resolve a partial or informal drug name to its RxTerms display name and RxCUI, autocomplete a health condition or problem-list entry to its formal name and ICD-10-CM/ICD-9-CM codes, normalize a disease mention to a UMLS CUI, look up an HCPCS Level II billing/DME code, autocomplete a pharmacogenomic star allele (e.g. CYP2D6, CYP2C19) to its nucleotide/protein change, or find a US healthcare provider/organization by name via the NPPES NPI registry. Use when someone gives a free-text or informal clinical term ("high blood pressure", "metfor...", "Cleveland Clinic") and needs the standardized name/code before a downstream lookup, or explicitly asks to "autocomplete", "look up the RxCUI for", "find the ICD-10 code for", "look up this star allele", or "find the NPI for".
disable-model-invocation: true
---

# Clinical Terminology Lookup (NLM Clinical Tables)

A **fast, lightweight normalization utility** — not a research skill. Six
autocomplete-style tools from the NLM Clinical Table Search Service turn a
partial or informal clinical term into a standardized name/code. Use this
as a **supporting first step** before a deeper lookup in another skill, not
as a destination in itself.

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
