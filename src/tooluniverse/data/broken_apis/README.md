# Broken / Inaccessible APIs

This folder tracks APIs that were attempted for ToolUniverse integration but confirmed
non-functional after multiple attempts. Each file documents one broken API.

---

## Purpose

Before investing time building a tool for an API, check this folder. If an entry exists,
the API has already been thoroughly investigated and found to be broken. Skip it and use
the documented workaround instead.

## Retry Policy

An API moves into this folder when **all three** conditions are met:

1. **At least 3 independent attempts** failed with the same root cause
2. **Root cause confirmed** — not a transient error (rate limit, maintenance window, etc.)
3. **GitHub/forum search** shows others experiencing the same issue without a fix

## Entry Format

Each JSON file contains:

| Field | Description |
|-------|-------------|
| `api_name` | Human-readable API name |
| `base_url` | The broken endpoint(s) |
| `failure_mode` | HTTP status code or error type |
| `root_cause` | Confirmed technical reason for failure |
| `confirmed_broken_date` | ISO date when confirmed broken |
| `last_retry_date` | ISO date of most recent retry |
| `retry_count` | Total number of attempts made |
| `github_issues` | Links to open issues confirming the bug |
| `retry_after` | Suggested next retry date (or "never") |
| `workaround` | What was implemented instead |
| `attempted_config` | The tool JSON config that was attempted |

## Workflow

```
API attempt fails
      │
      ▼
Is this a transient error?  ──yes──► Wait and retry (max 3 times)
      │ no
      ▼
Search GitHub/forums for others reporting the same issue
      │
      ▼
Still broken after 3 attempts + confirmed root cause?
      │ yes
      ▼
Create entry in broken_apis/<api_name>.json
Document workaround (alternative API, local computation, etc.)
Update api-tool-builder agent memory
      │
      ▼
Implement workaround tool instead
```

## Retry Schedule

Review entries periodically:
- Entries with `retry_after` dates in the past should be retried
- If fixed: remove from this folder and build the real tool
- If still broken: update `last_retry_date` and `retry_count`

## Current Entries

| File | API | Broken Since | Workaround |
|------|-----|-------------|------------|
| `metaboanalyst_rest.json` | MetaboAnalyst public REST API | 2024-12 | KEGG REST + local scipy |
| `drugcentral_rest.json` | DrugCentral REST API | 2026-02 | OpenFDA Drugs@FDA API (openfda_approval_tools.json) |
| `ttd_rest.json` | TTD (Therapeutic Target Database) REST API | 2026-02 | Open Targets, DGIdb, ChEMBL, Pharos |
| `repodb_rest.json` | RepoDB Drug Repurposing Database | 2026-02 | Open Targets, ChEMBL, ClinicalTrials.gov |
| `scop2_rest.json` | SCOP2 (Structural Classification of Proteins 2) | 2026-02 | CATH, InterPro, PDBe |
| `decipher_api.json` | DECIPHER Rare Disease Variants API | 2026-02 | Orphanet (Orphadata + RDcode) + GenCC |
