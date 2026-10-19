"""OpenDDE 1.1.1 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter, with ``OPENDDE_OPT`` and
``OPENDDE_ROOT_DIR`` in the environment::

    OPENDDE_OPT=off OPENDDE_ROOT_DIR=~/.opendde \\
        <model python> opendde_resident_worker.py --socket … --slug …

WHAT OPENDDE IS, STATED PLAINLY BECAUSE NOTHING IN THIS REPOSITORY SAID SO.
OpenDDE (Aureka AI Research, Apache 2.0, PyPI ``opendde`` 1.1.1, model
``opendde_v1``, 655.8 M parameters, one general-purpose checkpoint
``opendde.pt`` of 2,625,249,069 bytes) is an AlphaFold3-class all-atom
co-folding model: it takes a complex of protein / DNA / RNA chains, ligands
and ions and returns diffusion-sampled all-atom mmCIF structures, each scored
with pLDDT / pTM / ipTM / PAE and a ranking score. Its code is a descendant of
Protenix's (the CLI shape, the dumper's file names and the AlphaFold-Server
style input JSON are Protenix's), rewritten around a typed config tree.

ITS INPUT DIALECT is that JSON: a non-empty list of jobs, each
``{"name": ..., "sequences": [<entity>, ...]}`` with an entity one of
``{"proteinChain": {"sequence", "count"}}``, ``{"dnaSequence": ...}``,
``{"rnaSequence": ...}``, ``{"ligand": {"ligand": "CCD_<id>" | <SMILES> |
"FILE_<path>", "count"}}`` or ``{"ion": {"ion": "NA", "count"}}``.

ONE REQUEST here is ONE job of that list: one complex, folded for ONE seed
into ``num_diffusion_samples`` structures (upstream's default five), through
``num_recycles`` Pairformer cycles (default 10) and ``num_diffusion_steps``
steps per sample (default 200), with the per-sample scores. Nothing more:
no MSA search, no templates, no RNA MSA (see below).

WHAT RESIDENCY BUYS. Stock's entry point is ``opendde pred``, whose
``runner.batch_inference.get_default_runner`` builds ``InferenceRunner`` --
the 655.8 M-parameter model, the 2.6 GB checkpoint, the CUDA context -- and
exits. Upstream's own ``inference_jsons`` already builds ONE runner and loops
``infer_predict`` over several input files, which is the evidence that a held
runner is something upstream expects; this worker is that loop with a socket
in front of it.

WHO HOLDS THE WEIGHTS: **this worker**, and the reason it may is that the kit
is off (``provider.toml`` has the argument). Under a kit mode
``opendde_opt.stack`` wraps ``InferenceRunner.__init__`` and refuses to
activate when something else got there first. The ready line and every reply
say ``weights_held_by = "worker"``.

UPSTREAM'S BUILDER IS RE-ENTRANT, which was the first thing checked and is
the check that would have mattered most: ``get_default_runner`` was called
THREE times in one process (the first runner still alive for the second, then
closed for the third) and every build succeeded with the same 655.8 M
parameters and identical leading tensors. No module state limits a process to
one build, which is what genie3's config did.

NO NETWORK AT REQUEST TIME, and the doors are closed here rather than hoped
shut:

* **MSA.** ``opendde pred`` runs ``preprocess_input`` -> ``update_infer_json``
  before folding, which posts the query's sequences to an MSA web service.
  The half this worker drives (the dataloader and the model) does not, and
  ``use_msa`` is pinned false. Single-sequence OpenDDE is a materially weaker
  model than MSA-fed OpenDDE; the reply says which was used.
* **Templates and RNA MSA** are pinned false (templates fetch mmCIF files
  from PDBe on demand, RNA MSA needs databases this provider does not have).
* **Weights.** ``download_inference_cache`` runs once inside
  ``get_default_runner`` and finds five certified files.

NO FORK. ``configs.num_workers`` is 0 upstream and is set to 0 again here,
because the standard's rule is unconditional and a default is not a guarantee;
``OMP_NUM_THREADS=1`` (``[kit.env]``) closes the other door, a library's own
thread pool, which no ``num_workers`` reaches.

THE LOOP IS UPSTREAM'S, STATEMENT FOR STATEMENT, with two additions and one
omission. ``runner.inference._infer_predict_impl`` is written for
rank-synchronised Fold-CP and for a whole input file; this does what it does
for one job on one rank -- ``seed_everything``, ``cleanup_device_memory``,
``get_inference_dataloader``, ``_prepare_prediction_batch`` (which stamps the
seed into the features and updates the model's configs), ``runner.predict``,
``runner.dumper.dump`` -- inside ``disable_cudnn_benchmark``. Added: a token
ceiling checked after featurisation and BEFORE the model runs (a ligand's
token count is its atom count, which only the featuriser knows, so the tool
cannot enforce it); and the structure count is asserted. Omitted: nothing
swallows a per-sample exception, because the failure must arrive as a failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description="OpenDDE resident worker")
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="opendde", help="provider slug, echoed in ping")
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
    print(f"[opendde-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds OpenDDE's pinned stack
    (torch 2.7.1+cu128, numpy 2.4.1) and nothing of ToolUniverse, and importing
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
            f"[opendde-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (os.environ.get("OPENDDE_OPT") or "off").strip().lower()
if MODE != "off":
    raise _refuse(
        f"[opendde-resident] OPENDDE_OPT={MODE!r}: this worker holds upstream's "
        f"InferenceRunner itself, which is only coherent with the kit off -- under "
        f"a kit mode opendde_opt wraps the runner's constructor and refuses a "
        f"process that built one first. provider.toml declares [kit] mode = "
        f'"off" and the kit step refuses every other value on this architecture.'
    )

# Request limits. The token ceiling is where the declared VRAM budget was
# measured (provider.toml [gpu]); it equals opendde_tool.MAX_TOKENS_TOTAL, which
# checks the polymer residues, while this checks the featurised count -- the
# only place a ligand's tokens (its atoms) are known. The sample ceiling moves
# time and not memory (measured: peak identical at 1 and 5 samples).
# Constants, not environment variables: a ceiling an operator can raise past the
# envelope the budget was measured at is not a ceiling.
MAX_TOKENS = 400
MAX_N_SAMPLE = 5
MAX_N_STEP = 400
MAX_N_CYCLE = 20
# Upstream's own CLI defaults (stock/PINS.json cli_defaults): the values a
# request that names nothing gets, and the ones restored after a request that
# did -- the configs object is held across requests, so a request that changed
# a knob must not leak it into the next.
DEFAULT_N_SAMPLE = 5
DEFAULT_N_STEP = 200
DEFAULT_N_CYCLE = 10
# bf16 autocast, and ONLY bf16. It is the kit's stock arm (`--mode off` passes
# --dtype bf16, "one of the two documented speed settings upstream exposes");
# fp32 is upstream's CLI default. It is not a request option and not an
# environment variable because it moves the declared VRAM budget and the time:
# measured at 200 tokens, one worker each, fp32 peaks at 10.98 GiB against
# 6.85 for bf16 (1.60x) and takes 517 s against 245 (2.1x, on a contended
# card). An axis that multiplies the envelope has to be measured at the
# envelope's worst point, and a precision nobody asked for is not worth a
# second row of the ladder.
DTYPE = "bf16"

# ---------------------------------------------------------------- build, once
import torch  # noqa: E402

ROOT = os.environ.get("OPENDDE_ROOT_DIR")
if not ROOT:
    raise _refuse(
        "[opendde-resident] OPENDDE_ROOT_DIR is not set: it is the weights and "
        "data root upstream reads (<root>/checkpoint/ + <root>/common/). "
        "`tu remote setup opendde` exports it from [weights] root_env."
    )

# Upstream's own default is "torch" (opendde/model/triangular/layers.py reads the
# variable with that default). The kit's stock arm exports `fast_layernorm` as a
# "documented speed setting"; `provider.toml [kit.env]` states "torch" and says
# why that was measured rather than assumed, and it overrides whatever the
# operator exported. Read here only so the ready line reports what is in force.
LAYERNORM_TYPE = os.environ.get("LAYERNORM_TYPE", "torch")

say(f"building: kit mode={MODE}, root={ROOT}, layernorm={LAYERNORM_TYPE}, dtype={DTYPE}")
from runner.batch_inference import get_default_runner  # noqa: E402
from runner.inference import (  # noqa: E402
    _prepare_inference_batch,
    _prepare_prediction_batch,
    _tensor_scalar,
)
from opendde.data.inference.infer_dataloader import (  # noqa: E402
    get_inference_dataloader,
)
from opendde.utils.seed import seed_everything  # noqa: E402
from opendde.utils.torch_utils import (  # noqa: E402
    cleanup_device_memory,
    disable_cudnn_benchmark,
)

RUNNER = get_default_runner(
    use_msa=False,
    use_template=False,
    use_rna_msa=False,
    dtype=DTYPE,
    # `auto` and nothing else, on purpose. Upstream's own platform gate
    # (opendde/utils/environment.py) resolves `auto` to the torch triangle
    # kernels on anything but Linux x86_64 and REFUSES an explicit
    # `cuequivariance` there ("supported only on Linux x86_64. Use auto/torch
    # kernels on this platform."), so on this host `auto` IS `torch` and the
    # cuEquivariance wheels the lock carries are never imported. That matters:
    # cuEquivariance 0.10.0's triangle-multiplication kernel is Triton, and
    # triton 3.3.1 cannot lower a warp shuffle for sm_121 -- measured in a
    # standalone probe, it aborts the PROCESS ("LLVM ERROR: Cannot select:
    # intrinsic %llvm.nvvm.shfl.sync.bfly.i32") at 128 tokens and up. Upstream's
    # gate is what keeps a fold from ever reaching it.
    trimul_kernel="auto",
    triatt_kernel="auto",
)
# Unconditional, per STANDARD.md section 14: a resident worker must not fork a
# data-loader child. Upstream's own default agrees (inference_defaults.py sets
# num_workers 0), which is why this costs nothing and is set anyway.
RUNNER.configs.num_workers = 0
DEVICE = "cuda" if RUNNER.device.type == "cuda" else RUNNER.device.type
BUILD_S = time.time() - T0
PARAMS_M = sum(p.numel() for p in RUNNER.model.parameters()) / 1e6
TRIMUL = RUNNER.configs.triangle_multiplicative
TRIATT = RUNNER.configs.triangle_attention
say(
    f"ready in {BUILD_S:.1f}s on {DEVICE}: {PARAMS_M:.1f}M parameters, "
    f"weights_held_by=worker, trimul={TRIMUL}, triatt={TRIATT}"
)
if DEVICE != "cuda":
    raise _refuse(
        f"[opendde-resident] the runner selected device {DEVICE!r}, not cuda: this "
        f"provider declares [gpu] policy = \"required\"."
    )

_CHAIN_KEYS = ("proteinChain", "dnaSequence", "rnaSequence", "ligand", "ion")
# Fields upstream would resolve against the HOST's filesystem or the network on
# a caller's say-so. None is offered by the tool; this is the second lock.
_FORBIDDEN_FIELDS = (
    "unpairedMsaPath",
    "pairedMsaPath",
    "templatesPath",
    "msa",
    "templates",
)


def _parse_input(text: str) -> list:
    """The request's OpenDDE input JSON, validated to upstream's shape.

    Upstream requires "a non-empty top-level list" of named jobs; everything
    beyond that is refused here rather than three minutes into a featurisation.
    """
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"'input' is not JSON: {exc}") from None
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or len(data) != 1:
        raise ValueError(
            "'input' must be an OpenDDE input JSON holding exactly ONE job: "
            '[{"name": ..., "sequences": [...]}]'
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
            body = next((v for k, v in chain.items() if k in _CHAIN_KEYS), {})
            if isinstance(body, dict):
                bad = [f for f in _FORBIDDEN_FIELDS if f in body]
                if bad:
                    raise ValueError(
                        f"entry {i} chain {j}: {bad} would make the worker read a "
                        f"path or fetch from the network; this provider runs "
                        f"single-sequence"
                    )
                lig = body.get("ligand")
                if isinstance(lig, str) and lig.startswith("FILE_"):
                    raise ValueError(
                        f"entry {i} chain {j}: upstream's FILE_<path> ligand form "
                        f"reads a file off the host"
                    )
    return data


_OPTION_KEYS = ("num_diffusion_samples", "num_diffusion_steps", "num_recycles")


def _apply_options(opts: dict, seed) -> dict:
    """Per-request knobs on the held runner's configs. The model is untouched.

    EVERY knob is set on EVERY request -- to the request's value or to
    upstream's default -- because ``RUNNER.configs`` outlives the request. A
    setter that only touched the keys a request named would let one caller's
    ``num_recycles=2`` become the next caller's default, and nothing would
    raise. ``N_cycle``, ``N_sample`` and ``N_step`` are read out of ``configs``
    by the forward pass at call time and ``update_model_configs`` re-binds the
    model's own copies; nothing in the model is rebuilt by any of them. An
    option this function does not know is refused rather than ignored: a typo
    that quietly did nothing would read as a setting that was honoured.
    """
    unknown = sorted(set(opts) - set(_OPTION_KEYS))
    if unknown:
        raise ValueError(f"unknown option(s) {unknown}; this worker takes {list(_OPTION_KEYS)}")
    cfg = RUNNER.configs
    applied = {}
    for key, default, low, high in (
        ("num_diffusion_samples", DEFAULT_N_SAMPLE, 1, MAX_N_SAMPLE),
        ("num_diffusion_steps", DEFAULT_N_STEP, 1, MAX_N_STEP),
        ("num_recycles", DEFAULT_N_CYCLE, 1, MAX_N_CYCLE),
    ):
        value = int(opts.get(key, default))
        if not low <= value <= high:
            raise ValueError(f"'{key}' must be between {low} and {high}")
        applied[key] = value
    cfg.sample_diffusion.N_sample = applied["num_diffusion_samples"]
    cfg.sample_diffusion.N_step = applied["num_diffusion_steps"]
    cfg.model.N_cycle = applied["num_recycles"]
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
    """One prediction. The request carries the OpenDDE input JSON as text."""
    text = req.get("input") or req.get("query_json")
    if not text:
        raise ValueError("a request needs 'input': an OpenDDE input JSON")
    entries = _parse_input(text)
    name = req.get("name") or entries[0].get("name") or "input"
    entries[0]["name"] = name
    out_dir = Path(req["out_dir"]) / name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Upstream reads the job list from a file path. It is written inside the
    # request's own output directory -- never the kit tree, never a shared path.
    input_path = out_dir / f"{name}.json"
    input_path.write_text(json.dumps(entries, indent=1))

    opts = dict(req.get("options") or {})
    applied = _apply_options(opts, req.get("seed"))
    cfg = RUNNER.configs
    cfg.input_json_path = str(input_path)
    cfg.dump_dir = str(out_dir)
    cfg.num_workers = 0
    cfg.use_msa = False
    cfg.use_template = False
    cfg.use_rna_msa = False
    # Upstream's own two methods: `init_basics` re-points dump/error dirs at
    # configs.dump_dir (and resets ERR, "the status of this Runner invocation");
    # `init_dumper` binds the DataDumper to the new base directory.
    RUNNER.init_basics()
    RUNNER.init_dumper(
        need_atom_confidence=cfg.need_atom_confidence,
        sorted_by_ranking_score=cfg.sorted_by_ranking_score,
    )

    t = time.time()
    sizes = []
    featurize_s = predict_s = dump_s = 0.0
    with disable_cudnn_benchmark(RUNNER.device):
        for seed in cfg.seeds:
            seed_everything(seed=seed, deterministic=cfg.deterministic)
            cleanup_device_memory(RUNNER.device)
            dataloader = get_inference_dataloader(configs=cfg)
            iterator = iter(dataloader)
            while True:
                seed_everything(seed=seed, deterministic=cfg.deterministic)
                t1 = time.time()
                try:
                    batch = next(iterator)
                except StopIteration:
                    break
                data, atom_array, data_error_message = _prepare_inference_batch(batch)
                featurize_s += time.time() - t1
                sample_name = str(data["sample_name"])
                if data_error_message:
                    raise RuntimeError(
                        f"OpenDDE refused the input for {sample_name!r}: "
                        f"{data_error_message}"
                    )
                n_token = _tensor_scalar(data, "N_token")
                if n_token is not None and n_token > MAX_TOKENS:
                    raise ValueError(
                        f"{sample_name!r} featurised to {n_token} tokens, over this "
                        f"provider's {MAX_TOKENS}-token ceiling, which is the "
                        f"envelope its VRAM budget was measured at (a ligand's "
                        f"tokens are its atoms, which only the featuriser knows)"
                    )
                sizes.append(
                    {
                        "sample_name": sample_name,
                        "n_token": n_token,
                        "n_atom": _tensor_scalar(data, "N_atom"),
                        "n_asym": _tensor_scalar(data, "N_asym"),
                        "n_msa": _tensor_scalar(data, "N_msa"),
                    }
                )
                prediction = None
                try:
                    _prepare_prediction_batch(RUNNER, cfg, data, seed=seed)
                    t2 = time.time()
                    prediction = RUNNER.predict(data)
                    torch.cuda.synchronize()
                    predict_s += time.time() - t2
                    t3 = time.time()
                    RUNNER.dumper.dump(
                        group_name="",
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
                    dump_s += time.time() - t3
                finally:
                    del batch, data, atom_array, prediction
                    cleanup_device_memory(RUNNER.device, collect_garbage=False)
            del iterator
            cleanup_device_memory(RUNNER.device, synchronize=True)
    timing = {
        "total_s": round(time.time() - t, 2),
        "featurize_s": round(featurize_s, 2),
        "predict_s": round(predict_s, 2),
        "dump_s": round(dump_s, 2),
    }

    files = sorted(str(p) for p in out_dir.rglob("*") if p.is_file())
    # `<name>_sample_<rank>.cif`, as runner/dumper.py writes it. The same glob
    # is [runtime] outputs, and it matches nothing the provider writes on a
    # failure: the featuriser's copy of the input is .json and ERR/ holds .txt.
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
        raise RuntimeError(f"OpenDDE wrote no structure for {name!r}.\n\n{detail}")

    body = {
        "out_dir": str(out_dir),
        "structures": structures,
        "n_structures": len(structures),
        "files": files,
        "seeds": list(cfg.seeds),
        "inputs": sizes,
        "use_msa": False,
        "options_applied": applied,
        "timing": timing,
        "weights_held_by": "worker",
        "kit_mode": MODE,
        "loader_workers": 0,
        "scores": _scores(out_dir),
    }
    # A high-water mark, not a per-request figure: no reset and no on_reset, so
    # this is what the worker holds, which is what a host adds up.
    body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    # Beside it, what tensors actually held at the peak. The gap between the two
    # is the caching allocator's own slack (fragmentation), which is what
    # `expandable_segments` exists to return, and a budget quoted from one of
    # them without the other cannot be told apart from a model that needs it.
    body["peak_allocated_gib"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
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
        "trimul_kernel": TRIMUL,
        "triatt_kernel": TRIATT,
        "dtype": DTYPE,
        "max_tokens": MAX_TOKENS,
        "max_samples": MAX_N_SAMPLE,
        "loader_workers": 0,
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", "unset"),
        "opendde_root_dir": ROOT,
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
