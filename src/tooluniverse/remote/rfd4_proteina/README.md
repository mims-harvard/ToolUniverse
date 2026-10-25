# RFD4-Proteina

Joint sequence and structure design — de novo monomers, protein and DNA
binders, motif scaffolding, enzyme active sites, small-molecule binders,
antibody and TCR CDR redesign, partial diffusion and inverse folding — held
resident behind one MCP tool.

NVIDIA's Generative AI team with the David Baker Lab at the UW Institute for
Protein Design. Released 2026-10-19, BSD 3-Clause, 435,622,465 parameters.

```bash
tu remote setup rfd4_proteina
tu remote check rfd4_proteina
tu remote run   rfd4_proteina
```

## The first provider here that wraps no optimization kit

The thirty-one resident providers before this one each pin a commit of
`anthropics/uplifting-biomolecular-modeling`, and most of their worker code
exists to arm that kit. There is no kit for this model: upstream publishes the
inference runtime itself as `rfd4-proteina` on PyPI. Three consequences a
reader comparing providers will notice:

* **no `[kit]` table** in `provider.toml`. The manifest loader already treated
  it as optional, so nothing had to change to accept the shape.
* **a local `launch.py`** instead of `kit_launch:build_command`. The shared
  launcher resolves a kit checkout and reads the kit's mode variable, and
  would refuse this provider while describing a kit that does not exist.
* **nothing editable on top of `requirements.lock`**. Elsewhere the kit and
  `opt_core` install over the frozen list and are deliberately absent from it.
  Here the list is the whole environment.

## One tool, not seven

Upstream serves seven tasks, and it is tempting to expose seven tools. Its own
documentation is why we do not:

> `task` selects how the sampler runs the trajectory, not which design problem
> is being solved.

The design problem lives in the **input**. A binder against a target is
`generation` with the target's coordinates and sequence conditioned and its
epitope marked as hotspots; a scaffolded motif is the same call with different
annotations; several conditions compose in one file, so a binder that also
preserves a structural motif is expressed by supplying both. Splitting by task
would invent a distinction the model does not have, and would push callers
towards choosing a mode instead of annotating their structure.

So `input_cif` is the argument, and it must be an **annotated** mmCIF. An
ordinary structure is not a design specification, and the tool refuses one up
front rather than spending half a minute discovering it. Upstream's
`examples/` directory has one input per design shape.

## Choosing a backend: measure it yourself, because this card could not

`inference_backend` and `compile_lengths` are the two levers, and the
measurements here **do not settle which to use**. Three configurations were run
as four-request ladders in one process -- one unconditional 100-mer,
`num_replicates=1` -- and every one of them was measured on a host carrying a
load average between 30 and 70 from unrelated CPU jobs, rising across the
session rather than holding still:

| configuration | req 0 | warm mean | peak |
|---|---:|---:|---:|
| native, compilation off | 44.9 s | 22.7 s | 1.86 GiB |
| native, released `compile_lengths` | 128.1 s | 29.1 s | 1.90 GiB |
| `bioir`, `cuda_graph: true` | 169.5 s | 30.8 s | 2.80 GiB |

Those are upper bounds under contention, not the model's speed. How badly that
matters is easy to show: the same request in the same configuration has since
been timed at 128 s and at 298 s on this card. **The warm-column ordering is
inside that spread and should not be read as a ranking.** The table is here so
a later measurement on a quiet machine has something to compare against.

What survives the noise is the first-request cost, because the differences are
far larger than the spread: compilation cost 83 s more up front and BioIR
125 s more, and neither visibly repaid it within four requests at this size.
That is a reason to measure before enabling one, not a finding that they lose.
CUDA graph capture is capped at 511 tokens and upstream's own figures -- 22-55 s
for a cold length bucket against 3-28 s warm -- were measured on an H100 across
a range of sizes. A crossover at larger designs is likely and nobody has
measured where. Upstream's default is therefore left alone, the backend is a
per-request argument, and anyone deploying at a size that matters to them
should run the same four requests at that size before choosing.

## What residency buys, and what it does not

The usual argument for holding a model -- a long weight load paid once -- is the
*weakest* one available here. The bundle is 1.74 GB and
`Proteina.from_pretrained` returned in 2-17 s from a warm Hub cache.

What a held worker actually collects is what the first request of a process
defers, and that gap is large and survives the whole stack rather than only
existing inside a benchmark script. Through the live MCP endpoint it is 185.9 s
cold against 49.6 s warm; through the worker's socket, 297.9 s cold against
28-45 s warm. A worker that exits after each call pays all of it again, every
time.

