---
name: setup-af3_jax-remote-tool
description: Set up, launch, validate, and troubleshoot the AlphaFold 3 (JAX fork) ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up AlphaFold 3 (JAX fork) as a remote tool

> Validation status (2026-10-01): AF3-JAX (the sokrypton/alphafold3 open fork on public OpenFold3-preview2 weights) folded on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode. **It is the first JAX provider on this standard, and the largest residency gain measured here: 24-26x** — four consecutive identical requests ran 170.5 / 8.3 / 7.0 / 7.0 s on an idle card and 179.1 / 6.8 / 6.8 / 6.8 s on a contended one, against RFdiffusion3's 12x. (A contended card gives the *higher* ratio, because it slows the first request far more than the replays; read any residency multiple with that in mind.) **That figure is the smallest input's, which is where it is largest: at the row the budget is declared on — 800 residues — the same worker gives 3.5x**, 755.0 s cold against ~218 s held. Plan with the second number; the first is the best case. Three things residency keeps, and the third is this provider's own: the 1.37 GB zstd weight read, the XLA executables (one per padding bucket), and **tokamax's per-shape autotune, which nothing persists** — upstream's `ModelRunner._load_autotune_cache` reads a file that its `except Exception: pass`-wrapped writer never produces here, so a worker restart pays the first-request price again per bucket. That is why `idle_timeout_s` is 900 and not something shorter. Ladder 2.0 / 4.0 / 4.0 / 8.0 GiB at 100 / 200 / 400 / 800 residues; declared budget 8.0 at the 832-token bucket. Eleven acceptance requests, every one asserted to have produced a structure. Two cautions below are specific to this provider: it does not run at all without one upstream flag (**the shared-memory wall**), and **its VRAM figure is quantised** in a way a torch provider's is not. Public publication, cross-user isolation, concurrency, recovery and scientific quality are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation af3_jax
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point
-- the model's stack is not installable beside ToolUniverse's.

~~~bash
python3 -m venv .venvs/af3_jax
. .venvs/af3_jax/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_AF3_JAX_PYTHON` names,
and nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/af3_jax-venv` -- and `tu remote setup --only environment`
fills it from
`src/tooluniverse/remote/af3_jax/environment/requirements.lock` with
`--no-deps`, so no version is silently resolved to something else.

Two things about this lock are worth knowing before it runs. All 81 lines
resolve to aarch64 wheels at the kit's exact versions — jax / jaxlib /
jax-cuda12-plugin / jax-cuda12-pjrt 0.10.2, every nvidia-*-cu12 at CUDA
12.9.x, cuDNN 9.17.1.4 — with one substitution, torch's aarch64 file for the
same release the kit pinned by x86-64 URL. And **the torch in this environment
is CPU-only on purpose**: it is there for the weights converter and because
`check_pins.py` lists it, not to drive the card. JAX drives the card. The
shared arch probe reports `jax.default_backend()` for exactly this reason, so
torch's silence is not read as "no GPU".

