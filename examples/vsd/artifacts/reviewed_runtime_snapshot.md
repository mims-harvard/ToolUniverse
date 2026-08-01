# Reviewed Multi-protocol Runtime Proof

## Clinical question

Can ToolUniverse combine rare-disease genes, longitudinal motor scores, molecular diagnostics, trials, safety signals, literature, and variant classification when providers use incompatible reviewed protocols and formats?

## Result

Yes. Ten runtime cases exercised reviewed GraphQL, REST, SOAP, gRPC, MCP, webhook, OAuth, multipart, pagination, JSON, CSV, XML, HTML, binary, and SSE contracts; an eleventh case completed draft-through-fresh-runtime promotion.

| Case | Transport | Protocol | Pages/messages | Payload identity |
| --- | --- | --- | ---: | --- |
| Rare-disease GraphQL with OAuth | `http` | `graphql` | 1 | `2faaf6b7d55016e1` |
| Paginated SMA cohort CSV | `http` | `rest` | 3 | `a4a734b55b652ad5` |
| Legacy molecular panel SOAP | `http` | `soap` | 1 | `b68f75b308893a75` |
| Clinical-trial HTML table | `http` | `rest` | 1 | `9157eed716a090df` |
| Binary evidence report | `http` | `rest` | 1 | `62c329fbc1737834` |
| Bounded safety SSE | `http` | `rest` | 1 | `e93f3deb07ddbbdc` |
| In-memory multipart analysis | `http` | `rest` | 1 | `4a2c257c79113e6a` |
| SMN1 variant gRPC | `grpc` | `grpc` | 1 | `dcdf7c836aabc11a` |
| Pinned literature MCP | `mcp` | `mcp` | 1 | `e1a9484cabbc1513` |
| Signed safety webhook | `event` | `webhook` | 1 | `01abf0c0641f08dc` |

## Promotion proof

Candidate `c837126c2a40ae52` was bound to draft `promotedsmnpanelsoap_75b3146b1be8`, verified with three cases, approved, published, loaded into a fresh ToolUniverse instance, and executed for sample `S-404`.

All 33 assertions passed. Case identity: `05e0870fe14c61d560e483fcec472c9eeeabfb28f1042587fbe37e56ab8bd310`.

Provider fixtures are deterministic because no provider credentials are bundled. Contract validation, request construction, response decoding, schema validation, provenance, promotion, publication, and loading use production code.
