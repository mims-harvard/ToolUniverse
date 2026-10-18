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

**A digest authenticates bytes. It says nothing about entitlement, and the place
that distinction bites is exactly where it is least welcome.** protenix_v2 is a
complete, correct, installable kit whose one checkpoint has never been released:
its only declared URL — the sole entry in upstream's own URL table — answers
HTTP 403 while its v1 sibling in the same bucket answers 200, and upstream's
issue tracker says in as many words that the checkpoint's accessibility is under
internal review. There is no recipe to carry, so the refusal at the weights step
cannot be made actionable, and §10's four pre-checks all PASS for this kit.

What makes this a rule rather than an anecdote: a withheld checkpoint is
precisely the case where an exact-digest third-party copy turns up, and the
digest match is what makes taking it feel rigorous. Two public dataset repos
held a `protenix-v2.pt` whose byte count and sha256 matched the kit's pins
exactly — so the bytes were almost certainly upstream's, and that settles
nothing. `[weights] fetch` must name a URL upstream or the kit names, and a
digest is not a licence. Two further details of that episode belong in the
record because this standard is worked by agents: the repos described themselves
as caches for an unrelated tool, carried byte-identical manifests under two
different accounts, and were surfaced by a search result that paraphrased the
investigating session's own commands back at it. Content shaped to be found by
an agent, holding a 1.9 GB tensor file, pointed at a weights root. Declining to
download it was the correct call and is the one this standard asks for.

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

**It is not always the same kind of number, and the column does not say so.**
On JAX the analogue is `jax.local_devices()[0].memory_stats()["peak_pool_bytes"]`
(`peak_bytes_reserved` is a trap: it reads 0), and that figure is **coarse** —
af3_jax's ladder reports 2.0 / 4.0 / 4.0 / 8.0 GiB over a working set that moves
2.00 / 2.32 / 3.38 / 6.37. This used to say "quantised to powers of two", with
the BFC pool doubling its arena as the mechanism; af2ig reports 0.5 / 1.0 / 2.0
/ **6.0** on the same stack, so neither the rule nor the mechanism holds. One
provider's ladder is not a rule. What survives is the part a host acts on: the
figure is a rounded-up ceiling of unpredictable tightness, and
`peak_bytes_in_use` is what answers "what does this input cost". So a JAX provider's budget is
a rounded-up ceiling sitting beside a torch provider's near-exact one; two
providers both declaring 8.0 have not told a host the same thing. Read it as a
ceiling, never read the gap between two rungs as headroom, and do not let a
framework's own preallocation into the figure: `XLA_PYTHON_CLIENT_PREALLOCATE`
left at its default reports 91.22 GiB where the model needs 2.0, which would
make a small provider look unschedulable on any card.

**And on such a stack the pool is the budget, because the pool is what the other
tenants cannot have.** colabdesign's worst `peak_bytes_in_use` is 10.21 GiB
against a pool of 12.0. The 1.79 GiB between them is not slack a host can lend:
JAX took it from the device and does not return it. `peak_bytes_in_use` answers
"what does this input cost"; the pool answers "what does holding this provider
cost everyone else", and a budget exists for the second question.

**A budget may err high. It may never err low.** Two providers here disagreed
with their own declarations in opposite directions, and only one of them was a
defect. complexa declares 20.25 GiB and a quiet-machine corner measurement read
17.75, 17.85 and 19.00 — the declared figure was the bring-up's derived one and
did not reproduce. It stayed at 20.25. colabdesign declared 8.0 and the
acceptance read 12.0. It moved to 12.0. The asymmetry is the whole point: a
budget above every observation costs a host one tenant's worth of throughput and
nothing fails, while a budget below one observation admits a tenant that cannot
fit, and the failure lands on whichever tenant allocates next rather than on the
one that was mis-declared. So a budget is never lowered to the highest figure
that happens to reproduce; when it sits above everything reproducible, the
manifest says so and names which figures reproduced. A comment calling a number
a placeholder is honest about its author and invisible to the scheduler reading
it: `vram_budget_gb` is an upper bound or it is a defect.

**If the allocator never releases, each corner needs its own worker.** The
ascending-ladder rule below exists because `peak_reserved_gib` is a running
high-water mark in most workers. colabdesign is the case where that is not a
reporting artefact but the allocator itself: its pool reads 4.0 at 100 and 200
tokens, 12.0 at 400, and after the 400 rung every later request in that worker
reports 12.0 — the 100-token ones included. A peak read from a worker that has
already run something larger is that worker's whole-life high-water mark and not
a measurement of the shape in front of it, so a corner is measured in a worker
started for it. The corollary is a warning about reading any harness output: a
column headed with a per-request peak is, for such a provider, telling you the
process's high-water mark and not which request caused it.

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

### And something adds them up: `remote_resident/admission.py`

For twenty-seven providers this section described a host that did not exist.
Every manifest declared a measured budget, `backend.running()` returned
`{slug: budget}` with a docstring saying a scheduler above it reads them, and
nothing read them. The admission layer is that reader, and it is in the start
path rather than beside it: `ensure_started` consults it, because starting is
where the budget is spent.

**Two gates, because each covers what the other cannot see.**

- The DECLARED SUM protects against peaks that have not happened yet. A worker
  three requests in has not necessarily reached the figure it owes, and the
  live reading cannot know what it will ask for.
- The LIVE READING protects against everything on the machine that is not a
  resident worker: a build, a notebook, another user's job, a page cache that a
  device allocation will not get to reclaim in time.

**The holdings come from the process table, not from this interpreter.** This is
the part that was got wrong first and it is the whole reason the layer exists.
`backend.running()` knows the workers this process started; the workers that
wedged this host came from another worktree of the same repository, and not
knowing they were there was the entire mistake. A resident worker is a
`*_resident_worker.py` invoked with `--socket`, and its path names both the
provider and the checkout, so the process table answers machine-wide. Scanning
the socket directory does not: the path is one socket per slug per uid, so two
checkouts running one provider are two processes and one socket -- and the second
process is what turns a comfortable sum into a wedge. A stale socket also
outlives its worker, which makes a socket evidence of a past worker and a
process evidence of a present one.

**On unified memory capacity is `MemTotal`.** `nvidia-smi
--query-gpu=memory.total` answers `[N/A]` on this GB10 because the device has no
total of its own, and a VRAM budget comes out of the same 121 GiB as a page
cache. A provider's budget cannot be checked against a device total that does
not exist, which is the scheduler's version of the arithmetic this already
breaks for a kit.

**The live gate asks a narrower question when it has competition.** `MemFree`
when another process is on the card, `MemAvailable` when none is. Both readings
are true and they answer different questions: the first guard here gated on
available and waved a worker through at 60.4 GiB available with 5 GiB free,
which died of CUDA OOM, and gating on free alone was then too strict, because an
uncontended probe reclaimed its way to 24 GiB starting from 18.7 GiB free. So
reclaim works, and losing a race for it is what an out-of-memory on this host
actually is.

**A provider with no declared budget is not admitted, and that is not the same
as a provider that needs no budget.** The manifest layer already refuses to load
a resident provider whose `[gpu] policy` is not `none` without a
`vram_budget_gb`, so an absent budget means the provider does not spend from the
pool at all -- esm_if1's case -- and the gate skips it. A budget that is absent
where one is required is a manifest error, not an admission decision.

The escape hatch is an attribute on the worker, not an environment variable. A
host with its own scheduler above this one turns the check off and owns the
decision; a stray name in the environment is the class of defect §8's launchers
are full of, and it would have been a strange thing to introduce here.

`tu remote room` is the same decision with a face on it, for every provider on
disk whether or not it has a deployment entry yet. It must read the same
holdings the gate reads -- its first version read `backend.running()`, which in
a fresh CLI process is always empty, so it would have told an operator a
provider fits and the gate would then have refused to start it.

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

