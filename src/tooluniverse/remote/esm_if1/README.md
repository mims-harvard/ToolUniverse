# ESM-IF1 inverse-folding remote tool

## TOU validation and deployment status (2026-08-16)

> ESM-IF1 sequence design ran on the NVIDIA GB10 host (aarch64, 20 cores, cc 12.1, driver 580.173.02) **on the CPU**, under the optimization kit's `fast` mode (lever `batched_sampling`). **This is the first provider on the standard with `[gpu] policy = "none"`, and that is a measurement rather than a fallback.** The kit pins torch 2.4.0, whose CUDA generation predates this card: cuBLAS 12.4 for aarch64 carries cubins only through sm_90. It does carry **sm_90 PTX**, so a forward JIT is not ruled out and the honest status of that route is **unmeasured rather than impossible** — `provider.toml`'s `[gpu]` section has the `cuobjdump` output and the three reasons the route was not taken anyway, the first being that the kit's pinned PyG companions have no aarch64 build at any version. Four consecutive identical requests produced **byte-identical** FASTA files, and the same sha256 as the kit's own CLI. Peak RSS is flat in length and driven by the product of length and sample rows: 2.45 GiB from 64 through 395 residues, 3.65 at 800x2, and **11.22 GiB at the worst request the declared ceilings admit together** (1600 tokens x 4 rows, 757.7 s). Schedule on 11.22 unless the deployment caps the input; the smoke's 2.45 would under-budget an ordinary request by 4.6x. Public publication, cross-user isolation, concurrency, recovery and design quality are untested; keep this deployment private.

- Operation: `esm_if1_design`
- Start: `python -m tooluniverse.remote.esm_if1.esm_if1_tool`
- Endpoint: `http://127.0.0.1:8050/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  Read the measured budget and the envelope it was measured at in the manifest
  before co-tenanting anything else on the card.
- TOU check: `tu doctor --forward http://127.0.0.1:8050/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8050/mcp --name validation-esm-if1 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation esm_if1`. Add `--check-provider-env` before launch, `--live`
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
tu remote share esm_if1
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share esm_if1 --name my-esm-if1-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-esm_if1-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

ESM-IF1 inverse folding: sampled sequences for a protein backbone (fair-esm GVP-Transformer, 142M)

Weights and kit are pinned: `src/tooluniverse/remote/esm_if1/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/esm_if1.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
