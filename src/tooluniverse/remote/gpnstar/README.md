# GPN-Star variant-effect remote tool

## TOU validation and deployment status (2026-08-16)

> GPN-Star `v100-200m` (gpn 0.9.0, optimization kit `exact` mode) ran on the NVIDIA GB10 (aarch64, cc 12.1) under torch 2.13.0+cu130, so the GPU is open here. **What one request is:** a list of single-nucleotide variants (`chrom`, 1-based `pos`, `ref`, `alt`) scored against a multiple-species ALIGNMENT STORE the host holds; each score is `logit(alt) - logit(ref)` at the masked position, averaged over the forward and reverse-complement windows. GPN-Star is a language model over an alignment window, not over bare DNA. **The alignment store is an input, not a weight, and was NOT downloaded for this validation**: the real hg38 100-way store is a 42 GB zip that unpacks to ~64 GB (`songlab/multiz100way`). Everything above was measured against the kit's 0.14 MiB sparse example store (eight windows on chromosomes 1, 2, 3 and 5) and against a synthetic store of the same shape for worst-case content; any other position is refused with "the alignment holds no data". Verified on FOUR CONSECUTIVE IDENTICAL REQUESTS, a mixed-batch-shape sequence, and a window / batch / single-variant / refusal sequence in which the same request returned a byte-identical `scores_sha256` five times. Peak reserved 1.01 GiB at 2 variants rising to 5.79 GiB at the 8192-column ceiling (batch 64 x window 128); declared budget 7.72 GiB, the stock-projection bound at that row. The kit's CUDA-graph lever is declined: with it on, 29 distinct batch shapes grew the reserve to 24.3 GiB. Wall times were taken on a contended card (load average ~65, five other GPU processes); peaks reproduce under contention and times do not. Public publication, cross-user isolation, concurrency, recovery and scientific validity of the scores against a full store are untested; keep this deployment private.

- Operation: `run_gpnstar_vep`
- Start: `python -m tooluniverse.remote.gpnstar.gpnstar_tool`
- Endpoint: `http://127.0.0.1:8057/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 7.72 GiB; read the envelope it was measured at
  in the manifest before co-tenanting anything else on the card, because a
  larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8057/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8057/mcp --name validation-gpnstar --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation gpnstar`. Add `--check-provider-env` before launch, `--live`
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
tu remote share gpnstar
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share gpnstar --name my-gpnstar-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-gpnstar-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

GPN-Star multi-species-alignment language model: single-nucleotide variant effect scores

Weights and kit are pinned: `src/tooluniverse/remote/gpnstar/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/gpnstar.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
