"""RFdiffusion3 held resident on the GPU, answering one design request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    RFDIFFUSION3_OPT=fast <model python> rfdiffusion3_resident_worker.py --socket … --slug …

The kit engages through its own ``.pth`` -- the common form, 30 of the 36 kits
-- so this file is simply a script the model's interpreter runs. The variable's
name is read from the kit by ``kit_launch``'s probe (``_autoload.ENV``; this
kit has no ``modes.ENV``), never guessed here.

**The shape of a design request, which is not the shape of a prediction.**

The three providers before this one predict: one input, one answer. This one
generates, and it generates N backbones from a specification, where N is
something the caller asks for rather than something the input has. Upstream
splits that N across two knobs and -- this is the part a resident worker has to
get right -- the two live at different times:

* ``n_batches`` is an argument of ``RFD3InferenceEngine.run`` (engine.py:273),
  so it is free to vary per request: it multiplies the specification into that
  many independent roll-outs.
* ``diffusion_batch_size`` and every ``inference_sampler.*`` setting are
  arguments of the engine's **constructor**. They are merged into the
  checkpoint's config at ``initialize()`` (base.py, ``self.overrides``) and are
  fixed for the life of the built model.

So a held worker answers ``n_batches``, ``seed``, the specification and the
output directory for free, and a request that names a different
``diffusion_batch_size`` or sampler setting is a request for a **different
model build**. This worker treats that honestly: it keys the built engine on
those settings, holds exactly one, and rebuilds -- once, visibly, on the ready
line and in the reply -- when a request asks for another key. Silently ignoring
the request would be the dangerous kind of wrong, and refusing it would make a
legitimate parameter unreachable.

**Who holds the weights.** Chai-1 had to decide: its upstream reloads its
modules inside every call, and under a kit mode the kit replaces that loader
and refuses to activate if anything else replaced it first. Neither half of
that applies here, and the reason is worth stating because it is a third
answer rather than one of Chai-1's two:

* Upstream already memoises. ``BaseInferenceEngine.initialize`` returns early on
  ``self.initialized_``, so the 2.7 GB checkpoint is read once per engine and
  ``engine.run`` reuses the built model.
* The kit replaces no loader at all. ``rfdiffusion3_opt`` is a **file overlay**
  on ``site-packages/rfd3/model/`` plus seven environment switches read at the
  import of the patched modules; there is no function of upstream's that it
  wraps at run time and none for this worker to race it for.

So there is nothing to memoise here and nothing to leave alone: the engine is
the holder under every mode, and the ready line says ``weights_held_by=engine``
with the mode that is driving it.

**Each request gets its own output directory**, and that is not tidiness. With
``skip_existing`` on, ``_multiply_specifications`` looks at what is already in
``out_dir`` and drops the designs it finds -- and a run in which every design
was skipped initialises nothing, which the kit then reports as
``KERNELS refused … engine-never-initialized`` and exits 5 (the kit's README
says so in as many words). The worker therefore gives each request a fresh
directory and builds the engine with ``skip_existing=False``.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="rfdiffusion3", help="provider slug, echoed in ping")
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
    print(f"[rfdiffusion3-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds RFdiffusion3's pinned
    stack and nothing of ToolUniverse, and importing the package would defeat
    that."""
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
            f"[rfdiffusion3-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import torch  # noqa: E402

torch.set_grad_enabled(False)

# The kit's trigger is the first import of `rfd3`; its finder lets that
# package's own body run and then activates the mode. Importing the engine here
# is what arms and fires it, before any model is built.
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine  # noqa: E402

MODE = (os.environ.get("RFDIFFUSION3_OPT") or "off").strip().lower() or "off"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} device={DEVICE}")


def _checkpoint() -> str:
    """The checkpoint file, from what setup verified -- never fetched here.

    ``RFD3_CKPT`` is the kit's own name for the file. Failing that, the
    manifest's weights root is in the environment under upstream's own variable
    and the pinned file name is upstream's registry entry's.
    """
    named = (os.environ.get("RFD3_CKPT") or "").strip()
    if named:
        return named
    roots = [
        p
        for p in (os.environ.get("FOUNDRY_CHECKPOINT_DIRS") or "").split(os.pathsep)
        if p.strip()
    ]
    roots.append(os.path.expanduser("~/.foundry/checkpoints"))
    for root in roots:
        candidate = Path(root).expanduser() / "rfd3_latest.ckpt"
        if candidate.is_file():
            return os.fspath(candidate)
    raise _refuse(
        "[rfdiffusion3-resident] no checkpoint: set RFD3_CKPT, or run "
        "`tu remote setup rfdiffusion3 --only weights`"
    )


CKPT = _checkpoint()

