---
name: setup-colabdesign-remote-tool
description: Set up, launch, validate, and troubleshoot the ColabDesign (BindCraft binder design) ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up ColabDesign as a remote tool

> Validation status (2026-10-02): BindCraft's binder-hallucination step on ColabDesign 1.1.3 and AlphaFold-Multimer v3 ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `exact` mode, on jax/jaxlib 0.6.0 with CPython 3.10. **It needs no alignment and contacts no external service at request time**: the design step feeds AlphaFold the target's backbone as a template and a single sequence for the binder, so there is nothing to search or fetch. **Only the design step runs** — no MPNN redesign, reprediction, PyRosetta relaxation or filtering — so the sequences it returns are a hallucination's output, not filtered final designs. **Nobody holds the model**: upstream clears the device and rebuilds it for every trajectory, so what a held worker keeps is the imports, the CUDA context and the compile cache. **This skill is UNVERIFIED: the acceptance ladder, the 400-token row and the example run through the live endpoint were not completed** (stopped by the host memory guard). Measured so far: the smoke case is byte-identical between the kit's stock design body, the resident worker under `off` and under `exact` (design.pdb sha256 d2a404a3...), peak_pool 4.0 GiB at 100 and 200 tokens. Public publication, cross-user isolation, concurrency, recovery and scientific accuracy are unvalidated; keep this deployment private.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- A CUDA GPU is required. This provider holds its worker resident between requests.
- The model environment needs **Python 3.10** (`uv venv --seed --managed-python --python 3.10.18 ~/colabdesign-venv`).
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation colabdesign
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
python3 -m venv .venvs/colabdesign
. .venvs/colabdesign/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives at the path `TOOLUNIVERSE_COLABDESIGN_PYTHON` names, and
nothing above creates it. Create a **Python 3.10** interpreter there first, and
`tu remote setup --only environment` fills it from
`src/tooluniverse/remote/colabdesign/environment/requirements.lock` with
`--no-deps`, so no version is silently resolved to something else.

The kit pins its stack as conda packages, which do not install on aarch64, so the
lock is that stack expressed as PyPI distributions at the kit's own versions. The
index was checked per file: jaxlib 0.6.0 publishes a
`cp310-cp310-manylinux2014_aarch64` wheel, as do `jax-cuda12-plugin` 0.6.0 and
(as one `py3-none` file) `jax-cuda12-pjrt` 0.6.0, and every CUDA library the kit
pins has an aarch64 file at that version except NCCL, whose conda `.1` build
suffix has none (2.30.7 is used; one device never runs a collective).

**BindCraft's DSSP executable is an x86-64 binary, and it cannot run on aarch64.**
`run.sh install` fetches it from BindCraft's repository at the pinned commit
and digest-checks it; on this architecture it fails with `Exec format error`. The
worker probes it at start-up and, when it cannot run, sets BindCraft's own
`optimise_beta` setting false (the setting that calls DSSP on the stage-1
structure). The reply says `optimise_beta`. On a host where DSSP runs, BindCraft's
default is kept.

The rest is built by `tu remote setup`, which reads
`src/tooluniverse/remote/colabdesign/provider.toml` and runs five steps:
preflight, environment, kit, weights, smoke. Each refuses by name and carries
its fix.

~~~bash
export TOOLUNIVERSE_COLABDESIGN_PYTHON=~/colabdesign-venv/bin/python
export COLABDESIGN_PARAMS_DIR=~/.colabdesign
tu remote setup colabdesign
~~~

Run one step at a time with `--only preflight|environment|kit|weights|smoke`.
The smoke step is the one that matters: it holds the worker, sends one design
request, asserts the provider produced what its manifest says a successful run
produces (a `design.pdb` plus a non-empty `sequences`), and records the measured
peak VRAM to `~/.cache/tooluniverse/measured/colabdesign.json`. A host schedules
on that file.

Package/network-dependent commands must be rerun in a clean environment before marking this skill complete.

## The input

