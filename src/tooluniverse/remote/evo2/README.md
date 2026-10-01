# Evo 2 remote tool

## TOU validation and deployment status (2026-08-16)

> Evo 2 7B ran on the NVIDIA GB10 (aarch64, cc 12.1) under the optimization kit's `exact` mode. Two things had to be built for this architecture and neither was optional: **flash-attn from source** (~2 h; `import evo2` does not survive its absence, because upstream's `vortex/model/rotary.py` imports it unguarded -- so `mode = "off"` would not have routed around it), and **a CUDA 12.9 ptxas** for Triton, whose bundled one tops out below this card. Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS plus a mixed-shape sequence: 5.6-6.5 s per 1024 bp window after a 243 s first call that reads the 12.8 GiB checkpoint. Peak reserved 16.82 GiB at 1024 bp rising only to 19.98 at 8192 -- 1.19x over 8x the length, because a 7B parameter term dominates. **evo2_40b is not this provider**: 76.6 GiB of weights, two visible devices for vortex's layer split, and FP8 through Transformer Engine, none of which this host has. Public publication, cross-user isolation, concurrency, recovery and scoring quality are unvalidated; keep this deployment private.

- Operation: `run_evo2_score`
- Start: `python -m tooluniverse.remote.evo2.evo2_tool`
- Endpoint: `http://127.0.0.1:8041/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 19.98 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8041/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8041/mcp --name validation-evo2 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation evo2`. Add `--check-provider-env` before launch, `--live`
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
tu remote share evo2
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share evo2 --name my-evo2-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-evo2-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

Evo 2 genomic foundation model: DNA sequence likelihoods and per-position embeddings

Weights and kit are pinned: `src/tooluniverse/remote/evo2/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/evo2.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
