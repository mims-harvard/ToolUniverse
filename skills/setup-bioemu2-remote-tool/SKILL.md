---
name: setup-bioemu2-remote-tool
description: Set up, launch, validate, and troubleshoot the BioEmu-2 ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up BioEmu-2 as a remote tool

> Validation status (2026-10-25): BioEmu-2 ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified), driver 580.173.02, through this provider's own path. `tu remote setup` completed all four steps: weights 2/2 at their pins after an independent fetch, and the smoke OK in 89 s at 2.06 GiB peak reserved with both declared outputs matched by the manifest's globs. Four socket requests exercised the one-entry session cache in both directions; 428- and 642-token multi-chain systems ran on the same socket with real ColabFold queries, every frame passing physicality; a three-shape session at and below the 448-token ceiling held peak reserved flat at 12.38 GiB. The live MCP endpoint on 8063 returned correct results for three calls and named refusals for six malformed ones, four from the tool and two from the published schema, with no traceback reaching a caller. The orphan watchdog was observed releasing the card 122 s after the server stopped. Every wall-clock figure is an upper bound measured under a host load average of 26-45 and is not the model's speed; no saving from trunk reuse is established, because an identical repeat ran 15.4 s then 11.1 s through the socket but 22.3 s then 23.6 s through MCP -- opposite signs, both inside the noise at 20 tokens. Propagation is not exposed. Only protein chains have gone through the worker; ligands, RNA, DNA, contact conditioning, steering samplers and every physicality mode but high_quality are unexercised. Ensemble accuracy is unvalidated and nothing here checks it: the physicality report is geometry, and sampling frequency is not a calibrated Boltzmann probability. Public publication, cross-user isolation, concurrency, recovery and long inputs are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests; CPU is not a target. Upstream supports Linux and NVIDIA only.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation bioemu2
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point
-- the model's stack pins `torch<2.14` while every other provider on this card
runs 2.14.x.

~~~bash
python3 -m venv .venvs/bioemu2
. .venvs/bioemu2/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_BIOEMU2_PYTHON` names, and
nothing above creates it. Create an empty interpreter there first --
`python3 -m venv ~/bioemu2-venv`, or `uv venv` -- and
`tu remote setup --only environment` fills it from
`src/tooluniverse/remote/bioemu2/environment/requirements.lock` with
`--no-deps`, so no version is silently resolved to something else.

**Three resolver traps are recorded in that lock's header and each cost a
run.** `bioemu2` is published only as `0.1.0rc0`, so installing it needs
`--prerelease allow` -- and that flag is global in `uv`, so it also drags in
prereleases of five packages that have perfectly good stable releases.
`hydra-core` 1.3.7 declares `omegaconf<2.4`, so the stable pair is 1.3.7 +
2.3.0, and pinning omegaconf back to 2.3.0 needs `antlr4-python3-runtime`
added by hand, because 2.4 dropped that dependency and `--no-deps` will not
re-add it -- the symptom is `ModuleNotFoundError: No module named 'antlr4'` on
every hydra import.

**The `torch<2.14` pin is not a blocker on an sm_121 card, and the reason is
worth knowing.** PyPI's `torch==2.13.0` aarch64 wheel is a `+cu130` build whose
arch list reads sm_80, sm_90, sm_100, sm_110, sm_120 -- it does not name
sm_121 -- and it drives the GB10 anyway through CUDA 13 family compatibility.
That was measured with a device matmul rather than inferred, because the
inference went the other way once before: torch 2.5.1 on the same card reports
`is_available True` and then raises "no kernel image is available" on the first
device allocation. cuEquivariance is covered by name: `cuobjdump --list-elf` on
`libcue_ops.so` reports an **sm_121a** cubin.

**This provider wraps no optimization kit**, so its setup has four steps rather
than five -- there is no kit step. Upstream publishes the inference runtime
itself as `bioemu2` on PyPI, and the levers a kit would add (`precision`,
`matmul_precision`, `batch_size`, `num_steps`, `compile_denoiser`, the tiled
cuEquivariance kernels) are arguments the package already owns.

~~~bash
export TOOLUNIVERSE_BIOEMU2_PYTHON=~/bioemu2-venv/bin/python
export BIOEMU2_HF_HOME=~/.cache/tooluniverse/bioemu2-hf   # optional
tu remote setup bioemu2
~~~

Run one step at a time with `--only preflight|environment|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request, asserts the provider produced what its manifest
says a successful run produces (`topology.cif` and `samples.xtc`), and records
the measured peak VRAM to `~/.cache/tooluniverse/measured/bioemu2.json`. A host
schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- No credential is needed. The checkpoint is public on the Hugging Face Hub under the MIT License.
- `BIOEMU2_HF_HOME` names the Hub cache the pinned snapshot is fetched into; it defaults to `~/.cache/tooluniverse/bioemu2-hf` and does not have to be set.
- **The checkpoint's `config.yaml` is pinned for a security reason, not only a reproducible one.** `load_model()` builds the network by handing that config to `hydra.utils.instantiate()`, and hydra's own warning on that call is explicit: "config-controlled targets can execute arbitrary code. This warning will become an error in Hydra 1.5." A `_target_` is an import path hydra will import and call, so a config that has moved off its pin is a refusal rather than something to load and hope about.
- The 2.05 GB `checkpoint.ckpt` digest is upstream's own: it is the `lfs.oid` the Hub API reports, confirmed equal to the sha256 of the bytes this provider was built on. The `config.yaml` digest is **not** independently corroborated -- that file is under the Hub's LFS threshold so the API reports only a git blob sha1, which is a hash over a different preimage and cannot be compared. The pinned value was computed here.
- Nothing is fetched at request time. The launch refuses if either file is off its pin.

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
tu remote share bioemu2
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
tu remote share bioemu2 --name my-bioemu2-remote --workers 1
~~~

