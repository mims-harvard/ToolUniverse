"""Borzoi variant scoring (calico/borzoi `borzoi_sad.py`) held resident.

Run by the model's own interpreter::

    BORZOI_OPT=<mode> <model python> borzoi_calico_resident_worker.py --socket … --slug …

WHAT IS HELD, AND WHY THAT IS THE WHOLE PROVIDER. Stock `borzoi_sad.py` does
three things in one `main()`: it reads the parameters and the targets table and
builds the strand-sum transform; it builds the network, restores the fold-0
checkpoint and assembles the reverse-complement ensemble; and only then does it
loop over the variants. The first two cost about 49 s of the 304 s a
one-variant run takes, and they do not depend on the request at all. This worker
does them once at start-up and keeps the genome handle open beside them, so a
request pays the loop alone.

NOTHING NUMERIC IS REIMPLEMENTED HERE. The setup below is stock's own lines
161-227 in stock's own order, and the loop calls stock's own module-level
helpers -- `initialize_output_h5`, `write_snp_len`, `write_pct` -- imported out
of `borzoi_sad` itself, plus `baskerville.vcf.snp_seq1`,
`baskerville.dataset.untransform_preds` and the `seqnn` model. The worker writes
the same `sad.h5` into the request's own directory, and the reply is read back
out of that file. The equivalence gate therefore compares two files that stock's
own writer produced, which is the only comparison worth making.

One subtlety that is easy to get wrong and changes the arithmetic: stock sets
`sum_length = (options.sad_stats == 'SAD')`, an equality against the whole
comma-joined string. The pinned command passes `--stats SAD,logSAD,D2,logD2`, so
`sum_length` is **False**, `build_sad()` is NOT called, and `write_snp_len` runs
rather than `write_snp`. Reading that line as "SAD is among the stats" would
build a different graph and write a different file.

One request at a time: two of these in one process would share the TensorFlow
intra-op pool and ~10 GiB of peak RSS each.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="borzoi_calico", help="provider slug, echoed in ping")
ap.add_argument("--weights-root", default="", help="holds f0/model0_best.h5 and hg38.ml.fa")
ap.add_argument("--borzoi-dir", default="", help="the calico/borzoi checkout (examples/ lives here)")
ap.add_argument(
    "--stats",
    default="SAD,logSAD,D2,logD2",
    help="stock's --stats, verbatim; the pinned set",
)
args = ap.parse_args()

T0 = time.time()


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr."""
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[borzoi-calico-resident] {msg}", flush=True)


def _load_worker_base():
    import importlib.util

    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    here = Path(__file__).resolve()
    path = (
        Path(override)
        if override
        else here.parents[3] / "remote_resident" / "worker_base.py"
    )
    if not path.is_file():
        raise _refuse(
            f"[borzoi-calico-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

WEIGHTS_ROOT = Path(args.weights_root or os.environ.get("BORZOI_CALICO_WEIGHTS", "")).expanduser()
BORZOI_DIR = Path(args.borzoi_dir or os.environ.get("BORZOI_DIR", "")).expanduser()
if not WEIGHTS_ROOT.is_dir():
    raise _refuse(
        "[borzoi-calico-resident] no weights directory: set BORZOI_CALICO_WEIGHTS "
        "to the directory holding f0/model0_best.h5 and hg38.ml.fa"
    )
if not BORZOI_DIR.is_dir():
    raise _refuse(
        "[borzoi-calico-resident] no borzoi checkout: set BORZOI_DIR to the "
        "calico/borzoi checkout (its examples/params.json and "
        "examples/targets_human.txt are read here)"
    )

MODEL_FILE = WEIGHTS_ROOT / "f0" / "model0_best.h5"
GENOME_FASTA = WEIGHTS_ROOT / "hg38.ml.fa"
PARAMS_FILE = BORZOI_DIR / "examples" / "params.json"
TARGETS_FILE = BORZOI_DIR / "examples" / "targets_human.txt"
for p, what in (
    (MODEL_FILE, "the fold-0 checkpoint"),
    (GENOME_FASTA, "the genome"),
    (PARAMS_FILE, "upstream's params.json"),
    (TARGETS_FILE, "upstream's targets_human.txt"),
):
    if not p.is_file():
        raise _refuse(f"[borzoi-calico-resident] {what} is not at {p}")

# stock's own imports, in stock's own order (borzoi_sad.py:26-38).
import json  # noqa: E402
import h5py  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pysam  # noqa: E402
from scipy.sparse import dok_matrix  # noqa: E402
import tensorflow as tf  # noqa: E402

from baskerville import dataset  # noqa: E402
from baskerville import seqnn  # noqa: E402
from baskerville import vcf as bvcf  # noqa: E402

# Stock's own writer and initialiser, imported rather than copied. `borzoi_sad`
# is a script on PYTHONPATH (BORZOI_DIR/src/scripts), which is how upstream's own
# image puts it there.
try:
    import borzoi_sad as STOCK  # noqa: E402
except Exception as exc:  # noqa: BLE001
    raise _refuse(
        f"[borzoi-calico-resident] stock borzoi_sad is not importable ({exc!r}). "
        f"Put {BORZOI_DIR / 'src' / 'scripts'} on PYTHONPATH -- its "
        f"initialize_output_h5, write_snp_len and write_pct are what this worker "
        f"writes with, and nothing here reimplements them."
    )

GPUS = tf.config.list_physical_devices("GPU")
DEVICE = "gpu" if GPUS else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s tf={tf.__version__} device={DEVICE} "
    f"kit_mode={os.environ.get('BORZOI_OPT', 'off')}"
)

