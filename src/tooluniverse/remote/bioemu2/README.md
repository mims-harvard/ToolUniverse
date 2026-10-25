# BioEmu-2 as a ToolUniverse remote tool

BioEmu-2 ("biomolecular emulator") is Microsoft Research AI for Science's
foundation model for biomolecular structure and dynamics, released as a public
preview on 2026-10-19 under the **MIT License** with open weights. It is a
diffusion-based all-atom score model of roughly 500M parameters: given a
molecule's composition it generates an *ensemble* of plausible 3D structures,
rather than one. Multi-chain complexes, ligands and nucleic acids are
supported.

- Weights and model card: <https://huggingface.co/microsoft/bioemu2>
- Source: <https://github.com/microsoft/bioemu2>

## What it does, and the three things it does not

`bioemu2_sample_structures` takes a system — protein chains as sequences, or
upstream's own system definition for anything richer — and returns conformations.
Two modes, which differ in the sampler and not in what they accept:

- **`structure`** sharpens towards one accurate fold (`step_scale=1.5`).
- **`equilibrium`** samples the modelled equilibrium ensemble without
  sharpening.

It does **not** generate sequences. It does **not** predict binding affinities
or absolute free energies. And **sampling frequency is not a calibrated
Boltzmann probability** — upstream lists uncalibrated ensembles among its known
limitations, so counting how often a state appears is not a free-energy
measurement.

**Propagation is deliberately not exposed yet.** Stepping a sampled
conformation forward 1 ns to 1 µs with the implicit transfer operator is the
capability BioEmu-2 has that nothing else in ToolUniverse does, and it is the
headline of upstream's announcement. It is absent here because it needs a
starting ensemble handed back in — over this interface, a base64 XTC — and
nothing in this provider has run it. Shipping an operation whose only evidence
is that the Python API exists is the mistake the standard's section 9 names.
It belongs in a second change, with its own measurement.

## Composition is the input, coordinates are the output

Pass either:

- `sequences` — one one-letter amino-acid string per protein chain, lettered
  A, B, C… in the order given. Identical sequences become one entity with
  several chain ids.
- `system_yaml` — BioEmu-2's own system YAML, as written by
  `System.to_yaml()`. This is the route for ligands by CCD code or SMILES,
  RNA and DNA, modified residues, explicit chain ids and non-standard covalent
  bonds.

The worker composes both into one request document whose `system:` block is
upstream's system YAML unchanged, so the smoke input and an MCP call travel the
same path. `src/tooluniverse/remote/bioemu2/smoke/trp_cage.yaml` is that
document, written out by hand.

## The MSA is a network dependency unless you supply one

With no `msa_a3m`, BioEmu-2 retrieves an A3M alignment from the **public
ColabFold server** on a cache miss. That leaves this machine and depends on a
third party's availability and goodwill; upstream asks callers to query
serially from one IP, which this provider's one-request-at-a-time worker
happens to guarantee, and `launch.py` points `BIOEMU2_MSA_CACHE` under the
weights root so an alignment fetched by one worker survives into the next.

Supply `msa_a3m` to stay local. A query-only alignment is valid A3M and the
model degrades rather than failing — upstream says quality is expected to fall
for shallow MSAs, including orphan proteins and engineered constructs. The
smoke input carries exactly such a single-sequence alignment, which is why
`tu remote setup --only smoke` depends on no third party and why its result is
not a statement about accuracy.

## Residency buys the load here, not the warm-up

The opposite balance from `rfd4_proteina`, where the weights loaded in seconds
and warm-up was everything. `load_model()` measured **44.6 s and 49.9 s** on
the verified card across two processes and leaves 1.92 GiB resident; an
identical second request in the same process ran 27.3 s against 35.6 s for the
first. A worker that exits pays that 50 s again for every caller.

A third saving is built in the worker rather than inherited: the trunk runs
once per system at `O(RN² + N³)`, and an `EmuSession` holds those embeddings,
so one session is cached keyed by (system, MSA, mode) and a repeat request
skips the trunk. Exactly one, because the pair representations are `O(N²)` of
GPU memory and a cache of several would put the footprint outside the declared
budget.

## Measured envelope

Tokens are `AllAtomStructure.num_tokens`. Peak *allocated* is the per-request
figure; peak *reserved* is a session high-water mark that never shrinks, and
is the one a held worker must be budgeted against. "worker" rows went through
this provider's own socket; the others are a bare process.

| path | system | tokens | MSA | samples | alloc | reserved |
|---|---|---:|---|---:|---:|---:|
| bare | 1UBQ ubiquitin | 76 | deep | 16 | 3.03 | 3.73 |
| bare | 1AKE from PDB | 271 | deep | 16 | 6.07 | 8.76 |
| bare | 6LU7 Mpro + N3 | 676 | shallow | 8 | 7.66 | 12.25 |
| worker | 2 × adenylate kinase | 428 | deep | 4 | 8.56 | 12.38 |
| worker | 3 × adenylate kinase | 642 | deep | 4 | 12.40 | 18.04 |
| worker | the same, 2nd request | 642 | deep | 4 | 13.23 | 21.15 |

