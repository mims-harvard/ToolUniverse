# GA4GH Service Qualification Portfolio

## Scope

This evaluation asked whether an official registry entry was sufficient to create a usable ToolUniverse operation. VSD derived only the standard Service Info path, then required live response structure and registered service-type agreement before approval.

The same parameterized runner evaluated every service; organization names, URLs, expected outcomes, and replay responses are scenario data.

## Results

- Evaluated services: `15`
- Accepted and published: `3`
- Rejected before approval: `12`
- Verification executions: `9`
- Fresh-universe executions: `3`
- Live cases: `15`
- Checked-replay cases: `0`
- Portfolio SHA-256: `8f20711089278a292c9f88d86fd40c8fa3fbc4f887f2d7d104f3408013e63243`

| Registry record | Standard | Endpoint | Result | Evidence |
| --- | --- | --- | --- | --- |
| org.ga4gh.registry | service-registry 1.0.0 | https://registry.ga4gh.org/v1/service-info | accepted | 3 conformance calls, publication, fresh load, and final execution |
| gov.nih.nlm.ncbi.drs | drs 1.2.0 | https://locate.be-md.ncbi.nlm.nih.gov/ga4gh/drs/v1/service-info | accepted | 3 conformance calls, publication, fresh load, and final execution |
| org.dockstore.dockstoreapi | trs 2.0.1 | https://dockstore.org/api/ga4gh/trs/v2/service-info | accepted | 3 conformance calls, publication, fresh load, and final execution |
| com.sbgenomics.cavatica-ga4gh-api.wes | wes 1.0.0 | https://cavatica-ga4gh-api.sbgenomics.com/ga4gh/wes/v1/service-info | rejected | registered metadata mismatch |
| com.sbgenomics.cgc-ga4gh-api.wes | wes 1.0.0 | https://cgc-ga4gh-api.sbgenomics.com/ga4gh/wes/v1/service-info | rejected | registered metadata mismatch |
| gov.nih.nhlbi.biodatacatalyst.sb.ga4gh-api.wes | wes 1.0.0 | https://ga4gh-api.sb.biodatacatalyst.nhlbi.nih.gov/ga4gh/wes/v1/service-info | rejected | registered metadata mismatch |
| com.sb.cavatica.drs | drs 1.3.0 | https://cavatica-ga4gh-api.sbgenomics.com/service-info | rejected | execution failure |
| com.sb.cgc.drs | drs 1.3.0 | https://cgc-ga4gh-api.sbgenomics.com/service-info | rejected | execution failure |
| com.sb.bdc.drs | drs 1.3.0 | https://ga4gh-api.sb.biodatacatalyst.nhlbi.nih.gov/service-info | rejected | execution failure |
| eu.crg.rnaget | rnaget 1.0.0 | https://genome.crg.cat/rnaget/service-info | rejected | execution failure |
| bio.terra.data | drs 1.3.0 | https://data.terra.bio/service-info | rejected | response media type mismatch |
| io.datacommons.gen3.drs | drs 1.2.0 | https://gen3.datacommons.io/service-info | rejected | response media type mismatch |
| io.datacommons.nci-crdc.drs | drs 1.2.0 | https://nci-crdc.datacommons.io/service-info | rejected | response media type mismatch |
| ai.viral | drs 1.3.0 | https://viral.ai/service-info | rejected | redirect rejected |
| api.service.nhs.uk/genomic-data-access | drs 1.4.0 | https://sandbox.api.service.nhs.uk/genomic-data-access/service-info | rejected | execution failure |

## Lifecycle Evidence

Every discovered candidate was non-executable and content-addressed. All 15 drafts were blocked from publication before verification. The three conforming services passed registry-bound assertions three times, were explicitly approved and published, remained absent from a fresh ToolUniverse until loaded, executed successfully after loading, and were suppressed from the next discovery result as exact duplicates.

The other 12 candidates produced no approval or publication artifact. They included valid JSON with service-type drift, unavailable standard paths, HTML responses at API-looking URLs, and a redirect.

## Interpretation

Without VSD, the registry supplies useful leads but does not establish that their standard metadata operation is reachable or still agrees with the registered contract. With VSD, conforming leads become narrow, auditable ToolUniverse operations while stale or inconsistent records fail before approval. In this snapshot, indiscriminate registration would have treated all 15 records as usable; qualification admitted three and prevented 12 unsupported additions.

## Reproduction

```console
PYTHONPATH=src python examples/vsd/ga4gh_service_qualification_portfolio.py --mode replay
PYTHONPATH=src python examples/vsd/ga4gh_service_qualification_portfolio.py --mode network_backed
```

Replay uses checked provider-shaped responses. Network-backed mode labels each service independently as live or checked replay and records the bounded reason for any fallback.
