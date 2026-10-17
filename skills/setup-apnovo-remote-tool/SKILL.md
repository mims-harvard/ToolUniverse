---
name: setup-apnovo-remote-tool
description: Set up, launch, validate, and troubleshoot the AlphaProtein Novo (de novo enzyme design) ToolUniverse remote tool. Use when deploying or auditing this implementation.
---

# Set up AlphaProtein Novo as a remote tool

> Validation status (2026-10-16): **`verified`.** The acceptance suite has now run twice, 12/12 requests answered each time with `peak_reserved_gib` 2.0 on every one; see `provider.toml`'s `verified_on`. Earlier status (2026-10-06): all five setup steps pass. On the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02): `tu remote setup apnovo` reports preflight OK, environment present, kit at the pinned commit, weights 1/1 at their pins, and `smoke: OK — one prediction in 69s, peak reserved 2.0 GiB`, which agrees with the manifest's independently measured budget. The weights refusal was tested in both directions. Residency is **5.3x** at the published 1000 denoising steps (193.1 s for the design that pays the XLA compile, 36.6 s for the one that reuses it) and far larger at 50 steps (158.5 s and 1.99 s), where compilation rather than compute dominates — plan with the figure at your own step count. Folding and resequencing are deliberately not part of this provider. What has been established on
> the NVIDIA GB10 (aarch64, cc 12.1, driver 580.173.02) is the environment and
> the no-weights path: the 72-package lock installs natively, `alphafold3`'s C++
> extension builds from source, the pinned stack reports
> `jax.default_backend() == "gpu"` on `CudaDevice(id=0)` "NVIDIA GB10"
> cc 12.1, and a design manifest validates and its motif spec parses with no
> weights and no GPU. The generator weights have been fetched and their sha256
> recorded. **Not** established: the residency gain, the acceptance suite, and
> scientific quality. Folding and resequencing are deliberately not part of this
> provider — see the provider README for why. Keep this deployment private.

**Read `src/tooluniverse/remote/apnovo/README.md` before deploying.** This
provider's weights are licensed for non-commercial use by non-commercial
organisations only and must not be redistributed, its Output carries terms, and
citation is a licence condition. That is a deployment constraint, not a
footnote: a public or mixed-audience deployment does not satisfy it.

## Prerequisites

- Run from the ToolUniverse repository root on Linux with Python 3.12.
- A CUDA GPU is required. The model is held resident between requests; CPU is
  not a target.
- Keep provider data, weights, caches and credentials outside Git.
- Bind to loopback. A non-loopback bind requires `TOOLUNIVERSE_API_TOKEN`;
  never put it in arguments or results.

Run the standard-library contract check before downloading anything large:

~~~bash
python scripts/remote_validation/setup_skill_preflight.py --implementation apnovo
~~~

After exporting provider resources add `--check-provider-env`; after the server
starts add `--live` to verify the MCP tool set without running the model.

## Create the two environments

The MCP server runs in ToolUniverse's environment; the model runs in its own,
built from a pinned lock. They cannot import each other, and that is the point.

~~~bash
python3 -m venv .venvs/apnovo
. .venvs/apnovo/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install fastmcp
~~~

The model half lives where `TOOLUNIVERSE_APNOVO_PYTHON` points, and nothing
above creates it. Create an empty interpreter first; `tu remote setup --only
environment` fills it from
`src/tooluniverse/remote/apnovo/environment/requirements.lock` with `--no-deps`,
so no version is silently resolved to something else.

~~~bash
python3 -m venv ~/apnovo-venv            # NOT `uv venv` -- see below
export TOOLUNIVERSE_APNOVO_PYTHON=~/apnovo-venv/bin/python
export APNOVO_WEIGHTS_ROOT=~/.apnovo
~~~

**Use `python3 -m venv`, not `uv venv`.** The kit step installs upstream
editable with `{python} -m pip`, and `uv venv` does not put pip in the
interpreter it creates, so the kit step fails with `No module named pip` after
the environment step has already reported `present`. If you have such a venv
already, `~/apnovo-venv/bin/python -m ensurepip --upgrade` repairs it in place.

**Two things about this lock before it runs.**

