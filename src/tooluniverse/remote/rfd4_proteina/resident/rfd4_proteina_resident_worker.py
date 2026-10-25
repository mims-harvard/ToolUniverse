"""RFD4-Proteina, held resident.

THE FIRST PROVIDER ON THIS STANDARD THAT WRAPS NO OPTIMIZATION KIT. The
thirty-one before it all wrap a kit from ``anthropics/uplifting-biomolecular-
modeling``, and most of what their workers do is arm one: import the package
whose finder the kit has hooked, read the mode variable the kit named, report
the row the probe will compare against. There is no such kit for RFD4-Proteina.
Upstream ships the inference runtime itself -- ``rfd4-proteina`` on PyPI, a
``py3-none-any`` wheel over binary dependencies that all have aarch64 builds --
and the levers a kit would add are already configuration here: a compiled
native backend and NVIDIA's BioIR runtime with CUDA graph capture, both
selected in ``configs/inference.yaml``.

So this worker is the plain shape the standard describes with nothing in
between it and upstream: load the matched pair once, serve designs off it, and
let the per-process costs accrue to the process rather than to each request.

WHAT RESIDENCY COLLECTS HERE IS NOT THE WEIGHTS. They are 1.74 GB + 1.03 GB and
``Proteina.from_pretrained`` returns in about 2 s from a warm Hub cache -- so
the usual argument, that a held worker saves a long load, is the weakest one
available for this model. What it actually collects is everything the first
request defers and every later one skips: measured on an NVIDIA GB10, an
unconditional 100-mer with compilation disabled runs 44.9 s on the first
request of a process and 20.9-24.1 s on the three after it. The ratio comes
from warm-up, not from loading, and a worker that exits cannot collect it.
provider.toml records the compiled and graph-captured configurations, where the
per-process cost -- and so the gap -- is larger.

ONE REQUEST AT A TIME, which the shared serve loop enforces, and which matters
more here than for a predictor: ``num_replicates`` makes one request an
arbitrary amount of work, so two in one CUDA context would interleave
allocations whose peak is attributable to neither.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="rfd4_proteina", help="provider slug, echoed in ping")
args = ap.parse_args()

T0 = time.time()

MAX_REPLICATES = 16
MAX_INPUT_BYTES = 8 * 1024 * 1024
RECYCLE_STRATEGIES = ("thinking_low", "thinking_medium", "thinking_high")
BACKENDS = ("native", "bioir")


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    ``raise SystemExit("text")`` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[rfd4_proteina-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds RFD4's pinned stack and
    nothing of ToolUniverse, and importing the package would defeat that."""
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
            f"[rfd4_proteina-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import torch  # noqa: E402

torch.set_grad_enabled(False)

# Imported here, not inside the request: hydra's config directory is resolved
# from the installed package and a failure to find it is a start-up refusal,
# not a failed design.
import rootutils  # noqa: E402
import rfproteina  # noqa: E402
from hydra import compose, initialize_config_dir  # noqa: E402
from rfproteina.generate import run_generation  # noqa: E402
from rfproteina.proteina import Proteina  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# The Hub pin. A flow model and the autoencoder it was trained against are a
# MATCHED PAIR -- upstream is explicit that mixing one release's flow model
# with another's autoencoder "produces nonsense rather than an error", because
# the autoencoder defines the latent space the flow model generates in. So the
# revision is pinned here and in provider.toml, and neither moves alone.
HF_REPO = os.environ.get("RFD4_PROTEINA_HF_REPO", "nvidia/RFD4-Proteina")
HF_REVISION = os.environ.get(
    "RFD4_PROTEINA_HF_REVISION", "a06e2509c7033b010fc43614e9fd840303588502"
)

_CONFIG_DIR = (
    rootutils.find_root(rfproteina.__file__, indicator=".project-root") / "configs"
)

_MODEL = {"obj": None, "load_s": None}


def _model():
    if _MODEL["obj"] is None:
        t = time.time()
        _MODEL["obj"] = Proteina.from_pretrained(HF_REPO, revision=HF_REVISION)
        _MODEL["load_s"] = round(time.time() - t, 2)
    return _MODEL["obj"]


def _str_field(req: dict, name: str, allowed: tuple, default: str) -> str:
    value = req.get(name, default)
    if value is None:
        return default
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"'{name}' must be one of {', '.join(allowed)}")
    return value


def _sequences(path: Path) -> dict:
    """Read a design back. Biotite is in the model's environment already --
    upstream depends on it -- so nothing is added to the stack for this."""
    from biotite.sequence import ProteinSequence
    from biotite.structure.io.pdbx import CIFFile, get_structure
    import biotite.structure as struc

    opener = __import__("gzip").open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        cif = CIFFile.read(handle)
    atoms = get_structure(cif, model=1)
    chains = {}
    for chain_id in sorted(set(atoms.chain_id)):
        residues = struc.get_residues(atoms[atoms.chain_id == chain_id])[1]
        letters = []
        for name in residues:
            try:
                letters.append(ProteinSequence.convert_letter_3to1(name))
            except KeyError:
                # A non-standard component: the unified autoencoder covers
                # nucleic acids and small molecules, so this is expected rather
                # than an error, and the chain is reported with its gap.
                letters.append("X")
        chains[str(chain_id)] = "".join(letters)
    return {"chains": chains, "n_atoms": int(atoms.array_length())}


