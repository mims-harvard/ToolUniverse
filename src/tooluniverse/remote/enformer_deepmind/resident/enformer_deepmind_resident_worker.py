"""The official DeepMind Enformer SavedModel held resident, one request at a time.

Run by the model's own interpreter::

    ENFORMER_DEEPMIND_OPT=<mode> <model python> enformer_deepmind_resident_worker.py --socket … --slug …

The kit's mode variable is set by ``launch.py`` and is ``off`` on this host, so
nothing of the kit is on the path and what runs is upstream's own call --
``tensorflow_hub.load(handle).model.predict_on_batch(x)``, exactly as
``enformer-usage.ipynb`` writes it. The kit's ``exact`` mode refuses here for a
reason that is read off the file rather than guessed: its levers live in
``opt/enformer_deepmind_opt/ops/edm_ops.so``, whose ELF header says ``x86-64``,
and the kit's own dry run says ``NOT ACTIVE mode=exact reason=no CUDA device
visible``.

WHAT RESIDENCY BUYS HERE, MEASURED: almost nothing, and the provider says so
rather than implying otherwise. Two consecutive predictions of the same window
cost 194.1 s and 205.8 s -- the second is not faster, so there is no graph
tracing to amortise and no warm-up to collect. The model load is 2.7 s warm and
28.6 s cold against a ~200 s request. What this provider is actually for is the
separation (TensorFlow 2.17.1 with numpy 1.26.4 cannot be installed beside
ToolUniverse's own stack), the pinned-weights verification, and the one
lifecycle every provider on this standard shares.

One request at a time: TensorFlow would otherwise thread two 393,216-base
windows through one intra-op pool and make either one's wall time
unattributable.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="enformer_deepmind", help="provider slug, echoed in ping")
ap.add_argument(
    "--handle",
    default="https://tfhub.dev/deepmind/enformer/1",
    help="the pinned TF-Hub handle (resolved offline from TFHUB_CACHE_DIR)",
)
args = ap.parse_args()

T0 = time.time()


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr."""
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[enformer-deepmind-resident] {msg}", flush=True)


# The shared worker runtime is loaded BY PATH, never as a ToolUniverse import:
# this process runs in the model's own environment, which holds TensorFlow
# 2.17.1 and nothing of this package.
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
            f"[enformer-deepmind-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import numpy as np  # noqa: E402

# The cache directory must be set before tensorflow_hub reads it, and the
# launcher sets it; a missing one is a refusal rather than a silent fetch.
if not os.environ.get("TFHUB_CACHE_DIR"):
    raise _refuse(
        "[enformer-deepmind-resident] TFHUB_CACHE_DIR is unset: this worker "
        "resolves the pinned SavedModel offline and never fetches. Run "
        "`tu remote setup enformer_deepmind --only weights`."
    )

import tensorflow as tf  # noqa: E402
import tensorflow_hub as hub  # noqa: E402

# Upstream's own shapes, read from the kit's stock/PINS.json rather than assumed.
INPUT_LENGTH = 393_216          # what predict_on_batch takes
RECEPTIVE_LENGTH = 196_608      # what the graph reads out of the centre
N_BINS = 896
BASE_TO_COL = {"A": 0, "C": 1, "G": 2, "T": 3}
ORGANISMS = ("human", "mouse")
N_TRACKS = {"human": 5313, "mouse": 1643}

GPUS = tf.config.list_physical_devices("GPU")
DEVICE = "gpu" if GPUS else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s tf={tf.__version__} "
    f"hub={hub.__version__} device={DEVICE}"
)

_t = time.time()
MODEL = hub.load(args.handle).model
BUILD_S = time.time() - _t
say(f"SavedModel resident on {DEVICE} in {BUILD_S:.1f}s")


def _one_hot(sequence: str) -> "np.ndarray":
    """Centre-crop or N-pad to the model's fixed input length, then one-hot.

    ACGT order with N (and any other letter) as an all-zero row, which is what
    upstream's usage notebook feeds and what stock/PINS.json records.
    """
    seq = (sequence or "").strip().upper()
    if len(seq) > INPUT_LENGTH:
        start = (len(seq) - INPUT_LENGTH) // 2
        seq = seq[start : start + INPUT_LENGTH]
    elif len(seq) < INPUT_LENGTH:
        pad = INPUT_LENGTH - len(seq)
        left = pad // 2
        seq = "N" * left + seq + "N" * (pad - left)
    x = np.zeros((1, INPUT_LENGTH, 4), dtype=np.float32)
    cols = np.fromiter(
        (BASE_TO_COL.get(b, -1) for b in seq), dtype=np.int8, count=INPUT_LENGTH
    )
    known = cols >= 0
    x[0, np.nonzero(known)[0], cols[known]] = 1.0
    return x


def _predict_one(req: dict) -> dict:
    """One window through the SavedModel.

    Returns the centre bin across every track -- the same key the torch-port
    `enformer` provider answers with, so a caller can compare the two
    implementations field for field -- plus the full profile of any track named.
    The whole (896, 5313) tensor is 19 MB of JSON and nothing asks for it.
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
    x = _one_hot(sequence)
    timing["encode_s"] = round(time.time() - t, 3)

    t = time.time()
    out = MODEL.predict_on_batch(x)
    pred = np.asarray(out[organism])[0]          # (896, n_tracks)
    timing["inference_s"] = round(time.time() - t, 3)

    if pred.shape[1] != N_TRACKS[organism]:
        raise ValueError(
            f"{organism} head returned {pred.shape[1]} tracks, not the pinned "
            f"{N_TRACKS[organism]}: the SavedModel is not the pinned revision"
        )

    body = {
        "organism": organism,
        "n_bins": int(pred.shape[0]),
        "n_tracks": int(pred.shape[1]),
        "input_length": INPUT_LENGTH,
        "receptive_length": RECEPTIVE_LENGTH,
        "centre": [float(v) for v in pred[N_BINS // 2]],
        "timing": timing,
    }
    if tracks:
        wanted = [int(i) for i in tracks if 0 <= int(i) < pred.shape[1]]
        body["profiles"] = {str(i): [float(v) for v in pred[:, i]] for i in wanted}
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "handle": args.handle,
        "tf": tf.__version__,
        "kit_mode": os.environ.get("ENFORMER_DEEPMIND_OPT", "off"),
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