The jax layer is the half that was hardest to prove on this class of card, and
it is already proven: AP Novo pins `jax==0.10.2` and `tokamax==0.0.12`, exactly
the stack the sibling `af3_jax` provider verified here. All 13
`nvidia-*-cu12` wheels resolve natively at CUDA 12.9.x with cuDNN 9.27.0.42, and
nothing in the lock is pinned by an x86-64 direct URL.

`alphafold3` is a **git dependency with a C++ extension, and its build fetches
Eigen from gitlab.com during the build.** A first attempt here failed three
retries with `fatal: remote error: GitLab is currently unable to handle this
request`; an unchanged retry succeeded minutes later. **Retry before
diagnosing** — and do not repeat the wrong turn this took: constraining
`cmake<4` on the theory that CMake 4 had removed cifpp's deprecated
`FetchContent_Populate` calls changed nothing, because that was not the problem.

`build_data` then compiles alphafold3's CCD (`ccd.pickle` and
`chemical_component_sets.pickle`); ligand parsing fails without it. If
`components.cif` cannot be found, set `LIBCIFPP_DATA_DIR` to its directory
first. The kit step runs this.

## The third environment, for resequencing

`apnovo_resequence_designs` runs LigandMPNN, which pins `torch==2.2.1`,
`triton==2.2.0` and CUDA 12.1 wheels. That cannot share an interpreter with
this provider's jax stack, so it gets its own — which is how upstream's
`run_ligandmpnn.py` already works, by invoking a separate `--python_executable`.

**It runs on the CPU, and on this card it has to.** torch below 2.7 drives no
sm_121 part: 2.5.1 reports `cuda.is_available() True`, warns that sm_121 is not
in its arch list, then raises `no kernel image is available` on the *first*
device allocation, and `cuobjdump` shows its `libtorch_cuda.so` carries cubins
sm_50..sm_90a and no PTX to JIT from. PyPI publishes no CUDA aarch64 torch below
2.7 at all.

So install the **CPU-only** wheel at upstream's own pin. This is not a
preference: LigandMPNN's `run.py` picks its device with
`torch.cuda.is_available()`, so a CUDA build here would make it select the card
and die on the first allocation, with a message about kernel images rather than
about devices.

~~~bash
uv venv --python 3.11 ~/ligandmpnn-venv
git clone https://github.com/dauparas/LigandMPNN.git ~/LigandMPNN
# upstream's requirements minus its CUDA 12.1 wheels, which do not exist for
# aarch64 and which we deliberately do not want
grep -v '^nvidia-\|^triton==' ~/LigandMPNN/requirements.txt > /tmp/lmpnn-reqs.txt
VIRTUAL_ENV=~/ligandmpnn-venv uv pip install -r /tmp/lmpnn-reqs.txt "setuptools<82"
export LIGANDMPNN_DIR=~/LigandMPNN
export TOOLUNIVERSE_LIGANDMPNN_PYTHON=~/ligandmpnn-venv/bin/python
~~~

`setuptools<82` is upstream's own note: ProDy imports `pkg_resources`, which 82
removed. Verify the one fact that matters before going further:

~~~bash
~/ligandmpnn-venv/bin/python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
# 2.2.1 None False   <- `None False` is the point
~~~

The checkpoint is fetched by the weights step along with the generator's, under
`$APNOVO_WEIGHTS_ROOT/ligandmpnn/`. It is **MIT licensed**, so unlike the
generator it is not behind the acceptance gate — its terms are not AP Novo's.

Both environment variables are **optional**. Left unset the provider still
starts and the other three operations work; `apnovo_resequence_designs` then
refuses by name and says which of the three pieces is missing. Measured: one
129-residue design resequenced in 12 s on the CPU.

**Why bother.** Resequencing is the input to the strongest filter in the paper.
Hold a backbone, generate 7-10 sequences for it, and score the *backbone* by how
many of them pass your filter set: multi-resequence scoring was worth 2.5x
(Kemp) to 5.4x (serine esterase) at 50% recall retrospectively, and up to 30x
prospectively. `num_sequences: 1` is the default pipeline; MR needs 7 to 10.

## Accept the weights terms, explicitly

`tu remote setup apnovo --only weights` **refuses by design** until you accept:

~~~
[apnovo] NOT ACTIVE reason=weights_terms_not_accepted
~~~

The refusal prints the terms and the two policy URLs. There is no credential to
supply and no form to post — the gate is contractual, not technical, which is
why it is an acceptance you make rather than a side effect of running setup:

