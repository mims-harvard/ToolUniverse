---
name: setup-borzoi_calico-remote-tool
description: Set up, launch, validate, and troubleshoot the calico/borzoi variant-scoring (SAD/logSAD/D2/logD2) ToolUniverse remote tool and optionally relay it through ToolUniverse Connect. Use when deploying or auditing this implementation.
---

# Set up calico's Borzoi variant scoring as a remote tool

> Validation status (2026-10-14): calico's own `borzoi_sad.py` at `5c93582` on
> `baskerville` at `544073b`, fold 0, reverse-complement ensemble, ran on the
> NVIDIA GB10 host (aarch64, 20 cores, 121.6 GiB unified, cc 12.1, driver
> 580.173.02) **on the CPU**, under kit mode `off`. The worker holds the model
> but **reimplements nothing numeric**: it imports stock's own
> `initialize_output_h5`, `write_snp_len` and `write_pct` out of `borzoi_sad`
> and calls `baskerville`'s own `snp_seq1`, `untransform_preds` and `seqnn`
> model in stock's order, then writes the same `sad.h5`. **This kit's `exact`
> mode is the first on this standard that actually runs on this host** — it
> ships no prebuilt host objects and its levers are Python data-path rewrites,
> not CUDA kernels — and it is byte-identical to stock across three pairs, all 16
> datasets; it is still set to `off` because no speed advantage could be
> established here (within-mode spread 33 s against a between-mode difference of
> 14.6 s, on a host whose load climbed through the measurement).
> `provider.toml`'s `[kit]` section carries every number. **`[gpu] policy =
> "none"` is a measurement:** TensorFlow publishes no GPU-capable aarch64 wheel
> at any version. About 255 s per variant; four variants maximum. Public
> publication, cross-user isolation, concurrency, recovery and indels are
> untested; keep this deployment private.

## What this provider is for, and what it is not

Regulatory variant scoring the way the Borzoi paper reports it: each variant's
reference and alternate 524,288-base windows through the fold-0 network under a
reverse-complement ensemble, untransformed with upstream's targets table,
strand-summed from 7,611 tracks down to 6,385, scored as **SAD, logSAD, D2,
logD2**.

**It is not the same operation as `run_borzoi_variant_effect` at port 8012**,
which is `borzoi-pytorch` — a community port — taking two sequences and
returning a central-bin delta on the GPU in seconds. Reach for that one for
throughput, and for this one when the paper's statistics are what you need.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.3.
- **No GPU is required and none can be used** on aarch64.
- Python **3.10** for the model environment (the kit's `python` pin).
- About **3.9 GiB** of weights and genome, plus ~1 GiB of environment, in a
  directory that must be **writable** — see below.
- ~10 GiB of free RAM per request. Peak RSS measured 10,011,120 KB.

Run the standard-library contract check before downloading large dependencies:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation borzoi_calico
~~~

After exporting provider resources, add `--check-provider-env`. After the server
starts, add `--live` to verify the exact MCP tool set without running the model.

## The weights directory must be writable

Unlike every other provider on this standard, a read-only weights mount does not
serve this one: `pysam.Fastafile` builds `hg38.ml.fa.fai` **beside the genome**
the first time it opens it (`borzoi_sad.py:246`). `launch.py` checks
`os.access(root, os.W_OK)` and refuses by name, rather than letting the worker
die inside pysam with an errno nobody will connect to the mount.

## Create the environment

```bash
uv venv --seed --managed-python --python 3.10 ~/borzoi-kit-venv
~/borzoi-kit-venv/bin/pip install --no-deps -r \
  src/tooluniverse/remote/borzoi_calico/environment/requirements.lock
export TOOLUNIVERSE_BORZOI_CALICO_PYTHON=~/borzoi-kit-venv/bin/python
```

Then the two upstream checkouts, which the kit ships as archives so nothing is
cloned at setup time (`stock/borzoi-5c93582.tar.gz`,
`stock/baskerville-544073b.tar.gz`; an archive install has no `.git`, so
setuptools_scm needs the version handed to it):

```bash
SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BASKERVILLE=1.0.0 \
  ~/borzoi-kit-venv/bin/pip install --no-deps -e <baskerville checkout>
SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BORZOI=1.0.1 \
  ~/borzoi-kit-venv/bin/pip install --no-deps -e <borzoi checkout>
export BORZOI_DIR=<borzoi checkout> BASKERVILLE_DIR=<baskerville checkout>
```

`launch.py` puts `$BORZOI_DIR/src/scripts` on the worker's `PYTHONPATH`, which
is how upstream's own image makes `borzoi_sad` importable — and the worker
**refuses to start** if it is not importable, rather than reimplementing its
writer.

## One thing the index cannot tell you, and it bites this stack

The kit pins `tensorflow==2.15.1`. **On aarch64 that wheel carries no code:** its
RECORD is six dist-info lines, and

```
Requires-Dist: tensorflow-cpu-aws ==2.15.1 ; platform_system == "Linux" and (platform_machine == "aarch64")
```

hands the real library to a different distribution of the same version. With
`--no-deps` that redirect is never followed, so `pip list` shows
`tensorflow 2.15.1` while `import tensorflow` raises `ModuleNotFoundError`. The
lock therefore keeps the pin **and** adds `tensorflow-cpu-aws==2.15.1` beside
it. Check what a wheel contains, not that it exists.

## Fetch and verify the weights

```bash
tu remote setup borzoi_calico --only weights
```

Two files, both declared with a size and a sha256 in `provider.toml` and
verified before the worker starts:

| file | bytes |
| --- | --- |
| `f0/model0_best.h5` | 744,112,468 |
| `hg38.ml.fa` | 3,091,663,428 |

The genome is **not** the README's UCSC `hg38.fa`: upstream's
`download_models.sh:63-67` fetches `hg38.ml.fa.gz` from its own bucket, and that
is what `-f` defaults to. Contig names must carry the `chr` prefix.

## Start the server and call it

```bash
python -m tooluniverse.remote.borzoi_calico.borzoi_calico_tool
tu doctor --forward http://127.0.0.1:8061/mcp --json
```

```json
{"variants": [{"chrom": "chr1", "pos": 43110773, "ref": "G", "alt": "A"}],
 "top_tracks": 20}
