---
name: setup-gpnstar-remote-tool
description: Set up, launch, validate, and troubleshoot the GPN-Star ToolUniverse remote tool (single-nucleotide variant effect scores from a multi-species-alignment language model) and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up GPN-Star as a remote tool

> Validation status (2026-10-02): GPN-Star `v100-200m` (gpn 0.9.0, optimization kit `exact` mode) ran on the NVIDIA GB10 (aarch64, cc 12.1) under torch 2.13.0+cu130, so the GPU is open here. **What one request is:** a list of single-nucleotide variants (`chrom`, 1-based `pos`, `ref`, `alt`) scored against a multiple-species ALIGNMENT STORE the host holds; each score is `logit(alt) - logit(ref)` at the masked position, averaged over the forward and reverse-complement windows. GPN-Star is a language model over an alignment window, not over bare DNA. **The alignment store is an input, not a weight, and was NOT downloaded for this validation**: the real hg38 100-way store is a 42 GB zip that unpacks to ~64 GB (`songlab/multiz100way`). Everything above was measured against the kit's 0.14 MiB sparse example store (eight windows on chromosomes 1, 2, 3 and 5) and against a synthetic store of the same shape for worst-case content; any other position is refused with "the alignment holds no data". Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS, a mixed-batch-shape sequence, and a window / batch / single-variant / refusal sequence in which the same request returned a byte-identical `scores_sha256` five times. Peak reserved 1.01 GiB at 2 variants rising to 5.79 GiB at the 8192-column ceiling (batch 64 x window 128); declared budget 7.72 GiB, the stock-projection bound at that row. The kit's CUDA-graph lever is declined: with it on, 29 distinct batch shapes grew the reserve to 24.3 GiB. Wall times were taken on a contended card (load average ~65, five other GPU processes); peaks reproduce under contention and times do not. Public publication, cross-user isolation, concurrency, recovery and scientific validity of the scores against a full store are untested; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required (driver 580 or newer for the pinned CUDA 13.0 stack). This provider holds its model resident between requests; CPU is not a target.
- Keep provider data, weights, alignment stores, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation gpnstar
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point
-- the model's stack (Python 3.13, torch 2.13.0, transformers 5.15.0) is not
installable beside ToolUniverse's.

~~~bash
python3 -m venv .venvs/gpnstar
. .venvs/gpnstar/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_GPNSTAR_PYTHON` names, and
nothing above creates it. Create an empty interpreter there first with
`uv venv --seed --managed-python --python 3.13 ~/gpnstar-venv` (upstream
requires Python >= 3.13, < 3.14), and `tu remote setup --only environment`
fills it from `src/tooluniverse/remote/gpnstar/environment/requirements.lock`
with `--no-deps`, so no version is silently resolved to something else. That
step needs network and `git`: the lock names stock `gpn` by its pinned commit,
and pip builds it with hatchling.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/gpnstar/provider.toml` and runs five steps: preflight,
environment, kit, weights, smoke. Each refuses by name and carries its fix.

