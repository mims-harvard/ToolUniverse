# AtlasFold remote tool

## TOU validation and deployment status (2026-08-16)

> AtlasFold v1.0.0 ran on the NVIDIA GB10 (aarch64, cc 12.1) under the optimization kit's `big` mode with **thirteen levers ablated and upstream's triangle backend forced to `torch`**. Both were necessary. This stack's triton 3.3.1 cannot compile a warp-shuffle kernel for this card -- it aborts the process with `LLVM ERROR: Cannot select`, which no worker can catch -- and a newer `ptxas` does not help, because the failure is upstream of ptxas. Verified on twelve requests in held workers including 600- and 800-residue folds. Peak reserved 12.06 GiB at 100 residues, 19.64 at 600, 38.63 at 800. **Read three warnings before deploying this one.** (1) A 35-residue smoke exercises NONE of the kit's kernel levers -- they are all gated at 512 tokens -- so a green smoke here would have been the most misleading result this provider could produce; the acceptance test must reach the largest input you will accept. (2) Stock AtlasFold under its own default `--kernel auto` cannot fold past about 128 tokens on this card at all, kit or no kit, because cuEquivariance ships its own Triton kernels; `--kernel torch` is the only backend that answers here. (3) The VRAM reserve RATCHETS: after one 800-residue fold the worker reports 38.63 GiB for every later request including a 3-second one, because the caching allocator keeps the segments it grew. A deployment capped at 400 residues holds this provider in 14 GiB rather than 39. Public publication, cross-user isolation, concurrency, recovery and structural accuracy are unvalidated; keep this deployment private.

- Operation: `atlasfold_predict`
- Start: `python -m tooluniverse.remote.atlasfold.atlasfold_tool`
- Endpoint: `http://127.0.0.1:8043/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 38.63 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8043/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8043/mcp --name validation-atlasfold --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation atlasfold`. Add `--check-provider-env` before launch, `--live`
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
tu remote share atlasfold
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share atlasfold --name my-atlasfold-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-atlasfold-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

AtlasFold v1.0.0 all-atom structure prediction for a protein monomer or a multimer complex

Weights and kit are pinned: `src/tooluniverse/remote/atlasfold/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/atlasfold.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