~~~bash
export APNOVO_ACCEPT_WEIGHTS_TERMS=1
~~~

Set this only if your organisation is a non-commercial organisation as the
terms define it. The fetch then downloads `generator.bin.zst` (547,140,096 B,
sha256 `f023bed8…128928`) into `$APNOVO_WEIGHTS_ROOT/apnovo_generator/`, and the
weights step verifies both. A short or off-pin file is named and the launch
stops; nothing is fetched at request time.

**Do not relocate these weights to shared or group-readable storage, and do not
mirror them.** Google grants access either to one individual for their own use,
who may not share their copy, or to an authorised organisational representative
who may share it within that organisation.

## Run setup

~~~bash
tu remote setup apnovo
tu remote check apnovo
tu remote run   apnovo
~~~

Five steps, each idempotent and each reporting `present` when it has nothing to
do: preflight → environment → kit → weights → smoke. Each refuses by name and
carries its fix. `check` is part of the normal path, not a debugging step: run
it before the first `run` and after anything changes.

## Operations

| operation | GPU | weights | what it does |
|---|---|---|---|
| `apnovo_validate_motif` | no | no | parses a motif CIF + `motif_str` with upstream's own `MotifSpec`; reports fixed atoms, ligand chains, whether conditioning is indexed |
| `apnovo_generate_designs` | yes | AP Novo | runs the diffusion generator over a campaign manifest |
| `apnovo_resequence_designs` | no (CPU) | LigandMPNN | LigandMPNN over a campaign's backbones, in a third interpreter |
| `apnovo_ingest_folded` | no | no | writes predictions from elsewhere into the campaign as upstream's folded stage |
| `apnovo_evaluate_designs` | no | no | runs upstream's metrics over a folded campaign |

`apnovo_validate_motif` exists because `motif_str` is the field that silently
wastes GPU-hours: a malformed one is otherwise only visible after generation.
Run it first, always.

**`apnovo_evaluate_designs` needs a folded campaign, and this provider does not
fold.** Upstream's evaluation does not fall back to the metrics that need no
structure prediction: it reads each design's metadata, finds no folding seed,
and refuses the run —

~~~
ValueError: …/metadata/kemp_0000_metadata.json records no folding seed for
kemp_0000 in …/01_generation, so it describes a design that has not been folded
~~~

Read that message closely, because **half of it was our bug**. It names the
directory it searched, and `01_generation` is the wrong one: the flag's own
help says "Directory with the output of run_alphafold.py", and
`_discover_folded_designs_for_metadata` looks for
`<sample>_<state>_confidences_seed<n>.json` inside the directory it is given.
A generation stage holds none, so a campaign that HAD been folded failed in
exactly this way too, and the two causes were indistinguishable. Fixed: the
worker now reads `03_folded`.

The other half is real and stays: the structures have to come from somewhere,
and that somewhere is not this provider while the AlphaFold 3 weights question
is unsettled. **`apnovo_ingest_folded` closes it.** Fold each design's states
with any predictor that has settled its own weights question — `openfold3`,
`protenix_v1`, `esmfold2`, `chai1` and `rosettafold3` are five on this same
standard — and post the mmCIF text:

```json
{
  "run_dir": "/path/to/campaign/returned/by/apnovo_generate_designs",
  "states": [
    {
      "sample_name": "kemp_0000",
      "state": "apo",
      "seed": 0,
      "folded_cif": "data_kemp_0000\n_entry.id kemp_0000\n",
      "designed_cif": "kemp_0000.cif"
    }
  ]
}
```

Then call `apnovo_evaluate_designs`. Two rules the layout imposes, both read
from `design_manifest.py` at the pinned commit rather than guessed: **seeds
must be contiguous from 0**, because upstream counts up and stops at the first
gap (the response reports any gap it would hit), and the **first state of each
design must carry `designed_cif`**, because upstream refuses a design whose
first confidence record names no structure to score against. Every other key
in `confidences` is carried through into the metric row, so a sibling's pTM,
ipTM and pLDDT arrive without any mapping here.

