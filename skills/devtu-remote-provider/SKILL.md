---
name: devtu-remote-provider
description: Bring up, standardise or debug a GPU-backed ToolUniverse remote tool in src/tooluniverse/remote/<slug>/ — the provider.toml manifest, the resident model worker, wrapping a third-party optimization kit, and reading what `tu remote setup` refuses. Use when adding a self-hosted model provider, converting one from per-request subprocess to resident, diagnosing a setup or launch refusal, or reviewing a provider against the standard.
---

# ToolUniverse remote provider

A remote tool is a model you host yourself, exposed over MCP. The contract lives
in `src/tooluniverse/remote_resident/STANDARD.md`; read it before changing a
provider. This page is how to apply it and how to read what it refuses.

## The shape

```
agent ──MCP──> remote/<slug>/<slug>_mcp_server.py     ToolUniverse's env, CPU only
                      │
                      │ Unix socket, one request at a time
                      ▼
               remote/<slug>/resident/<slug>_worker.py   the model's own env
```

Two environments because their pinned stacks conflict. Boltz-2 needs torch
2.12.0+cu130 / triton 3.7.0 / numpy 1.26.4, which cannot be installed alongside
ToolUniverse's other 1000+ tools. **The MCP server must not import the model's
dependencies, and the worker must not import ToolUniverse** — the shared surface
is one dependency-free file (`remote_resident/protocol.py`) loaded by path.

## Top mistakes

1. **Requiring the model's CLI at tool construction.** `shutil.which("boltz")`
   in `__init__` fails on a correctly separated deployment. Accept either route.
2. **Trusting weights because the download exited 0.** A `boltz2_conf.ckpt`
   arrived as 1.2 % of itself and served predictions for a month. Declare
   `size` and `sha256`; nothing is fetched implicitly at request time.
3. **Starting the model per request.** Measured on a GB10: 110 s per call as a
   subprocess, ~54 s held. Most of the difference is not kernels — it is CUDA
   graphs captured on one request and replayed on the next, which a worker that
   exits cannot collect.
4. **Letting a worker outlive its server.** `start_new_session=True` keeps a
   Ctrl-C from killing a prediction, and also orphans the worker; SIGKILLing the
   MCP server left two processes holding the GPU. Workers need the idle timeout
   *and* the orphan watchdog.
5. **Claiming `status = "verified"` without hardware.** It must carry
   `verified_on`. A bare "verified" claims every machine.
6. **Hashing gigabytes on every check.** Use the digest memo; pass `deep=True`
   only in setup, where what is certified should have been read.
7. **Forgetting package data.** A built wheel carries only `.py` under
   `remote/`. Provider JSON, `provider.toml`, lock files, smoke inputs and the R
   halves of R-backed providers need globs in `pyproject.toml`.
8. **Believing exit 0.** OpenFold3's smoke exited 0 in 29 s, reported a GPU
   peak, and produced no structure: upstream caught the per-query exception,
   wrote "Failed Queries: 1" to a summary file and returned normally. Declare
   `[runtime] outputs` (globs) or `output_keys` (reply fields); the manifest
   refuses `status = "verified"` without one and the smoke step refuses when
   nothing matched.
9. **Quoting a budget from the smoke.** RFdiffusion3's 60-mer smoke reserves
   2.12 GiB; a 400-residue, 4-design request reserves 12.49. When peak tracks
   input size, measure a ladder and declare the envelope alongside the number.
10. **Forking a loader out of a resident worker.** The parent has CUDA and the
   kit's threads initialised long before a request arrives. Set
   `num_workers = 0` unconditionally — it is a property of the resident route,
   not of one kit.
11. **Accepting a smoke as verification.** One request is not a test of a
   resident provider. openfold3 produced five real structures and then failed
   deterministically on the SECOND request of the same shape, because a lever
   dropped a CUDA graph on moved storage while keeping its emptied pool handle.
   Run **at least four consecutive identical requests**, then a mixed-shape
   sequence. Four *different* shapes pass on a build that cannot serve a repeat.
