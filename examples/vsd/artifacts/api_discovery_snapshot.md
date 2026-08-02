# Demand-Driven API Discovery Validation

## Decision Question

Can ToolUniverse discover an API-ready public dataset for analyzing active cancer trials by protocol, site, phase, title, opening date, and investigator without executing an unreviewed endpoint?

## Search Result

- Demand query: `active cancer clinical trials primary site phase protocol`
- Catalog matches: **13**
- Normalized API candidates: **10**
- Candidates passing the review-readiness screen: **1**

## Candidate Comparison

| Candidate | Score | Fields | Capabilities | Official | Government | Review next |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Current Active Clinical Trials - Roswell Park Cancer Institute | 0.9000 | 7 | 6/6 | yes | yes | yes |
| Public Health Activities and Services - 2014 | 0.5563 | 47 | 0/6 | yes | yes | no |
| Texas Commission on Environmental Quality - Water Quality General Permits Active/Pending | 0.5563 | 23 | 0/6 | yes | yes | no |
| Texas Commission on Environmental Quality - Water Quality Individual Permits Active/Pending | 0.5563 | 22 | 0/6 | yes | yes | no |
| Emissions Inventory System (EIS) Facilities 2017 - Current County Environmental Protection | 0.4875 | 45 | 0/6 | yes | yes | no |
| Public Health Activities and Services - 2013 | 0.4875 | 50 | 0/6 | yes | yes | no |
| Public Life Data - Locations | 0.4875 | 20 | 0/6 | yes | yes | no |
| COVID-19 Vaccination Locations - Historical | 0.4375 | 16 | 0/6 | yes | no | no |
| Energy and Water Data Disclosure for Local Law 84 2022 (Data for Calendar Year 2021) | 0.4375 | 50 | 0/6 | yes | no | no |
| Property | 0.4188 | 50 | 0/6 | yes | yes | no |

## Selected for Contract Review

- Name: **Current Active Clinical Trials - Roswell Park Cancer Institute**
- Candidate ID: `31dcb2ce74f62d7c`
- Proposed API endpoint: `https://data.ny.gov/resource/2ig8-yxf8.json`
- Catalog record: https://data.ny.gov/d/2ig8-yxf8
- Dataset updated: `2026-04-14T21:08:58.000Z`
- Execution allowed: **no**

| Requested capability | Candidate field |
| --- | --- |
| stable trial identifier | `protocol` |
| cancer site | `primary_site` |
| study phase | `study_phase` |
| study title | `title` |
| opening date | `date_opened` |
| principal investigator | `principal_investigator` |

## Reproducibility

- Catalog endpoint: `https://api.us.socrata.com/api/catalog/v1`
- Retrieved at: `2026-08-01T01:21:26.815204+00:00`
- Catalog payload: `5f6e0ccff73a84da93b8d5c1c0780445f48b6946c015b048d70f371436d9657a`
- Selection rule: Official catalog label, government API domain, API-ready schema, and at least five of six demanded capabilities; then most capabilities, highest discovery score, and stable candidate ID.

## Interpretation Boundary

Selection means suitable for human contract review only. It does not approve the source, validate its scientific content, or execute it.
