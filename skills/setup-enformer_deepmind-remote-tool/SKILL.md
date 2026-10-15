---
name: setup-enformer_deepmind-remote-tool
description: Set up, launch, validate, and troubleshoot the official DeepMind Enformer (TF-Hub SavedModel) genomic track prediction ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up the official DeepMind Enformer as a remote tool

> Validation status (2026-10-14): the official TF-Hub SavedModel
> `deepmind/enformer/1` ran on the NVIDIA GB10 host (aarch64, 20 cores,
> 121.6 GiB unified memory, cc 12.1, driver 580.173.02) **on the CPU**, under kit
> mode `off`. **This provider's lock has no deviation at all, a first on this
> standard:** 41 of the kit's 53 pins are installed at exactly their pinned
> version, and the other 12 are `nvidia-*-cu12` CUDA runtime wheels that a CPU
> TensorFlow loads none of. All three weight files match the kit's
> `stock/PINS.json` by size and sha256. **`[gpu] policy = "none"` is a
> measurement, not a preference:** `tf.test.is_built_with_cuda()` is False and
> `tf.config.list_physical_devices('GPU')` is empty, because TensorFlow
> publishes no GPU-capable aarch64 wheel at any version. One 393,216-base window
> costs ~200 s, and **residency buys almost nothing** — two consecutive
> predictions of the same window measured 194.1 s then 205.8 s, so there is no
> graph tracing to amortise. `provider.toml`'s header has the numbers and says
> what residency is actually for here. Cross-implementation agreement with the
> `enformer` port at 8011 has **not** been measured. Public publication,
> cross-user isolation, concurrency and recovery are untested; keep this
> deployment private.

## What this provider is for

Enformer predicts thousands of genomic tracks — CAGE, DNase, ATAC, ChIP — from
DNA sequence alone, integrating regulatory signal over ~100 kb. This provider
serves **the authors' own artifact**: the TF-Hub SavedModel they exported, pinned
by digest.

One sibling overlaps and the distinction is the whole reason both exist:

- **enformer** (port 8011) is `enformer-pytorch`, a community port whose weights
  were converted from the authors' release, running on the GPU with a 4.12 GiB
  budget. It is faster and it is what you want for throughput.
- **enformer_deepmind** (this one, port 8060) is the official TensorFlow
  SavedModel on the CPU. A converted checkpoint under another framework's
  kernels does not agree to the last float, so **published Enformer numbers
  reproduce against this one**.

They are complements, not alternatives: this one reserves no VRAM, so both can
be resident at once.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- **No GPU is required, and none can be used.** `[gpu] policy = "none"` makes
  the preflight skip every GPU check, which is honest here rather than a
  shortcut: there is no CUDA code in an aarch64 TensorFlow wheel to reach a card
  with.