```

SNVs only, GRCh38, 1-based. A bare `1` is normalised to `chr1` in **both** the
tool and the worker — `baskerville.vcf.SNP` prepends the prefix itself
(`vcf.py:672-675`), so two callers who disagreed about it would otherwise get
rows that look like different variants.

## Bounds, and what happens at them

| bound | value | at the bound |
| --- | --- | --- |
| `variants` | at most 4 | refused with the count and the per-variant cost named |
| alleles | ACGT, SNVs only | refused by name; indels are not scored |
| `pos` | integer ≥ 1 | refused by name |
| `top_tracks` | 1–100 | refused; the full 6,385-track vectors stay in `sad.h5` |
| concurrency | one request at a time | a second request queues on the worker's lock |

## Reproducing the equivalence gate

```bash
# stock, through the kit's own entry point
cd <kit>/borzoi
PATH=~/borzoi-kit-venv/bin:$BORZOI_DIR/src/scripts:$PATH \
  bash run.sh sad --mode off -f <weights>/hg38.ml.fa -o /tmp/off \
  --rc --stats SAD,logSAD,D2,logD2 -t $BORZOI_DIR/examples/targets_human.txt -u \
  $BORZOI_DIR/examples/params.json <weights>/f0/model0_best.h5 one.vcf
```

Then the same variant through the worker, and compare **dataset by dataset** —
not as bytes. HDF5 allocation order and the kit's chunked writer differ
legitimately between two runs that agree on every number, so a byte diff
produces a false negative. Compare each dataset's name, shape, dtype and values
exactly: `SAD`, `logSAD`, `D2`, `logD2` at `(n, 6385)` float16, their four
`(6385, 279)` percentile tables, and `snp`, `chr`, `pos`, `ref_allele`,
`alt_allele`, `percentiles`, `target_ids`, `target_labels`.

## Two upstream details this provider preserves on purpose

**Stock's `sum_length` branch is dead.** `borzoi_sad.py:159` splits `--stats`
into a list; `:210` then tests `sum_length = (options.sad_stats == 'SAD')`, a
list against a string, which is always False. So upstream never calls
`build_sad()` and always writes with `write_snp_len`, for every `--stats` value
including `--stats SAD` alone. The worker reproduces that rather than correcting
it, because its whole claim is that it answers what stock answers.

**`--shifts` is a list by the time it reaches baskerville.** `:158` converts it,
and `seqnn.build_ensemble` takes `len()` of it. Passing the bare int raises —
which is the good case: a signature that accepted it would have scored every
variant without the reverse-complement average the pinned command asks for.

Neither of these was caught by comparing outputs. The first is invisible to the
gate because the pinned stats make the bug and a "fixed" version agree; the
second failed loudly. **Read the stock script; do not infer it from its own
output.**

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
tu remote share borzoi_calico
~~~

Override the defaults only when needed:

~~~bash
tu remote share borzoi_calico --name my-borzoi-calico-remote --workers 1
~~~

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced.
Use `tu remote logout` to remove only the locally stored key.

## Check discovery and relay privately

~~~bash
tu doctor --forward http://127.0.0.1:8061/mcp --json
tu serve --share --forward http://127.0.0.1:8061/mcp --name validation-borzoi-calico --workers 1
~~~

## Run a verified example

The Streamable HTTP endpoint is http://127.0.0.1:8061/mcp. In a second
activated shell run:

Operation: run_borzoi_calico_sad

~~~json
{"variants":[{"chrom":"chr1","pos":43110773,"ref":"G","alt":"A"}],"top_tracks":5}
~~~

Invoke the example through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads('''{"variants":[{"chrom":"chr1","pos":43110773,"ref":"G","alt":"A"}],"top_tracks":5}''')
    async with Client("http://127.0.0.1:8061/mcp") as client:
        result = await client.call_tool("run_borzoi_calico_sad", arguments)
        print(result)

asyncio.run(main())
PY
~~~

Expected success shape: implementation, n_variants, n_tracks 6385, stats, a variants array whose top_tracks carry all four statistics, and sad_h5. Check scientific meaning, finite values,
output bounds, invalid-input behaviour, and the absence of paths,
secrets and traces.

## Troubleshooting

- **`import tensorflow` fails after a clean install.** The aarch64
  `tensorflow==2.15.1` wheel is a shim; install `tensorflow-cpu-aws==2.15.1`
  (the lock already does).
- **The worker refuses naming `BORZOI_DIR` or `borzoi_sad.py`.** The checkout is
  missing or `src/scripts` is not where it expects. The worker imports stock's
  writer and will not proceed without it.
- **The worker refuses naming a non-writable weights directory.** pysam needs to
  write the `.fai` beside the genome.
- **`Unable to synchronously create dataset (name already exists)`.** Something
  passed the comma-joined `--stats` **string** where stock's helpers expect the
  split **list**: `for sad_stat in sad_stats` then iterates characters and dies
  on the second `S`.
- **A request takes twenty minutes.** Four variants at ~255 s each, on the CPU.
  That is this provider.