# ---------------------------------------------------------------- stock's setup
# borzoi_sad.py:161-227, verbatim in order. `--rc` on, `--shifts 0`,
# `--stats SAD,logSAD,D2,logD2`, `-u` (untransform), targets file given.
_t = time.time()
with open(PARAMS_FILE) as params_open:
    params = json.load(params_open)
PARAMS_MODEL = params["model"]
PARAMS_TRAIN = params["train"]

TARGETS_DF = pd.read_csv(TARGETS_FILE, sep="\t", index_col=0)
TARGET_SLICE = TARGETS_DF.index
SUM_STRAND = "strand_pair" in TARGETS_DF.columns
if SUM_STRAND:
    TARGETS_STRAND_DF = dataset.targets_prep_strand(TARGETS_DF)
    orig_new_index = dict(zip(TARGETS_DF.index, np.arange(TARGETS_DF.shape[0])))
    targets_strand_pair = np.array(
        [orig_new_index[ti] for ti in TARGETS_DF.strand_pair]
    )
    PARAMS_MODEL["strand_pair"] = [targets_strand_pair]
    _st = dok_matrix((TARGETS_DF.shape[0], TARGETS_STRAND_DF.shape[0]))
    ti = 0
    sti = 0
    for _, target in TARGETS_DF.iterrows():
        _st[ti, sti] = True
        if target.strand_pair == target.name:
            sti += 1
        else:
            if target.identifier[-1] == "-":
                sti += 1
        ti += 1
    STRAND_TRANSFORM = _st.tocsr()
else:
    TARGETS_STRAND_DF = TARGETS_DF
    STRAND_TRANSFORM = None

# STOCK'S OWN LIST, AND STOCK'S OWN DEAD BRANCH, BOTH PRESERVED DELIBERATELY.
# borzoi_sad.py:159 splits `--stats` into a list, and :210 then tests
# `sum_length = (options.sad_stats == 'SAD')` -- a LIST against a STRING, which
# is always False. So upstream never calls `build_sad()` and always writes with
# `write_snp_len`, for every `--stats` value including `--stats SAD` alone.
# That is an upstream bug and it is reproduced here rather than corrected,
# because this provider's whole claim is that it answers what stock answers.
# Correcting it would change the graph and the file for `--stats SAD`.
#
# Note what did NOT catch this: the equivalence gate. The pinned stats make the
# bug and a "fixed" version agree, so comparing outputs proved nothing; reading
# :159 and :210 together is what found it. An earlier draft of this worker
# passed the comma-joined STRING to stock's helpers, which made
# `for sad_stat in sad_stats` iterate CHARACTERS and die on the second 'S' with
# "name already exists" -- the same line, failing loudly for a different reason.
STATS = [x for x in args.stats.split(",") if x]
SUM_LENGTH = STATS == "SAD"

MODEL = seqnn.SeqNN(PARAMS_MODEL)
MODEL.restore(str(MODEL_FILE))
MODEL.build_slice(TARGET_SLICE)
if SUM_LENGTH:
    MODEL.build_sad()