def _design_one(req: dict) -> dict:
    """Serve one design request off the held model."""
    # ``input`` is the shared name: the setup smoke step sends the declared
    # smoke file's text under it and knows nothing provider-specific, so a
    # worker that invented its own field name would be unsmokeable. Here that
    # text is the annotated mmCIF itself rather than a JSON envelope, because
    # the specification already has a file format and wrapping it would mean
    # the smoke exercised a reading no caller uses.
    input_cif = req.get("input") or req.get("input_cif")
    if not isinstance(input_cif, str) or not input_cif.strip():
        raise ValueError(
            "'input' must be the text of an annotated mmCIF. The design "
            "conditions live inside the file; an ordinary unannotated "
            "structure is not a design specification."
        )
    if len(input_cif.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError(
            f"'input_cif' is larger than {MAX_INPUT_BYTES} bytes; upstream's "
            f"own published examples run 3 KB to 725 KB"
        )

    replicates = req.get("num_replicates", 1)
    if not isinstance(replicates, int) or isinstance(replicates, bool):
        raise ValueError("'num_replicates' must be an integer")
    if not 1 <= replicates <= MAX_REPLICATES:
        raise ValueError(f"'num_replicates' must be between 1 and {MAX_REPLICATES}")

    recycle = _str_field(req, "recycle_strategy", RECYCLE_STRATEGIES, "thinking_medium")
    backend = _str_field(req, "inference_backend", BACKENDS, "native")

    seed = req.get("seed")
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError("'seed' must be an integer or null")

    return_structures = bool(req.get("return_structures", False))

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()

    model = _model()
    # The caller's directory when it names one, and the setup smoke step always
    # does: its outputs assertion walks exactly that tree, so a worker writing
    # into a temporary directory of its own would leave it empty and the
    # assertion would report a provider that produced nothing.
    requested_out = req.get("out_dir")
    work = Path(tempfile.mkdtemp(prefix="rfd4-"))
    owns_out = requested_out is None
    try:
        source = work / "input.cif"
        source.write_text(input_cif)
        out_dir = work / "out" if owns_out else Path(requested_out)
        out_dir.mkdir(parents=True, exist_ok=True)

        overrides = [
            f"inputs={source}",
            f"out_dir={out_dir}",
            f"num_replicates={replicates}",
            f"recycle_strategy={recycle}",
            f"inference_backend={backend}",
            "~metrics",
        ]
        if seed is not None:
            overrides.append(f"seed={seed}")

        t = time.time()
        with initialize_config_dir(config_dir=str(_CONFIG_DIR), version_base="1.3"):
            cfg = compose(config_name="inference", overrides=overrides)
        run_generation(cfg, model=model)
        elapsed = time.time() - t

        produced = sorted((out_dir).rglob("*_generated.cif*"))
        if not produced:
            raise RuntimeError(
                "upstream wrote no design; read the worker log for its own "
                "lines. An input that is a structure but carries no design "
                "annotation is the common cause."
            )

        designs = []
        for path in produced:
            entry = {"design_id": path.stem.replace("_generated", "")}
            entry.update(_sequences(path))
            if return_structures:
                entry["cif"] = path.read_text() if path.suffix != ".gz" else None
            designs.append(entry)

        body = {
            "model": f"{HF_REPO}@{HF_REVISION[:12]}",
            "n_designs": len(designs),
            "designs": designs,
            "recycle_strategy": recycle,
            "inference_backend": backend,
            "seed": seed,
            "timing": {"generate_s": round(elapsed, 2)},
            "weights_held_by": "worker:Proteina",
        }
        if not return_structures:
            body["structures_note"] = (
                "sequences only; pass return_structures=true for the mmCIF text"
            )
        if DEVICE == "cuda":
            body["peak_reserved_gib"] = round(
                torch.cuda.max_memory_reserved() / 2**30, 2
            )
        return body
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": DEVICE,
        "model": f"{HF_REPO}@{HF_REVISION[:12]}",
        "model_load_s": _MODEL["load_s"],
        "weights_held_by": "worker:Proteina",
        "kit": None,
    }


if __name__ == "__main__":
    # Loaded here rather than on the first request. It is only ~2 s, so this is
    # not the usual "spare the first caller a long load" argument -- it is that
    # a checkpoint that cannot be fetched or does not match its pin should
    # refuse at start, where the host is watching, and not in the middle of
    # someone's design.
    _model()
    say(
        f"ready t={time.time() - T0:.1f}s device={DEVICE} "
        f"model={HF_REPO}@{HF_REVISION[:12]} load={_MODEL['load_s']}s "
        f"(no optimization kit: upstream ships the runtime, and the levers are "
        f"inference_backend and compile_lengths in its own config)"
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