~~~bash
export TOOLUNIVERSE_GPNSTAR_PYTHON=~/gpnstar-venv/bin/python
export HF_HOME=~/.gpnstar/hf_home
tu remote setup gpnstar
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`
while bringing a machine up. The smoke step is the one that matters: it holds
the model, sends one request of eight example variants, asserts the provider
produced what its manifest says a successful run produces (a non-empty `scores`
and `ids`), and records the measured peak VRAM to
`~/.cache/tooluniverse/measured/gpnstar.json`. A host schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## Obtain credentials, data, and model weights

- HF_HOME names the Hugging Face cache holding the checkpoint snapshot (`hub/models--songlab--gpn-star-hg38-v100-200m/snapshots/<commit>/`, 0.8 GB). `tu remote setup gpnstar --only weights` fetches it with the kit's own downloader from upstream's repository at the pinned revision and checks all nine files by sha256 and size. The model card says `license: mit`.
- Nothing is fetched at request time. The manifest declares every weight file with its size and sha256, and the launch refuses if one is off its pin.
- **The alignment store is yours to supply.** Unset, the provider reads the kit's sparse example (`examples/msa`, windows of eight variants on chromosomes 1, 2, 3 and 5 only). For real use point TOOLUNIVERSE_GPNSTAR_MSA_ROOT at a directory holding `<n_species>/all.zarr` -- for the primary model `<root>/100/all.zarr`, one array per chromosome named `1` ... `22`, `X`, `Y`:

~~~bash
hf download songlab/multiz100way 99.zarr.zip --repo-type dataset --local-dir /data/msa   # a 42 GB download
python -m zipfile -e /data/msa/99.zarr.zip /data/msa/100/all.zarr/                      # unpacks to ~64 GB
export TOOLUNIVERSE_GPNSTAR_MSA_ROOT=/data/msa
~~~

  `ref` must equal the alignment's own human base at that position (there is no genome FASTA); a mismatch is refused, not scored.
- TOOLUNIVERSE_GPNSTAR_GRAPHS (default `off`) keeps or drops the kit's CUDA-graph lever. Leave it off unless you have measured the memory: the lever keeps one graph pool per distinct batch shape and nothing bounds the number of shapes.

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
tu remote share gpnstar
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
tu remote share gpnstar --name my-gpnstar-remote --workers 1
~~~

Use `tu remote check gpnstar` for a non-sharing readiness check and
`tu remote run gpnstar` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.gpnstar.gpnstar_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8057/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8057/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains run_gpnstar_vep; stop on empty, duplicate, or schema-drifted discovery.

The first request after a restart pays the interpreter, the imports and the 0.8 GB checkpoint read (about 15-35 s on a contended card); the ones after it do
not. That is the whole reason this provider is resident, and a benchmark that
measures only the first call measures the wrong thing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8057/mcp --json
tu serve --share --forward http://127.0.0.1:8057/mcp --name validation-gpnstar --workers 1
~~~

Prefer browser device authorization. For CI or migration, supply
`TOOLUNIVERSE_SERVICE_KEY` only through a protected environment or use
`tu remote login --manual-key`; never put a key in shell arguments.

This implementation was added after the authenticated 2026-08-16 Platform matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested.

## Run a verified example

Operation: run_gpnstar_vep

~~~json
{"variants": [{"chrom": "1", "pos": 1425822, "ref": "C", "alt": "G"}, {"chrom": "2", "pos": 5718743, "ref": "A", "alt": "G"}, {"chrom": "3", "pos": 213423, "ref": "A", "alt": "G"}, {"chrom": "5", "pos": 850655, "ref": "C", "alt": "T"}], "window_size": 128, "batch_size": 8}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"variants": [{"chrom": "1", "pos": 1425822, "ref": "C", "alt": "G"}, {"chrom": "2", "pos": 5718743, "ref": "A", "alt": "G"}, {"chrom": "3", "pos": 213423, "ref": "A", "alt": "G"}, {"chrom": "5", "pos": 850655, "ref": "C", "alt": "T"}], "window_size": 128, "batch_size": 8}''')
    async with Client("http://127.0.0.1:8057/mcp") as client:
        result = await client.call_tool("run_gpnstar_vep", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape, as returned on the validation host with the kit's example store: `n_variants` 4, `ids` `["1:1425822:C>G", "2:5718743:A>G", "3:213423:A>G", "5:850655:C>T"]`, and `scores` `[2.88394, -0.08641, -3.10446, 0.36191]` (negative: the alternate base is less likely than the reference given the alignment), plus `scores_sha256`, `window_size`, `batch_size`, `levers_applied`, `levers_declined` (`["graph"]`) and `peak_reserved_gib`. The same eight variants through the kit's own `GPNSTAR_OPT=exact gpn star vep` and through stock `gpn star vep` write byte-identical parquet, and this worker's `scores_sha256` over them matches both. Scores are reproducible per (variants, batch shape); a different `batch_size` can move the last digits, because cuBLAS picks its algorithm per shape.

Things the tool refuses rather than guesses, each by name: a `ref` that disagrees with the alignment; a position the store holds no data at; `batch_size` x `window_size` above 8192 columns per forward (this is what bounds peak memory); `variants` x `window_size` above 524,288 (this is what bounds how long one call holds the worker); more than 2048 variants; an odd or out-of-range window; indels and ambiguity codes. One variant alone is scored as a batch of two copies (upstream's own command fails on a one-row table) and the reply says `single_variant_sent_twice`. Check scientific meaning, output bounds, invalid-input behavior, and absence of paths, secrets, and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Read `vram_budget_gb` from the provider manifest and the measured file before co-tenanting anything else on the card. Peak follows `batch_size` x `window_size`, not the variant count: 2.5 GiB holds a host that never goes past 16 x 128, and the declared 7.72 GiB covers the 64 x 128 corner under the stock K/V projections.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small), then change `window_size` and `batch_size` separately: they change the kit's per-shape state and are the engine key here, not the variant count. Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/gpnstar-resident.log`, and it holds the kit's lever census. The kit's ACTIVE and LEVER lines still name `graph` as on; the worker declines it afterwards and says so on its own line and in every reply.
- `Reference allele mismatch ... genome has '-'` means the alignment holds nothing at that position: you are on the sparse example store, or the position is outside the store. Set TOOLUNIVERSE_GPNSTAR_MSA_ROOT to a full store.
- `[gpnstar-opt] NOT ACTIVE` at start means the kit refused the stack (gpn or transformers off their pins, no CUDA device, or a weight file off its digest); `bash run.sh check` in the kit checkout prints the reason.
- Import/executable failure in the model half: re-run `tu remote setup gpnstar --only environment`. It rebuilds from the lock with `--no-deps` and will not silently resolve a different version.
- Weights off their pin: the named file is left in place for inspection rather than deleted, because a truncated transfer and a corrupt file look alike. Remove it by hand and re-run `--only weights`.
- TF32: the launch removes `NVIDIA_TF32_OVERRIDE` and `TORCH_ALLOW_TF32_CUBLAS_OVERRIDE` from the worker's environment, so a shell that exports them cannot move the scores out of fp32.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-gpnstar`.
- A worker outliving its server is a known shape: it has an idle timeout (300 s) and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/gpnstar, `~/gpnstar-venv` and the provider's own cache directory (`~/.gpnstar`); never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
