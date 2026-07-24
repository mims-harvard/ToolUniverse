#!/usr/bin/env python3
"""Primer-pair QC for the tooluniverse-primer-design skill.

Checks a forward/reverse primer against the standard design rules — length,
GC%, GC clamp, 3'-end self/cross complementarity (dimer risk), mononucleotide
runs, a salt-adjusted Tm estimate, and Tm match between the pair — and prints
PASS/WARN per check. The rigorous nearest-neighbor Tm comes from the
NEB_Tm_calculate / IDT_analyze_oligo tools; this is a fast, dependency-free
screen for any primer pair.

Usage:
  python primer_qc.py --forward CTACCTGAAGAACCTGAG --reverse CTTGATGTCCTCCAGCAT
"""

import argparse

_COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}


def gc(seq):
    return 100.0 * sum(b in "GC" for b in seq) / len(seq)


def tm_saltadj(seq, na_mm=50.0):
    """Rough Tm: Wallace for <14 nt, else the 64.9+41*... formula (~50 mM Na+).

    A fast screening estimate only — it runs lower than the nearest-neighbor
    Tm from NEB_Tm_calculate / IDT_analyze_oligo, which are the values to cite.
    """
    import math

    n = len(seq)
    gc_n = sum(b in "GC" for b in seq)
    if n < 14:
        tm = 2 * (n - gc_n) + 4 * gc_n  # Wallace rule (assumes ~50 mM salt)
    else:
        tm = 64.9 + 41 * (gc_n - 16.4) / n  # baseline at ~50 mM Na+
    # correction relative to the 50 mM reference the baseline assumes
    return tm + 16.6 * math.log10(max(na_mm, 1) / 50.0)


def longest_run(seq):
    best = run = 1
    for i in range(1, len(seq)):
        run = run + 1 if seq[i] == seq[i - 1] else 1
        best = max(best, run)
    return best


def three_prime_complement(a, b, window=5):
    """Count complementary bases when a's 3' end pairs against b's 3' end.

    High overlap at the 3' ends is the classic primer-dimer signature.
    """
    a3 = a[-window:]
    b3 = b[-window:][::-1]  # align 3'-to-3'
    return sum(_COMP.get(x) == y for x, y in zip(a3[::-1], b3))


def check(seq, name):
    seq = seq.upper().strip()
    out = []
    out.append(("length", 18 <= len(seq) <= 24, f"{len(seq)} nt (want 18-24)"))
    out.append(("GC%", 40 <= gc(seq) <= 60, f"{gc(seq):.0f}% (want 40-60)"))
    clamp = sum(b in "GC" for b in seq[-3:])
    out.append(("3' GC clamp", 1 <= clamp <= 2, f"{clamp} G/C in last 3 (want 1-2)"))
    run = longest_run(seq)
    out.append(("no long runs", run < 4, f"longest run {run} (want <4)"))
    selfd = three_prime_complement(seq, seq)
    out.append(("3' self-dimer", selfd <= 2, f"{selfd}/5 3'-complementary (want <=2)"))
    return seq, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forward", required=True)
    ap.add_argument("--reverse", required=True)
    ap.add_argument("--na-mm", type=float, default=50.0)
    args = ap.parse_args()

    fseq, fchecks = check(args.forward, "forward")
    rseq, rchecks = check(args.reverse, "reverse")
    tmf, tmr = tm_saltadj(fseq, args.na_mm), tm_saltadj(rseq, args.na_mm)

    def show(name, seq, checks, tm):
        print(f"\n{name}: {seq}  (Tm~{tm:.1f} C, salt-adjusted estimate)")
        for label, ok, detail in checks:
            print(f"  [{'PASS' if ok else 'WARN'}] {label:14} {detail}")

    show("Forward", fseq, fchecks, tmf)
    show("Reverse", rseq, rchecks, tmr)

    print("\nPair:")
    dtm = abs(tmf - tmr)
    print(f"  [{'PASS' if dtm <= 3 else 'WARN'}] Tm match      dTm={dtm:.1f} C (want <3)")
    cross = three_prime_complement(fseq, rseq)
    print(f"  [{'PASS' if cross <= 2 else 'WARN'}] 3' cross-dimer {cross}/5 3'-complementary (want <=2)")
    print(
        "\nNote: this is a thermodynamic/structure screen only. It does NOT check genome "
        "specificity — BLAST each primer (or Primer-BLAST) before ordering. Use NEB_Tm_calculate "
        "for the polymerase-specific annealing temperature."
    )


if __name__ == "__main__":
    main()
