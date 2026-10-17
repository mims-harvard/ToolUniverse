---
name: setup-opendde-remote-tool
description: Set up, launch, validate, and troubleshoot the OpenDDE ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up OpenDDE as a remote tool

> Validation status (2026-10-02): OpenDDE 1.1.1 ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) with the optimization kit OFF, torch 2.7.1+cu128 and the triangle kernels resolved by upstream to torch. This provider is UNTESTED, not verified. Established by running it: all five `tu remote setup` steps (smoke: one 35-residue fold, five samples, pLDDT about 93.5, peak reserved 3.12 GiB), and a 100/200/400-residue ladder in two separate held workers with identical peaks of 3.69 / 6.85 / 22.55 GiB. NOT established: four consecutive identical requests, the mixed sequence, residency gains, the ceiling refusals, the hostile-environment launcher test, and the example below through the live MCP endpoint, because the host's memory guard refused to start a worker (about 5 GiB free, co-tenants holding the rest). Wall times seen were on a heavily contended card and are not measurements. Public publication, cross-user isolation, concurrency, recovery and structural accuracy are untested; keep this deployment private.

## What OpenDDE is, and what one request means

OpenDDE (Aureka AI Research, Apache 2.0, PyPI `opendde` 1.1.1, model `opendde_v1`, 655.8 M parameters, one general-purpose checkpoint `opendde.pt`) is an AlphaFold3-class all-atom co-folding model. It folds a complex of protein, DNA and RNA chains, ligands and ions into diffusion-sampled mmCIF structures and scores every sample (pLDDT, pTM, ipTM, PAE, a ranking score). Its code descends from Protenix's, and so does its input dialect: an AlphaFold-Server style job whose entities are `proteinChain`, `dnaSequence`, `rnaSequence`, `ligand` and `ion`, each with a `count`.

**One request is one complex folded for one seed**: up to 5 diffusion samples (`num_diffusion_samples`), each separately scored, through `num_recycles` Pairformer cycles (default 10) and `num_diffusion_steps` steps per sample (default 200). Rank the samples on `ranking_score`.

Three deployment decisions are not oversights:

- **No MSA search, no templates.** `opendde pred` posts the query to an MSA web service before folding, and OpenDDE accepts alignments only as file paths on the host. Neither is acceptable on a remote caller's say-so, so every request is folded **single-sequence** and the reply says so (`use_msa: false`). Single-sequence OpenDDE is materially less accurate than MSA-fed OpenDDE.
- **Ligands are SMILES or `CCD_<id>`.** Upstream's `FILE_<path>` form reads a file off the host and is refused.
- **The optimization kit is OFF** (`[kit] mode = "off"`). Its one prebuilt object is x86-64, `kit_foreign_objects` refuses every other mode on this architecture, and the worker has to hold upstream's own `InferenceRunner` itself.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target.
- Its stack is torch 2.7.1+cu128, so it needs an NVIDIA driver that runs CUDA 12.8 (570 or newer).
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation opendde
~~~

After exporting provider resources, add `--check-provider-env`. After the server starts, add `--live` to verify the exact MCP tool set without running the model. Before sharing, add `--check-connect-prereqs`; this reports only whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not one: the MCP server runs in ToolUniverse's, and the model runs in its own, built from a pinned lock. They cannot import each other, and that is the point -- the model's stack is not installable beside ToolUniverse's.