**This path has been run.** On 2026-10-15, upstream's `kemp_test_manifest.json`
at 2 designs / 50 steps, folded by `protenix_v1` (both derived states, the
complex with ligand `CCD_6NT`), ingested and scored: `status: ok`, 2 designs,
**547 metrics each**, families `['complex', 'monomer', 'sampled', 'sequence']`,
of which 68 are kemp-suite metrics including `complex/acid_base/distance`
6.086 A. kemp_0000: `monomer/tm_score` 89.47, `monomer/rmsd` 1.596 A, zero
missing motif residues. The confidence pass-through is visible as
`complex/plddt` 94.71 and `complex/iptm` 0.9285.

Two things to know when you fold with a sibling. The predicted mmCIF of a
130-residue monomer is ~100 KB, and **a tool result is capped at 100,000
characters** by the transport before falling back to raw truncation -- which
corrupts the JSON rather than shortening it -- so ask the folding provider for
`out_dir` and read the files from disk, not for `return_structures`. And
`apnovo_evaluate_designs` reports `eval_suite_skipped`: upstream SKIPS a
reaction suite it cannot compute, with a warning rather than an error, so an
empty list there is what tells you the suite actually ran.

## Troubleshooting

**`weights_terms_not_accepted`** — intended. See above.

**The environment step fails in `alphafold3`'s build.** Read the error before
acting. If it names `gitlab.com` or Eigen, retry unchanged. If it names the
compiler or `cifpp` itself, that is a different problem.

**`jax.default_backend()` is `"cpu"`.** The `verify` line in `provider.toml`
asserts `gpu` and will refuse the environment. Check the driver first: this card
needs the 580 series for `sm_121` to be enumerated at all.

**A shared-memory error from XLA, with an invariant byte count.** Expect this
class on this card: a kernel tuned for a part with more shared memory per block
than this one has. `af3_jax` hit it at 110,592 bytes against 101,376 available,
and the fix was upstream's own flag,
`--tokamax_autotuning_cache_miss_fallback=autotune`. If three attempts to switch
a suspect off leave the number byte-identical, that is a statement about where
the culprit is not — do not read it as three dead ends.

**`nvidia-smi` reports `[N/A]` for memory.used.** Correct on this unified-memory
part, and the reason a VRAM figure here comes from JAX's own
`memory_stats()["peak_bytes_in_use"]` rather than from `nvidia-smi`. A JAX
provider's budget is not in the same column as a torch provider's.

## Before claiming `verified`

~~~bash
python scripts/remote_validation/verify_provider.py apnovo
pytest tests/unit/test_remote_schema_parity.py tests/unit/test_remote_setup_preflight.py \
       tests/unit/test_remote_runtime.py tests/unit/test_remote_resident.py -q
~~~

`status = "verified"` additionally needs `verified_on` naming this hardware, and
a `vram_budget_gb` that was measured rather than guessed. One smoke request is
not a test of a provider that holds state between requests.

## Start and verify locally

~~~bash
python -m tooluniverse.remote.apnovo.apnovo_tool
~~~

The Streamable HTTP endpoint is http://127.0.0.1:8059/mcp. In a second activated shell run:

~~~bash
python - <<'PY'
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://127.0.0.1:8059/mcp") as client:
        print([tool.name for tool in await client.list_tools()])

asyncio.run(main())
PY
~~~

Confirm discovery contains apnovo_validate_motif, apnovo_generate_designs and
apnovo_evaluate_designs; stop on empty, duplicate, or schema-drifted discovery.

The first request at a given **step count** pays the XLA compile; the ones
after it do not. **The axis is the step count, not the design length.**
Upstream pads every design to one fixed 512-residue shape, and caches the
compiled trajectory in `functools.lru_cache(maxsize=8)` keyed on
`(num_sampling_steps, num_partial_diffusion_steps)` — so a second campaign at
a different step count is cold again however many designs preceded it, and a
ninth distinct step count evicts the first. Measured at the published 1000
denoising steps, as the two designs of one request: 193.1 s for the design
that pays the compile and 36.6 s for the one that reuses it. At 50 steps the
same pair is 158.5 s and 1.99 s. **Benchmark at the step count you will
actually run** — a ratio
measured at 50 steps says almost nothing about one at 1000, and this provider's
own figures differ by more than an order of magnitude between them.

## Connect to ToolUniverse Connect

The `tuplatform-connect` relay is not yet published on PyPI. Install the
reviewed public wheel below; its SHA-256 is pinned. Interactive sharing uses
browser device authorization, so no key copy/paste is required.

