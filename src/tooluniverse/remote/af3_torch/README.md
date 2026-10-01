# AlphaFold 3 (PyTorch port) remote tool

## TOU validation and deployment status (2026-08-16)

> AlphaFold3 (the xfold PyTorch re-implementation, Apache-2.0, on the public OpenFold3-preview2 checkpoint -- not DeepMind's licence-gated parameters) ran on the NVIDIA GB10 (aarch64, cc 12.1) under the optimization kit's `fast` mode. This deployment was expected not to be possible on aarch64 and is: the one C++ extension its second environment needs built clean over 236 targets with no portability patch, and the converted weights file is bit-exact against a sha256 the kit measured on x86-64. Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS plus a mixed-shape sequence and an ascending ladder: forward 3.51 s cold then 1.46 s warm, peak reserved 1.75 GiB at 100 residues rising to 9.21 at 800 -- the steepest ladder of any provider here (5.3x), because the AF3 pair track dominates with no large constant term to flatten it. **This provider needs TWO pinned interpreters**, one for the model and one CPU-only for featurisation and the mmCIF writers; `[env]` declares one, so the second is supplied through environment variables and the weights step refuses by name without it. Public publication, cross-user isolation, concurrency, recovery and structural accuracy are unvalidated; keep this deployment private.

- Operation: `af3_torch_predict`
- Start: `python -m tooluniverse.remote.af3_torch.af3_torch_tool`
- Endpoint: `http://127.0.0.1:8036/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 9.21 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8036/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8036/mcp --name validation-af3_torch --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation af3_torch`. Add `--check-provider-env` before launch, `--live`
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
tu remote share af3_torch
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share af3_torch --name my-af3_torch-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-af3_torch-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

AlphaFold 3 (xfold PyTorch port) on OpenFold3-preview2 weights: all-atom structure prediction from an AlphaFold 3 fold-input JSON

Weights and kit are pinned: `src/tooluniverse/remote/af3_torch/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/af3_torch.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