# `--rc` on and `--shifts "0"`, which stock turns into a LIST before it gets
# here (borzoi_sad.py:158, `[int(s) for s in options.shifts.split(",")]`).
# Passing the bare int builds no ensemble at all: baskerville takes len()
# of it (seqnn.py:240) and raises, which is the good case -- a signature
# that silently accepted it would have scored every variant without the
# reverse-complement average the pinned command asks for.
MODEL.build_ensemble(True, [0])
TARGETS_LENGTH = MODEL.target_lengths[0]
BUILD_S = time.time() - _t
GENOME = pysam.Fastafile(str(GENOME_FASTA))
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s "
    f"(targets {TARGETS_DF.shape[0]} -> {TARGETS_STRAND_DF.shape[0]} strand-summed, "
    f"target_length {TARGETS_LENGTH}, sum_length={SUM_LENGTH}) genome open"
)

MAX_VARIANTS = int(os.environ.get("BORZOI_CALICO_MAX_VARIANTS", "4"))
VCF_HEADER = "##fileformat=VCFv4.2\n"


def _write_vcf(variants, path: Path) -> None:
    """A VCF stock's own reader will parse. `chr` prefix required: baskerville's
    vcf.SNP prepends it to a bare chromosome name (vcf.py:672-675), so a caller
    sending `1` and a caller sending `chr1` must not land on different
    sequences."""
    lines = [VCF_HEADER]
    for v in variants:
        lines.append(
            "\t".join(
                [
                    str(v["chrom"]),
                    str(v["pos"]),
                    str(v["id"]),
                    str(v["ref"]),
                    str(v["alt"]),
                    ".",
                    ".",
                ]
            )
            + "\n"
        )
    path.write_text("".join(lines))


def _parse_vcf_text(text: str) -> list:
    """The columns stock's own reader takes, from VCF text."""
    out = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t") if "\t" in line else line.split()
        if len(f) < 5:
            raise ValueError(f"VCF line has {len(f)} fields, needs at least 5: {line!r}")
        out.append(
            {"chrom": f[0], "pos": f[1], "id": f[2], "ref": f[3], "alt": f[4]}
        )
    return out


def _normalise(v: dict, i: int) -> dict:
    """One variant, with the `chr` prefix settled HERE rather than left to
    chance. baskerville's `vcf.SNP` prepends `chr` to a bare chromosome name
    (vcf.py:672-675), so `1` and `chr1` reach the same sequence -- but the id
    written into sad.h5 is whatever the caller sent, and two callers who disagree
    about the prefix would get rows that look like different variants."""
    if not isinstance(v, dict):
        raise ValueError(f"variant {i} is not an object: {v!r}")
    missing = [k for k in ("chrom", "pos", "ref", "alt") if not str(v.get(k, "")).strip()]
    if missing:
        raise ValueError(f"variant {i} is missing {missing}")
    chrom = str(v["chrom"]).strip()
    if not chrom.startswith("chr"):
        chrom = "chr" + chrom
    pos = int(str(v["pos"]).strip())
    ref = str(v["ref"]).strip().upper()
    alt = str(v["alt"]).strip().upper()
    for name, allele in (("ref", ref), ("alt", alt)):
        if set(allele) - set("ACGT") or not allele:
            raise ValueError(f"variant {i} {name} allele {allele!r} is not ACGT")
    rsid = str(v.get("id") or "").strip() or f"{chrom}_{pos}_{ref}_{alt}"
    return {"chrom": chrom, "pos": pos, "id": rsid, "ref": ref, "alt": alt}


