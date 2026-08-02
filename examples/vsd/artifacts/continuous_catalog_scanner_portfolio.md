# Continuous VSD Catalog Scanner Scale Evaluation

## Evaluation objective

Evaluate whether a scheduled VSD scanner can inventory a large public API directory, rotate through changing contracts, compare operations with the real ToolUniverse registry, and prepare hundreds of inert, draft-ready tool configurations without approval or execution.

## Method

Two linked live cycles read the complete APIs.guru OpenAPI Directory response, audited the current ToolUniverse registry, selected previously uninspected OpenAPI 3 contracts across catalog categories, saved content-addressed local snapshots, inspected each operation, and invoked the existing VSD configuration generator for operations that passed the static contract boundary. No provider operation was called.

The broader source-intelligence and contract-inspection path accepts: `openapi`, `graphql`, `asyncapi`, `postman`, `wsdl`, `protobuf`, `mcp`. The large-scale live directory used OpenAPI because it provides a single bounded catalog containing thousands of independently maintained contracts.

## Directory and registry

| Measure | Result |
| --- | ---: |
| Live catalog records | 2,529 |
| Compatible OpenAPI 3 records | 1,521 |
| Unsupported OpenAPI 2 records | 1,008 |
| Catalog response bytes | 8,855,894 |
| ToolUniverse tools audited | 2,744 |
| ToolUniverse source hosts audited | 259 |

## Results

| Measure | Result |
| --- | ---: |
| Linked scan cycles | 2 |
| Unique contracts inspected | 127 |
| Unique operation candidates inventoried | 4,925 |
| Unique draft-ready configuration hashes | 717 |
| Provider hosts represented by draft-ready operations | 31 |
| Blocked operations | 4,281 |
| Isolated contract failures | 24 |
| Catalog categories represented | 31 |

A draft-ready result is a configuration-generation proof, not a published tool. The scanner retained only the candidate identity and configuration hash in its review queue.

## Cycle progression

| Cycle | Added | Changed | Removed | Contracts | Operations | Draft-ready | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1297b5e01f49381b` | 2,529 | 0 | 0 | 66 | 2,880 | 487 | 6 |
| `1fd05c99ac045db2` | 0 | 0 | 0 | 62 | 2,118 | 230 | 18 |

## Representative draft-ready operations

| API | Operation | Request | Registry relationship | Preview identity |
| --- | --- | --- | --- | --- |
| Events API | `getAuthIntrospect` | `GET events.1password.com/api/auth/introspect` | candidate_gap | `VSDScanc71d946215ef05089797` |
| Authentiq API | `key_retrieve` | `GET 6-dot-authentiqio.appspot.com/key/{PK}` | candidate_gap | `VSDScan069e1f90c8b4532ef2cd` |
| Control API v1 | `get_/accounts/{account_id}/apps` | `GET control.ably.net/v1/accounts/{account_id}/apps` | candidate_gap | `VSDScan80401544c7abdd32bc32` |
| IP geolocation API | `get_/v1/` | `GET ipgeolocation.abstractapi.com/v1` | candidate_gap | `VSDScanf7f8180279f07217924b` |
| AGCO API | `Activities_GetActivities` | `GET secure.agco-ats.com/api/v2/activities` | candidate_gap | `VSDScan13c1b3721a6a836c6c8d` |
| Flight Offers Search | `getFlightOffers` | `GET test.api.amadeus.com/v2/shopping/flight-offers` | candidate_gap | `VSDScand400050def693bdeb2a0` |
| Flight Price Analysis API | `get-itinerary-price-metrics` | `GET test.api.amadeus.com/v1/analytics/itinerary-price-metrics` | candidate_gap | `VSDScan47e3f1cc8329b4b87584` |
| api.video | `GET-video` | `GET ws.api.video/videos/{videoId}` | candidate_gap | `VSDScan24cf60efbec5bbadb87f` |
| Swagger API2Cart | `AccountCartList` | `GET api.api2cart.com/v1.1/account.cart.list.json` | candidate_gap | `VSDScan670320e13c45a0486c8a` |
| ApiDapp | `get_/account/{id}` | `GET ethereum.apidapp.com/1/account/{id}` | candidate_gap | `VSDScandcf8b8adb4354a1ec706` |
| Search Services | `get_/search/v1/fields` | `GET api.archive.org/search/v1/fields` | candidate_gap | `VSDScanefaa8335e46919314878` |
| Wayback API | `get_/wayback/v1/available` | `GET api.archive.org/wayback/v1/available` | candidate_gap | `VSDScaneab71b472758db743c57` |
| SearchLy API v1 | `src.searchly.api.v1.controllers.similarity.by_song` | `GET searchly.asuarez.dev/api/v1/similarity/by_song` | candidate_gap | `VSDScaneb50e96aedb55a39a2c8` |
| Big Red Cloud API | `Accounts_Get` | `GET app.bigredcloud.com/api/v1/accounts` | candidate_gap | `VSDScana481e0da95c1ff99a441` |
| Billingo API v3 | `GetBankAccount` | `GET api.billingo.hu/v3/bank-accounts/{id}` | candidate_gap | `VSDScane950ba11652dbdc75588` |
| PeerTube | `get_/api/v1/accounts/{name}/video-channel-syncs` | `GET peertube2.cpy.re/api/v1/accounts/{name}/video-channel-syncs` | candidate_gap | `VSDScanf1bcdbd3570003f85a94` |
| Forem API V1 | `get_/api/pages` | `GET dev.to/api/api/pages` | candidate_gap | `VSDScanfd43a6784423a99b630e` |
| ElevenLabs API Documentation | `Get_default_voice_settings__v1_voices_settings_default_get` | `GET api.elevenlabs.io/v1/voices/settings/default` | candidate_gap | `VSDScan95ebb26752f75be86243` |
| goog.io | Unoffical Google Search API | `Crawl` | `GET api.goog.io/v1/crawl/{query}` | candidate_gap | `VSDScanfe02a6b9556c9cc5ae55` |
| Developer documentation | `getAccountProperties` | `GET api.journy.io/properties/accounts` | candidate_gap | `VSDScan9dce9fb0ad7f556b8b2b` |

## Interpretation

The evaluation demonstrates a practical supply-side growth mechanism: an approved directory can be monitored repeatedly, unchanged sources can be rotated rather than rescanned in every cycle, broken contracts remain isolated, and hundreds of exact read operations can enter a local review queue without becoming executable. Demand ranking and workflow planning can then prioritize which candidates justify the cost of representative verification and maintenance.

## Limitations

Directory inclusion and successful static generation do not establish scientific relevance, provider reliability, or response correctness. The checked cycles intentionally stop before verification, approval, publication, and execution. OpenAPI 2 records are inventoried but not inspected because the current reviewed OpenAPI boundary accepts 3.0 and 3.1 documents.

## Reproduction

```console
PYTHONPATH=src TOOLUNIVERSE_CACHE_PERSIST=false \
  uv run python examples/vsd/continuous_catalog_scanner_case_study.py
```

Portfolio SHA-256: `4181b8af874d3fb6c86a51546b8125fc93b560672732f935d671ff915a5cd054`.
