---
name: setup-mosaic-remote-tool
description: Set up, launch, validate, and troubleshoot the mosaic (Boltz-2 binder hallucination) ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up mosaic (Boltz-2 binder design) as a remote tool

> Validation status (2026-10-02): mosaic (escalante-bio/mosaic through the joltz JAX port of Boltz-2) designed binders on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode. **mosaic DESIGNS a binder; it does not fold a sequence you give it.** One request is one design: a target sequence and a binder length in, a binder sequence plus the predicted complex and its ipTM / pLDDT / PAE out. Every one of the 125 optimiser steps is a full Boltz-2 forward and backward pass. Acceptance in one held worker: ladder 169 / 256 / 384 tokens (pool peak 8.0 / 16.0 / 32.0 GiB, in-use 4.85 / 8.13 / 15.67), mixed shapes 4/4, four identical requests 4/4 (23.6 / 23.4 / 23.3 / 23.2 s), every request writing a complex PDB. **Declared budget 32.0 GiB at the 384-token ceiling.** 512 tokens was measured and is not offered: about 120 s per step, so one design is hours. **Residency gain depends heavily on request size**: 11.5x for a 5-step request at 169 tokens (269.5 s cold, 23.5 s held) but only ~1.5x at 169 tokens and ~1.08x at 384 for the full 125-step recipe, because the compile it saves (a few minutes per shape) is small against the work. A new SHAPE (target residues x copies + binder length) pays a compilation; a seed or step change does not; an epitope or a second target copy costs a smaller recompile. Designs are not bit-reproducible across requests (boltz re-draws reference coordinates). The kit's `fast` mode engages here but was not adopted: see provider.toml. Wall times were taken on a shared card; peaks reproduce, times do not. Public publication, cross-user isolation, concurrency, recovery and scientific quality (a high ipTM is the model's opinion of a design optimised against it) are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. The model is JAX; its torch is CPU-only on purpose (it only reads the checkpoint).
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.
- The host's memory is one pool shared with the GPU: before starting the worker run `python scripts/remote_validation/wait_for_memory.py --need 42`.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation mosaic
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

The MCP server runs in ToolUniverse's environment and the model runs in its
own, built from a pinned lock; they cannot import each other.

