"""ProteinMPNN held resident, answering one design request at a time.

Run by the model's own interpreter, with the mode on the command line and NOT
in the environment::

    <model python> proteinmpnn_resident_worker.py --socket … --slug … --kit … --mode off

**This worker runs on the CPU, and that is a measurement.** `[gpu] policy =
"none"` in provider.toml carries the evidence and `environment/requirements.lock`
carries the deviations. The kit pins torch by direct URL to
`torch-2.5.1+cu124-cp311-cp311-linux_x86_64.whl`, which cannot install on
aarch64 at all; PyPI's `torch==2.5.1` for cp311 aarch64 is the same version and
is CPU-only, read off the install: `torch.version.cuda is None`,
`torch.cuda.get_arch_list() == []`, four libtorch objects and no
`libtorch_cuda.so`.

**Why this worker runs STOCK's loop and not the kit's own persistent worker,
which exists.** The kit ships `mpnn_worker2.py`, a persistent sampler built for
exactly this job, and on this host it RUNS: `--mode exact` completed on the CPU
and its `.fa` files and `parsed.jsonl` compared byte for byte equal to stock's,
on a device the kit never documents. It was still declined, on the clock:

    off (stock)   42.78 s wall   30.45 s generation
    exact (kit)   43.07 s wall   38.53 s t_run_s

The kit's worker switches off three of its eleven levers without a CUDA device
(`mpnn_worker2.py:1192`: `graph_rng`, `single_graph`, `fused_draw`) and runs the
other eight, and the eight are all ways of filling a GPU -- 16 backbones per
forward, a low-memory featuriser that recomputes rather than materialises. On a
CPU there is nothing to fill, so they cost 8 s and buy nothing. Held against the
42.8 s a non-resident request pays, the kit's worker would make this provider
1.11x and stock's loop makes it 1.40x; 1.11x is below the floor of every
provider on this standard. The kit's own driver reaches the same verdict in its
own vocabulary and refuses to call the run activated: `NOT ACTIVE: partial
activation -- graph_rng,single_graph,fused_draw`, exit 3.

So `[kit] mode = "off"` and `levers_declined` names all of them. What is NOT
declined is the one lever with no device in it: `fast_parse`, the kit's
read-once PDB parser (`cls = "datapath"`, tier 1), 1.32 s against the stock
helper's 1.32->0.47 s on the same two files with byte-identical output, because
the stock helper re-reads each file for all 352 candidate chain letters. It is a
plain function, `parse_pdb(path)`, and this worker calls it.

**What this script is, precisely.** A different script in the position
`protein_mpnn_run.py` occupies, calling stock's own functions in stock's own
order. Nothing in ProteinMPNN is patched, shadowed or copied. Every step below
cites the line of `protein_mpnn_run.py` it mirrors, and the claim that it
mirrors them is not an argument: the acceptance suite byte-compares this
worker's `.fa` output against the `off` route's for the same input and seed.

**The one thing residency changes, and how it is kept exact.** Stock calls
`torch.manual_seed(seed)` (`protein_mpnn_run.py:29`) BEFORE constructing
`ProteinMPNN`, and construction consumes the default generator (measured:
`torch.get_rng_state()` differs across it). A resident worker builds the model
once, so it cannot inherit that generator position for a seed it has not seen.
Per request it therefore replays it: `manual_seed(seed)`, construct a throwaway
`ProteinMPNN` with the same arguments -- 16 ms, 1.66M parameters -- and discard
it, leaving the default generator exactly where stock's would be. Measured
replayable. The held model's weights are untouched by this; only the generator
moves.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import resource
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ap = argparse.ArgumentParser(description="ProteinMPNN resident design worker")
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="proteinmpnn", help="provider slug, echoed in ping")
ap.add_argument("--kit", default="", help="the kit tree (proteinmpnn/ of the checkout)")
ap.add_argument(
    "--mode",
    default="off",
    help="the kit mode this worker was built for. 'off' is the only value this "
    "provider declares and the only one it accepts: the kit's optimised line is "
    "a GPU line and was declined on the clock (see the module docstring).",
)
ap.add_argument(
    "--variant",
    default="vanilla",
    choices=["vanilla", "soluble"],
    help="the weight set held at start-up; upstream's default is vanilla "
    "(protein_mpnn_run.py:44-49). A request may name the other, which costs one "
    "checkpoint load (0.01 s, 6.7 MB) and is then held too.",
)
args = ap.parse_args()

SLUG = args.slug


def say(msg: str) -> None:
    print(f"[{SLUG}-resident] {msg}", flush=True)


def _refuse(message: str) -> SystemExit:
    """Exit 3 -- the standard's 'refused', whose last line names the cause."""
    say(message)
    return SystemExit(3)


