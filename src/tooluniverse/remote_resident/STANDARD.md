# The remote-tool standard

What a GPU-backed remote tool in `src/tooluniverse/remote/<slug>/` must declare
and must do. `manifest.py` enforces the declarative half; the rest is a contract
this document states and reviews check.

Every rule below carries its evidence. Rules marked **[n=1]** are generalisations
from Boltz-2 alone and are expected to be tested — and some of them broken — by
the second provider. Do not treat them as settled.

---

## 1. What a user does

Three commands, the same for every provider, whatever the model:

```bash
tu remote setup <slug>     # install: environment, kit, weights — all verified
tu remote check <slug>     # dry run: what will engage on THIS machine
tu remote run   <slug>     # serve: start the MCP server, reachable by ToolUniverse
```

`check` is part of the normal path, not a debugging step. It is run before the
first `run` and after anything changes, and it prints what a host needs to decide
whether to proceed: the mode, the device budget, the weights' state, and which
interpreter actually holds the model.

`setup` is five steps, each idempotent and each reporting `present` when it has
nothing to do, so re-running after a failure continues rather than restarts:
preflight (refuse for a host reason before downloading gigabytes) → environment
(install the lock into the interpreter the manifest names; never create one) →
kit (fetch the pinned commit, refuse a modified tree, run its own install) →
weights (deep, so what it certifies it read) → smoke.

*Evidence:* the pattern is the optimization kits' (`install` → `check` → run),
where `check` is step 3 of 4. All three commands exist. On the first provider a
complete re-run of all five steps with everything already in place takes 23 s.

---

## 2. Two environments, one socket

A provider's MCP server runs in ToolUniverse's environment. Its model runs in its
own. They communicate over a Unix socket.

This is not a preference. Boltz-2's stack is torch 2.12.0+cu130, triton 3.7.0 and
numpy 1.26.4; ToolUniverse's 600+ other tools cannot be installed alongside it.
Providers therefore never share one environment with each other or with the
package.

Consequences that are part of the contract:

- **The MCP server must import nothing from the model's environment.** A
  provider whose tool class requires the model's CLI on `PATH` at construction
  fails on a correctly separated deployment. Check both routes, accept either.
- **The worker must import nothing from ToolUniverse.** The shared surface is one
  dependency-free file (`protocol.py`) loaded by path. Importing the package
  would pull its whole dependency set into the model's environment and defeat
  the separation.

*Evidence:* measured — `import tooluniverse` in the model environment fails on
`huggingface_hub`, which that environment has no reason to carry.

---

## 3. Execution: resident by default

```toml
[runtime]
mode = "resident"        # or "subprocess", which then needs mode_reason
```

A GPU provider spends most of its wall clock on work that is identical for every
request: loading weights, building the CUDA context, compiling kernels the first
pass needs. A process that exits after each request pays all of it again.

Measured for Boltz-2 (330-residue protein + ligand + affinity, NVIDIA GB10):

| | per request |
| --- | --- |
| `boltz predict` in a subprocess | 110 s |
| optimization kit `--mode fast`, fresh worker per call | 102 s |
| the same worker, held | **~54 s** |

The 2x is the holding, not the kit — whose kernels are worth ~8 % on this card.
The structure pass alone falls from ~23 s to 5.8 s, because CUDA graphs captured
on one request are replayed on the next: a saving that a per-call worker cannot
collect, since it exits before the second request arrives.

`mode = "subprocess"` is allowed and must state `mode_reason`. A provider that
pays the start-up cost on every request says why it must.

**One request at a time per worker.** Two requests sharing one CUDA context
interleave their allocations and make an out-of-memory attributable to neither.
Callers queue; the supervisor holds a lock for the whole request.

**A worker must not outlive what it serves.** It retires after `idle_timeout_s`
with no requests, so an idle provider stops occupying the card, and it exits on
its own when orphaned — being reparented to init plus a grace period is the
signal. *Evidence:* measured — an MCP server killed with SIGKILL left two worker
processes holding the GPU; with the watchdog they exit within the grace period.

---

## 4. Weights are verified, never assumed

```toml
[weights]
root_env = "BOLTZ_CACHE"
root_default = "~/.boltz"

[[weights.files]]
name = "boltz2_conf.ckpt"
size = 2286561469
sha256 = "090e82ac…"
```

Every file declares `size`, `sha256`, or both; a file with neither is refused at
load. A cache that is short a file, or holds a file off its pin, is **named and
the launch stops**. Nothing is fetched implicitly at request time.

*Evidence:* `boltz2_conf.ckpt` on the development box was a 28.5 MB truncation of
a 2,286 MB file — 1.2 % of it — and served predictions from it for over a month.
The download had "succeeded". Nothing compared it to anything. Across the 30
existing setup skills, 30/30 pin a SHA-256 for the relay SDK wheel and 0/30 pin
anything about the model weights.

---

## 5. Environments are rebuilt from a lock, not resolved

```toml
[env]
kind = "venv"                              # venv | docker | apptainer
python = "$TOOLUNIVERSE_BOLTZ_PYTHON"      # a variable, never a path
lock = "environment/requirements.lock"
```

The lock is a complete freeze, installed with `--no-deps`. Letting a resolver
re-derive the set is how a stack stops being the one that was measured.

`python` names an environment variable because the interpreter's location is
per-machine. The manifest declares *what*, the machine supplies *where*.

A manifest that names a file it does not ship is refused at load: it reads as a
promise the deployment can rebuild this environment.

*Evidence:* across the 30 existing setup skills, 0/30 contain a single
`pip install <pkg>==<version>`; the documented boltz setup is
`pip install -e . && pip install fastmcp boltz` into one shared environment.

`kind` picks how the stack is materialised, and the kits offer the same three
ways, noting that everything after getting the stack is identical. The same
holds here: a resident worker is the same script, holding the same model,
answering on the same socket. Only the argv that starts it differs, so only
that is abstracted (`exec_env.py`).

**Paths are mapped identity** in a container: every bind mounts a host path at
the same path inside. A private layout would need translation for the socket,
the weights, the worker script, the shared protocol file and every per-request
output directory the caller names, in both directions, forever. Identity
mapping costs one convention and removes all of it.