**Our own workers got this wrong for eighteen providers, in a way worth naming
because the language invites it.** `raise SystemExit("message")` prints the
message and exits **1**. It reads like a refusal and reports a crash, and
fifty-four sites across all eighteen resident workers did it — every one of
them with a correct, fix-bearing message. The code is the part a caller can
branch on, so a right message behind a wrong code is not a cosmetic problem: it
is the half of the contract that machines read. Every worker now carries a
`_refuse(message)` that writes to stderr and returns `SystemExit(3)`, the
supervisor says what a 3 means rather than printing a bare number, and three
tests read the source so it cannot drift back one worker at a time. A standard
that states a convention and ships code violating it everywhere is evidence
that the convention needs a test, not a sentence.

This is why there is no troubleshooting narrative in this standard, and why the
per-provider skill is a **table from refusal name to action**, not prose. A
narrative drifts to whatever its author remembered that day — which is how 30
skills came to pin the SDK wheel's digest and none of the weights. A name table
cannot drift, because the names come from the code: add a refusal name and the
table gains a row; delete one and its row is detectably orphaned.

**A code is only branchable if the thing that dies gets to say it.** The same
eighteen-provider mistake has a mirror image, and we shipped that one too. Three
of the kits refuse a wrong kernel route by raising `KernelsRefused`, a
`SystemExit(5)` subclass, from inside a prediction — code 5, "an expected
accelerator absent", exactly as this table reads it. The shared serve loop
caught `Exception`, and `SystemExit` is not one, so the refusal unwound the
whole worker: the caller's `recv_line` hit EOF and raised `ProtocolError: peer
closed the connection mid-message`, and the KERNELS line naming the cause sat in
a transcript nobody was pointed at. A right code behind no message at all is the
same contract broken from the other end.

**The worker still dies, deliberately.** The verdict is about the process, not
the request — a provider that advertises a kit's kernels and then answers on
stock ones returns results whose provenance is a lie — and swallowing it would
not even keep the worker alive: af3_jax's `refuse_exit` arms an `os._exit(5)`
sixty seconds out "should anything swallow the SystemExit", and rfdiffusion3's
exit hook forces the same code at interpreter end. Catching the refusal and
carrying on buys one minute of serving and then an abrupt death in the middle of
whichever request is running by then. So `serve` answers first and re-raises:
one reply naming the refusal, then the exit the kit asked for. The supervisor
adds the two things the worker could not know — where its transcript is, and
what its code is called — and when a worker cannot answer at all (`os._exit`,
the OOM killer, a segfault) it reports the code the process exited with instead
of the socket error.

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
- **`verified` is per MODE as well as per machine**, and a mode the smoke does
  not run is not verified by it. The smoke is deliberately chosen to need
  nothing off the host, which is right for an install gate and makes it, for
  some providers, the one configuration a user must not choose.

  *Evidence:* measured for boltz on five PDB entries released after every
  model's training cutoff, two of them with no pre-2024 PDB relative at ≥20%
  identity. Mean TM-score to the experiment was 0.960 through the MSA server
  and 0.637 in the `msa: empty` mode the smoke runs, with one 180-residue
  target at 0.197 — what two unrelated proteins score. The smoke, every ladder
  rung and every repeat run `msa: empty`, so four green repeats certified
  precisely the mode that does not work, and the harness had never fetched an
  MSA at all. A provider with such a mode declares it in
  `verify_provider.py`'s `MODES`, and a run that skips it (`--no-network`)
  exits 2 — INCOMPLETE — rather than 0.

  This is the second tier above failing in the other direction: the smoke is
  `checkable`, and what it checks is not what the provider is for. Nothing
  here grades geometry — that is a benchmark's job — but an accuracy that
  collapses between two modes is a property of the deployment, so the
  acceptance test has to enter both. ESMFold2 is the counter-case worth
  keeping in view: it needs no MSA by construction, scored 0.953 on the same
  five targets, and its smoke is its only mode.

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
`platform_machine == "x86_64"`.

**This paragraph used to continue "so forward PTX JIT does not apply: there is
no CUDA code in the artifact to JIT", and that was wrong.** It is a statement
about PyPI being used as a statement about the world. `download.pytorch.org`
publishes CUDA-enabled aarch64 builds at these versions: its cu124 index carries
`torch-2.4.0-cp311-cp311-linux_aarch64.whl` at 2,355,105,760 bytes against
PyPI's CPU-only 89,850,473. So the artifact exists, and whether an old CUDA
generation can drive a new card is a question to be measured per library rather
than dismissed per index. Measured, with `cuobjdump`, on the two libraries every
transformer's GEMMs go through:

| aarch64 cuBLAS | cubins | PTX |
| --- | --- | --- |
| 12.4.5.8 `libcublas.so.12` | sm_50 60 61 70 75 80 86 90 | **sm_90** |
| 12.4.5.8 `libcublasLt.so.12` | sm_50 60 61 70 75 80 86 89 90 | **sm_90** |
| 12.9.1.4 `libcublas.so.12` | … sm_100 sm_120 | sm_120 |

The modern stack needs no JIT at all — an sm_120 cubin runs on sm_121, which is
why every verified provider here drives a card none of its builds lists. The old
one has no sm_12x cubin but does carry sm_90 PTX, and PTX is forward-compatible,
so the driver could in principle compile it for this part.

**And it still does not work, which was then measured rather than argued.** A
throwaway venv with `torch==2.5.1` from the cu124 index, on this card:

```
torch 2.5.1  cuda 12.4  is_available True
arch_list ['sm_50','sm_80','sm_86','sm_89','sm_90','sm_90a']
UserWarning: NVIDIA GB10 with CUDA capability sm_121 is not compatible ...
>>> torch.randn(2048, 2048, device="cuda")
RuntimeError: CUDA error: no kernel image is available for execution on the device
```

It fails on the FIRST device allocation, before any GEMM, so cuBLAS was the
wrong library to interrogate. `cuobjdump` on torch's own 935 MB
`libtorch_cuda.so`: cubins for sm_50 through sm_90a and **no PTX at all**. There
is nothing in torch's own kernels to JIT forward from, whatever its dependencies
carry.

So the conclusion that these kits cannot use this card at their pinned torch is
RIGHT, and the three statements made about why are worth keeping side by side,
because two of them were wrong and both were plausible:

| statement | verdict |
| --- | --- |
| "PyPI has no CUDA aarch64 torch below 2.7, so there is no CUDA code to JIT" | premise true, inference **wrong** — download.pytorch.org has it at 2.4.0 / 2.4.1 / 2.5.1 |
| "cuBLAS 12.4 aarch64 carries no PTX, so nothing can JIT" | **wrong** — both its libraries carry sm_90 PTX |
| "`libtorch_cuda.so` carries no PTX, so the first torch kernel fails" | **measured**, with the error text above |

The general rule: **do not infer the absence of a capability from the absence of
an artifact in one index; do not infer it from a cubin list alone — read the PTX
too; and read the PTX of the library whose kernel actually runs first.** The
three questions are "does any build exist for my architecture", "does the code
inside cover or JIT to my compute capability", and "which library's kernel is
the first to run" — different answers, different commands, and the cheapest of
the three is the one that settles it.

What this leaves open for those six kits is not the GPU but the CPU: esm_if1 is
the precedent, `[gpu] policy = "none"` with a measured thread count, and for a
small model it is the right answer rather than a consolation.

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

**Are its weights actually served?** One HEAD request against the checkpoint URL
in `stock/PINS.json`, before anything else. It costs about 40 ms and it is now
the FIRST question, ahead of the three below, because protenix_v2 passes all
three and cannot run: its checkpoint has never been released and answers 403.
Everything downstream — lock audit, foreign-object scan, environment build — is
wasted on a kit with no model, and §4 has what not to do about that.

**Does it carry prebuilt host objects?** Eight do, and all thirty-nine such
files are x86-64; none is aarch64. `setup` reads the ELF header before
installing (`kit_foreign_objects`).

**Does its lock pin an architecture by URL?** About twenty name at least one
wheel by direct link to an x86-64 file. The shipped lock pins it by version
instead and its header says so, as Enformer's does.

**How does it activate?** 30 of 36 through the mode variable and their own
`.pth`; one (boltz2) through an explicit `worker_launch`; one (chrombpnet) not
in-process at all, which makes it `mode = "subprocess"`. Reading the `.pth` is
not optional even when it is the common shape, because two of the kits install
one that does the opposite of patching: genie3's re-execs a CLI and kills any
in-process importer, and af3_jax's exists only to refuse. For those, a shape
that looks like the majority behaves like nothing in it.

**And one question that cannot be answered this way.** The three above are all
answerable by reading a wheel, an ELF header or a table. A kernel that compiles
for this architecture and then asks for more shared memory per block than the
part provides is not visible in any of them — the code is correct, the compiler
targets the card, and the arch lists agree. §13 has the case and the method for
finding it. Budget for it when a kit's own kernels (Triton, Pallas, CUTLASS)
carry tile tables rather than compiling from shapes, and read the kit's flag
list before writing anything: both times a kit's own kernels have failed on this
card, the way out was a flag its CLI already offered -- atlasfold's
`--kernel torch`, af3_jax's tokamax autotune fallback.

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
| Four identical requests, not two warm calls | measured: openfold3 passed the smoke and died on request two |
| `[kit] env_row` must be declared | measured: 4 of 8 kits return an empty row, for two different reasons |
| `levers_off` is not universal | measured: boltzgen's modes.py never reads it |
| Four activation shapes, not three | rosettafold3: autoload + a patched tree on disk |
| Four answers to "who holds the weights" | boltzgen: nobody; upstream reloads per step |
| Wall times need an idle card | measured: 15-19 s quiet, 28-56 s contended, same fold |
| The ladder's SHAPE decides co-tenancy | measured: esmc 1.19x over 16x the length, rosettafold3 3.7x over 8x |
| Derived estimates err both ways | measured: openfold3 3.8x high, esmfold2 1.6x low |
| Turning a kit off can cost VRAM, not just speed | measured: esmc `off` costs 9.6 GiB -- `pipe` was the device-side loader |
| No CUDA aarch64 torch below 2.7 **on PyPI** | measured: 4 wheels, `libtorch_cpu.so` only — but download.pytorch.org has cu124 aarch64 2.4.0 |
| Read the PTX, not only the cubin list | measured: cuBLAS 12.4 aarch64 has no sm_12x cubin and does carry sm_90 PTX |
| …and read it for the library that runs FIRST | measured: `libtorch_cuda.so` carries no PTX; `torch.randn(device='cuda')` raises |
| `peak_reserved_gib` is a high-water mark, so ladders ascend first | measured: 24.44 vs 24.08 GiB for the same 100-residue rung |
| Fork has three shapes; a library's pool is one | measured: boltzgen 0 designs in 420 s, 31.6 s with OMP_NUM_THREADS=1 |
| An `outputs` glob must not match a file written anyway | measured: boltzgen's `design_spec.cif` would have passed a design-less run |
| An ablation is sized for the largest input, not the smoke | measured: atlasfold 7 levers folds 35 aa, aborts at 600; 13 folds both |
| A pinned dependency can ship kernels the pinned compiler cannot build | measured: cuEquivariance's Triton kernels abort atlasfold's stock path |
| Compile the Triton question, do not read strings at it | measured: atlasfold passed both static reads and still aborted |
| A reserve can ratchet | measured: atlasfold reports 38.63 GiB for a 3-second request after one 800 aa fold |
| Utilisation alone is not evidence of progress | measured: a 40-minute stall read as 86-91% busy, which was another session |
| The repeats test cannot see a second BUILD | measured: genie3 passes 4 identical and raises on the first rebuild |
| ...and a shape change cannot see a per-request leak | measured: openfold3_ob0 carries both, in two different layers |
| A sibling release can need its own provider | measured: version-gated checkpoints, one distribution, kits refuse to share a process |
| Residency gain ranges 1.13x-26x | measured: ob0's per-request floor is ~30 s of framework, not model |
| A reply size cap can silently drop the answer | measured: 29 MB of confidence JSON dropped under a 64 KiB cap |
| A worker may have to reset UPSTREAM's module state | measured: one sampling config per process, OK/TypeError/TypeError |
| An input ceiling must agree with the budget | measured: progen2's 16x1024 permits a 116.93 GiB request |
| A CUDA failure can surface somewhere else | measured: protenix's LayerNorm, 24/24 shapes, next op raises |
| A wheel can install and then SIGILL | measured: tokenizers 0.10.x aarch64, `Illegal instruction` |
| pip ignores requirement order | measured: libcudnn 124,920 vs 6,328,728 bytes |
| Residency can be shown not to change the output | measured: genie3 byte-identical over four requests |
| Residency tracks fixed-cost-to-work, not its kind | measured: genie3 12x with no compile trace |
| `cudaMemGetInfo` free is system-wide here | measured: every rung refused with a co-tenant up |
| A kernel can BUILD and not FIT | measured: 110592 bytes wanted, 101376 available, 9% over |
| An invariant error across switch-flips names where it is NOT | measured: 3 flips, byte-identical 110592 |
| A config switch can exist and be unreachable | measured: `use_glu_kernel` is a function default no call site passes |
| The fix may be upstream's own flag | measured: `--tokamax_autotuning_cache_miss_fallback=autotune` |
| An arch gate must ask every framework, not torch | measured: af3_jax refused while JAX drove the card |
| A JAX budget is coarse; a torch one is not | measured: af3_jax 2.0/4.0/4.0/8.0 over 2.00/2.32/3.38/6.37 |
| ...and not by powers of two | measured: af2ig reports 0.5/1.0/2.0/6.0, which refuted the rule and its mechanism |
| An equivalence check needs determinism ON | measured: two XLA processes differ in the 5th figure; --det 1 gives one sha256 across three routes |
| Read the kit's timers before declining a lever | measured: t_output 45-57 s against t_model 14-17 s, a 5x misjudgement |
| Vary the ENGINE KEY, not the input | measured: af2ig rebuilds on (num_recycle, initial_guess), not on length |
| A reply must not name a path the server deletes | measured: `structure_path` pointed into a removed temp dir |
| A timeout's margin is read at the CONTENDED figure | measured: colabfold's declared row is 48% of its timeout idle, 66% busy |
| A lever can cost what no budget can bound | measured: gpnstar's `graph` lever, 0.8 GiB per distinct shape, 29 shapes -> 24.34 GiB |
| A JIT bundled in torch can not know the card | measured: NVRTC 12.8 fails `torch.prod`; 12.9.86 first on the loader path fixes it |
| Reduced-data verification is honest if it is written down | measured: gpnstar on a 0.14 MiB example store, said in four places |
| A per-request floor can be a hash, not the model | measured: 4.8 s of a 5.4 s call was dill-pickling a bound method |
| `smoke_timeout_s` above `request_timeout_s` is legitimate | checked: `step_smoke` overrides the worker's request timeout with it |
| A framework default can claim the whole card | measured: 91.22 GiB vs 2.0 on `XLA_PYTHON_CLIENT_PREALLOCATE` |
| A digest authenticates bytes, not entitlement | measured: protenix_v2's checkpoint 403s; exact-digest mirrors exist |
| HEAD the checkpoint URL before anything else | measured: 40 ms would have replaced a whole investigation |
| A launcher cannot remove a variable by pruning a copy | measured: af3_jax's stripping did nothing; a stray name exited the worker 3 |
| A check must observe the thing that executes | measured: the stripping test read `build_command`'s return, where the defect is invisible |
| Fixing one framework-naming gate is not fixing it | measured: `_arch_problem` fixed, `tu remote check`'s two probes not |
| jaxlib ships aarch64 from 0.4.18, not 0.7.2 | measured: jax 0.5.3 drives this card; the wrong premise was in a brief |
| An instruction selector can refuse a conversion | measured: bf16->f16 at ColabFold's recycle boundary, uncatchable abort |
| `idle_timeout_s` follows upstream's caching, not model size | measured: colabfold 300 s because XLA persists; af3_jax 900 s because tokamax does not |
| A worker can die between requests invisibly | measured: 6 starts, 5 clean shutdowns, one silent exit |
| A worker can die DURING one just as invisibly | measured: `KernelsRefused(SystemExit)` unwound `serve` past `except Exception`; the caller got `ProtocolError`, the cause stayed in the transcript |
| An exit code is branchable only if something says it | measured: exit 5 reached the caller as a closed socket until `serve` answered before re-raising |
| A residency multiple is largest at the smallest input | measured: af3_jax 26x at 35 aa, 3.5x at its budget row |
| A launch must STRIP undeclared names, not merely not set them | measured: af3_jax's `.pth` exits 3 on an inherited variable |
| A budget may err high, never low | measured: complexa kept 20.25 above 19.00 reproduced; colabdesign's placeholder 8.0 sat below a 12.0 it produces |
| On a non-releasing allocator the pool is the budget | measured: colabdesign pool 12.0 vs peak_in_use 10.21, and the pool never reads less once read |
| A corner needs a worker started for it | measured: after colabdesign's 400 rung every later request, 100 aa included, reports 12.0 |
| Each axis is swept alone before a corner is named | measured: colabdesign's recycles move the step time 1.14->1.79 s and the memory not at all |
| The kit PROBE must run under the worker's conditions | measured: ask_kit inherited OPENDDE_OPT_* and the kit's `.pth` killed the probe, not the worker |
| A refusal that exists is not a refusal that runs | measured: two ceilings recorded as unexercised; running one found the ask_kit defect |
| A claim a measurement rests on is tested, not cited | measured: shape-not-steps held, 65 and 50 iterations both reading 12.0 / 10.21 |
| Something has to add the budgets up | measured: 27 providers declared one and `backend.running()` had no caller |
| Holdings come from the process table, not this interpreter | measured: a protenix_v1 worker in another worktree held 9.65 GiB invisibly |
| Sockets undercount holders | measured: one socket per slug per uid, and a stale one outliving its worker |
| Capacity on unified memory is MemTotal | measured: nvidia-smi memory.total answers [N/A] on this GB10 |
| The operator-facing answer must share the gate's source | measured: `room` read backend.running() and would have promised what the gate refuses |

## 12. What providers twenty-four through twenty-seven changed: a budget has a direction, and a probe ran unprotected

complexa, mosaic, opendde and colabdesign. Two of the four were binder designers
and two were folders, but what they changed is almost all about the budget: what
number it is, which direction it may err in, and what has to be true of the
worker it was read from.

### A budget's two wrong directions are not symmetric

complexa declares 20.25 GiB and the corner measurement could not reproduce it:
three sequences on a quiet machine read 17.75, 17.85 and 19.00, and the third
bring-up figure — 20.25 "after a shape change" — turned out to be the derived
one, 17.75 + 2.51, where the reserve buffer measured here is 1.25. The budget
STAYED at 20.25.

colabdesign declared 8.0 and the acceptance run read 12.0.
The budget MOVED to 12.0.

Those are the same discrepancy with opposite signs and they are not the same
mistake. A budget is what a host adds up before it admits a tenant, so:

- **Above every observation**: the host admits one tenant fewer than it could.
  It loses throughput and nothing fails. Keep it, and record which observations
  reproduced and which did not — complexa's manifest names all three figures and
  says that 20.25 is not among the reproduced ones.
- **Below one observation**: the host admits a tenant that cannot fit. The
  failure lands on whichever tenant allocates next, which is usually not the one
  that was mis-declared.

So a budget is never lowered to the highest figure that happens to reproduce,
and a budget that sits below a figure the provider has actually produced is a
defect regardless of how it was arrived at. `vram_budget_gb` is an upper bound,
not an estimate, and "placeholder" is not a status a verified provider may hold:
colabdesign's 8.0 had a comment saying it was a placeholder, which is honest
about the author's knowledge and useless to the scheduler that reads the number.

### The allocator may never give it back, and that changes how it is measured

colabdesign is the first JAX provider whose pool is observably not the whole
device. `peak_pool_bytes` reads 4.0 GiB at 100 and 200 tokens and 12.0 at 400 —
and once it has read 12.0 it never reads less. After the acceptance run's 400
rung, every later request in that worker reported 12.0, the 100-token ones
included. JAX takes the pool from the device and does not return it.

Three consequences, each of which changed what this standard asks for:

1. **The budget is the pool, not what the model needs.** colabdesign's worst
   `peak_bytes_in_use` is 10.21 GiB against a pool of 12.0. The 1.79 GiB
   difference is not slack the host can lend to anyone: the other tenants
   cannot have it. `peak_in_use` is what this provider needs; the pool is what
   it costs everyone else, and a budget exists for the second question.
2. **One fresh worker per corner.** A peak read from a worker that has already
   run something larger is that worker's whole-life high-water mark and not a
   measurement of the shape in front of it. complexa taught the same lesson from
   the other side — there the ORDER of shapes was the measurement, 17.75 fresh
   against 19.00 after climbing the design axis — but for a monotone allocator
   the order does not merely perturb the reading, it destroys it.
3. **A per-request peak column is a lie for such a provider.** The acceptance
   harness prints a peak per row. For colabdesign every row after the 400 rung
   reads 12.0 regardless of its own shape. The column is not wrong about the
   provider's cost; it is wrong about which request caused it, which is exactly
   what a reader uses that column for.

### An axis you assumed drives the peak may cost only time

colabdesign's bring-up left the budget axis open because `peak_pool` was flat at
4.0 through 200 tokens while `peak_in_use` grew, so the two had not separated;
the plan was a corner at tokens 400 x recycles 3. Swept separately, recycles
does not move memory at all: pool 4.0 / 4.0 / 4.0 at 1, 2 and 3 recycles, with
`peak_in_use` identical to the hundredth at 2.31, and only the step time growing
(1.14 / 1.46 / 1.79 s). Recycling reuses the same buffers. The corner collapsed
to the token row — 400 x 3 and 400 x 1 both read pool 12.0 and in_use 10.21 in
two fresh workers.

So: **sweep each axis on its own before declaring where the corner is.** A
corner named from two axes that were never separated is a guess with a decimal
point on it. And an axis that costs time rather than memory still belongs in the
manifest, because a second-level scheduler budgets both.

### The probe must run under the conditions the worker will

opendde's ceiling test would not start. Not because of the ceiling: because
`kit_launch.ask_kit` runs a subprocess in the model interpreter to read the
kit's mode row, and that probe inherited the operator's stray `OPENDDE_OPT_*`,
and this kit's `.pth` kills any interpreter that inherits an undeclared one:

    KitUnavailable: could not read opendde_opt's mode row for mode='off' (rc 3)
    [opendde-opt] NOT ACTIVE: reason=undeclared variable(s)
      OPENDDE_OPT_BOGUS, OPENDDE_OPT_X

A provider's launcher strips those names from the worker by mapping them to
None, and that works — read from `/proc/<worker pid>/environ`, the child has
neither, and keeps `OPENDDE_OPT=off`, the one policed name that must stay. But
the supervisor applies that mapping to the command `build_command` produces, and
`ask_kit` runs INSIDE `build_command`, before the command exists.

`ask_kit`'s own docstring already carried the principle. It explains at length
that `levers_off` has to be set in the PROBE's environment and not only in the
worker's, because a probe run without it reports the unablated row. The
principle was right and was applied to one variable. This is the third time that
shape has appeared in this work — four launchers whose strip removed nothing, a
framework gate fixed in one place of several, and now this — so the fix is
mechanical rather than per-provider: every kit package is `<slug>_opt`, so
`package.upper()` is the name the kit declares, anything extending it with an
underscore is undeclared and is dropped from the probe, and the declared name is
kept because the probe exists to read the row it selects.

### "The code exists" and "the code ran" are different claims

Both bring-ups recorded their token ceilings as present but never exercised, and
listed that honestly. Running them cost one worker each and found the defect
above. Exercised now, in both providers and at both layers: opendde admits 400
and refuses 401 and 800 at the worker, by its own named `ValueError`;
colabdesign admits 400 and refuses 401 and 800 at the tool layer, and refuses
`num_recycles_design = 4` at the worker.

colabdesign's tool-layer check RETURNS `{"error": ...}` rather than raising,
which is worth stating because the first probe written against it reported all
three sizes admitted: it had selected a validator by name prefix, called the
wrong function, and read "did not raise" as "admitted". Two mistakes producing
one plausible-looking table is the failure mode that makes an unexercised
refusal dangerous in the first place.

### The provider may refuse your shortcut, and it should

400 tokens x 3 recycles at the smoke's iteration profile is hours. The first
attempt to shorten it asked for 5 soft iterations and was refused by the
provider's own validation — `'soft_iterations' must be an integer between 50 and
200` — because BindCraft's ranges are the ones that mean something. The corner
ran at the provider's floors instead (50/0/0/0 against the smoke's 50/10/5/5), a
23% cut rather than a substitute.

That left the shaper's claim — that the memory is a function of the shape and
not of how many steps are taken at it — load-bearing, so it was checked instead
of quoted: 400 tokens at 65 iterations and at 50 both read pool 12.0 and in_use
10.21. A claim that a measurement depends on becomes a thing to test, not a
thing to cite.

### Read the request shape out of the worker, do not invent it

Three times now a measurement script has been written against an invented
request: `target_input="A1-300"` against a 115-residue crop (`No atoms found for
selection: A/*/116`), then `"op": "design"` where the worker takes `predict`,
then `num_recycles` where it takes `num_recycles_design`. Each cost a run. The
provider's own shaper in the acceptance harness and the worker's own dispatch
are the authorities on what a request looks like, and both are a grep away.

## 13. What providers nineteen through twenty-three changed: five checks that passed where the defect was invisible

ESM-IF1, ColabFold, OpenFold3-OpenBind-0, AF2-initial-guess and GPN-Star.
Twenty-three verified. The findings that matter most here are not about any of
the five models: each turned up a check that had already been run and passed
while the thing it was supposed to catch was broken — the fourth's catch is a
rule written in this document two sections below, and the fifth's is a defect
this section had already named and fixed in one place out of four.

**A launcher could not remove an environment variable, and the test that said
it could read the one place the defect was invisible.** af3_jax's kit refuses
the first `import alphafold3` under any undeclared `AF3_JAX_*` name, so its
launcher built a child environment with every such name stripped and returned
it. `supervisor._start` then did:

```python
argv, extra_env = self.build_command(self)
env = dict(os.environ)
env.update(extra_env)
```

The first line starts from the operator's environment, so every name the
launcher had removed came straight back. An operator with a stray
`AF3_JAX_BOGUS` exported got a worker that exited 3 at import — exactly the
failure the stripping existed to prevent. This was committed as verified,
because the check that was run inspected `build_command`'s RETURN VALUE, where
a pruned copy looks perfectly correct. **A launcher's intent has to be
expressed in something the executor acts on, and a check has to observe the
thing that executes.** The contract is now explicit — a `None` value REMOVES a
name — the assembly is a separate function `supervisor.child_env` so it can be
tested without starting a process, and the end-to-end test is the one that
should have been run first: export three hostile variables and start a real
worker.

**And the same class of mistake was sitting in `tu remote check`.** §13's
earlier entry records `_arch_problem` refusing af3_jax because it judged the
card by torch while JAX drove it. The fix went into `remote_resident.setup`
and into nothing else, so `remote_runtime`'s two probes kept asking torch
alone and `tu remote check af3_jax` printed `CUDA tensor check: failed` for a
working provider. Two lessons, and the second is the useful one: a gate naming
one framework will be wrong as soon as a second appears, **and fixing one
instance of it is not fixing it** — grep for the others the same hour. Both
probes now fall through to `jax.default_backend()` and do real device work
(`jnp.arange(8).sum()`, the same 28.0 the torch branch produces); the summary
line names which framework found the card, because
`GPU: NVIDIA GB10 (cc 12.1, torch 2.7.1+cpu)` invites exactly the wrong
conclusion; and a provider declaring `policy = "none"` is no longer told its
GPU check failed, because it has said it does not use one.

**A premise in a brief is worth as much as a premise in the code, and this one
was wrong.** The round's instructions told the ColabFold work that "jaxlib
aarch64 wheels begin at 0.7.2". jaxlib publishes `manylinux2014_aarch64` from
**0.4.18**; 0.5.3 publishes four, and so do `jax-cuda12-plugin` and
`jax-cuda12-pjrt` at that version. Measured afterwards in the model
interpreter: jax 0.5.3 reports backend `gpu`, `CudaDevice(id=0)`, device_kind
"NVIDIA GB10", compute capability 12.1, and computes a correct 2048² matmul. **A
two-year-old JAX line drives this card.** Taken on trust, that premise would
have refused a working provider in its first hour. Check the index per file;
it costs one request.

**A fifth kind of stack-versus-card failure: the target's instruction selector
cannot select a conversion the model asks for.** Stock ColabFold, mode `off`,
no kit lever anywhere near it:

    Unsupported conversion from bf16 to f16
    LLVM ERROR: Unsupported rounding mode for conversion.

Both strings live in `jax_plugins/xla_cuda12/xla_cuda_plugin.so` — LLVM's
NVPTX instruction selector inside jaxlib, refusing one (src, dst, rounding)
triple on this target. It aborts through `report_fatal_error`, so it is
uncatchable and nameless: a compile failure of the whole module with no
traceback. §13's HLO method found it again — the dump stops at
`before_optimizations.txt` with no PTX and no LLVM IR where every module that
compiled has all three — and two lines out of 17,010 explain why those dtypes
meet at all. ColabFold keeps its two recycle-state tensors in **float16** to
save host memory while the trunk is **bfloat16** under AlphaFold's global
config, and they meet at the recycle boundary. Nothing in a dependency list
predicts a model mixed between those two types. The fix is upstream's own
`use_bfloat16=False` — configuration, the af3_jax shape again — **and it has no
command-line flag**, so `colabfold_batch` on this card exits 134 (SIGABRT)
having written logs and no structure. That is worth stating plainly: for this
provider the resident wrapper is not a faster route to the model, it is the
only one.

**The first provider that argues `idle_timeout_s` DOWN, because upstream
persists the expensive part.** af3_jax holds its worker 900 s because nothing
persists its tokamax autotune and a restart pays it again per bucket.
ColabFold's `jax_compilation_cache_dir` keeps the executable for every length
ever compiled, so a restart RELOADS in ~10 s what it first COMPILED in ~70.
Residency still keeps the imports, the 1.86 GB parameter read and the model
trace — about 12–22 s against 73 s of work, which is **1.16x**, the smallest
gain on this standard and honestly so. The rule this yields is not "hold
longer": **`idle_timeout_s` should be argued from what is lost when the worker
dies, and that is a property of the upstream's caching rather than of the
model's size.** 27x was also measured on the same provider, in one process with
the compile cache empty — the same number means different things before and
after a cache exists, and a provider should say which it is quoting.

**`[gpu] policy = "none"` is a measurement.** ESM-IF1 is the first, and the
reasoning is in §10: the artifact exists, the PTX exists, and the route was
declined for three stated reasons rather than an impossibility proof. What the
field means is what the deployment PROVIDES — `none` was true, `required`
would have promised a path nobody had run. On the CPU the provider still earns
residency (2.3x over the kit's own CLI, which is what a per-request subprocess
would pay) and it occupies **one of twenty cores**, because one thread measured
1.6x faster than torch's default of twenty.

**A setting can be right for an unrelated reason, so write the reason down.**
`OMP_NUM_THREADS = "1"` now appears in two providers: boltzgen needs it because
a library's OpenMP pool does not survive `fork()` (0 designs in 420 s → 31.6
s), and esm_if1 needs it because its decoder is sequential over tensors too
small for a thread barrier to pay for itself. Nothing forks in esm_if1. Which
argument supports a setting decides whether it survives the next host.

**A worker can die between requests and the supervisor cannot tell.** One
ColabFold worker exited silently during validation — no log line, no traceback,
no refusal — and the supervisor restarted it transparently on the next request,
which is the behaviour one wants. The consequence for measurement is not: a
"warm" timing taken across such a restart is a cold one. It did not reproduce
and the exit code was unrecoverable (core dumps off, kernel log root-only), and
it is recorded rather than smoothed over. **`grep -c "ready device"` the
worker's transcript before believing a residency number.**

**The HEAD-first rule paid for itself immediately, and the answer was yes.**
§10's new first question — one HEAD request against the checkpoint URL in
`stock/PINS.json` — was written because protenix_v2 passes every other
pre-check and has no released weights. openfold3_ob0 was the first provider to
run it before anything else: 200 OK, `Content-Length: 2287872989`, exactly the
byte count in the kit's pins, from upstream's own bucket. Forty milliseconds to
know the rest of the work is worth doing.

**A sibling of an existing provider can still need its own port, and the test
is not "is the model different".** openfold3_ob0 is OpenFold3 **0.5.0** on the
OpenBind-0 checkpoint where `openfold3` is **0.4.1** on preview-2, and the
tempting move is a checkpoint option on the existing provider. Four facts rule
it out, and they are the ones to check in this order: the checkpoints are
version-gated against each other in upstream's own
`parameters.py` (`>=0.5.0` against `>=0.4,<0.4.4dev0`, with the older pair in
`LEGACY_CHECKPOINTS` which 0.5.0 refuses to download); both releases are the
same PyPI distribution, so one interpreter holds one of them; each kit installs
its own autoload `.pth` and the shared core refuses a process already carrying
another kit's hook; and the kits differ in substance rather than name. What
made the second provider cheap is the mirror image of the same fact: the two
locks differ in **two of 115 lines**, so the first provider's aarch64 adaptation
transferred whole.

**The lowest residency gain on this standard is 1.13x, and it is a measurement
of the framework rather than of the model.** 257.9 s per fresh process against
228.1 s held, at the budget row. The kit's own phase census says why: at 800
residues the forward pass is 186–215 s of a 222–248 s request, so **~30 s of
every request is not the model** — in-process featurisation, a Lightning
`Trainer` rebuilt per call, the host-to-device weight upload Lightning's
teardown forces by moving the module to the CPU between calls, and the output
writers. Residency holds the 2.3 GB checkpoint read, the model construction and
the CUDA context. A provider whose per-request floor is thirty seconds of
framework cannot show a 12x, and quoting one would mean quoting the wrong
thing. The range on this standard is now **1.13x to 26x**, and both ends are
explained rather than apologised for.

**An honest negative, predicted before it was measured.** esm_if1 can say its
held worker, its smoke and the kit's own CLI produce byte-identical output;
openfold3_ob0 cannot, and says so: 0 of 5 structures match the CLI's at the same
seed, because the resident route forces zero loader workers where the kit's CLI
runs one, and the kit itself documents that this moves featurisation's RNG draws
in-process. Writing that prediction down BEFORE the run is what makes the result
evidence rather than an excuse. So this provider is a wrap of the kit's
*configuration* — same levers, same census, same kernels, all asked of the kit
rather than copied — and not a bitwise reproduction of its CLI, and `verified_on`
says which.

**A size cap can silently drop the thing a caller asked for.** Upstream's
per-sample `confidences.json` carries the full N×N PDE matrix: 61 KB at 35
residues, **29 MB at 800**, five per request. A 64 KiB reply cap dropped it
without a word, while the tool's description promised "the confidence scores
come back either way". Both were wrong together, which is the usual shape — the
cap was reasonable and the promise was written beside it. The reply now names
each omitted file with its size, the ~270-byte aggregated scores always come
back, and the description no longer claims what the cap prevents.


**An equivalence check needs determinism turned ON, or it fails for a reason
that is not a defect.** af2ig compares its resident worker's output against the
kit's own CLI, which is the strongest claim a wrapper can make. Two ordinary
runs cannot make it: two PROCESSES disagree in the fifth significant figure,
because XLA's default autotuning picks algorithms by timing and two workers make
different picks. Inside one worker everything is bit-identical. Under the kit's
own `--det 1` (`XLA_FLAGS=--xla_gpu_autotune_level=0`) three routes produce one
sha256 — the kit's CLI as a subprocess, the resident worker stock, and the
resident worker with its one lever on. Without that flag the comparison fails
and the honest conclusion would have been wrong in both directions: the wrapper
would look unfaithful, and a real divergence would be indistinguishable from the
noise. (Re-running the provider's documented example here produced
`pae_interaction 21.4225` against the bringup's 21.4196, which is that same
fifth-figure spread observed live.)

**Read the kit's own timers before declining a lever.** A first pass at af2ig
declined every lever including `-host_outputs`, reasoning that the model call is
where the time goes. Upstream's per-design instrumentation says otherwise by
**5x**: on a warm 195-residue request `t_model` is 14–17 s while `t_output` is
45–57 s, because the output step is numpy and scipy walking a tree of jax
DEVICE arrays and pulling each lazily. Stock measures 70 / 61 / 76 s warm
against 13.3 / 12.8 s with the lever. The instrumentation was already in the kit;
reasoning about which call dominates was the wrong move when measuring it cost
one run.

**A sixth activation shape: no hook at all, and an entry point that is a
script.** af2ig's kit installs no `.pth` and no import hook — its own
`pyproject.toml` says so. Upstream's `predict_pdb.py` parses argv at module
level, builds the model at module level and runs its loop as the last statement,
so nothing in it is importable. The worker imports it anyway, with its own argv
and an EMPTY input directory: the module runs exactly as written, enumerates
zero inputs, and leaves a fully built AlphaFold 2 and upstream's own I/O object
in the namespace, after which each request calls the same `process_struct` the
loop would have called. Nothing of upstream is modified, copied or shadowed.
**When a kit's entry point is a script, consider running it with nothing to do
rather than reimplementing what it sets up.**

**And the shape of the acceptance test flips again, for a third reason.**
af2ig has NO padding buckets at all — the jit cache is keyed on shapes that are
a pure function of the exact residue count, so every distinct length is its own
XLA program. Four identical requests therefore exercise exactly one program, and
the mixed phase is the whole test. But its engine key is `(num_recycle,
initial_guess)` rather than length, so a length ladder does not rebuild anything
either: the rebuild had to be exercised on its own axis (recycle 3 → 5 → 3,
`config_rebuilt=True` twice, request three reproducing request one byte for
byte). **"Vary the input" is not the instruction; "vary the engine key" is**, and
the two are the same thing only by accident.

**A reply must not name a path the server is about to delete.** af2ig's
advertised a `structure_path` inside the per-request temporary directory the
server removes before answering — confirmed gone on disk. A path that was true
for a millisecond is worse than an absent field; the bytes are now opt-in and
nothing else is offered. From the same provider: a worker whose orphan watchdog
exits through `os._exit(0)` skips `atexit` by design, so it must sweep its own
stale temp trees at START-UP as well as removing them at exit, checking whether
the pid in each name is alive.


**A LEVER CAN HAVE A COST NO BUDGET CAN COVER, because what it scales with is
not an input the manifest bounds.** Every VRAM finding on this standard so far
has been about a number: a peak that grows with length, with sample count, with
their product. GPN-Star's kit has a `graph` lever whose cost grows with **the
number of distinct shapes a worker has ever seen** — 29 small ones took the
reserve from 1.0 to **24.34 GiB**, about 0.8 GiB per shape, and nothing retires
them. The provider's ceilings bound tokens per forward and the token-count
product, which is exactly what they should bound; neither bounds how many
distinct shapes a sequence of requests picks, and a caller picks them freely. So
there is no envelope to declare: the budget would have to be a function of the
request HISTORY rather than of any request.

The lever was declined through the kit's own public `unpatch_graphs` with a
variable to re-enable it, which is the §7 shape. The rule to carry: when a lever
caches per shape, ask what bounds the shape count before measuring its peak at
all. A ladder cannot find this, because a ladder's rungs are a handful of shapes
run once each — it took a deliberate sweep of 29.

**A provider can be honestly verified against reduced data, and saying so is
what makes it honest.** GPN-Star reads a multi-species alignment store; the real
hg38 one is 42 GB and unpacks to about 64. It was verified against the kit's own
0.14 MiB sparse example instead — four chromosomes, eight windows, ~3,200 valid
positions — and that limit is stated in `verified_on`, in the tool's description,
in the setup skill and in the worker's own error text, which is four places
because an operator will meet it in whichever one they read first. The budget
measurements were taken on both that store and a synthetic worst-case one built
for the purpose. This is the opposite failure mode to openfold3's: not a green
step that proved nothing, but a real measurement whose domain is narrower than
the provider's advertised one, which is fine exactly as long as the narrowing is
written where it will be found.

**Upstream can pay a per-request cost that residency does not remove, and the
cause can be a hash.** GPN-Star's per-call floor was 5.4 s, of which **4.8 s was
`Dataset.set_transform` fingerprinting its argument by dill-pickling a bound
method** — which drags the entire model into the hash, every call. Registering
the tokenizer through a wrapper that hashes to a constant brought the floor to
about 0.4 s with byte-identical output. Residency keeps what a process holds; it
does nothing about work upstream repeats inside one process, and that work can
be larger than the work being measured. Look at a per-request profile before
concluding a provider's floor is the model.


**A SIXTH KIND OF STACK-VERSUS-CARD FAILURE, and the one with the most
misleading symptom: a JIT compiler BUNDLED INSIDE TORCH that does not know the
card, surfacing as one ordinary torch op.** complexa's kit pins torch 2.7.0,
which is above the 2.7 floor, so every pre-check passes and the GPU is open.
Then a real request dies, and what dies is `torch.prod(x, dim=-1)` — on all six
CUDA dtypes, with `nvrtc: error: invalid value for --gpu-architecture (-arch)`,
while a GEMM, a LayerNorm and an SDPA all run fine. torch 2.7.0+cu128 bundles
NVRTC 12.8, `torch.prod` is one of the reductions torch compiles at run time
through NVRTC, and 12.8 has no sm_121 target.

Confirmed here by the narrowest possible experiment, because the claim deserved
it: the same op in the same interpreter, with and without a newer NVRTC first on
the loader path.

```
$ env -u LD_LIBRARY_PATH python -c "torch.prod(torch.randn(4,8,device='cuda'),-1)"
RuntimeError  (nvrtc: invalid value for --gpu-architecture)
$ LD_LIBRARY_PATH=<site-packages>/nvidia/cuda_nvrtc/lib python -c "...same..."
-0.006928586401045322
```

The fix is to add a dependency torch already bundles, at a HIGHER version:
`nvidia-cuda-nvrtc-cu12==12.9.86` in the lock, and its directory first on
`LD_LIBRARY_PATH` from the launcher. Three things make this worth its own entry
rather than a footnote on §10's table:

  * **The failing component is inside torch, not in the kit**, so no amount of
    reading the kit's pins or levers finds it, and `[kit] mode = "off"` does not
    help.
  * **The symptom is an ordinary op.** `atlasfold`'s version of this was a kit's
    Triton kernels against a bundled `ptxas` — suspicious code in a suspicious
    place. Nobody suspects `torch.prod`, and upstream calls it once per target in
    a data transform, so it looks like a data problem.
  * **The remedy is additive, not a deviation downward.** The lock gains a newer
    wheel of something the stack already contains, which is a different move from
    dropping a pin or turning a mode off, and `[env] verify` can assert it: run
    the op.

Generalised, this is §10's "read the PTX of the library whose kernel runs first"
with a second clause: **a stack can also compile at RUN time, and then the
question is which compiler does that and whether it knows the card.** Both
`ptxas` (ahead of time, in triton) and NVRTC (at run time, in torch) have now
failed here while everything around them was correctly pinned.


## 14. What the eighteenth provider changed: the first one that is not PyTorch

AF3-JAX. Eighteen verified. Seventeen of the eighteen are PyTorch, and five of
the seven findings below exist only because this one is not.

**There is a fourth kind of stack-versus-card failure, and it is the one no
inventory predicts: the kernel builds, and it does not fit.** The three already
on this standard are all knowable before you run anything — no CUDA aarch64
torch below 2.7 (read the wheel), the kit's levers have no tile table for this
compute capability (read the table), a pinned dependency ships kernels the
pinned compiler cannot build (read the compiler's target list). This one is
none of them:

    JaxRuntimeError: RESOURCE_EXHAUSTED: Shared memory size limit exceeded:
      requested 110592, available: 101376, context: []

108 KiB wanted against 99 KiB available, about 9% over. The code is correct,
the compiler targets the card, the arch lists all agree. A tile tuned for a
part with 227 KiB of shared memory per block simply lands the wrong side of a
line on a part with 99. Nothing in a dependency list says so, and the only
place to learn it is a run. The entry in §10's table for this class therefore
cannot be a pre-check; it is "expect it, and know how to find it".

**Finding it: an invariant error number across independent switch-flips is
itself the diagnostic.** This arrives from XLA's own compiler, during
`backend_compile_and_load`, as a failure of the whole module — so it is a
COMPILE failure, the Python traceback cannot name the kernel, and `context: []`
is empty. Three attempts to turn the suspect off each left the number
**byte-identical** at 110592: the attention implementation switched to cudnn
and to triton, `use_glu_kernel = False` set on all fifteen sites in the config
tree, and the kit's own `--xla_gpu_enable_triton_gemm=false`. The temptation is
to read three dead ends as three dead ends. The correct reading is that the
culprit is insensitive to every knob tried, which is a strong statement about
where it is not. The method that then named it, and which generalises to any
XLA stack:

  1. Dump the HLO. XLA's own emitted kernels are exonerated by their PTX
     shared-memory annotations — of 477 PTX modules here the largest asked
     8,320 bytes, three orders off the number in the error.
  2. That leaves the custom calls. The 175 `__gpu$xla.gpu.triton` calls are the
     Pallas kernels, and each carries `metadata={op_name="..."}` naming its op
     and its scope.
  3. Partition them by dtype and scope. Every FlashAttention call was bf16
     inside a named pairformer scope; every f32 call was a
     `PallasTritonGatedLinearUnit` under `vmap(diffusion_head)`. One printed
     its config: `block_m=128, block_n=32, block_k=32, num_warps=4,
     num_stages=4` over `f32[1536,128]` and `f32[128,2,256]`.
     `(128*32 + 32*2*32) x 4 bytes x 4 stages = 98,304` before the epilogue —
     the right size class, in the right dtype, at four stages.

**A config field can exist, be documented, have an exact fallback, and be
unreachable.** `use_glu_kernel` is a real upstream field on
`TransitionBlock.Config` and `TriangleMultiplication.Config` with an equivalent
XLA else-branch. But `diffusion_transformer.transition_block` takes it as a
**function default** (`use_glu_kernel: bool = True`) and none of its three call
sites passes it. So the only GLUs that could not be turned off were exactly the
f32 ones that were too big. When a config switch provably does nothing, check
that the call site reads it before concluding the switch is not the issue.

**The fix for a card the upstream has never seen may be upstream's own flag.**
tokamax registers absl flags at import, so `run_alphafold.py --helpfull` lists:

    --tokamax_autotuning_cache_miss_fallback=<heuristics|autotune|error>

Default `heuristics` — synthesise a config, which here means synthesise one
sized for a bigger card. `autotune` measures tokamax's own default config set
on the device present and keeps the fastest one that compiles and runs. It is
public, documented, flag-backed, and its entire purpose is an unseen device. It
is not a tile override, not a reach into internals, and not a patch, so it
stays inside §7. Before writing a patch for a stack-versus-card failure, read
the flag list: a project that ships kernels has usually thought about the case
where its tile table has no row for you.

**The arch check asks the card, not torch.** `setup.step_environment` refused
this provider `torch_arch_unsupported` — "torch reports no usable GPU: no
device" — and was wrong. The torch in this environment is 2.7.1+**cpu** by
design: it is present for the weights converter and because `check_pins.py`
lists it, while JAX drives the card. The probe now also reports
`jax.default_backend()` and `jax.local_devices(backend="gpu")`, and
`_arch_problem` returns None when another framework holds the device. The
manifest was not weakened to buy a green step — `[gpu] policy` stayed
`required`, because the GPU is required. The general rule: a gate that names
one framework is a gate that will refuse a correct provider as soon as a second
framework appears, and the refusal will be confident and specific and wrong.

**A JAX provider's VRAM number is not the same kind of number as a torch
provider's, and a scheduler cannot tell.** Two measurements, both load-bearing:

  * `peak_pool_bytes` is the analogue of torch's `max_memory_reserved`, and
    `peak_bytes_reserved` is a trap that reads 0. But `peak_pool_bytes` is
    **coarse** (an earlier draft said "quantised to powers of two"; af2ig's
    0.5 / 1.0 / 2.0 / 6.0 refuted that): the ladder read 2.0 / 4.0 / 4.0 / 8.0 GiB
    while the working set moved 2.00 / 2.32 / 3.38 / 6.37. So `vram_budget_gb`
    for a JAX provider is a rounded-up allocator high-water mark sitting in the
    same column as a torch provider's near-exact one. Schedule on it as a
    ceiling; do not read the gap between two rungs as headroom, and do not
    compare 8.0 here with 8.0 elsewhere as though they measured the same thing.
  * `XLA_PYTHON_CLIENT_PREALLOCATE=false` is worth **45x on the reported
    figure**: 91.22 GiB without it against 2.0 with it. That is JAX claiming
    the card up front, not the model needing it. A framework default can make a
    5 GiB model unschedulable, and the default is the one that does it.

**Residency's largest gain on this standard is 24-26x, and the reason is a cost
upstream intends to persist and does not.** Four identical requests, measured
twice: 170.5 / 8.3 / 7.0 / 7.0 s on an idle card, and 179.1 / 6.8 / 6.8 / 6.8 s
on a card with three other provider builds competing for it — 26.3x rather than
24x. The ratio went UP under contention, and the reason is worth keeping in mind
when reading any such figure: contention slows work and a replay is almost no
work, so the cold request absorbs nearly all of it. A residency multiple measured
on a busy card flatters itself. (The ladder's wall times, by contrast,
reproduced rung for rung within a few percent and in both directions — 234.8
against 228.5 at 100 residues, 468.7 against 503.0 at 400 — so "contended" was
not a blanket excuse for every number that moved.) Three things are held — the 1.37 GB zstd
weight read, the XLA executables, and tokamax's per-shape autotune, which this
provider must turn on to run at all. The third is the bulk of it, and it is
unpersisted *by accident*: `ModelRunner._load_autotune_cache` reads
`<cache_dir>/tokamax_autotune.json` at construction, and the call that would
write it (`tokamax.autotune(...)` at the top of `run_inference`) is wrapped in
`except Exception: pass` and does not succeed here, so no file is ever
produced. This is the residency argument in its purest form: the only copy of a
very expensive artifact lives in a process's memory, and the alternative design
would recompute it per request because the cache it looks for will never be
there. It also sets `idle_timeout_s` — 900 s, not something shorter, because a
restart pays the full first-request price again, per bucket.

**The cost is per bucket, which makes the repeats test cheap here and the shape
change the whole test.** This fork pads every input to a bucket (every multiple
of 64 up to 5120) and every featurised batch's shape is a pure function of the
bucket, not of the token count, MSA depth, chain count or template count. So
the cost is per bucket, not per request: an ascending ladder of 100 / 200 / 400
residues paid 234.8 / 269.9 / 468.7 s, one compile-plus-autotune each, and a
mixed sequence of 100, 100, 200, 100 afterwards paid 14.4 / 13.2 / 31.1 / 13.3
because every one of those buckets was already held. Four identical requests
exercise ONE bucket and ONE compile, which is why they are the cheap half here.
§15's blind-spot finding, which came from genie3, lands here as a measurement
rather than a hazard — and note what the mixed sequence actually proves that
repeats cannot: the engine switched 100 → 200 → 100 and the third request was
not slower than the first, so the worker holds both and chooses, rather than
rebuilding whichever it last used.

**And the headline multiple is measured at the smallest input, which is where it
is largest. State both ends.** The 24-26x is 35 residues. At the row the budget
is declared on — 800 residues, the 832-token bucket — the same worker gives
**3.5x**: 755.0 s for the cold bucket against 217.8 / 216.3 / 217.9 / 223.5 s for
four held ones. Nothing regressed; the fixed cost is the same and the work it is
divided by grew, so residency returns a smaller multiple exactly where a request
is expensive. A provider quoting only its best rung tells a host the opposite of
what it needs to plan with, because the expensive requests are the ones being
scheduled around. Quote the gain at the budget row, and the best case as the best
case.

**A fifth activation shape: a `.pth` whose only job is to refuse.** The
taxonomy was autoload-that-patches (30 of 36 kits), `worker_launch`, a
replacement entry script, and autoload-plus-a-patched-tree. af3_jax installs
the same shaped `.pth` and uses it to kill importers: it arms a meta-path
finder on `alphafold3` when `AF3_JAX_OPT` names a mode other than `off`, **or
when any `AF3_JAX_*` name outside its declared tuple is set** — and the second
trigger fires with the mode unset. A resident worker must import `alphafold3`,
so the consequence for `[runtime] launch` is sharper than "do not set the mode":
it must **strip** undeclared `AF3_JAX_*` names from the child's environment,
because a variable inherited from the operator's shell is enough to make the
worker exit 3 on import. Not setting a variable and removing it are different
operations, and only one of them is safe against an environment you did not
build.

## 15. What providers fifteen through seventeen changed

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

**And the other half earned its own reason, from one provider carrying both
defects at once.** openfold3_ob0 has two "the second request fails" bugs of the
same observable shape in two different layers. One is the kit's: a CUDA graph
pool handle kept after a dropped graph, reachable only by REPEATING a shape, and
invisible to a mixed sequence. The other is upstream 0.5.0's: `InferenceExperimentRunner`
binds its MSA record root once at construction and then
`mkdir(..., exist_ok=False)` on that one path per request, so request one folds
and every request after it — **of any shape** — raises `FileExistsError`, caught
per query and arriving as "wrote no structure". That one is invisible to a
one-request smoke and invisible to four identical requests too, because it does
not care about shape; it showed up on ladder rung two. The sibling at 0.4.1 never
saw it, because 0.4.1 has no MSA settings object.

So the two halves of the acceptance sequence are now defended by two different
arguments rather than one: repeats catch what only recurrence exposes, a shape
change catches what only a rebuild exposes, and **"the second request" is a
property of residency itself rather than of any one kit** — which is why neither
half is optional and why a provider that passes one and skips the other has
tested nothing it did not already know.

**A resident worker may have to reset UPSTREAM's module state, not just the
kit's.** This is the sixth resident-worker hazard and the first that is neither a
fork, a lever, nor a graph. Section 16 names the kit's own recovery for a failed
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
fixed cost.** Section 17 explains the 2.0x–12x range by what a kit does at import
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

## 16. What providers eleven through fourteen changed

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

## 17. What providers seven through ten changed

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

## 18. What providers four, five and six changed

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

## 19. What the third provider changed

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

## 20. What the second provider changed

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