12. **Assuming `levers_off` reaches the kit.** boltzgen's `modes.py` never
   reads `MODEL_OPT_LEVERS_OFF`, and its `stack.activate()` overwrites a
   caller's value for any switch the mode exports. Check the ACTIVE line: if
   the lever is still listed the door did not open, and shipping the setting
   anyway is worse than saying so.
13. **Quoting wall times from a contended card.** The same fold read 15-19 s
   quiet and 28-56 s with another session on the GPU. Peak reserved reproduced
   to the hundredth of a GiB in both. Report peaks from any run; report wall
   times only from an idle card. **And utilisation alone is not evidence that
   YOUR process is computing** — a 40-minute boltzgen stall was read as progress
   because the card showed 86-91%, which belonged to someone else. The usable
   signal is utilisation *plus* `/proc/<pid>/stat` CPU, on a quiet card.
14. **Letting a library fork.** `num_workers = 0` covers the loader and nothing
   else. boltzgen's DataLoader worker sat in `torch.cdist` → `at::parallel_for`
   → an OpenMP region, alive and at 0% CPU, waiting on a pool `fork()` did not
   carry over — up only because the kit's levers had done host-tensor work
   during activation. The rule that covers all three observed shapes: **a
   resident worker that has run any host-tensor work must not let a library
   fork**, and `[kit.env] OMP_NUM_THREADS = "1"` is the cheapest guarantee.
15. **An `outputs` glob that matches a file written regardless of success.**
   boltzgen's `configure` writes `design_spec.cif` — a picture of the
   *specification* — whether or not anything is designed, so `*.cif` would have
   passed a run that produced nothing. Test the glob against a failing run, not
   only a passing one.
16. **Reading four identical requests as the acceptance test.** They are the
   WEAKER half. A held engine is built once and replayed, so N identical requests
   exercise exactly one build — they cannot show the worker can build a SECOND
   one. genie3 would have passed four and raised on the first request that
   changed its engine key, because upstream's sampling config is a module-level
   mutable permitting one build per process. Run four identical requests **then at
   least one that changes the engine key**; the rebuild is the danger, not the new
   shape. Before writing a worker, **call the upstream config or model builder
   twice in one process** — one minute, and invisible to the repeats test.
17. **An input ceiling that the budget cannot cover.** progen2's tool allowed 16
   sequences × 1024 tokens; each is sane, the product costs **116.93 GiB**,
   essentially the whole card. Bound the product, and check the ceilings against
   the budget rather than only against each other.
18. **Trusting a probe that does nothing afterwards.** protenix's stock LayerNorm
   emits SASS with no PTX above sm_100, so the call returns, `synchronize()`
   PASSES, and the *next unrelated* op raises `no kernel image is available`. The
   first probe printed "LAUNCH OK" twice because it stopped there.
19. **Assuming a wheel that installs will run.** tokenizers 0.10.x publishes
   well-formed aarch64 wheels that `Illegal instruction (core dumped)` at import.
   In a worker that is a `smoke_protocolerror` with no traceback, because SIGILL
   is uncatchable. Import every compiled pin in `[env] verify`.
20. **Assuming pip honours requirement order.** A lock with two CUDA generations
   gets whichever of a colliding pair pip reaches last — measured, `libcudnn.so.9`
   at 124,920 bytes instead of 6,328,728. Declare ordered passes with
   `# --- pass break ---`.
21. **Sizing an ablation to the smoke.** Every kernel lever of the atlasfold kit
   is gated at `min_tokens = 512`; its 35-residue smoke exercises none. Seven
   ablated levers fold 35 residues and abort at 600; thirteen fold both. Size
   the ablation for the largest input the provider accepts — and check whether
   stock itself survives that size, because atlasfold's does not.