**A container runs as the calling user**, and that is not free. The kits' own
recipes note "Containers run as root ... do not create an unprivileged user",
which for a model writing into a bind means root-owned output on the host. Run
it as yourself and four things break, each of which this project hit in order:

- `pwd.getpwuid` raises for a uid the image never heard of, which surfaced as a
  Boltz-2 zygote preload failing and then a nanobind abort from the double
  import that followed. A synthetic two-line `passwd` — root and the caller —
  is bound; the host's own would hand the model every account on the machine.
- `site-packages` is root-owned, and libraries that compile want to write
  beside the module: numba refuses with "cannot cache function … no locator
  available". Every compiler cache is pointed at one bound, writable place.
- `$HOME` is a mount point the daemon created and owns, so `~/.triton` cannot
  be made and Triton's probe fails with a permission error that reads as a
  kernel refusal. The container gets a home of its own — it does not have the
  host's.
- A host user site-packages must not shadow the image's pinned stack
  (`PYTHONNOUSERSITE`), which the kits' Apptainer recipe sets for the same
  reason.

**`work_root` is required for a container**, because a per-request output path
the caller invents is not visible inside unless something bound it.

**Images are built from the kit's own recipe**, in a hard-linked shadow of the
checkout — the checkout must stay byte-identical to its pinned commit, and the
Dockerfiles want an empty archive in a `_jitcache/` directory the checkout does
not have. The archive's name has to satisfy the Dockerfile's own glob,
`_jitcache/<kit>-*-jit.ta[r]`.

All three routes are exercised. On the same input and the same card they give
the same peak reserved memory, 3.21 GiB, which is the useful check: it says the
three are running the same model on the same stack rather than three things
that merely all finish.

| route | one prediction | peak |
| --- | --- | --- |
| venv | 15 s | 3.21 GiB |
| docker | 13 s | 3.21 GiB |
| apptainer | 22 s | 3.21 GiB |

**Apptainer's build needs privilege; its run does not**, and that asymmetry is
the point of the route rather than a wart. A `.def` with a `%post` section runs
commands inside the image, which needs fakeroot, which needs unprivileged user
namespaces — and Ubuntu 24.04 ships
`kernel.apparmor_restrict_unprivileged_userns=1`, so `unshare --user` is denied
even with `subuid`/`subgid` configured. Building therefore takes one root
command. Running the resulting `.sif` takes none, and runs as the calling user
rather than as root, which is what Docker needs `--user` and a synthetic
`passwd` to achieve. That is the kits' own recommended shape: build the `.sif`
once on a machine that has Docker, copy the one file to the cluster, and the
cluster needs only Apptainer.

**Which implementation is "apptainer"** is worth stating. Apptainer (Linux
Foundation, 1.x) and SingularityCE (Sylabs, 4.x) are forks of the same project
and the kits treat them as interchangeable — their `.def` headers read
"Apptainer / Singularity". This standard's `kind = "apptainer"` covers both and
the runner is whichever of the two is on `PATH`. What was exercised here is
SingularityCE 4.1.1, because Ubuntu 24.04 packages that one and upstream
Apptainer publishes no aarch64 build; a provider's `verified_on` should say
which it ran under rather than let the vocabulary imply it.

---

## 6. The GPU declaration is what a host schedules on

```toml
[gpu]
policy = "required"
vram_budget_gb = 5.54     # measured peak reserved, not a guess
shareable = true
isolation = "process"     # process | mps | container
```

`vram_budget_gb` is the highest `torch.cuda.max_memory_reserved` observed over
consecutive requests in one held worker — the later requests, not the first:
Boltz-2 measured 4.31, 5.15, 5.54 GiB over three. It is what a host adds up to
decide how many providers may be resident at once.

**When peak depends on the input, the budget states the envelope it was
measured at.** The first three providers hid this, because a folding smoke is
roughly a folding request. The fourth broke it: RFdiffusion3's smoke is a
60-residue unconditional design and reserves 2.12 GiB, while a 400-residue,
4-design request — an ordinary thing to ask it for — reserves 12.49. A budget
quoted from the smoke would have under-budgeted a real request by 6x, and
under-budgeting is precisely the failure multi-tenancy cannot absorb. So the
manifest carries the ladder and names the row it declares:

| model | 100 aa | 200 aa | 400 aa | 800 aa | declared at |
| --- | --- | --- | --- | --- | --- |
| OpenFold3 | 1.45 | 1.61 | 2.27 | 4.24 | 800 aa |
| ESMFold2 | 14.14 | 15.07 | 17.70 | 25.28 | 800 aa |
| RFdiffusion3 | 2.62 | 2.92 (1 design) | 12.49 (4 designs) | — | 400 aa, 4 designs |

**A ladder must run ascending, in a worker nothing larger has touched yet.**
`peak_reserved_gib` is a running high-water mark in six of the eight workers
written so far; only Boltz-2 and Enformer reset it per request through
`on_reset`, so the same field means two different things across providers and
their records are not directly comparable. The consequence for measurement is
concrete: taking esmc's ladder after a mixed-shape phase made its 100-residue
rung read 24.44 GiB where a clean ascending session reads 24.08. Neither number
is wrong — the first answers "what does this worker hold now", which is what a
scheduler wants, and the second answers "what does this input cost", which is
what an envelope needs. A new provider should NOT reset: a host adding budgets
up needs the worker's worst case, and a per-request peak under-reports whatever
the allocator pool has grown to.

Reading the ladder is as useful as reading the number. ESMFold2 costs 1.8x
going from 100 to 800 residues where OpenFold3 costs 2.9x, because almost all
of ESMFold2's footprint is the constant ESMC-6B term; a host that will not fold
past ~200 residues can hold it in 16 GiB rather than 26. RFdiffusion3's peak is
driven by length and barely by count — doubling designs at 400 residues adds
5%. None of that is derivable from the architecture on paper; all of it comes
from one held worker and seven requests.

**A derived estimate is worth writing down and worth distrusting.** Both
estimates made before measuring were off in different directions: OpenFold3 was
budgeted at 16 GiB from weights-plus-pair-tensor arithmetic and measures 4.24,
because the kit keeps far less of the trunk resident than the arithmetic
assumed; ESMFold2 was budgeted at 16 GiB and measures 25.28. An estimate that
is 3.8x high wastes a card; one that is 1.6x low overcommits it.

