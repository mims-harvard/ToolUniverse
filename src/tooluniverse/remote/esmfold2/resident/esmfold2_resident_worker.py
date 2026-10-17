"""ESMFold2 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    ESMFOLD2_OPT=fast <model python> esmfold2_resident_worker.py --socket … --slug …

That is the whole activation, and it is the form 30 of the 36 kits offer: the
kit installs ``esmfold2_opt_autoload.pth``, which imports ``esmfold2_opt._autoload``
at interpreter start; with ``ESMFOLD2_OPT`` naming a mode, a meta-path finder
waits for the first import of ``transformers.models.esmfold2`` or
``esm.models.esmfold2`` and calls ``esmfold2_opt.enable(mode, …)`` on it. The
variable's name is the kit's own (``_autoload.ENV``), read off the kit by
``kit_launch``'s probe rather than guessed from the slug.

**Two orderings this worker has to get right, both of them the kit's rules.**

*The variant is read at the trigger import, not at interpreter start.* The kit
takes it from ``ESMFOLD2_VARIANT`` at the moment its finder fires
(``esmfold2_opt/stack.py``), one variant per process and never two. So this
script puts the variant in its own environment **before** it imports anything
upstream. ``kit_launch`` cannot set it: it comes from this worker's own
``--variant``, since the variant chooses the checkpoint as well as the model.

*The model is built after the trigger import.* ``enable()`` is refused once an
``ESMFold2Model`` instance exists — "importing upstream before enable() is fine;
constructing a model before it is not" (``stack.py``). Building the model at the
top of this file would therefore take the whole kit to NOT ACTIVE.

**Who holds the weights, and why the answer differs from Chai-1's.** Chai-1's
kit replaces ``chai1.load_exported`` with its own loader and refuses to activate
if anything replaced it first, so that worker must *not* memoise it. This kit
replaces no loader at all: what it wraps is ``ESMFold2InputBuilder.fold`` (so its
``configure()`` runs on a model at that model's first fold) and
``ESMFold2Model.__new__`` (only to count instances, calling the original
unchanged). Nothing in the kit holds a checkpoint between folds. So the holding
is this worker's job under every mode, kit or ``off`` — it builds the model once
and keeps it — and the ready line says ``weights_held_by=worker`` with the kit
word beside it, so the record never reads as a claim about the kit.

What that buys: the kit's own README measures ≈25 s of start-up per process in
every mode — interpreter, checkpoint load and digest — on a 6B-parameter language
model that every variant loads. A process that exits after each request pays all
of it again, and the CUDA graphs the ``exact`` / ``fast`` modes capture on one
request are collectable only by a process that survives to the next.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# stock/PINS.json "variants": the checkpoint each variant folds with. Every one
# of them also loads biohub/ESMC-6B as its language model.
HF_REPO = {
    "fast": "biohub/ESMFold2-Fast",
    "full_msa": "biohub/ESMFold2",
    "full_nomsa": "biohub/ESMFold2",
}

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="esmfold2", help="provider slug, echoed in ping")
ap.add_argument(
    "--variant",
    default="fast",
    choices=sorted(HF_REPO),
    help="one variant per process (the kit's rule): fast = ESMFold2-Fast, "
    "full_msa / full_nomsa = ESMFold2 with / without MSAs",
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
    print(f"[esmfold2-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds ESMFold2's pinned stack
    and nothing of ToolUniverse, and importing the package would defeat that."""
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
            f"[esmfold2-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

VARIANT = args.variant
MODE = (os.environ.get("ESMFOLD2_OPT") or "off").strip().lower() or "off"
# Before any upstream import: the kit reads this when its finder fires, and a
# variant that disagrees with one already in the environment is the kit's own
# refusal, so we do not overwrite a caller's choice silently.
declared = (os.environ.get("ESMFOLD2_VARIANT") or "").strip()
if declared and declared != VARIANT:
    raise _refuse(
        f"[esmfold2-resident] --variant {VARIANT} disagrees with "
        f"ESMFOLD2_VARIANT={declared} in the environment; one variant per process"
    )
os.environ["ESMFOLD2_VARIANT"] = VARIANT
# The weights are pinned and verified before this process starts; nothing is
# fetched at request time. run.sh sets both of these when they are unset and we
# are not run through run.sh, so the worker sets them itself.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch  # noqa: E402

torch.set_grad_enabled(False)

# The kit's trigger, and the module that carries the model class. Importing it
# is what arms the kit on this process; constructing a model must come after.
from transformers.models.esmfold2.modeling_esmfold2 import (  # noqa: E402
    ESMFold2Model,
)
from esm.models.esmfold2.processor import ESMFold2InputBuilder  # noqa: E402
from esm.utils.structure.input_builder import (  # noqa: E402
    deserialize_structure_prediction_input,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} variant={VARIANT} mode={MODE}"
)

