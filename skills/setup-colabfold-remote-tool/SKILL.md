---
name: setup-colabfold-remote-tool
description: Set up, launch, validate, and troubleshoot the ColabFold (AlphaFold2-Multimer) ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up ColabFold as a remote tool

> Validation status (2026-10-01): ColabFold 1.6.1 on AlphaFold2-Multimer v3 ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode, on jax/jaxlib 0.5.3. **It takes a precomputed MSA and contacts no MMseqs2 server** — that is upstream's own branch (`run()` is `if a3m_lines is None: get_msa_and_templates(...) else: unserialize_msa(...)`), and `run_mmseqs2` is imported inside the branch this provider never takes. **Stock ColabFold cannot fold on this card at all**: the forward pass aborts with `Unsupported conversion from bf16 to f16 / LLVM ERROR: Unsupported rounding mode for conversion`, an uncatchable `report_fatal_error` from LLVM's NVPTX instruction selector, because ColabFold keeps its two recycle-state tensors in float16 while the trunk is bf16. Upstream's own `use_bfloat16=False` clears it, and that parameter has no command-line flag — `colabfold_batch` exits 134 (SIGABRT) on this hardware having written logs and no structure. So this wrapper is not a faster route to the model here; it is the only one. 17 requests, 17 ranked structures, 0 failures. Ladder 4.0 GiB flat at 100 / 200 / 400 residues (declared at 400); residency 1.16x warm, because upstream persists the expensive part. Public publication, cross-user isolation, concurrency, recovery and scientific accuracy are unvalidated; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its model resident between requests.
- The model environment needs **Python 3.11** (`uv venv --seed --managed-python --python 3.11 ~/colabfold-venv`).
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation colabfold
~~~

After exporting provider resources, add `--check-provider-env`. After the
server starts, add `--live` to verify the exact MCP tool set without running
the model. Before sharing, add `--check-connect-prereqs`; this reports only
whether a key is set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments, not
one: the MCP server runs in ToolUniverse's, and the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point.

~~~bash
python3 -m venv .venvs/colabfold
. .venvs/colabfold/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_COLABFOLD_PYTHON` names, and
nothing above creates it. Create a **Python 3.11** interpreter there first, and
`tu remote setup --only environment` fills it from
`src/tooluniverse/remote/colabfold/environment/requirements.lock` with
`--no-deps`, so no version is silently resolved to something else.

The lock carries exactly **one** deviation from the kit's, and it is a package
NAME rather than a version: `tensorflow_cpu==2.21.0` publishes x86-64 and
Windows wheels only, while `tensorflow==2.21.0` publishes a cp311
`manylinux_2_27_aarch64` wheel which on this architecture IS the CPU build.
Everything else is at its pin. The kit's own gate notices — expect this line
and do not widen the gate to silence it:

~~~
[colabfold-opt] PINS NOT MET packages=MISMATCH files=ok
  tensorflow_cpu: expected 2.21.0 got None
~~~

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/colabfold/provider.toml` and runs five steps:
preflight, environment, kit, weights, smoke. Each refuses by name and carries
its fix.

~~~bash
export TOOLUNIVERSE_COLABFOLD_PYTHON=~/colabfold-venv/bin/python
export COLABFOLD_OPT_DATA_DIR=~/.colabfold
tu remote setup colabfold
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`.
The smoke step is the one that matters: it holds the model, sends one request,
asserts the provider produced what its manifest says a successful run produces
(`*_unrelaxed_rank_*.pdb` plus a non-empty `structures`), and records the
measured peak VRAM to `~/.cache/tooluniverse/measured/colabfold.json`. A host
schedules on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## The input dialect, and why it has to be exact

A **plain a3m** is one chain: the whole file is its unpaired MSA. A **complex
a3m** begins `#<len1>,<len2>\t<card1>,<card2>` — the aligned lengths of the
*unique* chains and how many copies of each. Line 2 is `>101\t102`, line 3 is
the concatenated unique query, and every later row is split by aligned-column
count into paired and per-chain unpaired alignments.