`isolation` states what the deployment actually provides, never what one would
like. The vocabulary deliberately excludes `mig`: the development box reports
"No MIG-supported devices found", gVisor's nvproxy carries no Blackwell ABI, and
a word nobody can honour does not belong in a vocabulary a host reads to decide
whether to accept other people's work. On such hardware co-tenants are separated
by process and by budget — there is no hardware boundary between them, and a
manifest that implied one would be the dangerous kind of wrong.

---

## 7. Third-party kits are referenced, never vendored

```toml
[kit]
upstream = "https://github.com/anthropics/uplifting-biomolecular-modeling"
commit   = "f4f62fa6592ae4938d49b1757bea0cfeff9f468e"   # full sha, never a tag
subdir   = "boltz2"
sparse   = ["boltz2", "common"]
mode     = "fast"
```

Zero bytes of kit code enter the install package. `setup` fetches the pinned
commit into `$TOOLUNIVERSE_KIT_ROOT/<repo>@<commit>/` — content-addressed, so
providers pinning the same commit share one checkout and an upgrade never
clobbers a working one.

*Evidence:* the kit is 473 MB, of which `common/opt_core` is 308 MB and 297 MB of
that is prebuilt kernels — largely x86_64/sm_80 binaries that an aarch64 host
cannot load at all. A sparse blobless clone of what boltz needs is 402 MB in 8 s.
Its licence (Apache 2.0) permits vendoring; the size and an explicit "the install
must stay editable" in its own `pyproject.toml` forbid it.

**Wrap a kit, do not patch it.** Boltz-2's resident worker is a different script
in the position the kit's own batch worker occupies, so the kit's import hooks
attach 25 of its 28 levers to the model that worker builds. Nothing in the kit is
modified, copied or shadowed, and the kit's own version and pin checks keep
working. **[n=1]** Whether that position exists in other kits is exactly what the
second kit-backed provider tests.

---

## 8. Failures are named, and the name carries the fix

Every refusal prints one blank-free token naming it, and — where a fix exists —
the command that applies it:

```
run.sh: boltz2_opt is not installed on /path/python: /path/run.sh install
[boltz2-opt] NOT ACTIVE: reason=core_missing:boltz2_opt
```

Exit codes are stable and branchable: `0` ok · `1` failed · `2` usage · `3` not
active or refused · `5` an expected accelerator absent.

This is why there is no troubleshooting narrative in this standard, and why the
per-provider skill is a **table from refusal name to action**, not prose. A
narrative drifts to whatever its author remembered that day — which is how 30
skills came to pin the SDK wheel's digest and none of the weights. A name table
cannot drift, because the names come from the code: add a refusal name and the
table gains a row; delete one and its row is detectably orphaned.

**Design the failure out where you can, rather than document it.** The kits do
this: files fetched over HTTP lose their executable bit, so every command in
their READMEs invokes `bash script.sh` rather than `./script.sh`, and the failure
becomes impossible. Two of ours are already handled this way — an orphaned worker
retires itself instead of a note saying "remember to kill it", and the
interpreter's directory is resolved without following the venv's symlink instead
of a warning about it.

---

## 9. What this standard does not promise

Three tiers, and only the first two are guaranteed.

**Deterministic — `setup` guarantees it.** The same bytes install everywhere the
install succeeds at all: lock file, pinned commit, weight digests. All of it is
digest comparison.

**Checkable — `setup` refuses early, before downloading gigabytes.** Driver
version, compute-capability floor, a compiler on `PATH`, free disk, `/dev/shm`
size, host reachability.

**Only discoverable by running — `setup` cannot guarantee it.** Which levers
engage on an unseen GPU; whether something hangs; whether it fits beside another
tenant; how fast it is.

Four issues were hit bringing up one provider on one machine, and three were of
the third kind: a kit lever whose zygote featurizer hangs where a plain torch
DataLoader does not, a Triton kernel that reports `OutOfResources` on sm121, and
`nvidia-smi --query-gpu=memory.total` returning `[N/A]` on unified memory, which
silently zeroes the kits' MPS budget arithmetic.

Therefore:

- **`setup` ends with a smoke test under a timeout**, not with "installed". The
  prefetch hang presents as a stall, not an error; without a deadline the setup
  waits forever and reports nothing.
- **`setup` records what actually happened on this machine** — which levers
  engaged, peak memory, wall time — to a per-host file. The numbers in
  `provider.toml` are the reference they were measured against, not a claim about
  the host reading them. A scheduler reads the measured file.
- **A provider is `verified` only on hardware where that smoke test has run.**
  Everything else is `untested`: installable, and said so. `[provider] status =
  "verified"` must carry `verified_on` naming that hardware — a bare "verified"
  claims every machine.

---

## 10. Choosing which kit to bring up next

The thirty-six upstream kits are uniform in structure — all carry `run.sh`,
`environment/`, `opt/` and `stock/PINS.json` — and unhelpfully varied in the
three things that decide whether one can run on a given machine at all. Each is
cheap to read before committing to a download:

**Can its pinned torch drive this card?** Six kits pin torch below 2.7 —
pxdesign (2.3.1+cu121), chrombpnet (2.4.1+cu124), rfdiffusion1 (2.4.0),
proteinmpnn (2.5.1+cu124), flashzoi (2.5.1), caliby (2.6.0+cu124) — and on
aarch64 the reason they cannot run is sharper than a cubin-coverage argument.
**PyPI publishes no CUDA-enabled aarch64 torch wheel below 2.7 at all.**
Checked, not assumed: the `manylinux*_aarch64` wheels for 2.3.1, 2.4.0, 2.5.1
and 2.6.0 each contain `libtorch_cpu.so` and no `libtorch_cuda.so`, and every
`nvidia-*` dependency in their metadata carries the marker
`platform_machine == "x86_64"`. So forward PTX JIT — the usual escape when a
cubin set stops short of a new architecture — does not apply: there is no CUDA
code in the artifact to JIT.

Three ways out, in descending honesty:

1. **Run it on the CPU.** Legitimate, and for a small model it is the right
   answer rather than a consolation: `[gpu] policy = "none"`, and residency
   still earns its place because the import graph and the weight read dominate.
   proteinmpnn's entire weight set is 10 MB.
2. **Build torch from source** for aarch64 + CUDA 13 + sm_121 at the pinned
   version. Days, and the pinned version may predate CUDA 13 support.