The tool takes the target as **PDB text** (`target_pdb`), its `chain`, the
`binder_len` and optionally `hotspot` residues in BindCraft's own grammar: `56`,
`31,33,57`, `A31,A33` or `A1-10`, in the PDB's own residue numbering. A hotspot
that names a residue the PDB does not hold is refused by upstream
(`positions 999 and chain A not found`) and the request fails; nothing is written.

**The ceiling is tokens, and the worker enforces it.** Target residues plus
binder length may not exceed 400, the row the VRAM budget was measured at.
Peak memory and time both grow with it, so crop the target to the region
around the site you want to bind, which is also BindCraft's own advice.

**Every distinct (target residues, binder length, recycles) triple is a new set of
XLA programs**, and the first request of one compiles for minutes. The reply says
`first_of_engine_key`. A trajectory that fails BindCraft's own pLDDT gates is
still a completed request: it returns its best sequence with
`accepted_by_stage_gates: false` and the gate named in `gate_fired`. Judge the
design, not the reply.

The optional iteration counts (`soft_iterations`, `temporary_iterations`,
`hard_iterations`, `greedy_iterations`) are BindCraft's own advanced settings,
defaults 75 / 45 / 5 / 15, bounded here. Upstream hard-codes the first 50 logit
iterations, so `soft_iterations` below 50 is not accepted.

## Obtain credentials, data, and model weights

- No credentials. `COLABDESIGN_PARAMS_DIR` (default `~/.colabdesign`) holds 1.7 GiB in five declared entries, `params/params_model_{1..5}_multimer_v3.npz`, each with a size and a digest. They are DeepMind's AlphaFold parameters (CC BY 4.0), fetched by the kit's own `python -m colabdesign_opt.weights` from `https://storage.googleapis.com/alphafold/alphafold_params_2022-12-06.tar` (a HEAD request answers 200, 5,587,968,000 bytes), and never from a mirror.
- **No alignment, no MMseqs2 server and no template database is needed or hidden.** Nothing in the request path touches the network.
- The only other thing `tu remote setup` fetches is BindCraft's DSSP executable, once, at install, digest-checked.
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
tu remote share colabdesign
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
tu remote share colabdesign --name my-colabdesign-remote --workers 1
~~~

Use `tu remote check colabdesign` for a non-sharing readiness check and
`tu remote run colabdesign` for a local-only foreground server.

In an interactive terminal, sharing automatically starts the same browser flow
when the key is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced; unset
or correct it, then run `tu remote login`. Non-interactive jobs also fail fast.
Use `tu remote logout` to remove only the local copy. Use `tu remote logout --revoke` to revoke the computer-only platform connection first; the server record remains offline for owner inspection.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.colabdesign.colabdesign_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8054/mcp. In a second activated shell run:

~~~bash
python - <<'EOF'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8054/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
EOF
~~~

Confirm discovery contains colabdesign_design; stop on empty, duplicate, or schema-drifted discovery.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses browser device authorization, so no key copy/paste or GitHub access is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8054/mcp --json
tu serve --share --forward http://127.0.0.1:8054/mcp --name validation-colabdesign --workers 1
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

Operation: colabdesign_design

The example is a deliberately tiny case so it answers in a minute or two: a
20-residue backbone-only crop of the PD-L1 target in BindCraft's own bundled
example (chain A, residues 46-65, hotspot 56) and a 12-residue binder, with only
the 50 logit iterations upstream hard-codes. It exercises the whole path; it is
not a design anyone should expect to pass BindCraft's gates.

