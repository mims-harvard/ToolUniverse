"""Protenix 1.1.0 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter, with ``PROTENIX_V1_OPT`` and
``PROTENIX_ROOT_DIR`` in the environment::

    PROTENIX_V1_OPT=off PROTENIX_ROOT_DIR=~/.protenix \\
        <model python> protenix_v1_resident_worker.py --socket … --slug …

WHAT RESIDENCY BUYS HERE. Stock Protenix's entry point is ``protenix pred``,
whose ``runner.batch_inference.get_default_runner`` builds ``Protenix(configs)``
and then ``InferenceRunner.load_checkpoint`` reads 1,475,950,125 bytes into it.
The construction alone is expensive for a reason the kit's own ``lazy_init``
lever documents precisely: the model's random parameter initialisation is
"about a minute of CPU per process for the 368 M parameters", and every one of
those values is then overwritten by ``load_state_dict(strict=True)``. A
per-request process pays that minute, the checkpoint read, the CUDA context and
the first-use cuEquivariance/Triton compiles on every call. This worker pays
them once; only the per-request configuration, the dataloader and the dumper
are rebuilt.

WHO HOLDS THE WEIGHTS: **this worker**, and the reason it may is that the kit is
off. Under a kit mode ``protenix_v1_opt.stack`` wraps
``runner.inference.InferenceRunner.__init__`` and binds the kit's levers to the
runner the stock CLI builds, and it refuses to activate if something else got
there first -- so a worker that held a runner across requests under a kit mode
would be holding a runner the kit never saw. ``provider.toml`` explains why
``[kit] mode = "off"`` on this host; the consequence here is simply that nothing
replaces upstream's loader, so memoising it is this worker's job. The ready line
and every reply say ``weights_held_by = "worker"``.

NO NETWORK AT REQUEST TIME, and three separate doors are closed for it:

* **MSA.** ``protenix pred`` runs ``preprocess_input`` -> ``update_infer_json``
  before it builds anything, which posts the query's sequences to ByteDance's
  MSA web service. ``infer_predict`` -- the half this worker drives -- does not.
  So the search simply never happens here: ``use_msa`` defaults to false and a
  caller who has MSAs supplies them in the request JSON, by path or inline
  (``unpairedMsaPath`` / ``pairedMsaPath`` / ``unpairedMsa`` / ``pairedMsa``, or
  the older ``msa.precomputed_msa_dir``), which is what
  ``InferenceMSAFeaturizer.make_msa_feature`` reads.
* **Templates.** ``use_template`` is pinned false and is not a request option.
  Upstream's ``TemplateHitFeaturizer`` is constructed with
  ``fetch_remote=True`` by default and downloads mmCIF files from PDBe on
  demand, which is a per-request fetch from somebody else's server.
* **Weights.** ``download_inference_cache`` is called once, inside
  ``get_default_runner``, at build time -- and by then ``tu remote setup`` has
  already verified all seven files against ``stock/PINS.json``, so it finds
  everything present and fetches nothing.

NO FORK, and here upstream agrees with the standard rather than fighting it.
``get_inference_dataloader`` passes ``num_workers=configs.num_workers``, and
``configs/configs_inference.py`` already sets that to 0. This worker sets it to
0 again, explicitly, because the standard's rule is unconditional and a default
is not a guarantee. ``[kit.env] OMP_NUM_THREADS = "1"`` closes the other door
BoltzGen found -- a library's own thread pool, which no ``num_workers`` reaches.

UPSTREAM SWALLOWS PER-ITEM EXCEPTIONS, so this worker does not use
``infer_predict``. That function catches every exception a fold raises, writes
it to ``<dump_dir>/ERR/<sample>.txt`` and returns normally -- the exact shape
that made OpenFold3 report success for a run that folded nothing (STANDARD.md
section 14). The loop below is ``infer_predict``'s, statement for statement,
with the ``try/except`` removed and the structure count asserted: upstream's own
``get_inference_dataloader``, ``update_inference_configs``,
``runner.update_model_configs``, ``runner.predict`` and ``runner.dumper.dump``
are called, in that order. Nothing of upstream is patched; this is a different
driver for it, which is the position the kit's own batch worker occupies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description="Protenix v1 resident worker")
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="protenix_v1", help="provider slug, echoed in ping")
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
    print(f"[protenix_v1-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds Protenix's pinned stack
    (torch 2.13.0+cu130, numpy 2.4.1) and nothing of ToolUniverse, and importing
    the package would defeat the separation the standard exists for."""
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
            f"[protenix_v1-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("PROTENIX_V1_OPT") or "off").strip().lower()
