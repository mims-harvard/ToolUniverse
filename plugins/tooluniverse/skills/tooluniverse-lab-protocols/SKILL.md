---

name: tooluniverse-lab-protocols
description: "Find and inspect published, peer-reviewed or community lab protocols from protocols.io — search by technique/keyword, pull a protocol's full description and materials list, or get its ordered step-by-step instructions. Use when someone asks to \"find a protocol for X\", \"how do others do [technique]\", \"get the steps for protocol [ID/DOI]\", or \"check the materials list for this method\" before designing or running a wet-lab experiment. NOT for designing a novel cloning/assembly strategy from scratch (use tooluniverse-molecular-cloning), NOT for primer design (use tooluniverse-primer-design). Honest: protocols.io requires an OAuth Bearer token (PROTOCOLS_IO_API_KEY) for every call, including public reads — without it these tools are blocked, not degraded."
---

# Lab Protocol Discovery (protocols.io)

Find a published, step-by-step lab protocol before designing your own from scratch, or pull the exact steps/materials for a protocol someone already pointed you to.

## Honesty contract (read first)

1. **This requires a real API key.** protocols.io's API requires `Authorization: Bearer <token>` on every endpoint, including protocol search — there is no anonymous tier. If `PROTOCOLS_IO_API_KEY` is not set, the tools return a clean error naming the missing key rather than a raw HTTP failure. Tell the user plainly that a key is needed and point them to https://www.protocols.io/api-clients to register an API client and obtain one.
2. **Never fabricate a protocol.** If the key is missing or a lookup fails, say so — do not describe a plausible-sounding protocol from memory and present it as if it came from protocols.io.
3. **Tokens expire (~1 year).** A previously-working key that starts failing with an auth error may simply need refreshing, not re-registering from scratch.

## When to Use This Skill

Apply when users:
- Want to find a published protocol for a specific technique before running it themselves (e.g., "is there a protocols.io method for lentiviral titering?")
- Already have a protocols.io ID, URI slug, or DOI and want its full description, materials list, or step-by-step instructions
- Want to compare how different labs perform the same technique

**NOT for** (route elsewhere):
- Designing a novel Gibson/Golden Gate assembly strategy -> `tooluniverse-molecular-cloning`
- PCR primer design -> `tooluniverse-primer-design`
- General plasmid/reagent sourcing (Addgene) -> already covered by `Addgene_*` tools

## Workflow

### 1. Search for a protocol by technique/keyword

```
ProtocolsIO_search_protocols {"query": "<technique or keyword>", "limit": <1-50, default 10>, "order_field": "relevance"|"activity"|"date"|"name"|"id"}
```

Returns candidate protocols with `id`, `title`, `doi`, `authors`, `published_on`. Pick the most relevant hit — do not assume the first result is the best match; check the title against what the user actually wants.

### 2. Get full detail for one protocol

```
ProtocolsIO_get_protocol {"protocol_id": "<id, URI slug, or DOI>", "content_format": "json"|"html"|"markdown"}
```

Returns `title`, `description`, `materials`, `authors`, `doi`. `protocol_id` accepts the numeric ID from step 1's search results, a protocols.io URI slug, or a DOI (e.g. `dx.doi.org/10.17504/protocols.io.xxxxx`) if the user already has one.

### 3. Get the ordered steps

```
ProtocolsIO_get_protocol_steps {"protocol_id": "<same as step 2>", "content_format": "json"|"html"|"markdown"}
```

Returns `steps` as an ordered array, each with its `components` (text, reagents referenced, timers, images). Use this once a specific protocol has been identified — it's the actual bench-level instructions, not just metadata.

## Notes

- Search (`ProtocolsIO_search_protocols`) uses the v3 API; per-protocol detail and steps use the newer v4 API — this is a real API-versioning quirk in protocols.io itself, not an inconsistency in this tool.
- **Live-verified**: an invalid/malformed Bearer token returns **HTTP 400**, not 401/403 as the API docs' general auth-error convention would suggest — confirmed by actually calling the live API with a dummy key. If a call fails with "protocols.io returned HTTP 400," check the token before assuming the request itself is malformed.
- The response-body schemas here (protocol fields, step structure) were built directly from protocols.io's published API documentation (https://apidoc.protocols.io/), not live-verified end-to-end in this environment (no real API key was available at authoring time). If a response shape doesn't match what's documented here once a real key is in use, trust the live response and treat this doc as a starting point, not ground truth.