**Tokens are not the only axis.** Trunk memory is `O(RN + N²)`, and R — the
alignment depth — is the term that is easy to forget. 676 tokens with a 234 KB
A3M cost *less* than 428 tokens with a 3.2 MB one. An earlier draft of this
provider set the ceiling at 704 tokens from the 6LU7 row and declared 14.0
GiB; the 642-token rows are what that would actually have cost, and the
admission pool would have been oversold by 4 GiB on a realistic request.

**The same request costs more later in a session.** 642 tokens reserved 18.04
GiB as a fresh worker's first request and 21.15 GiB as its second, because the
caching allocator's high-water mark never shrinks.

**Inside the 448-token ceiling the ratchet does not appear.** Three different
shapes in one session — 428 tokens at 4 samples, 214 at 16, 428 at 8 — all
reported exactly 12.38 GiB reserved. That is what makes 448 a measurement
rather than a guess.

**Batch size barely moves the peak.** 1UBQ at 1 and at 16 samples both peaked
at 3.03 GiB, and the 214-token request at 16 samples allocated less than the
428-token one at 4. The `O(N²)` pair representation dominates `O(BN)`
throughout this range, so `num_samples` costs wall clock, not memory.

**Count tokens the way BioEmu-2 does.** Summing sequence lengths is a *floor*:
214 against a true 271 for 1AKE from the PDB, 624 against 676 for 6LU7. The
worker builds `AllAtomStructure.from_system()` and reads `num_tokens` — CPU
work on composition alone. The MCP tool does not duplicate the check, because
it cannot import `bioemu2`; an oversized system is refused one round trip
later, by name, with the real number.

## TOU validation and deployment status (2026-08-16)

> BioEmu-2 ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified), driver
> 580.173.02, on 2026-10-25, through this provider's own path: `tu remote
> setup` completed all four steps, with the smoke returning OK in 89 s at
> 2.06 GiB peak reserved and both declared outputs matched by the manifest's
> globs; four socket requests exercised the one-entry session cache in both
> directions; 428- and 642-token multi-chain systems ran on the same socket
> with real ColabFold queries, every frame passing physicality; and the live
> MCP endpoint returned correct results for three calls and named refusals
> for six malformed ones, four from the tool and two from the published
> schema. The orphan watchdog was observed releasing the card 122 s after the
> server stopped. Every wall-clock figure is an upper bound measured under a
> host load average of 26-45 and is **not** the model's speed; in particular
> **no saving from trunk reuse is established** — an identical repeat ran
> 15.4 s then 11.1 s through the socket but 22.3 s then 23.6 s through MCP,
> opposite signs and both inside the noise at 20 tokens. Propagation is not
> exposed. Only protein chains have gone through the worker: ligands, RNA and
> DNA are supported by upstream and unexercised here, as are contact
> conditioning, steering samplers and every physicality mode but one. Ensemble
> accuracy is unvalidated and nothing here checks it — the physicality report
> is geometry, and sampling frequency is not a calibrated Boltzmann
> probability. Public publication, cross-user isolation, concurrency and
> recovery are untested; keep this deployment private.

- Operation: `bioemu2_sample_structures`
- Start: `python -m tooluniverse.remote.bioemu2.bioemu2_tool`
- Endpoint: `http://127.0.0.1:8063/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the
  checkpoint is declared with a size and a sha256 and verified before the
  worker starts. It wraps no optimization kit, so `tu remote setup` has four
  steps rather than five. Keep provider data, weights, caches and credentials
  outside Git. Use one worker: the resident worker serves one request at a
  time by design, and a second in-flight request queues on its lock rather
  than doubling peak VRAM. The declared VRAM budget is 16.0 GiB against a
  measured 12.38 GiB session high-water mark at the 448-token ceiling, and it
  is an admission input rather than documentation: the pool reserves what the
  manifest declares on every request, large or small, so the headroom is paid
  for by every co-tenant all the time. Budget against *reserved*, not
  allocated — the largest in-cap request allocated 8.56 GiB, and a worker
  budgeted on that number would be 3.8 GiB short of what it holds. Raising
  `--max-tokens` is a scheduling decision as much as a measurement one:
  admitting 642 tokens would mean declaring roughly 24 GiB. Upstream supports
  far larger systems with context parallelism across four GPUs, which is a
  different deployment and is not this one.
- TOU check: `tu doctor --forward http://127.0.0.1:8063/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8063/mcp --name validation-bioemu2 --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation bioemu2`. Add `--check-provider-env` before launch, `--live`
after launch, and `--check-connect-prereqs` before sharing. Live preflight
checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix found all 30 private owner relays
online and all 41 operations discoverable. It imported each implementation as
unpublished owner draft(s), configured a 120-second timeout, and invoked it
through `/expert-sessions/{id}/test`. **This implementation was added after
that matrix and was not part of it**, so none of that evidence covers it: it
has not been exercised through the Platform at all, and everything above was
measured locally, on one card. Public publication, independent-caller
authorization/isolation, broad saturation and persistent supervision are
unvalidated here.

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
tu remote share bioemu2
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share bioemu2 --name my-bioemu2-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-bioemu2-remote-tool/SKILL.md).
The skill is the whole guide for this provider — how to build the two
environments, what `tu remote setup`'s four steps each prove, every refusal
name with its fix, and the measured numbers a host schedules on. This file
carries the deployment contract and deliberately does not restate it, because
two copies of a procedure drift and only one of them gets corrected.
