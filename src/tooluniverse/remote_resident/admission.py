"""Whether there is room to hold one more provider. This is what the budgets are for.

Every manifest declares `[gpu] vram_budget_gb`, measured rather than guessed, and
STANDARD.md §6 says it is "what a host adds up to decide how many providers may
be resident at once". Twenty-seven providers now declare one and nothing added
them up: `backend.running()` returns `{slug: budget}` with a docstring saying a
scheduler above it reads that, and no caller. This module is the addition.

IT EXISTS BECAUSE THE MACHINE WAS WEDGED, by this project, with the numbers in
hand. Four providers' workers were held, their RSS summed to about 12 GiB, and a
fifth provider's 28 GiB smoke was started on top. The host stopped responding.
Two things made that possible and both are requirements here:

1. **The sum of what THIS process holds is not what the machine holds.** The
   workers that turned 12 GiB into a wedge were `boltzgen` workers from a
   different checkout entirely, started by a session that had no reason to
   announce them. `backend.running()` is blind in exactly the direction that
   caused the harm, so the holdings come from `machine_holdings` -- the process
   table, which sees every checkout's workers and counts two processes of one
   provider as two holders. The two gates then cover different unknowns: the
   declared sum protects against peaks that have not happened yet, and the live
   reading protects against everything on this machine that is not a resident
   worker at all.
2. **On unified memory the two budgets are one budget.** `nvidia-smi
   --query-gpu=memory.total` answers `[N/A]` on this GB10 because device memory
   IS system memory: 121 GiB for the host and the card together. So capacity is
   `MemTotal`, a VRAM budget is spent from the same pool as a page cache, and a
   provider's budget cannot be checked against a device total that does not
   exist. STANDARD.md already recorded that this breaks a kit's own arithmetic;
   it breaks a scheduler's the same way one level up.

THE LIVE GATE ASKS A NARROWER QUESTION WHEN IT HAS CO-TENANTS, which is the
second thing this project got wrong before measuring it. The first guard gated
on `MemAvailable` and waved a worker through at 60.4 GiB available with 5 GiB
free; it died with `CUDA error: out of memory`, because the other 56 was
reclaimable page cache that a device allocation did not get to reclaim in time.
Changing it to `MemFree` then made it too strict: a bounded probe allocated to 24
GiB starting from 18.7 GiB free, with `Cached` falling 72.2 -> 63.4 while free
held near 4 -- reclaim works. Both readings are true and they answer different
questions, so which one gates depends on whether anything else is competing for
the reclaim: `MemFree` when there are co-tenants, because losing a race to one
is what the OOM was, and `MemAvailable` when there are none, because then
reclaim is not a race.

THE LIMIT OF THAT EVIDENCE, stated because the rule extrapolates past it: the
uncontended probe reached 24 GiB starting from 18.7 GiB free. An uncontended
admission of more than that is trusting the kernel's own estimate of what it can
reclaim, which is exactly what `MemAvailable` is, and which has not been
falsified here -- but it has only been confirmed once and at one size. A host
that wants a harder floor passes a larger `reserve_gb`; the honest default is
not to invent a bound nobody measured.

A refusal here names the numbers and does not round them, per §8.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Tuple

GIB = 1024 * 1024 * 1024


class AdmissionRefused(RuntimeError):
    """There is not room to hold this provider. The message carries the numbers."""


@dataclass
class Verdict:
    """The decision, the reason, and every number it was made from."""

    admit: bool
    reason: str
    slug: str = ""
    budget_gb: Optional[float] = None
    capacity_gib: Optional[float] = None
    capacity_source: str = ""
    declared_held_gb: float = 0.0
    free_gib: Optional[float] = None
    available_gib: Optional[float] = None
    gate: str = ""
    co_tenants: int = 0
    unknown_budgets: Tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:  # `if decide(...):` reads as intended
        return self.admit

    def raise_if_refused(self) -> "Verdict":
        if not self.admit:
            raise AdmissionRefused(self.reason)
        return self


def meminfo_gib() -> Dict[str, float]:
    """`MemTotal`, `MemFree` and `MemAvailable` in GiB, from /proc/meminfo."""
    want = {"MemTotal": None, "MemFree": None, "MemAvailable": None}
    with open("/proc/meminfo") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            if key in want:
                want[key] = int(rest.split()[0]) / (1024 * 1024)
    missing = [k for k, v in want.items() if v is None]
    if missing:
        raise RuntimeError(f"/proc/meminfo has no {', '.join(missing)}")
    return want  # type: ignore[return-value]


def capacity_gib() -> Tuple[Optional[float], str]:
    """The size of the one pool a budget is spent from, and where the figure came from.

    On unified memory there is no device total to ask for -- `nvidia-smi` returns
    `[N/A]` -- and the honest capacity is `MemTotal`, because a VRAM allocation
    and a page cache come out of the same 121 GiB. On a discrete card the device
    total is the right ceiling for a VRAM budget and `MemTotal` is not.

    Returns `(None, reason)` when neither can be established, which is a thing a
    caller must handle rather than a zero it can compare against.
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"nvidia-smi did not run ({type(exc).__name__})"
    first = (out.stdout or "").strip().splitlines()
    value = first[0].strip() if first else ""
    if value and "N/A" not in value:
        try:
            return float(value) / 1024.0, "nvidia-smi memory.total (discrete device)"
        except ValueError:
            pass
    # `[N/A]` is the unified-memory answer, not an error: the device has no total
    # of its own because it is sharing the host's.
    try:
        return meminfo_gib()["MemTotal"], "/proc/meminfo MemTotal (unified memory)"
    except (OSError, RuntimeError) as exc:
        return None, f"no device total and no MemTotal ({exc})"


