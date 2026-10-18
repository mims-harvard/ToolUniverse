"""Chai-1 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    CHAI1_OPT=fast <model python> chai1_resident_worker.py --socket … --slug …

Why holding matters more here than for the other providers. ``chai_lab``'s
``load_exported`` is not memoised, and ``run_folding_on_context`` calls it six
times per fold -- the feature embedder, the bond projection, the token
embedder, the trunk, the diffusion module and the confidence head -- on top of
a 5.4 GB traced ESM. A process that exits after each request re-reads all of it
every time. Residency is not a refinement for this model; it is the difference
between a usable provider and one that spends most of every request on disk.

Who does the holding depends on the mode, and the worker must not get this
wrong. Under a kit mode the kit replaces ``chai1.load_exported`` with its own
loader and **refuses to activate if anything else replaced it first**
(``chai1_opt/stack.py``), so memoising it here would silently turn the kit off.
Under ``mode = "off"`` nothing replaces it and this worker memoises it itself.
Either way the modules are loaded once; the difference is whose loader holds
them, and :func:`_arrange_resident_weights` says which on the ready line.
"""

from __future__ import annotations

import argparse
import functools
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="chai1", help="provider slug, echoed in ping")
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
    print(f"[chai1-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds chai_lab's pinned stack
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
            f"[chai1-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import torch  # noqa: E402

torch.set_grad_enabled(False)

from chai_lab import chai1 as _chai1  # noqa: E402  <- the kit's trigger module

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")


def _arrange_resident_weights() -> str:
    """Make the six modules load once, without fighting the kit for the job.

    Returns the word that says who is holding them, for the ready line.
    """
    mode = (os.environ.get("CHAI1_OPT") or "").strip().lower()
    if mode and mode != "off":
        # The kit owns the loader under any of its modes. Touching it here
        # would make the kit refuse to activate, which is a silent loss of
        # every lever rather than a visible failure.
        return f"kit:{mode}"
    _chai1.load_exported = functools.lru_cache(maxsize=None)(_chai1.load_exported)
    return "worker"


HOLDER = _arrange_resident_weights()
say(f"weights held by: {HOLDER}")

DEFAULTS = {
    "num_trunk_recycles": 3,
    "num_diffn_timesteps": 200,
    "num_diffn_samples": 5,
    "num_trunk_samples": 1,
    "use_esm_embeddings": True,
    "use_msa_server": False,
    "low_memory": True,
}
PASSTHROUGH = tuple(DEFAULTS) + ("msa_server_url", "recycle_msa_subsample")
BUILD_S = time.time() - T0


def _predict_one(req: dict) -> dict:
    """One fold. The request carries the FASTA text; chai_lab wants a file."""
    fasta = req.get("input") or req.get("fasta")
    if not fasta:
        raise ValueError("a request needs 'input' (or 'fasta'): a chai-lab FASTA")
    out_root = Path(req["out_dir"])
    name = req.get("name") or "input"
    opts = dict(req.get("options") or {})

    item = out_root / name
    item.mkdir(parents=True, exist_ok=True)
    fasta_path = item / f"{name}.fasta"
    fasta_path.write_text(fasta if fasta.endswith("\n") else fasta + "\n")
    # run_inference asserts the output directory is empty, so give each fold
    # its own rather than making the caller clean up between requests.
    out_dir = item / "predictions"
    if out_dir.exists():
        for stale in sorted(out_dir.rglob("*"), reverse=True):
            stale.unlink() if stale.is_file() else stale.rmdir()
        out_dir.rmdir()

    fold = {k: opts[k] for k in PASSTHROUGH if k in opts}
    timing = {}
    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()

    t = time.time()
    candidates = _chai1.run_inference(
        fasta_file=fasta_path,
        output_dir=out_dir,
        seed=int(req.get("seed", 0)),
        device=DEVICE,
        **{**DEFAULTS, **fold},
    )
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    timing["fold_s"] = round(time.time() - t, 2)

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    body = {
        "out_dir": str(out_dir),
        "files": files,
        "timing": timing,
        "weights_held_by": HOLDER,
    }
    # The ranking scores are what a caller compares folds on; they are the
    # point of returning anything but a path.
    for attr in ("aggregate_score", "ptm", "iptm"):
        value = getattr(candidates, attr, None)
        if value is not None:
            try:
                body[attr] = [float(v) for v in value.flatten()]
            except Exception:  # noqa: BLE001 - a score we cannot read is not fatal
                pass
    if DEVICE == "cuda":
        # The kit captures a CUDA graph per fold and warms it up on a fresh
        # side stream (chai1_eager/hoist.py step_graphed), which leaves torch
        # holding a 32 MiB cuBLAS workspace for a stream nothing will use
        # again -- 0.039 GiB a fold forever, the whole declared budget in
        # about 140 folds. `WB.serve` gives those back after every request
        # now, for every provider, and puts the figure in
        # `cublas_workspaces_freed_mib`; this worker used to do it on its own
        # last line. See `release_cublas_workspaces` for why it is safe to do
        # for everybody.
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {"build_s": round(BUILD_S, 1), "device": DEVICE, "weights_held_by": HOLDER}


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
