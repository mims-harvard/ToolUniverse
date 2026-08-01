# Multi-format VSD Contract Proof

## Research question

Can six incompatible provider contract formats be converted into a reviewable inventory for an SMA evidence workflow without executing provider calls, opening listeners, or running local commands?

## Result

Yes. Ten operations across six formats were inventoried with exact source and candidate identities; safe read candidates were separated from mutations, event transports, SOAP, gRPC, and local MCP commands that require later explicit review.

| Case | Format | Operations | Reviewable | Blocked |
| --- | --- | ---: | ---: | ---: |
| Rare-disease registry GraphQL | `graphql` | 2 | 1 | 1 |
| Post-market safety AsyncAPI | `asyncapi` | 1 | 0 | 1 |
| Natural-history cohort Postman collection | `postman` | 2 | 1 | 1 |
| Molecular diagnostics WSDL | `wsdl` | 1 | 0 | 1 |
| Variant evidence gRPC/protobuf | `protobuf` | 2 | 0 | 2 |
| Literature synthesis MCP manifest | `mcp` | 2 | 1 | 1 |

All 27 assertions passed. Case identity: `13259b09e2177b83969f210445f9ed1bbe8013e7d715f493bebc6612dc268e35`.

The inspection used only local contract files. No provider request, listener, RPC channel, or local MCP command was executed.
