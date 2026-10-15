---
name: setup-atlasfold-remote-tool
description: Set up, launch, validate, and troubleshoot the AtlasFold ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up AtlasFold as a remote tool

> Validation status (2026-10-01): AtlasFold v1.0.0 ran on the NVIDIA GB10 (aarch64, cc 12.1) under the optimization kit's `big` mode with **thirteen levers ablated and upstream's triangle backend forced to `torch`**. Both were necessary. This stack's triton 3.3.1 cannot compile a warp-shuffle kernel for this card -- it aborts the process with `LLVM ERROR: Cannot select`, which no worker can catch -- and a newer `ptxas` does not help, because the failure is upstream of ptxas. Verified on twelve requests in held workers including 600- and 800-residue folds. Peak reserved 12.06 GiB at 100 residues, 19.64 at 600, 38.63 at 800. **Read three warnings before deploying this one.** (1) A 35-residue smoke exercises NONE of the kit's kernel levers -- they are all gated at 512 tokens -- so a green smoke here would have been the most misleading result this provider could produce; the acceptance test must reach the largest input you will accept. (2) Stock AtlasFold under its own default `--kernel auto` cannot fold past about 128 tokens on this card at all, kit or no kit, because cuEquivariance ships its own Triton kernels; `--kernel torch` is the only backend that answers here. (3) The VRAM reserve RATCHETS: after one 800-residue fold the worker reports 38.63 GiB for every later request including a 3-second one, because the caching allocator keeps the segments it grew. A deployment capped at 400 residues holds this provider in 14 GiB rather than 39. Public publication, cross-user isolation, concurrency, recovery and structural accuracy are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation atlasfold
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
python3 -m venv .venvs/atlasfold
. .venvs/atlasfold/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_ATLASFOLD_PYTHON` names,
and nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/atlasfold-venv`, or `uv venv` unless this provider's
lock header says otherwise -- and `tu remote setup --only environment` fills
it from `src/tooluniverse/remote/atlasfold/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/atlasfold/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export TOOLUNIVERSE_ATLASFOLD_PYTHON=~/atlasfold-venv/bin/python
tu remote setup atlasfold
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces, and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/atlasfold.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- The resident worker forces the data loader to 0 workers. Upstream defaults to 10 and the kit's cap floors that at 1, but a resident worker has CUDA initialised in the parent long before a request arrives and the forked child dies without a traceback.
- Nothing is fetched at request time. The manifest declares every weight file with its size and sha256, and the launch refuses if one is off its pin.

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
tu remote share atlasfold
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
tu remote share atlasfold --name my-atlasfold-remote --workers 1
~~~

Use `tu remote check atlasfold` for a non-sharing readiness check and
`tu remote run atlasfold` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.atlasfold.atlasfold_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8043/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8043/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains atlasfold_predict; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8043/mcp --json
tu serve --share --forward http://127.0.0.1:8043/mcp --name validation-atlasfold --workers 1
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

Operation: atlasfold_predict

~~~json
{"chains":["LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"]}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"chains":["LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"]}''')
    async with Client("http://127.0.0.1:8043/mcp") as client:
        result = await client.call_tool("atlasfold_predict", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: `n_structures` above zero with the five diffusion samples plus upstream's ranked copy, and per-structure confidence. The reply also carries `triton_usable` and the selected `kernel` backend: on this card they read `false` and `torch`, and a `kernel=cuequiv` on a host whose Triton cannot compile would be a fold about to abort rather than a faster one. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. For a model whose peak depends on input size, the manifest states the envelope the figure was measured at; a larger request exceeds it.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: atlasfold passed exactly that and still died on the second request of the same shape, because a CUDA graph captured on the first replay attempt left a failed capture behind. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/atlasfold-resident.log`, and it holds the kit's full lever census. A lever reading `state=off reason=...` is the kit declining something, which is usually correct.
- Tracebacks are NOT in the request's output directory. Upstream binds `log_dir` to the lightning module at construction, so a resident worker's failures all land in its BIRTH directory, `/tmp/atlasfold-resident-*/logs/predict_err_rank0.log`. This has cost two debugging rounds.
- Import/executable failure in the model half: re-run `tu remote setup atlasfold --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-atlasfold`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/atlasfold and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