LAYERNORM_TYPE = os.environ.get("LAYERNORM_TYPE", "fast_layernorm")
# Upstream's defaults, from stock/PINS.json "cli_defaults". They are the kernel
# choices `protenix pred` makes when nothing is said, and both resolve to
# cuEquivariance 0.11.1, which was measured working on this card -- see
# provider.toml. A deployment that needs the torch statements sets these two.
TRIMUL_KERNEL = os.environ.get("PROTENIX_V1_TRIMUL_KERNEL", "cuequivariance")
TRIATT_KERNEL = os.environ.get("PROTENIX_V1_TRIATT_KERNEL", "cuequivariance")

# Request limits. N^2 in tokens dominates this architecture's footprint, so the
# ceiling is where the provider's budget was measured and not a round number.
MAX_N_SAMPLE = 10
MAX_N_STEP = 400
MAX_N_CYCLE = 20


def _refuse_fast_layernorm() -> None:
    """Refuse to start under ``LAYERNORM_TYPE=fast_layernorm`` on a card the
    extension has no code for, rather than serve silent corruption.

    Stock Protenix compiles its own fast-LayerNorm CUDA extension at the first
    import of ``protenix.model.layer_norm``, and
    ``protenix/model/layer_norm/torch_ext_compile.py`` hard-codes the
    architectures it emits: ``("70","80","86","89","90","100")``, intersected
    with what the local nvcc lists, as ``-gencode arch=compute_X,code=sm_X``
    with no ``code=compute_X`` row -- so SASS only, no PTX, nothing above
    sm_100. Measured on this host (nvcc 13.0, compute capability 12.1), the
    built object holds exactly ``sm_80, sm_86, sm_89, sm_90, sm_100`` cubins and
    ``cuobjdump --list-ptx`` reports "No PTX file found".

    What makes this worth a refusal rather than a note is HOW it fails. The
    extension call returns normally, ``torch.cuda.synchronize()`` after it
    passes, and the next unrelated torch op on the card raises::

        torch.AcceleratorError: CUDA error: no kernel image is available for
        execution on the device

    so the error arrives attached to innocent code, with a LayerNorm output in
    hand that was never written. ``LAYERNORM_TYPE=torch`` is upstream's own
    switch for it (``protenix/model/triangular/layers.py`` reads the variable
    and does not even import the extension module when it is not
    ``fast_layernorm``), and ``[kit.env]`` sets it. This check exists so that an
    operator who overrides it on a card without sm_12x support is stopped at
    start-up instead of at the second request.
    """
    if LAYERNORM_TYPE != "fast_layernorm":
        return
    import torch

    if not torch.cuda.is_available():
        return
    major, minor = torch.cuda.get_device_capability()
    built = {(7, 0), (8, 0), (8, 6), (8, 9), (9, 0), (10, 0)}
    if (major, minor) in built:
        return
    raise _refuse(
        f"[protenix_v1-resident] LAYERNORM_TYPE=fast_layernorm on compute "
        f"capability {major}.{minor}: stock's fast-LayerNorm extension emits "
        f"SASS for {sorted(built)} and no PTX, so its kernels cannot launch "
        f"here -- and the failure is latent (the call returns, synchronize() "
        f'passes, the NEXT CUDA op raises). Set LAYERNORM_TYPE="torch", which '
        f"is what this provider's [kit.env] does."
    )


_refuse_fast_layernorm()

# ---------------------------------------------------------------- build, once
import torch  # noqa: E402  after the LayerNorm gate, which must precede any protenix import

ROOT = os.environ.get("PROTENIX_ROOT_DIR")
if not ROOT:
    raise _refuse(
        "[protenix_v1-resident] PROTENIX_ROOT_DIR is not set: it is the weights "
        "and data root upstream reads (<root>/checkpoint/ + <root>/common/). "
        "`tu remote setup protenix_v1` exports it from [weights] root_env."
    )

say(f"building: kit mode={MODE}, root={ROOT}, layernorm={LAYERNORM_TYPE}")
from runner.batch_inference import get_default_runner  # noqa: E402
from runner.inference import update_inference_configs  # noqa: E402