Use `tu remote check bioemu2` for a non-sharing readiness check and
`tu remote run bioemu2` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.bioemu2.bioemu2_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8063/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8063/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains bioemu2_sample_structures; stop on empty,
duplicate, or schema-drifted discovery.

The first request after a restart pays the model build; the ones after it do
not. Here that cost is unusually concentrated in the **load**: `load_model()`
measured 44.6-49.9 s, against about 8 s of CUDA warm-up on top. That is the
whole reason this provider is resident, and a benchmark that measures only the
first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8063/mcp --json
tu serve --share --forward http://127.0.0.1:8063/mcp --name validation-bioemu2 --workers 1
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

Operation: bioemu2_sample_structures

~~~json
{"sequences": ["NLYIQWLKDGGPSSGRPPPS"], "mode": "structure", "num_samples": 1, "seed": 0, "msa_a3m": {"A": ">query\nNLYIQWLKDGGPSSGRPPPS\n"}}
~~~

That is Trp-cage (PDB 1L2Y), the same system the provider ships as its smoke
input at `src/tooluniverse/remote/bioemu2/smoke/trp_cage.yaml`, and it is a
request that works rather than only a shape. **Its `msa_a3m` is a
single-sequence alignment**, which is legitimate A3M and a poor alignment: it
is there so the example touches no third-party server, and its structural
quality is correspondingly not something to read anything into.

Omitting `msa_a3m` is the normal path and sends a query to the **public
ColabFold server** on a cache miss. Use `system_yaml` instead of `sequences`
for ligands by CCD code or SMILES, nucleic acids, modified residues, explicit
chain ids or non-standard covalent bonds.

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

TRP_CAGE = "NLYIQWLKDGGPSSGRPPPS"

async def main():
    async with Client("http://127.0.0.1:8063/mcp") as client:
        result = await client.call_tool(
            "bioemu2_sample_structures",
            {
                "sequences": [TRP_CAGE],
                "mode": "structure",
                "num_samples": 1,
                "seed": 0,
                "msa_a3m": {"A": f">query\n{TRP_CAGE}\n"},
            },
        )
        print(result.content[0].text)

asyncio.run(main())
PY
~~~