~~~bash
python3 -m venv .venvs/opendde
. .venvs/opendde/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_OPENDDE_PYTHON` names, and nothing above creates it. Create an empty interpreter there first with the STDLIB `venv` module, on CPython 3.11 (the kit's own interpreter): `uv venv` writes a `_virtualenv.pth` that breaks kit-hook detection, and this kit activates through a `.pth`. For example:

~~~bash
~/.local/share/uv/python/cpython-3.11.5-linux-aarch64-gnu/bin/python3.11 -m venv ~/opendde-venv
export TOOLUNIVERSE_OPENDDE_PYTHON=~/opendde-venv/bin/python
~~~

`tu remote setup --only environment` then fills it from `src/tooluniverse/remote/opendde/environment/requirements.lock` with `--no-deps`, so no version is silently resolved to something else. The lock is the kit's own with two deviations, argued in its header: torch 2.7.1+cu126 becomes 2.7.1+cu128 (the kit pins an x86-64 file, and only the cu128 build carries a cubin this card can run), and the sixteen `nvidia-*-cu12` lines are absent (the aarch64 torch wheel bundles its CUDA runtime).

The rest is built by `tu remote setup`, which reads `src/tooluniverse/remote/opendde/provider.toml` and runs five steps: preflight, environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export TOOLUNIVERSE_OPENDDE_PYTHON=~/opendde-venv/bin/python
tu remote setup opendde
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke` while bringing a machine up. The smoke step is the one that matters: it holds the model, sends one request, asserts the provider produced what its manifest says a successful run produces (at least one `*_sample_<n>.cif`, and a non-empty `structures` field in the reply), and records the measured peak VRAM to `~/.cache/tooluniverse/measured/opendde.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- Nothing is fetched at request time. The manifest declares every weight file with its size and sha256 (the 2.6 GB checkpoint and the four `common/` files), and the launch refuses if one is off its pin. They come from upstream's own Hugging Face repository (`aurekaresearch/OpenDDE`) through upstream's own downloader, which the kit's install step runs.
- The resident worker forces the data loader to 0 workers: a resident worker has CUDA initialised in the parent long before a request arrives, and a forked child dies without a traceback.
- `OPENDDE_ROOT_DIR` names the weights root (default `~/.opendde`).
- **Do not export any `OPENDDE_OPT_*` variable.** The kit's start-up hook exits EVERY interpreter of this environment with status 3 when it sees an `OPENDDE_OPT*` name it does not declare, even with the kit off. The provider's launcher strips such names from the worker's environment, but `pip` and your own shell commands in this interpreter are not protected.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and installing the pinned relay SDK described under Connect below, run from the repository root. Log in only once per machine (and again after key rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share opendde
~~~

By default, `tu remote login` requests a short-lived device code, opens the TU Platform approval page, and polls until the signed-in user approves. No key copy/paste is required. On a headless machine, add `--no-browser` and open the printed link elsewhere. The CLI exchanges the approval for a computer-only key, verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and never displays it.

The share command runs environment and TU Platform preflights, starts or reuses the exact loopback endpoint, validates discovery, and keeps the relay in the foreground until Ctrl-C. It automatically uses the reviewed Python, name, and worker count. Override them only when needed:

~~~bash
tu remote share opendde --name my-opendde-remote --workers 1
~~~

Use `tu remote check opendde` for a non-sharing readiness check and `tu remote run opendde` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow when the key is missing, expired, or revoked. A malformed or revoked explicit `TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset or correct it, then run `tu remote login`. Non-interactive jobs also fail fast. Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.opendde.opendde_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8058/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8058/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains opendde_fold; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do not. That is the whole reason this provider is resident, and a benchmark that measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8058/mcp --json
tu serve --share --forward http://127.0.0.1:8058/mcp --name validation-opendde --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply `TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use `tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform matrix and was not part of it. That matrix imported each implementation it covered as unpublished owner drafts and invoked them through `/expert-sessions/{id}/test`; this provider was imported as no such draft and invoked through no such route. It has not been exercised through the Platform at all: the evidence above is local, on one card, through the loopback endpoint. Public publication, independent-caller authorization/isolation, saturation, and persistent supervision are untested.

## Run a verified example

Operation: opendde_fold

~~~json
{"chains":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}]}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"chains":[{"molecule_type":"protein","sequence":"LSDEDFKAVFGMTRSAFANLPLWKQQNLKKEKGLF"}]}''')
    async with Client("http://127.0.0.1:8058/mcp") as client:
        result = await client.call_tool("opendde_fold", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: `n_structures` of 5, a `scores` object carrying each sample's confidence summary (`plddt`, `ptm`, `iptm`, `ranking_score`), `use_msa: false` and `peak_reserved_gib`. This example has NOT yet been run through the live endpoint; run it and record the reply before marking the provider verified. A fold that fails on its input comes back as "OpenDDE could not fold this complex: ..." carrying upstream's own words, which is different from the worker being unavailable.

## Request limits

- At most 400 polymer tokens per complex (the tool refuses more; the worker re-checks the featurised count, which includes a ligand's atoms), at most 20 chains, `count` 1 to 16.
- `num_diffusion_samples` 1 to 5, `num_diffusion_steps` 1 to 400, `num_recycles` 1 to 20. The sample count moves time, not memory (measured: identical peak at 1 and 5 samples at 200 and 400 tokens); tokens drive the peak.
- Precision is bf16 only; fp32 measured 1.6x the memory and about twice the time at 200 tokens and is not offered.
- 400 is the largest size measured, not a proven maximum: 512 and 800 tokens were not run.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. Peak depends on BOTH the token count and `num_diffusion_samples`; the manifest states the worst point the two admit together and the ladder it was read from.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/opendde-resident.log`.
- `kit_foreign_objects`: you set `[kit] mode` to something other than `off`. The kit's one prebuilt object is x86-64; leave the mode at `off` on this architecture.
- A worker that never becomes ready and a `[opendde-opt] NOT ACTIVE: reason=undeclared variable(s) OPENDDE_OPT_...` line: an `OPENDDE_OPT*` name other than `OPENDDE_OPT` is exported. Unset it.
- Import/executable failure in the model half: re-run `tu remote setup opendde --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-opendde`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/opendde and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
