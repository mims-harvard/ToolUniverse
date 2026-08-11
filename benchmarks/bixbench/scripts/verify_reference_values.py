#!/usr/bin/env python3
"""Recompute the PhyKIT reference values the phylogenetics questions depend on.

Recomputes, from the capsule's own shipped alignments and trees, four values
that several questions depend on. If these do not match, the environment differs
from the reference and the phylogenetics questions will not reproduce.

    python3 verify_reference_values.py --capsule <CapsuleFolder-...>

Expected output, with the convention each value depends on:

    saturation median          0.6146   taking phykit's FIRST column gives
                                        0.3854 -- the two sum to 1.0000
    treeness median            0.0501   takes no alignment, so it isolates
                                        data/tool problems from convention
                                        problems
    treeness/RCV median        0.2683   untrimmed .faa.mafft; the trimmed
                                        .clipkit gives 0.3050
    >70%-gap max treeness/RCV  0.2572   "gap percentage" means the fraction of
                                        COLUMNS containing a gap (3 genes
                                        qualify); by residue fraction none do
"""

import argparse
import glob
from concurrent.futures import ThreadPoolExecutor
import os
import statistics as st
import subprocess
import sys
import zipfile


def phykit(*args, timeout=180):
    r = subprocess.run(
        ["phykit", *args], capture_output=True, text=True, timeout=timeout
    )
    return r.stdout.strip() if r.returncode == 0 else None


def column_gap_fraction(path):
    """Fraction of alignment columns holding at least one gap."""
    seqs, cur = [], []
    for line in open(path):
        if line.startswith(">"):
            if cur:
                seqs.append("".join(cur))
                cur = []
        else:
            cur.append(line.strip())
    if cur:
        seqs.append("".join(cur))
    if not seqs:
        return 0.0
    n = min(len(s) for s in seqs)
    return sum(1 for i in range(n) if any(s[i] == "-" for s in seqs)) / n if n else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--capsule", required=True, help="extracted CapsuleFolder-... directory"
    )
    ap.add_argument("--workdir", default="/tmp/bixbench_ref")
    a = ap.parse_args()

    zf = os.path.join(a.capsule, "scogs_fungi.zip")
    if not os.path.exists(zf):
        print(f"ERROR: {zf} not found", file=sys.stderr)
        return 2
    os.makedirs(a.workdir, exist_ok=True)
    with zipfile.ZipFile(zf) as z:
        z.extractall(a.workdir)
    os.chdir(a.workdir)

    stems = sorted(
        f[: -len(".faa.mafft.clipkit.treefile")]
        for f in glob.glob("*.faa.mafft.clipkit.treefile")
    )
    print(f"{len(stems)} ortholog alignment/tree pairs\n")

    def measure(s):
        """The three values for one ortholog, with the column each needs."""
        aln_t = f"{s}.faa.mafft.clipkit"
        aln_u = f"{s}.faa.mafft"
        tr = f"{s}.faa.mafft.clipkit.treefile"
        out = {}
        o = phykit("saturation", "-a", aln_t, "-t", tr)
        if o:
            out["sat"] = float(o.split("\t")[1])  # 1-slope, not the first column
        o = phykit("treeness", tr)
        if o:
            out["tree"] = float(o.split("\t")[0])
        o = phykit("toverr", "-a", aln_u, "-t", tr)  # untrimmed alignment
        if o:
            out["tov"] = float(o.split("\t")[0])
        return s, out

    # Each ortholog is independent and the work is subprocess wall time, so a
    # thread pool turns ~20 minutes of serial phykit calls into a couple.
    sat, tree, tov = [], [], []
    workers = min(16, (os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for s, out in pool.map(measure, stems):
            if "sat" in out:
                sat.append(out["sat"])
            if "tree" in out:
                tree.append(out["tree"])
            if "tov" in out:
                tov.append((s, out["tov"]))

    gapped = [s for s in stems if column_gap_fraction(f"{s}.faa.mafft") > 0.70]
    gap_max = max((v for s, v in tov if s in gapped), default=None)

    checks = [
        ("saturation median", st.median(sat) if sat else None, 0.6146),
        ("treeness median", st.median(tree) if tree else None, 0.0501),
        (
            "treeness/RCV median (untrimmed)",
            st.median([v for _, v in tov]) if tov else None,
            0.2683,
        ),
        (f">70%-gap max treeness/RCV ({len(gapped)} genes)", gap_max, 0.2572),
    ]
    bad = 0
    for name, got, want in checks:
        ok = got is not None and abs(got - want) < 0.005
        bad += not ok
        print(
            f"  {'ok  ' if ok else 'FAIL'} {name:42s} {got if got is None else round(got, 4)}  (expected {want})"
        )
    print(
        "\nreference values reproduced"
        if not bad
        else f"\n{bad} value(s) differ -- do not trust downstream results"
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