The stock `alphafold3-open` 3.1.4 distribution ships no wheel anywhere, so
every route compiles it; it builds clean on aarch64 in about three minutes
with no portability patch, and `build_data` then writes the CCD. The CCD
snapshot is whatever wwPDB serves on the build day, so your code count will
differ from the kit's x86-64 wheel by a few hundred. That is expected and
stock/PINS.json says so.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/af3_jax/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export TOOLUNIVERSE_AF3_JAX_PYTHON=~/af3_jax-venv/bin/python
export AF3_JAX_REPO=~/af3_jax-repo
export AF3_JAX_PARAMS_ROOT=~/.af3_jax
tu remote setup af3_jax
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces (`*_model.cif`, plus a non-empty `structures`
key), and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/af3_jax.json`. A host schedules on that file.
Expect roughly 190 s for the smoke: most of it is the autotune below, not the
fold.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## The shared-memory wall, and the flag that clears it

Without one flag this provider does not run on this card at all. It fails to
**compile**, not to launch:

~~~
JaxRuntimeError: RESOURCE_EXHAUSTED: Shared memory size limit exceeded:
  requested 110592, available: 101376, context: []
~~~

108 KiB wanted against 99 KiB available, about 9% over. The kernel is one of
tokamax's Pallas `PallasTritonGatedLinearUnit` calls in the diffusion head,
over f32 operands at four pipeline stages; tokamax ships no tuned config for
this part, so it synthesises one from heuristics written for cards with
164–227 KiB of shared memory. The fix is upstream's own flag, registered as an
absl flag at import and listed by `run_alphafold.py --helpfull`:

~~~
--tokamax_autotuning_cache_miss_fallback=autotune
~~~

Its default is `heuristics`; `autotune` makes tokamax measure its own default
config set on the card present and keep the fastest config that compiles and
runs. The worker passes it on the absl parse it already does, and the same
single flag fixes the kit's CLI route, which passes stock flags through
verbatim. This is a documented option whose entire purpose is an unseen
device — not a tile override, not a patch.

Three things it is worth knowing you do **not** need to try, because all three
were measured and all three leave the number byte-identical at 110592:
`--flash_attention_implementation=cudnn` (or `triton`), setting
`use_glu_kernel = False` on all fifteen config sites, and the kit's pinned
`--xla_gpu_enable_triton_gemm=false`. The GLU that overflows is the one with
no switch: `diffusion_transformer.transition_block` takes `use_glu_kernel` as
a **function default** and none of its three call sites passes it. An
invariant error number across three independent switch-flips is itself the
diagnostic — it says the culprit is insensitive to every knob you tried.

## Obtain credentials, data, and model weights

- `AF3_JAX_PARAMS_ROOT` holds the OpenFold3-preview2 record file (1.37 GB, zstd). The manifest declares it with its size and sha256, and the launch refuses if it is off its pin.
- `AF3_JAX_REPO` is the kit's checkout. The stock patch there is **not optional and not upstream's**: nine lines in `template_modules.py`, gated on `global_config.of3_weights`, featurise absent template slots as GAP rather than restype 0. Upstream AF3-JAX never runs OF3 weights and so never needs it; this provider runs nothing but OF3 weights. `check_pins.py` checks the pinned files' presence, not their content, so an environment assembled another way would not be caught downstream — build from `stock/unpack_src.sh`, which applies it.
- No alignment is built and no external service is contacted at request time. A protein chain with `unpairedMsa: null` means "the data pipeline will fill this", which this provider does not run; pass `""` for MSA-free.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and
installing the pinned relay SDK described under Connect below, run from the
repository root. Log in only once per machine (and again after key
rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share af3_jax
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. It automatically uses the reviewed Python, name,
and worker count. Override them only when needed:

~~~bash
tu remote share af3_jax --name my-af3_jax-remote --workers 1
~~~

Use `tu remote check af3_jax` for a non-sharing readiness check and
`tu remote run af3_jax` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.af3_jax.af3_jax_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8045/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8045/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains af3_jax_predict; stop on empty, duplicate, or schema-drifted discovery.

The first request into a padding bucket pays the XLA compile **and** the
tokamax autotune; the ones after it pay neither. Measured: an ascending ladder of 100 / 200 / 400
residues paid 234.8 / 269.9 / 468.7 s, one compile-plus-autotune each, and a
mixed sequence of 100, 100, 200, 100 afterwards paid 14.4 / 13.2 / 31.1 / 13.3
because every one of those buckets was already held. A benchmark that measures
only the first call measures the wrong thing, and one that measures only
identical calls misses that the price is per bucket, not per request.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8045/mcp --json
tu serve --share --forward http://127.0.0.1:8045/mcp --name validation-af3_jax --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested.

## Run a verified example

Operation: af3_jax_predict

~~~json
{"sequences":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}],"seed":1}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"sequences":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}],"seed":1}''')
    async with Client("http://127.0.0.1:8045/mcp") as client:
        result = await client.call_tool("af3_jax_predict", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: a non-empty `structures` list ranked best-first with a
per-sample ranking score, and `weights_held_by = "worker"`. The mmCIF text
itself is opt-in (`return_structures`), because it is megabytes per sample;
the confidence scores come back either way. `num_diffusion_samples` and
`num_recycles` each change the engine key, so changing one recompiles the held
model — which is correct behaviour, not a fault, and it is what the
mixed-shape test below exists to exercise. Check scientific meaning, output
bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. For a model whose peak depends on input size, the manifest states the envelope the figure was measured at; a larger request exceeds it.
- **A JAX provider's VRAM number is not the same kind of number as a torch provider's.** `peak_pool_bytes` — the analogue of torch's `max_memory_reserved` — is coarse: it read 2.0 / 4.0 / 4.0 / 8.0 GiB while the actual working set moved 2.00 / 2.32 / 3.38 / 6.37. (This ladder happens to land on powers of two and an earlier draft called that the rule; af2ig reads 0.5 / 1.0 / 2.0 / 6.0 on the same stack, so read it as coarse rounding of unpredictable tightness, not binary rounding.) So this provider's 8.0 is a rounded-up allocator high-water mark being compared against a torch provider's near-exact one. Schedule on it as a ceiling, and do not read the gaps between rungs as headroom. (Note also that `peak_bytes_reserved` reads 0 on this stack and is a trap.)
- `XLA_PYTHON_CLIENT_PREALLOCATE=false` is set by the launch and is load-bearing for scheduling, not for correctness: without it the reported peak is 91.22 GiB instead of 2.0 — a 45x difference that is JAX claiming the card up front, not the model needing it. A co-tenant arrangement that loses this variable loses the whole card.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape, because a CUDA graph captured on the first replay attempt left a failed capture behind. A repeat and a shape change are different tests and a resident provider has to survive both. For this provider the repeats are the cheap half — a bucket is compiled once — so the shape change is where the real evidence is.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/af3_jax-resident.log`. "Autotuning cache miss for PallasTritonGatedLinearUnit ... on NVIDIA GB10" is normal and expected here — it is the per-shape autotune doing its job, and it is why the first request into a bucket is slow.
- `Shared memory size limit exceeded` means the tokamax flag above is not reaching the model. It is a compile failure, so it arrives before any fold, and the Python traceback cannot name the kernel; do not go looking for an attention or GEMM switch.
- This kit's `.pth` hook **only refuses**. It arms a meta-path finder on `alphafold3` when `AF3_JAX_OPT` names a mode other than `off`, or when any `AF3_JAX_*` name outside its declared tuple is set — the second trigger fires with the mode unset — and the first `import alphafold3` then exits 3. The launch therefore *strips* undeclared `AF3_JAX_*` names rather than merely not setting them. If the worker dies on import with exit 3, look for a stray `AF3_JAX_*` variable in the environment.
- Import/executable failure in the model half: re-run `tu remote setup af3_jax --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-af3_jax`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/af3_jax and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
