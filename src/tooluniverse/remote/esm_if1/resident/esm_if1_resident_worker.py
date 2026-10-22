"""ESM-IF1 held resident, answering one inverse-folding request at a time.

Run by the model's own interpreter, with the mode on the command line and NOT
in the environment::

    <model python> esm_if1_resident_worker.py --socket … --slug … --kit … --mode fast

**The activation shape.** This kit is argv-only -- the shape ef2inv and
af3_torch share and the one the shared ``kit_launch`` probe cannot describe. It
ships no autoload ``.pth`` (``opt/pyproject.toml``: "this kit ships no autoload
.pth (the mode is chosen on the command line; no import is hooked)"), there is
no ``esm_if1_opt._autoload`` module to import, and ``ESM_IF1_OPT`` is
documented as "the environment route of the mode (this command line and run.sh
only)". ``launch.py`` therefore strips that name from this process's
environment and passes the mode as ``--mode``; see its docstring.

**What the kit's ``fast`` tier actually is, and why a resident worker can hold
it.** One lever, ``batched_sampling``, and it is a pair of plain functions over
an already-built model:

    esm_if1_opt.batched.sample_batch(model, coords_list, temperature, device,
                                     partial_seq=None, steps=None)
    esm_if1_opt.batched.sample_complex_batch(model, complexes, chain,
                                             temperature, device)

Upstream's ``GVPTransformerModel.sample`` designs one backbone per call with a
batch of one hard-wired, and upstream's example script calls it once per
requested sequence. Those two functions run the same statements -- the kit's own
docstring cites ``gvp_transformer.py`` line by line, ``:102-105``, ``:108-110``,
``:119``, ``:126-136``, ``:137-140`` -- over B (backbone, sample) rows per
forward. Nothing is patched, shadowed or copied: this script is a different
script in the position ``esm_if1_opt/kit_design.py`` occupies, calling the kit's
functions in the order ``esm_if1_opt/batched.py``'s ``run()`` calls them, and
every step below cites the line of ``run()`` it mirrors.

The one thing ``run()`` does that this worker does differently is the part that
makes residency possible: ``run()`` parses, loads the model, seeds and samples
in one pass and then the process exits. Here the load happens once, at start-up,
and a request is the parse-seed-sample tail of it.

**Who holds the weights: the worker.** This is a decision and the fourth of the
four answers the standard records does not apply. Nothing in ``esm_if1_opt``
touches ``esm.pretrained`` -- the kit replaces no loader, installs no finder and
has no opinion about where the checkpoint comes from; ``run()`` calls
``esm.pretrained.esm_if1_gvp4_t16_142M_UR50()`` itself, exactly as upstream's
script does, once per process. So there is nothing for a memo of ours to
collide with (chai1's problem) and nobody else is holding anything
(boltzgen's). The ready line says ``weights_held_by=worker``.

What that buys, measured on this machine and recorded in ``provider.toml``: the
checkpoint is 1.7 GB read through ``torch.load`` and the model is 142M
parameters; the kit's own README puts start-up and checkpoint load at "≈5 s of
start-up and checkpoint load in either mode" per call, which a process that
exits after each request pays every time. On aarch64 CPU the read is the larger
share of it.

**This worker runs on the CPU, by measurement.** ``provider.toml``'s ``[gpu]``
section and ``environment/requirements.lock``'s header carry the evidence; the
short version is that the kit pins torch 2.4.0, the CUDA 12.4 cuBLAS such a
stack would load carries cubins for sm_50…sm_90 and **no PTX at all** (measured
with ``cuobjdump`` on the aarch64 wheel), and this card is sm_121. The device is
still chosen the way the kit chooses it -- ``torch.cuda.is_available()``, which
is upstream's own test (``sample_sequences.py:21-22``) -- so this same worker
drives a GPU on a host whose torch has one. It reports which it got.

**What is retained between requests, and what is not.**

* Retained: the model (eval, no grad), the alphabet, the kit's activation
  report, and the ``torch.hub`` cache entry symlinked to the verified
  checkpoint. That is all.
* Not retained: every tensor of a request. ``torch.inference_mode()`` wraps the
  sampling, ``torch.set_grad_enabled(False)`` is set before the model is built,
  and no graph can be retained because none is built. There are no CUDA graphs
  to drop a pool handle for (openfold3's second-request failure) and no compile
  trace to key (rfdiffusion3's gain).
* Upstream module state: checked by doing the thing genie3 made necessary --
  calling ``esm.pretrained.esm_if1_gvp4_t16_142M_UR50()`` TWICE in one process
  before this worker was written. The result is in ``provider.toml`` under
  ``[provider] verified_on``. Nothing upstream memoises a config the second
  build would trip over; the loader reads the checkpoint again and returns an
  independent model.
* **Nothing forks.** Upstream's ESM-IF1 path constructs no ``DataLoader``, no
  multiprocessing pool and no subprocess, so there is no ``num_workers`` to set
  to zero and no OpenMP pool a ``fork()`` could leave behind. boltzgen's rule
  ("a resident worker that has run any host-tensor work must not let a library
  fork") is therefore satisfied by there being no fork rather than by destroying
  the pool -- and ``OMP_NUM_THREADS = "1"`` is nonetheless declared in
  ``[kit.env]``, for an entirely different reason: one thread is **faster** here
  by 1.5x. The measurement and the reason are at ``torch.set_num_threads``
  below. Two providers can end up at the same setting through different
  arguments, and which argument it was decides whether the setting survives the
  next host.

One request at a time, by construction: ``worker_base.serve`` accepts and
answers serially.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser(description="ESM-IF1 resident inverse-folding worker")
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="esm_if1", help="provider slug, echoed in ping")
ap.add_argument("--kit", default="", help="the kit tree (esm_if1/ of the checkout)")
ap.add_argument(
    "--mode",
    default="fast",
    help="the kit mode: fast (batched_sampling) or off (upstream unchanged). "
    "Passed here and NOT through ESM_IF1_OPT -- see launch.py",
)
args = ap.parse_args()

T0 = time.time()

# ---------------------------------------------------------------- declared ceilings
# A declared input ceiling that the budget cannot cover is not a bound
# (progen2: 16 sequences x 1024 tokens is sane in each factor and costs 116.93
# GiB). The cost here is driven by the product of the rows in one forward pass
# and the encoder length, because the GVP encoder is run once per row and the
# decoder keeps an incremental state per row. Both numbers below are measured,
# not derived; provider.toml's [gpu] section carries the ladder they come from.
MAX_TOKENS = 1600  # the longest backbone (or concatenated complex) accepted
MAX_SAMPLES = 64  # the most sequences per request
# rows_per_forward x tokens. The ladder's top rung is 800 tokens at 2 rows;
# this admits 8 rows there and 32 rows at 200, and refuses the corner that the
# two ceilings above would otherwise permit together (64 x 1600 = 102,400).
MAX_ROW_TOKENS = 6400


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
    print(f"[esm_if1-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds ESM-IF1's pinned stack
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
            f"[esm_if1-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODE = (args.mode or "fast").strip().lower()
if args.kit:
    # run.sh exports MODEL_OPT on every command and configs/<card>.env sets it;
    # launch.py does too. Stating it again costs nothing and keeps a worker that
    # is started by hand working.
    os.environ.setdefault("MODEL_OPT", args.kit)

# The kit's own refusal if ESM_IF1_OPT disagrees with --mode would be a
# ModeConflict from four frames down. launch.py strips the name; if something
# else put it back, say so here rather than letting the kit's usage error
# surface as a protocol failure.
_inherited = (os.environ.get("ESM_IF1_OPT") or "").strip().lower()
if _inherited and _inherited != MODE:
    raise _refuse(
        f"[esm_if1-resident] ESM_IF1_OPT={_inherited} is in this process's "
        f"environment and disagrees with --mode {MODE}. The kit calls that a "
        f"usage error (modes.ModeConflict); launch.py strips the name, so "
        f"something set it after the launch -- unset it and restart the worker"
    )

# ----------------------------------------------------------------- the kit
# Statement one of every entry of this package is its core pin gate, which
# refuses by name with exit 3 before anything of opt_core is imported.
try:
    import esm_if1_opt
except ModuleNotFoundError as exc:
    raise _refuse(
        f"[esm_if1-resident] NOT ACTIVE: reason=kit_missing:esm_if1_opt "
        f"({exc}) on {sys.executable} -- run `tu remote setup esm_if1 --only kit`, "
        f"which runs the kit's own `bash run.sh install`"
    ) from None

try:
    # stack.enable(mode): `off` -> the stock route, inactive by definition;
    # `fast` -> active with its one lever. It raises ActivationError when
    # fair-esm or torch is not installed, and when a second mode is resolved in
    # one process. core_gate() runs inside it.
    KIT_REPORT = esm_if1_opt.enable(MODE)
except esm_if1_opt.ActivationError as exc:
    raise _refuse(
        f"[esm_if1-resident] NOT ACTIVE: reason=kit_activation_refused: {exc}"
    ) from None

from esm_if1_opt import batched, modes, stack  # noqa: E402

LEVERS = list(KIT_REPORT.get("levers_applied") or ())
ROUTE = KIT_REPORT.get("route") or modes.route_of(MODE)
say(
    f"kit esm_if1_opt {esm_if1_opt.__version__} mode={MODE} route={ROUTE} "
    f"active={KIT_REPORT.get('active')} levers={LEVERS or 'none'}"
)

# ------------------------------------------------------------- the checkpoint
# TORCH_HOME IS SET HERE, BEFORE ANYTHING STAGES OR LOADS, and it is the one
# line of this file that was written because a probe caught it rather than
# because the kit's source said so.
#
# `stack.stage_torch_home()` links the checkpoint into `stack.torch_home()`,
# which is `$TORCH_HOME` when set and `<MODEL_OPT_STATE>/torch_home` otherwise.
# `torch.hub` does not know about `MODEL_OPT_STATE`: it reads `TORCH_HOME` and
# falls back to `~/.cache/torch`. So with `MODEL_OPT_STATE` set and `TORCH_HOME`
# unset, the staging reports `hub_entry: linked` -- truthfully, about a
# directory torch will never look in -- and upstream's loader then DOWNLOADS 1.7
# GB into `~/.cache/torch/hub/checkpoints/`. Measured exactly that way before
# this line existed.
#
# The kit does the same thing for its own children and says so: `stack.kit_env`
# and `stack.stock_env` both do `env["TORCH_HOME"] = torch_home(env)`, and
# STOCK.md records that TORCH_HOME is "passed to every child as an absolute
# path". A resident worker is the child here, so it sets its own.
os.environ["TORCH_HOME"] = stack.torch_home()

# The kit's own staging: with ESM_IF1_WEIGHTS naming a local copy, the
# torch.hub cache entry becomes a symlink to it, so upstream's loader finds the
# file this provider verified and downloads nothing. The function "never raises
# on the checkpoint's content and never reads it" -- the verification is the
# weights step's, against [[weights.files]], and it has already happened.
STAGED = stack.stage_torch_home()
if STAGED.get("hub_entry") != "linked":
    raise _refuse(
        f"[esm_if1-resident] NOT ACTIVE: reason=weights_not_linked: "
        f"torch.hub's cache entry {stack.hub_entry()} is "
        f"'{STAGED.get('hub_entry')}', not 'linked' to "
        f"{STAGED.get('source')}. Upstream's loader reads that entry and "
        f"DOWNLOADS 1.7 GB when it is absent, or loads whatever is there when "
        f"it is a regular file -- neither of which this provider verified. "
        f"Set ESM_IF1_WEIGHTS to the checkpoint `tu remote setup esm_if1 "
        f"--only weights` certified, and remove any regular file at that cache "
        f"entry by hand (it is not deleted here: a truncated transfer and a "
        f"different checkpoint look alike)"
    )
say(f"weights {STAGED['file']} linked into {STAGED['torch_home']} ({STAGED['source']})")

# ------------------------------------------------------------------- the stack
import torch  # noqa: E402

# The second half of the same check, from torch's side rather than the kit's.
# `hub_entry: linked` is a statement about a directory; this asks the library
# that will do the reading which directory it is going to read.
_HUB = os.path.realpath(os.path.join(torch.hub.get_dir(), "checkpoints"))
_WANT = os.path.realpath(os.path.dirname(stack.hub_entry()))
if _HUB != _WANT:
    raise _refuse(
        f"[esm_if1-resident] NOT ACTIVE: reason=torch_hub_elsewhere: the "
        f"checkpoint is staged under {_WANT} and torch.hub will read {_HUB}. "
        f"Upstream's loader would download 1.7 GB into the second one. "
        f"TORCH_HOME is {os.environ.get('TORCH_HOME')!r}; unset it, or set it to "
        f"{os.path.dirname(_WANT)}"
    )

torch.set_grad_enabled(False)
# ONE THREAD, AND IT IS MEASURED RATHER THAN INHERITED. torch's default is
# os.cpu_count(), which on this host is 20, and 20 is the slowest setting
# tested. Min of three repeats, 64 residues x 2 samples, on a contended box
# (load average 29) and again pinned to the ten performance cores:
#
#   threads      1       2       4       8      20
#   all 20    8.66   12.59   13.88   13.07   13.91   s
#   cores 0-9 7.50    9.82    8.28    8.27   11.52   s
#
# and the ordering holds at 256 residues (57.21 s at one thread against 68.16
# at four). The reason is the shape of the work, not the host: ESM-IF1's decoder
# takes one sequential step per designed position, and a step is a 512-wide,
# 8-layer forward over at most a few hundred positions for a handful of rows --
# tensors small enough that the per-op thread barrier costs more than the
# arithmetic it divides. There is no large GEMM here for threads to win on.
#
# This is ALSO why `OMP_NUM_THREADS = "1"` is declared in [kit.env], and the
# reason is worth separating from boltzgen's: there it existed to stop a library
# forking a pool that `fork()` would not carry over, and here nothing forks at
# all. It is set because one thread is faster. The side effect is that this
# provider occupies one of twenty cores, which is a better neighbour than the
# default would have been.
#
# ESM_IF1_RESIDENT_THREADS overrides it for a host that measures otherwise.
THREADS = int(os.environ.get("ESM_IF1_RESIDENT_THREADS") or 1)
torch.set_num_threads(THREADS)

import esm  # noqa: E402
import esm.inverse_folding  # noqa: E402
import esm.inverse_folding.multichain_util  # noqa: E402

# sample_sequences.py:21-22 / :45-46, which batched.run() mirrors: the GPU when
# torch sees one, the CPU otherwise. `device=None` is what the kit passes its
# own sampler on the CPU route.
USE_CUDA = torch.cuda.is_available()
DEVICE = torch.device("cuda") if USE_CUDA else None
DEVICE_WORD = "cuda" if USE_CUDA else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE_WORD} threads={THREADS} esm={esm.__version__}"
)

_t = time.time()
# batched.run():  model, alphabet = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
#                model = model.eval()
#                if use_cuda: model = model.cuda()
MODEL, ALPHABET = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
MODEL = MODEL.eval()
if USE_CUDA:
    MODEL = MODEL.cuda()
BUILD_S = time.time() - _t
# The kit's own post-hoc check, run for the reason it exists: `cache_word()` is
# "hit when the torch.hub cache entry still resolves to the ESM_IF1_WEIGHTS
# file, miss when it does not (something replaced it -- a download)". A `miss`
# here means the model that is now resident was built from bytes this provider
# never verified, which is the one thing the weights step cannot see.
_CACHE = stack.cache_word()
if _CACHE != "hit":
    raise _refuse(
        f"[esm_if1-resident] NOT ACTIVE: reason=weights_replaced: after the "
        f"load, the kit's own cache_word() reads {_CACHE!r} rather than 'hit' -- "
        f"the torch.hub entry {stack.hub_entry()} no longer resolves to "
        f"{STAGED.get('source')}. The model in memory was built from bytes this "
        f"provider did not verify. Remove that entry by hand and re-run "
        f"`tu remote setup esm_if1 --only weights`"
    )
HOLDER = "worker"
N_PARAMS = sum(p.numel() for p in MODEL.parameters())
say(
    f"model resident on {DEVICE_WORD} in {BUILD_S:.1f}s "
    f"({N_PARAMS / 1e6:.0f}M parameters, weights_held_by={HOLDER} kit={MODE})"
)


def _peak_rss_gib() -> float:
    """The process's high-water resident set, in GiB.

    ru_maxrss is in KiB on Linux and is a HIGH-WATER MARK that never falls,
    which is the same semantics `peak_reserved_gib` has in six of the eight
    workers the standard counted: a host adding budgets up wants the worker's
    worst case, so this is deliberately not reset between requests and the
    ladder in provider.toml is therefore measured ascending in a fresh worker.
    """
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 2)


def _rss_gib() -> float:
    """The process's current resident set, in GiB (/proc/self/statm, pages)."""
    try:
        with open("/proc/self/statm", "r", encoding="ascii") as fh:
            pages = int(fh.read().split()[1])
        return round(pages * os.sysconf("SC_PAGE_SIZE") / 2**30, 2)
    except (OSError, ValueError, IndexError):
        return -1.0


