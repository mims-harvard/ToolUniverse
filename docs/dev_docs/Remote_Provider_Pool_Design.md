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

### One interpreter per provider

A provider's environment is its own: `tu remote run` resolves
`TOOLUNIVERSE_REMOTE_<SLUG>_PYTHON`, then `TOOLUNIVERSE_REMOTE_PYTHON`, then
`.venvs/<slug>/bin/python` — per provider, and so does `check_environment`, which is what
`tu serve` prints "environment ok" from. The pool resolves it the same way, for each
provider it starts.

It used to resolve one interpreter, from the first name in `--allow`, and start every
provider with that. Measured on this project's GB10 with
`TOOLUNIVERSE_REMOTE_ENFORMER_DEEPMIND_PYTHON` pointing at a second environment: the
check read it, the start ignored it, and `enformer_deepmind`'s server ran in the
interpreter resolved for `borzoi_calico`. So sharing two providers whose pinned stacks do
not coexist — which is why a resident provider splits its server from its model at all —
was the one thing a pool could not do, and it surfaced as a missing import inside the
second provider rather than as anything about the pool.

`--python` is still one interpreter for all of them, resolved before anything starts,
because naming one is what asks for that.

### Admission and eviction

`--max-active` bounds how many providers are resident; the default is 1, because one
large model usually fills a GPU. Admitting a new provider evicts the
least-recently-used **idle** one, and `--max-active 0` drops the count and lets the
memory ceiling decide alone (see "Letting memory decide alone"). A provider with a call
in flight is never evicted — the caller is told to retry instead, since the alternative
is killing a running GPU job to admit a new one.

`--idle-ttl` (default 900s) stops providers that stop being called, returning their
memory without operator involvement.