3. **Deviate from the pin** and install torch ≥ 2.7. This breaks what the lock
   is for, and the kit's own pin check will refuse the mode — so it is only
   reachable through `[kit] mode = "off"`, which is to say by not using the kit.

Seventeen kits pin 2.7 or later and are the normal queue. For those, `setup`
reads `torch.cuda.get_arch_list()` after installing and refuses
`torch_arch_unsupported` rather than letting it arrive as a kernel error — but
the rule there is binary compatibility, not equality: an sm_120 cubin runs on
sm_121, which is how every verified provider here drives a card none of their
builds lists.

**Does it carry prebuilt host objects?** Eight do, and all thirty-nine such
files are x86-64; none is aarch64. `setup` reads the ELF header before
installing (`kit_foreign_objects`).

**Does its lock pin an architecture by URL?** About twenty name at least one
wheel by direct link to an x86-64 file. The shipped lock pins it by version
instead and its header says so, as Enformer's does.

**How does it activate?** 30 of 36 through the mode variable and their own
`.pth`; one (boltz2) through an explicit `worker_launch`; one (chrombpnet) not
in-process at all, which makes it `mode = "subprocess"`.

## 11. Evidence status

| Rule | Evidence |
| --- | --- |
| Resident by default; 2x | measured, Boltz-2, one card |
| Weight digests | a real month-long failure; 0/30 skills pin weights |
| Lock, `--no-deps` | 0/30 skills pin any version |
| Two environments | measured: the model env cannot import ToolUniverse |
| Orphan watchdog | measured: SIGKILL left 2 workers holding the GPU |
| `vram_budget_gb` from the *later* requests | measured: 4.31 → 5.15 → 5.54 GiB |
| `isolation` excludes `mig` | measured: no MIG on this hardware |
| Kit referenced, not vendored | measured: 473 MB, 297 MB of foreign-arch binaries |
| Named refusals carry the fix | the kits' design; **ours: 2 of 16 do so today** |
| Wrapping a kit without patching it | two kits, two mechanisms |
| Three commands suffice for every provider | two providers |
| `setup`'s five steps are the right five | two providers |
| `[env] kind` beyond `venv` | three routes, one provider each way |
| The worker/manifest/launch contract | six providers, six upstreams |
| `outputs` / `output_keys` required to claim `verified` | measured: openfold3 exited 0 and folded nothing |
| A budget needs its envelope when peak tracks input size | measured: 2.12 GiB smoke vs 12.49 GiB request |
| A resident worker must not fork loader children | measured: openfold3 crash; boltz named it first |
| Residency gain ranges 2.0x–12x | measured, five providers |
| Four identical requests, not two warm calls | measured: openfold3 passed the smoke and died on request two |
| `[kit] env_row` must be declared | measured: 4 of 8 kits return an empty row, for two different reasons |
| `levers_off` is not universal | measured: boltzgen's modes.py never reads it |
| Four activation shapes, not three | rosettafold3: autoload + a patched tree on disk |
| Four answers to "who holds the weights" | boltzgen: nobody; upstream reloads per step |
| Wall times need an idle card | measured: 15-19 s quiet, 28-56 s contended, same fold |
| The ladder's SHAPE decides co-tenancy | measured: esmc 1.19x over 16x the length, rosettafold3 3.7x over 8x |
| Derived estimates err both ways | measured: openfold3 3.8x high, esmfold2 1.6x low |
| Turning a kit off can cost VRAM, not just speed | measured: esmc `off` costs 9.6 GiB -- `pipe` was the device-side loader |
| No CUDA aarch64 torch below 2.7 | measured: 4 wheels inspected, `libtorch_cpu.so` only, nvidia deps marked x86_64 |
| `peak_reserved_gib` is a high-water mark, so ladders ascend first | measured: 24.44 vs 24.08 GiB for the same 100-residue rung |
| Fork has three shapes; a library's pool is one | measured: boltzgen 0 designs in 420 s, 31.6 s with OMP_NUM_THREADS=1 |
| An `outputs` glob must not match a file written anyway | measured: boltzgen's `design_spec.cif` would have passed a design-less run |
| An ablation is sized for the largest input, not the smoke | measured: atlasfold 7 levers folds 35 aa, aborts at 600; 13 folds both |
| A pinned dependency can ship kernels the pinned compiler cannot build | measured: cuEquivariance's Triton kernels abort atlasfold's stock path |
| Compile the Triton question, do not read strings at it | measured: atlasfold passed both static reads and still aborted |
| A reserve can ratchet | measured: atlasfold reports 38.63 GiB for a 3-second request after one 800 aa fold |
| Utilisation alone is not evidence of progress | measured: a 40-minute stall read as 86-91% busy, which was another session |
| The repeats test cannot see a second BUILD | measured: genie3 passes 4 identical and raises on the first rebuild |
| A worker may have to reset UPSTREAM's module state | measured: one sampling config per process, OK/TypeError/TypeError |
| An input ceiling must agree with the budget | measured: progen2's 16x1024 permits a 116.93 GiB request |
| A CUDA failure can surface somewhere else | measured: protenix's LayerNorm, 24/24 shapes, next op raises |
| A wheel can install and then SIGILL | measured: tokenizers 0.10.x aarch64, `Illegal instruction` |
| pip ignores requirement order | measured: libcudnn 124,920 vs 6,328,728 bytes |
| Residency can be shown not to change the output | measured: genie3 byte-identical over four requests |
| Residency tracks fixed-cost-to-work, not its kind | measured: genie3 12x with no compile trace |
| `cudaMemGetInfo` free is system-wide here | measured: every rung refused with a co-tenant up |

## 12. What providers fifteen through seventeen changed

ProGen2, Protenix and Genie 3, plus the two still in flight. Seventeen verified.
Five of this batch's findings change what the acceptance test is for.

**The four-identical-request test has a blind spot, and it is the half everyone
would skip.** It proves a held engine serves repeats. It cannot prove the worker
can build a SECOND engine, because a held engine is built once. Genie 3 would
have passed four identical requests and raised on the first request that changed
its engine key — which the tool makes the second real user request — because
upstream's sampling config is a module-level mutable `ConfigDict` holding
`FieldReference` objects and `registry.get_config()` can only run once per
process. Reproduced on the CPU with the identical document three times: OK,
TypeError, TypeError.

