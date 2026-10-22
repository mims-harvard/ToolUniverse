# AlphaFold 3 (JAX fork) remote tool

## TOU validation and deployment status (2026-08-16)

> AF3-JAX (the sokrypton/alphafold3 open fork on public OpenFold3-preview2 weights) folded on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode. **It is the first JAX provider on this standard, and the largest residency gain measured here: 24-26x** — four consecutive identical requests ran 170.5 / 8.3 / 7.0 / 7.0 s on an idle card and 179.1 / 6.8 / 6.8 / 6.8 s on a contended one, against RFdiffusion3's 12x. (A contended card gives the *higher* ratio, because it slows the first request far more than the replays; read any residency multiple with that in mind.) **That figure is the smallest input's, which is where it is largest: at the row the budget is declared on — 800 residues — the same worker gives 3.5x**, 755.0 s cold against ~218 s held. Plan with the second number; the first is the best case. Three things residency keeps, and the third is this provider's own: the 1.37 GB zstd weight read, the XLA executables (one per padding bucket), and **tokamax's per-shape autotune, which nothing persists** — upstream's `ModelRunner._load_autotune_cache` reads a file that its `except Exception: pass`-wrapped writer never produces here, so a worker restart pays the first-request price again per bucket. That is why `idle_timeout_s` is 900 and not something shorter. Ladder 2.0 / 4.0 / 4.0 / 8.0 GiB at 100 / 200 / 400 / 800 residues; declared budget 8.0 at the 832-token bucket. Eleven acceptance requests, every one asserted to have produced a structure. Two cautions below are specific to this provider: it does not run at all without one upstream flag (**the shared-memory wall**), and **its VRAM figure is quantised** in a way a torch provider's is not. Public publication, cross-user isolation, concurrency, recovery and scientific quality are unvalidated; keep this deployment private.

- Operation: `af3_jax_predict`
- Start: `python -m tooluniverse.remote.af3_jax.af3_jax_tool`
- Endpoint: `http://127.0.0.1:8045/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 8.0 GiB; read the envelope it was measured at in
  the manifest before co-tenanting anything else on the card, because a larger
  request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8045/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8045/mcp --name validation-af3_jax --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation af3_jax`. Add `--check-provider-env` before launch, `--live`
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
tu remote share af3_jax
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share af3_jax --name my-af3_jax-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-af3_jax-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

AlphaFold 3 (sokrypton/alphafold3 JAX fork) on OpenFold3-preview2 weights: all-atom structure prediction from an AlphaFold 3 fold-input JSON carrying its own MSAs

Weights and kit are pinned: `src/tooluniverse/remote/af3_jax/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/af3_jax.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
