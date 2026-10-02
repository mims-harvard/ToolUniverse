#!/usr/bin/env python
"""mosaic resident worker -- builds Boltz-2-as-JAX once, designs binders many times.

Runs in the MODEL's environment (CPython 3.12.1, jax/jaxlib 0.10.2 +
jax-cuda12-plugin, torch 2.7.1+cpu, the escalante-bio ``mosaic``/``joltz``/
``boltz`` packages at their pinned commits, and the optimisation kit's
``mosaic_opt``). It imports nothing from ToolUniverse: ``protocol.py`` and
``worker_base.py`` are loaded by path.

WHAT ONE REQUEST IS
-------------------
One DESIGN: a target protein sequence and a binder length go in; a binder
sequence, the predicted complex and its confidence come out. The recipe is
upstream's ``examples/boltz_notebook.py``, and this worker does not retype any of
it: the kit's ``tools/recipe.py`` -- the one module both the kit's driver and the
kit's package import -- carries every literal with its source line, and every
function called below is that module's. In order:

  1. featurise [binder of length L as poly-X] + [target x copies]
  2. build the loss over the soft sequence:
       2*BinderTargetContact + WithinBinderContact + 5*InverseFoldingSequenceRecovery
  3. 75 + 50 steps of simplex_APGM; EVERY STEP IS A FULL BOLTZ-2 FORWARD AND
     BACKWARD PASS (1 recycle, 25 diffusion steps) plus a ProteinMPNN pass
  4. refold the final PSSM once, forward only, and score it

WHAT IS HELD, AND WHAT IS NOT
-----------------------------
Held: the process (imports, CUDA context), the Boltz-2 model converted to a JAX
module (``joltz.from_torch``, 521,023,231 parameters, ~27 s to build), the
ProteinMPNN weights, and **every XLA executable ever compiled for a shape**.
That last one is what residency is worth here. A shape -- target residues x
copies + binder length, plus the epitope list when there is one -- is its own
XLA program, and compiling a new one cost 185-255 s on this card for the first
step alone. Measured in one worker: shape A 256 s, shape B 318 s, shape A again
42 s for the same 8 steps. A per-request process pays the first number every time.

Not held: features and the loss. ``featurize`` -> ``build_loss`` are 1.0 s and
0.2 s and are rebuilt per request. They are not cached because boltz re-draws
``ref_pos`` at every featurisation (the kit says so in det.py), so two requests
for one design differ in the 4th figure of the first loss whatever is done;
this provider is a held worker, not a bitwise-reproducible one, and says so.

THE ENGINE KEY, AND WHY THERE IS NO "CONFIG REBUILD" HERE
---------------------------------------------------------
Other providers rebuild an engine when a request changes a compile-time option
(af3_jax: recycles and samples; genie3: sampling config). Here nothing the
caller can set changes the model: recycling (1) and sampling steps (25) are the
recipe's literals, asserted by ``recipe.build_loss``, and are not options. What
varies the compiled program is the SHAPE, so a shape change is this provider's
rebuild, and the acceptance test exercises it as one (see provider.toml).
The kit's per-step levers are installed ONCE per process by the kit's own hook
(``levers.install`` raises ``lever_already_installed`` on a second call), so the
mode is fixed for a worker's life by ``[kit] mode``.

HOW THE KIT IS ENGAGED
----------------------
By the variable the kit documents for "a program of your own": ``MOSAIC_OPT=fast``
in the environment (set by launch.py), whose ``.pth`` arms a finder that fires
on the first ``import mosaic`` and calls ``pcc.enable()`` + ``levers.install()``.
Before that import this worker has to have done nothing that initialises the JAX
backend or builds a ``Boltz2`` (the kit refuses by name if either has happened),
and it asserts afterwards that the hook ran rather than trusting that it did:
an unset variable runs stock silently, and a worker that reported ``fast`` while
running stock is the failure the kit's whole refuse-by-name design exists to
prevent. P2 (the fast weight load) is a call-site replacement no hook can apply;
the kit's recipe module does it (``load_model("fastinit")``), exactly as the
kit's driver does, and the kit says so on its own ACTIVE line
(``-aside[P2:driver_only]``).

PEAK MEMORY UNDER JAX
---------------------
``peak_reserved_gib`` is ``memory_stats()["peak_pool_bytes"]`` and
``peak_in_use_gib`` is ``peak_bytes_in_use`` (``peak_bytes_reserved`` reads 0 and
is not the analogue of torch's). Both are running high-water marks and neither is
reset between requests: a host adding budgets up needs the worst case, and JAX
offers no reset for the pool figure. The pool figure is coarse (8.0 GiB for a
working set of 4.8); the in-use figure is what answers "what does this input
cost".

NOTHING FORKS. ``boltz.main.process_inputs`` only opens a ``Pool`` when asked for
more than one preprocessing thread and it defaults to one; the data module is
built with ``num_workers=0`` by mosaic itself; and nothing here starts a process.
So there is no ``OMP_NUM_THREADS`` setting in this provider's manifest: the
reason boltzgen needs one does not exist here, and a setting without an argument
is one nobody can later tell is safe to remove.
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

SLUG = "mosaic"

# Largest complex this provider will design, in Boltz-2 tokens (target residues
# x copies + binder length). The figure the declared [gpu] vram_budget_gb was
# measured at, and not a number that was convenient: the pair track is N^2 and a
# request above it needs the budget re-measured, not this limit raised.
MAX_TOKENS = 384
MIN_BINDER = 8
MAX_BINDER = 200
MAX_COPIES = 4
MAX_TARGET = 376
MAX_STEPS = 400
_AA = set("ACDEFGHIKLMNPQRSTVWY")


def _refuse(message: str) -> SystemExit:
    """A refusal exits 3, per STANDARD section 8; its message goes to stderr.

    ``raise SystemExit("text")`` would print the text and exit **1**, which the
    standard reserves for "failed" -- the half of the contract a caller branches
    on.
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