**The alignment width is the unique lengths summed, not the complex's residue
count.** A four-chain 574-residue hemoglobin is `#141,146\t2,2` with every line
287 columns wide. `unserialize_msa` re-cuts every later row using the header's
numbers, so a header that disagrees with the rows does not error — it silently
feeds the model a different alignment. A single-sequence a3m is the MSA-free
sentinel, and pLDDT around 35 is the expected consequence rather than a fault.

## Obtain credentials, data, and model weights

- No credentials. `COLABFOLD_OPT_DATA_DIR` (default `~/.colabfold`) holds 1.7 GiB in six declared entries, each with a size and a digest. One of them is a 0-byte `download_complexes_multimer_v3_finished.txt`, declared on purpose: without that marker upstream's CLI re-downloads 2 GB at run time.
- **No local MMseqs2 database is needed and none is hidden.** The search is the remote service's, and this provider never takes that branch, so no route here carries a UniRef or environmental database. Templates are refused by name, because upstream's only template route for an a3m input calls the same remote service.
- Nothing is fetched at request time.

## Authorize once, then share with one short command

After installing dependencies, exporting the provider resources above, and
installing the pinned relay SDK described under Connect below, run from the
repository root. Log in only once per machine (and again after key rotation):

~~~bash
tu remote login
# Or import an existing protected 0600 file without sourcing it:
tu remote login --env-file /path/to/tooluniverse-service.env
~~~

Then each private share is one short command:

~~~bash
tu remote share colabfold
~~~

By default, `tu remote login` requests a short-lived device code, opens the
TU Platform approval page, and polls until the signed-in user approves. No key
copy/paste is required. On a headless machine, add `--no-browser` and open the
printed link elsewhere. The CLI exchanges the approval for a computer-only key,
verifies `/remote-servers/preflight`, stores it in a local 0600 config file, and
never displays it.

The share command runs environment and TU Platform preflights, starts or reuses
the exact loopback endpoint, validates discovery, and keeps the relay in the
foreground until Ctrl-C. Override the defaults only when needed:

~~~bash
tu remote share colabfold --name my-colabfold-remote --workers 1
~~~

Use `tu remote check colabfold` for a non-sharing readiness check and
`tu remote run colabfold` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.colabfold.colabfold_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8051/mcp. In a second activated shell run:

~~~bash
python - <<'EOF'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8051/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
EOF
~~~

Confirm discovery contains colabfold_predict; stop on empty, duplicate, or schema-drifted discovery.

**There are no padding buckets on this path.** Upstream pads only the monomer
branch, and this provider runs the multimer parameters, so every distinct total
length is its own XLA compilation and the reply says `padding = "none"`. The
MSA axis *is* padded to fixed widths, so alignment depth changes no shape: an
8-row MSA at an already-compiled length costs about 10 s and rebuilds nothing.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8051/mcp --json
tu serve --share --forward http://127.0.0.1:8051/mcp --name validation-colabfold --workers 1
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

Operation: colabfold_predict

The example is the smoke input: insulin, chains A (21) and B (30), as a
two-chain a3m with no alignment rows beyond the query — MSA-free, which is why
one model and one recycle are enough to exercise the path.

~~~json
{"a3m": "#21,30\t1,1\n>101\t102\nGIVEQCCTSICSLYQLENYCNFVNQHLCGSHLVEALYLVCGERGFFYTPKT\n>101\nGIVEQCCTSICSLYQLENYCN------------------------------\n>102\n---------------------FVNQHLCGSHLVEALYLVCGERGFFYTPKT\n", "name": "insulin", "num_models": 1, "num_recycles": 1, "seed": 0}
~~~

Invoke it through the live local MCP endpoint:

~~~bash
python - <<'EOF'
import asyncio
import json
import pathlib
from fastmcp import Client

a3m = pathlib.Path("src/tooluniverse/remote/colabfold/smoke/input.a3m").read_text()
arguments = {"a3m": a3m, "name": "insulin", "num_models": 1, "num_recycles": 1, "seed": 0}

async def main():
    async with Client("http://127.0.0.1:8051/mcp") as client:
        print(await client.call_tool("colabfold_predict", arguments))

asyncio.run(main())
EOF
~~~