~~~json
{"target_pdb": "ATOM    223  N   LYS A  46      42.677 -51.097 -27.336  1.00 30.62           N  \nATOM    224  CA  LYS A  46      43.737 -51.751 -28.084  1.00 33.55           C  \nATOM    225  C   LYS A  46      43.367 -53.198 -28.413  1.00 34.94           C  \nATOM    226  O   LYS A  46      43.812 -53.733 -29.424  1.00 36.17           O  \nATOM    232  N   GLN A  47      42.542 -53.793 -27.559  1.00 35.11           N  \nATOM    233  CA  GLN A  47      42.044 -55.155 -27.717  1.00 38.92           C  \nATOM    234  C   GLN A  47      40.532 -55.115 -27.597  1.00 35.82           C  \nATOM    235  O   GLN A  47      40.013 -54.557 -26.651  1.00 37.51           O  \nATOM    241  N   LEU A  48      39.839 -55.740 -28.541  1.00 34.86           N  \nATOM    242  CA  LEU A  48      38.396 -55.871 -28.486  1.00 33.75           C  \nATOM    243  C   LEU A  48      37.991 -56.747 -27.270  1.00 32.17           C  \nATOM    244  O   LEU A  48      38.291 -57.937 -27.261  1.00 34.34           O  \nATOM    249  N   ASP A  49      37.377 -56.147 -26.247  1.00 29.17           N  \nATOM    250  CA  ASP A  49      36.835 -56.894 -25.104  1.00 29.89           C  \nATOM    251  C   ASP A  49      35.384 -57.302 -25.342  1.00 27.26           C  \nATOM    252  O   ASP A  49      34.469 -56.551 -25.039  1.00 25.90           O  \nATOM    257  N   LEU A  50      35.166 -58.512 -25.836  1.00 27.29           N  \nATOM    258  CA  LEU A  50      33.796 -58.946 -26.135  1.00 26.96           C  \nATOM    259  C   LEU A  50      32.886 -59.041 -24.905  1.00 27.30           C  \nATOM    260  O   LEU A  50      31.676 -58.839 -25.015  1.00 27.10           O  \nATOM    265  N   ALA A  51      33.446 -59.312 -23.726  1.00 26.91           N  \nATOM    266  CA  ALA A  51      32.610 -59.468 -22.535  1.00 28.07           C  \nATOM    267  C   ALA A  51      31.873 -58.183 -22.187  1.00 27.80           C  \nATOM    268  O   ALA A  51      30.744 -58.228 -21.689  1.00 28.66           O  \nATOM    270  N   ALA A  52      32.463 -57.045 -22.559  1.00 27.21           N  \nATOM    271  CA  ALA A  52      31.887 -55.734 -22.245  1.00 25.64           C  \nATOM    272  C   ALA A  52      31.019 -55.140 -23.350  1.00 23.78           C  \nATOM    273  O   ALA A  52      30.189 -54.278 -23.054  1.00 26.12           O  \nATOM    275  N   LEU A  53      31.174 -55.625 -24.576  1.00 20.26           N  \nATOM    276  CA  LEU A  53      30.510 -55.050 -25.758  1.00 19.00           C  \nATOM    277  C   LEU A  53      29.093 -55.580 -25.988  1.00 18.32           C  \nATOM    278  O   LEU A  53      28.859 -56.795 -26.014  1.00 18.18           O  \nATOM    283  N   ILE A  54      28.177 -54.653 -26.220  1.00 17.55           N  \nATOM    284  CA  ILE A  54      26.876 -54.957 -26.764  1.00 17.55           C  \nATOM    285  C   ILE A  54      26.633 -54.103 -28.000  1.00 16.09           C  \nATOM    286  O   ILE A  54      26.825 -52.894 -27.947  1.00 16.82           O  \nATOM    291  N   VAL A  55      26.199 -54.738 -29.086  1.00 15.13           N  \nATOM    292  CA  VAL A  55      25.818 -54.058 -30.315  1.00 15.27           C  \nATOM    293  C   VAL A  55      24.373 -54.374 -30.630  1.00 14.36           C  \nATOM    294  O   VAL A  55      24.024 -55.547 -30.721  1.00 14.45           O  \nATOM    298  N   TYR A  56      23.555 -53.331 -30.811  1.00 13.69           N  \nATOM    299  CA  TYR A  56      22.116 -53.468 -30.995  1.00 13.66           C  \nATOM    300  C   TYR A  56      21.723 -52.695 -32.246  1.00 13.92           C  \nATOM    301  O   TYR A  56      21.989 -51.521 -32.334  1.00 14.70           O  \nATOM    310  N   TRP A  57      21.157 -53.377 -33.224  1.00 13.95           N  \nATOM    311  CA  TRP A  57      20.607 -52.725 -34.414  1.00 14.19           C  \nATOM    312  C   TRP A  57      19.111 -52.999 -34.500  1.00 13.68           C  \nATOM    313  O   TRP A  57      18.671 -54.159 -34.333  1.00 13.85           O  \nATOM    324  N   GLU A  58      18.334 -51.967 -34.832  1.00 13.55           N  \nATOM    325  CA  GLU A  58      16.912 -52.113 -35.054  1.00 13.97           C  \nATOM    326  C   GLU A  58      16.495 -51.300 -36.260  1.00 15.21           C  \nATOM    327  O   GLU A  58      17.196 -50.380 -36.684  1.00 14.76           O  \nATOM    333  N   MET A  59      15.322 -51.651 -36.797  1.00 16.36           N  \nATOM    334  CA  MET A  59      14.682 -50.807 -37.834  1.00 19.55           C  \nATOM    335  C   MET A  59      13.403 -50.356 -37.132  1.00 19.31           C  \nATOM    336  O   MET A  59      12.612 -51.231 -36.759  1.00 17.59           O  \nATOM    341  N   GLU A  60      13.194 -49.056 -37.006  1.00 19.50           N  \nATOM    342  CA  GLU A  60      12.153 -48.499 -36.124  1.00 21.07           C  \nATOM    343  C   GLU A  60      12.346 -49.170 -34.761  1.00 19.54           C  \nATOM    344  O   GLU A  60      13.380 -48.905 -34.121  1.00 18.62           O  \nATOM    350  N   ASP A  61      11.407 -50.016 -34.319  1.00 18.18           N  \nATOM    351  CA  ASP A  61      11.535 -50.673 -33.010  1.00 17.05           C  \nATOM    352  C   ASP A  61      11.775 -52.169 -33.169  1.00 16.99           C  \nATOM    353  O   ASP A  61      11.821 -52.926 -32.165  1.00 16.77           O  \nATOM    358  N   LYS A  62      11.916 -52.618 -34.418  1.00 16.15           N  \nATOM    359  CA  LYS A  62      12.090 -54.069 -34.696  1.00 17.08           C  \nATOM    360  C   LYS A  62      13.570 -54.450 -34.624  1.00 15.39           C  \nATOM    361  O   LYS A  62      14.352 -53.924 -35.408  1.00 14.38           O  \nATOM    367  N   ASN A  63      13.904 -55.370 -33.723  1.00 15.36           N  \nATOM    368  CA  ASN A  63      15.298 -55.736 -33.568  1.00 15.15           C  \nATOM    369  C   ASN A  63      15.815 -56.537 -34.741  1.00 15.86           C  \nATOM    370  O   ASN A  63      15.115 -57.419 -35.233  1.00 16.08           O  \nATOM    375  N   ILE A  64      17.013 -56.187 -35.189  1.00 16.06           N  \nATOM    376  CA  ILE A  64      17.704 -56.923 -36.236  1.00 16.96           C  \nATOM    377  C   ILE A  64      18.882 -57.673 -35.660  1.00 17.31           C  \nATOM    378  O   ILE A  64      18.998 -58.856 -35.915  1.00 18.04           O  \nATOM    383  N   ILE A  65      19.735 -56.991 -34.886  1.00 17.16           N  \nATOM    384  CA  ILE A  65      20.955 -57.579 -34.324  1.00 17.58           C  \nATOM    385  C   ILE A  65      20.987 -57.359 -32.817  1.00 16.65           C  \nATOM    386  O   ILE A  65      20.706 -56.261 -32.339  1.00 16.26           O  \nEND\n", "chain": "A", "binder_len": 12, "hotspot": "56", "seed": 0, "name": "example", "soft_iterations": 50, "temporary_iterations": 0, "hard_iterations": 0, "greedy_iterations": 0}
~~~