So the acceptance sequence is four identical requests **then at least one that
changes the engine key**. The mixed-shape phase was already asked for; the reason
is now sharper. **The rebuild is the danger, not the new shape.** A provider with
no way to vary its input cannot be accepted on repeats alone, and the
verification script says so and exits non-zero rather than printing 4/4.

**A resident worker may have to reset UPSTREAM's module state, not just the
kit's.** This is the sixth resident-worker hazard and the first that is neither a
fork, a lever, nor a graph. Section 13 names the kit's own recovery for a failed
capture; this is the same shape one layer down, with nobody naming it, in a
library that is entitled to assume one model per process because the kits' own
determinism contracts say one process per request. The cheap generalisable check
before writing a worker: **call the upstream config or model builder twice in one
process.** One minute, and invisible to the identical-request test.

**A declared input ceiling can admit a request no budget covers.** ProGen2's tool
allowed 16 sequences of up to 1024 tokens; each ceiling is sane and the product
is not. Measured, fresh worker per point: 4096 tokens costs 5.81 GiB, 8192 costs
29.2, and 16384 — which the two ceilings permit together — costs **116.93 GiB**,
essentially the whole device, because peak is roughly quadratic in
`num_samples x max_length` and nothing caps the K/V cache. The bound must be on
the product, and it must exist in the tool as well as in the budget: a ceiling
that admits an unschedulable request is not a bound. Check the ceilings against
the budget, not only against each other.

**A CUDA failure can be latent and surface somewhere else.** Protenix's stock
fast-LayerNorm extension hard-codes the architectures it emits — 70, 80, 86, 89,
90, 100 — as SASS with no PTX row. On a newer card the extension call returns,
`torch.cuda.synchronize()` after it PASSES, and the *next unrelated* torch
operation raises `no kernel image is available for execution on the device`, with
an output in hand that was never written. The first probe printed "LAUNCH OK"
twice because it did not touch the card again. A probe for this class has to do
something afterwards.

**A prebuilt wheel can be the right file, install cleanly, and kill the
interpreter.** `tokenizers` 0.10.0/0.10.1/0.10.2 publish well-formed
`manylinux2014_aarch64` artifacts that `pip install` accepts and that raise
`Illegal instruction (core dumped)` at import on this core; 0.10.3, the pin,
publishes no aarch64 wheel at all. In a worker that surfaces only as
`smoke_protocolerror` with no traceback, because SIGILL is uncatchable. The
standard already covers "no wheel for this architecture" and "the kernels cannot
build"; this is a third: the wheel exists, installs, and does not run. The only
way to find it is to import every compiled pin, which is what `[env] verify` is
for.

**pip does not honour requirement order.** A lock carrying two CUDA generations
gets whichever of a colliding pair pip reaches last. Protenix's keeps both the
12.9 and 13.0 runtimes and 27 paths collide under `nvidia/{cudnn,nccl,cusparselt}`;
one pass leaves `libcudnn.so.9` at 124,920 bytes where two passes with CUDA 13
last leave 6,328,728, and that single path is the one torch 2.13.0+cu130
preloads. The result imports fine and is simply not the stack that was measured.
A lock may now declare ordered passes with `# --- pass break ---`.

**Residency's payoff tracks the ratio of fixed cost to work, not the kind of
fixed cost.** Section 14 explains the 2.0x–12x range by what a kit does at import
and at first call. Genie 3 reaches 12x with no compile trace and no held-weights
advantage over Boltz-2, purely because a 20-step 50-residue pass is *shorter than
the per-process set-up it is compared against*. Both terms matter, and the
prediction made from the first one alone was wrong by 6x.

**And residency need not change the answer, which has now been shown rather than
assumed.** Genie 3's four identical requests produce byte-identical PDB files,
sha256 over every file, on a kit whose own contract claims byte-identity only for
one process per request. Its worker snapshots four RNG generator states when the
engine is built and restores them before every later request. It is the only one
of the seventeen where this has been measured, and it is measurable only because
the claim was written down in a falsifiable form first.

**Two measurement notes.** A kit's recorded probe constant is a portable
cross-check for any provider that deviates from a pin: Genie 3's kit records
2.02 GB at 670 padded tokens on an H100 and this substituted cu128/aarch64 stack
measures 1.983 GB, 1.8% apart — the role the three container routes' identical
3.21 GiB peak plays in section 5. And `cudaMemGetInfo`'s `free` is **system-wide**
on unified memory, so a co-tenant's host allocations make a kit's own capacity
guard refuse requests needing a hundredth of the card. That is the second place
unified memory breaks a kit's arithmetic, after `nvidia-smi memory.total`
returning `[N/A]`, and the first that reaches the resident path rather than only
the kit's CLI.

**One about this layer's own checks.** Three of them have now refused a provider
that works: the Triton LLVM version check, `kit_foreign_objects`'s message, and
`_arch_problem` judging a JAX provider by an incidental CPU-only torch. The
pattern is worth naming, because it will recur: **a check that encodes what was
true of the providers already shipped will refuse the next one shaped
differently, and that costs more than a missing check, because a refusal is
believed.** Each was fixed by measuring instead of asserting.

## 13. What providers eleven through fourteen changed

AF3-torch, Evo 2, ESMFold2-binder-design, AtlasFold and BoltzGen — brought up by
one agent each, with the GPU serialized. Fourteen providers are verified now.
Three of these five were expected not to run on this hardware at all.

**Fork has three shapes, not one, and `num_workers = 0` covers only the first.**

| provider | what forked | how it failed |
| --- | --- | --- |
| OpenFold3 | upstream's DataLoader worker | child died, no traceback |
| AtlasFold | the kit's writer child (spawn, not fork) | never reached; would reload the model |
| BoltzGen | **nothing of ours** — a library's thread pool | worker alive, 0% CPU, waiting forever |

BoltzGen's is the one that generalises. Its DataLoader worker sits in
`torch.cdist` → `at::parallel_for` → an OpenMP parallel region, waiting on a
pool `fork()` did not carry over. The kit's levers do host-tensor work during
activation, so the pool is already up when upstream forks; stock has not touched
it yet, which is why **stock computes at 95% GPU and the kit mode sits at 0%**.
Unset, zero designs after 420 s; `[kit.env] OMP_NUM_THREADS = "1"`, 31.6 s.

