# ProteinMPNN remote tool

## TOU validation and deployment status (2026-08-16)

> ProteinMPNN / SolubleMPNN at stock commit `8907e667` ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) **on the CPU**, holding stock's own design loop, under kit mode `off` with one lever kept (`fast_parse`). **`[gpu] policy = "none"` and no `vram_budget_gb`, which is the point of this provider and not a limitation of it:** `admission.py` skips a provider with no declared budget, so this one is admitted while the card is full and can be resident alongside every folding model on the box. Its central claim is EQUIVALENCE, not speed, and it was checked rather than argued: the acceptance suite byte-compares the worker's reply against `run.sh design --mode off` across five cases — two backbones, two seeds, two temperatures, two batch layouts and both weight sets, 36 designs — comparing every field stock writes, and every field was identical. **Read three notes before deploying.** (1) The kit's optimised `exact` line also runs on this CPU host and is also byte-identical there; it was declined on the clock, 38.53 s of generation against stock's 30.45 s, because every lever that survives a CPU host is a way of filling a GPU. (2) Building this provider found a real bug in the admission gate: a CPU provider's absent budget was read as UNKNOWN rather than zero, so a held worker refused every GPU provider on the host — exactly inverted. Fixed, with tests, and verified live. (3) **The owed quiet-host pair is paid and it halved the number.** The first runs happened while another session held the host at 681 % CPU and load 20.6 on 20 cores. Re-measured at load 3.25, same request: stock 15.22 and 14.40 s generation against 22.05 and 20.66 s wall, resident 18.3 and 19.2 s design against 18.4 and 19.5 s wall. Both contended figures were ~2.4x inflated and the real wall ratio is **1.13x**, not the 1.4x recorded as the expectation -- because residency saves a constant ~3 s, which reads as 1.40x against a contended 42.8 s baseline and 1.13x against a true 21 s one. Public publication, cross-user isolation, concurrency, recovery, backbones above 400 residues, multi-chain complexes and design quality are unvalidated; keep this deployment private.

- Operation: `proteinmpnn_design`
- Start: `python -m tooluniverse.remote.proteinmpnn.proteinmpnn_tool`
- Endpoint: `http://127.0.0.1:8049/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Its weights ship **inside the stock clone** — a first for this standard —
  so there is no download and nothing to accept terms for; `MPNN_DIR` names the
  clone. Keep provider data, weights, caches and credentials outside Git. Use
  one worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock.
- TOU check: `tu doctor --forward http://127.0.0.1:8049/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8049/mcp --name validation-proteinmpnn --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation proteinmpnn`. Add `--check-provider-env` before launch,
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

See the [complete setup and verification guide](../../../../skills/setup-proteinmpnn-remote-tool/SKILL.md).

## Authorize once, then share with one short command

Run once per machine, and again after key rotation:

```bash
tu remote login
```

Then each private share is:

```bash
tu remote share proteinmpnn
```

Override the defaults only when needed:

```bash
tu remote share proteinmpnn --name my-proteinmpnn-remote --workers 1
```

Sharing automatically starts the browser flow when the key is missing,
expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast instead of being silently replaced;
unset or correct it, then run `tu remote login`. Non-interactive jobs also
fail fast. Use `tu remote logout` to remove only the locally stored key.

## Where this sits among the siblings

Inverse folding — a backbone in, sequences out — is what you run between a
backbone generator and a structure predictor that checks the design folds back.

| provider | model | device | budget |
| --- | --- | --- | --- |
| `proteinmpnn` | ProteinMPNN / SolubleMPNN, 1.66M params | CPU | none |
| `esm_if1` | ESM-IF1 GVP-Transformer, 142M params | CPU | none |
| `ef2inv` | binder design by descent through a folding model | GPU | 28.03 GiB |

The first two are different priors over the same task and cost no card memory.
`ef2inv` is a different task that happens to produce a sequence.

## Setup

Five steps, run one at a time so a failure is attributable:

~~~bash
uv venv --seed --managed-python --python 3.11.5 ~/proteinmpnn-venv
export TOOLUNIVERSE_PROTEINMPNN_PYTHON="$HOME/proteinmpnn-venv/bin/python"
export TOOLUNIVERSE_PROTEINMPNN_WEIGHTS="$HOME/ProteinMPNN"
for step in preflight environment kit weights smoke; do
  python -m tooluniverse.cli remote setup proteinmpnn --only "$step" || break
done
~~~

`skills/setup-proteinmpnn-remote-tool/SKILL.md` has the long form, the bounds
table, and how to re-run the equivalence gate after a change to the worker.