# ------------------------------------------------------------------- requests
_SUFFIX = {"pdb": ".pdb", "cif": ".cif"}


def _request(req: dict) -> dict:
    """The request document: either the smoke/tool JSON, or a bare PDB/CIF text.

    A bare structure is accepted because `tu remote setup --only smoke` sends
    the smoke file's text verbatim and a future smoke may be a plain `.pdb`;
    everything else then takes its default.
    """
    text = req.get("input") or req.get("json") or req.get("structure")
    if not text:
        raise ValueError(
            "a request needs 'input': a JSON document with a 'structure' "
            "(PDB or mmCIF text) and optionally chain / num_samples / "
            "temperature / seed / batch_size / multichain_backbone"
        )
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        return {"structure": text, "structure_format": "pdb"}
    doc = json.loads(text)
    if not isinstance(doc, dict):
        raise ValueError("the input JSON must be one object, not a list")
    return doc


def _write_structure(doc: dict, work: Path) -> Path:
    """The backbone as a file, which is what upstream's loader takes.

    `esm.inverse_folding.util.load_structure` dispatches on the SUFFIX of the
    path ('.cif' -> pdbx, '.pdb' -> pdb) and raises UnboundLocalError on
    anything else, so the suffix is chosen here rather than inherited from a
    caller's filename. The file is written on every request, successful or not,
    which is why `[runtime] outputs` does not match it -- see provider.toml.
    """
    text = doc.get("structure")
    if not text:
        path = doc.get("structure_path")
        if not path:
            raise ValueError(
                "the request carries neither 'structure' (PDB/mmCIF text) nor "
                "'structure_path'"
            )
        src = Path(path).expanduser()
        if not src.is_file():
            raise ValueError(f"structure_path {src} is not a file")
        text = src.read_text()
        doc.setdefault(
            "structure_format", "cif" if src.suffix.lower() == ".cif" else "pdb"
        )
    fmt = str(doc.get("structure_format") or "pdb").lower().lstrip(".")
    if fmt not in _SUFFIX:
        raise ValueError(
            f"structure_format {fmt!r} is not one of {sorted(_SUFFIX)} -- "
            f"upstream's load_structure dispatches on the file suffix"
        )
    path = work / f"input{_SUFFIX[fmt]}"
    path.write_text(text)
    return path