Expected success shape: `mode`, `num_samples`, `tokens`, `chains`, `msa`
(either `caller` or `colabfold`, so a reply says which path it took), a
`physicality` object carrying per-frame `passed` and `reasons`, a `files`
list, `timing` with `generate_s` and `embeddings_reused` -- one figure and not two, because `EmuSession()` only stores its inputs and the trunk runs lazily inside the first `sample()`, so a separate "embedding" timing would read ~0 s and hide the trunk in the sampling number -- plus
`weights_held_by`, `peak_reserved_gib` and `peak_allocated_gib`. The
`topology.cif` text is returned only when `return_topology` is true; it is off
by default because a transport truncates an oversized reply into invalid JSON
rather than refusing it, and the trajectory frames are never inlined. Check
scientific meaning, output bounds, invalid-input behavior, and absence of
paths, secrets, and traces.

**A frame that fails physicality is still returned and still saved.** The
check labels frames; it does not filter them. `physicality.checked` is false
when no eligible protein atoms were found, in which case every frame is
reported `not_checked` rather than passing.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. The declared 16.0 GiB sits above a measured 12.38 GiB session high-water mark at the 448-token ceiling, and the pool reserves what is declared on **every** request, large or small, so the headroom is paid for by every co-tenant all the time. Budget against **reserved**, not allocated: the largest in-cap request allocated 8.56 GiB, and a worker budgeted on that would be 3.8 GiB short of what it holds.
- **`num_samples` costs wall clock, not memory, at these sizes.** 1UBQ peaked at 3.03 GiB for both 1 and 16 samples, and a 214-token request at 16 samples allocated less than a 428-token one at 4: the `O(N²)` pair representation dominates the `O(BN)` term.
- **The token ceiling is 448, and two axes put it there.** Trunk memory is `O(RN + N²)`, so alignment depth matters as much as size: 676 tokens with a 234 KB A3M cost less than 428 with a 3.2 MB one. And the allocator's high-water never shrinks, so a 642-token request reserved 18.04 GiB fresh and 21.15 GiB as a session's second. Admitting 642 would mean declaring roughly 24 GiB on every request. Below 448 neither effect appears -- three shapes in one session all held 12.38 GiB.
- **Tokens are not residues, and the difference is in the unsafe direction.** The worker counts them as BioEmu-2 does, with `AllAtomStructure.num_tokens`: 1AKE from the PDB is 271 tokens against 214 residues, 6LU7 is 676 against 624. A ceiling checked against a residue sum would admit a system a fifth larger than the budget was measured at.
- The worker caches **one** `EmuSession`, so a repeat request for the same system, MSA and mode skips the trunk entirely; `timing.embeddings_reused` says whether it did. Alternating between two systems defeats it by design -- the pair representations are `O(N²)` and holding two would put the footprint outside the declared budget.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape. A repeat and a shape change are different tests and a resident provider has to survive both.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/bioemu2-resident.log`.
- **`CUDA error: out of memory` on a 500M-parameter model is almost always the host, not the request.** This card's memory is unified with system RAM, so another tenant's spike denies an allocation that succeeded minutes earlier. Check `free -g` and `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before changing anything; the first end-to-end run here failed this way and the identical rerun succeeded.
- **A request that hangs before sampling is usually the ColabFold query**, not the model. The log line that ends it names the cache path it wrote. Supply `msa_a3m` to take the network out of the request entirely.
- **`pynvml` is not supported on the GB10**, so BioEmu-2 logs `Failed to get GPU information from pynvml: Not Supported. Using default values for NVIDIA GB10` and proceeds on hardcoded defaults. It is noise on this card rather than a fault, but any heuristic upstream derives from those numbers is working from guesses here.
- Import/executable failure in the model half: re-run `tu remote setup bioemu2 --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version. If you are building the lock by hand instead, read its header first -- see the three resolver traps above.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-bioemu2`.
- A worker outliving its server is a known shape, and it was observed here: with the server stopped the worker logged `orphaned (parent gone) and idle 122s >= 120s: releasing the GPU and exiting` and left no process on the card. **Its socket file survives that exit** -- `os._exit(0)` skips cleanup by design -- so judge liveness with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` or by PID, never by `ls` on the socket directory.
- Revoke temporary keys. After confirmation, remove only .venvs/bioemu2 and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