def _nvidia_pids() -> int:
    """How many processes the driver says are holding the card right now.

    Counted rather than named: the point is only whether this decision has
    competition for reclaim, and the processes that wedged the machine belonged
    to another checkout, so their identities were not available anyway.
    """
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    return len([ln for ln in (out.stdout or "").splitlines() if ln.strip()])


# .../remote/<slug>/resident/<slug>_resident_worker.py, and the segment after
# `worktrees` when the holder is a different checkout of this repository.
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _holder_of(path: str) -> Tuple[str, Optional[str]]:
    parts = path.split("/")
    slug = parts[-3] if len(parts) >= 3 else "?"
    tree = next(
        (
            parts[i + 1]
            for i, seg in enumerate(parts)
            if seg == "worktrees" and i + 1 < len(parts)
        ),
        None,
    )
    return slug, tree


def machine_holdings(
    *, ps_output: Optional[str] = None, budget_of=None
) -> Dict[str, Optional[float]]:
    """Every resident worker on this machine, not only this process's.

    THIS IS THE HOLE THE REST OF THIS MODULE WAS WRITTEN AROUND. `backend.running()`
    knows what this interpreter started; the workers that wedged this host were
    started by a session in another worktree of this same repository, and the
    whole mistake was not knowing they were there. The process table does know:
    a resident worker is a `*_resident_worker.py` invoked with `--socket`, and
    its own path names the provider and the checkout.

    Scanning sockets instead would undercount, because the socket path is one per
    slug per uid: two checkouts running the same provider are one socket and two
    processes, and the second process is the one that turns a comfortable sum
    into a wedge. A stale socket also outlives its worker -- there is one in that
    directory as this is written -- so a socket is evidence of a past worker and
    a process is evidence of a present one.

    Keys are `slug` for a holder in this tree and `slug@tree` for one elsewhere,
    so a restart can release its own budget without releasing someone else's.
    Values are the DECLARED budget from the local manifest, because that is what
    a budget is for; a slug this checkout does not have returns None, which
    `decide` refuses on rather than treating as free.
    """
    if ps_output is None:
        try:
            ps_output = subprocess.run(
                ["ps", "-eo", "args"], capture_output=True, text=True, timeout=20
            ).stdout
        except (OSError, subprocess.SubprocessError):
            return {}
    if budget_of is None:
        budget_of = _declared_budget

    out: Dict[str, Optional[float]] = {}
    for line in (ps_output or "").splitlines():
        if "resident_worker.py" not in line or "--socket" not in line:
            continue
        worker = next((tok for tok in line.split() if "/resident/" in tok), "")
        if not worker:
            continue  # a shell wrapper that merely mentions the worker
        slug, tree = _holder_of(worker)
        # A SHELL WHOSE COMMAND LINE QUOTES A WORKER PATH IS NOT A WORKER, and
        # the token test above does not catch it: the first run of this function
        # reported a holder called `<slug>`, matched out of the `bash -c` that
        # was writing this very function and had the path template in a comment.
        # Checking that the file exists would not do -- a worker outlives a
        # deleted worktree, and that holder is real -- so the shape of the slug
        # is the test, which a template or a glob fails and a deleted checkout
        # still passes.
        if not SLUG_RE.match(slug):
            continue
        if tree is not None and not SLUG_RE.match(tree.replace("-", "_")):
            tree = None
        key = f"{slug}@{tree}" if tree else slug
        # Two processes of the same slug in the same tree are two holders: the
        # second is exactly what made 12 GiB into a wedged host.
        suffix = 2
        base = key
        while key in out:
            key = f"{base}#{suffix}"
            suffix += 1
        out[key] = budget_of(slug)
    return out