So the rule is not "set `num_workers = 0`" and not "no model-sized child by any
start method" — it is: **a resident worker that has run any host-tensor work
must not let a library fork**, and making the OpenMP pool not exist is the
cheapest way to guarantee it.

**An `outputs` glob must not match a file the provider writes regardless of
success.** BoltzGen's `configure` writes `design_spec.cif` — a picture of the
*specification* — whether or not anything is designed, so the obvious `*.cif`
would have passed a run that produced nothing, which is the exact failure the
key exists to catch. The shipped glob is `*_[0-9]*.cif`, tested against a real
run and a design-less one.

**A smoke may not reach the kit's levers at all.** Every kernel lever of the
AtlasFold kit is gated at `min_tokens = 512`, so its 35-residue smoke exercises
none of them: a seven-lever ablation folds 35 residues and aborts at 600, while
thirteen folds both. **An ablation must be sized for the largest input the
provider accepts, not for the smoke.** Worse, stock AtlasFold under upstream's
own `--kernel auto` folds 35 residues and aborts at 200 — so the one length that
works is the smoke's, and a green smoke would have been the most misleading
result that provider could produce.

**A pinned runtime dependency can ship kernels the pinned compiler cannot
build.** That is a third kind of stack-versus-card failure, after "no aarch64
CUDA wheel below torch 2.7" and "the kit's own levers cannot run": cuEquivariance
0.10.0 carries its own Triton kernels, and AtlasFold's `--kernel auto` resolves
to them on nothing more than the Python package importing.

**So the Triton question is measured, not read.** `step_environment` compiles one
`tl.sum` kernel in the model interpreter — the construct that emits the warp
shuffle — and reports what happened; the target-string reads stay to *explain* a
failure rather than to predict it. AtlasFold passed every static read and still
aborted. Two implementation details each cost an agent an hour: the kernel must
be written to a FILE and run as a CHILD, because `@triton.jit` reads its own body
with `inspect.getsource` and because the failure under test is an `abort()`.

The Triton version boundary, established by reading each `libtriton.so` and then
running the intrinsic:

| triton | LLVM knows `sm_121a` | bundled ptxas | verdict |
| --- | --- | --- | --- |
| 3.3.x | no | 12.4 + a 12.8 `ptxas-blackwell` | aborts on any cross-lane reduction |
| 3.4.0 | yes | 12.8 only | `ptxas fatal`, fixable with a 12.9 ptxas |
| 3.6.0 / 3.7.1 | yes | + 12.9 / 13.1 `ptxas-blackwell` | works as shipped |

And the variable name is derived, not literal: Triton builds it as
`TRITON_<BINARY>_PATH` and selects `ptxas-blackwell` above cc 100, so on this
card it reads `TRITON_PTXAS-BLACKWELL_PATH`, hyphen included. A worker sets both.

**A reserve can ratchet and not come back.** After one 800-residue fold,
AtlasFold's worker reports 38.63 GiB for every later request including a
3-second one, because the figure is `max_memory_reserved` and the caching
allocator keeps the segments it grew. A deployment capped at 400 residues holds
that provider in 14 GiB rather than 39 — the cap is the budget.

**`[env]` assumes one interpreter and two providers need two.** AF3-torch's
weights file has no URL anywhere: it is *produced* by a converter in a second
pinned environment, whose one C++ extension nobody had built on aarch64. It
built — 236 targets, no portability patch — and the converted file is bit-exact
against a digest the kit measured on x86-64. ESMFold2-binder-design needs its
second interpreter too. Both carry it in environment variables and refuse by
name without it; `[env] aux` is recorded as a gap rather than built for two in
fourteen.

**An envelope may be the DEVICE rather than the input.** ESMFold2-binder-design's
checkpointing planner budgets 0.90 × the card's total memory and grows to fill
whatever card it is on above ~500 tokens, so a ladder would measure the host. It
declares its budget at the one point it was measured, sets `shareable = false`,
and names a different kit MODE as the bounded alternative.

**On a shared card, GPU utilisation alone is not evidence that a process is
computing.** A 40-minute BoltzGen stall was read as progress because the card
showed 86-91% — which belonged to an unrelated session. The usable signal is
utilisation *plus* `/proc/<pid>/stat` CPU, on a quiet card. Peaks reproduce under
contention; wall times do not.

## 14. What providers seven through ten changed

RoseTTAFold3, BoltzGen, ESM Cambrian and AF3-torch, brought up by one agent
each in parallel, with the GPU serialized by the caller. The four together
broke more of this document's assumptions than the six before them.

**A one-request smoke cannot verify a resident provider.** OpenFold3 passed its
smoke producing five real structures and then failed, deterministically, on the
SECOND request of the same shape: `RuntimeError: Offset increment outside graph
capture encountered unexpectedly`. The chain is worth reading because nothing
in it is exotic. Lightning moves the module to the CPU between requests, so
every parameter address changes; the `trunk_graph` lever correctly refuses to
replay over moved storage and deletes the graph entry — but keeps the graph
POOL handle that the deleted graph had just emptied. The re-capture hands that
dead handle to `torch.cuda.graph(...)` and fails inside the allocator. A
capture that began and never ended leaves the CUDA generator's `capturing_`
flag set, and the next eager `torch.randint` reports it, three call frames
away in a different lever. The kit names this exact aftermath in
`opt_core/capture/graphs.py::reset_generator_capture_state`; the cell that
caused it calls neither that recovery nor its own `release()`.

A ladder of four DIFFERENT shapes passed throughout, because a new token count
makes the lever call `release()`, which does clear the pool. **So the
acceptance test for a resident provider is at least four consecutive IDENTICAL
requests, then a mixed-shape sequence.** "Cold start and two warm calls" — what
the setup skills said — passes on a build that cannot serve a repeat.

The fix was the kit's own gate knob rather than an ablation, and it was chosen
by measuring the alternative:

| | 35 res, 4 requests | peak @ 800 res |
| --- | --- | --- |
| `post_release` forced on every item | 18.4 / 15.7 / 18.3 / 17.6 s | **9.12 GiB** |
| `trunk_graph` off | 16.6 / 13.3 / 15.3 / 15.8 s | 11.13 GiB |

Two seconds for two gigabytes is the right trade for a provider held resident,
and it leaves one fewer lever ablated.