def _predict_one(req: dict) -> dict:
    """One VCF through stock's loop, written with stock's own writer."""
    variants = req.get("variants")
    # The smoke step hands a provider the TEXT of its smoke file as `input`,
    # which for this one is either a JSON body or a VCF. Accepting both here is
    # what lets `smoke/input.json` and a tool request travel the same path --
    # proteinmpnn's smoke contract, learned from `setup.step_smoke` rather than
    # assumed.
    if variants is None and isinstance(req.get("input"), str):
        text = req["input"].strip()
        if text.startswith("{"):
            variants = json.loads(text).get("variants")
        else:
            variants = _parse_vcf_text(text)
    if not isinstance(variants, list) or not variants:
        raise ValueError(
            "a request needs 'variants' (a non-empty list of "
            "{chrom,pos,id,ref,alt}), or 'input' holding that as JSON or a VCF"
        )
    variants = [_normalise(v, i) for i, v in enumerate(variants)]
    if len(variants) > MAX_VARIANTS:
        raise ValueError(
            f"{len(variants)} variants asked; the ceiling is {MAX_VARIANTS}. "
            f"Each costs about 255 s on this CPU."
        )
    out_dir = Path(req.get("out_dir") or ".").expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    timing = {}
    t = time.time()
    vcf_path = out_dir / "request.vcf"
    _write_vcf(variants, vcf_path)
    snps = bvcf.vcf_snps(str(vcf_path))
    timing["read_vcf_s"] = round(time.time() - t, 3)
    if not snps:
        raise ValueError("stock's VCF reader found no usable variants in the request")

    t = time.time()
    # stock's own initialiser, into the request's own directory
    sad_out = STOCK.initialize_output_h5(
        str(out_dir), STATS, snps, TARGETS_LENGTH, TARGETS_STRAND_DF
    )
    for si, snp in enumerate(snps):
        snp_1hot_list = bvcf.snp_seq1(snp, PARAMS_MODEL["seq_length"], GENOME)
        snps_1hot = np.array(snp_1hot_list)
        if PARAMS_TRAIN["batch_size"] == 1:
            ref_preds = MODEL(snps_1hot[:1])[0]
            alt_preds = MODEL(snps_1hot[1:])[0]
        else:
            snp_preds = MODEL(snps_1hot)
            ref_preds, alt_preds = snp_preds[0], snp_preds[1]
        # READ THE OPTION'S `dest`, NOT ITS LETTER. The pinned command passes
        # `-u`, and `-u` is declared `dest='untransform_old'`
        # (borzoi_sad.py:98-103) with no help string -- so the pinned run takes
        # the OLD untransform, `untransform_preds1`, not `untransform_preds`.
        # An earlier draft of this worker read `-u` as "untransform" and called
        # the new one; the numbers differ, so the gate would have caught it,
        # but the option table said so first.
        ref_preds = dataset.untransform_preds1(ref_preds, TARGETS_DF)
        alt_preds = dataset.untransform_preds1(alt_preds, TARGETS_DF)
        if SUM_STRAND:
            ref_preds = ref_preds * STRAND_TRANSFORM
            alt_preds = alt_preds * STRAND_TRANSFORM
        if SUM_LENGTH:
            STOCK.write_snp(ref_preds, alt_preds, sad_out, si, STATS)
        else:
            STOCK.write_snp_len(ref_preds, alt_preds, sad_out, si, STATS)
    STOCK.write_pct(sad_out, STATS)
    sad_out.close()
    timing["score_s"] = round(time.time() - t, 3)

    # The reply is read back out of the file stock's writer produced, so what a
    # caller sees and what the gate compares are the same numbers.
    top_k = int(req.get("top_tracks") or 20)
    stats = list(STATS)
    body = {
        "n_variants": len(snps),
        "n_tracks": int(TARGETS_STRAND_DF.shape[0]),
        "stats": stats,
        "sad_h5": str(out_dir / "sad.h5"),
        "variants": [],
        "timing_s": timing,
    }
    with h5py.File(out_dir / "sad.h5", "r") as f:
        ids = [b.decode() for b in f["target_ids"][()]]
        labels = [b.decode() for b in f["target_labels"][()]]
        for si, snp in enumerate(snps):
            row = {
                "snp": f["snp"][si].decode(),
                "chr": f["chr"][si].decode(),
                "pos": int(f["pos"][si]),
                "ref_allele": f["ref_allele"][si].decode(),
                "alt_allele": f["alt_allele"][si].decode(),
            }
            sad = np.asarray(f["SAD"][si], dtype=np.float64)
            order = np.argsort(-np.abs(sad))[:top_k]
            row["top_tracks"] = [
                {
                    "index": int(i),
                    "identifier": ids[int(i)],
                    "description": labels[int(i)],
                    **{s: float(np.asarray(f[s][si])[int(i)]) for s in stats},
                }
                for i in order
            ]
            row["max_abs_SAD"] = float(np.abs(sad).max())
            body["variants"].append(row)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "tf": tf.__version__,
        "kit_mode": os.environ.get("BORZOI_OPT", "off"),
        "n_targets": int(TARGETS_DF.shape[0]),
        "n_tracks": int(TARGETS_STRAND_DF.shape[0]),
        "sum_length": SUM_LENGTH,
        "max_variants": MAX_VARIANTS,
        "weights_held_by": "worker",
    }


if __name__ == "__main__":
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            log=say,
        )
    )