if args.mode != "off":
    raise _refuse(
        f"--mode {args.mode!r}: this provider declares mode 'off' and holds stock "
        f"ProteinMPNN's own loop. The kit's optimised line runs on this CPU host "
        f"and is byte-identical to stock there, and it is 8 s slower per pass "
        f"because every lever it keeps is a way of filling a GPU; provider.toml's "
        f"[kit] levers_declined names them with the measurement. Nothing here can "
        f"serve another mode, so this is a refusal rather than a fallback."
    )


def _load_by_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise _refuse(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_worker_base():
    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    path = Path(override) if override else None
    if path is None or not path.is_file():
        raise _refuse(
            "the shared worker base was not found; set "
            "TOOLUNIVERSE_REMOTE_WORKER_BASE to worker_base.py's path"
        )
    return _load_by_path("_tu_remote_worker_base", path)


WB = _load_worker_base()

# ----------------------------------------------------------------- the stack
MPNN_DIR = os.environ.get("MPNN_DIR", "")
if not MPNN_DIR or not (Path(MPNN_DIR) / "protein_mpnn_run.py").is_file():
    raise _refuse(
        f"MPNN_DIR={MPNN_DIR!r} does not hold protein_mpnn_run.py -- it must be the "
        f"stock ProteinMPNN clone at 8907e667 (run `tu remote setup {SLUG}`)"
    )
sys.path.insert(0, MPNN_DIR)  # == mpnn_worker2.py:97, and what run.sh exports

import numpy as np  # noqa: E402
import torch  # noqa: E402

# stock's own helpers, imported as protein_mpnn_run.py:21 imports them
from protein_mpnn_utils import (  # noqa: E402
    ProteinMPNN,
    StructureDatasetPDB,
    _S_to_seq,
    _scores,
    tied_featurize,
)

# The kit's read-once PDB parser: a plain function, the one lever of this kit
# that pays on a CPU. Loaded by path because `kit/` is not an importable
# package; if the kit tree is not there the stock helper's logic is not
# reimplemented here -- the launch refuses, because a provider that silently
# stops using a declared lever is mistake 12.
KIT_HOME = Path(args.kit) if args.kit else None
_parser_path = (
    KIT_HOME / "opt" / "forward" / "mpnn_pdb_parser" / "kit" / "fast_parse.py"
    if KIT_HOME
    else None
)
if _parser_path is None or not _parser_path.is_file():
    raise _refuse(
        f"the kit's read-once parser is not at {_parser_path} -- "
        f"run `tu remote setup {SLUG} --only kit`"
    )
FAST_PARSE = _load_by_path("_mpnn_fast_parse", _parser_path)

DEVICE = torch.device("cpu")
if torch.cuda.is_available():  # pragma: no cover - not reachable on this stack
    say(
        "torch reports a CUDA device, which this provider's stack is not built "
        "for ([gpu] policy = \"none\"): designing on the CPU as declared"
    )

ALPHABET = "ACDEFGHIKLMNPQRSTVWYX"
OMIT_AAS_NP = np.array([AA in "X" for AA in ALPHABET]).astype(np.float32)
BIAS_AAS_NP = np.zeros(len(ALPHABET))

_CKPTS: Dict[str, Any] = {}
_MODELS: Dict[str, Any] = {}


def _ckpt_path(variant: str) -> Path:
    return Path(MPNN_DIR) / f"{variant}_model_weights" / "v_48_020.pt"


def _build_bare(num_edges: int):
    """stock's constructor call, protein_mpnn_run.py:213-215, verbatim."""
    return ProteinMPNN(
        ca_only=False,
        num_letters=21,
        node_features=128,
        edge_features=128,
        hidden_dim=128,
        num_encoder_layers=3,
        num_decoder_layers=3,
        augment_eps=0.0,
        k_neighbors=num_edges,
    )


def _model(variant: str):
    """The held model for `variant`, loaded on first use and then kept."""
    if variant in _MODELS:
        return _MODELS[variant], _CKPTS[variant]
    path = _ckpt_path(variant)
    if not path.is_file():
        raise ValueError(
            f"variant {variant!r}: no checkpoint at {path}; the clone must hold "
            f"both weight sets (the kit's stock/PINS.json pins them)"
        )
    t0 = time.time()
    ck = torch.load(path, map_location=DEVICE)
    model = _build_bare(ck["num_edges"])
    model.to(DEVICE)
    model.load_state_dict(ck["model_state_dict"])
    model.eval()
    _MODELS[variant], _CKPTS[variant] = model, ck
    say(
        f"{variant}: held ({path.name}, {path.stat().st_size} bytes, "
        f"num_edges={ck['num_edges']}, {time.time() - t0:.3f}s)"
    )
    return model, ck


def _seed_as_stock(seed: int, num_edges: int) -> None:
    """Put the default generators where stock's are at the start of its loop.

    protein_mpnn_run.py:29,31 seed torch and numpy, then :213-215 CONSTRUCT the
    model, and construction draws from the default generator. A held model
    cannot inherit that position, so it is replayed: one throwaway construction
    with stock's own arguments, 16 ms, discarded. Measured replayable; the
    acceptance suite byte-compares the result against the stock route's.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    _build_bare(num_edges)


# --------------------------------------------------------------- bookkeeping
def _peak_rss_gib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024.0**2)


def _rss_gib() -> float:
    try:
        with open("/proc/self/statm", "r", encoding="utf-8") as fh:
            return int(fh.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / (1024.0**3)
    except OSError:  # pragma: no cover
        return 0.0


MAX_RESIDUES = int(os.environ.get("PROTEINMPNN_MAX_RESIDUES", "3000"))
MAX_SEQS = 128


def _request(req: Dict[str, Any]) -> Dict[str, Any]:
    """The request body, from either shape the standard sends.

    An ordinary request from the tool layer carries its fields directly. THE
    SMOKE STEP SENDS A DIFFERENT SHAPE, fixed by `setup.step_smoke` and not by
    this provider: `{"op": "predict", "input": <the smoke file's TEXT>,
    "out_dir": …, "name": "smoke", "seed": 0, "options": {}}`. `input` is
    deliberately neutral -- "the provider decides what its input text means" --
    and for this provider it means a JSON object with the tool layer's own
    parameter names, so `smoke/input.json` is readable as the request it is.

    The outer `seed: 0` is the standard saying "the provider decides", not a
    caller asking for seed zero, so it never overrides a seed in the body. This
    was got wrong first: the smoke failed with this worker's own refusal,
    `'seed' must be >= 1`, because the shape was guessed from a sibling instead
    of read from `setup.py` -- mistake 55, for the fourth time.
    """
    body = req.get("request") or req.get("payload")
    if body is None and isinstance(req.get("input"), str):
        try:
            body = json.loads(req["input"])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"this provider's smoke input must be a JSON object with the "
                f"tool layer's parameter names; it did not parse: {exc}"
            ) from None
        if not isinstance(body, dict):
            raise ValueError("the smoke input must be a JSON object")
        # the outer envelope's fields, where the body does not speak for itself
        if "name" in req and "name" not in body:
            body["name"] = req["name"]
    if body is None:
        body = req
    if not isinstance(body, dict):
        raise ValueError("the request body must be an object")
    return body


def _check(body: Dict[str, Any]) -> Dict[str, Any]:
    """Every bound this worker enforces, named, before anything is built."""
    variant = str(body.get("variant", body.get("weight_set", args.variant)))
    if variant not in ("vanilla", "soluble"):
        raise ValueError(
            f"'variant' must be 'vanilla' or 'soluble', not {variant!r} "
            f"(the two weight sets the kit's PINS.json pins)"
        )
    num_seq = int(body.get("num_seq_per_target", body.get("num_sequences", 8)))
    batch = int(body.get("batch_size", num_seq))
    if num_seq < 1 or num_seq > MAX_SEQS:
        raise ValueError(f"'num_seq_per_target' must be between 1 and {MAX_SEQS}")
    if batch < 1 or batch > num_seq:
        raise ValueError(
            f"'batch_size' must be between 1 and num_seq_per_target ({num_seq})"
        )
    if num_seq % batch:
        raise ValueError(
            f"'num_seq_per_target' ({num_seq}) must be a whole number of batches "
            f"of 'batch_size' ({batch}); stock designs "
            f"num_seq_per_target // batch_size batches per temperature and "
            f"silently drops the remainder"
        )
    temps = body.get("sampling_temp", body.get("temperature", 0.1))
    temps = [temps] if isinstance(temps, (int, float, str)) else list(temps)
    try:
        temperatures = [float(t) for t in temps]
    except (TypeError, ValueError):
        raise ValueError("'sampling_temp' must be a number or a list of numbers")
    for t in temperatures:
        if not 0.0 < t <= 1.0:
            raise ValueError(
                f"'sampling_temp' must be in (0, 1]; got {t}. Upstream's default "
                f"is 0.1 and it divides the logits, so 0 is a division by zero."
            )
    # 0 is "unspecified" rather than "draw one": the smoke envelope sends
    # `seed: 0` to mean the provider decides, and stock's own `--seed 0` draws a
    # per-PROCESS seed, which a held process cannot reproduce for a caller. So
    # the default stands and nothing is drawn, ever.
    seed = int(body.get("seed") or 37)
    if seed < 0:
        raise ValueError("'seed' must be a non-negative integer (0 = unspecified)")
    return {
        "variant": variant,
        "num_seq_per_target": num_seq,
        "batch_size": batch,
        "temperatures": temperatures,
        "seed": seed,
    }


def _structure_text(body: Dict[str, Any], work: Path) -> Path:
    pdb = body.get("pdb") or body.get("structure") or body.get("pdb_text")
    path = body.get("pdb_path")
    if pdb and path:
        raise ValueError("give 'pdb' or 'pdb_path', not both")
    if path:
        src = Path(str(path)).expanduser()
        if not src.is_file():
            raise ValueError(f"'pdb_path' is not a file: {src}")
        return src
    if not pdb:
        raise ValueError("the request needs a structure: 'pdb' (text) or 'pdb_path'")
    if not isinstance(pdb, str):
        raise ValueError("'pdb' must be the text of a PDB file")
    if "ATOM" not in pdb:
        raise ValueError("'pdb' holds no ATOM record")
    dst = work / "input.pdb"
    dst.write_text(pdb, encoding="utf-8")
    return dst


def _predict_one(req: Dict[str, Any]) -> Dict[str, Any]:
    body = _request(req)
    opts = _check(body)
    t_start = time.time()
    with tempfile.TemporaryDirectory(prefix=f"{SLUG}-req-") as tmp:
        work = Path(tmp)
        pdb_path = _structure_text(body, work)

        # the kit's read-once parser, in the stock helper's position
        t0 = time.time()
        protein = FAST_PARSE.parse_pdb(os.fspath(pdb_path), ca_only=False)
        t_parse = time.time() - t0
        if not protein:
            raise ValueError(
                f"no chain could be parsed from {pdb_path.name}: the parser found "
                f"no ATOM lines it could read"
            )
        # parse_pdb answers a list of one entry per file, as the stock helper's
        # parsed.jsonl holds one object per file
        entry = protein[0] if isinstance(protein, list) else protein
        n_res = len(entry.get("seq", ""))
        if n_res == 0:
            raise ValueError("the parsed structure has no residues")
        if n_res > MAX_RESIDUES:
            raise ValueError(
                f"{n_res} residues exceeds this provider's ceiling of "
                f"{MAX_RESIDUES}. The ceiling is stock's dense featuriser, which "
                f"builds [B, L, K, 3H] tensors for every position at once; the "
                f"kit's lowmem transform lifts it and is a GPU line this provider "
                f"declined (see [kit] levers_declined)."
            )

        dataset = StructureDatasetPDB([entry], truncate=None, max_length=200000)
        proteins = list(dataset)
        if not proteins:
            raise ValueError(
                "stock's StructureDatasetPDB discarded the structure (bad "
                "characters, or a sequence/length mismatch)"
            )

        model, ck = _model(opts["variant"])
        _seed_as_stock(opts["seed"], ck["num_edges"])

        num_batches = opts["num_seq_per_target"] // opts["batch_size"]
        batch_copies = opts["batch_size"]
        temperatures = opts["temperatures"]
        out = work / "out"
        (out / "seqs").mkdir(parents=True, exist_ok=True)

        records: List[Dict[str, Any]] = []
        t_design0 = time.time()
        with torch.no_grad():
            for prot in proteins:  # == protein_mpnn_run.py:229
                batch_clones = [copy.deepcopy(prot) for _ in range(batch_copies)]
                (
                    X, S, mask, lengths, chain_M, chain_encoding_all,
                    chain_list_list, visible_list_list, masked_list_list,
                    masked_chain_length_list_list, chain_M_pos, omit_AA_mask,
                    residue_idx, dihedral_mask, tied_pos_list_of_lists_list,
                    pssm_coef, pssm_bias, pssm_log_odds_all, bias_by_res_all,
                    tied_beta,
                ) = tied_featurize(
                    batch_clones, DEVICE, None, None, None, None, None, None,
                    ca_only=False,
                )
                pssm_log_odds_mask = (pssm_log_odds_all > 0.0).float()
                name_ = batch_clones[0]["name"]

                # the native pass, protein_mpnn_run.py:309-315
                randn_1 = torch.randn(chain_M.shape, device=X.device)
                log_probs = model(
                    X, S, mask, chain_M * chain_M_pos, residue_idx,
                    chain_encoding_all, randn_1,
                )
                mask_for_loss = mask * chain_M * chain_M_pos
                native_score = _scores(S, log_probs, mask_for_loss).cpu().data.numpy()
                global_native_score = (
                    _scores(S, log_probs, mask).cpu().data.numpy()
                )

                designs: List[Dict[str, Any]] = []
                native_seq_out: Optional[str] = None
                for temp in temperatures:  # == :324
                    for j in range(num_batches):  # == :325
                        randn_2 = torch.randn(chain_M.shape, device=X.device)
                        sample_dict = model.sample(
                            X, randn_2, S, chain_M, chain_encoding_all, residue_idx,
                            mask=mask, temperature=temp, omit_AAs_np=OMIT_AAS_NP,
                            bias_AAs_np=BIAS_AAS_NP, chain_M_pos=chain_M_pos,
                            omit_AA_mask=omit_AA_mask, pssm_coef=pssm_coef,
                            pssm_bias=pssm_bias, pssm_multi=0.0,
                            pssm_log_odds_flag=False,
                            pssm_log_odds_mask=pssm_log_odds_mask,
                            pssm_bias_flag=False, bias_by_res=bias_by_res_all,
                        )
                        S_sample = sample_dict["S"]
                        log_probs = model(
                            X, S_sample, mask, chain_M * chain_M_pos, residue_idx,
                            chain_encoding_all, randn_2,
                            use_input_decoding_order=True,
                            decoding_order=sample_dict["decoding_order"],
                        )
                        mask_for_loss = mask * chain_M * chain_M_pos
                        scores = (
                            _scores(S_sample, log_probs, mask_for_loss)
                            .cpu().data.numpy()
                        )
                        global_scores = (
                            _scores(S_sample, log_probs, mask).cpu().data.numpy()
                        )
                        for b_ix in range(batch_copies):  # == :345
                            masked_chain_length_list = masked_chain_length_list_list[b_ix]
                            masked_list = masked_list_list[b_ix]
                            seq_recovery_rate = torch.sum(
                                torch.sum(
                                    torch.nn.functional.one_hot(S[b_ix], 21)
                                    * torch.nn.functional.one_hot(S_sample[b_ix], 21),
                                    axis=-1,
                                )
                                * mask_for_loss[b_ix]
                            ) / torch.sum(mask_for_loss[b_ix])
                            seq = _S_to_seq(S_sample[b_ix], chain_M[b_ix])
                            if b_ix == 0 and j == 0 and temp == temperatures[0]:
                                native_seq_out = _chain_join(
                                    _S_to_seq(S[b_ix], chain_M[b_ix]),
                                    masked_chain_length_list,
                                    masked_list,
                                )
                            designs.append(
                                {
                                    "T": temp,
                                    "sample": j * batch_copies + b_ix + 1,
                                    "sequence": _chain_join(
                                        seq, masked_chain_length_list, masked_list
                                    ),
                                    "score": _fmt4(scores[b_ix]),
                                    "global_score": _fmt4(global_scores[b_ix]),
                                    "seq_recovery": _fmt4(
                                        seq_recovery_rate.detach().cpu().numpy()
                                    ),
                                }
                            )
                sorted_masked = np.argsort(masked_list_list[0])
                records.append(
                    {
                        "name": name_,
                        "n_residues": int(X.shape[1]),
                        "designed_chains": [
                            masked_list_list[0][i] for i in sorted_masked
                        ],
                        "fixed_chains": [
                            visible_list_list[0][i]
                            for i in np.argsort(visible_list_list[0])
                        ],
                        "native_sequence": native_seq_out,
                        "native_score": _fmt4(native_score.mean()),
                        "global_native_score": _fmt4(global_native_score.mean()),
                        "designs": designs,
                    }
                )
        t_design = time.time() - t_design0

    return {
        "model": (
            "ProteinMPNN 8907e667 (stock loop, held resident) / "
            f"{opts['variant']}_model_weights v_48_020"
        ),
        "device": "cpu",
        "kit_mode": "off",
        "variant": opts["variant"],
        "seed": opts["seed"],
        "sampling_temp": temperatures,
        "num_seq_per_target": opts["num_seq_per_target"],
        "batch_size": opts["batch_size"],
        "structures": records,
        "n_designs": sum(len(r["designs"]) for r in records),
        "timing_s": {
            "parse": round(t_parse, 4),
            "design": round(t_design, 4),
            "total": round(time.time() - t_start, 4),
        },
        "rss_gib": round(_rss_gib(), 3),
        "peak_rss_gib": round(_peak_rss_gib(), 3),
    }


def _fmt4(x: Any) -> float:
    """stock's own print precision (np.format_float_positional, precision 4)."""
    return float(np.format_float_positional(np.float32(x), unique=False, precision=4))


def _chain_join(seq: str, masked_chain_length_list, masked_list) -> str:
    """stock's chain re-ordering and '/' joining, protein_mpnn_run.py:386-397."""
    start = end = 0
    parts = []
    for mask_l in masked_chain_length_list:
        end += mask_l
        parts.append(seq[start:end])
        start = end
    out = "".join(list(np.array(parts)[np.argsort(masked_list)]))
    l0 = 0
    for mc_length in list(np.array(masked_chain_length_list)[np.argsort(masked_list)])[:-1]:
        l0 += mc_length
        out = out[:l0] + "/" + out[l0:]
        l0 += 1
    return out


def _ready() -> Dict[str, Any]:
    return {
        "device": "cpu",
        "kit_mode": "off",
        "variants_held": sorted(_MODELS),
        "default_variant": args.variant,
        "mpnn_dir": MPNN_DIR,
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "weights_held_by": "worker",
        "max_residues": MAX_RESIDUES,
        "rss_gib": round(_rss_gib(), 3),
        "peak_rss_gib": round(_peak_rss_gib(), 3),
    }


_model(args.variant)
say(
    f"ready: stock ProteinMPNN held on the CPU, variant {args.variant}, "
    f"torch {torch.__version__} (cuda {torch.version.cuda}), "
    f"rss {_rss_gib():.2f} GiB"
)

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