~~~bash
python -m pip install fastmcp pyyaml "tuplatform-connect @ https://connect.aiscientist.tools/downloads/tuplatform_connect-0.3.0-py3-none-any.whl#sha256=3fad5eee5ecf7887a693d93ccd1aa112dc0955617a885d1fc3daded0030f9ae0"
tu doctor --forward http://127.0.0.1:8059/mcp --json
tu serve --share --forward http://127.0.0.1:8059/mcp --name validation-apnovo --workers 1
~~~

Authorize once per machine, then share with one command:

~~~bash
tu remote login
tu remote share apnovo
~~~

Override the reviewed name and worker count only when needed:

~~~bash
tu remote share apnovo --name my-apnovo-remote --workers 1
~~~

Sharing starts the browser flow when the key is missing, expired, or revoked. A
malformed or revoked explicit `TOOLUNIVERSE_SERVICE_KEY` fails fast rather than
being silently replaced. `tu remote logout` removes only the local copy;
`tu remote logout --revoke` revokes the computer-only platform connection
first.

**Think before sharing this one.** The relay makes the model reachable by
whoever holds the link, and the weights licence restricts who may use it and
whose Input it may process to eligible non-commercial organisations. Share it
inside such an organisation, or not at all.

This implementation was added after the authenticated 2026-08-16 Platform
matrix and was not part of it. That matrix imported each implementation it
covered as unpublished owner drafts and invoked them through
`/expert-sessions/{id}/test`; this provider was imported as no such draft and
invoked through no such route. It has not been exercised through the Platform at
all: the evidence above is local, on one card, through the loopback endpoint.
Public publication, independent-caller authorization/isolation, saturation and
persistent supervision are untested.

## Run a verified example

Operation: apnovo_validate_motif

~~~json
{"manifest": "{\"defaults\": {\"num_designs\": 1, \"seed_start\": 0, \"num_sampling_steps\": 1000}, \"designs\": [{\"name\": \"kemp_eliminase\", \"output_prefix\": \"kemp\", \"input_file\": \"motif.cif\", \"motif_str\": \"A1,A2|10-100,{},2-80,{},10-100/B1\", \"motif_atoms\": \"A1:OE2,OE1,CD,CG A2:OG,CB,CA\", \"seq_length\": \"120-160\", \"is_author_naming\": false}]}", "files": {"motif.cif": "data_motif\n# the transition-state motif, mmCIF\n"}}
~~~

This one is deliberately the cheapest operation: it parses the manifest and
every design's motif spec and touches neither the weights nor the card, so it
is the right first call after `tu remote run` and the right first call of any
campaign. Replace `files["motif.cif"]` with your real motif mmCIF — the stub
above is shaped to the schema, and a real motif carries the catalytic
side-chain atoms and the ligand.

**This example has been run through the live endpoint**, with the stub replaced
by the real Kemp eliminase motif mmCIF. `list_tools` returned all three
operations, and the call came back `{"status": "ok", "designs":
[{"name": "kemp_eliminase", "indexed_conditioning": true,
"partial_diffusion": false, "parsed_at_seeds": [0, 1, 2]}], ...}`. With the stub
CIF above the call is schema-valid but will not parse as a motif, which is why
replacing it is the first thing to do.

Invoke it through the live local MCP endpoint:

~~~bash
python - <<'PY'
import asyncio
import json
from fastmcp import Client

async def main():
    arguments = json.loads(r'''{"manifest": "{\"defaults\": {\"num_designs\": 1, \"seed_start\": 0, \"num_sampling_steps\": 1000}, \"designs\": [{\"name\": \"kemp_eliminase\", \"output_prefix\": \"kemp\", \"input_file\": \"motif.cif\", \"motif_str\": \"A1,A2|10-100,{},2-80,{},10-100/B1\", \"motif_atoms\": \"A1:OE2,OE1,CD,CG A2:OG,CB,CA\", \"seq_length\": \"120-160\", \"is_author_naming\": false}]}", "files": {"motif.cif": "data_motif\n# the transition-state motif, mmCIF\n"}}''')
    async with Client("http://127.0.0.1:8059/mcp") as client:
        result = await client.call_tool("apnovo_validate_motif", arguments)
        print(result)

asyncio.run(main())
PY
~~~