Invoke it through the live local MCP endpoint:

~~~bash
python - <<'EOF'
import asyncio
import json
import re
from fastmcp import Client

text = open("skills/setup-colabdesign-remote-tool/SKILL.md").read()
arguments = json.loads(re.search(r"~~~json\n(.*?)\n~~~", text, re.DOTALL).group(1))

async def main():
    async with Client("http://127.0.0.1:8054/mcp") as client:
        print(await client.call_tool("colabdesign_design", arguments))

asyncio.run(main())
EOF
~~~

The example has NOT been executed through the live endpoint yet; no result is quoted here.

## Tune GPU and concurrency

- Use one worker. The resident worker serves one request at a time by design; a second in-flight request queues on its lock rather than doubling peak VRAM.
- Peak pool reads 4.0 GiB at 100 and 200 tokens (peak in use 2.26 and 3.24 GiB); the 400-token row is not yet measured.
- `idle_timeout_s` is 300: with the kit's `exact` persistent cache a restarted worker's first call took 16-26 s where a cold one took 175-252 s.
- `XLA_PYTHON_CLIENT_PREALLOCATE=false` is set by the launch and is load-bearing for scheduling: left at its default JAX claims most of the card up front and every peak this provider reported would measure the preallocation instead of the model.
- Measure cold start, then **at least four consecutive identical requests**, then a mixed-shape sequence (small, small, large, small), then a request that changes the recycle count and back. A repeat and a shape change are different tests.
- Then parallel levels 1, 2, 4, 8, and only 16 if memory permits.
- Record successes/errors, p50/p95, peak RAM/VRAM, utilization, queueing, cancellation cleanup, and recovery.
- Increase workers only after single-flight initialization and sanitized recoverable OOM/timeout behavior are proven.

