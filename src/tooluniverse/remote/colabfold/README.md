# ColabFold (AlphaFold2-Multimer) remote tool

## TOU validation and deployment status (2026-08-16)

> ColabFold 1.6.1 on AlphaFold2-Multimer v3 ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode, on jax/jaxlib 0.5.3. **It takes a precomputed MSA and contacts no MMseqs2 server** — that is upstream's own branch (`run()` is `if a3m_lines is None: get_msa_and_templates(...) else: unserialize_msa(...)`), and `run_mmseqs2` is imported inside the branch this provider never takes. **Stock ColabFold cannot fold on this card at all**: the forward pass aborts with `Unsupported conversion from bf16 to f16 / LLVM ERROR: Unsupported rounding mode for conversion`, an uncatchable `report_fatal_error` from LLVM's NVPTX instruction selector, because ColabFold keeps its two recycle-state tensors in float16 while the trunk is bf16. Upstream's own `use_bfloat16=False` clears it, and that parameter has no command-line flag — `colabfold_batch` exits 134 (SIGABRT) on this hardware having written logs and no structure. So this wrapper is not a faster route to the model here; it is the only one. 17 requests, 17 ranked structures, 0 failures. Ladder 4.0 GiB flat at 100 / 200 / 400 residues (declared at 400); residency 1.16x warm, because upstream persists the expensive part. Public publication, cross-user isolation, concurrency, recovery and scientific accuracy are unvalidated; keep this deployment private.

- Operation: `colabfold_predict`
- Start: `python -m tooluniverse.remote.colabfold.colabfold_tool`
- Endpoint: `http://127.0.0.1:8051/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 4.0 GiB; read the envelope it was measured at in
  the manifest before co-tenanting anything else on the card, because a larger
  request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8051/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8051/mcp --name validation-colabfold --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation colabfold`. Add `--check-provider-env` before launch, `--live`
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
tu remote share colabfold
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share colabfold --name my-colabfold-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-colabfold-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

ColabFold 1.6.1 / AlphaFold2-Multimer v3 structure prediction from a PRECOMPUTED MSA (.a3m): no MMseqs2 server is contacted and no alignment is built

Weights and kit are pinned: `src/tooluniverse/remote/colabfold/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/colabfold.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