**Two new manifest keys came out of this batch, both for the same reason: an
absence and a failure to read look identical from here.**

`[kit] env_row` is `"probe"` or `"none"`, and `"none"` needs `env_row_reason`.
Four of eight kits return an empty row and it means two different things —
esmfold2, esmc and rosettafold3 keep no row at all (their variables live in
`configs/<card>.env` files shipped for h100/h200/a100), while boltzgen has an
eight-switch row it applies to itself in `stack.activate()`. OpenFold3 meant to
get 37 variables, got zero, and said nothing.

`[kit.env]` is a table of settings the provider states for its kit, applied
before the process starts. It exists because OpenFold3's fix is a size gate,
not a lever, so `levers_off` could not express it and it would otherwise live
as a line of Python in a worker no reviewer reads.

**`levers_off` is not universal.** BoltzGen ignores `MODEL_OPT_LEVERS_OFF`
entirely — its `modes.py` never reads it — and its `stack.activate()` overrides
a caller's value for any switch the mode exports, which its own tests state
("the caller's `SZ_TD_CHUNK=8` is dropped for the mode's own 64"). So neither
door reaches it. A provider cannot assume the kits' shared vocabulary is
implemented by the kit it is wrapping; check, and if neither door works, say so
in the manifest rather than shipping a setting that silently does nothing.

