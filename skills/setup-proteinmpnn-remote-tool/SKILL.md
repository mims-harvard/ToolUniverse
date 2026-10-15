---
name: setup-proteinmpnn-remote-tool
description: Set up, launch, validate, and troubleshoot the ProteinMPNN / SolubleMPNN fixed-backbone sequence-design ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up ProteinMPNN sequence design as a remote tool

> Validation status (2026-10-14): ProteinMPNN sequence design ran on the NVIDIA
> GB10 host (aarch64, 20 cores, 121.6 GiB unified memory, cc 12.1, driver
> 580.173.02) **on the CPU**, holding stock ProteinMPNN at commit `8907e667`.
> **`[gpu] policy = "none"` and `vram_budget_gb` is absent, which is the point of
> this provider:** `remote_resident/admission.py` skips a provider with no
> declared budget, so this one is admitted while the card is full and can be
> resident alongside every folding model on the box. Its central claim is
> equivalence, not speed: the worker holds stock's own loop and the acceptance
> suite byte-compares its reply against `run.sh design --mode off` across five
> cases — two backbones, two seeds, two temperatures, two batch layouts and both
> weight sets — comparing every field stock writes, which came out **identical**.
> The optimization kit's `exact` line also runs on this CPU host and is also
> byte-identical to stock there, and it was **declined on the clock**: 38.53 s of
> generation against stock's 30.45 s. Both of those were measured together on a
> contended host, so the decision stands while the absolute figures do not -- a
> later quiet-host pair read stock's generation at 14.4-15.2 s. Residency itself
> is worth **1.13x** here, not the 1.40x first recorded; `provider.toml`'s header
> has that correction and its arithmetic.
> Public publication, cross-user isolation, concurrency and recovery are
> untested; keep this deployment private.

## What this provider is for

Inverse folding: you have a backbone and want sequences that fold to it.
ProteinMPNN is the field's default for that step — 1.66M parameters, seconds per
design on a CPU — and it is what you run between a backbone generator
(RFdiffusion, Genie) and a structure predictor that checks the design folds back
(Boltz, OpenFold3, ColabFold).

Two sibling providers overlap and are worth distinguishing:

- **esm_if1** also designs a sequence for a backbone, by a 142M-parameter
  GVP-Transformer decode. Different model, different prior; also CPU-only here.
- **ef2inv** designs a *binder* sequence by gradient descent through a folding
  model, which is a different task and a GPU one (28.03 GiB).

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- **No GPU is required, and none is used.** `[gpu] policy = "none"` makes the
  preflight step skip every GPU check, which is what makes that honest rather
  than merely quiet.
- The model environment needs **Python 3.11 exactly** — the kit's own
  requirement, and its lock is cp311.
- The weights ship **inside the stock clone** (6,681,301 bytes each for the
  vanilla and soluble sets), so there is no download step and nothing to accept
  terms for. `MPNN_DIR` names the clone.
- Keep provider data, weights, caches, and credentials outside Git.
- Bind to loopback. A non-loopback bind requires TOOLUNIVERSE_API_TOKEN; never
  put it in arguments or results.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation proteinmpnn
~~~

After exporting provider resources, add `--check-provider-env`. After the server
starts, add `--live` to verify the exact MCP tool set without running the model.
Before sharing, add `--check-connect-prereqs`; this reports only whether a key is
set and never prints its value.

## Create the two environments

This provider is on the remote-tool standard, so it has two environments: the
MCP server runs in ToolUniverse's, and the model runs in its own, built from a
pinned lock. They cannot import each other, and that is the point.

~~~bash
# the model's own environment, at the kit's pinned interpreter
uv venv --seed --managed-python --python 3.11.5 ~/proteinmpnn-venv
export TOOLUNIVERSE_PROTEINMPNN_PYTHON="$HOME/proteinmpnn-venv/bin/python"
export TOOLUNIVERSE_PROTEINMPNN_WEIGHTS="$HOME/ProteinMPNN"
~~~

Then run the five setup steps, one at a time so a failure is attributable:

~~~bash
for step in preflight environment kit weights smoke; do
  python -m tooluniverse.cli remote setup proteinmpnn --only "$step" || break