_t = time.time()
MODEL = ESMFold2Model.from_pretrained(HF_REPO[VARIANT]).to(DEVICE).eval()
BUILDER = ESMFold2InputBuilder()
BUILD_S = time.time() - _t
# Not a choice between the kit and us, as it is for Chai-1: this kit replaces no
# loader, so the worker holds the model under every mode. The kit word says
# which mode it is holding it for.
HOLDER = "worker"
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s (weights_held_by={HOLDER} kit={MODE})"
)

# ESMFold2InputBuilder.fold's own defaults, named rather than left implicit so
# a reply says what it folded at. STOCK.md "How stock is run" is the reference.
DEFAULTS = {
    "num_loops": 20,
    "num_sampling_steps": 200,
    "num_diffusion_samples": 1,
    "msa_max_depth": 1024,
}
# fold()'s optional overrides, passed through only when a caller names one.
PASSTHROUGH = tuple(DEFAULTS) + (
    "lm_dropout",
    "msa_column_mask_rate",
    "noise_scale",
    "step_scale",
    "max_inference_sigma",
    "lm_mask_pct",
    "early_exit",
)
# The kit's own file stem: <id>__<fast|full>__s<seed>_x<k>.cif (outputs.py).
SERVER_VARIANT = {"fast": "fast", "full_msa": "full", "full_nomsa": "full"}


def _items(text: str) -> list:
    """Upstream's prediction-input JSON: one input, or a list of them."""
    obj = json.loads(text)
    items = obj if isinstance(obj, list) else [obj]
    if not items:
        raise ValueError("the input JSON holds no prediction inputs")
    return items


def _spi(item: dict):
    """One input dict -> upstream's StructurePredictionInput.

    Upstream's own deserializer, not the kit's wrapper around it, so this reads
    the same under ``mode = "off"``. An ``msa`` naming an A3M file is only read
    by ``full_msa``; under the other variants upstream is given the chain
    without one, which is what that variant means.
    """
    data = {
        k: v for k, v in item.items() if k not in ("seeds", "num_diffusion_samples")
    }
    if VARIANT != "full_msa":
        data["sequences"] = [dict(ch, msa=None) for ch in data.get("sequences", [])]
    return deserialize_structure_prediction_input(data)


def _scalar(value):
    """A result attribute as JSON: a 0-d tensor becomes its number."""
    try:
        return value.item() if hasattr(value, "item") else value
    except Exception:  # noqa: BLE001 - a score we cannot read is not fatal
        return None


def _predict_one(req: dict) -> dict:
    """One pass over the request's inputs. The request carries the JSON text."""
    text = req.get("input") or req.get("json")
    if not text:
        raise ValueError(
            "a request needs 'input': upstream's prediction-input JSON "
            '({"sequences": [...]}, one input or a list)'
        )
    items = _items(text)
    out_dir = Path(req["out_dir"]) / (req.get("name") or "esmfold2")
    cif_dir = out_dir / "cif_all"
    cif_dir.mkdir(parents=True, exist_ok=True)
    opts = dict(req.get("options") or {})
    fold_kwargs = {**DEFAULTS, **{k: opts[k] for k in PASSTHROUGH if k in opts}}

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    files: list = []
    predictions: list = []
    t = time.time()
    for index, item in enumerate(items):
        item_id = str(item.get("id") or f"input_{index}")
        spi = _spi(item)
        seeds = item.get("seeds") or [req.get("seed", 0)]
        samples = int(
            item.get("num_diffusion_samples") or fold_kwargs["num_diffusion_samples"]
        )
        for seed in seeds:
            seed = None if seed is None else int(seed)
            result = BUILDER.fold(
                MODEL,
                spi,
                seed=seed,
                complex_id=item_id,
                **{**fold_kwargs, "num_diffusion_samples": samples},
            )
            for k, one in enumerate(result if isinstance(result, list) else [result]):
                stem = (
                    f"{item_id}__{SERVER_VARIANT[VARIANT]}"
                    f"__s{'none' if seed is None else seed}_x{k}"
                )
                cif = cif_dir / f"{stem}.cif"
                cif.write_text(one.complex.to_mmcif())
                files.append(str(cif))
                predictions.append(
                    {
                        "id": item_id,
                        "seed": seed,
                        "sample": k,
                        "cif": str(cif),
                        "ptm": _scalar(getattr(one, "ptm", None)),
                        "iptm": _scalar(getattr(one, "iptm", None)),
                    }
                )
    if DEVICE == "cuda":
        torch.cuda.synchronize()

    body = {
        "out_dir": str(out_dir),
        "files": files,
        "predictions": predictions,
        "variant": VARIANT,
        "timing": {"fold_s": round(time.time() - t, 2)},
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
    }
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "variant": VARIANT,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
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
