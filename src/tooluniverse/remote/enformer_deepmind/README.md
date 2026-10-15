# Enformer (official DeepMind release) remote tool

## TOU validation and deployment status (2026-08-16)

> The **official** Enformer artifact — the TF-Hub SavedModel
> `deepmind/enformer/1` — held resident **on the CPU** of an NVIDIA GB10
> (aarch64, cc 12.1, driver 580.173.02), under kit mode `off`. **This provider's
> lock has no deviation, which is a first on this standard:** 41 of the kit's 53
> pins are installed at exactly their pinned version and the other 12 are the
> `nvidia-*-cu12` CUDA runtime wheels that a CPU TensorFlow loads none of. The
> three weight files are verified against the kit's `stock/PINS.json` by size
> and sha256 before the worker starts, and all three match. **Read four notes
> before deploying.** (1) **Residency buys almost nothing here and the provider
> says so:** two consecutive predictions of the same window cost 194.1 s then
> 205.8 s — the second is *not* faster, so there is no graph tracing to
> amortise, and the model load is 2.7 s warm against a ~200 s request. What it
> is resident *for* is the separation (TensorFlow 2.17.1 holds numpy to 1.26.4
> and cannot be installed beside ToolUniverse's stack), the pinned-weights
> verification, and the shared lifecycle. (2) **`[gpu] policy = "none"` is a
> measurement:** `tf.test.is_built_with_cuda()` is False and
> `list_physical_devices('GPU')` is empty, because TensorFlow publishes no
> GPU-capable aarch64 wheel at any version — the same shape as the torch floor
> below 2.7, one framework over. The upside is real: this model reserves no VRAM,
> so it is admitted and resident while the card is full. (3) The kit's `exact`
> mode is declined for a reason read off a file rather than guessed —
> `opt/enformer_deepmind_opt/ops/edm_ops.so` has ELF `e_machine` 0x3e (x86-64),
> and the kit's own dry run says `NOT ACTIVE mode=exact reason=no CUDA device
> visible`. (4) **This is not a replacement for `run_enformer_predict`** at port
> 8011; it is its complement. That one is `enformer-pytorch`, a community port
> on converted weights, running on the GPU. Use this one when published Enformer
> numbers must reproduce against the authors' own artifact. Cross-implementation
> agreement between the two has **not** been measured; both ship the same smoke
> sequence so that it can be. Public publication, cross-user isolation,
> concurrency and recovery are unvalidated; keep this deployment private.

- Operation: `run_enformer_deepmind_predict`
- Start: `python -m tooluniverse.remote.enformer_deepmind.enformer_deepmind_tool`
- Endpoint: `http://127.0.0.1:8060/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  The SavedModel lives in tensorflow-hub's own cache layout under
  `TFHUB_CACHE_DIR`; the worker **refuses to start** if that variable is unset
  rather than silently reaching the network. Keep provider data, weights, caches
  and credentials outside Git. Use one worker: the resident worker serves one
  request at a time by design, and a second in-flight request queues on its lock.
- TOU check: `tu doctor --forward http://127.0.0.1:8060/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8060/mcp --name validation-enformer-deepmind --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation enformer_deepmind`. Add `--check-provider-env` before launch,
`--live` after launch, and `--check-connect-prereqs` before sharing. Live
preflight checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it has
not been exercised through the Platform at all, and everything above was
measured locally, on one card, through the loopback endpoint. Public
publication, independent-caller authorization/isolation, broad saturation and
persistent supervision are unvalidated here.

See the [complete setup and verification guide](../../../../skills/setup-enformer_deepmind-remote-tool/SKILL.md).

## Authorize once, then share with one short command

Run once per machine, and again after key rotation:

```bash
tu remote login
```

Then each private share is:

```bash
tu remote share enformer_deepmind
```

Override the defaults only when needed:

```bash
tu remote share enformer_deepmind --name my-enformer-deepmind-remote --workers 1
```

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced;
unset or correct it, then run `tu remote login`. Non-interactive jobs also
fail fast. Use `tu remote logout` to remove only the locally stored key.

## What a caller sends and gets

One window, one reply. The request is a DNA string; it is centre-cropped or
N-padded to 393,216 bases, of which the network reads the central 196,608 —
so **the cost does not depend on the length sent**, and a 8 kb sequence costs
the same ~200 s as a 393 kb one.

The reply carries `centre`, the centre-bin value across every track of the
chosen head (5,313 human, 1,643 mouse), and `profiles`, the full 896-bin
profile of any track named (at most 32; each is 896 floats travelling as JSON).
`centre` is deliberately the same key the port at 8011 answers with.

## One thing the index cannot tell you

At `tensorflow==2.15.1` the aarch64 wheel on PyPI **carries no code**: its
RECORD is six lines of dist-info, and a
`Requires-Dist: tensorflow-cpu-aws ==2.15.1 ; platform_machine == "aarch64"`
hands the real library to another distribution of the same version. Installed
with `--no-deps`, that redirect is never followed: `pip list` then shows
`tensorflow 2.15.1` and `import tensorflow` fails. At **2.17.1**, the version
pinned here, the aarch64 wheel is the real library (13,509 RECORD lines) and is
installed as pinned. Check what a wheel contains, not that it exists.
