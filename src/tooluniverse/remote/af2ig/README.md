# AlphaFold 2 initial-guess (binder interface) remote tool

## TOU validation and deployment status (2026-08-16)

> af2ig — the `af2_initial_guess` step of nrbennet/dl_binder_design at commit `cafa3853`, AlphaFold 2 `model_1_ptm` re-predicting a designed binder–target complex from the complex itself as the structural initial guess — ran on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) under the optimization kit's `off` mode. **Read what this is before reading anything else: "ig" is INITIAL GUESS, the input is a STRUCTURE and not a sequence, and the number it exists to produce is `pae_interaction` (angstroms; the field's working threshold is below 10).** All five `tu remote setup` steps are green and the acceptance suite passed: an ascending ladder, a mixed-shape phase, four consecutive identical requests, and a separate clean-worker run at the row the budget is declared on — an ascending ladder of 100 / 200 / 400 residues, a mixed-shape phase, four consecutive identical requests, a separate clean-worker run at 800 residues (the row the budget is declared on), and a two-rebuild engine test. **29 held-worker requests, 29 structures, 0 failures**, every one asserted to have written a `*_af2pred.pdb`. **THERE ARE NO PADDING BUCKETS HERE, which is the opposite of AlphaFold 3 and changes which half of the test carries the evidence**: this model compiles one XLA program per *exact* total residue count, so four identical requests exercise one program and the shape change is the whole test. Residency is worth **26x at its best rung and 1.7x at the row the budget is declared on** -- 95.0 s cold against 3.6 s held at 100 residues, and 272.1 s against ~163 s at 800. Plan with the second number; the first is the best case, and it is largest where a request is cheapest. Declared budget **6.0 GiB at 800 residues**, which is also the tool's input ceiling; the ladder is 0.5 / 1.0 / 2.0 / 6.0 GiB at 100 / 200 / 400 / 800 residues (reported), over a working set of 0.49 / 0.62 / 1.23 / 4.36 GiB (actual). Two cautions below are specific to this provider: its **VRAM figure is quantised** in a way a torch provider's is not, and its environment carries one named deviation from the kit's lock (`tensorflow` for `tensorflow-cpu`, because no aarch64 wheel of the latter exists). Public publication, cross-user isolation, concurrency, recovery and scientific quality are untested; keep this deployment private.

- Operation: `af2ig_predict`
- Start: `python -m tooluniverse.remote.af2ig.af2ig_tool`
- Endpoint: `http://127.0.0.1:8053/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  Keep provider data, weights, caches and credentials outside Git. Use one
  worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM.
  The measured VRAM budget is 6.0 GiB; read the envelope it was measured at in
  the manifest before co-tenanting anything else on the card, because a larger
  request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8053/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8053/mcp --name validation-af2ig --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation af2ig`. Add `--check-provider-env` before launch, `--live`
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
tu remote share af2ig
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share af2ig --name my-af2ig-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-af2ig-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.

## Overview

AlphaFold 2 initial-guess re-prediction of a designed binder-target complex (nrbennet/dl_binder_design, model_1_ptm): takes the complex as a PDB, returns the predicted complex plus the interface confidence scores (pae_interaction, plddt_binder, RMSDs). No MSA is built and no external service is contacted.

Weights and kit are pinned: `src/tooluniverse/remote/af2ig/provider.toml`
declares the upstream kit by commit, the environment by lock file, and every
weight file with its byte count and digest. Nothing is fetched at request time.
The measured peak VRAM for this host is written to
`~/.cache/tooluniverse/measured/af2ig.json`, and that per-host file -- not the
number in the manifest -- is what a scheduler should read.
