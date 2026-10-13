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
   workers that turned 12 GiB into a wedge were five `boltzgen` workers from a
   different checkout entirely, started by a session that had no reason to
   announce them. A decision made from `backend.running()` alone is blind in
   exactly the direction that caused the harm, so admission reads the machine as
   well, and the two gates are independent: the declared sum protects against
   peaks that have not happened yet, and the live reading protects against
   tenants this process cannot see.
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
    """`decide` against what this process is holding, which is not all of it.

    Imported lazily because `backend` imports this module's siblings; the
    docstring of the function it calls is the one that explains why the answer
    is only half the question.
    """
    from . import backend

    return decide(slug, budget_gb, backend.running(), **kw)