def _declared_budget(slug: str) -> Optional[float]:
    """`[gpu] vram_budget_gb` from this checkout's manifest for `slug`.

    None means UNDECLARED, which `decide` reports rather than summing as zero:
    a provider whose cost is unknown cannot be added up.

    **A CPU-ONLY PROVIDER IS 0.0, NOT None**, and the distinction is the whole
    difference between a useful co-tenant and a blocker. A manifest with
    `[gpu] policy = "none"` is the one case where an absent `vram_budget_gb` is
    legal -- the manifest layer enforces that -- and it means the provider holds
    no device memory at all, not that nobody measured it. Mapping it to None
    made a held esm_if1 or proteinmpnn worker refuse every GPU provider on the
    box with "already held without a declared budget, so what the card is
    carrying cannot be summed": exactly inverted, since a CPU provider is the
    one thing that can safely be resident while the card is full. Found by
    running `tu remote room boltz` with a real proteinmpnn worker up, which
    reported `held: {"proteinmpnn": null}` and refused boltz on a card holding
    nothing.

    Another checkout's copy of the same provider could in principle declare a
    different figure; using the local one assumes the checkouts agree, which is
    worth stating because it is an assumption and not a reading.
    """
    from . import manifest as M

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "remote",
        slug,
        "provider.toml",
    )
    if not os.path.exists(path):
        return None
    try:
        m = M.load(path)
    except Exception:  # noqa: BLE001 - a broken manifest is `tu remote check`'s to report
        return None
    if m.vram_budget_gb is None and (m.gpu_policy or "").lower() == "none":
        return 0.0
    return m.vram_budget_gb


