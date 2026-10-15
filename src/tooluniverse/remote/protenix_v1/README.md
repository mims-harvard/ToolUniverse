# Protenix v1 remote tool

## TOU validation and deployment status (2026-08-16)

> Protenix 1.1.0 (ByteDance's AlphaFold3 reproduction) ran on the NVIDIA GB10 (aarch64, cc 12.1) with the optimization kit **OFF** — its one prebuilt object is x86-64 and `kit_foreign_objects` refuses per directory, so the kit mode is unreachable here. Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS plus a mixed-shape sequence and an ascending ladder: 4.4-5.1 s per 35-residue fold, peak reserved ~1.9 GiB at 100 residues rising to 9.65 at 800 — about 5.1x, the same shape protenix_v1 measures (5.3x) for the same architecture through a different reimplementation. **One thing to know before deploying: stock's fast-LayerNorm extension cannot run on this card and fails LATENTLY.** It emits SASS for sm_70..sm_100 with no PTX, so on sm_121 the call returns, `torch.cuda.synchronize()` passes, and the NEXT unrelated torch operation raises `no kernel image is available for execution on the device` — with a LayerNorm output in hand that was never written. `[kit.env] LAYERNORM_TYPE = "torch"` is upstream's own switch and is load-bearing; the worker refuses to start if an operator overrides it back on a card outside the extension's built set. Public publication, cross-user isolation, concurrency, recovery and structural accuracy are unvalidated; keep this deployment private.

- Operation: `protenix_v1_fold`
- Start: `python -m tooluniverse.remote.protenix_v1.protenix_v1_tool`
- Endpoint: `http://127.0.0.1:8046/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 9.65 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8046/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8046/mcp --name validation-protenix_v1 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation protenix_v1`. Add `--check-provider-env` before launch, `--live`
after launch, and `--check-connect-prereqs` before sharing. Live preflight
checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it has
not been exercised through the Platform at all, and everything above was
measured locally, on one card, through the loopback endpoint. Public
publication, independent-caller authorization/isolation, broad saturation and
persistent supervision are unvalidated here.

## Authorize once, then share with one short command

Log in once per machine, and again after key rotation:

```bash
tu remote login
```

`tu remote login` requests a short-lived device code, opens the TU Platform
approval page and polls until the signed-in user approves; no key is copied or
pasted, and the CLI never displays the computer-only key it stores in a local
0600 file. On a headless machine add `--no-browser`. Then each private share is
one command:

```bash
tu remote share protenix_v1
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share protenix_v1 --name my-protenix_v1-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-protenix_v1-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Getting the structures out

`return_structures: true` returns the mmCIF as text, and that works only for
small complexes. **A tool result is capped at 100,000 characters** by
`smcp.py`, which then falls back to RAW STRING truncation -- it cuts the JSON
mid-string and hands the caller something that does not parse, rather than a
short answer or a named error. A 131-residue monomer measured 102,306
characters, so the very first thing most callers fold already exceeds it. The
tool now refuses a structure above that limit with a message naming the way
through, instead of letting the transport corrupt the reply.

The way through is **`out_dir`**: an absolute server-side directory the
predictions are written to, returned as `structure_paths`. That is also the
right shape when one provider's output is another's input -- it keeps a
megabyte of mmCIF off the wire entirely. `apnovo_generate_designs` already
works this way, returning a `run_dir` its own evaluation reads, and the
apnovo -> protenix_v1 -> apnovo chain measured on 2026-10-15 used `out_dir`
for exactly this reason.

## Overview

Protenix 1.1.0 all-atom structure prediction for a protein, nucleic-acid, ligand and ion complex

Weights and kit are pinned: `src/tooluniverse/remote/protenix_v1/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/protenix_v1.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
