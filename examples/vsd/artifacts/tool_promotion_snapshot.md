# Reviewed Tool Promotion: Cancer-Trial Case Study

## Result

One discovery candidate produced two distinct, narrow ToolUniverse tools. Each tool passed three live provider cases, was approved against the exact verification hash, was published atomically, loaded into a fresh ToolUniverse instance, and executed again.

- Provider: `https://data.ny.gov/resource/2ig8-yxf8.json`
- Dataset: `2ig8-yxf8`
- Loaded tools: `VSDGeneratedCancerTrialsByPhase`, `VSDGeneratedCancerTrialsBySite`
- Boundary: This validates software contracts and live retrieval, not trial quality, clinical relevance, or scientific conclusions.

## Promotion Evidence

| Tool | Required filter | Verification cases | Rows observed | Operation hash |
| --- | --- | ---: | --- | --- |
| `VSDGeneratedCancerTrialsBySite` | `primary_site` | 3 | 19, 23, 20 | `1b11bb8efdd7de75...` |
| `VSDGeneratedCancerTrialsByPhase` | `study_phase` | 3 | 25, 25, 25 | `5e49d68e48d1abf0...` |

## Fresh Runtime Check

| Tool | Query | Rows | Payload hash |
| --- | --- | ---: | --- |
| `VSDGeneratedCancerTrialsBySite` | `primary_site=Breast` | 23 | `5562338d7fdf189f...` |
| `VSDGeneratedCancerTrialsByPhase` | `study_phase=III` | 25 | `322b0476c5a33b91...` |

## What This Proves

1. Discovery metadata alone never executes and never enters the approved directory.
2. Generation converts reviewed fields into bounded GET contracts with mandatory filters.
3. Verification uses ToolUniverse itself and records counts, fields, timestamps, and hashes without storing entire provider responses.
4. Approval and publication fail if the draft, evidence, or approval chain changes.
5. Published tools are loaded only by an explicit call and cannot replace an existing tool.

## Interpretation

This validates software contracts and live retrieval, not trial quality, clinical relevance, or scientific conclusions.