def decide(
    slug: str,
    budget_gb: Optional[float],
    held: Optional[Mapping[str, Optional[float]]] = None,
    *,
    reserve_gb: float = 4.0,
    mem: Optional[Mapping[str, float]] = None,
    capacity: Optional[Tuple[Optional[float], str]] = None,
    co_tenants: Optional[int] = None,
) -> Verdict:
    """Whether `slug` may be started now, given what is already held.

    `held` is `{slug: budget}` as `backend.running()` returns it, and a None in
    it is an UNDECLARED budget, which is reported rather than treated as zero: a
    provider whose cost is unknown cannot be added up, and a sum that silently
    drops it would be an admission made on a number nobody measured.

    `reserve_gb` is left for the host itself. It is not a safety fudge over the
    budgets -- those are already upper bounds -- but the room the operating
    system needs to not be the thing that fails: the wedge happened with the
    pool nominally sufficient and the machine unable to schedule anything.

    The injectable arguments exist so the decision is testable without a card.
    """
    held = dict(held or {})
    held.pop(slug, None)  # restarting what is already held frees its own budget
    unknown = tuple(sorted(k for k, v in held.items() if v is None))
    declared = sum(v for v in held.values() if v is not None)

    cap, cap_source = capacity if capacity is not None else capacity_gib()
    m = dict(mem) if mem is not None else meminfo_gib()
    free, avail = m.get("MemFree"), m.get("MemAvailable")
    tenants = _nvidia_pids() if co_tenants is None else co_tenants
    gate = "MemFree" if tenants else "MemAvailable"
    gate_value = free if tenants else avail

    v = Verdict(
        admit=False,
        reason="",
        slug=slug,
        budget_gb=budget_gb,
        capacity_gib=cap,
        capacity_source=cap_source,
        declared_held_gb=round(declared, 2),
        free_gib=None if free is None else round(free, 1),
        available_gib=None if avail is None else round(avail, 1),
        gate=gate,
        co_tenants=tenants,
        unknown_budgets=unknown,
    )

    if budget_gb is None:
        v.reason = (
            f"{slug} declares no vram_budget_gb, so there is nothing to add up. "
            f"A provider is admitted on a measured budget or not at all: measure "
            f"it with scripts/remote_validation/verify_provider.py and put the "
            f"figure in [gpu] vram_budget_gb."
        )
        return v

    if unknown:
        v.reason = (
            f"{', '.join(unknown)} {'is' if len(unknown) == 1 else 'are'} already "
            f"held without a declared budget, so what the card is carrying cannot "
            f"be summed and admitting {slug} ({budget_gb} GiB) would be a guess. "
            f"Declare {'its' if len(unknown) == 1 else 'their'} budget, or stop "
            f"{'it' if len(unknown) == 1 else 'them'} before starting {slug}."
        )
        return v

    if cap is None:
        v.reason = (
            f"the size of the pool {slug}'s {budget_gb} GiB would come out of "
            f"could not be established ({cap_source}), so no sum means anything. "
            f"On unified memory this is MemTotal; on a discrete card it is the "
            f"device total."
        )
        return v

    wanted = declared + budget_gb + reserve_gb
    if wanted > cap:
        v.reason = (
            f"{slug} needs {budget_gb} GiB and {declared} GiB is already declared "
            f"held by {len(held)} worker(s); with {reserve_gb} GiB left for the "
            f"host that is {round(wanted, 2)} GiB against a pool of "
            f"{round(cap, 1)} GiB ({cap_source}). Stop a resident provider, or "
            f"run this one on a quieter machine -- do not start it anyway: that "
            f"is the sequence that wedged this host, with the budgets in hand."
        )
        return v

    if gate_value is None:
        v.reason = f"/proc/meminfo gave no {gate}, so the live gate cannot be read"
        return v

    if gate_value < budget_gb + reserve_gb:
        detail = (
            f"{round(free or 0, 1)} GiB free and {round(avail or 0, 1)} GiB "
            f"available, {tenants} process(es) on the card"
        )
        why = (
            "MemFree is the gate because something else is competing for reclaim, "
            "and losing that race is what a CUDA out-of-memory here actually is"
            if tenants
            else "MemAvailable is the gate because nothing else is competing, so "
            "reclaim is not a race"
        )
        v.reason = (
            f"the pool is big enough on paper -- {declared} GiB declared held of "
            f"{round(cap, 1)} -- but the machine does not have the room right "
            f"now: {detail}. {slug} needs {budget_gb} GiB plus {reserve_gb} GiB "
            f"for the host. {why}. Wait for a co-tenant to finish; "
            f"scripts/remote_validation/wait_for_memory.py --need "
            f"{int(budget_gb + reserve_gb)} does the waiting."
        )
        return v

    v.admit = True
    v.reason = (
        f"{slug} fits: {budget_gb} GiB on top of {declared} GiB declared held, "
        f"{round(wanted, 2)} of {round(cap, 1)} GiB ({cap_source}), and "
        f"{gate} reads {round(gate_value, 1)} GiB with {tenants} process(es) on "
        f"the card."
    )
    return v


def room_for(slug: str, budget_gb: Optional[float], **kw) -> Verdict:
    """`decide` against what the MACHINE is holding, not what this process is.

    `backend.running()` was the obvious source and is the wrong one: it sees the
    workers this interpreter started, and the ones that wedged this host came
    from another worktree. `machine_holdings` reads the process table instead,
    which covers both, so this function does not need to add them up.

    A holder in this tree with the same slug is dropped, because restarting a
    worker releases its own budget. A holder of the same slug in ANOTHER tree is
    kept, because that one is still holding it.
    """
    held = machine_holdings()
    held.pop(slug, None)
    return decide(slug, budget_gb, held, **kw)