## Weights

Loaded through `hf_ckpt_path` + `hf_ckpt_revision`, so what `setup` fetches
and verifies is the pinned Hub snapshot, into the directory
`RFD4_PROTEINA_HF_HOME` names.

The flow model and the autoencoder are a **matched pair**. Upstream is explicit
that mixing one release's flow model with another's autoencoder "produces
nonsense rather than an error", because the autoencoder defines the latent
space the flow model generates in. The root bundle is that pair in one
safetensors file; `config.json` is checked alongside it because it carries the
latent dimension and residue vocabulary size (32 and 147 here, against 16 and
33 in the release this supersedes) — a stale config against current weights is
exactly the mixing upstream warns about, arriving in a file small enough that
nobody would look at it.

Both digests are upstream's own `bundle_sha256` and `bundle_config_sha256`
from `release-checkpoints.json`, and both were confirmed against the bytes this
provider was measured on.

## Metrics

Not computed. The worker passes `~metrics`, and the oracle-backed refolding
metrics need AlphaFold2 or AlphaFold3 with their own environment and weights,
a separate download. Upstream's hosted deployment makes the same choice and
says so. The per-design numbers you get back are sequences and atom counts
read out of the design itself.

## TOU validation and deployment status (2026-08-16)

> RFD4-Proteina ran on the NVIDIA GB10 (aarch64, cc 12.1, 128 GB unified), driver 580.173.02, on 2026-10-25, through this provider's own path: `tu remote setup --only smoke` returned OK with peak reserved 1.89 GiB and a design matched by the manifest's `outputs` glob, four requests through the worker's socket each returned a 100-residue design, and two live calls through the MCP endpoint returned 862 and 825 atoms at 185.9 s cold against 49.6 s warm. Every wall-clock figure is an upper bound measured under a host load average of 30-45 and is **not** the model's speed; the backend ranking is unmeasured on a quiet machine. Only the unconditional monomer mode was exercised -- binder design, motif scaffolding, enzyme active sites, small-molecule binders, antibody/TCR redesign, partial diffusion and inverse folding are the same call with different annotations but none of them has been run here. Design quality is unvalidated and nothing in this provider checks it: refolding metrics are off, and the unconditional input gave strikingly charged repetitive helices (glutamate 29-68% of residues against roughly 6% in natural proteins), which reproduces in a bare process and is the model on this input rather than a defect in the path. Public publication, cross-user isolation, concurrency, recovery and long inputs are unvalidated; keep this deployment private.

- Operation: `rfd4_proteina_design`
- Start: `python -m tooluniverse.remote.rfd4_proteina.rfd4_proteina_tool`
- Endpoint: `http://127.0.0.1:8062/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the weights
  are declared with a size and a sha256 and verified before the worker starts.
  It wraps no optimization kit, so `tu remote setup` has four steps rather than
  five. Keep provider data, weights, caches and credentials outside Git. Use
  one worker: the resident worker serves one request at a time by design, and a
  second in-flight request queues on its lock rather than doubling peak VRAM --
  which matters more here than for a predictor, because `num_replicates` makes
  one request an arbitrary amount of work. The declared VRAM budget is 6.0 GiB
  against a measured 1.89-2.80 GiB, and it is now an admission input rather
  than documentation: the pool reserves what the manifest declares, so the
  headroom is paid for in scheduling. It was measured at 100 residues and
  upstream caps a design at 1024 tokens; read that envelope before
  co-tenanting anything else on the card, because a larger request exceeds it.
- TOU check: `tu doctor --forward http://127.0.0.1:8062/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8062/mcp --name validation-rfd4_proteina --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation rfd4_proteina`. Add `--check-provider-env` before launch,
`--live` after launch, and `--check-connect-prereqs` before sharing. Live
preflight checks exact MCP discovery only; it does not run or validate a model.

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
tu remote share rfd4_proteina
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share rfd4_proteina --name my-rfd4_proteina-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key is
missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced; unset
or correct it and run `tu remote login` again. Non-interactive jobs also fail
fast. `tu remote logout` removes only the local copy; `tu remote logout
--revoke` revokes the computer-only platform connection first and leaves the
server record offline for owner inspection.

See the [complete setup and verification guide](../../../../skills/setup-rfd4_proteina-remote-tool/SKILL.md).
The skill is the whole guide for this provider -- how to build the two
environments, what `tu remote setup`'s four steps each prove, every refusal name
with its fix, and the measured numbers a host schedules on. This file carries
the deployment contract and deliberately does not restate it, because two copies
of a procedure drift and only one of them gets corrected.
