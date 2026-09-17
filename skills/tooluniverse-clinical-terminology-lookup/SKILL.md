---
name: tooluniverse-clinical-terminology-lookup
description: Fast autocomplete/normalization lookups against the NLM Clinical Table Search Service — resolve a partial or informal drug name to its RxTerms display name and RxCUI, autocomplete a health condition or problem-list entry to its formal name and ICD-10-CM/ICD-9-CM codes, normalize a disease mention to a UMLS CUI, look up an HCPCS Level II billing/DME code, autocomplete a pharmacogenomic star allele (e.g. CYP2D6, CYP2C19) to its nucleotide/protein change, or find a US healthcare provider/organization by name via the NPPES NPI registry. Also covers standardized coding-system lookups: search or look up ICD-10-CM diagnosis codes directly by name or code, resolve a drug name to its full RxNorm identity (RXCUI, related brand/generic products, NDC package-level status/properties), browse NCI Thesaurus cancer-concept hierarchy and its cross-vocabulary maps to MedDRA/SNOMED/GDC, and search/resolve LOINC lab-test and clinical-form codes. Also resolves UniProt's own disease and functional-keyword controlled vocabularies (DI-/KW- IDs) for protein-annotation contexts. Use when someone gives a free-text or informal clinical term ("high blood pressure", "metfor...", "Cleveland Clinic") and needs the standardized name/code before a downstream lookup, or explicitly asks to "autocomplete", "look up the RxCUI for", "find the ICD-10 code for", "look up this star allele", "find the NPI for", "what does ICD-10 code X mean", "look up the NDC for this drug package", "find the NCIt code for this cancer concept", "what does this cancer concept map to in MedDRA", or "find the LOINC code for this lab test".
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
- A cancer-related term or concept -> NCI Thesaurus code, definition, and
  hierarchy position (`NCIThesaurus_search`, `NCIThesaurus_get_concept`,
  `NCIThesaurus_get_children`, `NCIThesaurus_get_parents`), or its
  cross-vocabulary mapping to MedDRA/SNOMED/GDC (`NCIThesaurus_get_concept_maps`)
- A lab test or clinical observation name -> LOINC code
  (`LOINC_search_tests`, `LOINC_get_code_details`); a coded observation's
  permissible values (`LOINC_get_answer_list`); or a clinical
  form/panel/survey-instrument name -> its LOINC code (`LOINC_search_forms`)

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

## Cancer Ontology and Lab-Test Coding: NCI Thesaurus and LOINC

Two more standardized-coding-system tool families, for cancer-specific
concepts and lab-test/observation codes respectively — neither overlaps
with ICD-10-CM/RxNorm above.

### NCI Thesaurus / NCIt (`src/tooluniverse/data/nci_thesaurus_tools.json`)

| Tool | Resolves | Auth |
|---|---|---|
| `NCIThesaurus_search` | free-text term -> matching NCIt concept codes (`term`, `page_size`) | none |
| `NCIThesaurus_get_concept` | NCIt code -> full definition, synonyms (with source terminology), properties (incl. `UMLS_CUI` as one of the `properties` entries, not a top-level field) | none |
| `NCIThesaurus_get_children` | NCIt code -> immediate subcategories (downward hierarchy) | none |
| `NCIThesaurus_get_parents` | NCIt code -> immediate broader categories / drug-class parents (upward hierarchy) | none |
| `NCIThesaurus_get_concept_maps` | NCIt code -> cross-vocabulary maps to MedDRA/SNOMED/GDC/ICD | none |