def _int(spec: dict, key: str, default: int, low: int, high: int) -> int:
    value = spec.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"'{key}' must be an integer")
    if not low <= value <= high:
        raise ValueError(f"'{key}' must be between {low} and {high}")
    return value


def parse_input(text) -> dict:
    """The request's ``input`` text: one JSON object naming one design."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError(
            "'input' must be a JSON object: "
            '{"target_sequence": "...", "binder_length": 80, ...}'
        )
    try:
        spec = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"'input' is not JSON: {exc}") from exc
    if not isinstance(spec, dict):
        raise ValueError("'input' must be a JSON object")
    known = {
        "target_sequence",
        "binder_length",
        "target_copies",
        "steps1",
        "steps2",
        "epitope",
        "seed",
    }
    unknown = sorted(set(spec) - known)
    if unknown:
        raise ValueError(f"unknown field(s) {unknown}; the input takes {sorted(known)}")
    seq = spec.get("target_sequence")
    if not isinstance(seq, str) or not seq.strip():
        raise ValueError("'target_sequence' must be a non-empty protein sequence")
    seq = re.sub(r"\s+", "", seq).upper()
    bad = sorted(set(seq) - _AA)
    if bad:
        raise ValueError(
            f"'target_sequence' has letters outside the 20 standard amino acids: {bad}"
        )
    if len(seq) > MAX_TARGET:
        raise ValueError(
            f"'target_sequence' is {len(seq)} residues; the limit is {MAX_TARGET}"
        )
    out = {
        "target_sequence": seq,
        "binder_length": _int(spec, "binder_length", 80, MIN_BINDER, MAX_BINDER),
        "target_copies": _int(spec, "target_copies", 1, 1, MAX_COPIES),
        "steps1": _int(spec, "steps1", 75, 1, MAX_STEPS),
        "steps2": _int(spec, "steps2", 50, 1, MAX_STEPS),
        "epitope": spec.get("epitope"),
    }
    if out["epitope"] is not None and not isinstance(out["epitope"], str):
        raise ValueError("'epitope' must be a string such as '12,15,40-48'")
    if "seed" in spec:
        out["seed"] = _int(spec, "seed", 0, 0, 2**31 - 1)
    tokens = len(seq) * out["target_copies"] + out["binder_length"]
    if tokens > MAX_TOKENS:
        raise ValueError(
            f"{tokens} tokens (target {len(seq)} x {out['target_copies']} + binder "
            f"{out['binder_length']}) exceeds this provider's {MAX_TOKENS}-token "
            f"envelope, the size its VRAM budget was measured at"
        )
    return out


class Engine:
    """Everything held between requests."""

    def __init__(self, args):
        self.args = args
        self.mode = args.mode
        self.weights_root = os.path.abspath(os.path.expanduser(args.weights_root))
        self.build_s = None
        self.requests = 0
        self.shapes_seen = {}
        self.M = None
        self.model = None
        self.mpnn = None
        self.jax = None
        self.device = None
        self.kit_report = None
        self.load_path = None

    # ---------------------------------------------------------------- build
    def build(self) -> None:
        t0 = time.time()
        if self.mode not in ("off", "fast", "big", "exact"):
            raise _refuse(f"[{SLUG}-resident] --mode {self.mode!r} is not a kit mode")
        if self.mode == "exact":
            # exact is the warm row: it needs a per-shape populate step
            # (`mosaic-opt warm`) before it is exact, and a resident worker
            # serves shapes nobody has warmed. Running it would be stock under
            # another name, which the kit itself reports as "not warm".
            raise _refuse(
                f"[{SLUG}-resident] --mode exact needs `warm` once per shape and "
                f"this worker serves shapes nobody warmed; use fast or off"
            )
        ckpt = os.path.join(self.weights_root, "boltz", "boltz2_conf.ckpt")
        if not os.path.isfile(ckpt):
            raise _refuse(
                f"[{SLUG}-resident] {ckpt} is absent; run `tu remote setup mosaic`. "
                f"Nothing is fetched at request time."
            )
        if os.path.abspath(os.environ.get("MOSAIC_CACHE_DIR", "")) != self.weights_root:
            raise _refuse(
                f"[{SLUG}-resident] MOSAIC_CACHE_DIR is "
                f"{os.environ.get('MOSAIC_CACHE_DIR')!r} but the certified weights "
                f"root is {self.weights_root!r}: the library would load a file the "
                f"weights step never read"
            )
        if self.mode != "off" and os.environ.get("MOSAIC_OPT") != self.mode:
            raise _refuse(
                f"[{SLUG}-resident] --mode {self.mode} but MOSAIC_OPT="
                f"{os.environ.get('MOSAIC_OPT')!r}: the kit would not engage and "
                f"stock would run under the name of {self.mode}. launch.py sets it"
            )

        # The kit's accessor; importing it loads no jax and no upstream package.
        from mosaic_opt import recipe as kit_recipe

        self.M = M = kit_recipe.module()

        # jax first, and nothing that initialises its backend: the kit refuses
        # a late activation by name.
        import jax

        self.jax = jax
        # THIS import is the trigger. Under MOSAIC_OPT the kit's finder fires on
        # the first `import mosaic` and activates the mode, or exits 3.
        M.import_stack()

        devices = jax.local_devices(backend="gpu")
        if not devices:
            raise _refuse(
                f"[{SLUG}-resident] jax reports no GPU device "
                f"(default_backend={jax.default_backend()!r}); this provider "
                f'declares [gpu] policy = "required"'
            )
        self.device = devices[0]

        if self.mode != "off":
            import mosaic_opt

            rep = mosaic_opt.status()
            self.kit_report = rep
            if not rep.get("active"):
                raise _refuse(
                    f"[{SLUG}-resident] MOSAIC_OPT={self.mode} but the kit reports "
                    f"inactive ({rep.get('reason')}); refusing to run stock under "
                    f"the name of {self.mode}"
                )
            if rep.get("partial"):
                raise _refuse(
                    f"[{SLUG}-resident] the kit activated PARTIALLY "
                    f"({rep.get('levers_unavailable')}); its own gate exits 3 on this"
                )

        # P2 is the kit's fast weight load for the fast and big rows; stock mode
        # uses upstream's own Boltz2(). Same parameters either way.
        self.model, self.load_path = M.load_model(
            "torch" if self.mode == "off" else "fastinit"
        )
        self.mpnn = M.load_mpnn()
        self.build_s = round(time.time() - t0, 2)
        applied = (self.kit_report or {}).get("levers_applied") or []
        _say(
            f"ready device={self.device.device_kind} cc={self.compute_capability} "
            f"jax={jax.__version__} mode={self.mode} weights_held_by=worker "
            f"levers={','.join(applied) or 'none'} "
            f"p1={'on' if (self.kit_report or {}).get('p1') else 'off'} "
            f"load={self.load_path.split(' (')[0]} build_s={self.build_s}"
        )

    @property
    def compute_capability(self) -> str:
        try:
            return str(self.device.compute_capability)
        except Exception:  # noqa: BLE001 - informational only
            return "?"

    # ------------------------------------------------------------ measuring
    def memory(self) -> dict:
        try:
            stats = self.device.memory_stats() or {}
        except Exception:  # noqa: BLE001 - a missing stat must not fail a design
            return {}
        gib = 1024.0**3
        out = {}
        if stats.get("peak_pool_bytes") is not None:
            out["peak_reserved_gib"] = round(stats["peak_pool_bytes"] / gib, 2)
        if stats.get("peak_bytes_in_use") is not None:
            out["peak_in_use_gib"] = round(stats["peak_bytes_in_use"] / gib, 2)
        out["memory_source"] = "jax.local_devices()[0].memory_stats()"
        return out

    # --------------------------------------------------------------- design
    def predict(self, req: dict) -> dict:
        t0 = time.time()
        M = self.M
        jax = self.jax
        spec = parse_input(req.get("input"))
        seed = req.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            seed = spec.get("seed", 0)
        if seed < 0:
            raise ValueError("'seed' must be non-negative")
        self.requests += 1

        out_dir = req.get("out_dir") or tempfile.mkdtemp(prefix=f"{SLUG}-out-")
        os.makedirs(out_dir, exist_ok=True)
        name = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(req.get("name") or "design")).strip(
            "-"
        )
        name = name or "design"

        L = spec["binder_length"]
        target = M.target(
            sequence=spec["target_sequence"],
            name="target",
            copies=spec["target_copies"],
        )
        epitope = M.epitope(spec["epitope"], target) if spec["epitope"] else None
        n_tokens = M.tokens(target, L)
        # The shape key as the compiled program sees it: what decides whether
        # this request pays a compilation. The epitope index list is part of the
        # loss pytree, so its length is part of the key.
        shape_key = (
            n_tokens,
            L,
            spec["target_copies"],
            len(epitope["idx"]) if epitope else 0,
        )
        shape_cold = shape_key not in self.shapes_seen

        t = time.time()
        features, _writer = M.featurize(self.model, L, target)
        features = M.as_jax(features)
        del _writer  # releases the temporary directory boltz's featuriser made
        featurise_s = round(time.time() - t, 2)
        got = int(features["res_type"].shape[1])
        if got != n_tokens:
            raise RuntimeError(
                f"featurisation produced {got} tokens, the recipe expects {n_tokens}"
            )

        loss = M.build_loss(
            self.model,
            self.mpnn,
            dict(features),
            epitope_idx=epitope["idx"] if epitope else None,
        )
        x0 = M.x0(seed, L)
        stages = M.stages(spec["steps1"], spec["steps2"])

        t = time.time()
        s1, s2 = M.design(loss, x0, seed, stages, trajectory_fn=M.trajectory_record)
        design_s = round(time.time() - t, 2)
        import numpy as np

        traj = [r["loss"] for r in s1["trajectory"] + s2["trajectory"]]
        if not traj or not all(math.isfinite(v) for v in traj):
            raise RuntimeError(
                "the design's loss went non-finite; no sequence is reported"
            )
        x2 = s2["x"]

        t = time.time()
        out = M.refold(self.model, x2, features)
        jax.block_until_ready(out.pae)
        refold_s = round(time.time() - t, 2)

        import jax.numpy as jnp
        from mosaic.common import TOKENS
        from mosaic.losses.structure_prediction import IPTMLoss

        iptm = float(
            -IPTMLoss()(jnp.asarray(x2), out, key=jax.random.key(M.REFOLD_KEY))[0]
        )
        pssm = np.asarray(x2)
        sequence = "".join(TOKENS[i] for i in pssm.argmax(-1))
        plddt = np.asarray(out.plddt)
        pae = np.asarray(out.pae)
        scores = {
            "iptm": iptm,
            "plddt_binder_mean": float(plddt[:L].mean()),
            "plddt_target_mean": float(plddt[L:].mean()),
            "pae_binder_to_target_mean": float(pae[:L, L:].mean()),
        }
        if not all(math.isfinite(v) for v in scores.values()):
            raise RuntimeError(f"the refold's scores are not finite: {scores}")

        # Census and fail-closed gates of the kit's per-step levers: "installed"
        # is not "ran". A gate that fails raises RecipeError and fails the request.
        lever_facts = {}
        if self.mode != "off":
            M.levers_finalize(name)
            lever_facts = {
                k: {
                    kk: vv
                    for kk, vv in v.items()
                    if kk in ("state", "served", "fallback")
                }
                for k, v in (M.levers_record() or {}).items()
            }

        # Written only now, after every check above passed. A request that
        # fails earlier leaves nothing for [runtime] outputs to match.
        structure = out.to_structure()
        pdb_path = os.path.join(out_dir, f"{name}_complex.pdb")
        structure.write_pdb(pdb_path)
        n_chains = len(structure[0])
        n_res = sum(len(c) for c in structure[0])
        if n_chains != 1 + spec["target_copies"] or n_res != n_tokens:
            raise RuntimeError(
                f"the written complex has {n_chains} chains / {n_res} residues; "
                f"expected {1 + spec['target_copies']} / {n_tokens}"
            )
        summary_path = os.path.join(out_dir, f"{name}_design.json")
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "binder_sequence": sequence,
                    "target_sequence": spec["target_sequence"],
                    "scores": scores,
                    "loss_trajectory": traj,
                },
                fh,
            )

        self.shapes_seen[shape_key] = self.shapes_seen.get(shape_key, 0) + 1
        body = {
            "model": "Boltz-2 (JAX, via joltz) binder hallucination -- escalante-bio/mosaic",
            "kit_mode": self.mode,
            "weights_held_by": "worker",
            "binder_sequence": sequence,
            "binder_length": L,
            "target_sequence": spec["target_sequence"],
            "target_copies": spec["target_copies"],
            "n_tokens": n_tokens,
            "epitope": epitope["spec"] if epitope else None,
            "seed": seed,
            "steps": {"stage1": spec["steps1"], "stage2": spec["steps2"]},
            "scores": scores,
            "sequence_sharpness": float(pssm.max(-1).mean()),
            "loss": {
                "first": traj[0],
                "final": traj[-1],
                "best": min(traj),
                "trajectory": [round(v, 4) for v in traj],
            },
            "files": [pdb_path, summary_path],
            "shape_compiled_before": not shape_cold,
            "shapes_held": len(self.shapes_seen),
            "requests_served": self.requests,
            "levers": lever_facts,
            "timing": {
                "featurise_s": featurise_s,
                "design_s": design_s,
                "refold_s": refold_s,
                "total_s": round(time.time() - t0, 2),
            },
        }
        body.update(self.memory())
        _say(
            f"request {self.requests} done tokens={n_tokens} "
            f"{'held' if not shape_cold else 'compiled'} "
            f"total_s={body['timing']['total_s']} "
            f"peak_pool_gib={body.get('peak_reserved_gib')} "
            f"peak_in_use_gib={body.get('peak_in_use_gib')}"
        )
        return body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="mosaic resident worker")
    parser.add_argument("--socket", required=True)
    parser.add_argument("--slug", default=SLUG)
    parser.add_argument("--mode", default="off")
    parser.add_argument("--kit", default="")
    parser.add_argument("--weights-root", required=True)
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
            "shapes_held": len(engine.shapes_seen),
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