Two concurrent first-calls for the same model must not both launch it, so a slug being
started is tracked and the second caller gets `ProviderStarting` — or waits for that start
to finish, where the host has asked for it (`start_wait_s`, 0 by default; see "Waiting out
a cold model").

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
| `status` | owner or member | what the host shares, what is loaded (`model_loaded` per provider that keeps a worker), `max_active`, `idle_ttl` |
| `prewarm` | owner or member | start a provider **and load its model** before the call that needs it |
| `stop` | **owner only** | unload a provider; refuses while a call is in flight |

`prewarm` returns as soon as it has started loading, because a model takes minutes and a
control call is bounded in seconds; readiness is read back through `status`. A prewarmed
provider deliberately holds no in-flight slot, or it could never be evicted or reaped.

**A prewarm loads the model, which it did not used to.** Starting a resident provider's
server is not warming it: the server is a CPU-only process that binds its port and waits,
and the weights go in when the first request starts the worker. Measured on this project's
GB10, `boltz`'s port answered 12.5 s after the prewarm and its model was in memory 31.3 s
after it — so a prewarm that stopped at the port hid 12.5 s of a 31 s wait and reported the
provider ready for the other 19. So the pool now starts a prewarmed provider with
`TOOLUNIVERSE_REMOTE_WARM_MODEL=1` in its environment, and
`remote_resident.backend.warm_if_requested` — reached by both shapes of provider server,
the shared `mcp_tool_registry.start_mcp_server` and a hand-written FastMCP one — loads the
model in a thread while the port binds. A real call never sets it: the call loads the model
by being the request that loads it.

Because "running" and "holding its model" are now different states, `status` reports
`model_loaded` for every provider that keeps a worker, read from the process table. It is
absent, rather than `false`, for a provider with no worker to look for and on a host whose
process table cannot be read.

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
large one does not. Memory can, and two sources answer what a model costs:

- **The provider's own manifest.** `[gpu] vram_budget_gb` is a measured peak — `tu remote
  room` prints 28 of them — measured on the machine that verified that provider, which
  makes it a prior anywhere else and not a reading. That is what it is used as.
- **This host's own measurement.** Free memory before the provider started, free memory
  once its model is actually in memory, and the difference is what it costs *here*.
  `FootprintStore` caches it beside the schema snapshots. *When* the second reading is
  taken depends on where the provider keeps its model, and that is the whole of it: see
  "Measuring the model and not the server" below.

Admission decides on the **larger of the two**, because each one can be the low one and
either being low overcommits the machine:

- a declared budget can be low here, because this is not the machine it was measured on;
- a local measurement can be low because a provider loads its model on the FIRST REQUEST
  and not when its server binds — a resident one in its worker, the rest lazily in the
  server process. `wait_until_ready` returns once `tools/list` matches the reviewed
  contract, which it does with the card still empty, so a difference measured across a
  start is the server's own memory rather than the model's. Reading the manifests is what
  makes the memory ceiling apply to the 32 resident providers at all, and not merely
  sooner.

A provider that declares nothing and has never been loaded here is still admitted on count
alone: 28 of the 60 reviewed slugs declare no budget, so count-only admission stays a
normal mode of operation rather than a fallback.

#### What a declared zero is worth, and on which machine

`[gpu] policy = "none"` is a measurement: three of these providers' kits publish no
GPU-capable wheel for this architecture, so they hold no device memory at all, and
`borzoi_calico`'s manifest draws the conclusion — ~10 GiB of host RSS and no VRAM, so it
"is admitted while the card is full, which is what a variant-scoring job wants to be when
a folding model owns the GPU". On a discrete-GPU host that is exactly right.

On unified memory it is not. `pool_free_gib` answers there with `MemAvailable`, because
the weights, the host RSS and the page cache all come out of one 121 GiB pool — so the
10 GiB that provider holds is spent from the pool admission is reading, and calling it
free admits a 10 GiB resident as though it were nothing. The old answer skipped the
*measurement* for the same providers, so the figure stayed unlearnable as well as
unknown.

So `admission.pool_is_shared_with_the_host()` decides what the declaration is worth, off
which machine `capacity_gib` answered from rather than a second detection that could
drift from it: on unified memory a declared 0 becomes **unknown** — measured after the
first call the provider answers, bounded one at a time until then — and on a discrete
device it stays 0, read for nothing and recorded for nothing. A machine that cannot say
which kind it is keeps the manifest's answer, since it has no free reading to protect
either. The answer is read once per pool; a failed reading is not kept.

#### Letting memory decide alone

`--max-active 0` means "no count ceiling, memory decides". It exists because the default
of 1 is the one setting an operator cannot tune honestly: on a 121 GiB machine sharing
five 6 GiB models, a count of 1 leaves four of them being loaded and unloaded against a
pool that could have held all five, and a count of 5 is a promise about sizes the
operator would have to keep re-checking as manifests change. Memory already knows both
halves of that — what the machine has and what each model costs — so 0 hands it the
decision rather than asking for a number that stands in for one.

Two things keep that from meaning "unbounded":

- **It is refused where memory cannot be read.** If `capacity_gib` cannot answer — no
  NVIDIA driver, no unified memory to fall back on — then dropping the count would leave
  nothing deciding at all, so the pool refuses to start and says to pass a count.
  Capacity rather than the free reading, because both come from the same detection of
  which kind of machine this is and capacity is the one that does not move: a pool is
  not refused over a driver that was busy for a second.
- **A provider nobody has costed is still admitted one at a time.** Memory can only
  judge a provider with a figure, and for the 28 that declare nothing and have never
  been loaded here there is none, so with the count gone their loads would be admitted
  on no evidence at all. Those keep the ceiling every provider used to have until a call
  one of them answered has been measured here, and then memory speaks for them like
  anything else. The bound is on ignorance and not on size: a 6 GiB model and a 38 GiB
  model both have a figure, and memory is allowed to decide about both. A `[gpu] policy =
  "none"` provider has a figure on a discrete-GPU host and has none on unified memory, for
  the reason "What a declared zero is worth" gives above.

The default stays 1. 0 is a statement about the machine, and the person running the
command is the one who knows whether this machine has room for several models.

Decisions worth keeping:

- **The largest figure wins**, for both of the reasons above. A model that allocates lazily
  also looks smaller on a run that only initialised it.
- **Freed memory is estimated from the victims' own footprints, not re-read from the
  driver.** A stopped process does not return its memory immediately, so a fresh reading
  straight after a kill reports it as still in use. A victim whose cost nobody declared or
  measured counts as freeing nothing, which can refuse an admission that would have fit —
  preferred over the opposite error.
- **Free memory is read per machine, not per card.** `admission.pool_free_gib` answers with
  a discrete device's own `memory.free` (the most free device, never the sum: one provider
  lands on one GPU), with `MemAvailable` on unified memory where the device has no memory
  of its own, and with nothing at all where there is no NVIDIA driver. The unified case is
  not hypothetical: a machine used to develop this answers `[N/A]` to `memory.free`, which
  this module first read as "do not reason about memory" — so on a host with 121 GiB worth
  reasoning about, no memory ceiling applied. Admitting against the `[N/A]` would have been
  worse than ignoring it; asking the pool the allocation actually comes out of is the third
  option, and `capacity_gib` was already making that distinction one layer down.
- **A model larger than the machine is refused up front.** Capacity does not move, so it is
  read once and a provider needing more than this machine's whole pool is refused before
  anything is evicted — and reported as permanent rather than as "at capacity, retry
  shortly", which would send a caller into a loop that cannot succeed.

Memory pressure never evicts a provider with a call in flight, exactly like the count
ceiling: the caller is told to retry instead of having a running GPU job killed under it.

#### Measuring the model and not the server

A difference is only a model's cost if the model was loaded between the two readings, and
**nothing in this catalog has its model in memory when its port starts answering**:

| provider | where its model lives | when it loads |
|---|---|---|
| resident manifest (32 slugs, e.g. `boltz`) | a worker process of its own | on the first request, which starts the worker |
| no resident manifest (28 slugs, e.g. `esm`) | the MCP server process | on the first request too — lazily, which is how it can serve `tools/list` before its weights exist |

So every measurement is taken after a call the provider answered, against the free reading
taken before its server started. Measuring across the start is what the pool used to do,
and it recorded the MCP server's own memory for all 60. `footprint_mib` taking the larger
of declared and measured covered the 28 providers that declare a budget; for a provider
that declares none, the small figure was the only one admission had — and being optimistic
about a model's cost ends in an out-of-memory, where being pessimistic ends in a refusal.

A call can be answered without a model ever loading — a rejected argument, a cached
answer. For the 32 providers that keep a worker, the process table says which happened
(`admission.machine_holdings`, keyed by the bare slug for this checkout's own workers;
`admission.declares_resident_worker` is what asks whether to look), and a call that left
no worker running measures nothing. For a provider holding its model in its own server
process there is no such evidence to be had, so a call that loaded nothing records
something small, and `FootprintStore.record` keeping the largest figure it has ever seen
is what corrects that on the first call that does load.

A measurement is taken once per residency — every later call would be measured against a
baseline from before the load — and it is a residency cost plus whatever that one call
still holds, which is not the request peak the manifests carry.

On a unified-memory host the local reading is frequently worthless, and that is a reason
the declared budget exists rather than a reason to distrust the design: measured live on
this project's GB10 with `boltz` prewarmed, `MemAvailable` *rose* by 1.3 GiB across the
load — something else on the machine released more than the model was taking, and with
one pool for host and device there is nothing in the reading to tell them apart. A
difference of zero or less is recorded as nothing, so admission went on using the
manifest's 5673 MiB. The measurement is worth taking where it is reliable, and worth
nothing where it is not — which is why it is never the only figure.

Reading the machine still degrades to "do not reason about memory" rather than to "no
memory": no `nvidia-smi`, a non-zero exit, a reading that is neither a number nor `[N/A]`,
or one device answering while another does not.

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

That is why the pool deliberately has no pre-wait of its own, and measuring the start
confirmed it rather than softening it: `boltz`'s MCP server takes **12.5 s** to bind its
port on this project's GB10 (most of it importing ToolUniverse in the child), so a wait
long enough to cover a real start spends half the relay's budget before the call begins.
The platform's backoff absorbs the same delay without putting the tunnel at risk.

`ProviderPool.start_wait_s` exists for the case where the cliff does not: a host serving
its own endpoint without `--share` answers to a client whose timeout is its operator's
own business, and there a few seconds of waiting turn a failed first call into an answered
one. **It is 0 by default**, so nothing behind a relay waits unless its owner says so.

Control dispatch is local-connection only. The Redis coordinator forwards request frames
between replicas and has no control representation, so a control call for an agent on
another replica reports no agent rather than silently doing nothing.

## Verified

Unit tests (`tests/unit/test_remote_pool.py`, 94 cases) drive routing, admission,
eviction, idle reaping, snapshot invalidation, the measurement rules and the HTTP surface
with injected lifecycle callables — no GPU, no provider environment, no network, and
since the readings are injected there, no dependence on what else is running on the
machine. Mutation-checked: replacing LRU selection with an arbitrary pick, dropping the
in-flight guard, or dropping the concurrent-start guard each fail their own test.

The warm path is covered on both sides: `test_remote_resident.py::TestWarmOnStart` for the
server half (nothing loads unasked, a request loads in a thread, a provider with no
manifest has nothing to warm, a failed load leaves a working server) and
`test_remote_pool.py` for the pool half (a prewarm asks for the model, a call does not).

Live on this project's GB10, driving the real `ProviderPool` against the real `boltz`
provider: a prewarm bound the port in 12.5 s with `model_loaded` false, and the weights
were in memory at 31.3 s with `machine_holdings` naming the worker; `memory_plan` sized it
at the manifest's 5673 MiB; `MemAvailable` moved the wrong way across the load, so the
local measurement was discarded rather than recorded as a ceiling.

`--max-active 0` is verified live against two real provider subprocesses on this
project's GB10, driving the real `ProviderPool`: with the count gone both stayed resident
(`borzoi_calico` then `enformer_deepmind`, up in 4.2 s and 4.9 s), and the same pair at
`--max-active 1` evicted the first to admit the second. A pool built with a capacity
reading of None refused to start and said to pass a count.

The same two providers are what "What a declared zero is worth" is about, and the change
is visible in the same live run: `memory_plan` reported `expected_mib` of 0 for both
before it and `null` after, this machine answering `pool_is_shared_with_the_host()` with
True, and `--max-active 0` then held one of them resident at a time instead of both. Their
servers cost 135 MiB of the pool to bind a port — the ~10 GiB their manifests measure is
what an answered call holds, which is why the figure is learned from one.

Per-provider interpreters are verified in the same place, by reading
`/proc/<pid>/cmdline` of the processes the pool actually started: with
`TOOLUNIVERSE_REMOTE_ENFORMER_DEEPMIND_PYTHON` set to a second environment, both
providers ran under the first one's interpreter before the change and each under its own
after it.

End-to-end against two real provider subprocesses over real HTTP, counting actual
process launches: nothing starts at boot; `tools/list` stays empty and starts nothing;
`--warm` starts each provider once and leaves nothing resident; a `tools/call` launches
only its owner; a repeat call reuses it; calling the other model evicts the first at
`--max-active 1`; idle reaping stops it; an unknown tool returns `-32601` rather than a
tunnel-killing 404.