**A fourth activation shape.** The taxonomy was `.pth` autoload (30 of 36),
`worker_launch` (boltz2), replacement entry script (chrombpnet). RoseTTAFold3
adds *autoload plus a patched tree on disk*: five files of the installed `rf3`
package must be byte-equal to the kit's copies, checked by sha256 in
`stack.activate`, and the kit's own installer refuses to patch an interpreter
that shares site-packages with a pristine one ("two interpreters, never one
switched in place"). The provider therefore runs the four lines `run.sh
install` runs for the patched interpreter, and gives up `[kit] mode = "off"` —
a stock pass on a patched tree is not a stock pass — which the manifest states
rather than leaving to be discovered.

**A fourth answer to "who holds the weights": nobody.** BoltzGen's pipeline
runs one interpreter per step and upstream calls `load_from_checkpoint` inside
every step. The kit replaces no loader, so memoising would mean patching
upstream on top of the kit and racing its `fastinit` lever. Its ready line says
`weights_held_by=upstream-per-step`, and residency there buys the process —
imports, CUDA context, JIT caches — rather than the weights. That is still
worth having, but it is a different claim and the manifest makes it.

**A kit may refuse to degrade, and that is the design.** ESM Cambrian's `fused`
lever needs flash-attn. With flash-attn absent the kit does not fall back: it
prints `NOT ACTIVE: partial activation — fused: flash_attn is not importable; a
mode is all of its levers: the load is refused` and raises. A provider wrapping
such a kit has exactly three options — build the missing piece, run `mode =
"off"`, or declare the lever — and guessing which is cheapest without reading
the kit wastes hours. (flash-attn 2.7.4.post1 ignores `TORCH_CUDA_ARCH_LIST`
and reads its own `FLASH_ATTN_CUDA_ARCHS`; left at its default it builds four
architectures and takes most of a day.)

**`[env]` assumes one interpreter and one kit needs two.** AF3-torch's
featuriser and its output writers run CPU-only under a second pinned
environment, and the weights file it loads has no URL anywhere — it is
*produced* by a converter running in that second environment. The provider
cannot be smoke-tested on a machine that has only the first, and the honest
form of that is a named refusal at the weights step carrying the recipe, which
is why a fetch exiting 3 is now reported as REFUSED rather than FAILED. This is
one kit in ten; the fix is recorded as a gap, not built.

**Timings on a shared card are not measurements.** Two of this batch's
acceptance runs shared the GPU with another session and read 28-56 s for a fold
that takes 15-19 s quiet. Peak reserved reproduced to the hundredth of a GiB
across both; wall time did not. Report peaks from any run, and wall times only
from an idle card.

## 15. What providers four, five and six changed

Three at once — RFdiffusion3, ESMFold2 and OpenFold3 — brought up in parallel
by one agent each, with the GPU serialized by the caller. Two passed; the third
taught the most.

**An exit code is not evidence that a model ran.** OpenFold3's smoke exited 0
in 29 s, reported `peak reserved 1.41 GiB`, and was recorded as verified. Its
output directory held `inference_query_set.json` and a `summary.txt` reading
"Successful Queries: 0, Failed Queries: 1". Upstream catches the per-query
exception itself, writes the summary and returns normally, so nothing raised
and nothing was produced. The smoke step had counted files and checked for an
exception, and neither of those is the question.

So a manifest now declares what a successful run leaves behind, and the smoke
step refuses when it is absent:

```toml
[runtime]
outputs = ["*.cif.gz"]        # globs matched against what the run wrote
output_keys = ["centre"]      # or, for a provider that writes no files
```

`status = "verified"` requires one of the two — the manifest refuses the claim
without it, the way it already refuses a bare `verified` with no `verified_on`.
`output_keys` exists because Enformer answers with arrays and writes nothing;
a file glob would have refused it forever. `outputs` is matched against both
the paths the worker reported and a walk of the output directory, because a
provider is not obliged to list what it wrote, and against the file *name*, so
RFdiffusion3's compound `*.cif.gz` matches.

**A resident worker must not fork data-loader children.** OpenFold3's first
failure was a real crash: `DataLoader worker (pid 778073) exited unexpectedly`,
no traceback from the child. Upstream defaults to 10 workers and the kit's own
cap floors that at 1 — a floor a resident worker cannot use, because the parent
has CUDA initialised and its kit hooks, cuEquivariance, DeepSpeed and Triton
threads long before a request arrives, and `fork()` copies only the calling
thread. `boltz_tool.py` had named the same shape a year earlier. The fix is
`num_workers = 0`, which the kit's own `plan()` short-circuits on, and its
stated cost is that featurisation's RNG draws move in-process, so runs are not
bit-comparable with a forked run at the same seed. This is a property of the
resident route rather than of any one kit, so it is unconditional.

**Residency's payoff varies by an order of magnitude, and the reason is the
kit, not the model.** RFdiffusion3 returns 19.4 s, 1.6 s, 1.6 s over three
designs — 12x — because its `fast` mode traces the denoiser through
torch.compile and captures it as a CUDA graph, both per process. ESMFold2
returns 2.7 s, 1.1 s, 1.1 s because 25.6 GiB of weights are read once instead
of three times. OpenFold3 would save the least: a 2.1 GiB checkpoint and a
5.9 s build. The ranking is not predictable from model size; it is predictable
from reading what the kit does at import and at first call.

| provider | cold | held | gain | what residency actually keeps |
| --- | --- | --- | --- | --- |
| RFdiffusion3 | 19.4 s | 1.6 s | 12x | compile trace + CUDA graph |
| Chai-1 | 67.6 s | 25.7 s | 2.6x | six TorchScript modules |
| ESMFold2 | 2.7 s | 1.1 s | 2.5x | 25.6 GiB of weights |
| Boltz-2 | 110 s | 55 s | 2.0x | checkpoint + featurizer |
| Enformer | — | — | in-process | nothing to reload |

**A kit's `resolve()` has no single shape, and guessing costs a silent
zero.** Three kits, three signatures: Boltz-2's `resolve(mode)` returns a
mapping with `env`; OpenFold3's takes `(mode, home, ...)` and returns a
`Resolution` carrying `exports`; ESMFold2's takes `(mode, variant, kit_home)`
and returns one carrying neither, because that kit keeps its deployment
variables in per-card `configs/*.env` files and ships none for this card. The
probe tries the shapes it knows and *records the TypeError* when none fits,
which is how the fourth shape will be found. Before this, OpenFold3 silently
yielded a zero-variable row and its `alloc_expandable` lever read
`skipped reason=pending`; after, 37 variables and `state=on`.

**A third answer to "who holds the weights".** The first three providers split
between the worker holding them and the kit holding them. RFdiffusion3 gives a
third: upstream already memoises, so nobody should add another cache, and the
ready line says `engine:fast` rather than `worker` or `kit`. A provider still
has to know which of the three it is, and still has to say so.

**Two things that only appear when agents work in parallel.** `uv venv` writes
a `_virtualenv.pth` that broke OpenFold3's kit-hook detection, so a kit that
finds its hook by scanning `.pth` files needs the stdlib `python -m venv`. And
a shared scratchpad is shared: one agent's `weights.log` was overwritten
mid-download by a sibling writing the same filename. Neither is deep; both cost
an hour.

## 16. What the third provider changed

Chai-1 is the first whose upstream loads its model inside the call that uses
it. `chai_lab.load_exported` is not memoised and `run_folding_on_context` calls
it six times per fold, on top of a 5.4 GB traced ESM, so a per-request process
re-reads all of it every time. Three folds of one input in a held worker took
67.6 s, 26.6 s, 25.7 s — the largest residency gain of the three providers, on
the upstream that does least to help.

**Who holds the weights is a decision, not a detail.** Under a kit mode the kit
replaces `load_exported` with its own loader and refuses to activate if
anything replaced it first, so a worker that memoises it itself silently turns
the whole kit off. Under `mode = "off"` nothing replaces it and the worker
should. A provider wrapping a kit must know which of the two it is doing and
say so — Chai-1's worker reports `weights_held_by` on its ready line and in
every reply.

**A kit's environment row is not always in its mode table.** `chai1_opt` keeps
the allocator setting in `alloc.env_row()`, documented as the row for a *child*
process, and `boltz2_opt` keeps a 23-variable row in `modes.resolve()`. The
probe reads both, because what is written here is where to look, never what the
value is.

**`[kit] levers_off` exists for a lever that cannot win.** Chai-1's `alloc`
lever exports `PYTORCH_CUDA_ALLOC_CONF`, and `opt_core` checks "CUDA already
initialised in this process" before it checks "the variable already holds
exactly this value" (`mem/torch_alloc.py` `export()`). The kit's trigger is
`chai_lab.chai1`, whose own module body initialises CUDA, so the answer is
always yes — and one opt-in refusal takes the whole mode to NOT ACTIVE. Setting
the variable before the process starts and declaring the lever off keeps the
policy in force (`alloc_effective=true` on the kit's own EXIT line) and costs
only the bookkeeping, which the kit then records as a PARTIAL activation. That
is the accurate word and the manifest says why.

## 17. What the second provider changed

Enformer was brought onto the standard next, deliberately unlike the first, and
four things that looked settled after one provider were not.

**Activation is usually a variable, not a launcher.** Boltz-2 ships
`worker_launch` and it is the only kit of the thirty-six that does. The common
form (30 of 36) is a `.pth` that imports the kit's `_autoload` at interpreter
start and patches the model package in place when the kit's mode variable is
set; the worker is then just a script the model's interpreter runs. Which one a
kit uses is detected, not declared. The variable's name is read from the kit —
`modes.ENV` where there is a modes module, `_autoload.ENV` where there is not —
because guessing it from the slug is how a renamed kit silently runs stock.

**One kit cannot be made resident with its levers at all.** ChromBPNet says so
itself: "THE ONE DEVIATION from an in-process hook: the kit's form is a
replacement entry script; it offers no in-process patch." Its finder fires only
for the stock console script and then runs a child. A provider like that
declares `mode = "subprocess"` with the reason.

**A kit's own `check` does not check its own architecture.** Enformer's reports
`DRY mode=exact gpu=NVIDIA GB10(sm121) build=sm_90-ptx` on this box and exits 0
— the GPU architecture its CUDA objects target, which says nothing about the
ELF machine type of the file holding them. Both of its prebuilt objects are
x86-64. Eight of the thirty-six kits carry prebuilt host objects; all thirty-nine
such files are x86-64 and none is aarch64. `setup` now reads the ELF header
before installing and refuses by name, instead of letting it surface as an
`ImportError` reading "cannot open shared object file" — `dlopen`'s wording for
a file that is sitting right there.

**A lock can pin an architecture by URL.** Enformer's pins
`nvidia-cudnn-frontend` by direct link to its x86-64 wheel, though the same
version publishes an aarch64 one. A provider whose shipped lock deviates from
its kit's says so in the lock's own header.

Two more things generalised rather than broke. The weights step grew a declared
`fetch`, because not every kit fetches weights in its install step and some
models pull their own from a hub at first load — still without restating a URL.
And the smoke request's input key became neutral, since `yaml` was only ever
Boltz-2's word for it.
