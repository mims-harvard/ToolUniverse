"""Block until the machine has room for a resident worker, or refuse.

THIS EXISTS BECAUSE THE MACHINE WAS WEDGED. Four providers' workers were held
(about 12 GiB between them) when a fifth provider's smoke was started, and that
provider wants 28 GiB. On this host GPU allocations and system memory come out
of ONE unified 121 GiB pool, so "the GPU looks idle" and "there is room" are
different questions, and the sum of the resident workers' RSS is not the answer
to either: it leaves out the loading peak, the page cache a GPU allocation
displaces, and the fact that co-tenants start workers of their own without
telling you.

STANDARD.md already said the co-tenant version of this -- `cudaMemGetInfo`'s
free figure is system-wide and will mislead a kit's own capacity guard. The
scheduling version is the same fact one level up.

    python scripts/remote_validation/wait_for_memory.py --need 30
    python scripts/remote_validation/wait_for_memory.py --need 30 --timeout 1800

Exits 0 when `MemAvailable` has been at or above `--need` GiB for two readings
thirty seconds apart (two, because a single reading catches the gap between one
co-tenant finishing and the next starting). Exits 3 -- a refusal, per section 8
-- when the timeout passes without that, naming what is holding the memory so
the operator can decide rather than guess.
"""

import argparse
import os
import subprocess
import sys
import time


def meminfo_gib() -> dict:
    """`MemFree` and `MemAvailable`, in GiB.

    **The number that predicts a CUDA failure here is MemFree, not
    MemAvailable**, and the first version of this guard used the wrong one. It
    let a worker start at 60.4 GiB *available* and the worker died with
    `CUDA error: out of memory` -- because only 5 GiB was *free* and the other 56
    was reclaimable page cache, which a device allocation on this host does not
    get to reclaim in time. `MemAvailable` answers "how much could a well-behaved
    process eventually get"; a CUDA allocation asks a narrower question, and the
    guard has to ask the narrow one.

    Both are returned so the refusal can say which gate stopped it, because the
    gap between them is the interesting part of the message.
    """
    want = {"MemFree": None, "MemAvailable": None}
    with open("/proc/meminfo") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            if key in want:
                want[key] = int(rest.split()[0]) / (1024 * 1024)
    missing = [k for k, v in want.items() if v is None]
    if missing:
        raise RuntimeError(f"/proc/meminfo has no {', '.join(missing)}")
    return want


def holders() -> str:
    """Who is holding a resident worker right now, largest first."""
    try:
        out = subprocess.run(
            ["ps", "-eo", "rss,args"], capture_output=True, text=True, timeout=20
        ).stdout
    except Exception:
        return "(could not read the process table)"
    rows = []
    for line in out.splitlines():
        if "resident_worker.py" not in line or "--socket" not in line:
            continue
        rss, _, args = line.strip().partition(" ")
        worker = next((p for p in args.split() if "/resident/" in p), "")
        if not worker:
            # A shell wrapper whose command line merely mentions the worker.
            continue
        parts = worker.split("/")
        # .../remote/<slug>/resident/<slug>_resident_worker.py
        slug = parts[-3] if len(parts) >= 3 else "?"
        # A holder may be an entirely different checkout of this repository.
        # The one that wedged this host was, and not knowing that was the whole
        # mistake -- so name the tree, not just the provider.
        tree = next(
            (
                parts[i + 1]
                for i, seg in enumerate(parts)
                if seg == "worktrees" and i + 1 < len(parts)
            ),
            None,
        )
        rows.append((int(rss) / (1024 * 1024), f"{slug}@{tree}" if tree else slug))
    if not rows:
        return "no resident workers are running"
    rows.sort(reverse=True)
    return ", ".join(f"{name} {gib:.1f} GiB" for gib, name in rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--need",
        type=float,
        required=True,
        help="GiB of MemAvailable required, which should be the provider's "
        "declared vram_budget_gb plus headroom for the loading peak",
    )
    ap.add_argument("--timeout", type=float, default=2700.0)
    ap.add_argument("--interval", type=float, default=30.0)
    a = ap.parse_args()

    deadline = time.time() + a.timeout
    clear = 0
    while True:
        mem = meminfo_gib()
        free, avail = mem["MemFree"], mem["MemAvailable"]
        if free >= a.need:
            clear += 1
            if clear >= 2:
                print(
                    f"ok: {free:.1f} GiB free ({avail:.1f} available), "
                    f"{a.need:.1f} needed"
                )
                return 0
        else:
            clear = 0
        if time.time() >= deadline:
            print(
                f"refused: {free:.1f} GiB FREE, {a.need:.1f} needed, after "
                f"{a.timeout:.0f}s. ({avail:.1f} GiB is 'available', but that "
                f"counts reclaimable page cache a device allocation here does "
                f"not get in time -- a worker started at 60.4 available with 5 "
                f"free and died of CUDA out of memory.) Holding it now: "
                f"{holders()}. Wait for a co-tenant to finish, or run this "
                f"provider when the machine is quieter -- do not start it "
                f"anyway: one 28 GiB smoke on top of four held workers wedged "
                f"this host.",
                file=sys.stderr,
            )
            return 3
        time.sleep(min(a.interval, max(0.0, deadline - time.time())))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(main())