NCIt is the National Cancer Institute's reference terminology for cancer
diseases, drugs, anatomy, genes, and biological processes — broader than
just tumor types (e.g. drugs like Trastuzumab and processes like
Apoptosis are also NCIt concepts). Use `get_children`/`get_parents` to
navigate from a broad category down to a specific subtype (or back up to
find a drug's mechanistic class) rather than guessing hierarchy from the
name alone. Use `get_concept_maps` specifically when you need the code in
*another* vocabulary (e.g. a MedDRA term for a pharmacovigilance report,
or a GDC therapeutic-agent code) — `get_concept` never returns this, only
`get_concept_maps` does.

Real example chain (`immunotherapy` -> `Breast Carcinoma`): `NCIThesaurus_search
{"term": "immunotherapy", "page_size": 5}` -> 2 hits including `C15262`
("Immunotherapy") and `C308` ("Immunotherapeutic Agent"). Separately,
`NCIThesaurus_get_concept {"code": "C4872"}` -> "Breast Carcinoma" with an
18-entry `synonyms[]` (each tagged by `source`, e.g. `GDC`, `FDA`,
`CTRP`) and a `properties[]` array containing `{"type": "UMLS_CUI",
"value": "C0678222"}` and `{"type": "Semantic_Type", "value": "Neoplastic
Process"}`. Feeding the same code into `NCIThesaurus_get_concept_maps
{"code": "C4872"}` returns a *different* field the concept-detail call
never exposes: `maps: [{"target_terminology": "MedDRA", "target_code":
"10006187", "target_term_type": "LLT"}, {"target_terminology": "GDC",
...}]` — confirming `get_concept`'s synonym `source` tags and
`get_concept_maps`'s cross-vocabulary codes are genuinely different data,
not duplicates.

### LOINC (`src/tooluniverse/data/loinc_tools.json`)

| Tool | Resolves | Auth |
|---|---|---|
| `LOINC_search_tests` | lab-test/observation name -> matching LOINC codes | none |
| `LOINC_get_code_details` | one LOINC code -> full component/property/method detail | none |
| `LOINC_get_answer_list` | LOINC code (or a search term) -> its permissible coded values, if any | none |
| `LOINC_search_forms` | clinical form/panel/survey-instrument name -> matching whole-instrument LOINC codes | none |

LOINC standardizes lab tests, vital signs, and clinical observations —
distinct from ICD (diagnoses) and RxNorm (drugs). **Important, verified
live**: this index (`clinicaltables loinc_items/v3`) does not publish
`SYSTEM` (specimen type), `SCALE_TYP`, `CLASS`, `METHOD_TYP`,
`TIME_ASPCT`, `STATUS`, or `COMMON_TEST_RANK` for any code — every result
returns these as empty strings regardless of the actual code, and the
response itself says so via a `fields_unavailable`/`fields_unavailable_note`
pair. **Never read an empty `SYSTEM`/`CLASS` field as "this code has no
specimen/class" — it means the field isn't in this data source at all.**
Use `LONG_COMMON_NAME`/`COMPONENT`/`SHORTNAME` (which ARE populated) to
disambiguate instead, and note the limitation if a user specifically
needs specimen type.

`LOINC_search_forms` only returns whole instruments (PHQ-9, GAD-7, MMSE,
lab panels) — a single question or individual lab test never appears
here even on a matching keyword; use `LOINC_search_tests` for those.
`LOINC_get_answer_list` distinguishes "code matched but has no coded
answer list" (free-value datatypes like `REAL`/`ST`) from "code not
found" via its `answer_lists_found` count and a `note` field present only
when that count is 0 — don't conflate a `CNE`/`CWE` code with an empty
list with a lookup failure.

Real example chain (`hemoglobin A1c` -> ABO answer list): `LOINC_search_tests
{"terms": "hemoglobin A1c", "max_results": 3}` -> 14 total matches
including `4548-4` ("Hemoglobin A1c/Hemoglobin.total in Blood") ->
`LOINC_get_code_details {"loinc_code": "4548-4"}` confirms
`SHORTNAME: "HbA1c MFr Bld"`, `PROPERTY: "MFr"`, with `SYSTEM`/`CLASS`/etc.
correctly flagged empty via `fields_unavailable`. Separately,
`LOINC_get_answer_list {"loinc_code": "883-9"}` (ABO blood group) returns
`datatype: "CNE"` and a real 4-value answer list (`Group A`/`Group
B`/`Group O`/`Group AB`, each with an `AnswerStringID` like `LA19710-5`) —
this is the exact permissible-value set an EHR would present as a
dropdown for this observation.

See `references/clinical_tables_tool_reference.md` for full parameter
tables and real captured example responses for all 9 of these tools.

## Protein-Annotation Vocabularies: UniProt Disease and Keywords

Two more standardized-vocabulary tool families, from
`src/tooluniverse/data/uniprot_ref_tools.json` — genuinely different from
ICD-10-CM/NCIt above: these are the controlled vocabularies UniProt itself
uses to annotate *proteins* with disease and functional-keyword tags, not
a clinical/EHR coding system. Reach for these when the task is "which
UniProt disease/keyword ID does this term map to" (e.g. before calling a
UniProt-based tool elsewhere that expects a `DI-XXXXX` or `KW-XXXX` ID),
not for clinical documentation.

| Tool | Resolves | Key output |
|---|---|---|
| `UniProtRef_search_diseases` | disease name/symptom/gene -> UniProt disease ID(s) (`DI-XXXXX`) | `id`, `name`, `cross_references[]` (OMIM/MeSH/MedGen/SNOMED), `reviewed_protein_count` |
| `UniProtRef_get_disease` | one `DI-XXXXX` ID -> full definition | `definition`, `alternative_names[]`, `cross_references[]`, `reviewed_protein_count`, `unreviewed_protein_count` |
| `UniProtRef_search_keywords` | functional/biological-process term -> UniProt keyword ID(s) (`KW-XXXX`) | `id`, `name`, `category`, `reviewed_protein_count` |
| `UniProtRef_get_keyword` | one `KW-XXXX` ID -> full definition + hierarchy | `parents[]`, `go_mappings[]` (GO term equivalents), `reviewed_protein_count`, `unreviewed_protein_count` |

Real example chain (verified live): `UniProtRef_search_keywords
{"query": "zinc finger"}` -> `KW-0863` ("Zinc-finger", category `Domain`,
13,427 reviewed proteins) — a *different* keyword from `UniProtRef_get_keyword
{"keyword_id": "KW-0862"}` ("Zinc", category `Ligand`, 43,994 reviewed +
6,677,859 unreviewed proteins) — don't conflate "protein contains a
zinc-finger domain" with "protein binds zinc," they're separate keywords
with separate IDs despite the name overlap. Disease side: `UniProtRef_search_diseases
{"query": "breast cancer"}` -> `DI-03803` ("Breast cancer, lobular") among
others; `UniProtRef_get_disease {"disease_id": "DI-01559"}` -> "Breast-ovarian
cancer, familial, 1" with OMIM/MeSH cross-references and separate
reviewed/unreviewed protein counts.

For downstream "which genes/proteins are actually linked to this disease"
research (not just the disease-name-to-ID mapping these two tools give
you), hand off to `tooluniverse-gene-disease-association`, which already
curates OMIM/GenCC/Gene2Phenotype for that purpose — these UniProt tools
only resolve the term, they don't return the associated protein list
itself (only a count).

See `references/clinical_tables_tool_reference.md` for full parameter
tables and real captured example responses for these 4 tools.

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