Expected success shape, with the reply's own key names: `n_structures` above
zero, `scores` (one record per model, ranked best-first, carrying `mean_plddt`,
`ptm`, `iptm`), `best`, `query_length`, `chains`, `msa_rows`, `msa_source`,
`engine_rebuilt` and `weights_held_by = "worker"`. **There is no `structures`
key unless you pass `return_structures: true`** — the PDB text is opt-in because
it is megabytes per model, and `n_structures` is what tells you a fold
happened. The worker's own reply carries `padding = "none"`; the MCP layer does
not forward it.

Run above, on this example: `n_structures: 1`, `mean_plddt 44.72`, `chains: 2`,
`msa_rows: 1`, `msa_source: "caller (precomputed a3m; no MMseqs2 server
contacted)"`. A pLDDT in the forties is the expected consequence of a
single-sequence MSA, not a fault — see the dialect section. Check scientific
meaning, output bounds, invalid-input behavior, and absence of paths, secrets,
and traces.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- **The budget is flat and the quantisation is why one column would say nothing.** `peak_pool_bytes` reads 4.0 GiB at 100, 200 and 400 residues while the working set sits at 2.52; the pool doubles once at the first request and never moves. (`peak_bytes_reserved` reads 0 and is a trap.) The shape is ESM C's, not OpenFold3's: 1.86 GB of held parameters plus fixed buffers set the mark and a 400-residue pair track never approaches it. So capping length buys a host **no memory** — what length buys is time, about 2.9x per doubling.
- `XLA_PYTHON_CLIENT_PREALLOCATE=false` is set by the launch and is load-bearing for scheduling: left at its default JAX claims most of the card up front and every peak this provider reported would measure the preallocation instead of the model.
- **`idle_timeout_s` is 300, not 900, and that is an argument rather than a default.** Upstream persists its XLA compilation cache, so a restart *reloads* in about 10 s what it first *compiled* in about 70. Residency still keeps the imports, the 1.86 GB parameter read, the model trace and the in-process executable cache — about 12–22 s against 73 s of work, which is 1.16x warm. That is the opposite of af3_jax, whose autotune nothing persists and which therefore holds its worker three times as long.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small). Two warm calls of different shapes is not enough: openfold3 passed exactly that and still died on the second request of the same shape. A repeat and a shape change are different tests. Here the shape change is the whole test, because there are no buckets to hide behind.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/colabfold-resident.log`.
- **`grep -c "ready device" ` that log before believing a warm number.** One worker exited silently between two requests during validation — no log line, no traceback, no refusal — and the supervisor restarted it transparently. From the supervisor's side a death between requests is invisible, so a "warm" timing taken across one is not warm.

| refusal | what it means | what to do |
| --- | --- | --- |
| `env_python_unset` | `TOOLUNIVERSE_COLABFOLD_PYTHON` is not exported | the refusal prints the recipe |
| `lock_install_failed` | the pinned stack did not install | read the tail; check the interpreter is Python 3.11 |
| `kit_install_failed` | a package is off its pin | the printed line names which. Only `tensorflow_cpu` is accepted, and only against `tensorflow` at the same version |
| `weights_off_pin` | a file is absent, short, or a different digest | the named file is left in place for inspection; remove it by hand and re-run `--only weights` |
| `smoke_workerstarterror` | the worker died before binding | read the transcript; the kit's own `NOT ACTIVE: undeclared variable(s) …` names an inherited `COLABFOLD_OPT*` typo |
| `jax reports no GPU device` | the model interpreter sees no card | check the driver and `jax.default_backend()` in that interpreter |
| `use_bfloat16` / `use_templates` / `num_relax` / `msa_mode` | asked for at request time | refused by name. `use_bfloat16: true` is refused because the abort it causes is uncatchable and would take the worker down rather than fail the request |
| `num_models x num_seeds > 5` | more passes than the timeout admits | 5 passes at 400 residues measured 1736 s against a 3600 s request timeout |

- Import/executable failure in the model half: re-run `tu remote setup colabfold --only environment`. It rebuilds from the lock with `--no-deps`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-colabfold`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/colabfold and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
