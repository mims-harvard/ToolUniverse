#!/usr/bin/env python3
"""Measure what Carbon-X can actually do through this deployment.

The provider's acceptance test proves the DEPLOYMENT: the engine loads, the
socket answers, refusals are named, the card is released. It says nothing
about whether the answers are right, and for a model whose whole purpose is
to answer questions, that gap is most of what a user cares about.

This measures the answers, against ground truth nobody here chose:

  variants      50 real ClinVar missense SNVs, 25 pathogenic and 25 benign,
                with the reference window pulled from UCSC hg38 and the
                alternate built by substituting one base. The set is BALANCED
                because a model that answers one word to everything scores
                50% on a balanced set and 100% on an unbalanced one.
  translation   a real CDS and the protein Ensembl gives for the same
                transcript. The truth is a codon table, so a wrong answer
                cannot be argued with.
  organism      the group a genomic window comes from, asked as multiple
                choice because that is how GenomeQA -- the benchmark the
                model card scores 93.2% on -- poses it. Asked open-ended it
                is a different and harder task, and scoring that against
                93.2% would be comparing two things.

EVERY WINDOW IS VERIFIED BEFORE IT IS USED. A window fetched around a
coordinate is only usable if its centre base is the reference allele ClinVar
names; a silently off-by-one window would make every answer measured on it
meaningless while still looking like data. Windows that disagree are dropped
and counted.

Nothing here is a unit test: it needs the GPU, the weights, network access to
ClinVar/UCSC/Ensembl, and tens of minutes.

Usage:
    tu remote run carbonx &                     # or start the tool directly
    python scripts/remote_validation/carbonx_capability_eval.py \\
        --out carbonx_capability --windows 55,1001,8001
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import json
import random
import re
import sys
import time
from pathlib import Path

HALF = 4096  # half-width of the fetched window; rungs are cut from it

QUESTION = (
    "Is this variant likely to be benign or pathogenic? "
    "Reply with exactly one line and nothing else: "
    "'Answer: pathogenic' or 'Answer: benign'."
)
VERDICT = re.compile(r"answer\s*:\s*(pathogenic|benign)", re.I)
SPDI = re.compile(r"^NC_0*(\d+)\.\d+:(\d+):([ACGT]):([ACGT])$")
MISSENSE = re.compile(r"\(p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)$")
CDNA_SNV = re.compile(r"c\.(\d+)([ACGT])>([ACGT])")

GENES = ["BRCA1", "BRCA2", "TP53", "CFTR", "LDLR", "PAH", "MYH7", "SCN1A",
         "RET", "FBN1", "APC", "MLH1", "ATM", "PTEN", "KCNQ1", "TTN"]

ORGANISM_LOCI = [
    ("hg38", "chr11:5225000-5227000", "human", "A"),
    ("mm39", "chr7:103800000-103802000", "mouse", "A"),
    ("galGal6", "chr1:50000000-50002000", "chicken", "B"),
    ("danRer11", "chr3:30000000-30002000", "zebrafish", "C"),
    ("dm6", "chr2L:5000000-5002000", "fruit fly", "D"),
    ("ce11", "chrII:5000000-5002000", "nematode", "E"),
    ("sacCer3", "chrIV:500000-502000", "budding yeast", "F"),
]
CHOICES = [("A", "mammal"), ("B", "bird"), ("C", "fish"), ("D", "insect"),
           ("E", "nematode"), ("F", "fungus"), ("G", "bacterium")]

TRANSCRIPTS = ["ENST00000335295", "ENST00000269305", "ENST00000646891",
               "ENST00000366667", "ENST00000263100"]

_B = "TCAG"
_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON = {a + b + c: _AA[i * 16 + j * 4 + k]
         for i, a in enumerate(_B) for j, b in enumerate(_B)
         for k, c in enumerate(_B)}


def translate(cds: str) -> str:
    aa = "".join(CODON.get(cds[i:i + 3], "X") for i in range(0, len(cds) - 2, 3))
    return aa[:-1] if aa.endswith("*") else aa


def verdict(text: str) -> str:
    hits = VERDICT.findall(text or "")
    if hits:
        return hits[-1].lower()
    low = (text or "").lower()
    p, b = low.rfind("pathogenic"), low.rfind("benign")
    if p < 0 and b < 0:
        return "unparsed"
    return "pathogenic" if p > b else "benign"


# --------------------------------------------------------------------------
# building the set


def _dna(res) -> str:
    data = res.get("data") if isinstance(res, dict) else None
    if isinstance(data, dict):
        for key in ("dna", "sequence", "seq"):
            if isinstance(data.get(key), str) and data[key]:
                return data[key].upper()
    return ""


def build_variants(tu, per_gene: int, log) -> tuple[list, list]:
    def call(name, args, tries=4):
        for i in range(tries):
            try:
                out = tu.run_one_function({"name": name, "arguments": args})
                if isinstance(out, (dict, str)):
                    return out
            except Exception:  # noqa: BLE001 - retried, then reported as a drop
                pass
            time.sleep(1.5 * (i + 1))
        return None

    candidates = []
    for gene in GENES:
        for significance in ("Pathogenic", "Benign"):
            res = call("ClinVar_search_variants",
                       {"gene": gene, "clinical_significance": significance,
                        "max_results": 100})
            found = 0
            for v in (((res or {}).get("data") or {}).get("variants") or []):
                title = v.get("title") or ""
                m, s = MISSENSE.search(title), CDNA_SNV.search(title)
                # Missense SNVs only. A frameshift or a stop is pathogenic for
                # a reason a model can read off the sequence, so a set full of
                # them measures something easier than the task.
                if not (m and s) or m.group(1) == m.group(3):
                    continue
                if "Ter" in (m.group(1), m.group(3)):
                    continue
                candidates.append({"gene": gene, "variant_id": v["variant_id"],
                                   "title": title, "significance": significance})
                found += 1
                if found >= per_gene:
                    break
    log(f"clinvar candidates: {len(candidates)}")

    built, dropped = [], []
    for cand in candidates:
        det = call("ClinVar_get_variant_details", {"variant_id": cand["variant_id"]})
        raw = ((det or {}).get("data") or {}).get("raw_data") or {}
        spdi = ((raw.get("variation_set") or [{}])[0]).get("canonical_spdi") or ""
        m = SPDI.match(spdi)
        if not m:
            dropped.append((cand["title"], f"not a single-base spdi: {spdi!r}"))
            continue
        chrom, pos0, ref, alt = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        pos1 = pos0 + 1
        window = _dna(call("UCSC_get_sequence", {
            "genome": "hg38",
            "region": f"chr{int(chrom)}:{pos1 - HALF}-{pos1 + HALF}"}))
        if len(window) != 2 * HALF + 1:
            dropped.append((cand["title"], f"window is {len(window)} bases"))
            continue
        if window[HALF] != ref:
            dropped.append((cand["title"],
                            f"centre base {window[HALF]} != ClinVar ref {ref}"))
            continue
        built.append({**cand, "ref": ref, "alt": alt, "pos1": pos1,
                      "chrom": f"chr{int(chrom)}", "spdi": spdi,
                      "ref_window": window,
                      "alt_window": window[:HALF] + alt + window[HALF + 1:]})
    log(f"verified windows: {len(built)}, dropped {len(dropped)}")
    for title, why in dropped:
        log(f"  DROPPED {title}: {why}")
    return built, dropped


def balance(items: list, seed: int = 7) -> list:
    P = [i for i in items if i["significance"] == "Pathogenic"]
    B = [i for i in items if i["significance"] == "Benign"]
    n = min(len(P), len(B))
    random.Random(seed).shuffle(P)
    random.Random(seed).shuffle(B)
    return P[:n] + B[:n]


# --------------------------------------------------------------------------
# asking


def cut(seq: str, window: int) -> str:
    lo = HALF - window // 2
    return seq[lo:lo + window]


def context_line(window: int, ref: str, alt: str) -> str:
    return (f"Human genomic DNA, plus strand. The variant differs from the "
            f"reference at position {window // 2 + 1} of the sequence, "
            f"{ref}>{alt}.")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="http://127.0.0.1:8064/mcp")
    ap.add_argument("--out", default="carbonx_capability")
    ap.add_argument("--windows", default="55,1001,8001",
                    help="variant window lengths in BASES, comma separated")
    ap.add_argument("--per-gene", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=1,
                    help=">1 also reports whether the verdict is stable")
    ap.add_argument("--max-tokens", type=int, default=24)
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        lines.append(msg)

    from fastmcp import Client
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()
    variants, dropped = build_variants(tu, args.per_gene, log)
    variants = balance(variants)
    n_each = len(variants) // 2
    log(f"balanced set: {n_each} pathogenic + {n_each} benign")
    (out_dir / "variants.json").write_text(json.dumps(
        [{k: v for k, v in x.items() if not k.endswith("_window")}
         for x in variants], indent=1))

    windows = [int(w) for w in args.windows.split(",")]
    rows: list[dict] = []
    async with Client(args.endpoint) as client:

        async def ask(question, sequences, context, max_tokens, seed):
            res = await client.call_tool("carbonx_ask_dna", {
                "question": question, "sequences": sequences,
                "context": context, "max_tokens": max_tokens, "seed": seed})
            return json.loads(res.content[0].text)

        for window in windows:
            for seed in range(args.seeds):
                for item in variants:
                    payload = await ask(
                        QUESTION,
                        {"reference": cut(item["ref_window"], window),
                         "variant": cut(item["alt_window"], window)},
                        context_line(window, item["ref"], item["alt"]),
                        args.max_tokens, seed)
                    rows.append({
                        "title": item["title"], "gene": item["gene"],
                        "truth": item["significance"].lower(),
                        "window": window, "seed": seed,
                        "verdict": verdict(payload.get("answer", "")),
                        "prompt_tokens": payload.get("prompt_tokens"),
                        "error": payload.get("error")})
            cell = [r for r in rows if r["window"] == window]
            ok = sum(1 for r in cell if r["verdict"] == r["truth"])
            tp = sum(1 for r in cell
                     if r["truth"] == "pathogenic" and r["verdict"] == "pathogenic")
            tn = sum(1 for r in cell
                     if r["truth"] == "benign" and r["verdict"] == "benign")
            un = sum(1 for r in cell if r["verdict"] in ("unparsed", "error"))
            log(f"VARIANTS window={window:5d} n={len(cell):3d} "
                f"acc={100*ok/max(len(cell),1):5.1f}%  "
                f"sens={tp}/{n_each*args.seeds} spec={tn}/{n_each*args.seeds} "
                f"unparsed={un}")

        # A verdict that moves with the window is not a property of the
        # variant, and the aggregate hides it: a small net gain can be a large
        # number of offsetting flips.
        if len(windows) > 1:
            by = {}
            for r in rows:
                if r["seed"] == 0:
                    by.setdefault(r["title"], {})[r["window"]] = r["verdict"]
            lo, hi = windows[-2], windows[-1]
            changed = sum(1 for d in by.values()
                          if d.get(lo) != d.get(hi))
            log(f"VERDICT CHANGED between window {lo} and {hi}: "
                f"{changed}/{len(by)} variants")

        if args.seeds > 1:
            by = {}
            for r in rows:
                by.setdefault((r["title"], r["window"]), []).append(r["verdict"])
            unanimous = sum(1 for v in by.values() if len(set(v)) == 1)
            log(f"UNANIMOUS across {args.seeds} seeds: {unanimous}/{len(by)}")

        # ---- translation ---------------------------------------------------
        for tid in TRANSCRIPTS:
            cds = _dna(tu.run_one_function({
                "name": "EnsemblSeq_get_id_sequence",
                "arguments": {"ensembl_id": tid, "type": "cds"}}))
            if len(cds) < 300:
                log(f"TRANSLATE {tid}: skipped, cds is {len(cds)} bases")
                continue
            for nbases in (60, 300):
                truth = translate(cds[:nbases])
                payload = await ask(
                    "Translate this sequence into its amino-acid sequence "
                    "using the standard genetic code. Reply with exactly one "
                    "line and nothing else: the one-letter amino-acid sequence.",
                    {"reference": cds[:nbases]},
                    "Human coding DNA, plus strand, in frame: the first base "
                    "is the first base of a codon.", 160, 0)
                said = re.sub(r"[^A-Z*]", "", (payload.get("answer") or "").upper())
                sm = difflib.SequenceMatcher(None, truth, said, autojunk=False)
                aligned = sum(b.size for b in sm.get_matching_blocks())
                rows.append({"kind": "translation", "transcript": tid,
                             "bases": nbases, "exact": said == truth,
                             "aligned": aligned, "length": len(truth)})
                log(f"TRANSLATE {tid} {nbases:4d}bp len={len(truth):3d} "
                    f"exact={said == truth} aligned={aligned}/{len(truth)}")

        # ---- organism group, multiple choice --------------------------------
        menu = "\n".join(f"{k}. {v}" for k, v in CHOICES)
        for nbases in (300, 2001):
            hits = total = 0
            for genome, region, name, want in ORGANISM_LOCI:
                dna = _dna(tu.run_one_function({
                    "name": "UCSC_get_sequence",
                    "arguments": {"genome": genome, "region": region}}))
                if len(dna) < nbases or set(dna) - set("ACGTN"):
                    log(f"ORGANISM {name}: skipped, {len(dna)} usable bases")
                    continue
                payload = await ask(
                    f"Which group of organisms is this genomic DNA from?\n"
                    f"{menu}\n\nReply with exactly one line and nothing else: "
                    f"the single letter of your choice.",
                    {"reference": dna[:nbases]}, "", 8, 0)
                m = re.search(r"\b([A-G])\b", (payload.get("answer") or "").upper())
                got = m.group(1) if m else "?"
                hits += got == want
                total += 1
                rows.append({"kind": "organism", "organism": name,
                             "bases": nbases, "want": want, "got": got})
            if total:
                log(f"ORGANISM window={nbases:5d} {hits}/{total} correct, "
                    f"chance is 1/{len(CHOICES)}")

    (out_dir / "rows.json").write_text(json.dumps(rows, indent=1))
    (out_dir / "report.txt").write_text("\n".join(lines) + "\n")
    log(f"\nwrote {out_dir}/rows.json and {out_dir}/report.txt")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
