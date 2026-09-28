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

**Can its pinned torch drive this card?** Five kits pin torch below 2.7, whose
CUDA builds stop at sm_90: flashzoi (2.5.1), proteinmpnn (2.5.1), rfdiffusion1
(2.4.0), caliby (2.6.0), plus borzoi which is TensorFlow. Seventeen pin 2.7 or
later. `setup` now reads `torch.cuda.get_arch_list()` after installing and
refuses `torch_arch_unsupported` rather than letting it arrive as a kernel
error — but the rule is binary compatibility, not equality: an sm_120 cubin
runs on sm_121, which is how both of this project's stacks drive a card neither
of them lists.

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
| The worker/manifest/launch contract | three providers, three upstreams |

## 12. What the third provider changed

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

## 13. What the second provider changed

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
