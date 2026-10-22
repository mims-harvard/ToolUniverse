# Mosaic gradient binder-design remote tool

## TOU validation and deployment status (2026-08-16)

> mosaic (escalante-bio/mosaic through the joltz JAX port of Boltz-2) designed binders on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode. **mosaic DESIGNS a binder; it does not fold a sequence you give it.** One request is one design: a target sequence and a binder length in, a binder sequence plus the predicted complex and its ipTM / pLDDT / PAE out. Every one of the 125 optimiser steps is a full Boltz-2 forward and backward pass. Acceptance in one held worker: ladder 169 / 256 / 384 tokens (pool peak 8.0 / 16.0 / 32.0 GiB, in-use 4.85 / 8.13 / 15.67), mixed shapes 4/4, four identical requests 4/4 (23.6 / 23.4 / 23.3 / 23.2 s), every request writing a complex PDB. **Declared budget 32.0 GiB at the 384-token ceiling.** 512 tokens was measured and is not offered: about 120 s per step, so one design is hours. **Residency gain depends heavily on request size**: 11.5x for a 5-step request at 169 tokens (269.5 s cold, 23.5 s held) but only ~1.5x at 169 tokens and ~1.08x at 384 for the full 125-step recipe, because the compile it saves (a few minutes per shape) is small against the work. A new SHAPE (target residues x copies + binder length) pays a compilation; a seed or step change does not; an epitope or a second target copy costs a smaller recompile. Designs are not bit-reproducible across requests (boltz re-draws reference coordinates). The kit's `fast` mode engages here but was not adopted: see provider.toml. Wall times were taken on a shared card; peaks reproduce, times do not. Public publication, cross-user isolation, concurrency, recovery and scientific quality (a high ipTM is the model's opinion of a design optimised against it) are unvalidated; keep this deployment private.

- Operation: `mosaic_design_binder`
- Start: `python -m tooluniverse.remote.mosaic.mosaic_tool`
- Endpoint: `http://127.0.0.1:8055/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 32.0 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8055/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8055/mcp --name validation-mosaic --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation mosaic`. Add `--check-provider-env` before launch, `--live`
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
tu remote share mosaic
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share mosaic --name my-mosaic-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-mosaic-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

Designs a protein binder against a target sequence by gradient descent through Boltz-2 (escalante-bio/mosaic + joltz): 125 steps of simplex APGM on a position-weight matrix under a contact + inverse-folding loss, then one refold of the designed sequence. Returns the binder sequence, the predicted complex and its ipTM / pLDDT / PAE. No MSA server is contacted.

Weights and kit are pinned: `src/tooluniverse/remote/mosaic/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/mosaic.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