done
~~~

What each step does here:

| step | what it does | expected |
| --- | --- | --- |
| `preflight` | checks the declared prerequisites; no GPU checks | OK |
| `environment` | installs 17 pinned distributions into the venv | OK |
| `kit` | widens the shared kit checkout's sparse set to include `proteinmpnn`, installs `proteinmpnn_opt` + `opt_core` editable, then `run.sh install --weights` clones or hash-checks the stock repo | `WEIGHTS OK: 2/2 pinned files match stock/PINS.json` |
| `weights` | re-verifies both checkpoints against the manifest's digests | `2/2 entries at their pins` |
| `smoke` | 4 designs for a 40-residue backbone | one reply, sequences returned |

## The environment is a CPU stack, on purpose

`environment/requirements.lock` is the kit's own lock with **one** line
re-pointed and **fourteen** not installed, and its header states each with its
reason. The short version:

- The kit pins torch by direct URL to
  `torch-2.5.1+cu124-cp311-cp311-linux_x86_64.whl`, which cannot install on
  aarch64 at all — the platform tag, before any question about CUDA. PyPI's
  `torch==2.5.1` for cp311 aarch64 is the **same version** and is CPU-only.
- The twelve `nvidia-*-cu12` pins carry `platform_machine == "x86_64"` in
  torch's own metadata and a CPU torch loads none of them.
- `triton==3.1.0` publishes no aarch64 wheel at any version of the 3.x line. It
  is imported by the kit's `--fused_draw` lever only, which the kit itself
  switches off without a CUDA device.
- `gemmi==0.6.7` has no linux aarch64 wheel (the first are 0.7.3) and is **not
  installed and not substituted**. `git grep gemmi` over the whole kit at this
  commit matches the lock line and nothing else, so no path this provider runs
  needs it. If one is ever found, that comment is where to start.

A trap worth knowing: the kit's own `check` prints `gpu=NVIDIA GB10(sm_121)` on
this host. It reads the card through NVML (`nvidia-ml-py`, a pure-Python wheel
that installs anywhere) while torch cannot reach it. **A kit naming the card is
not a kit that can use it.**

## Start the server and call it

~~~bash
python -m tooluniverse.remote.proteinmpnn.proteinmpnn_tool
~~~

The worker starts on the first request and is retired after 900 s idle. A
documented example, run live:

~~~python
{
  "name": "proteinmpnn_design",
  "arguments": {
    "structure": "<the text of a PDB file>",
    "num_sequences": 8,
    "temperature": 0.1,
    "weight_set": "vanilla",
    "seed": 37
  }
}
~~~

