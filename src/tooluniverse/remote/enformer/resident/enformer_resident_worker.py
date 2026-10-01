"""Enformer held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    ENFORMER_OPT=exact <model python> enformer_resident_worker.py --socket … --slug …

That is the whole activation. The kit installs a ``.pth`` that imports its
``_autoload`` at interpreter start; with the variable set, a meta-path finder
waits for ``enformer_pytorch`` and installs the kit's levers on it in this
process — ``poscache``, ``fused``, ``graph`` and ``xattn``. Our code is
unmodified, and nothing of the kit is patched or copied. This is the path 30 of
the 36 kits offer; ``boltz2`` is the one that instead ships an explicit
``worker_launch``, and ``chrombpnet`` the one that offers no in-process patch at
all.

Why hold it. Enformer's tool already cached the model in the MCP server's own
process, so residency is not what this buys — the two things it buys are the
separation and the levers. The separation is the point of the exercise: this
model pins torch 2.13.0 and numpy 2.4.6, Boltz-2 pins torch 2.12.0 and numpy
1.26.4, and ToolUniverse's other 600+ tools want neither. The levers include
``graph``, which captures on one call and replays on later ones, so the saving
is only collectable by a process that survives between requests.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="enformer", help="provider slug, echoed in ping")
ap.add_argument(
    "--model", default="EleutherAI/enformer-official-rough", help="the pinned snapshot"
)
args = ap.parse_args()

T0 = time.time()


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on, and
    the whole point of a named refusal is that a caller can.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[enformer-resident] {msg}", flush=True)


# The shared worker runtime is loaded BY PATH, never as a ToolUniverse import:
# this process runs in the model's own environment, which holds enformer_pytorch
# and its pinned stack and nothing of this package.
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
            f"[enformer-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import torch  # noqa: E402

torch.set_grad_enabled(False)

from enformer_pytorch import from_pretrained  # noqa: E402  <- the kit's trigger

SEQ_LENGTH = 196_608
N_BINS = 896
BASE_TO_IDX = {"A": 0, "C": 1, "G": 2, "T": 3, "N": 4}
ORGANISMS = ("human", "mouse")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")

_t = time.time()
MODEL = from_pretrained(args.model).to(DEVICE)
MODEL.eval()
BUILD_S = time.time() - _t
say(f"model resident on {DEVICE} in {BUILD_S:.1f}s")


def _encode(sequence: str) -> torch.Tensor:
    """Centre-crop or N-pad to Enformer's fixed input length, then index-encode.

    The same crop and pad the tool has always applied, so a sequence gives the
    same prediction through either route.
    """
    seq = (sequence or "").strip().upper()
    if len(seq) > SEQ_LENGTH:
        start = (len(seq) - SEQ_LENGTH) // 2
        seq = seq[start : start + SEQ_LENGTH]
    elif len(seq) < SEQ_LENGTH:
        pad = SEQ_LENGTH - len(seq)
        left = pad // 2
        seq = "N" * left + seq + "N" * (pad - left)
    return torch.tensor(
        [[BASE_TO_IDX.get(b, 4) for b in seq]], dtype=torch.long, device=DEVICE
    )


def _predict_one(req: dict) -> dict:
    """One sequence through the model.

    Returns the centre bin across every track — what both of this provider's
    operations are computed from — plus the full profile of any track the caller
    names. The whole (896, 5313) tensor is 19 MB of JSON and nothing asks for it.
    """
    sequence = req.get("input") or req.get("sequence")
    if not sequence:
        raise ValueError("a request needs 'input' (or 'sequence'): a DNA string")
    organism = (req.get("organism") or "human").strip().lower()
    if organism not in ORGANISMS:
        raise ValueError(f"'organism' must be one of {ORGANISMS}, not {organism!r}")
    tracks = req.get("tracks") or []

    timing = {}
    t = time.time()
    encoded = _encode(sequence)
    timing["encode_s"] = round(time.time() - t, 3)

    t = time.time()
    with torch.no_grad():
        out = MODEL(encoded)
    pred = out[organism][0]  # (896, n_tracks)
    if DEVICE.type == "cuda":
        torch.cuda.synchronize()
    timing["inference_s"] = round(time.time() - t, 3)

    centre = pred[N_BINS // 2]
    body = {
        "organism": organism,
        "n_bins": int(pred.shape[0]),
        "n_tracks": int(pred.shape[1]),
        "centre": [float(v) for v in centre],
        "timing": timing,
    }
    if tracks:
        wanted = [int(i) for i in tracks if 0 <= int(i) < pred.shape[1]]
        body["profiles"] = {str(i): [float(v) for v in pred[:, i]] for i in wanted}
    if DEVICE.type == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {"build_s": round(BUILD_S, 1), "device": str(DEVICE), "model": args.model}


def _reset() -> None:
    if DEVICE.type == "cuda":
        torch.cuda.reset_peak_memory_stats()


if __name__ == "__main__":
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            on_reset=_reset,
            log=say,
        )
    )