# What the engine is built with, and therefore what a request cannot change
# without a rebuild. `diffusion_batch_size` is one because one design per
# roll-out is the unit a caller composes -- asking for more is `n_batches`,
# which is request-time and free. Everything under `inference_sampler` is
# upstream's own default at this pin (rfd3/configs/inference_engine/
# rfdiffusion3.yaml) and is left to upstream rather than restated.
BUILD_DEFAULTS = {"diffusion_batch_size": 1, "inference_sampler": {}}
# Request-time, passed straight to `engine.run`.
RUN_KEYS = ("n_batches",)
_ENGINE: dict = {"key": None, "engine": None, "build_s": None, "builds": 0}


def _build_key(opts: dict) -> dict:
    key = {
        "diffusion_batch_size": int(
            opts.get("diffusion_batch_size", BUILD_DEFAULTS["diffusion_batch_size"])
        ),
        "inference_sampler": dict(
            opts.get("inference_sampler", BUILD_DEFAULTS["inference_sampler"]) or {}
        ),
    }
    if key["diffusion_batch_size"] < 1:
        raise ValueError("diffusion_batch_size must be at least 1")
    return key


def _engine_for(key: dict):
    """The held engine, built for ``key``; rebuilt only when the key changes.

    One at a time, deliberately: two engines on one card would hold two copies
    of the network, and the supervisor already serialises requests, so there is
    never a second caller waiting on the one being dropped.
    """
    if _ENGINE["engine"] is not None and _ENGINE["key"] == key:
        return _ENGINE["engine"]
    if _ENGINE["engine"] is not None:
        say(
            f"rebuilding: the request's build key {key} is not the held {_ENGINE['key']}"
        )
        _ENGINE["engine"] = None
        # Dropping the reference is not enough to give the card back: the
        # network is reachable from the trainer's state until the collector
        # runs, and the caching allocator keeps the blocks until it is told to
        # release them.
        gc.collect()
        if DEVICE == "cuda":
            torch.cuda.empty_cache()
    t = time.time()
    cfg = RFD3InferenceConfig(
        ckpt_path=CKPT,
        diffusion_batch_size=key["diffusion_batch_size"],
        inference_sampler=dict(key["inference_sampler"]),
        # Each request has its own output directory, so nothing is ever there
        # to skip -- and a run in which everything was skipped initialises no
        # model, which the kit reports as engine-never-initialized and exits 5.
        skip_existing=False,
        # Seeded per request instead (see _design_one): the constructor's seed
        # is applied once, at construction, and would then be the same for
        # every design this engine ever makes.
        seed=None,
        verbose=False,
        # The kit compiles upstream's four compile targets itself under `fast`,
        # and refuses a line that asks upstream to do it as well.
        compile_model=False,
    )
    engine = RFD3InferenceEngine(**cfg)
    engine.initialize()
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    _ENGINE.update(
        {
            "key": key,
            "engine": engine,
            "build_s": round(time.time() - t, 1),
            "builds": _ENGINE["builds"] + 1,
        }
    )
    say(f"engine built in {_ENGINE['build_s']}s key={key} ckpt={CKPT}")
    return engine


def _read_request(text: str) -> tuple:
    """``(specification, options)`` from one request document.

    Two readings, because a design request carries more than a specification.
    Upstream's own file is a mapping of design name to specification, and that
    is accepted unchanged, so anything the kit's `inputs=` takes works here.
    But how many backbones to make, and how hard, are not specification fields
    -- upstream forbids extra keys there -- so the envelope form carries them
    beside it::

        {"specification": {<name>: {...}, ...}, "options": {...}}

    A document with a top-level ``specification`` key is read as the envelope;
    anything else is read as upstream's own mapping. Top-level keys beginning
    with ``_`` are ignored, so a document can carry a comment.
    """
    doc = json.loads(text)
    if not isinstance(doc, dict):
        raise ValueError("a design request is a JSON object, not " + type(doc).__name__)
    doc = {k: v for k, v in doc.items() if not str(k).startswith("_")}
    if "specification" in doc:
        spec = doc["specification"]
        opts = doc.get("options") or {}
        unknown = sorted(set(doc) - {"specification", "options"})
        if unknown:
            raise ValueError(
                f"unknown key(s) {unknown} beside 'specification'; the envelope "
                f"takes 'specification' and 'options'"
            )
    else:
        spec, opts = doc, {}
    if not isinstance(spec, dict) or not spec:
        raise ValueError(
            "the specification is a non-empty mapping of design name to "
            "RFdiffusion3 design specification"
        )
    if not isinstance(opts, dict):
        raise ValueError("'options' is a mapping")
    return spec, opts


