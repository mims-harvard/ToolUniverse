# Borzoi (calico release) variant-scoring remote tool

## TOU validation and deployment status (2026-08-16)

> calico's own `borzoi_sad.py` at commit `5c93582` on `baskerville` at
> `544073b`, fold 0, reverse-complement ensemble, held resident **on the CPU** of
> an NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02), under kit mode `off`.
> **Read five notes before deploying.** (1) **The equivalence gate is the
> provider:** the worker holds the model but reimplements nothing numeric — it
> imports stock's own `initialize_output_h5`, `write_snp_len` and `write_pct`
> out of `borzoi_sad` and calls `baskerville`'s own `snp_seq1`,
> `untransform_preds` and `seqnn` model in stock's own order, then writes the
> same `sad.h5`. **It passed:** compared against a stock `run.sh sad --mode off`
> run dataset by dataset — the right test rather than a byte diff, since HDF5
> allocation order and the kit's chunked writer differ legitimately — **all 16
> datasets are identical**, and the worker's two requests agreed to the last
> float. The gate has teeth, which was shown rather than asserted: an earlier
> draft misread the pinned `-u` (declared `dest='untransform_old'`) and called
> `untransform_preds` instead of `untransform_preds1`. That worker started, was
> deterministic across two requests, returned the pinned shapes and the right
> `target_ids`, and reported a plausible `max|SAD|` of 9.34 — while **every one
> of its eight score datasets was wrong** (SAD: 1809 of 6385 values, max
> |delta| 34.66) and the top-ranked track was a different track altogether. A
> provider can be deterministic, correctly shaped, correctly labelled and
> completely wrong in its numbers.
> (2) **This kit's `exact` mode is the first on this standard that actually runs
> here** — it ships no prebuilt host objects at all and its levers are Python
> data-path rewrites, not CUDA kernels — and it is byte-identical to stock across
> three pairs of runs, all 16 datasets. It is still set to `off`, because
> **no speed advantage could be established on this host**: the within-mode
> spread (33 s) exceeded the between-mode difference (14.6 s) and the host's load
> climbed monotonically through the measurement. `provider.toml`'s `[kit]`
> section has every number. (3) **`[gpu] policy = "none"` is a measurement:**
> TensorFlow publishes no GPU-capable aarch64 wheel at any version, so
> `is_built_with_cuda()` is False on a card torch drives in the same session. The
> upside is composition — no VRAM at all, ~10 GiB of host RSS, so variant scoring
> runs while a folding model owns the GPU. (4) **The weights directory must be
> writable**, unlike every other provider here: `pysam.Fastafile` builds
> `hg38.ml.fa.fai` beside the genome on first use. `launch.py` refuses by name
> rather than letting the worker die inside pysam. (5) **This is not a
> replacement for `run_borzoi_variant_effect`** at port 8012, and it is not even
> the same operation — see below. Public publication, cross-user isolation,
> concurrency, recovery and indels are unvalidated; keep this deployment private.

- Operation: `run_borzoi_calico_sad`
- Start: `python -m tooluniverse.remote.borzoi_calico.borzoi_calico_tool`
- Endpoint: `http://127.0.0.1:8061/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights are
  declared with a size and a sha256 and verified before the worker starts. Keep
  provider data, weights, caches and credentials outside Git. Use one worker: the
  resident worker serves one request at a time by design.
- TOU check: `tu doctor --forward http://127.0.0.1:8061/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8061/mcp --name validation-borzoi-calico --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation borzoi_calico`. Add `--check-provider-env` before launch,
`--live` after launch, and `--check-connect-prereqs` before sharing.

## Not the same operation as the sibling at 8012

| | `run_borzoi_variant_effect` (8012) | `run_borzoi_calico_sad` (this one) |
| --- | --- | --- |
| implementation | `borzoi-pytorch`, a community port | calico's `borzoi_sad.py` @ `5c93582` |
| input | two DNA sequences | variants against **pinned hg38** |
| what it computes | ref-vs-alt delta at the central bin | upstream's **SAD, logSAD, D2, logD2** |
| tracks | the port's heads | **6,385**, strand-summed from 7,611 |
| untransform | none | upstream's targets table (`-u`) |
| ensemble | none | reverse complement (`--rc`) |
| device | GPU | CPU only here |
| cost | seconds | ~255 s per variant |

The right reason to reach for this one is that the Borzoi paper's numbers are
SAD over the strand-summed, untransformed, RC-averaged tracks, and that is what
it returns. The right reason to reach for the other is throughput.

## What a caller sends and gets

```json
{"variants": [{"chrom": "chr1", "pos": 43110773, "ref": "G", "alt": "A"}],
 "top_tracks": 20}
```

SNVs only, at most four per request (≈17 minutes). Coordinates are GRCh38,
1-based, as in a VCF; a bare `1` is accepted and normalised to `chr1` in both
the tool and the worker, because `baskerville.vcf.SNP` prepends the prefix
itself and two callers who disagreed about it would otherwise get rows that look
like different variants.

The reply names the strongest tracks per variant by |SAD|, each with all four
statistics and upstream's own identifier and description, plus `max_abs_SAD`.
The full 6,385-track vectors stay in the provider's `sad.h5`, whose path the
reply carries.

## One thing the index cannot tell you

The kit pins `tensorflow==2.15.1`, and **on aarch64 that wheel carries no
code**: a RECORD of six dist-info lines and a
`Requires-Dist: tensorflow-cpu-aws ==2.15.1 ; platform_machine == "aarch64"`
that hands the real library to another distribution of the same version.
Installed with `--no-deps` the redirect is never followed, so `pip list` shows
`tensorflow 2.15.1` and `import tensorflow` raises. This provider's lock keeps
the pin and adds `tensorflow-cpu-aws==2.15.1` beside it. Its TensorFlow 2.17.1
sibling, `enformer_deepmind`, needs no such line.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it has
not been exercised through the Platform at all, and everything above was
measured locally, on one card, through the loopback endpoint. Public
publication, independent-caller authorization/isolation, broad saturation and
persistent supervision are unvalidated here.

See the [complete setup and verification guide](../../../../skills/setup-borzoi_calico-remote-tool/SKILL.md).

## Authorize once, then share with one short command

Run once per machine, and again after key rotation:

```bash
tu remote login
```

Then each private share is:

```bash
tu remote share borzoi_calico
```

Override the defaults only when needed:

```bash
tu remote share borzoi_calico --name my-borzoi-calico-remote --workers 1
```

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced;
unset or correct it, then run `tu remote login`. Non-interactive jobs also
fail fast. Use `tu remote logout` to remove only the locally stored key.