## Troubleshoot and clean up

- Read the refusal. Every step of `tu remote setup` names what is wrong and carries the fix; exit 3 is a refusal and exit 1 is a failure.
- The worker's own transcript is at `~/.cache/tooluniverse/remote-logs/colabdesign-resident.log`.
- **`grep -c "ready device" ` that log before believing a warm number.** From the supervisor's side a worker's death between requests is invisible, so a "warm" timing taken across one is not warm.

| refusal | what it means | what to do |
| --- | --- | --- |
| `env_python_unset` | `TOOLUNIVERSE_COLABDESIGN_PYTHON` is not exported | the refusal prints the recipe |
| `lock_install_failed` | the pinned stack did not install | read the tail; check the interpreter is Python 3.10 |
| `kit_install_failed` | `run.sh install` failed: pip, the DSSP fetch, or the kit's pin check | the printed line names which |
| `weights_off_pin` | a file is absent, short, or a different digest | the named file is left in place for inspection; remove it by hand and re-run `--only weights` |
| `smoke_workerstarterror` | the worker died before binding | read the transcript; the kit's own `NOT ACTIVE: ...` names an inherited `COLABDESIGN_OPT` value |
| `jax reports no GPU device` | the model interpreter sees no card | check the driver and `jax.default_backend()` in that interpreter |
| `<N> tokens ... exceeds this provider's 400` | target residues + binder length is past the budget's row | crop the target; the limit is the measured envelope |
| `refused by the kit: ...` | the kit's own named refusal before any model is built | the text names it (settings, DSSP, params file) |
| `positions <N> and chain <C> not found` | the hotspot names residues the PDB does not hold | use the PDB's own residue numbering |

- Import/executable failure in the model half: re-run `tu remote setup colabdesign --only environment`. It rebuilds from the lock with `--no-deps`.
- 401/403 on deliberate network binding: configure matching TOOLUNIVERSE_API_TOKEN bearer auth; prefer loopback plus relay.
- Stop server/relay with Ctrl-C. If installed, run `tuplatform-service uninstall --name validation-colabdesign`.
- A worker outliving its server is a known shape: it has an idle timeout and an orphan watchdog, and it exits when its parent becomes init. Check with `nvidia-smi --query-compute-apps=pid,used_memory --format=csv` before assuming the card is free.
- Revoke temporary keys. After confirmation, remove only .venvs/colabdesign and the provider's own cache directory; never use a broad recursive target.

Use only official upstream documentation linked by the implementation README; do not substitute third-party model mirrors.
