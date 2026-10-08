# On-demand remote providers

How one GPU host shares several models without keeping them all resident, what the
first implementation does, and what the remaining goals need that it cannot reach.

## The problem

`tu remote run` and `tu remote share` bind exactly one provider per invocation.
`implementation` is a single required positional argument, `RelayAgent` is constructed
with one fixed `deployment.endpoint`, and the command blocks in the foreground until
Ctrl-C, at which point `finally: stop_provider(managed)` stops what it started.

Sharing three models therefore costs three terminals and three resident processes. A
model nobody is calling still holds its GPU memory, so the number of models a host can
advertise is capped by what its GPU can hold *simultaneously* rather than by what it
can load *one at a time*.

Nothing starts on demand. If the agent for a shared provider is not connected, the
platform answers a call with 503:

```sql
-- handlers/remote_published_tools.go
AND rs.online = true AND (rs.expires_at IS NULL OR rs.expires_at > NOW())
```
→ `503 "The provider's remote MCP server is offline or unavailable"`

and there is no path by which it could do anything else. The tunnel carries only
proxied HTTP:

```go
// tunnel/registry.go
type Request  struct { ID, Method, Path string; Headers map[string]string; Body string; ... }
type Response struct { ID string; StatusCode int; Headers map[string]string; ... }
```

There is no control-plane message, so the platform cannot ask a connected agent to
start anything. It can only forward a request to the endpoint the agent already bound.

## Design

Put the multiplexing on the GPU host, in front of the relay, instead of changing the
relay or the platform:

```
                    ┌───────────────────── GPU host ─────────────────────┐
 caller ──relay──▶  │  RelayAgent  ──▶  pool :7999  ──┬──▶ boltz    :8080│  started on
 (TU Platform)      │  (unchanged)      (new)         │                  │  first call
                    │                                 ├──▶ esm      :8008│  idle, stopped
                    │                                 └──▶ enformer :8011│  never started
                    └────────────────────────────────────────────────────┘
```

The pool is an ordinary Streamable-HTTP MCP endpoint on loopback. `RelayAgent` points
at it exactly as it would point at a single provider, so **no change to
`tuplatform-connect`, the tunnel protocol, the platform, or the database** is required.

```bash
tu remote pool --allow boltz,esm,enformer --share
```

### Routing by tool name

Tool names are globally unique across the reviewed catalog — 41 operations, 41 distinct
names, zero collisions — so a `tools/call` identifies its provider without any
caller-supplied selector, extra header, or schema change.

`build_tool_index` refuses to start if two allowed providers ever claim the same name,
because the alternative is silently routing calls to whichever was registered last.
`test_every_reviewed_tool_name_resolves_to_exactly_one_provider` pins that invariant
against the real catalog, so a future provider that reuses a name fails in CI rather
than in production.

Routing uses the static `RemoteDeployment.operations` table, not discovery, so a
provider is routable even before its schema has ever been snapshotted.

### Discovery without starting anything

Most providers declare their schemas inside `<slug>_tool.py`; only one of the thirty
ships a `*_client_tools.json`. So schemas cannot be read without a running provider,
and `tools/list` cannot be answered from static metadata alone.

`SchemaStore` snapshots each provider's `tools/list` once and caches it on disk. After
that, discovery is served entirely from cache and starts nothing: a caller can browse
every model the host shares while the GPU sits empty. Snapshots are keyed by the
provider module's size and mtime, so upgrading a provider invalidates its entry rather
than publishing a stale schema.

`--warm` snapshots providers one at a time, so warming a host that advertises more
models than fit together never needs them resident together. Sharing implies warming
any provider that has no snapshot, because a manifest missing those tools would publish
an online server that does not list what it can actually run.

### Admission and eviction

`--max-active` bounds how many providers are resident; the default is 1, because one
large model usually fills a GPU. Admitting a new provider evicts the
least-recently-used **idle** one. A provider with a call in flight is never evicted —
the caller is told to retry instead, since the alternative is killing a running GPU job
to admit a new one.

`--idle-ttl` (default 900s) stops providers that stop being called, returning their
memory without operator involvement.

Two concurrent first-calls for the same model must not both launch it, so a slug being
started is tracked and the second caller gets `ProviderStarting`.

### Failure semantics

| condition | response | why |
|---|---|---|
| provider starting | `503` + `Retry-After: 15` | retry the same call; a JSON-RPC error would read as "this tool is broken" |
| all slots busy | `503` + `Retry-After: 10` | same, and never evict a running job |
| unknown tool | JSON-RPC `-32601`, HTTP `200` | **not** 404/405/410 — the relay agent treats those on its POST route as endpoint loss and tears down the shared tunnel for every caller |
| provider start failed | JSON-RPC `-32603` | the tool exists; this attempt failed |
| `GET` (SSE) | `501` | deliberately not 405, for the same tunnel-teardown reason |

The pool is sessionless. It holds no per-caller state, so there is no session to lose
when a provider underneath is stopped and restarted between two calls.

A provider that `ensure_provider` *adopted* — already running, started by another
terminal or by systemd — is tracked with `managed=None` and is never stopped by the
pool, not on eviction and not on shutdown.

## What this does not do

These are the remaining parts of "just run one command and let `tu` launch whatever is
needed", and each needs something the pool cannot reach from behind the relay.

**Scheduling across hosts.** Each agent is one tunnel bound to one `server_id`. Routing
a tool to whichever of several GPU hosts can serve it soonest is a platform-side
scheduling concern, not an agent-side one.