def _design_one(req: dict) -> dict:
    """One design request: one specification, N backbones, one directory."""
    text = req.get("input") or req.get("specification")
    if not text:
        raise ValueError(
            "a request needs 'input': the text of an RFdiffusion3 design "
            "specification (upstream's own inputs= JSON, or the envelope form)"
        )
    if isinstance(text, (dict, list)):
        text = json.dumps(text)
    spec, file_opts = _read_request(text)
    # The request's own options win over the document's: the document is the
    # design, the request is the call.
    opts = {**file_opts, **(req.get("options") or {})}

    name = req.get("name") or "design"
    item = Path(req["out_dir"]) / name
    item.mkdir(parents=True, exist_ok=True)
    # A fresh directory per request. Upstream skips designs it finds already
    # written, and a run that skips everything builds nothing.
    stamp = f"{int(time.time() * 1000):013d}"
    out_dir = item / f"designs-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    # Relative `input:` paths in a specification are resolved against the
    # specification file's own directory (engine.ensure_input_is_abspath), so
    # the file goes beside the outputs the caller named.
    spec_path = item / f"{name}.json"
    spec_path.write_text(json.dumps(spec, indent=2) + "\n")

    run_args = {k: opts[k] for k in RUN_KEYS if k in opts}
    n_batches = int(run_args.get("n_batches", 1))
    if n_batches < 1:
        raise ValueError("n_batches must be at least 1")
    run_args["n_batches"] = n_batches
    unknown = sorted(
        set(opts) - set(RUN_KEYS) - {"diffusion_batch_size", "inference_sampler"}
    )
    if unknown:
        raise ValueError(
            f"unknown option(s) {unknown}; this provider takes {sorted(RUN_KEYS)} "
            f"per request and ['diffusion_batch_size', 'inference_sampler'] as "
            f"the engine's build key"
        )

    key = _build_key(opts)
    builds_before = _ENGINE["builds"]
    engine = _engine_for(key)

    # Upstream applies the constructor's seed once, at construction. A held
    # engine therefore has to be seeded per request, or every request would
    # draw the same noise.
    seed = int(req.get("seed", 0))
    from lightning.fabric import seed_everything

    seed_everything(seed, workers=True, verbose=False)
    engine.seed = seed

    timing = {}
    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()
    engine.run(inputs=os.fspath(spec_path), out_dir=os.fspath(out_dir), **run_args)
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    timing["design_s"] = round(time.time() - t, 2)

    designs = []
    for cif in sorted(out_dir.glob("*.cif.gz")):
        entry = {
            "example_id": cif.name[: -len(".cif.gz")],
            "structure": os.fspath(cif),
        }
        meta = cif.with_suffix("").with_suffix(".json")
        if meta.is_file():
            entry["metadata_file"] = os.fspath(meta)
            try:
                loaded = json.loads(meta.read_text())
            except ValueError:
                loaded = {}
            # The per-design metrics are what a caller ranks N backbones on;
            # they are the point of returning anything but a list of paths.
            for field in ("metrics", "sequence", "task", "seed"):
                if field in loaded:
                    entry[field] = loaded[field]
        designs.append(entry)
    if designs:
        timing["per_design_s"] = round(timing["design_s"] / len(designs), 2)

    body = {
        "out_dir": os.fspath(out_dir),
        "specification_file": os.fspath(spec_path),
        "designs": designs,
        "n_designs": len(designs),
        "n_batches": n_batches,
        "diffusion_batch_size": key["diffusion_batch_size"],
        "seed": seed,
        "files": sorted(os.fspath(p) for p in out_dir.rglob("*") if p.is_file()),
        "timing": timing,
        "mode": MODE,
        "weights_held_by": f"engine:{MODE}",
        "engine_rebuilt": _ENGINE["builds"] != builds_before,
    }
    if not designs:
        # Nothing was written, and the likeliest reason is upstream skipping
        # work it thought was already done -- which also leaves the kit with no
        # initialised engine to report on.
        body["warning"] = (
            "no design was written; check the worker log for upstream's own "
            "lines and the kit's KERNELS line"
        )
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": DEVICE,
        "mode": MODE,
        "weights_held_by": f"engine:{MODE}",
        "checkpoint": CKPT,
        "engine_key": _ENGINE["key"],
        "engine_build_s": _ENGINE["build_s"],
    }


if __name__ == "__main__":
    # Built here rather than on the first request: the checkpoint is 2.7 GB and
    # under `fast` the process also pays torch.compile's trace, and
    # [runtime] start_timeout_s is what covers that. A request then finds a
    # model already on the card.
    _engine_for(_build_key({}))
    say(
        f"ready t={time.time() - T0:.1f}s mode={MODE} weights_held_by=engine:{MODE} "
        f"(the kit is a file overlay and replaces no loader; upstream's own "
        f"initialize() memoises the build, so nothing is memoised here)"
    )
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_design_one,
            ready=_ready,
            log=say,
        )
    )
