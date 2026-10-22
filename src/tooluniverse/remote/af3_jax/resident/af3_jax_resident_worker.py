#!/usr/bin/env python
"""AF3-JAX resident worker -- builds AlphaFold 3 (JAX) once, folds many times.

Runs in the MODEL's environment (CPython 3.12.1, jax/jaxlib 0.10.2 +
jax-cuda12-plugin, the sokrypton/alphafold3 fork installed as alphafold3-open
3.1.4). It imports nothing from ToolUniverse: ``protocol.py`` and
``worker_base.py`` are loaded by path, which is the whole reason the two
environments can hold conflicting stacks.

WHAT IS HELD, AND WHY IT IS WORTH HOLDING
-----------------------------------------
One ``run_alphafold.ModelRunner``. Both of its expensive properties are
``functools.cached_property``:

* ``model_params`` -- ``params.get_model_haiku_params`` zstd-streams the
  1.37 GB record file and turns every record into a ``jnp.array``, so the
  weights land on the device once instead of once per request.
* ``_model`` -- the jitted forward pass. This fork pads every input to a
  BUCKET, and a featurised batch's shapes are a pure function of that bucket
  alone, not of the token count, MSA depth, chain count or template count
  (``pipeline.calculate_bucket_size`` and ``PaddingShapes``). Two requests in
  one bucket are therefore a jit cache hit; two in different buckets cost one
  XLA compilation each, paid once per bucket for the worker's whole life. A
  per-request process pays every one of them every time.

On top of those, ``ModelRunner._autotune_result`` holds tokamax's autotune
table, which the kit's own README puts at about 20 s per process and says "no
cache holds"; and ``chemical_components.Ccd()`` is built once here rather than
per call (upstream's ``predict_structure`` rebuilds it every time).

TWO THINGS A READER WILL WANT AND WOULD NOT GUESS
------------------------------------------------
1. **The model config is compile-time.** ``num_recycles``,
   ``num_diffusion_samples`` and the attention implementation are baked into
   ``model.Model.Config`` at construction, so changing one needs a new
   ``ModelRunner`` and a fresh compilation. This worker holds ONE runner and
   rebuilds it when a request asks for a different pair, reporting
   ``config_rebuilt`` in the reply so the cost is visible rather than
   mysterious. Requests that keep the defaults never trigger it.
2. **Nothing is written until a structure exists.** Upstream's
   ``process_fold_input`` writes ``<job>_data.json`` BEFORE inference, so a run
   that folded nothing still leaves a file behind. This worker does not call
   it: the first write of any request is ``post_processing.write_output`` on an
   extracted sample, which is why ``provider.toml``'s ``outputs`` glob
   (``*_model.cif``) is evidence rather than decoration.

PEAK MEMORY UNDER JAX -- READ THIS BEFORE COMPARING THE NUMBER
--------------------------------------------------------------
There is no torch here, so ``peak_reserved_gib`` cannot come from
``torch.cuda.max_memory_reserved``. It is taken from
``jax.local_devices()[0].memory_stats()``, and WHICH FIELD matters, because a
scheduler adds these up across providers:

====================== =========================================================
field                  what it is
====================== =========================================================
``peak_pool_bytes``    high-water of the BFC pool -- all the memory the process
                       has taken from the device and not given back. This is
                       the analogue of torch's *reserved* and is what this
                       worker reports as ``peak_reserved_gib``.
``peak_bytes_in_use``  high-water of what was live inside that pool. The
                       analogue of torch's *allocated*. Reported beside it as
                       ``peak_in_use_gib``.
``peak_bytes_reserved``MEASURED ON THIS HOST AS 0 AND NOT THE ANALOGUE DESPITE
                       THE NAME: in XLA "reserved" means memory held OUTSIDE
                       the BFC pool. A 2048x2048 matmul reads
                       peak_bytes_in_use 150,995,200, peak_pool_bytes
                       287,309,824, peak_bytes_reserved 0. Reporting the field
                       whose name matches would have reported zero for every
                       request forever.
====================== =========================================================

The kit's own instrument (``opt_core/mem/peak.py``) samples
``peak_bytes_in_use`` instead, deliberately -- it is answering "what did this
input cost", a tighter question than "what does this worker hold". Both are
returned so neither reading has to be recomputed.

This worker does NOT reset peak statistics between requests, which the standard
asks of a new provider: a host adding budgets up needs the worker's worst case,
and a per-request peak under-reports whatever the pool has grown to. JAX offers
no reset for ``peak_pool_bytes`` in any case.

NOTHING FORKS. With ``run_data_pipeline=False`` and no MSA server, the fork's
request path contains no ``multiprocessing``, no ``ProcessPoolExecutor`` and no
``os.fork`` -- only a ``ThreadPoolExecutor`` inside
``model.Model.get_inference_result`` for the DSSP clash/disorder terms. The
kit's ``L1`` lever WOULD fork three featurisation children, which is why this
provider runs ``[kit] mode = "off"`` and why that is a safety property and not
only a performance one.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import math
import os
import sys
import tempfile
import time
from pathlib import Path

SLUG = "af3_jax"
# Upstream's own defaults (run_alphafold.make_model_config).
DEFAULT_RECYCLES = 10
DEFAULT_SAMPLES = 5
DEFAULT_ATTENTION = "triton"
# tokamax's `--tokamax_autotuning_cache_miss_fallback`. NOT upstream's default
# ("heuristics"), and the reason is a compile failure rather than a preference:
# see build(). "" restores upstream's default.
DEFAULT_TOKAMAX_FALLBACK = "autotune"


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


class Engine:
    """Everything held between requests."""

    def __init__(self, args):
        self.args = args
        self.mode = args.mode
        self.repo = os.path.abspath(os.path.expanduser(args.repo))
        self.params_dir = os.path.abspath(os.path.expanduser(args.params_dir))
        self.cache_dir = os.path.abspath(os.path.expanduser(args.cache_dir))
        self.build_s = None
        self.buckets_source = "unknown"
        self.config_rebuilds = 0
        self.requests = 0
        self._runner = None
        self._runner_key = None
        self._ccd = None
        self._device = None
        self._modules = {}

    # -------------------------------------------------------------- building
    def build(self) -> None:
        t0 = time.time()
        if self.mode != "off":
            # The kit's levers are a replacement script, a launcher and a flag
            # row on a command line -- never an in-process patch
            # (af3_jax_opt/_autoload.py). A worker that was handed another mode
            # would silently run stock and report the mode, which is the one
            # thing the kit's own hook exists to prevent.
            raise _refuse(
                f"[{SLUG}-resident] --mode {self.mode!r}: this worker implements "
                f"the kit's stock route only. af3_jax's levers are applied by "
                f"af3_jax_opt/levers_launch.py and fpf_launch.py to the script "
                f"they then run; engaging them from here would mean sitting in "
                f"that script's position, which provider.toml's [kit] section "
                f"explains is refused on this compute capability anyway."
            )

        if not os.path.isdir(self.params_dir):
            raise _refuse(
                f"[{SLUG}-resident] --params-dir {self.params_dir} is not a "
                f"directory; it must hold of3_ported_weights.bin.zst "
                f"(<AF3_JAX_PARAMS_ROOT>/p2/)"
            )
        if not os.path.isfile(os.path.join(self.repo, "run_alphafold.py")):
            raise _refuse(
                f"[{SLUG}-resident] --repo {self.repo} holds no run_alphafold.py; "
                f"it must be the sokrypton/alphafold3 fork checkout "
                f"(bash <kit>/af3_jax/stock/unpack_src.sh <dir>)"
            )

        # Set before jax is imported, in case the launcher did not: JAX
        # preallocates 75% of the device otherwise and every peak this worker
        # reported would be a measurement of that preallocation.
        os.environ.setdefault("XLA_PYTHON_CLIENT_PREALLOCATE", "false")

        # run_alphafold.py lives in the CHECKOUT, not in the installed package.
        if self.repo not in sys.path:
            sys.path.insert(0, self.repo)
        # Import exactly once: absl raises DuplicateFlagError if a module
        # defining flags is imported twice under two names.
        import run_alphafold as RA  # noqa: E402

        from absl import flags  # noqa: E402
        import jax  # noqa: E402
        from alphafold3.common import folding_input  # noqa: E402
        from alphafold3.constants import chemical_components  # noqa: E402
        from alphafold3.data import featurisation  # noqa: E402
        from alphafold3.model import post_processing  # noqa: E402

        # Five module-level flag reads sit outside main(), and one of them is in
        # ModelRunner.__init__ (_CACHE_DIR, via _load_autotune_cache), so the
        # runner cannot be constructed in a process whose flags are unparsed:
        # absl raises UnparsedFlagAccessError. Parse once, explicitly, with the
        # values this provider means -- never mark_as_parsed(), which would
        # leave --cache_dir at /tmp/alphafold_cache and silently scatter a
        # compile cache the manifest does not know about.
        if not flags.FLAGS.is_parsed():
            argv = [
                "run_alphafold",
                "--norun_data_pipeline",
                "--of3_weights",
                f"--model_dir={self.params_dir}",
                f"--cache_dir={self.cache_dir}",
                f"--output_dir={os.path.join(self.cache_dir, 'unused')}",
            ]
            # THE ONE FLAG THAT MAKES THIS PROVIDER RUN ON THIS CARD, and it is
            # upstream's own -- `run_alphafold.py --helpfull` lists it, because
            # tokamax registers it as an absl flag at import:
            #
            #   --tokamax_autotuning_cache_miss_fallback:
            #       <heuristics|autotune|error>
            #
            # Default `heuristics`. tokamax ships no tuned config for an
            # NVIDIA GB10 ("Autotuning cache miss for
            # PallasTritonGatedLinearUnit ... on NVIDIA GB10"), so it builds one
            # from heuristics written for cards with 164-227 KiB of shared
            # memory per block. On this card the heuristic GLU config
            # (block_m=128, block_n=32, block_k=32, num_stages=4) over f32
            # operands asks 110,592 bytes against the 101,376 this part
            # provides, and XLA refuses the whole module at COMPILE time:
            #
            #   RESOURCE_EXHAUSTED: Shared memory size limit exceeded:
            #     requested 110592, available: 101376, context: []
            #
            # `autotune` makes tokamax measure its own default config set ON
            # THIS CARD and keep the fastest one that compiles and runs. That is
            # the mechanism the option exists for -- an unseen device -- and it
            # is configuration, not a tile override and not a monkeypatch. The
            # same single flag fixes the kit's own CLI route, because the kit
            # passes stock flags through verbatim:
            #   bash run.sh pred --mode off ... \
            #       --tokamax_autotuning_cache_miss_fallback=autotune
            #
            # WHAT IT COSTS: the autotune runs per op shape at first use, in
            # process, and is not persisted -- upstream's own
            # `tokamax_autotune.json` is written by a different call
            # (`tokamax.autotune` in `run_inference`) that is wrapped in
            # `except Exception: pass` and does not succeed here, so no file
            # appears and a restarted worker pays it again. Measured on this
            # card: the first request of a worker takes ~3.5 minutes, later
            # requests of the same shape ~20 s. That is the residency argument
            # in one line, and it is why `start_timeout_s` and
            # `smoke_timeout_s` are set where they are.
            if self.args.tokamax_fallback:
                argv.append(
                    "--tokamax_autotuning_cache_miss_fallback="
                    f"{self.args.tokamax_fallback}"
                )
            flags.FLAGS(argv)

        # main() does this; ModelRunner does not, so a worker that skips main()
        # must do it itself -- and before the first compilation, or the
        # persistent cache is simply never consulted.
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
            "RA": RA,
            "jax": jax,
            "folding_input": folding_input,
            "featurisation": featurisation,
            "post_processing": post_processing,
            "chemical_components": chemical_components,
        }
        self._buckets, self.buckets_source = self._padding(RA)

        self._ensure_runner(DEFAULT_RECYCLES, DEFAULT_SAMPLES)
        # Force the 1.37 GB read now rather than on the first request, so that
        # `build_s` means what it says and a request's timing is the request's.
        _ = self._runner.model_params
        # Hoisted out of upstream's predict_structure, which rebuilds it per
        # call. Only an input carrying its own userCCD needs a private one.
        self._ccd = chemical_components.Ccd()

        self.build_s = round(time.time() - t0, 2)
        _say(
            f"ready device={self._device.device_kind} cc={self.compute_capability} "
            f"jax={jax.__version__} mode={self.mode} weights_held_by=worker "
            f"attn={self.args.attention} "
            f"tokamax_fallback={self.args.tokamax_fallback or 'heuristics'} "
            f"params={self.params_dir} buckets={len(self._buckets)}"
            f"@{self.buckets_source} build_s={self.build_s}"
        )

    def _padding(self, RA):
        """``(buckets, source)`` -- the kit's own padding row, or upstream's.

        ASKED, NOT COPIED. The kit's stock route does not run with upstream's
        default sixteen buckets: `modes.pad_flags(mode)` emits
        ``--buckets=64,128,...,5120``, every multiple of 64, because the kit's
        shape policy is ``kernel_tile`` with ``KERNEL_TILE = 64``. Eighty rungs
        instead of sixteen, and that is a MEMORY decision as much as a speed
        one -- 800 tokens pad to 832 rather than to 1024, which is 1.08x the
        pair area instead of 1.64x. A resident worker can afford the extra
        compilations precisely because it keeps them.

        Reading it from `af3_jax_opt` rather than transcribing it is the kit
        contract: a hard-coded copy drifts the first time the kit moves. The
        import is safe -- af3_jax_opt pulls in neither jax nor the fork, and its
        start-up hook is inert because this worker's environment carries no
        undeclared AF3_JAX_* name and no mode (see launch.py). If it is not
        importable at all, upstream's own default is the honest fallback and the
        ready line says which was used.
        """
        try:
            from af3_jax_opt import modes as kit_modes

            for flag in kit_modes.pad_flags(self.mode):
                if str(flag).startswith("--buckets="):
                    row = tuple(
                        int(x) for x in str(flag).split("=", 1)[1].split(",") if x
                    )
                    if row:
                        return row, "kit"
        except Exception as exc:  # noqa: BLE001 - the fallback is correct, not a patch
            _say(f"padding: af3_jax_opt unavailable ({exc}); using upstream's row")
        return tuple(int(b) for b in RA._BUCKETS.value), "upstream"

    @property
    def compute_capability(self) -> str:
        try:
            return str(self._device.compute_capability)
        except Exception:  # noqa: BLE001 - informational only
            return "?"

    def _ensure_runner(self, recycles: int, samples: int) -> bool:
        """Hold a ModelRunner for (recycles, samples); True when it was rebuilt."""
        key = (recycles, samples, self.args.attention)
        if self._runner is not None and self._runner_key == key:
            return False
        RA = self._modules["RA"]
        rebuilt = self._runner is not None
        if rebuilt:
            self.config_rebuilds += 1
            _say(
                f"config change {self._runner_key} -> {key}: rebuilding the "
                f"ModelRunner (a fresh XLA compilation per bucket follows)"
            )
            self._runner = None  # drop the old params before allocating new ones
        config = RA.make_model_config(
            flash_attention_implementation=self.args.attention,
            num_diffusion_samples=samples,
            num_recycles=recycles,
            of3_weights=True,  # the ported OF3 weights; see provider.toml
        )
        self._runner = RA.ModelRunner(
            config=config, device=self._device, model_dir=self.params_dir
        )
        self._runner_key = key
        return rebuilt

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
        folding_input = self._modules["folding_input"]
        featurisation = self._modules["featurisation"]
        post_processing = self._modules["post_processing"]
        jax = self._modules["jax"]

        text = req.get("input")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("'input' must be an AlphaFold 3 fold-input JSON string")
        options = req.get("options") or {}
        recycles = int(options.get("num_recycles", DEFAULT_RECYCLES))
        samples = int(options.get("num_diffusion_samples", DEFAULT_SAMPLES))

        out_dir = req.get("out_dir") or tempfile.mkdtemp(prefix=f"{SLUG}-out-")
        os.makedirs(out_dir, exist_ok=True)

        # Parsing is upstream's: every refusal a malformed input deserves is
        # already written there, by name, and re-deriving them here would mean
        # two schemas that drift.
        fold_input = folding_input.Input.from_json(text)
        # The caller's seed replaces the JSON's `modelSeeds`. `Input` is a
        # frozen dataclass and ships no setter, so this is dataclasses.replace
        # rather than a method -- stated because reaching for a `with_seeds`
        # that does not exist is the obvious first guess (the fork has
        # `with_multiple_seeds`, which EXPANDS one seed into a range and
        # raises when more than one is present).
        seed = req.get("seed")
        if isinstance(seed, int) and not isinstance(seed, bool):
            fold_input = dataclasses.replace(fold_input, rng_seeds=(seed,))

        config_rebuilt = self._ensure_runner(recycles, samples)

        t_feat = time.time()
        # The hoisted CCD serves every input that does not bring its own; one
        # that does gets a private copy, because upstream keys the component
        # table on it.
        if getattr(fold_input, "user_ccd", None):
            ccd = self._modules["chemical_components"].Ccd(user_ccd=fold_input.user_ccd)
        else:
            ccd = self._ccd
        examples = featurisation.featurise_input(
            fold_input=fold_input, buckets=self._buckets, ccd=ccd, verbose=False
        )
        featurise_s = round(time.time() - t_feat, 2)

        t_inf = time.time()
        structures = []
        scores = []
        for seed_value, example in zip(fold_input.rng_seeds, examples):
            rng_key = jax.random.PRNGKey(seed_value)
            result = self._runner.run_inference(example, rng_key)
            results = self._runner.extract_inference_results(
                batch=example, result=result, target_name=fold_input.name
            )
            for index, inference_result in enumerate(results):
                sample_dir = os.path.join(out_dir, f"seed-{seed_value}_sample-{index}")
                os.makedirs(sample_dir, exist_ok=True)
                prefix = (
                    f"{fold_input.sanitised_name()}_seed-{seed_value}_sample-{index}"
                )
                # The FIRST write of this request, and it happens only now --
                # after a sample exists. Upstream's own writer, so the names
                # and the JSON schemas are upstream's.
                post_processing.write_output(
                    inference_result=inference_result,
                    output_dir=sample_dir,
                    name=prefix,
                )
                structures.append(os.path.join(sample_dir, f"{prefix}_model.cif"))
                meta = inference_result.metadata
                scores.append(
                    {
                        "name": prefix,
                        "seed": int(seed_value),
                        "sample": index,
                        "ranking_score": _number(meta.get("ranking_score")),
                        "ptm": _number(meta.get("ptm")),
                        "iptm": _number(meta.get("iptm")),
                        "fraction_disordered": _number(meta.get("fraction_disordered")),
                        "has_clash": _number(meta.get("has_clash")),
                    }
                )
        inference_s = round(time.time() - t_inf, 2)

        if not structures:
            # Upstream can return an empty sample list without raising; an exit
            # code is not evidence that a model ran.
            raise RuntimeError(
                "inference returned no samples: nothing was written. The "
                "request is reported failed rather than empty."
            )

        scores.sort(
            key=lambda s: (s["ranking_score"] is None, -(s["ranking_score"] or 0))
        )
        body = {
            "model": "AlphaFold 3 (JAX fork) / OpenFold3-preview2 weights",
            "kit_mode": self.mode,
            "weights_held_by": "worker",
            "structures": structures,
            "scores": scores,
            "best": scores[0]["name"] if scores else None,
            "seeds": [int(s) for s in fold_input.rng_seeds],
            "num_recycles": recycles,
            "num_diffusion_samples": samples,
            "config_rebuilt": config_rebuilt,
            "config_rebuilds": self.config_rebuilds,
            "requests_served": self.requests,
            "padding_buckets": len(self._buckets),
            "padding_source": self.buckets_source,
            "attention_implementation": self.args.attention,
            "tokamax_fallback": self.args.tokamax_fallback or "heuristics",
            "timing": {
                "featurise_s": featurise_s,
                "inference_s": inference_s,
                "total_s": round(time.time() - t0, 2),
            },
        }
        body.update(self.memory())
        return body


def _number(value):
    """A JSON-safe float from a numpy scalar, bool or NaN."""
    if value is None:
        return None
    try:
        out = float(value)
        return None if math.isnan(out) else round(out, 4)
    except (TypeError, ValueError):
        return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="AF3-JAX resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--mode", default="off")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--params-dir", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--attention", default=DEFAULT_ATTENTION)
    # tokamax's own flag value; "" leaves upstream's default (heuristics) in
    # place, which on this card does not compile. See build().
    parser.add_argument("--tokamax-fallback", default=DEFAULT_TOKAMAX_FALLBACK)
    args = parser.parse_args(argv)

    base = _load_worker_base()
    engine = Engine(args)
    engine.build()

    def ready():
        body = {
            "build_s": engine.build_s,
            "kit_mode": engine.mode,
            "weights_held_by": "worker",
            "compute_capability": engine.compute_capability,
            "requests_served": engine.requests,
            "padding_source": engine.buckets_source,
            "padding_buckets": len(engine._buckets),
            "attention_implementation": args.attention,
            "tokamax_fallback": args.tokamax_fallback or "heuristics",
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
