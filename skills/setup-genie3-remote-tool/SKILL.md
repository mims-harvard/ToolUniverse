---
name: setup-genie3-remote-tool
description: Set up, launch, validate, and troubleshoot the Genie 3 ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up Genie 3 as a remote tool

> Validation status (2026-10-01): Genie 3 ran on the NVIDIA GB10 (aarch64, cc 12.1) under the optimization kit's `exact` mode, all nine levers. **It is the only provider here where residency has been shown not to change the output**: four consecutive identical requests in one held worker produced BYTE-IDENTICAL PDB files (sha256 over every file, 9.8 s then 0.8 s each), because the worker snapshots and restores four RNG generator states to emulate the kit's own "one process per request" contract. 12x warm with that contract intact. Ladder 0.31 / 0.61 / 1.28 / 2.82 GiB at 100 / 200 / 400 / 670 tokens, 4.84 at 670x2 — **the cheapest generative provider here by an order of magnitude** against RFdiffusion3's 12.49 and ESMFold2's 25.28. Two operational cautions. (1) Upstream can build exactly ONE sampling config per process: its `default_config` is a module-level mutable holding `FieldReference` objects, so the second distinct request raises unless the worker resets it — which this one does. Four identical requests cannot catch that, because a held engine is built once. (2) On unified memory the kit's capacity guard reads `total - free` from `cudaMemGetInfo`, which is SYSTEM-WIDE, so a co-tenant preallocating the card makes this provider refuse batches a hundredth of its size. Expect refusals rather than slowdowns when co-scheduling. Public publication, cross-user isolation, concurrency, recovery and design quality are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation genie3
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
python3 -m venv .venvs/genie3
. .venvs/genie3/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_GENIE3_PYTHON` names,
and nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/genie3-venv`, or `uv venv` unless this provider's
lock header says otherwise -- and `tu remote setup --only environment` fills
it from `src/tooluniverse/remote/genie3/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/genie3/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export GENIE3_WEIGHTS=...
export TOOLUNIVERSE_GENIE3_PYTHON=~/genie3-venv/bin/python
tu remote setup genie3
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces, and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/genie3.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- GENIE3_WEIGHTS points at `<root>/pretrained/v1` (2 files, 0.3 GiB) — the smallest weight set of any provider here. `[kit.env] GENIE3_OPT_AUTOLOAD = "0"` is load-bearing: this kit's `.pth` hook does not patch upstream, it KILLS any in-process importer of `genie3` with exit 3, and the mode is a driver script whose position the resident worker takes.
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
tu remote share genie3
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
tu remote share genie3 --name my-genie3-remote --workers 1
~~~

Use `tu remote check genie3` for a non-sharing readiness check and
`tu remote run genie3` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.genie3.genie3_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8048/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8048/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains genie3_design; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8048/mcp --json
tu serve --share --forward http://127.0.0.1:8048/mcp --name validation-genie3 --workers 1
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

Operation: genie3_design

~~~json
{"length":"60","n_designs":1,"seed":0}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"length":"60","n_designs":1,"seed":0}''')
    async with Client("http://127.0.0.1:8048/mcp") as client:
        result = await client.call_tool("genie3_design", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: `n_designs` above zero with per-design records, plus `engine_rebuilt` and `rng_restored`. The output glob is `*_[0-9]*.pdb`: the only file written regardless of success is the kit's own composed `request.yaml`, which it cannot match, and the worker additionally filters by this request's start time so a previous pass's file is not counted. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. For a model whose peak depends on input size, the manifest states the envelope the figure was measured at; a larger request exceeds it.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape, because a CUDA graph captured on the first replay attempt left a failed capture behind. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/genie3-resident.log`, and it holds the kit's full lever census. A lever reading `state=off reason=...` is the kit declining something, which is usually correct.
- Import/executable failure in the model half: re-run `tu remote setup genie3 --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-genie3`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/genie3 and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
