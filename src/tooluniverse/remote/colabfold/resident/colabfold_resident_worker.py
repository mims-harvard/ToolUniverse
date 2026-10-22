#!/usr/bin/env python
"""ColabFold resident worker -- builds AlphaFold2-Multimer once, folds many times.

Runs in the MODEL's environment (CPython 3.11, jax/jaxlib 0.5.3 +
jax-cuda12-plugin, colabfold 1.6.1 and alphafold-colabfold 2.3.13). It imports
nothing from ToolUniverse: ``protocol.py`` and ``worker_base.py`` are loaded by
path, which is the whole reason the two environments can hold conflicting
stacks.

THE MSA IS THE CALLER'S, AND THAT IS STRUCTURAL RATHER THAN A POLICY
--------------------------------------------------------------------
ColabFold's usual way to get an alignment is a remote MMseqs2 API. This worker
cannot reach it, and not because it was told not to: upstream's own branch in
``colabfold.batch.run`` is ``if a3m_lines is None: get_msa_and_templates(...)``
(the server) ``else: unserialize_msa(...)`` (no network), and
``colabfold.input.get_queries`` fills ``a3m_lines`` for exactly one input shape
-- a ``.a3m`` file. This worker only ever has an a3m, so it only ever takes the
second branch, and it calls ``unserialize_msa`` directly rather than ``run()``.
``run_mmseqs2`` is imported inside ``get_msa_and_templates`` and nowhere else,
so it is never even imported here.

Templates are refused by name for the same kind of reason: for an a3m input the
only template route upstream offers also calls ``run_mmseqs2`` (for the template
hits), and the local alternative wants an hhsearch database nothing in this
provider declares.

WHY NOT ``colabfold.batch.run``
-------------------------------
Two reasons, and both are the standard's own findings arriving in one function:

1. **It writes before it predicts.** ``run()`` writes ``config.json``, a bibtex
   file, ``<job>.a3m`` and a coverage PNG before inference, and then catches its
   own per-query exceptions (``except Exception: ... continue`` around the MSA
   step and the feature step, ``except RuntimeError: ... continue`` around the
   prediction) and returns normally. That is openfold3's "Failed Queries: 1"
   and boltzgen's ``design_spec.cif`` in one place. This worker's first write of
   any request is the PDB of a finished prediction, and an exception propagates.
2. **It rebuilds the model.** ``load_models_and_params`` is called inside
   ``run()``, so a per-request ``run()`` would re-read 1.86 GB of parameters and
   re-trace the model every time -- which is the cost residency exists to
   remove. The kit does not memoise it either: its ``weights.py`` is a DIGEST
   memo for the parameter check, not a parameter cache.

The consequence for ``[kit] mode`` is in provider.toml: this kit applies its
levers by patching ``colabfold.batch.run`` at the moment it is called, so a
worker that does not call ``run()`` would report a mode and run stock. ``off``
is the only honest mode for this shape, and under ``off`` nothing replaces
upstream's loader, which is why this worker may legitimately hold the weights.

WHAT IS HELD
------------
* **The parameters.** Five ``params_model_{1..5}_multimer_v3.npz``, 373 MB each,
  read once by ``get_model_haiku_params`` instead of once per request.
* **The traced model.** ``load_models_and_params`` builds ONE
  ``model.RunModel`` for the multimer path (``models_need_compilation = [3]``)
  and swaps the other four parameter sets into it, which is upstream's own
  trick for not recompiling. Held here, that trace is paid once per worker.
* **The XLA executable per query length** (see PADDING below) and jax's
  persistent compilation cache directory, which is the only one of these that
  survives a restart.
* **7.5 s of imports** (tensorflow, jax, haiku, colabfold, alphafold), measured
  on this host.

PADDING: THERE ISN'T ANY ON THIS PATH
------------------------------------
``predict_structure`` pads only the monomer path -- its ``if seq_len < pad_len:
pad_input(...)`` sits inside the ``else`` of ``if "multimer" in model_type``,
and ``run()``'s own comment at the multimer branch is
``# TODO: add pad_input_mulitmer()``. This provider runs the multimer
parameters, so every distinct total query length is its own XLA compilation and
there is no bucket to amortise it over. The reply says ``padding = "none"`` and
``padded_length = <seq_len>`` so nobody reads an af3_jax-style bucket into a
number that has none.

The MSA axis IS padded, by upstream, to the model config's ``num_msa`` /
``num_extra_msa`` (508 / 2048 for multimer v3, via
``process_multimer_features(..., min_num_seq=max_seq + 4)``), so alignment DEPTH
does not change a shape.

ONE DELIBERATE DEVIATION FROM ``run()``, STATED BECAUSE IT IS INVISIBLE
----------------------------------------------------------------------
``run()`` shrinks ``max_seq`` to the actual alignment depth when it has exactly
one query (``max_seq = min(num_seqs, max_seq)``). That is a sound optimisation
for a one-shot CLI with a shallow MSA and a trap for a resident worker: it would
make every distinct alignment depth a separate model build. This worker keeps
the model-type defaults (508 / 2048), so the held model serves any depth, and
reports ``max_seq`` / ``max_extra_seq`` in every reply. A caller who wants the
shrink can ask for it per request (``max_seq`` in ``options``) and pays one
rebuild.

PEAK MEMORY UNDER JAX -- READ THIS BEFORE COMPARING THE NUMBER
--------------------------------------------------------------
There is no torch here, so ``peak_reserved_gib`` cannot come from
``torch.cuda.max_memory_reserved``. It is
``jax.local_devices()[0].memory_stats()["peak_pool_bytes"]`` -- the BFC pool's
high-water mark, the analogue of torch's *reserved*. ``peak_bytes_in_use`` is
the analogue of *allocated* and comes back as ``peak_in_use_gib``.
``peak_bytes_reserved`` reads 0 on this stack, exactly as it does on af3_jax's
(in XLA "reserved" means held OUTSIDE the pool), and reporting the field whose
name matches would have reported zero for every request forever. Measured here
with one 2048x2048 matmul: in_use 150,994,944 / pool 153,092,096 / reserved 0.

This worker does NOT reset peak statistics between requests, which the standard
asks of a new provider: a host adding budgets up needs the worker's worst case.
JAX offers no reset for ``peak_pool_bytes`` in any case.

NOTHING OF OURS FORKS, AND THE CHILDREN THAT DO EXIST WERE LOOKED AT. With no
MSA search, no templates and no relaxation, the request path contains no
``multiprocessing``, no ``ProcessPoolExecutor`` and no ``os.fork``. ColabFold's
two fork sites are ``colabfold.download`` (the parameter fetch, which this
worker never calls) and ``relax_me`` (OpenMM, reachable only through
``num_relax > 0``, which this worker refuses by name).

Inspected rather than argued: during a compiling request this worker's
``/proc/<pid>/task/*/children`` held eight processes, every one of them
``nvidia/cuda_nvcc/bin/ptxas`` on a temporary file -- XLA assembling PTX in
parallel, exec'd rather than forked, holding no CUDA context and no model. That
is also why ``nvidia-cuda-nvcc-cu12`` is in the lock: the assembler this
provider needs is a pip package, not a host CUDA install. (163 threads, 2.9 GB
RSS, at the same moment.)

NOTHING DOWNLOADS, STRUCTURALLY. ``download_alphafold_params`` is called from
``colabfold.batch.main()`` and from nowhere else -- not ``run()``, not
``load_models_and_params``, not ``get_model_haiku_params``. This worker does not
call ``main()``. It also checks the marker file at build, because a parameters
directory without it is one from which upstream's CLI *would* fetch 2 GB.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SLUG = "colabfold"

# The only parameter set this provider has digests for, and the reason it is
# forced rather than resolved: `--model-type auto` sends a single-chain query to
# `alphafold2_ptm`, whose parameters the kit does not pin and does not fetch, and
# upstream would then download them AT REQUEST TIME. AlphaFold-Multimer on one
# chain is a supported configuration of upstream's own feature builder.
MODEL_TYPE = "alphafold2_multimer_v3"
# The marker whose presence is what stops `colabfold_batch` fetching
# (`colabfold.download.download_alphafold_params` returns early if and only if
# it exists). Checked at build so that a directory which would trigger a
# run-time download is refused before a request arrives.
MARKER = "params/download_complexes_multimer_v3_finished.txt"
# upstream's own numbers for this model type (`colabfold.batch.run`'s table:
# "508 2048 = alphafold-multimer_v3 (models 1,2,3)"). Kept at the defaults
# rather than shrunk per request -- see the module docstring.
DEFAULT_MAX_SEQ = 508
DEFAULT_MAX_EXTRA_SEQ = 2048
# THE ONE NUMERICS DEVIATION FROM UPSTREAM'S DEFAULT, and it is upstream's own
# parameter rather than a patch: `colabfold.batch.run`'s `use_bfloat16`, threaded
# to `load_models_and_params` and from there to
# `model_config.model.global_config.bfloat16`. Upstream's default is True. On
# this card, with this kit's pinned jax, True does not COMPILE -- it aborts the
# process:
#
#     Unsupported conversion from bf16 to f16
#     LLVM ERROR: Unsupported rounding mode for conversion.
#
# WHAT THAT IS, named rather than guessed. Both strings live in
# `jax_plugins/xla_cuda12/xla_cuda_plugin.so`, next to "Unsupported rounding
# mode for conversion to fp8:" -- they are LLVM's NVPTX instruction selector
# refusing to select a `cvt` for one dtype pair on this target, inside the LLVM
# that jaxlib 0.5.3 bundles. It is a COMPILE failure of the whole module
# (`module_0189.jit_apply_fn`, which is the model's forward pass): the dump stops
# at `before_optimizations.txt` with no PTX and no LLVM IR beside it, the abort
# is uncatchable, and there is no Python traceback.
#
# WHY bf16 AND f16 MEET AT ALL -- the part no inventory would predict. ColabFold
# keeps the RECYCLE STATE in float16 to save host memory: `model.py:153` is
# `zeros = lambda shape: np.zeros(shape, dtype=np.float16)` and `model.py:170`
# casts every output of a recycle iteration back with
# `np.asarray(v, np.float16)`. So the forward pass takes `f16[L,256]` and
# `f16[L,L,128]` as parameters (confirmed in the dumped HLO: those two are the
# ONLY f16 values in a 17,010-line module) and immediately converts them up
# (`modules_multimer.py:455`), while every activation in the trunk is bf16 under
# the global config. f16 and bf16 therefore meet at the recycle boundary of a
# model nobody would describe as mixed-precision between those two types.
#
# AND IT IS NOT THE OBVIOUS CONVERT. `jax.jit(lambda a: (a * a).astype(f16))`
# over a real bf16 device array compiles and runs correctly on this card, so a
# bf16->f16 conversion per se is selectable; what the model asks for is the same
# conversion under a rounding mode this LLVM has no pattern for. The kit measured
# this stock path on an H100 with the same jax, so the difference is the target,
# not the code.
#
# `use_bfloat16=False` is the switch upstream already offers for the activation
# dtype, so f16 then meets f32 -- a pair LLVM selects without complaint -- and
# the model folds. It is a real cost and it is declared in provider.toml: f32
# activations in the trunk, measured on this host at the ladder's rungs. It is
# not exposed to callers, deliberately: an abort cannot be caught, so a request
# that asked for bf16 would take the worker down rather than fail, and a
# provider that lets a request kill its own process has no refusal to report.
USE_BFLOAT16 = False
# upstream's own defaults for the knobs this worker exposes
# (`colabfold.batch.main`'s argparse and `run`'s signature).
DEFAULT_NUM_MODELS = 5
DEFAULT_NUM_SEEDS = 1
DEFAULT_RANDOM_SEED = 0
MAX_CHAINS = 16
# Everything `colabfold.batch` would set for itself at import if it were unset,
# and one more. The first two are the kit's own documented requirement ('Stock
# exceptions' in STOCK.md): left unset, `colabfold.batch` writes
# TF_FORCE_UNIFIED_MEMORY=1 and XLA_PYTHON_CLIENT_MEM_FRACTION=4.0 at its module
# body -- CUDA unified memory with a 4x oversubscribed pool, which the kit
# measured as not making progress on this stack at all. The third is this
# provider's, and provider.toml's [kit.env] explains it: without it jax
# preallocates MEM_FRACTION of the card at the first allocation and every peak
# this worker reported would be a measurement of that preallocation (91.22 GiB
# against 0.14 for one matmul, measured on this host).
ENV_DEFAULTS = (
    ("TF_FORCE_UNIFIED_MEMORY", "0"),
    ("XLA_PYTHON_CLIENT_MEM_FRACTION", "0.95"),
    ("XLA_PYTHON_CLIENT_PREALLOCATE", "false"),
)


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    `raise SystemExit("text")` would print the text and exit **1**, which the
    standard reserves for "failed" -- a distinction a caller branches on, and
    the whole point of a named refusal is that a caller can.
    """
    sys.stderr.write(str(message).rstrip("\n") + "\n")
    sys.stderr.flush()
    return SystemExit(3)