22. **Surveying whether four locks install, when the deciding question was
   whether stock needs the card.** A gate script ranked flashzoi the cheapest of
   four candidates on 46 of 51 pins installing as pinned. The kit's own dry run
   on the host answered in one line — `would_refuse='no usable GPU: no CUDA
   device visible to torch (the stock needs a CUDA device as much as the kit)'`
   — and the full reason took two more commands: stock `borzoi_pytorch`
   imports `flash_attn.modules.mha` unconditionally
   (`pytorch_borzoi_transformer.py:151`, `use_flash_attn=True`), flash-attn
   ships **sdist only on PyPI at every version**, and 2.7.0.post2's `setup.py`
   emits `code=sm_80` and `code=sm_90` with no PTX, so even a from-source
   aarch64 build runs no kernel on an sm_121 card. Installing was never the
   deciding question. **The deciding one was already written down one section
   below, in a table that names flashzoi first among the kits whose pinned torch
   cannot drive this card** — so the survey restated my own notes and inverted
   their conclusion. Ask the host before the index: `run.sh check --mode <kit
   mode>` costs one command, needs no weights, and prints the refusal. Then ask
   it of *stock*, which is the row the table had been missing.

23. **A wheel that installs and contains nothing.** `tensorflow==2.15.1` has an
   aarch64 wheel on PyPI; its RECORD is **six lines of dist-info** and
   `Requires-Dist: tensorflow-cpu-aws ==2.15.1 ; platform_machine == "aarch64"`
   hands the real library to another distribution of the same version. With
   `--no-deps` -- which is how every lock on this standard installs -- that
   redirect is never followed, so the install succeeds, `pip list` shows
   `tensorflow 2.15.1`, and `import tensorflow` raises `ModuleNotFoundError`.
   A gate that asks "does an aarch64 wheel of this exact version exist" answers
   yes and is useless. Read `info.requires_dist` from the same PyPI JSON you
   already fetched and flag a platform-gated redirect to another name; the fix
   is to keep the pin and add that name beside it. At 2.17.1 the same project's
   aarch64 wheel is the real library (13,509 RECORD lines), so this is per
   version, not per project.

24. **Reading the pinned command instead of the option table it binds to.** The
   kit records borzoi's pinned invocation as `-u`, which reads as
   "untransform". `-u` is declared `dest='untransform_old'` with no help string
   (`borzoi_sad.py:98-103`), so the pinned run takes `untransform_preds1`, not
   `untransform_preds` -- a different function, different numbers. Two more in
   the same 500-line script: `--stats` and `--shifts` are both converted from
   strings to **lists** before use (`:158-159`), so passing the comma-joined
   string to stock's own writer makes `for sad_stat in sad_stats` iterate
   CHARACTERS and die on the second `S` with "name already exists", while
   passing `--shifts` as a bare int makes `build_ensemble` raise on `len()` --
   and that raise is the good case, because a signature that accepted it would
   have scored every variant without the reverse-complement average the pinned
   command asks for. And one the gate cannot see at all:
   `sum_length = (options.sad_stats == 'SAD')` at `:210` compares the already
   split **list** against a **string**, so it is always False, `build_sad()` is
   dead, and `write_snp_len` always runs. **Reproduce that bug rather than
   fixing it** -- the provider's claim is that it answers what stock answers --
   and note that no output comparison could have found it, because the pinned
   stats make the bug and a corrected version agree. Read the option table and
   the conversions; the command line is a summary, not the behaviour.

25. **Being the load you launched a measurement to escape.** Three borzoi pairs
   gave 1.19x, 0.97x and 1.01x while the host's load climbed 7.79 -> 22.88, so I
   started a balanced-order repeat to cancel the drift -- and then started the
   provider's acceptance run beside it, two 600-850 % CPU TensorFlow processes
   competing, which is the same contamination with me as its source. **Before
   timing anything, check `/proc/loadavg` AND your own background jobs, and
   serialise them.** The within-mode spread across nine runs (42-50 s) stayed
   larger than the between-mode difference (15 s), so the honest answer is "no
   ratio established" -- which is a result, and is what the provider records.

