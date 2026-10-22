# ESMFold 2 remote tool

## TOU validation and deployment status (2026-08-16)

> ESMFold2-Fast under the optimization kit's `fast` mode ran on the NVIDIA GB10 (aarch64, cc 12.1). Three folds of an 89-residue chain in one held worker took 2.7 s, 1.1 s and 1.1 s; a live call through this entry point returned pTM 0.776 for barstar. Peak reserved is 14.21 GiB at rest and 25.28 GiB at 800 residues, measured. This is the most expensive of the six providers to hold: 25.6 GiB of weights across sixteen files, ESMC-6B among them. Public publication, cross-user isolation, concurrency, recovery and biological accuracy are unvalidated; keep this deployment private.

- Operation: `esmfold2_fold`
- Start: `python -m tooluniverse.remote.esmfold2.esmfold2_tool`
- Endpoint: `http://127.0.0.1:8038/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 25.28 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8038/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8038/mcp --name validation-esmfold2 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation esmfold2`. Add `--check-provider-env` before launch, `--live`
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
tu remote share esmfold2
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share esmfold2 --name my-esmfold2-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-esmfold2-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

ESMFold2 protein complex structure prediction from sequence (mmCIF + pLDDT/PAE)

Weights and kit are pinned: `src/tooluniverse/remote/esmfold2/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/esmfold2.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