~~~bash
python3 -m venv .venvs/mosaic
. .venvs/mosaic/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_MOSAIC_PYTHON` names and nothing
above creates it. Create an empty interpreter there first, with the stdlib
`python -m venv ~/mosaic-venv` (a CPython 3.12), and
`tu remote setup mosaic --only environment` fills it from
`src/tooluniverse/remote/mosaic/environment/requirements.lock` with `--no-deps`.
The lock is the kit's own with two lines changed: torch and torchvision, to the
aarch64 files of the same release from the same index.

~~~bash
export TOOLUNIVERSE_MOSAIC_PYTHON=~/mosaic-venv/bin/python
export MOSAIC_CACHE_DIR=~/.cache/mosaic
tu remote setup mosaic
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step asserts that the provider produced
what its manifest says a success produces (`*_complex.pdb`, plus a non-empty
`binder_sequence`) and records the measured peak to
`~/.cache/tooluniverse/measured/mosaic.json`. Expect a few minutes: most of it is
the first compilation.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- Weights are the public Boltz-2 checkpoint (`boltz2_conf.ckpt`, 2.29 GB) and the CCD molecules (`mols.tar`, 1.86 GB) under `MOSAIC_CACHE_DIR/boltz/`, fetched by the kit's own `python -m mosaic_opt.weights` from the hosts boltz names (no credential, no licence gate) and checked against the manifest's size and sha256. Boltz's downloader also fetches `boltz2_aff.ckpt`, which mosaic never loads.
- No alignment is built and no external service is contacted: the target is single-sequence (verified with a socket guard: zero network or DNS attempts while featurising).

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
tu remote share mosaic
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. Override the name and worker count only when needed:

~~~bash
tu remote share mosaic --name my-mosaic-remote --workers 1
~~~

Use `tu remote check mosaic` for a non-sharing readiness check and
`tu remote run mosaic` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.mosaic.mosaic_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8055/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8055/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains mosaic_design_binder; stop on empty, duplicate, or schema-drifted discovery.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8055/mcp --json
tu serve --share --forward http://127.0.0.1:8055/mcp --name validation-mosaic --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. The evidence above is local, on one card,
through the loopback endpoint. Public publication, independent-caller
authorization/isolation, saturation, and persistent supervision are untested.

## Run a verified example

Operation: mosaic_design_binder

~~~json
{"target_sequence":"KKAVINGEQIRSISDLHQTLKKELALPEYYGENLDALWDALTGWVEYPLVLEWRQFEQSKQLTENGAESVLQVFREAKAEGADITIILS","binder_length":80,"steps1":10,"steps2":5,"seed":0}
~~~

The example is barstar (1BRS chain D, 89 residues) with an 80-residue binder, 169 tokens, and the optimiser cut to 10 + 5 steps so it finishes in minutes; omit `steps1`/`steps2` for the full 75 + 50. Invoke it through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"target_sequence":"KKAVINGEQIRSISDLHQTLKKELALPEYYGENLDALWDALTGWVEYPLVLEWRQFEQSKQLTENGAESVLQVFREAKAEGADITIILS","binder_length":80,"steps1":10,"steps2":5,"seed":0}''')
    async with Client("http://127.0.0.1:8055/mcp") as client:
        result = await client.call_tool("mosaic_design_binder", arguments)
        print(result.content[0].text)

asyncio.run(main())
PY
~~~

Executed here, first call 505 s (it pays the compilation for this shape), second call 74 s. The reply carries `binder_sequence` (80 letters), `scores` (`iptm`, `plddt_binder_mean` and `plddt_target_mean` on a 0-1 scale, `pae_binder_to_target_mean` in angstroms), `loss` (first, final, best and the whole trajectory), `n_tokens` = 169, `shape_compiled_before`, `timing`, `peak_reserved_gib` = 8.0, `peak_in_use_gib` = 4.78, `weights_held_by` = "worker", `kit_mode` = "off". The PDB text is opt-in (`return_structure`); the complex is the binder as chain A followed by the target copies. A refused input comes back as `{"error": ...}`, for example a sequence containing `*`, and the worker stays up. Limits: 384 tokens in total (target residues x `target_copies` + `binder_length`), binder 8-200, target at most 376 residues.

## Tune GPU and concurrency

- Use one worker. It serves one request at a time; a second in-flight request queues on its lock.
- `vram_budget_gb` is 32.0 and is a JAX pool figure: coarse, doubling with size (8 / 16 / 32 GiB at 169 / 256 / 384 tokens) while the working set moves 4.85 / 8.13 / 15.67. Schedule on it as a ceiling; do not read the gaps as headroom. A deployment capped at 256 tokens fits in 16. `peak_bytes_reserved` reads 0 on this stack and is a trap.
- `XLA_PYTHON_CLIENT_PREALLOCATE=false` is set by the launch and load-bearing for scheduling: JAX otherwise claims ~75% of the pool up front.
- Time scales steeply with tokens: about 4.3 / 12.6 / 25 / 120 s per optimiser step at 169 / 256 / 384 / 512 tokens, so a full design is roughly 9 min / 26 min / 52 min at the first three rows on a lightly shared card.
- Measure cold start, then at least four consecutive identical requests, then a shape change; `python scripts/remote_validation/verify_provider.py mosaic --lengths 169,256,384 --repeats 4` does both (its `--lengths` are total tokens).
- Increase workers only after single-flight initialization and recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker transcript is `~/.cache/tooluniverse/remote-logs/mosaic-resident.log`; each request ends with a `request N done tokens=... peak_pool_gib=... peak_in_use_gib=...` line, and `grep -c "ready device"` tells you whether the worker restarted between requests.
- The launch STRIPS `XLA_FLAGS`, `JAX_COMPILATION_CACHE_DIR`, `JAX_PERSISTENT_CACHE_*`, `JAX_ENABLE_X64`, `JAX_DEFAULT_MATMUL_PRECISION` and every `MOSAIC_OPT*` name from the child, because the kit forbids them; check `/proc/<worker pid>/environ`, not the launcher's return value.
- The first request into a new shape is slow (minutes) and is compiling, not stalled.
- Weights off their pin: the named file is left in place; remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-mosaic`.
- Check `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/mosaic and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
