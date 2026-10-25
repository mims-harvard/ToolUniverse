"""BioEmu-2, held resident.

THE SECOND PROVIDER ON THIS STANDARD THAT WRAPS NO OPTIMIZATION KIT, and the
first whose residency argument is carried by the model load rather than by
warm-up. Upstream publishes the inference runtime itself -- ``bioemu2`` on
PyPI, a ``py3-none-any`` wheel over binaries that all have aarch64 builds --
so there is no ``anthropics/uplifting-biomolecular-modeling`` checkout to arm,
no mode variable to read, and no ``[kit]`` table in the manifest.

WHAT RESIDENCY COLLECTS HERE, MEASURED ON THE VERIFIED CARD. ``load_model()``
took **49.9 s** and left 1.92 GiB resident before any request. A second
identical request in the same process ran 27.3 s against 35.6 s for the first.
So the held model saves roughly 50 s per request that a per-request process
would pay, plus about 8 s of CUDA warm-up -- the opposite balance from
RFD4-Proteina, where the load was 2-17 s and warm-up was everything.

THE THIRD SAVING IS THE ONE THIS WORKER HAS TO BUILD ITSELF. Upstream's cost
model says the trunk runs **once per system** at ``O(RN^2 + N^3)`` and that
above roughly 600 tokens embedding one sequence costs more than denoising one
sample. An ``EmuSession`` holds those embeddings, so repeating a request for
the same system with the same MSA and mode should skip the trunk entirely.
``_SESSION_CACHE`` below keeps exactly **one** of them, because the pair
representations are ``O(N^2)`` of GPU memory and a cache of several would put
the footprint somewhere the declared budget does not cover.

NOTE THAT THE DEFAULT MSA PATH LEAVES THIS MACHINE. With no ``msa`` block in
the request, upstream queries the **public ColabFold server** on a cache miss.
That is an external service, it is rate-limited by courtesy rather than by
contract, and upstream asks callers to query serially from one IP -- which the
one-request-at-a-time serve loop happens to guarantee. A request that must not
touch the network has to carry its own ``msa``; see the provider README.

ONE REQUEST AT A TIME, enforced by the shared serve loop. ``num_samples`` makes
one request an arbitrary amount of work and the denoiser's peak is
``O(N^2 + BN)``, so two in one CUDA context would interleave allocations whose
peak is attributable to neither.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="bioemu2", help="provider slug, echoed in ping")
ap.add_argument(
    "--max-samples", type=int, default=16, help="ceiling on num_samples per request"
)
ap.add_argument(
    "--max-tokens",
    type=int,
    default=448,
    help="ceiling on BioEmu-2 tokens; the VRAM budget was measured just under it",
)
args = ap.parse_args()

T0 = time.time()

MAX_INPUT_BYTES = 4 * 1024 * 1024
MODES = ("structure", "equilibrium")
PHYSICALITY_MODES = (
    "no_filter",
    "no_violations",
    "high_quality",
    "high_quality_per_residue",
)


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    ``raise SystemExit("text")`` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def say(msg: str) -> None:
    print(f"[bioemu2-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds BioEmu-2's pinned stack
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
            f"[bioemu2-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

import torch  # noqa: E402

torch.set_grad_enabled(False)

# Imported at start, not inside a request: a missing or mismatched dependency
# is a start-up refusal the host is watching for, not a failed sample. The
# hydra `instantiate()` that load_model() performs is also why the checkpoint
# revision is pinned -- upstream's own warning is that a config-controlled
# `_target_` can execute arbitrary code.
import yaml  # noqa: E402
from bioemu2 import (  # noqa: E402
    EmuSession,
    MSA,
    System,
    check_physicality,
    load_model,
    save_frames,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

CHECKPOINT = os.environ.get("BIOEMU2_CHECKPOINT", "bioemu2-preview")

_MODEL = {"obj": None, "load_s": None}

# Exactly one held EmuSession, keyed by what determines its trunk embeddings.
# See the module docstring for why one and not several.
_SESSION_CACHE: dict = {"key": None, "session": None, "system": None}


def _model():
    if _MODEL["obj"] is None:
        t = time.time()
        # bf16-mixed for the trunk is upstream's own default for load_model();
        # denoising always runs in float32 regardless.
        _MODEL["obj"] = load_model(
            checkpoint=CHECKPOINT, device=DEVICE, precision="bf16-mixed"
        )
        _MODEL["load_s"] = round(time.time() - t, 2)
    return _MODEL["obj"]


def _request_document(req: dict) -> dict:
    """Parse the one text field every caller sends into a request document.

    ``input`` is the shared name: ``tu remote setup``'s smoke step sends the
    declared smoke file's text under it and knows nothing provider-specific, so
    a worker that invented its own field name would be unsmokeable. Here that
    text is YAML, and its ``system:`` block is upstream's own system YAML
    unchanged -- which is what lets a caller paste a ``system.to_yaml()`` file
    straight in, and what keeps the provider's own keys visibly outside it.
    """
    text = req.get("input")
    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "'input' must be the text of a BioEmu-2 request document: a YAML "
            "mapping with a 'system:' block holding upstream's entities, plus "
            "optional 'mode', 'num_samples' and 'msa' keys."
        )
    if len(text.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError(
            f"'input' is larger than {MAX_INPUT_BYTES} bytes; an MSA that "
            f"large belongs in a file the worker can read, not in a request"
        )
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"'input' is not valid YAML: {exc}") from None
    if not isinstance(doc, dict):
        raise ValueError(
            "'input' must parse to a YAML mapping, not "
            f"{type(doc).__name__}. The top level carries 'system:'."
        )
    if "system" not in doc:
        hint = (
            " It looks like a bare system definition: nest it under 'system:'."
            if "entities" in doc
            else ""
        )
        raise ValueError(f"'input' has no 'system:' block.{hint}")
    return doc


def _build_system(block) -> "System":
    if isinstance(block, str):
        # The MCP tool's 'system_yaml' branch passes upstream's system YAML
        # through as text rather than parsing it, so that this worker -- which
        # holds BioEmu-2's own validation -- is the only thing that reads it.
        try:
            block = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            raise ValueError(f"'system' is not valid YAML: {exc}") from None
    if not isinstance(block, dict):
        raise ValueError("'system' must be a mapping with an 'entities' list")
    try:
        return System.model_validate(block)
    except Exception as exc:  # noqa: BLE001 — upstream's own validation message
        raise ValueError(f"'system' is not a valid BioEmu-2 system: {exc}") from None


def _count_tokens(system) -> int:
    """N, counted the way upstream counts it, by building the structure.

    THE OBVIOUS SHORTCUT IS WRONG IN THE DANGEROUS DIRECTION. Summing
    ``len(entity.sequence)`` over chains looks like N and is a floor on it:
    a ligand's atoms are tokens and contribute nothing to that sum, and even
    an all-polymer entry can carry more. Measured against
    ``AllAtomStructure.num_tokens`` on the three systems this provider's VRAM
    envelope was taken on: 1UBQ 76 against 76, 1AKE **271 against 214**, 6LU7
    **676 against 624**. A ceiling checked against the floor would admit a
    system a fifth larger than the one the budget was measured at, which is
    exactly how a declared budget gets oversold.

    Building the structure is CPU work on composition only -- no model, no
    MSA, no GPU -- so it is cheap enough to do before admitting the request.
    """
    from bioemu2.data_interface.system import AllAtomStructure

    return int(AllAtomStructure.from_system(system).num_tokens)


def _build_msa(block, system):
    """A caller-supplied alignment, or None to let upstream fetch one.

    Returning None is NOT the cheap path: it reaches the public ColabFold
    server on a cache miss. It is the default because it is upstream's, and
    because a single-sequence alignment silently degrades the model rather
    than failing.
    """
    if block is None:
        return None
    if isinstance(block, str):
        chain_ids = list(system.chain_ids)
        if len(chain_ids) != 1:
            raise ValueError(
                f"'msa' given as one A3M string, but the system has "
                f"{len(chain_ids)} chains; pass a mapping of chain id to A3M"
            )
        block = {chain_ids[0]: block}
    if not isinstance(block, dict):
        raise ValueError("'msa' must be an A3M string or a chain-id to A3M mapping")
    for chain_id, a3m in block.items():
        if not isinstance(a3m, str) or not a3m.lstrip().startswith(">"):
            raise ValueError(
                f"'msa[{chain_id}]' must be A3M text whose first record is the "
                f"query sequence for that chain"
            )
    try:
        return MSA(block)
    except Exception as exc:  # noqa: BLE001 — upstream validates query match
        raise ValueError(f"'msa' was rejected by BioEmu-2: {exc}") from None


def _int_field(doc: dict, name: str, default: int, low: int, high: int) -> int:
    value = doc.get(name, default)
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"'{name}' must be an integer")
    if not low <= value <= high:
        raise ValueError(f"'{name}' must be between {low} and {high}")
    return value


def _session(system, msa, mode: str):
    """The held session for this system, built only when the key changes.

    The key is everything that determines the trunk embeddings. ``repr`` of the
    validated system is stable within a process, which is all this needs: a
    false miss costs one trunk run, and there is no false hit because every
    input to the trunk is in the key.
    """
    key = (repr(system), repr(getattr(msa, "sequences", msa)), mode)
    if _SESSION_CACHE["key"] == key and _SESSION_CACHE["session"] is not None:
        return _SESSION_CACHE["session"], True
    # Dropped before the new one is built so two systems' pair representations
    # are never both resident -- the budget is written for one.
    _SESSION_CACHE.update({"key": None, "session": None, "system": None})
    session = EmuSession(system, model=_model(), mode=mode, msa=msa)
    _SESSION_CACHE.update({"key": key, "session": session, "system": system})
    return session, False


def _sample(req: dict) -> dict:
    """Serve one sampling request off the held model."""
    doc = _request_document(req)

    system = _build_system(doc["system"])
    tokens = _count_tokens(system)
    if tokens > args.max_tokens:
        raise ValueError(
            f"the system is {tokens} tokens, above this provider's declared "
            f"ceiling of {args.max_tokens}. Tokens are counted as BioEmu-2 "
            f"counts them, so a ligand's atoms are included and the number is "
            f"usually larger than the residue count. The VRAM budget in "
            f"provider.toml was measured at that ceiling and nothing has "
            f"measured above it; raising one means re-measuring the other."
        )
    if tokens == 0:
        raise ValueError(
            "the system has no tokens. BioEmu-2 samples conformations of a "
            "molecule you define; it does not design one."
        )

    mode = doc.get("mode", "structure")
    if mode not in MODES:
        raise ValueError(f"'mode' must be one of {', '.join(MODES)}")

    num_samples = _int_field(doc, "num_samples", 1, 1, args.max_samples)

    physicality_mode = doc.get("physicality", "high_quality")
    if physicality_mode not in PHYSICALITY_MODES:
        raise ValueError(
            f"'physicality' must be one of {', '.join(PHYSICALITY_MODES)}"
        )

    seed = doc.get("seed", req.get("seed"))
    if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
        raise ValueError("'seed' must be an integer or null")

    msa = _build_msa(doc.get("msa"), system)
    return_topology = bool(doc.get("return_topology", False))

    # The caller's directory when it names one, and the setup smoke step always
    # does: its `outputs` assertion walks exactly that tree, so a worker writing
    # somewhere of its own would leave it empty and the assertion would report a
    # provider that produced nothing.
    #
    # WHEN NOBODY NAMES ONE, A TEMPORARY DIRECTORY -- NOT THE PROCESS'S CWD.
    # `Path(".")` was the first version of this line, and the MCP tool never
    # sends `out_dir`, so three files landed in the directory the MCP server
    # happened to be started from. That was the ToolUniverse checkout: `git
    # status` grew `topology.cif`, `samples.xtc` and `physicality.json` after
    # one live call. A server's working directory is not a scratch space.
    requested_out = req.get("out_dir")
    owns_out = requested_out is None
    work = Path(tempfile.mkdtemp(prefix="bioemu2-")) if owns_out else None
    out_dir = (work if owns_out else Path(requested_out)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        return _sample_into(
            out_dir, owns_out, system, msa, mode, tokens,
            num_samples, seed, physicality_mode, return_topology,
        )
    finally:
        if work is not None:
            shutil.rmtree(work, ignore_errors=True)


def _sample_into(
    out_dir,
    owns_out,
    system,
    msa,
    mode,
    tokens,
    num_samples,
    seed,
    physicality_mode,
    return_topology,
):
    """The GPU half of one request, with its output directory already chosen."""

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()

    session, embeddings_reused = _session(system, msa, mode)

    # ONE TIMING, NOT TWO, BECAUSE THE SPLIT WOULD BE A LIE. `EmuSession()` is
    # cheap: `__init__` only stores its inputs, and the trunk runs lazily
    # inside `_get_embedding()` on the first `sample()`. Timing the
    # constructor would therefore report ~0 s of "embedding" and hide the
    # trunk inside the sampling figure. `embeddings_reused` is the honest
    # signal -- on a miss the trunk is inside `generate_s`, on a hit it is
    # not, and the difference between the two is visible in the number.
    t = time.time()
    # progress=False: the bar writes carriage returns to the worker's log,
    # which is read as a transcript when something goes wrong.
    samples = session.sample(num_samples=num_samples, seed=seed, progress=False)
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    generate_s = round(time.time() - t, 2)

    report = check_physicality(samples, system=system, mode=physicality_mode)
    save_frames(samples, out_dir, physicality=report)

    passed = [bool(x) for x in report.passed]
    body = {
        "model": f"microsoft/bioemu2@{CHECKPOINT}",
        "mode": mode,
        "num_samples": num_samples,
        "tokens": tokens,
        "chains": list(system.chain_ids),
        "msa": "caller" if msa is not None else "colabfold",
        "seed": seed,
        "physicality": {
            "mode": physicality_mode,
            "checked": bool(getattr(report, "checked", True)),
            "n_passed": sum(passed),
            "passed": passed,
            "reasons": [None if r is None else str(r) for r in report.reasons],
        },
        "files": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
        "output_dir": None if owns_out else os.fspath(out_dir),
        "timing": {
            "generate_s": generate_s,
            "embeddings_reused": embeddings_reused,
        },
        "weights_held_by": "worker:bioemu2",
    }
    if return_topology:
        topology = out_dir / "topology.cif"
        body["topology_cif"] = topology.read_text() if topology.is_file() else None
    elif owns_out:
        body["structures_note"] = (
            "no out_dir was given, so topology.cif and samples.xtc were "
            "written to a temporary directory and deleted; pass "
            "return_topology=true for the CIF text in the reply. Trajectory "
            "frames are never inlined."
        )
    else:
        body["structures_note"] = (
            "topology.cif and samples.xtc were written to out_dir; pass "
            "return_topology=true for the CIF text in the reply"
        )
    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
        body["peak_allocated_gib"] = round(
            torch.cuda.max_memory_allocated() / 2**30, 2
        )
    return body


def _ready() -> dict:
    return {
        "build_s": round(time.time() - T0, 1),
        "device": DEVICE,
        "model": f"microsoft/bioemu2@{CHECKPOINT}",
        "model_load_s": _MODEL["load_s"],
        "max_tokens": args.max_tokens,
        "max_samples": args.max_samples,
        "weights_held_by": "worker:bioemu2",
        "kit": None,
    }


if __name__ == "__main__":
    # Loaded here rather than on the first request, and here it is the usual
    # argument rather than a formality: the load measured 49.9 s on the
    # verified card, which is longer than most requests it then serves.
    _model()
    say(
        f"ready t={time.time() - T0:.1f}s device={DEVICE} "
        f"model=microsoft/bioemu2@{CHECKPOINT} load={_MODEL['load_s']}s "
        f"limits={args.max_tokens}tok/{args.max_samples}samples "
        f"(no optimization kit: upstream ships the runtime)"
    )
    sys.exit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_sample,
            ready=_ready,
            log=say,
        )
    )
