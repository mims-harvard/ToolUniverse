---
name: setup-esmc-remote-tool
description: Set up, launch, validate, and troubleshoot the ESM Cambrian ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up ESM Cambrian as a remote tool

> Validation status (2026-10-01): ESM Cambrian 6B ran on the NVIDIA GB10 (aarch64, cc 12.1) with the optimization kit **OFF** -- stock ESM C, a supported mode of the kit and not a workaround. `exact` is not reachable on this card: its `fused` lever needs flash-attn, which publishes no aarch64 wheel, and this kit refuses to load at all rather than degrade ("a mode is all of its levers"). Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS in one held worker: build 141.7 s, then forwards of 0.69 / 0.076 / 0.074 / 0.074 s at a flat 24.07 GiB peak reserved. That ratio is the point of this deployment -- a per-request process spends 141.7 s reading 23.7 GiB of weights to do 0.076 s of work. Peak is nearly flat in length (28.75 GiB at 1600 residues, 1.19x the 100-residue figure), because the constant 6B parameter term dominates. Public publication, cross-user isolation, concurrency, recovery and embedding quality are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation esmc
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
python3 -m venv .venvs/esmc
. .venvs/esmc/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_ESMC_PYTHON` names,
and nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/esmc-venv`, or `uv venv` unless this provider's
lock header says otherwise -- and `tu remote setup --only environment` fills
it from `src/tooluniverse/remote/esmc/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/esmc/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export HF_HOME=...
export TOOLUNIVERSE_ESMC_PYTHON=~/esmc-venv/bin/python
tu remote setup esmc
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces, and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/esmc.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- HF_HOME points at the Hugging Face cache holding the pinned `biohub/ESMC-6B` snapshot (23.7 GiB). **It is the same pin esmfold2 already downloaded**, so if that provider is set up on this machine this one fetches nothing -- point both at the same root. The 300m and 600m variants are NOT on disk; switching to one needs a fetch and a completely different VRAM budget.
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
tu remote share esmc
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
tu remote share esmc --name my-esmc-remote --workers 1
~~~

Use `tu remote check esmc` for a non-sharing readiness check and
`tu remote run esmc` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.esmc.esmc_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8037/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8037/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains run_esmc_embed; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8037/mcp --json
tu serve --share --forward http://127.0.0.1:8037/mcp --name validation-esmc --workers 1
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

Operation: run_esmc_embed

~~~json
{"sequence": "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"sequence": "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"}''')
    async with Client("http://127.0.0.1:8037/mcp") as client:
        result = await client.call_tool("run_esmc_embed", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: the MEAN-POOLED embedding vector (2560 floats at d=2560), its norm, the sequence length and the dimension. The full per-residue matrix is never returned inline -- a residue window is opt-in and REFUSED rather than clipped above 20,000 floats, and the whole matrix comes back as a path to a float32 `.npy`. `run_esmc_logits` returns the mean log-likelihood, the pseudo-perplexity and the `top_n` least-likely residues. Bounds are enforced in both halves: in the tool so a bad call never occupies the GPU, and in the worker so a request that did not come through the tool cannot build a reply nothing can transport. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. For a model whose peak depends on input size, the manifest states the envelope the figure was measured at; a larger request exceeds it.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape, because a CUDA graph captured on the first replay attempt left a failed capture behind. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/esmc-resident.log`, and it holds the kit's full lever census. A lever reading `state=off reason=...` is the kit declining something, which is usually correct.
- Import/executable failure in the model half: re-run `tu remote setup esmc --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-esmc`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/esmc and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
