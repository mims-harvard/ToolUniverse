# AlphaProtein Novo (`apnovo`)

De novo enzyme design by catalytic-motif scaffolding. A conditional joint
sequence–structure diffusion model (147.5 M parameters) co-generates backbone
coordinates and sequence conditioned on a fixed catalytic motif and fixed
ligand atoms, followed by optional LigandMPNN resequencing, AlphaFold 3
structure prediction per mechanistic state, and metric evaluation.

Upstream: <https://github.com/google-deepmind/alphaprotein-novo> (Apache-2.0
source), pinned at `e7ce276cb4a1f68c2ba7d5aa793192cfcb4845c8`.
Paper: Wu, Z. et al., *Designing enzymes for new-to-nature chemistry and
non-natural substrates with AlphaProtein Novo*, bioRxiv 2026,
doi [10.64898/2026.10.01.756017](https://www.biorxiv.org/content/10.64898/2026.10.01.756017v1).

**Validation status: `verified`.** The acceptance suite has run twice, with two
different ladders, and the full generate -> fold -> ingest -> evaluate chain has
run end to end on this card. What has been established on this machine, and
what has NOT — scientific quality above all — is listed under
"What has been measured" below. Installation is
`skills/setup-apnovo-remote-tool/SKILL.md`; scientific use is
`skills/tooluniverse-enzyme-design/`.

---

## The deployment contract

This provider is **not** interchangeable with the other GPU providers in this
tree, because its weights are licensed and its outputs carry terms. Three
consequences bind any deployment:

**1. Non-commercial only, and the restriction is on the organisation.**
The AP Novo generator model parameters and their Output are available only to
non-commercial organisations — universities, non-profit organisations and
research institutes, educational, journalism and government bodies. They are
not available to any other kind of organisation *even for non-commercial work*,
and Input must not be provided by or on behalf of a commercial organisation.
A deployment that serves users whose eligibility is unknown does not satisfy
this. Keep this provider private to an eligible organisation.

**2. The weights are never redistributed, and this provider never fetches them
on a user's behalf without that user's own acceptance.**
`tu remote setup apnovo --only weights` prints the terms and refuses until
`APNOVO_ACCEPT_WEIGHTS_TERMS=1` is set by the operator. Google grants access
either to an individual for their own use — who may not share their copy — or
to an authorised representative who may share it within that organisation.
Weights may only be used if received directly from Google. **A matching
checksum is not a licence**: an exact-digest copy from a third party is still
not a copy you may use, which is the same rule this tree applied to
`protenix_v2`.

**3. Output carries notices, and this provider must not strip them.**
Upstream writes the AP Novo Output Terms of Use notice into its mmCIF and FASTA
output (`alphaprotein_novo.constants.terms_of_use`). Anything this provider
returns to a caller preserves it. If a caller converts formats and drops the
notice, re-attaching it and a copy of the terms before distribution is that
caller's obligation.

**Prohibited inputs and uses**, from upstream's prohibited-use policy, and
refused here: motifs, scaffolds, ligands or substrates derived from or
targeting biological toxins, venoms, virulence factors, regulated pathogens,
chemical or biological weapons or their precursors, controlled substances or
hazardous metabolic disruptors; circumventing biosecurity screening,
gene-synthesis customer or sequence screening, or safety filters; and using
Output to train, fine-tune or distil any de novo protein or enzyme design,
biomolecular structure generation or protein sequence design model.

**Citation is a licence condition**, not a courtesy: any publication or
disclosed finding arising from this provider must cite the paper above.

Full texts: [weights terms](https://github.com/google-deepmind/alphaprotein-novo/blob/main/WEIGHTS_TERMS_OF_USE.md),
[prohibited use](https://github.com/google-deepmind/alphaprotein-novo/blob/main/WEIGHTS_PROHIBITED_USE_POLICY.md),
[output terms](https://github.com/google-deepmind/alphaprotein-novo/blob/main/OUTPUT_TERMS_OF_USE.md).

---

## What has been measured

Established on this machine (NVIDIA GB10, aarch64, cc 12.1, driver 580.173.02):

- **The dependency set resolves natively.** `uv pip compile` on upstream's
  `pyproject.toml` for CPython 3.12 yields 72 pinned packages including 13
  `nvidia-*-cu12` wheels and **no x86-64 direct URLs** — so this kit does not
  pin an architecture by link, which is the failure mode about twenty of the
  surveyed kits have. `alphafold3` resolves to commit
  `c121cd877ae3d9ac62922f0f8bedde7179bb39b1`.
- **The JAX layer is already proven on this card by a sibling provider.**
  AP Novo pins `jax==0.10.2` and `tokamax==0.0.12`, which is exactly the stack
  `af3_jax` verified here. Its recorded shared-memory wall and the
  `--tokamax_autotuning_cache_miss_fallback=autotune` fix are expected to apply
  to this provider's folding stage; that has **not** been confirmed yet.
- **The environment builds and drives the card.** The 72-package lock installs
  into a CPython 3.12.13 venv on aarch64, `alphafold3`'s C++ extension compiles
  from source, and the pinned stack reports `jax.default_backend() == "gpu"`
  with `CudaDevice(id=0)`, `device_kind` "NVIDIA GB10", `compute_capability`
  "12.1" — no PTX JIT message. `dm-haiku` 0.0.17, `rdkit` 2026.03.3 and
  `tokamax` 0.0.12 all land at upstream's hard pins.
- **One build-time fragility, and it is upstream's, not this machine's.**
  `alphafold3`'s extension has cifpp fetch Eigen from
  `gitlab.com/libeigen/eigen.git` **during the build**. A first attempt failed
  three retries with "GitLab is currently unable to handle this request"; an
  unchanged retry succeeded. So a failed environment step here may be a third
  party being briefly down rather than anything about the pins — retry before
  diagnosing. (The first diagnosis attempted, that CMake 4 had removed the
  deprecated `FetchContent_Populate` cifpp calls, was wrong; constraining
  `cmake<4` changed nothing.)

Not established, and the reason in each case:

- **All five setup steps pass, and the smoke exercises the resident worker.**
  `tu remote setup apnovo` reports preflight OK, environment present, kit
  cloned at the pin, weights 1/1 at their pins (0.5 GiB), and
  `smoke: OK — one prediction in 69s, peak reserved 2.0 GiB`. The harness's own
  measurement of the peak agrees with the 2.0 GiB this manifest declares, which
  was arrived at independently.
- **The weights gate was tested in both directions.** With the file absent and
  `APNOVO_ACCEPT_WEIGHTS_TERMS` unset the step reports
  `REFUSED (weights_fetch_refused)` and prints the terms and the fix; with the
  file present and the variable set it reports 1/1 at their pins.
  `generator.bin.zst` is 547,140,096 B, sha256
  `f023bed8d3222223f3e0f14db09bf802bbab35c077c582d0fee7904a38128928`.

Not established, and the reason in each case:

| claim | status |
|---|---|
| residency gain **through the socket** | **measured.** The acceptance suite ran twice through the worker socket and replayed held engines: 36.8 s against a 129.2 s cold rung at 1000 steps, and 2.0-2.2 s against a cold 73-144 s at the smoke's 50 steps. |
| the acceptance suite | **run twice, passed twice.** `verify_provider.py apnovo` with `--lengths 100,250,500,1000` and with `--lengths 100,500,1000,2000`, `--repeats 4` each: 12/12 answered per run, every one `produced=yes`, `peak_reserved_gib` 2.0 on every request of both. The rungs are denoising step counts, because that — not the design length — is what keys a rebuild here. |
| folding stage | **blocked on an entitlement question, not a technical one.** AP Novo's folding uses AF3 / AF3-LA weights, whose terms are separate from AP Novo's. `af3_jax` deliberately avoids them by converting public OpenFold3-preview2 weights instead. Which route this provider takes is the operator's decision and is not made here. It no longer blocks evaluation: `apnovo_ingest_folded` takes predictions made by a provider that has settled its own weights question and writes them where upstream's evaluation looks. |
| resequencing stage | **done, on the CPU.** It gets the third interpreter it needs; it runs on the CPU because torch below 2.7 drives no sm_121 part, which is measured rather than assumed. Measured: one 129-residue design in 12 s. Its two environment variables are optional, and the operation refuses by name without them. |

## Operations

| operation | GPU | needs weights |
|---|---|---|
| `apnovo_validate_motif` | no | no |
| `apnovo_generate_designs` | yes | AP Novo generator |
| `apnovo_resequence_designs` | no, CPU | LigandMPNN (MIT) |
| `apnovo_ingest_folded` | no | no |
| `apnovo_evaluate_designs` | no | no |

`apnovo_validate_motif` parses a motif CIF and `motif_str` with upstream's own
`MotifSpec` and reports resolved segment lengths, fixed atoms and ligand
chains. It exists because a malformed `motif_str` otherwise surfaces only after
the generation stage has spent GPU-hours.

## Layout

```
provider.toml                       the declaration
apnovo_tool.py                      MCP server, CPU only, no model imports
resident/apnovo_resident_worker.py  holds the model, serves a Unix socket
environment/requirements.lock       complete freeze, installed --no-deps
smoke/input.json                    smallest input that exercises generation
```

## TOU validation and deployment status (2026-08-16)

> AlphaProtein Novo generated designs on the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) with upstream's own code at commit e7ce276, kit mode `off` because there is no optimization kit for it. **Measured: the peak is set by the model's one fixed input shape and not by the step count** — `peak_pool_bytes` was 2,145,386,496 at 50 denoising steps and the same 2,145,386,496 at the published 1000, so the declared 2.0 GiB budget does not move with the setting a caller is most likely to change. Residency at the published 1000 steps is **5.3x**: one 2-design request measures `per_design_s = [193.14, 36.55]`, so 193.1 s for the design that pays the XLA compile and 36.6 s for the one that reuses it. At 50 steps the same pair is 158.5 s and 1.99 s — far larger, because compilation dominates at 50 steps and real compute dominates at 1000. **Plan with the figure at your own step count**, and note that the axis is the step count rather than the design length: a second campaign at a different step count is cold again however many designs preceded it. *(An earlier version of this line said 79.3 s cold / 18.8 s held / 4.2x at 1000 steps. That pair does not reproduce; the 50-step pair does.)* What is held is the Haiku parameter set and upstream's per-(steps, partial_steps) compiled trajectory. **This provider is not a port of upstream's whole pipeline**: it serves motif validation, generation, resequencing and evaluation, and deliberately omits FOLDING, because AlphaFold 3 weights carry terms separate from AP Novo's and that question is unsettled here. Upstream's evaluation does not fall back to the metrics that need no prediction — it finds no folding seed in a design's metadata and refuses the whole run — so a campaign still has to be folded before it can be scored. **That no longer makes the operation unreachable, and part of why it was unreachable was ours:** `_evaluate` passed `--input_dir=01_generation` against a flag whose help says "Directory with the output of run_alphafold.py", so a folded campaign failed in exactly the same way as an unfolded one. The worker now reads `03_folded`, and `apnovo_ingest_folded` writes that stage from predictions made by any provider that has settled its own weights question — `openfold3`, `protenix_v1`, `esmfold2`, `chai1` and `rosettafold3` ship on this same standard. **MEASURED END TO END on 2026-10-15, on this GB10.** Generate -> fold -> ingest -> evaluate, all four stages through their MCP endpoints:

| stage | what ran | result |
|---|---|---|
| `apnovo_generate_designs` | upstream's `kemp_test_manifest.json`, 2 designs, 50 denoising steps | 160.5 s total: **158.52 s cold, 1.99 s held — residency is 79x at this setting**, where compilation dominates. `peak_reserved_gib` 2.0, matching the declared budget exactly |
| `protenix_v1_fold` x4 | each design's `monomer` and `complex` states, the latter with the derived ligand `CCD_6NT` | pLDDT 90.44 / 94.71 / 92.46 / 94.61; the complexes score ipTM **0.9285** and 0.7850 |
| `apnovo_ingest_folded` | the four predictions | 4 states written, `designed_cifs_missing: []`, `seed_gaps: []` |
| `apnovo_evaluate_designs` | `eval_suite: kemp_eliminase` | `status: ok`, 2 designs, **547 metrics each**, families `['complex', 'monomer', 'sampled', 'sequence']` |

kemp_0000 scored `monomer/tm_score` **89.47**, `monomer/rmsd` **1.596 Å**, `monomer/gdt_ha` 62.60, `complex/motif_allatom_rmsd` 1.733 Å, `sampled/num_missing_motif_residues` **0** and zero ligand-backbone clashes; kemp_0001 scored tm_score 92.66 and rmsd 1.428 Å. **The reaction suite ran**: 68 of those metrics are kemp-specific, including the catalytic geometry it exists to measure — `complex/acid_base/distance` 6.086 Å and `complex/acid_base/angle1` 83.78 deg. Protenix's own confidence record arrives as `complex/plddt`, `/ptm`, `/iptm` and `/ranking_score`, which is the pass-through this design promised.

So the state-prefixed families and the published threshold sets ARE reachable here, through a sibling provider. `verify_provider.py` **has now run**, twice, with two different ladders: 12/12 requests answered each time, every one `produced=yes`, and `peak_reserved_gib` 2.0 on every request of both runs — so `status` is `verified`. The rung is a denoising step count rather than a design length, because every design pads to one fixed shape and what keys a rebuild is upstream's `(sampling_steps, partial_steps)` trajectory cache; a length ladder here would have compiled one engine and printed four greens. See `provider.toml`'s `verified_on` for the figures and for the residency number it corrects. **Scientific quality remains unvalidated** — an acceptance measures that the provider answers, holds and rebuilds, not that its designs are good. The weights are licensed for non-commercial use by non-commercial organisations and must not be redistributed; public publication, cross-user isolation, concurrency and recovery are unvalidated. Keep this deployment private.

- Operation: `apnovo_validate_motif`
- Start: `python -m tooluniverse.remote.apnovo.apnovo_tool`
- Endpoint: `http://127.0.0.1:8059/mcp`
- Provider configuration: this provider is on the remote-tool standard, so the
  model runs in its own environment built from a pinned lock, and the generator
  weights are declared with a size and a sha256 and verified before the worker
  starts. Keep provider data, weights, caches and credentials outside Git, and
  do not place these weights on shared storage — the licence grants them to one
  individual or to one organisation's representative, not to a host's users.
  Use one worker: the resident worker serves one request at a time by design,
  and a second in-flight request queues on its lock rather than doubling peak
  VRAM. The measured VRAM budget is 2.0 GiB, and it is the figure for
  every design this provider can accept rather than for one bucket among
  several: upstream pads every design to one fixed 512-residue shape, so a
  longer design does not use more VRAM — it is **refused**. Co-tenant against
  2.0 GiB without reserving headroom for growth that cannot happen.
- TOU check: `tu doctor --forward http://127.0.0.1:8059/mcp --json`
- Private relay: `tu serve --share --forward http://127.0.0.1:8059/mcp --name validation-apnovo --workers 1`

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the
server on loopback. The relay requires `TOOLUNIVERSE_SERVICE_KEY`. Public
publication and independent-caller testing were not run — and for this provider
that is a licence matter as well as an evidence one, since serving callers whose
eligibility is unknown does not satisfy the non-commercial restriction.

New-user check: `python scripts/remote_validation/setup_skill_preflight.py
--implementation apnovo`. Add `--check-provider-env` before launch, `--live`
after launch, and `--check-connect-prereqs` before sharing. Live preflight
checks exact MCP discovery only; it does not run or validate a model.

The authenticated 2026-08-16 Platform matrix imported each implementation it
covered as unpublished owner draft(s), configured a 120-second timeout, and
invoked it through `/expert-sessions/{id}/test`. **This implementation was
added after that matrix and was not part of it**, so none of that evidence
covers it: it has not been exercised through the Platform at all, and
everything above was measured locally, on one card, through the loopback
endpoint. Public publication, independent-caller authorization/isolation, broad
saturation and persistent supervision are unvalidated here.

## Authorize once, then share with one short command

Log in once per machine, and again after key rotation:

```bash
tu remote login
```

`tu remote login` requests a short-lived device code, opens the TU Platform
approval page and polls until the signed-in user approves; no key is copied or
pasted. On a headless machine add `--no-browser`. Then each private share is
one command:

```bash
tu remote share apnovo
```

Override the reviewed name and worker count only when needed:

```bash
tu remote share apnovo --name my-apnovo-remote --workers 1
```

In an interactive terminal, sharing starts the same browser flow when the key
is missing, expired, or revoked. A malformed or revoked explicit
`TOOLUNIVERSE_SERVICE_KEY` fails fast rather than being silently replaced;
unset or correct it and run `tu remote login` again. `tu remote logout` removes
only the local copy; `tu remote logout --revoke` revokes the computer-only
platform connection first.

**Sharing this provider is not like sharing the others.** The relay makes it
reachable by whoever holds the link, and the weights licence restricts who may
use the model and whose Input it may process. Share it inside an eligible
organisation or not at all.

See the [complete setup and verification guide](../../../../skills/setup-apnovo-remote-tool/SKILL.md).
The skill is the whole guide for this provider — how to build the two
environments, what `tu remote setup`'s five steps each prove, every refusal
name with its fix, and the measured numbers a host schedules on. This file
carries the deployment contract and deliberately does not restate it, because
two copies of a procedure drift and only one of them gets corrected.