26. **Running the tests you remember instead of the directory.**
   `tests/unit/test_remote_runtime.py` went green for every provider on this
   standard, so it became the gate by habit. `tests/unit/test_remote_schema_parity.py`
   sits beside it, holds twenty tests, and had been **red since the commit that
   released opendde and colabdesign** -- both shipped with no
   `src/tooluniverse/remote/<slug>/README.md` at all, which that file checks and
   nothing else does. Running the whole directory also rejected three skills and
   three READMEs over a documented contract I did not know existed: eight
   **line-anchored** commands in the SKILL (`^python -m …`,
   `endpoint is http://127.0.0.1:<port>/mcp`, `^Operation: …`,
   `^> Validation status…`, and bare `tu doctor` / `tu serve --share` /
   `tu remote share` / `tu remote share … --workers N` lines), a published
   `src/tooluniverse/data/remote_tools/<slug>_tools.json` whose `parameter`
   schema the skill's `~~~json` example is validated against, a **frozen**
   `## TOU validation and deployment status (2026-08-16)` heading in the README
   (the date is the Platform-matrix evidence date, not the provider's), and
   sixteen required phrases across the two. **Two providers were released in a
   state the suite rejects.** And the directory held two more red modules that
   one file could never show: `test_remote_setup_preflight.py` rejected both new
   skills for omitting the shared
   `scripts/remote_validation/setup_skill_preflight.py` command, and
   `test_remote_tool_boundaries.py`'s boltz case had been red since **admission
   started probing the machine** (`5a8fbc72`) -- `run.assert_called_once()`
   counts the `ps` and two `nvidia-smi` probes, when the property it is for is
   that the *provider* command runs once. Three red modules, three different
   causes, none of them the file I was running. `pytest tests/unit` costs a few
   minutes; running one file costs a release.

## What eight verified providers cost, and where the time went

Every figure measured on one GB10 (aarch64, cc 12.1), held worker, steady state. "cold → warm" is
the first request against the later ones in ONE worker; peaks are declared at the envelope named.

| provider | activation | mode | cold → warm | peak reserved | what residency keeps |
| --- | --- | --- | --- | --- | --- |
| rfdiffusion3 | `.pth` + file overlay | fast | **19.4 → 1.6 s (12x)** | 12.49 GiB @ 400aa × 4 | compile trace + CUDA graph |
| esmc | `.pth` | **off** (needs flash-attn) | 0.69 → 0.076 s, build 142 s | 28.75 GiB @ 1600aa | 23.7 GiB of weights |
| chai1 | `.pth` | fast, `alloc` off | 67.6 → 25.7 s (2.6x) | 9.8 GiB | 6 TorchScript modules |
| esmfold2 | `.pth` | fast | 2.7 → 1.1 s | 25.28 GiB @ 800aa | 25.6 GiB of weights |
| boltz | `worker_launch` (1 of 36) | fast | 110 → 55 s (2.0x) | 5.54 GiB | checkpoint + featurizer |
| rosettafold3 | `.pth` + **patched tree** | fast | 20.7 → 16.1 s | 13.25 GiB @ 800aa | checkpoint + engine |
| openfold3 | `.pth` | fast, 2 gates | 18.8 → 15.2 s | 9.12 GiB @ 800aa | build + Triton compiles |
| enformer | `.pth` | **off** (x86-only objects) | in-process | 4.12 GiB | nothing to reload |

**The VRAM ladder's SHAPE matters as much as the number**, because it decides what a host can
co-tenant. Two families:

| | 100 aa | 800 aa | ratio | why |
| --- | --- | --- | --- | --- |
| esmc | 24.08 | 26.29 (28.75 @ 1600) | **1.19x** | a constant 6B parameter term dominates |
| esmfold2 | 14.14 | 25.28 | 1.8x | constant ESMC-6B term, plus a real trunk |
| openfold3 | 1.45 | 4.24 → 9.12 | 3.6x | N² pair track, small constant |
| rosettafold3 | 3.59 | 13.25 | 3.7x | N² pair track |

So esmc is a fixed ~29 GiB tenant for any sequence it will realistically see, while openfold3 fits
in 6 GiB if the host caps chains at 400 residues. Neither fact is derivable from parameter count.

**Derived estimates were wrong in both directions**, which is why the ladder is not optional:
openfold3's arithmetic said 16 GiB and measured 4.24 (3.8x high, wasting a card); esmfold2's said
16 and measured 25.28 (1.6x low, overcommitting one); esmc's said 14.5 and measured 24.07 — and
*that* one was right about `exact` and wrong only because this machine cannot run `exact`.

Ten providers attempted, eight verified, four shapes of activation (`.pth` autoload; `worker_launch`;
a replacement entry script; and autoload **plus a patched tree on disk**, which rosettafold3 verifies
by sha256 and which costs that provider `mode = "off"` entirely) and four answers to who holds the
weights (the worker; the kit; upstream's own memo; and boltzgen's **nobody** — upstream reloads
each pipeline step's checkpoint inside the step, so residency buys the process, not the weights).

Two manifest keys came out of that: `[kit] env_row`, because four of eight kits return an empty
environment row and "empty" means both "this kit keeps none" and "we failed to read one"; and
`[kit.env]`, for a kit's own documented knobs — a size gate, a cap — which `levers_off` cannot
express because they are not levers.

**Residency's payoff tracks the ratio of fixed cost to work, not the kind of fixed cost.** genie3
reaches 12x with no compile trace and no held-weights advantage over Boltz-2, purely because a
20-step 50-residue pass is shorter than the set-up it is compared against — a prediction made from
"what the kit does at import" alone was wrong by 6x. And residency **need not change the answer**:
genie3's four identical requests produce byte-identical PDBs, the only provider where that has been
shown rather than assumed, and only because the claim was written down falsifiably first.

Residency's payoff ranges 2.0x to 12x and the ranking does not follow model size — it follows what
the kit does at import and at first call, and how small the request is. RFdiffusion3 wins biggest because its `fast` mode traces
the denoiser through torch.compile and captures a CUDA graph, both per process; esmc wins on a
different axis entirely, because 142 s of weight reading buys a 0.076 s forward pass.

Nearly all the remaining time per provider goes on facts that have to be read out of the kit rather
than assumed, which is what the rest of this page is for.

## Adding a provider

```
src/tooluniverse/remote/<slug>/
├── provider.toml                    the declaration; see STANDARD.md
├── <slug>_client_tools.json         the MCP tool schemas
├── <slug>_mcp_server.py             thin, CPU-only
├── environment/requirements.lock    a complete freeze, installed --no-deps
├── resident/<slug>_worker.py        builds the model once, serves a socket
├── resident/launch.py               build_command(worker) -> (argv, env)
└── smoke/input.yaml                 the smallest input that exercises the path
```

Then `tu remote setup <slug>` → `tu remote check <slug>` → `tu remote run <slug>`.

Start `status = "untested"`. It becomes `verified` only after the smoke step has
run on hardware you then name in `verified_on`.

## Wrapping a third-party optimization kit

Anthropic's kits (`github.com/anthropics/uplifting-biomolecular-modeling`) are
referenced by pinned commit, never vendored: 473 MB, of which ~300 MB is
prebuilt kernels for architectures a given host may not even load, and their own
`pyproject.toml` says the install must stay editable.

**Wrap, do not patch.** Their launcher runs any script:

```
python -m <kit>_opt.worker_launch --route … --attach … -- your_worker.py …
```

so a resident worker is simply a different script in the position the kit's
batch worker occupies, and the kit's import hooks attach its levers to the model
your script builds. For Boltz-2 that is 25 of 28 levers; the three implemented
inside the kit's own worker script are forgone. Verify equivalence before
believing it: structure mean |dCA| and the affinity value should match the kit's
own `run.sh pred --mode <mode>` exactly.

Ask the kit for its own parameters rather than copying them — `launch.py` runs a
few lines in the *model's* interpreter to read `modes.resolve(mode)["env"]` and
`stack.launch_opts(...)`. A hard-coded copy drifts the first time the kit moves.

**An adapter in `--attach` whose switch is missing from the row refuses the whole
launch.** Keep the row intact and let the adapter decline by name instead.

## Choosing which kit to bring up

The thirty-six upstream kits are uniform in structure and varied in the three
things that decide whether one runs on a given machine. Read each before
committing to a download:

| question | how many fail it | what `setup` does |
| --- | --- | --- |
| Can its pinned torch drive this card? | 6 pin torch < 2.7 (sm_90 ceiling): proteinmpnn and flashzoi 2.5.1, caliby 2.6.0, rfdiffusion1 and esm_if1 2.4.0, pxdesign 2.3.1 — two of them by direct URL, so resolve the URL before counting; borzoi and chrombpnet are TensorFlow and have their own floor | refuses `torch_arch_unsupported` after install, by binary compatibility — an sm_120 cubin runs on sm_121 |
| …and when it cannot, does **stock** still run on the CPU? | proteinmpnn and caliby fall back (`device = "cuda" if torch.cuda.is_available() else "cpu"`); flashzoi does not — its own dry run says `no usable GPU … the stock needs a CUDA device as much as the kit` | nothing checks it: only `run.sh check --mode <kit mode>`, on the host, prints it as `would_refuse` |
| Does it carry prebuilt host objects? | 8 do; all 39 such files are x86-64, none aarch64 | refuses `kit_foreign_objects` from the ELF header, before installing |
| Does its lock pin an architecture by URL? | ~20 name a wheel by direct x86-64 link | ship a lock pinning by version instead, and say so in its header |
| How does it activate? | 30 by mode variable + `.pth`, 1 by `worker_launch` (boltz2), 1 not in-process at all (chrombpnet) | detected, not declared |

**Triton is a second toolchain, and a third party may be a third.** A stack whose
`torch.cuda.get_arch_list()` covers the card can still fail every kernel, in two separate places:
Triton's LLVM must know `sm_<cc>a` (3.3.x does not — a cross-lane reduction then aborts the process
uncatchably) and its bundled `ptxas` must target the card (3.4.0's does not — fixable with
`nvidia-cuda-nvcc-cu12==12.9.86`). `step_environment` now compiles one `tl.sum` kernel and reports
what happened, because the static reads are insufficient: atlasfold passed both and still died, since
**cuEquivariance ships Triton kernels of its own**. Note the env-var name is derived —
`TRITON_<BINARY>_PATH`, and `ptxas-blackwell` is selected above cc 100 — so `TRITON_PTXAS_PATH` alone
is the wrong name on every Blackwell-class card.

**On aarch64, the torch floor is harder than it looks — and the obvious reason for it is the
wrong one.** Six kits pin torch below 2.7. PyPI's `manylinux*_aarch64` wheels at 2.3.1 / 2.4.0 /
2.5.1 / 2.6.0 each carry `libtorch_cpu.so` and no `libtorch_cuda.so`, with every `nvidia-*`
dependency marked `platform_machine == "x86_64"` — but **do not stop at one index and call it the
world**: `download.pytorch.org` publishes CUDA aarch64 wheels at 2.4.0, 2.4.1 and 2.5.1 on its cu124
index. Those do not rescue the pin either, and their reason is the one worth knowing, because it is
the one a later kit will hit: `cuobjdump` on 2.5.1's 935 MB `libtorch_cuda.so` lists cubins
sm_50..sm_90a and **no PTX at all**, so the first device allocation — before any GEMM — raises
`no kernel image is available for execution on the device`. Forward PTX JIT cannot rescue what ships
no PTX. Measured on this GB10 (sm_121): the lowest aarch64 CUDA wheel that executes is
`torch-2.7.0+cu128` (`sm_90, sm_100, sm_120`, and an sm_120 cubin runs on sm_121); the cu126 index
answers 403 for the same version.

Four ways out, and the first two are not always open. Run the model on the CPU
(`[gpu] policy = "none"` — right rather than consolation for a small model; proteinmpnn's whole
weight set is 10 MB), which needs stock itself to tolerate the CPU and so is closed for flashzoi.
Build torch from source for this architecture at the pinned version (days). Abandon the pin and
reach `[kit] mode = "off"`, which is to say stop using the kit — and note this does **not** help a
kit whose stock needs the card, since `off` *is* stock. Or deviate the pin forward to 2.7.0 and say
so in the lock's header: that buys the card back, and takes the kit's triton pin with it (2.7.0
requires triton 3.3.0 against the kits' 3.1.0), so the kit's own bitwise claim must be re-earned
here rather than quoted — which the kit says itself, appending
`bitwise vs stock unverified on this class` to its `drift=[…]`.

## Six things to read out of the kit, never guess

Each of these was a wrong assumption that cost a debugging round.

**1. The mode variable's name.** `boltz2_opt` has none at module level; `chai1_opt` has no
`modes.resolve` at all and keeps `ENV` in `_autoload`; `enformer_opt` has no `modes` module. Read
`modes.ENV`, then `_autoload.ENV`. Deriving `<SLUG>_OPT` from the slug is how a renamed kit silently
runs stock.

**2. Where the child environment lives.** `boltz2_opt` returns 23 variables from
`modes.resolve(mode)["env"]`; `chai1_opt` keeps one in `alloc.env_row()`, documented as the row for
a *child* process. Both are read. Write down where to look, never what the value is.

**3. Who holds the model between calls.** Under a kit mode the kit usually replaces the upstream's
loader and **refuses to activate if anything replaced it first**, so a worker that memoises it turns
the whole kit off silently. Under `mode = "off"` nothing replaces it and the worker should. Decide
which case you are in, and report it: chai1's worker puts `weights_held_by` on its ready line and in
every reply.

**4. Whether a lever can win at all.** chai1's `alloc` exports `PYTORCH_CUDA_ALLOC_CONF`, and
`opt_core` checks "CUDA already initialised" *before* "the variable already holds this value"
(`mem/torch_alloc.py` `export()`). Its trigger module initialises CUDA, so the lever always loses,
and one opt-in refusal takes the whole mode to NOT ACTIVE. `[kit] levers_off = ["alloc"]` plus the
variable set before the process starts keeps the policy (`alloc_effective=true` on the kit's own
EXIT line) and costs only the bookkeeping.

**5. Whether the kit degrades or refuses.** esmc's `fused` lever needs flash-attn; with it absent
the kit does not fall back, it prints `NOT ACTIVE: partial activation — ... a mode is all of its
levers: the load is refused` and raises. Three options then: build the missing piece, run
`mode = "off"`, or declare the lever — and which is cheapest is a question the kit answers, not one
to guess. (flash-attn 2.7.4.post1 ignores `TORCH_CUDA_ARCH_LIST` and reads its own
`FLASH_ATTN_CUDA_ARCHS`; at its default it builds four architectures and takes most of a day.)

**6. What `modes.resolve()` takes and returns.** Three kits, three signatures, and guessing
yields a silent zero rather than an error: boltz2's `resolve(mode)` returns a mapping with `env`;
openfold3's takes `(mode, home, ...)` and returns a `Resolution` carrying `exports`; esmfold2's
takes `(mode, variant, kit_home)` and carries neither, keeping its variables in per-card
`configs/*.env` files that may not include this card. `kit_launch`'s probe tries the known shapes
and records the TypeError when none fits — read that record rather than patching around it. Before
this was handled, openfold3 yielded a zero-variable row and its `alloc_expandable` lever read
`skipped reason=pending`; after, 37 variables and `state=on`.

## Generate the manifest, do not transcribe it

The weight declarations come out of the kit's own `stock/PINS.json`. Write a few lines that read it
and emit `[[weights.files]]`; chai1's eight entries were generated that way. The schema varies:
`weights.files` as a dict (boltz2), as a list of `{local,url,sha256,bytes}` (chai1), keyed by
filename (rfdiffusion1), nested under a Hugging Face repo with a `snapshot_commit` (enformer,
esmfold2), or absent with a `checkpoints` key instead (evo2). Expect to add a shape, not to reuse
one unchanged.

## Parallelising the rollout

Everything except the smoke step parallelises: reading the kit, writing the manifest and worker,
building the environment, fetching weights. The smoke does not, because there is one GPU. Give each
agent one kit, its own `~/<slug>-venv`, and only `src/tooluniverse/remote/<slug>/` to write in; tell
it explicitly not to run `git sparse-checkout` in the shared kit checkout, which races, and not to
run `--only smoke`. Widen the checkout once, up front, for every slug the round covers.

Three more things learned running four agents at once:

* **Shared files belong to the caller.** `remote_runtime.py`, `remote_resident/*` and
  `pyproject.toml` are edited by one hand. Let each agent write its own `<slug>_tool.py` inside its
  own directory and *report* the `RemoteDeployment` entry it needs; add the entries yourself and
  assign the ports up front so two agents cannot pick the same one.
* **The scratchpad is shared too.** One agent's `weights.log` was overwritten mid-download by a
  sibling writing the same filename. Tell each agent to prefix its scratch files with its slug.
* **`uv venv` is not always safe.** It writes a `_virtualenv.pth`, which broke openfold3's
  kit-hook detection; a kit that finds its hook by scanning `.pth` files needs the stdlib
  `python -m venv`.
* **Stage by path, never `git add -A`.** With agents writing concurrently, `-A` sweeps their
  half-finished trees into your commit.

## Reading a refusal

Every step names itself. Exit codes: `0` ok · `1` failed · `2` usage · `3`
refused · `5` accelerator absent.

| reason | what it means | what to do |
| --- | --- | --- |
| `compiler_missing` | no `cc`/`gcc`; Triton compiles kernels at run time | `apt-get install build-essential`; needs root, so ask whoever has it |
| `driver_old` | below the 580 series for CUDA 13.0 | upgrade the driver, or use a host that has it |
| `cc_below_floor` | compute capability under 8.0 | no configuration lowers it; different hardware |
| `disk_low` | under ~20 GB free | one provider is ~16 GB (weights + environment + kit) |
| `env_python_unset` | `[env] python`'s variable is not exported | the refusal prints the `uv venv` recipe |
| `lock_install_failed` | the pinned stack did not install | read the tail; usually a wheel missing for this architecture |
| `kit_wrong_commit` / `kit_modified` | the checkout is not the pin, or has been edited | left in place; remove by hand and re-run |
| `weights_off_pin` | a file is absent, short, or a different digest | **never deleted automatically**: upstream writes straight to the final name, so a truncated transfer and a corrupt file look alike. Remove the named file yourself and re-run |
| `torch_arch_unsupported` | the stack installed and cannot emit code for this card | the kit needs newer hardware, or a host of the architecture it was pinned for |
| `kit_foreign_objects` | prebuilt `.so` of another architecture | `[kit] mode = "off"`, or a host of that architecture |
| `smoke_*` | it installed and then did not run | the transcript is in `~/.cache/tooluniverse/remote-logs/<slug>-resident.log` |

## What only running reveals

Three of the four problems the first provider hit appeared at run time, and one
presented as a stall rather than an error:

- a kit lever whose zygote featurizer hung for the full loader timeout, then
  hung again after falling back, while a plain torch DataLoader was fine;
- a Triton kernel reporting `OutOfResources` on compute capability 12.1;
- `nvidia-smi --query-gpu=memory.total` returning `[N/A]` on unified memory,
  which silently zeroes the kits' MPS budget arithmetic.

So: the smoke step carries a deadline, and `provider.toml`'s numbers are the
reference they were measured against — the per-host record in
`~/.cache/tooluniverse/measured/<slug>.json` is what a scheduler should read.

## Design the failure out

Prefer making a failure impossible over documenting it. The kits do this: files
fetched over HTTP lose their executable bit, so every command in their READMEs
is `bash script.sh`, never `./script.sh`. Ours:

- an orphaned worker retires itself, rather than a note saying to kill it;
- the interpreter's directory is taken without `resolve()`, because a venv's
  `bin/python` is a symlink to the interpreter it was built from and following
  it lands in the wrong `bin`;
- the worker passes `num_workers=0`, so a 64 MB `/dev/shm` in a container is not
  a failure mode.

## Checks

```bash
tu remote check <slug>              # both environments, weights, GPU
tu remote setup <slug> --only smoke # re-run just the proof
pytest tests/unit/test_remote_resident.py -q
python -m ruff check src/tooluniverse/remote_resident src/tooluniverse/remote
```

After editing this skill run `bash plugin/sync-skills.sh`.