def _predict_one(req: dict) -> dict:
    """One request: N sampled sequences for one backbone.

    The order is batched.run()'s, with the model already held:
      1. parse the input once, before anything else (run()'s PREPASS)
      2. torch.manual_seed(seed) -- run() does it once after the load; here it
         is once per request, which is what makes a held worker repeatable
      3. the forward batches of batched.batches(), each through the kit's
         sample_batch / sample_complex_batch under torch.inference_mode()
      4. a FASTA per backbone, written only when its S rows are all sampled
    """
    doc = _request(req)
    out_dir = Path(req["out_dir"]) / (req.get("name") or "esm_if1")
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = dict(req.get("options") or {})

    def pick(key, default):
        return opts[key] if key in opts else doc.get(key, default)

    chain = pick("chain", None)
    chain = None if chain in (None, "", "None") else str(chain)
    num_samples = int(pick("num_samples", 1))
    temperature = float(pick("temperature", 1.0))
    batch_size = int(pick("batch_size", batched.DEFAULT_BATCH))
    multichain = bool(pick("multichain_backbone", False))
    seed = int(
        pick(
            "seed",
            req.get("seed") if req.get("seed") is not None else batched.DEFAULT_SEED,
        )
    )

    # settings.check_values()'s own three refusals, in the kit's words.
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1 (got {batch_size})")
    if num_samples < 1:
        raise ValueError(f"num_samples must be >= 1 (got {num_samples})")
    if multichain and not chain:
        raise ValueError(
            "multichain_backbone needs chain: the chain to design (every chain "
            "of the file conditions it)"
        )
    if num_samples > MAX_SAMPLES:
        raise ValueError(
            f"num_samples {num_samples} is over this provider's declared "
            f"ceiling of {MAX_SAMPLES}; provider.toml [gpu] carries the budget "
            f"it is derived from"
        )

    work = out_dir
    struct_path = _write_structure(doc, work)

    t_parse = time.time()
    # batched.run()'s prepass, both routes, for the one structure a request
    # carries. keys[] is what the rows of one forward batch must share.
    if multichain:
        complexes, native_seqs = (
            esm.inverse_folding.multichain_util.extract_coords_from_complex(
                esm.inverse_folding.util.load_structure(os.fspath(struct_path))
            )
        )
        if chain not in complexes:
            raise ValueError(
                f"no chain {chain!r} in the structure (chains: "
                f"{', '.join(sorted(complexes))})"
            )
        coords = complexes
        native_seq = native_seqs[chain]
        designed_len = len(complexes[chain])
        tokens = sum(len(v) for v in complexes.values()) + 10 * (len(complexes) - 1)
        key = (tokens, designed_len)
    else:
        coords, native_seq = esm.inverse_folding.util.load_coords(
            os.fspath(struct_path), chain
        )
        designed_len = tokens = len(native_seq)
        key = tokens
    parse_s = time.time() - t_parse

    if tokens < 1:
        raise ValueError(
            f"the structure yielded {tokens} backbone residues; "
            f"load_coords keeps only N/CA/C of amino-acid residues"
        )
    if tokens > MAX_TOKENS:
        raise ValueError(
            f"{tokens} tokens is over this provider's declared ceiling of "
            f"{MAX_TOKENS}; the measured budget in provider.toml stops there"
        )
    rows_per_forward = min(batch_size, num_samples)
    if rows_per_forward * tokens > MAX_ROW_TOKENS:
        raise ValueError(
            f"{rows_per_forward} rows x {tokens} tokens = "
            f"{rows_per_forward * tokens} is over this provider's declared "
            f"ceiling of {MAX_ROW_TOKENS} row-tokens. Each ceiling alone is "
            f"sane and their product is what costs memory, so the bound is on "
            f"the product: lower batch_size (it only groups samples into one "
            f"forward pass; the sequences are the same distribution either way)"
        )

    # batched.run(): torch.manual_seed(int(seed)) once, before the first batch.
    torch.manual_seed(seed)
    seqs: list = [None] * num_samples
    t_sample = time.time()
    n_batches = 0
    with torch.inference_mode():
        for rows in batched.batches([key], num_samples, rows_per_forward):
            n_batches += 1
            if multichain:
                out = batched.sample_complex_batch(
                    MODEL, [coords for _ in rows], chain, temperature, DEVICE
                )
            else:
                out = batched.sample_batch(
                    MODEL, [coords for _ in rows], temperature, DEVICE
                )
            for (_, s), seq in zip(rows, out):
                seqs[s] = seq
    sample_s = time.time() - t_sample

    files: list = []
    complete = all(s is not None for s in seqs)
    if complete:
        # The kit's own layout and record format: <out>/seqs/<stem>.fasta with
        # records >sampled_seq_<i> (sample_sequences.py:37-38).
        seq_dir = out_dir / "seqs"
        seq_dir.mkdir(parents=True, exist_ok=True)
        fasta = seq_dir / f"{req.get('name') or 'esm_if1'}.fasta"
        batched.write_fasta(os.fspath(fasta), seqs)
        files.append(os.fspath(fasta))

    recovery = None
    if complete and native_seq:
        recovery = [
            round(
                sum(a == b for a, b in zip(native_seq, s)) / max(len(native_seq), 1), 4
            )
            for s in seqs
        ]

    body = {
        "out_dir": os.fspath(out_dir),
        "files": files,
        # The result. Empty when a backbone's rows were not all sampled, which
        # is what [runtime] output_keys branches on.
        "sequences": [s for s in seqs if s is not None] if complete else [],
        "native_seq": native_seq,
        "recovery": recovery,
        "chain": chain,
        "n_tokens": tokens,
        "designed_length": designed_len,
        "num_samples": num_samples,
        "temperature": temperature,
        "seed": seed,
        "batch_size": batch_size,
        "rows_per_forward": rows_per_forward,
        "n_batches": n_batches,
        "route": "multichain" if multichain else "singlechain",
        "device": DEVICE_WORD,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "kit_route": ROUTE,
        "kit_levers": LEVERS,
        "timing": {
            "parse_s": round(parse_s, 2),
            "sample_s": round(sample_s, 2),
            # Reported in `timing` as well as on its own key: this provider has
            # no VRAM figure, so the ladder a reviewer reads off an acceptance
            # run has to be visible where that run prints the timing.
            "peak_rss_gib": _peak_rss_gib(),
            "rss_gib": _rss_gib(),
            "threads": THREADS,
        },
        "peak_rss_gib": _peak_rss_gib(),
        # None on purpose, and not omitted: this is a CPU provider
        # ([gpu] policy = "none"), so there is no torch.cuda high-water mark to
        # report and a missing key would read as a worker that forgot.
        "peak_reserved_gib": (
            round(torch.cuda.max_memory_reserved() / 2**30, 2) if USE_CUDA else None
        ),
    }
    # Written on EVERY request, complete or not -- which is the point: a
    # provider that writes a record whatever happened must not let its
    # `outputs` glob match that record (boltzgen's design_spec.cif would have
    # passed a design-less run). `*.fasta` does not match `opt_manifest.json`
    # or `input.pdb`, and both of those are here on a failed request.
    record = {k: v for k, v in body.items() if k != "native_seq"}
    record["complete"] = complete
    (out_dir / "opt_manifest.json").write_text(json.dumps(record, indent=1))
    if not complete:
        raise RuntimeError(
            f"{sum(s is None for s in seqs)} of {num_samples} samples were not "
            f"produced for this backbone; nothing was written to seqs/ "
            f"(the kit's own `incomplete=k/n`, exit 1)"
        )
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE_WORD,
        "threads": THREADS,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "kit_route": ROUTE,
        "kit_levers": LEVERS,
        "esm_version": esm.__version__,
        "torch_version": torch.__version__,
        "parameters_m": round(N_PARAMS / 1e6, 1),
        "max_tokens": MAX_TOKENS,
        "max_samples": MAX_SAMPLES,
        "max_row_tokens": MAX_ROW_TOKENS,
        "peak_rss_gib": _peak_rss_gib(),
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
