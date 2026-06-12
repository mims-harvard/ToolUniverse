#!/usr/bin/env python3
"""Cloning assembly QC for the tooluniverse-molecular-cloning skill.

Screens DNA parts/fragments for the failures that wreck an assembly:
- Golden Gate: internal Type IIS recognition sites (BsaI/BbsI) that must be
  domesticated, plus uniqueness / palindrome checks on 4-bp overhangs.
- Gibson: overlap length and GC of the supplied homology arms.

Usage:
  # Golden Gate: check parts for internal sites + given overhangs
  python cloning_qc.py --golden-gate --enzyme BsaI --parts ATGGCG...,CTGAGC...
  python cloning_qc.py --overhangs AAAC,AAAG,AAAT
  # Gibson: check overlap arms
  python cloning_qc.py --overlaps ATGGCGCCCAAGACGGGCTA,GAGGACGAGCTGCTGAAGCT
"""

import argparse

_COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}
_SITES = {"BsaI": "GGTCTC", "BbsI": "GAAGAC"}


def revcomp(s):
    return "".join(_COMP.get(b, "N") for b in reversed(s.upper()))


def gc(s):
    return 100.0 * sum(b in "GC" for b in s.upper()) / len(s) if s else 0.0


def check_internal_sites(parts, enzyme):
    site = _SITES[enzyme]
    rc = revcomp(site)
    print(f"\nGolden Gate — internal {enzyme} sites ({site} / {rc}):")
    ok = True
    for i, p in enumerate(parts, 1):
        p = p.upper()
        n = p.count(site) + p.count(rc)
        flag = "PASS" if n == 0 else "WARN"
        if n:
            ok = False
        print(f"  [{flag}] Part_{i}: {n} internal site(s)" + ("" if n == 0 else " — DOMESTICATE (silent-mutate) before use"))
    if ok:
        print("  all parts free of internal sites.")


def check_overhangs(ohs):
    print("\nGolden Gate — 4-bp overhang QC:")
    ohs = [o.upper() for o in ohs]
    seen = {}
    for i, o in enumerate(ohs, 1):
        issues = []
        if len(o) != 4:
            issues.append(f"length {len(o)}!=4")
        if o == revcomp(o):
            issues.append("palindromic (self-complementary)")
        if o in seen:
            issues.append(f"duplicate of overhang #{seen[o]}")
        if revcomp(o) in ohs:
            issues.append("reverse-complement of another overhang")
        seen.setdefault(o, i)
        flag = "PASS" if not issues else "WARN"
        print(f"  [{flag}] {o}" + ("" if not issues else "  — " + "; ".join(issues)))


def check_overlaps(ovs):
    print("\nGibson — overlap arm QC:")
    for i, o in enumerate(ovs, 1):
        o = o.upper()
        issues = []
        if not (15 <= len(o) <= 40):
            issues.append(f"length {len(o)} (want 15-40 bp)")
        if not (40 <= gc(o) <= 65):
            issues.append(f"GC {gc(o):.0f}% (want 40-65%)")
        flag = "PASS" if not issues else "WARN"
        print(f"  [{flag}] overlap {i} ({len(o)} bp, GC {gc(o):.0f}%)" + ("" if not issues else "  — " + "; ".join(issues)))
    # shared-homology check
    for i in range(len(ovs)):
        for j in range(i + 1, len(ovs)):
            if ovs[i].upper() == ovs[j].upper():
                print(f"  [WARN] overlaps {i + 1} and {j + 1} are identical — fragments can swap; make each unique.")


def _split(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden-gate", action="store_true")
    ap.add_argument("--enzyme", choices=list(_SITES), default="BsaI")
    ap.add_argument("--parts", help="comma-separated part sequences")
    ap.add_argument("--overhangs", help="comma-separated 4-bp overhangs")
    ap.add_argument("--overlaps", help="comma-separated Gibson overlap arms")
    args = ap.parse_args()

    if (args.golden_gate or args.parts) and args.parts:
        check_internal_sites(_split(args.parts), args.enzyme)
    if args.overhangs:
        check_overhangs(_split(args.overhangs))
    if args.overlaps:
        check_overlaps(_split(args.overlaps))
    if not any((args.parts, args.overhangs, args.overlaps)):
        ap.error("provide --parts, --overhangs, and/or --overlaps")


if __name__ == "__main__":
    main()