def _load_worker_base():
    override = os.environ.get("TOOLUNIVERSE_REMOTE_WORKER_BASE")
    path = Path(override) if override else None
    if path is None or not path.is_file():
        raise _refuse(
            "TOOLUNIVERSE_REMOTE_WORKER_BASE must point at "
            "remote_resident/worker_base.py; this worker never imports "
            "tooluniverse"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _say(msg: str) -> None:
    print(f"[{SLUG}-resident] {msg}", flush=True)


def _number(value):
    """A JSON-safe float from a numpy scalar, bool or NaN."""
    if value is None:
        return None
    try:
        out = float(value)
        return None if math.isnan(out) else round(out, 4)
    except (TypeError, ValueError):
        return None


class Engine:
    """Everything held between requests."""

    def __init__(self, args):
        self.args = args
        self.mode = args.mode
        self.data_dir = os.path.abspath(os.path.expanduser(args.data_dir))
        self.cache_dir = os.path.abspath(os.path.expanduser(args.cache_dir))
        self.build_s = None
        self.engine_builds = 0
        self.config_rebuilds = 0
        self.requests = 0
        self.lengths_seen = []
        self._runners = None
        self._runner_key = None
        self._device = None
        self._modules = {}

    # -------------------------------------------------------------- building
    def build(self) -> None:
        t0 = time.time()
        if self.mode != "off":
            # The kit applies its levers by patching `colabfold.batch.run` at
            # the moment it is called (colabfold_opt/_autoload.py arms a finder
            # on `colabfold.batch` and `stack.hook_run` wraps `run`). This
            # worker does not call `run` -- it holds the model that `run` would
            # rebuild -- so a kit mode here would report itself and change
            # nothing. Reporting a mode that did not engage is the one thing
            # this kit's own hook exists to prevent.
            raise _refuse(
                f"[{SLUG}-resident] --mode {self.mode!r}: this worker implements "
                f"the kit's stock route only. colabfold_opt's levers are applied "
                f"by a hook on colabfold.batch.run, which a resident worker does "
                f"not call (it holds the model that run() rebuilds per call); "
                f"engaging them would mean one load_models_and_params per "
                f"request, which is the cost residency removes. provider.toml's "
                f"[kit] section has the measurement."
            )

        params = os.path.join(self.data_dir, "params")
        if not os.path.isdir(params):
            raise _refuse(
                f"[{SLUG}-resident] --data-dir {self.data_dir} holds no params/ "
                f"directory; it must be the parameters root "
                f"(<COLABFOLD_OPT_DATA_DIR>/params/params_model_*_multimer_v3.npz). "
                f"Run `tu remote setup {SLUG} --only weights`"
            )
        missing = [
            n
            for n in [f"params/params_model_{i}_multimer_v3.npz" for i in range(1, 6)]
            if not os.path.isfile(os.path.join(self.data_dir, n))
        ]
        if missing:
            raise _refuse(
                f"[{SLUG}-resident] the {MODEL_TYPE} parameters are incomplete "
                f"under {self.data_dir}: {', '.join(missing)}. "
                f"Run `tu remote setup {SLUG} --only weights`"
            )
        if not os.path.isfile(os.path.join(self.data_dir, MARKER)):
            # Not pedantry: upstream's CLI treats this file as "the parameters
            # are here" and fetches 2 GB from the network when it is absent. A
            # provider that must contact nothing at request time refuses a
            # parameters directory that would make upstream try.
            raise _refuse(
                f"[{SLUG}-resident] {MARKER} is absent under {self.data_dir}. "
                f"colabfold.download.download_alphafold_params returns early if "
                f"and only if that marker exists, so a parameters directory "
                f"without it is one from which upstream would FETCH at run time "
                f"-- which this provider must never do. "
                f"Run `tu remote setup {SLUG} --only weights`"
            )

        # Before any import of colabfold or jax. `colabfold.batch`'s module body
        # sets two of these itself when they are unset, to values this stack
        # cannot run (see ENV_DEFAULTS), and jax reads the third at its first
        # allocation.
        for name, value in ENV_DEFAULTS:
            os.environ.setdefault(name, value)

        from colabfold.batch import (  # noqa: E402
            generate_input_feature,
            predict_structure,
            unserialize_msa,
        )
        from colabfold.alphafold.models import load_models_and_params  # noqa: E402
        from colabfold.input import get_queries  # noqa: E402
        import jax  # noqa: E402

        # `main()` does this; nothing else does, so a worker that skips main()
        # must do it itself -- and before the first compilation, or the
        # persistent cache is simply never consulted. This is the only one of
        # the held things that survives a restart, which is why it is not
        # optional here.
        jax_cache = os.path.join(self.cache_dir, "jax")
        os.makedirs(jax_cache, exist_ok=True)
        jax.config.update("jax_compilation_cache_dir", jax_cache)

        devices = jax.local_devices(backend="gpu")
        if not devices:
            raise _refuse(
                f"[{SLUG}-resident] jax reports no GPU device "
                f"(default_backend={jax.default_backend()!r}); this provider "
                f'declares [gpu] policy = "required"'
            )
        self._device = devices[0]

        self._modules = {
            "jax": jax,
            "get_queries": get_queries,
            "unserialize_msa": unserialize_msa,
            "generate_input_feature": generate_input_feature,
            "predict_structure": predict_structure,
            "load_models_and_params": load_models_and_params,
        }

        # Build the default engine now rather than on the first request, so that
        # `build_s` means what it says and a request's timing is the request's.
        self._ensure_runners(self._default_key())

        self.build_s = round(time.time() - t0, 2)
        _say(
            f"ready device={self._device.device_kind} cc={self.compute_capability} "
            f"jax={jax.__version__} mode={self.mode} weights_held_by=worker "
            f"model_type={MODEL_TYPE} params={self.data_dir} "
            f"engine={self._runner_key} models_held={len(self._runners)} "
            f"bfloat16={USE_BFLOAT16} "
            f"jit_cache={jax_cache} build_s={self.build_s}"
        )

    def _default_key(self) -> tuple:
        return (
            DEFAULT_NUM_MODELS,
            None,  # num_recycles: upstream's config default (20, early stop 0.5)
            None,  # recycle_early_stop_tolerance
            DEFAULT_MAX_SEQ,
            DEFAULT_MAX_EXTRA_SEQ,
            "multimer",  # rank_by, upstream's own choice for a complex
        )

    def _ensure_runners(self, key: tuple) -> bool:
        """Hold the model runners for ``key``; True when they were rebuilt.

        EVERY FIELD OF THE KEY IS COMPILE-TIME. `load_models_and_params` bakes
        the recycle count, the early-stop tolerance, the MSA widths and the
        ranking metric into `model_config` before tracing, so changing one needs
        a new RunModel and a fresh XLA compilation. Requests that keep the
        defaults never trigger it.

        THIS PATH IS THE ONE THE FOUR-IDENTICAL-REQUEST TEST CANNOT SEE, which
        is why it was exercised deliberately before this worker was written:
        upstream's builder was called twice in one process -- with two different
        keys -- and checked for the genie3 failure (a module-level mutable config
        that permits one build per process). It does not have it:
        `config.model_config` deep-copies its CONFIG dict per call
        (`copy.deepcopy(CONFIG_MULTIMER)`), so a second build is a second
        independent config. Measured, not read: two builds, two traces, two
        predictions, in one process.
        """
        if self._runners is not None and self._runner_key == key:
            return False
        rebuilt = self._runners is not None
        if rebuilt:
            self.config_rebuilds += 1
            _say(
                f"engine change {self._runner_key} -> {key}: rebuilding the model "
                f"runners (a fresh parameter read and XLA compilation follow)"
            )
            # Drop the old parameters before allocating new ones: five 373 MB
            # device arrays per engine, and holding two sets would double a
            # budget this manifest declares.
            self._runners = None
        num_models, recycles, tolerance, max_seq, max_extra_seq, rank_by = key
        self._runners = self._modules["load_models_and_params"](
            num_models=num_models,
            use_templates=False,  # refused by name in predict(); see the docstring
            num_recycles=recycles,
            recycle_early_stop_tolerance=tolerance,
            model_order=[1, 2, 3, 4, 5],
            model_type=MODEL_TYPE,
            data_dir=Path(self.data_dir),
            rank_by=rank_by,
            max_seq=max_seq,
            max_extra_seq=max_extra_seq,
            # Not upstream's default, and the reason is a compile abort rather
            # than a preference -- see USE_BFLOAT16 at the top of this file.
            use_bfloat16=USE_BFLOAT16,
        )
        self._runner_key = key
        self.engine_builds += 1
        return rebuilt

    @property
    def compute_capability(self) -> str:
        try:
            return str(self._device.compute_capability)
        except Exception:  # noqa: BLE001 - informational only
            return "?"

    # ------------------------------------------------------------- measuring
    def memory(self) -> dict:
        try:
            stats = self._device.memory_stats() or {}
        except Exception:  # noqa: BLE001 - a missing stat must not fail a fold
            return {}
        gib = 1024.0**3
        out = {}
        if stats.get("peak_pool_bytes") is not None:
            out["peak_reserved_gib"] = round(stats["peak_pool_bytes"] / gib, 2)
        if stats.get("peak_bytes_in_use") is not None:
            out["peak_in_use_gib"] = round(stats["peak_bytes_in_use"] / gib, 2)
        if stats.get("bytes_limit") is not None:
            out["bytes_limit_gib"] = round(stats["bytes_limit"] / gib, 2)
        # Reported verbatim so a reader can see for themselves that the field
        # whose NAME says "reserved" is not the one to use.
        out["peak_bytes_reserved"] = stats.get("peak_bytes_reserved")
        out["memory_source"] = "jax.local_devices()[0].memory_stats()"
        return out

    # -------------------------------------------------------------- folding
    def predict(self, req: dict) -> dict:
        t0 = time.time()
        self.requests += 1

        text = req.get("input")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "'input' must be the text of an a3m: either a plain a3m (one "
                "chain, the file is its unpaired MSA) or ColabFold's complex "
                "dialect, whose first line is '#<len1>,<len2>\\t<card1>,<card2>'. "
                "This provider builds no alignment and contacts no MSA server."
            )
        options = req.get("options") or {}
        for forbidden, why in (
            (
                "use_templates",
                "for an a3m input upstream's only template route calls the "
                "MMseqs2 server for its hits, and the local alternative needs an "
                "hhsearch database this provider does not declare",
            ),
            (
                "num_relax",
                "amber relaxation runs OpenMM in a forked child, which a "
                "resident worker that has already run host-tensor work must not "
                "allow (STANDARD section 14)",
            ),
            (
                "msa_mode",
                "there is one MSA mode here and it is 'the caller's a3m'; a mode "
                "that searched would contact a network service at request time",
            ),
            (
                "use_bfloat16",
                "upstream's bf16 activations do not COMPILE on this card with "
                "this kit's pinned jax -- LLVM's NVPTX selector aborts the "
                "process with 'Unsupported rounding mode for conversion' where "
                "the bf16 trunk meets ColabFold's float16 recycle state. An "
                "abort cannot be caught, so honouring this would take the worker "
                "down instead of failing the request. See USE_BFLOAT16 in this "
                "worker and [gpu] in provider.toml",
            ),
        ):
            if options.get(forbidden):
                raise ValueError(f"'{forbidden}' is not available: {why}.")

        num_models = int(options.get("num_models", DEFAULT_NUM_MODELS))
        if not 1 <= num_models <= 5:
            raise ValueError("'num_models' must be between 1 and 5.")
        num_seeds = int(options.get("num_seeds", DEFAULT_NUM_SEEDS))
        if not 1 <= num_seeds <= 5:
            raise ValueError("'num_seeds' must be between 1 and 5.")
        # The same product bound the MCP server applies, enforced here because a
        # socket caller does not go through it: five (model, seed) passes at the
        # 400-residue envelope were measured at 1736 s against this provider's
        # 3600 s request_timeout_s.
        if num_models * num_seeds > 5:
            raise ValueError(
                f"num_models x num_seeds is {num_models * num_seeds}; this "
                f"provider allows 5, which is upstream's own default. Each pair "
                f"is one full forward pass of the held model, and five at the "
                f"400-residue envelope take 1736 s against a 3600 s request "
                f"timeout. Send several requests with different seeds."
            )
        recycles = options.get("num_recycles")
        recycles = None if recycles is None else int(recycles)
        if recycles is not None and not 1 <= recycles <= 48:
            raise ValueError("'num_recycles' must be between 1 and 48.")
        tolerance = options.get("recycle_early_stop_tolerance")
        tolerance = None if tolerance is None else float(tolerance)
        # BOUNDED AT THE MODEL TYPE'S OWN WIDTHS, not left open. These two are
        # the MSA axes of every shape in the model, so a caller who raised them
        # would move the memory envelope the budget was measured at without
        # changing the length the server's own ceiling checks -- progen2's
        # failure, where two individually sane ceilings multiplied into a
        # 116.93 GiB request. Lowering them is allowed (it is upstream's own
        # one-query optimisation, at the price of one rebuild); raising them is
        # refused by name.
        max_seq = int(options.get("max_seq", DEFAULT_MAX_SEQ))
        max_extra_seq = int(options.get("max_extra_seq", DEFAULT_MAX_EXTRA_SEQ))
        if not 1 <= max_seq <= DEFAULT_MAX_SEQ:
            raise ValueError(
                f"'max_seq' must be between 1 and {DEFAULT_MAX_SEQ}, which is "
                f"{MODEL_TYPE}'s own num_msa and the width this provider's VRAM "
                f"budget was measured at."
            )
        if not 1 <= max_extra_seq <= DEFAULT_MAX_EXTRA_SEQ:
            raise ValueError(
                f"'max_extra_seq' must be between 1 and {DEFAULT_MAX_EXTRA_SEQ}, "
                f"which is {MODEL_TYPE}'s own num_extra_msa and the width this "
                f"provider's VRAM budget was measured at."
            )
        seed = req.get("seed")
        random_seed = int(seed) if isinstance(seed, int) and not isinstance(seed, bool) else DEFAULT_RANDOM_SEED

        name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(req.get("name") or "query"))[:64] or "query"
        out_dir = req.get("out_dir") or tempfile.mkdtemp(prefix=f"{SLUG}-out-")
        os.makedirs(out_dir, exist_ok=True)

        get_queries = self._modules["get_queries"]
        unserialize_msa = self._modules["unserialize_msa"]
        generate_input_feature = self._modules["generate_input_feature"]
        predict_structure = self._modules["predict_structure"]

        # PARSING IS UPSTREAM'S. The a3m is written to a file and handed to
        # `get_queries`, which is the function `colabfold_batch` itself calls:
        # it returns the query, the a3m lines and `is_complex`, computed from
        # the dialect's own header. Re-deriving any of that here would mean two
        # parsers that drift, and the dialect's complex half (aligned-column
        # chain lengths and cardinalities) is not a thing to re-implement.
        with tempfile.TemporaryDirectory(prefix=f"{SLUG}-in-") as indir:
            a3m_path = Path(indir) / f"{name}.a3m"
            a3m_path.write_text(text)
            queries, is_complex = get_queries(a3m_path)
        if not queries:
            raise ValueError("the a3m held no sequence.")
        _, query_sequence, a3m_lines, _ = queries[0]
        if a3m_lines is None:
            # Unreachable through get_queries for a .a3m, and asserted anyway:
            # `a3m_lines is None` is precisely the branch in which upstream
            # calls the MMseqs2 server, and this provider must never be one
            # refactor away from it.
            raise ValueError(
                "the input parsed to a query with no alignment, which is the "
                "branch upstream fills from the MMseqs2 server. Refused."
            )

        (
            unpaired_msa,
            paired_msa,
            query_seqs_unique,
            query_seqs_cardinality,
            template_features,
        ) = unserialize_msa(a3m_lines, query_sequence)

        chains = int(sum(query_seqs_cardinality))
        if chains > MAX_CHAINS:
            raise ValueError(f"at most {MAX_CHAINS} chains per query; this one has {chains}.")
        sequence_lengths = sum(
            [[len(s)] * n for s, n in zip(query_seqs_unique, query_seqs_cardinality)], []
        )
        seq_len = int(sum(sequence_lengths))
        # BOTH HALVES, because reporting one of them as "the MSA depth" is
        # misleading in this dialect: a complex a3m whose rows carry amino acids
        # in two or more chains is sorted into the PAIRED MSA and leaves the
        # unpaired one at a single row. Measured: an 8-row two-chain alignment
        # arrives as 9 paired rows and 1 unpaired row per chain.
        def _rows(msas):
            return max((len(m.splitlines()) // 2 for m in (msas or []) if m), default=0)

        unpaired_rows = _rows(unpaired_msa)
        paired_rows = _rows(paired_msa)
        msa_rows = max(unpaired_rows, paired_rows)

        rank_by = "multimer" if is_complex else "plddt"
        key = (num_models, recycles, tolerance, max_seq, max_extra_seq, rank_by)
        engine_rebuilt = self._ensure_runners(key)

        t_feat = time.time()
        feature_dict, _domain_names = generate_input_feature(
            query_seqs_unique,
            query_seqs_cardinality,
            unpaired_msa,
            paired_msa,
            template_features,
            is_complex,
            MODEL_TYPE,
            max_seq=max_seq,
        )
        featurise_s = round(time.time() - t_feat, 2)

        t_inf = time.time()
        # No padding: `pad_len = seq_len` makes upstream's `if seq_len < pad_len`
        # false, which is what the multimer path does anyway (it has no
        # `pad_input_multimer`). Stated rather than left at 0, so that a reader
        # does not wonder whether a 0 means "unpadded" or "not reached".
        results = predict_structure(
            prefix=name,
            result_dir=Path(out_dir),
            feature_dict=feature_dict,
            is_complex=is_complex,
            use_templates=False,
            sequences_lengths=sequence_lengths,
            pad_len=seq_len,
            model_type=MODEL_TYPE,
            model_runner_and_params=self._runners,
            random_seed=random_seed,
            num_seeds=num_seeds,
            rank_by=rank_by,
        )
        inference_s = round(time.time() - t_inf, 2)

        structures = [
            os.fspath(p) for p in results.get("result_files", []) if str(p).endswith(".pdb")
        ]
        if not structures:
            # Upstream can finish without producing a structure (it catches its
            # own per-query exceptions in `run()`; here the only way to get
            # here is an empty model list). An exit code is not evidence that a
            # model ran, so this is reported failed rather than empty.
            raise RuntimeError(
                "the prediction wrote no ranked PDB: nothing was produced. The "
                "request is reported failed rather than empty."
            )

        scores = []
        for rank, metric in zip(results.get("rank", []), results.get("metric", [])):
            scores.append(
                {
                    "name": rank,
                    "mean_plddt": _number(metric.get("mean_plddt")),
                    "ptm": _number(metric.get("ptm")),
                    "iptm": _number(metric.get("iptm")),
                    "actifptm": _number(metric.get("actifptm")),
                }
            )

        self.lengths_seen.append(seq_len)
        body = {
            "model": "ColabFold 1.6.1 / AlphaFold2-Multimer v3",
            "model_type": MODEL_TYPE,
            "kit_mode": self.mode,
            "weights_held_by": "worker",
            "msa_source": "caller (precomputed a3m; no MMseqs2 server contacted)",
            "use_bfloat16": USE_BFLOAT16,
            "structures": structures,
            "files": structures,
            "scores": scores,
            "best": scores[0]["name"] if scores else None,
            "num_models": num_models,
            "num_seeds": num_seeds,
            "num_recycles": recycles,
            "random_seed": random_seed,
            "chains": chains,
            "sequence_lengths": sequence_lengths,
            "query_length": seq_len,
            "padded_length": seq_len,
            "padding": "none",
            "msa_rows": msa_rows,
            "unpaired_msa_rows": unpaired_rows,
            "paired_msa_rows": paired_rows,
            "max_seq": max_seq,
            "max_extra_seq": max_extra_seq,
            "is_complex": bool(is_complex),
            "engine_rebuilt": engine_rebuilt,
            "engine_builds": self.engine_builds,
            "config_rebuilds": self.config_rebuilds,
            "requests_served": self.requests,
            "lengths_compiled": sorted(set(self.lengths_seen)),
            "timing": {
                "featurise_s": featurise_s,
                "inference_s": inference_s,
                "total_s": round(time.time() - t0, 2),
            },
        }
        body.update(self.memory())
        return body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ColabFold resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--mode", default="off")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    args = parser.parse_args(argv)

    base = _load_worker_base()
    engine = Engine(args)
    engine.build()

    def ready():
        body = {
            "build_s": engine.build_s,
            "kit_mode": engine.mode,
            "weights_held_by": "worker",
            "model_type": MODEL_TYPE,
            "compute_capability": engine.compute_capability,
            "requests_served": engine.requests,
            "engine_builds": engine.engine_builds,
            "engine": json.dumps(engine._runner_key),
            "padding": "none",
            "use_bfloat16": USE_BFLOAT16,
            "msa_source": "caller (precomputed a3m)",
        }
        body.update(engine.memory())
        return body

    return base.serve(
        slug=args.slug,
        socket_path=args.socket,
        on_predict=engine.predict,
        ready=ready,
        log=_say,
    )


if __name__ == "__main__":
    sys.exit(main())