RUNNER = get_default_runner(
    use_msa=False,
    use_template=False,
    use_rna_msa=False,
    use_seeds_in_json=False,
    trimul_kernel=TRIMUL_KERNEL,
    triatt_kernel=TRIATT_KERNEL,
)
# Unconditional, per STANDARD.md section 14: a resident worker must not fork a
# data-loader child. Upstream's own default agrees (configs_inference.py sets
# num_workers 0), which is why this costs nothing and is set anyway.
RUNNER.configs.num_workers = 0
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
BUILD_S = time.time() - T0
PARAMS_M = sum(p.numel() for p in RUNNER.model.parameters()) / 1e6
say(
    f"ready in {BUILD_S:.1f}s on {DEVICE}: {PARAMS_M:.1f}M parameters, "
    f"weights_held_by=worker, trimul={TRIMUL_KERNEL}, triatt={TRIATT_KERNEL}"
)

_CHAIN_KEYS = ("proteinChain", "dnaSequence", "rnaSequence", "ligand", "ion")


def _parse_input(text: str) -> list:
    """The request's Protenix input JSON, validated to upstream's shape.

    ``infer_predict`` requires "a non-empty top-level list"; everything beyond
    that is refused here rather than three minutes into a featurisation.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"'input' is not JSON: {exc}") from None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        raise ValueError(
            "'input' must be a Protenix input JSON: a non-empty list of "
            '{"name": ..., "sequences": [...]} objects'
        )
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"entry {i} is not an object")
        seqs = item.get("sequences")
        if not isinstance(seqs, list) or not seqs:
            raise ValueError(f"entry {i}: 'sequences' must be a non-empty list")
        for j, chain in enumerate(seqs):
            if not isinstance(chain, dict) or not (set(chain) & set(_CHAIN_KEYS)):
                raise ValueError(
                    f"entry {i} chain {j}: expected one of {list(_CHAIN_KEYS)}"
                )
    return data


def _wants_msa(entries: list) -> bool:
    """True when any chain carries an MSA this worker can read from the request.

    No search is ever run; this only decides whether the featuriser is asked to
    look at what the caller supplied.
    """
    for item in entries:
        for chain in item.get("sequences") or []:
            c = chain.get("proteinChain") or chain.get("rnaSequence") or {}
            if not isinstance(c, dict):
                continue
            if any(
                c.get(k)
                for k in (
                    "unpairedMsa",
                    "pairedMsa",
                    "unpairedMsaPath",
                    "pairedMsaPath",
                )
            ):
                return True
            msa = c.get("msa")
            if isinstance(msa, dict) and msa.get("precomputed_msa_dir"):
                return True
    return False


def _apply_options(opts: dict, seed) -> dict:
    """Per-request knobs on the held runner's configs. The model is untouched.

    ``N_cycle``, ``N_sample`` and ``N_step`` are read out of ``configs`` by the
    forward pass at call time (``update_inference_configs`` already mutates the
    same object per item, which is upstream's own evidence that this is safe),
    and ``use_msa`` is read only by the dataset constructed per request --
    nothing in ``protenix/model/`` reads either of them.
    """
    cfg = RUNNER.configs
    applied = {}
    for key, path, low, high in (
        ("num_diffusion_samples", ("sample_diffusion", "N_sample"), 1, MAX_N_SAMPLE),
        ("num_diffusion_steps", ("sample_diffusion", "N_step"), 1, MAX_N_STEP),
        ("num_recycles", ("model", "N_cycle"), 1, MAX_N_CYCLE),
    ):
        if key not in opts:
            continue
        value = int(opts[key])
        if not low <= value <= high:
            raise ValueError(f"'{key}' must be between {low} and {high}")
        setattr(getattr(cfg, path[0]), path[1], value)
        applied[key] = value
    cfg.seeds = [int(seed) if seed is not None else 101]
    return applied


def _scores(out_dir: Path) -> dict:
    """The per-sample summary-confidence JSONs upstream writes beside each
    structure, parsed. With five diffusion samples the one thing a caller must
    do is rank them, and ``ranking_score`` in these files is how."""
    found = {}
    for path in sorted(out_dir.rglob("*summary_confidence*.json")):
        if path.stat().st_size > 1 << 20:
            continue
        try:
            found[str(path.relative_to(out_dir))] = json.loads(path.read_text())
        except (OSError, ValueError):  # a score we cannot read is not fatal
            continue
    return found


def _predict_one(req: dict) -> dict:
    """One prediction. The request carries the Protenix input JSON as text."""
    text = req.get("input") or req.get("query_json")
    if not text:
        raise ValueError("a request needs 'input': a Protenix input JSON")
    entries = _parse_input(text)
    name = req.get("name") or "input"
    out_dir = Path(req["out_dir"]) / name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Upstream writes an updated copy of the input beside the --input file, so
    # the request's own output directory is where it goes -- never the kit tree,
    # never a shared path.
    input_path = out_dir / f"{name}.json"
    input_path.write_text(json.dumps(entries, indent=1))

    opts = dict(req.get("options") or {})
    applied = _apply_options(opts, req.get("seed"))
    cfg = RUNNER.configs
    cfg.input_json_path = str(input_path)
    cfg.dump_dir = str(out_dir)
    cfg.num_workers = 0
    use_msa = bool(opts.get("use_msa", _wants_msa(entries)))
    cfg.use_msa = use_msa
    cfg.use_template = False
    RUNNER.dump_dir = str(out_dir)
    RUNNER.error_dir = str(out_dir / "ERR")
    os.makedirs(RUNNER.error_dir, exist_ok=True)
    RUNNER.init_dumper(
        need_atom_confidence=cfg.need_atom_confidence,
        sorted_by_ranking_score=cfg.sorted_by_ranking_score,
    )

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()

    # infer_predict's loop, without its per-item try/except. See the module
    # docstring: that except is what turns a fold that raised into a reply that
    # looks like success.
    from protenix.data.inference.infer_dataloader import get_inference_dataloader
    from protenix.utils.seed import seed_everything

    dataloader = get_inference_dataloader(configs=cfg)
    sizes = []
    for seed in cfg.seeds:
        seed_everything(seed=seed, deterministic=cfg.deterministic)
        for batch in dataloader:
            data, atom_array, data_error_message = batch[0]
            sample_name = data["sample_name"]
            if len(data_error_message) > 0:
                raise RuntimeError(
                    f"Protenix refused the input for {sample_name!r}: "
                    f"{data_error_message}"
                )
            n_token = int(data["N_token"].item())
            sizes.append(
                {
                    "sample_name": sample_name,
                    "n_token": n_token,
                    "n_atom": int(data["N_atom"].item()),
                    "n_asym": int(data["N_asym"].item()),
                    "n_msa": int(data["N_msa"].item()),
                }
            )
            RUNNER.update_model_configs(update_inference_configs(cfg, n_token))
            prediction = RUNNER.predict(data)
            RUNNER.dumper.dump(
                dataset_name="",
                pdb_id=sample_name,
                seed=seed,
                pred_dict=prediction,
                atom_array=atom_array,
                entity_poly_type={
                    k: v
                    for k, v in data["entity_poly_type"].items()
                    if v != "non-polymer"
                },
            )
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    timing = {"predict_s": round(time.time() - t, 2)}

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    # `<name>_sample_<rank>.cif`, as runner/dumper.py writes it. The same glob
    # is [runtime] outputs, and it matches nothing the provider writes on a
    # failure: the error path writes <dump_dir>/ERR/<sample>.txt and the
    # featuriser's copy of the input is .json.
    structures = [
        f
        for f in files
        if f.endswith(".cif") and "_sample_" in os.path.basename(f) and "/ERR/" not in f
    ]
    if not structures:
        errs = sorted((out_dir / "ERR").glob("*.txt"))
        detail = "\n\n".join(p.read_text()[:4000] for p in errs) or (
            "upstream left no error file; the worker transcript is the only record"
        )
        raise RuntimeError(f"Protenix wrote no structure for {name!r}.\n\n{detail}")

    body = {
        "out_dir": str(out_dir),
        "structures": structures,
        "n_structures": len(structures),
        "files": files,
        "seeds": list(cfg.seeds),
        "inputs": sizes,
        "use_msa": use_msa,
        "options_applied": applied,
        "timing": timing,
        "weights_held_by": "worker",
        "kit_mode": MODE,
        "loader_workers": 0,
        "scores": _scores(out_dir),
    }
    if DEVICE == "cuda":
        # A high-water mark, not a per-request figure: no on_reset is declared,
        # so this is what the worker holds, which is what a host budgets.
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "weights_held_by": "worker",
        "kit_mode": MODE,
        "model_name": RUNNER.configs.model_name,
        "parameters_m": round(PARAMS_M, 1),
        "layernorm_type": LAYERNORM_TYPE,
        "trimul_kernel": TRIMUL_KERNEL,
        "triatt_kernel": TRIATT_KERNEL,
        "loader_workers": 0,
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "unset"),
        "protenix_root_dir": ROOT,
    }


if __name__ == "__main__":
    raise SystemExit(
        WB.serve(
            slug=args.slug,
            socket_path=args.socket,
            on_predict=_predict_one,
            ready=_ready,
            log=say,
        )
    )