- About 1.0 GiB of disk for the SavedModel and ~600 MB for the environment.
- Python **3.11** for the model environment (the kit's `python` pin).

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation enformer_deepmind
~~~

After exporting provider resources, add `--check-provider-env`. After the server
starts, add `--live` to verify the exact MCP tool set without running the model.

## Create the environment

```bash
uv venv --seed --managed-python --python 3.11 ~/enformer-dm-venv
~/enformer-dm-venv/bin/pip install --no-deps -r \
  src/tooluniverse/remote/enformer_deepmind/environment/requirements.lock
export TOOLUNIVERSE_ENFORMER_DEEPMIND_PYTHON=~/enformer-dm-venv/bin/python
```

Then the kit, which supplies the mode machinery even though the mode is `off`:

```bash
tu remote setup enformer_deepmind --only kit
```

## One thing the index cannot tell you

This stack is the reason to check what a wheel *contains*, not that it exists.
At `tensorflow==2.15.1` the aarch64 wheel on PyPI carries **no code**: a RECORD
of six dist-info lines, and

```
Requires-Dist: tensorflow-cpu-aws ==2.15.1 ; platform_system == "Linux" and (platform_machine == "aarch64")
```

hands the real library to a different distribution of the same version. Install
that with `--no-deps` and `pip list` shows `tensorflow 2.15.1` while
`import tensorflow` raises `ModuleNotFoundError`. At **2.17.1**, pinned here,
the aarch64 wheel is the real library (13,509 RECORD lines) and installs as
pinned — which is why this provider needs no deviation and its TensorFlow 2.15
sibling (`borzoi`) does.

## Fetch and verify the weights

```bash
tu remote setup enformer_deepmind --only weights
```

That fills tensorflow-hub's own cache layout under `TFHUB_CACHE_DIR`:

```
$TFHUB_CACHE_DIR/c444fdff3e183daf686869692c26e00391f6773c/
    saved_model.pb                              2,310,075 B
    variables/variables.data-00000-of-00001 1,005,172,750 B
    variables/variables.index                       5,893 B
```

All three are declared in `provider.toml` with a size and a sha256 and verified
before the worker starts. **The worker refuses to start when
`TFHUB_CACHE_DIR` is unset** rather than silently reaching the network — a
provider that fetches at request time is a provider whose weights nobody pinned.

## Start the server and call it

```bash
export TFHUB_CACHE_DIR=~/enformer-dm-weights
python -m tooluniverse.remote.enformer_deepmind.enformer_deepmind_tool
```

```bash
tu doctor --forward http://127.0.0.1:8060/mcp --json
```

A request is a DNA string. It is centre-cropped or N-padded to 393,216 bases, of
which the network reads the central 196,608 — **so the cost does not depend on
the length you send**: an 8 kb sequence costs the same ~200 s as a 393 kb one.
Send the window you mean.

The reply carries `centre` (the centre-bin value across every track of the
chosen head: 5,313 human, 1,643 mouse) and `profiles` (the full 896-bin profile
of any track named). `centre` is deliberately the same key the port at 8011
answers with, so the two implementations can be compared field for field.

## Bounds, and what happens at them

| bound | value | at the bound |
| --- | --- | --- |
| sequence length | 786,432 (2x the input length) | refused with the ceiling named; anything past 393,216 is centre-cropped anyway |
| letters | A, C, G, T, N | anything else refused by name; N becomes an all-zero column, as upstream's notebook feeds it |
| `organism` | `human` or `mouse` | refused with both named |
| `tracks` | at most 32 profiles | refused with the count; each profile is 896 floats travelling as JSON |
| concurrency | one request at a time | a second request queues on the worker's lock |

Every bound is checked in the tool **and** in the worker. A ceiling only the
worker knows is a ceiling a caller discovers by having a request fail after
three minutes of work.

## Why the kit is off

`opt/enformer_deepmind_opt/ops/edm_ops.so` has ELF `e_machine` 0x3e — x86-64 —
and the repository ships no aarch64 build of it, as for all eight kits that
carry prebuilt host objects. The levers behind it are CUDA kernels, which a
CPU-only TensorFlow could not reach even with an aarch64 build. The kit says so
itself without being asked:

```
$ PYTHON=~/enformer-dm-venv/bin/python bash run.sh check
[enformer-deepmind-opt] NOT ACTIVE mode=exact reason=no CUDA device visible (tf.config.list_physical_devices('GPU') is empty)
```

exit 3. On x86-64 with a CUDA TensorFlow, set `[kit] mode = "exact"` and its
fourteen levers engage; `tu remote setup` refuses the mismatch by name before
installing.

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
tu remote share enformer_deepmind
~~~

Override the defaults only when needed:

~~~bash
tu remote share enformer_deepmind --name my-enformer-deepmind-remote --workers 1
~~~

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced.
Use `tu remote logout` to remove only the locally stored key.

## Check discovery and relay privately

~~~bash
tu doctor --forward http://127.0.0.1:8060/mcp --json
tu serve --share --forward http://127.0.0.1:8060/mcp --name validation-enformer-deepmind --workers 1
~~~

## Run a verified example

The Streamable HTTP endpoint is http://127.0.0.1:8060/mcp. In a second
activated shell run:

Operation: run_enformer_deepmind_predict

~~~json
{"sequence":"ACGTACGT","organism":"human","tracks":[0,4100]}
~~~

That eight-base request is a **plumbing check, not a result**: anything shorter
than 393,216 bases is N-padded, so the model sees almost nothing but zero
columns and the numbers it returns mean nothing. It costs the same three
minutes as a real window. The sequence the acceptance runs used -- and the one
whose `sum(centre)` of 4606.426440 reproduced across two requests -- is
`src/tooluniverse/remote/enformer_deepmind/smoke/input.txt`, which is too long
to inline; the block below reads it when it is there and falls back to the
short request when it is not.

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
import pathlib
from fastmcp import Client

async def main():
    arguments = json.loads('''{"sequence":"ACGTACGT","organism":"human","tracks":[0,4100]}''')
    smoke = pathlib.Path(
        "src/tooluniverse/remote/enformer_deepmind/smoke/input.txt"
    )
    if smoke.is_file():
        arguments["sequence"] = smoke.read_text().strip()
    async with Client("http://127.0.0.1:8060/mcp") as client:
        result = await client.call_tool("run_enformer_deepmind_predict", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: implementation, organism, n_bins 896, n_tracks 5313, a bounded centre array and timing. Check scientific meaning, finite values,
output bounds, invalid-input behaviour, and the absence of paths,
secrets and traces.

## Troubleshooting

- **`import tensorflow` fails after a clean install.** You installed
  `tensorflow==2.15.1` or another version whose aarch64 wheel is a shim. See
  "One thing the index cannot tell you" above; this provider pins 2.17.1, whose
  aarch64 wheel is the real library.
- **The worker exits 3 naming `TFHUB_CACHE_DIR`.** It is unset. Set it to the
  directory `--only weights` filled; the worker never fetches.
- **`hub.load` tries to reach the network.** The pinned cache key
  `c444fdff3e183daf686869692c26e00391f6773c` is missing from
  `$TFHUB_CACHE_DIR`. Re-run `--only weights`.
- **A request takes three minutes and you expected seconds.** That is this
  provider: CPU-only, and the second call is not faster than the first. Use
  `run_enformer_predict` at 8011 for throughput.