The reply carries `sequences` (the designed sequences), `native_sequence` (the
structure's own), `native_score`, and `designs` — one record per design with its
temperature, sample number, `score`, `global_score` and `seq_recovery`. The
field names are the worker's; **read them from the worker rather than guessing**,
which is mistake 55 of the devtu-remote-provider skill and has cost three runs.

## Bounds, and what happens at them

Checked in the tool layer *and* in the worker, because a ceiling only the worker
knows is one a caller discovers by having a request fail after a minute:

| bound | value | why |
| --- | --- | --- |
| `num_sequences` | 1–128 | |
| `batch_size` | 1–`num_sequences`, and must divide it | upstream designs `num_sequences // batch_size` batches per temperature and **drops the remainder silently**, so a non-dividing pair is refused instead |
| `temperature` | (0, 1] | it divides the logits, so 0 is a division by zero |
| `seed` | ≥ 1 | the worker will not draw one: it is held across requests, so a drawn seed could not be reproduced by the caller |
| residues | ≤ 3000 | stock's dense featuriser builds `[B, L, K, 3H]` tensors for every position at once; the kit's `lowmem` transform lifts this and is a GPU line this provider declined |
| structure | ≤ 8 MB | keeps a megabyte out of the MCP transport |

The tool layer **returns** `{"error": ...}` rather than raising. Assert on the
refusal's content, never on the absence of an exception — mistake 56.

## Reproducing the equivalence gate

This is the check to re-run after any change to the worker. It compares against
the kit's own stock route, on the **same single structure**:

~~~bash
cd <the kit checkout>/proteinmpnn
bash run.sh design --mode off --input <dir with one pdb> --out /tmp/base \
  --seed 37 --num_seq_per_target 8 --batch_size 8
~~~

then send the same structure, seed, count and temperature to the provider and
compare every field of `/tmp/base/seqs/<name>.fa` against the reply.

**One structure, not the kit's two-monomer example.** Stock runs ONE RNG stream
across its whole dataset, so in the two-monomer example 5L33 is designed from a
generator already advanced by 6MRR's draws: its native score reads 1.5954 there
and 1.5840 alone. That is a different baseline, not a defect — and the kit's own
`--mode stream` exists to replay exactly that cross-structure offset. Comparing
a one-structure request against the two-structure run is how this looked like a
bug for ten minutes.

## What the Platform evidence covers, and what it does not

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform
at all: the evidence above is local, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation,
saturation, and persistent supervision are untested.

## Authorize once, then share with one short command

Run once per machine, and again after key rotation:

~~~bash
tu remote login
~~~

Then each private share is:

~~~bash
tu remote share proteinmpnn
~~~

Override the defaults only when needed:

~~~bash
tu remote share proteinmpnn --name my-proteinmpnn-remote --workers 1
~~~

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced.
Use `tu remote logout` to remove only the locally stored key.

## Check discovery and relay privately

~~~bash
tu doctor --forward http://127.0.0.1:8049/mcp --json
tu serve --share --forward http://127.0.0.1:8049/mcp --name validation-proteinmpnn --workers 1
~~~

## Run a verified example

The Streamable HTTP endpoint is http://127.0.0.1:8049/mcp. In a second
activated shell run:

Operation: proteinmpnn_design

~~~json
{"structure":"ATOM      1  N   MET A   1      27.340  24.430   2.614  1.00  0.00           N\n","num_sequences":4,"seed":37}
~~~

That one ATOM line shows the **shape of the request, not a request that
works**: a single atom is not a backbone and the tool refuses it. The
structure the equivalence gate actually ran -- the first 40 residues of chain A
of 5L33, the monomer the kit's own README designs with -- is 27 KB and lives in
`src/tooluniverse/remote/proteinmpnn/smoke/input.json`, with the seed, weight
set, temperature and batch size that were byte-compared against `run.sh design
--mode off`. The block below uses that file when it is present.

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
import pathlib
from fastmcp import Client

async def main():
    arguments = json.loads('''{"structure":"ATOM      1  N   MET A   1      27.340  24.430   2.614  1.00  0.00           N\n","num_sequences":4,"seed":37}''')
    smoke = pathlib.Path("src/tooluniverse/remote/proteinmpnn/smoke/input.json")
    if smoke.is_file():
        arguments = {
            key: value
            for key, value in json.loads(smoke.read_text()).items()
            if not key.startswith("_")
        }
    async with Client("http://127.0.0.1:8049/mcp") as client:
        result = await client.call_tool("proteinmpnn_design", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: structures (with native_sequence, native_score and a designs array), n_designs and timing_s. Check scientific meaning, finite values,
output bounds, invalid-input behaviour, and the absence of paths,
secrets and traces.

## Troubleshooting

| symptom | cause |
| --- | --- |
| `the kit's read-once parser is not at …` | the kit step has not run, or ran against a different checkout. `launch.py` refuses rather than falling back to the stock helper, because a provider that silently stops using a declared lever is mistake 12. |
| `the kit checkout is not at ~/.cache/tooluniverse/kits/…` | the kit was installed from your own clone rather than the standard's cache checkout. Run `remote setup proteinmpnn --only kit`. |
| `MPNN_DIR=… does not hold protein_mpnn_run.py` | `TOOLUNIVERSE_PROTEINMPNN_WEIGHTS` does not point at the stock clone. |
| worker exits 3 at `--mode exact` | correct: this provider declares `off` and holds stock's loop. The refusal names why. |
| the worker vanished after two minutes | the orphan watchdog: its parent died and it had been idle 120 s. By design — a worker must not outlive the server that owns it. |
| designs differ from a previous run | check the seed, and check you are comparing against a one-structure stock run (see above). |