**Starting a provider the operator did not allow.** `--allow` is the security boundary
and is deliberately explicit: the pool starts local processes, so the set of startable
providers must come from the host's owner, never from a caller's request.

## The control plane

Implemented as `kind = 3` on the existing binary framing (`1 = request`, `2 = response`),
so it reuses the correlation map, timeouts and cancellation that already exist and adds
no second transport.

| op | who | effect |
|---|---|---|
| `status` | owner or member | what the host shares, what is loaded, `max_active`, `idle_ttl` |
| `prewarm` | owner or member | start a provider before the call that needs it |
| `stop` | **owner only** | unload a provider; refuses while a call is in flight |

`prewarm` returns as soon as it has started loading, because a model takes minutes and a
control call is bounded in seconds; readiness is read back through `status`. A prewarmed
provider deliberately holds no in-flight slot, or it could never be evicted or reaped.

Three rules carry the safety of this path:

- **Capability is negotiated, never assumed.** An agent advertises `control_protocol` in
  its handshake. Agents predating this raise on an unrecognised frame kind and drop the
  tunnel, taking every in-flight call with them, so the platform refuses to send a control
  frame to a connection that did not advertise support.
- **The transmittable op set is closed.** The tunnel validates against `controlOps` rather
  than relaying an arbitrary string, because each op runs as a local process action on
  someone else's machine.
- **The agent's `--allow` list is the real boundary.** The provider name is relayed from a
  caller, so the pool refuses any slug the host's operator did not share.

A control failure is answered, never raised: an exception on the agent side would close
the WebSocket and kill every in-flight tool call because one control message was
malformed.

### Admitting on memory, not just on count

`--max-active` is a count, and a count cannot express that two small models fit where one
large one does not. Memory can, but nothing declares what a reviewed provider costs: there
is no `provider.toml`, no figure in any of the thirty READMEs, and no field on
`RemoteDeployment`. Writing a table of numbers would be guessing about other people's
hardware.

So the pool measures instead. Free VRAM before a start, free VRAM once the provider
answers, and the difference is what that model costs *on this machine*. `FootprintStore`
caches it beside the schema snapshots. A provider's first load is therefore admitted on
count alone — there is nothing to reason with yet — and every later one can be admitted on
memory.

Three decisions worth keeping:

- **The largest measurement wins.** A model that allocates lazily looks smaller on a run
  that only initialised it, and admitting on that smaller number overcommits the GPU the
  next time it is really used.
- **Freed memory is estimated from the victims' own measurements, not re-read from the
  driver.** A stopped process does not return its VRAM immediately, so a fresh reading
  straight after a kill reports the memory as still in use. A victim nobody has measured
  yet counts as freeing nothing, which can refuse an admission that would have fit —
  preferred over the opposite error.
- **The most free device is reported, never the sum.** One provider lands on one GPU, so a
  sum would claim room no single model can use. The pool does not choose placement, so
  this is an upper bound on what the next model can expect rather than a guarantee.

Memory pressure never evicts a provider with a call in flight, exactly like the count
ceiling: the caller is told to retry instead of having a running GPU job killed under it.

Reading the GPU degrades to "do not reason about VRAM" rather than to "no memory": no
`nvidia-smi`, a non-zero exit, or a reading that is not a number. That last case is not
hypothetical — a machine used to develop this has `nvidia-smi` present and answering
`[N/A]` for `memory.free`, and admitting against that would be worse than ignoring it.
Twenty of the thirty reviewed providers need no GPU at all, so count-only admission stays
a normal mode of operation rather than a fallback.

### Waiting out a cold model

A call can still arrive for a model that is not loaded, and the pool answers it with 503
because it cannot hold the request: the relay agent abandons a local request after 25
seconds and that timeout tears the tunnel down for everyone on the host. A model load
takes minutes, so waiting here would trade one failed call for an outage.

The platform absorbs it instead, where the per-tool budget of up to 900 seconds already
lives: a 503 is re-dispatched after 2s, 4s, 8s, then 15s, capped at six attempts and only
while the pause plus a usable remainder still fits the caller's timeout. Only 503
qualifies — it is the one status that says the tool did not run, so a retry cannot
duplicate a side effect, whereas 502 and 504 can both mean the call executed and its
answer was lost.

That is why the pool deliberately has no pre-wait of its own. A few seconds there would
spare one round trip on a fast load, at the cost of moving every request closer to the
25-second cliff.

Control dispatch is local-connection only. The Redis coordinator forwards request frames
between replicas and has no control representation, so a control call for an agent on
another replica reports no agent rather than silently doing nothing.

## Verified

Unit tests (`tests/unit/test_remote_pool.py`, 35 cases) drive routing, admission,
eviction, idle reaping, snapshot invalidation and the HTTP surface with injected
lifecycle callables — no GPU, no provider environment, no network. Mutation-checked:
replacing LRU selection with an arbitrary pick, dropping the in-flight guard, or
dropping the concurrent-start guard each fail their own test.

End-to-end against two real provider subprocesses over real HTTP, counting actual
process launches: nothing starts at boot; `tools/list` stays empty and starts nothing;
`--warm` starts each provider once and leaves nothing resident; a `tools/call` launches
only its owner; a repeat call reuses it; calling the other model evicts the first at
`--max-active 1`; idle reaping stops it; an unknown tool returns `-32601` rather than a
tunnel-killing 404.
