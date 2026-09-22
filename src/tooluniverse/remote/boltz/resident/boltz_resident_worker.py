"""Boltz-2 held resident on the GPU, answering one request at a time.

Run through the optimization kit's launcher, never on its own::

    python -m boltz2_opt.worker_launch <kit launch opts> -- boltz_resident_worker.py \
        --socket <path> --cache <BOLTZ_CACHE> --checkpoint <ckpt>

``worker_launch`` installs the kit's import hooks before this file's ``import
boltz.model.models.boltz2`` runs, so the levers of the active mode attach to the
model this process builds. Nothing in the kit is modified or copied: this file
is simply a different script in the position the kit's own batch worker
occupies, and the three levers the kit implements inside that script
(``resid``, ``mask2``, ``dit_hoist``) are the ones we forgo. The other 25 attach
through the hooks and are reported on the launcher's own lines.

Why this file exists. Measured on this project's GB10 box, a 330-residue
protein with one ligand and an affinity pass costs

    stock ``boltz predict`` per call         110 s
    kit ``--mode fast``, worker per call     102 s
    kit ``--mode fast``, worker held         ~55 s

because a fresh worker pays ~47 s of weight load, CUDA context and kit warm-up
that a held one pays once. The 2x is the residency, not the kit -- which is why
this file is the part we own.

The process is deliberately single-threaded over the device: one request is
served at a time and concurrency is the caller's to queue. Two requests sharing
one CUDA context would interleave allocations and make an out-of-memory
attributable to neither.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import socket
import sys
import threading
import time
import traceback
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--cache", required=True, help="BOLTZ_CACHE directory")
ap.add_argument("--checkpoint", required=True, help="boltz2_conf.ckpt path")
ap.add_argument("--slug", default="boltz", help="provider slug, echoed in ping")
ap.add_argument("--kernels", default="on", choices=("on", "off"))
ap.add_argument("--step-scale", type=float, default=1.5)
ap.add_argument("--build-seed", type=int, default=0)
args = ap.parse_args()

T0 = time.time()


def say(msg: str) -> None:
    print(f"[boltz-resident] {msg}", flush=True)


# ---------------------------------------------------------------- heavy imports
# Order matters: torch first (a CUDA extension imported before it cannot resolve
# the runtime libraries torch's loader provides), then the model module whose
# execution the kit's hooks are waiting on.
import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)
torch.set_float32_matmul_precision("highest")  # stock main.py

from rdkit import Chem  # noqa: E402

Chem.SetDefaultPickleProperties(Chem.PropertyPickleOptions.AllProps)
for _k in ("CUEQ_DEFAULT_CONFIG", "CUEQ_DISABLE_AOT_TUNING"):
    os.environ.setdefault(_k, "1")

from dataclasses import asdict  # noqa: E402

from pytorch_lightning import seed_everything  # noqa: E402

from boltz.data.module.inferencev2 import Boltz2InferenceDataModule  # noqa: E402
from boltz.data.write.writer import BoltzWriter  # noqa: E402
from boltz.data.types import Manifest  # noqa: E402
from boltz.main import (  # noqa: E402
    Boltz2DiffusionParams,
    BoltzProcessedInput,
    BoltzSteeringParams,
    MSAModuleArgs,
    PairformerArgsV2,
)
from boltz.model.models.boltz2 import Boltz2  # noqa: E402  <- the hooks' trigger


# The protocol module is loaded BY PATH, not as ``tooluniverse.remote_resident``.
# This process runs in the model's own isolated environment, which holds boltz
# and its pinned stack and nothing of ToolUniverse -- importing the package
# would pull in its whole dependency set and defeat the per-model environment.
# One dependency-free file is the entire shared surface between the two sides;
# the socket is the boundary.
def _load_protocol():
    import importlib.util

    here = Path(__file__).resolve()
    # <repo>/src/tooluniverse/remote/<slug>/resident/<this file>
    candidate = here.parents[3] / "remote_resident" / "protocol.py"
    override = os.environ.get("TOOLUNIVERSE_REMOTE_PROTOCOL")
    path = Path(override) if override else candidate
    if not path.is_file():
        raise SystemExit(
            f"[boltz-resident] the wire protocol is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_PROTOCOL to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_remote_protocol", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load_protocol()

say(f"imports done t={time.time() - T0:.1f}s torch={torch.__version__}")

CACHE = Path(args.cache)
MOL_DIR = CACHE / "mols"
CCD_PATH = CACHE / "ccd.pkl"
DEV = torch.device("cuda:0")
KERNELS = args.kernels == "on"

# The kit's parsing zygote: every input is parsed in a fresh child of a process
# that has initialised no CUDA and embedded no conformer, because RDKit's
# conformer RNG is process-global and unseeded upstream -- a second parse in a
# reused process does not hand a SMILES ligand the conformer stock hands it.
# ``worker_launch`` forked it before any of the imports above.
from boltz2_opt import affinity_leg as AL  # noqa: E402
from boltz2_opt import prep as _prep  # noqa: E402

PREP = _prep.zygote()
say(f"parsing zygote: {PREP.describe()}")


def _model_kwargs(predict_args: dict, use_potentials: bool, step_scale: float) -> dict:
    diffusion = Boltz2DiffusionParams()
    diffusion.step_scale = float(step_scale)
    steering = BoltzSteeringParams()
    steering.fk_steering = steering.physical_guidance_update = bool(use_potentials)
    return dict(
        predict_args=predict_args,
        map_location="cpu",
        diffusion_process_args=asdict(diffusion),
        ema=False,
        use_kernels=KERNELS,
        pairformer_args=asdict(PairformerArgsV2()),
        msa_args=asdict(MSAModuleArgs(use_paired_feature=True)),
        steering_args=asdict(steering),
    )


DEFAULT_PREDICT_ARGS = {
    "recycling_steps": 3,
    "sampling_steps": 200,
    "diffusion_samples": 1,
    "max_parallel_samples": 5,
    "write_confidence_summary": True,
    "write_full_pae": False,
    "write_full_pde": False,
}


def _rng_state() -> dict:
    return {
        "torch": torch.get_rng_state().clone(),
        "np": np.random.get_state(),
        "py": random.getstate(),
        "cuda": torch.cuda.get_rng_state().clone(),
    }


def _rng_set(st: dict) -> None:
    torch.set_rng_state(st["torch"])
    np.random.set_state(st["np"])
    random.setstate(st["py"])
    torch.cuda.set_rng_state(st["cuda"])


# ------------------------------------------------------------------ build once
# Stock's order is seed_everything(seed) THEN load_from_checkpoint, because the
# constructor consumes CPU RNG (nn.init, trunc_normal through numpy's global
# generator). The state right after construction is what a stock process holds
# when it enters predict_step, so it is captured and replayed before each item.
_t = time.time()
seed_everything(args.build_seed)
MODEL = Boltz2.load_from_checkpoint(
    args.checkpoint,
    strict=True,
    **_model_kwargs(
        dict(DEFAULT_PREDICT_ARGS), use_potentials=False, step_scale=args.step_scale
    ),
)
MODEL_KWARGS = _model_kwargs(
    dict(DEFAULT_PREDICT_ARGS), use_potentials=False, step_scale=args.step_scale
)
MODEL.to(DEV)
MODEL.eval()
POST_CTOR = {args.build_seed: _rng_state()}
BUILD_S = time.time() - _t
say(f"model built and resident on {torch.cuda.get_device_name(0)} in {BUILD_S:.1f}s")

# The construction-time settings; a request that disagrees is refused by name
# rather than served by a model built for something else.
BUILT_STEP_SCALE = float(args.step_scale)


def _post_ctor_for(seed: int) -> dict:
    """The RNG state a stock process holds after building this model at ``seed``.

    Replayed by constructing a throwaway model with the same hparams -- the same
    draws ``load_from_checkpoint`` makes -- once per seed, then cached.
    """
    if seed not in POST_CTOR:
        t = time.time()
        seed_everything(seed)
        throwaway = Boltz2(
            **{k: v for k, v in MODEL.hparams.items() if k not in ("validators",)}
        )
        POST_CTOR[seed] = _rng_state()
        del throwaway
        say(f"ctor replay for seed={seed} in {time.time() - t:.1f}s")
    return POST_CTOR[seed]


def _rebuild_for_step_scale(step_scale: float) -> None:
    """Hold a model built for ``step_scale``, rebuilding only when it changes."""
    global MODEL, MODEL_KWARGS, BUILT_STEP_SCALE, POST_CTOR
    if abs(step_scale - BUILT_STEP_SCALE) <= 1e-9:
        return
    t = time.time()
    previous = BUILT_STEP_SCALE
    del MODEL
    torch.cuda.empty_cache()
    MODEL_KWARGS = _model_kwargs(
        dict(DEFAULT_PREDICT_ARGS), use_potentials=False, step_scale=step_scale
    )
    seed_everything(args.build_seed)
    MODEL = Boltz2.load_from_checkpoint(args.checkpoint, strict=True, **MODEL_KWARGS)
    MODEL.to(DEV)
    MODEL.eval()
    POST_CTOR = {args.build_seed: _rng_state()}
    BUILT_STEP_SCALE = step_scale
    say(f"rebuilt for step_scale {previous} -> {step_scale} in {time.time() - t:.1f}s")


def _predict_one(req: dict) -> dict:
    """One structure prediction. Returns the reply body; raises on a defect."""
    yaml_text = req["yaml"]
    out_root = Path(req["out_dir"])
    seed = int(req.get("seed", 0))
    opts = dict(req.get("options") or {})

    # step_scale is consumed when the diffusion module is built, so a request
    # that changes it needs a new model. Rebuilding costs a few seconds with the
    # checkpoint in page cache -- far less than refusing and sending the caller
    # down the ~110 s subprocess path -- and a deployment that keeps one value,
    # which is the normal case, never pays it.
    _rebuild_for_step_scale(float(opts.get("step_scale", BUILT_STEP_SCALE)))

    # Predict-time settings are read out of self.predict_args inside
    # predict_step, so they are the request's without rebuilding anything.
    MODEL.predict_args = dict(
        DEFAULT_PREDICT_ARGS,
        **{
            k: opts[k]
            for k in (
                "recycling_steps",
                "sampling_steps",
                "diffusion_samples",
                "max_parallel_samples",
                "write_full_pae",
                "write_full_pde",
            )
            if k in opts
        },
    )
    use_potentials = bool(opts.get("use_potentials", False))
    MODEL.steering_args["fk_steering"] = use_potentials
    MODEL.steering_args["physical_guidance_update"] = use_potentials

    out_root.mkdir(parents=True, exist_ok=True)
    stem = req.get("name") or "input"
    yaml_path = out_root / f"{stem}.yaml"
    yaml_path.write_text(yaml_text)
    item_out = out_root / f"boltz_results_{stem}"
    item_out.mkdir(parents=True, exist_ok=True)

    timing = {}
    t = time.time()
    parsed = PREP.parse(
        str(yaml_path),
        str(item_out),
        str(CCD_PATH),
        str(MOL_DIR),
        boltz2=True,
        use_msa_server=bool(opts.get("use_msa_server", False)),
        msa_server_url=opts.get("msa_server_url", "https://api.colabfold.com"),
        msa_pairing_strategy=opts.get("msa_pairing_strategy", "greedy"),
        preprocessing_threads=int(opts.get("preprocessing_threads", 1)),
        max_msa_seqs=int(opts.get("max_msa_seqs", 8192)),
    )
    sys.stdout.write(parsed.out)
    sys.stderr.write(parsed.err)
    sys.stdout.flush()
    sys.stderr.flush()
    timing["process_inputs_s"] = round(time.time() - t, 2)
    if parsed.rc != 0:
        raise RuntimeError(
            f"parsing {yaml_path} in the zygote's child failed (rc {parsed.rc}); "
            f"its traceback is above"
        )

    # The zygote's child wrote boltz's processed tree; assemble the same
    # BoltzProcessedInput stock's own predict() hands the data module.
    pdir = item_out / "processed"
    manifest = Manifest.load(pdir / "manifest.json")
    if stem not in [r.id for r in manifest.records]:
        # process_inputs catches its own parse error, prints "Failed to process
        # ... Skipping." and leaves the record out. Nothing reached the model.
        raise ValueError(
            f"the stock parser skipped {stem}: no record in the manifest "
            f"(its own words are above)"
        )
    processed = BoltzProcessedInput(
        manifest=manifest,
        targets_dir=pdir / "structures",
        msa_dir=pdir / "msa",
        constraints_dir=(pdir / "constraints")
        if (pdir / "constraints").exists()
        else None,
        template_dir=(pdir / "templates") if (pdir / "templates").exists() else None,
        extra_mols_dir=(pdir / "mols") if (pdir / "mols").exists() else None,
    )

    dm = Boltz2InferenceDataModule(
        manifest=processed.manifest,
        target_dir=processed.targets_dir,
        msa_dir=processed.msa_dir,
        mol_dir=str(MOL_DIR),
        num_workers=0,  # a DataLoader subprocess buys nothing for one item
        constraints_dir=processed.constraints_dir,
        template_dir=processed.template_dir,
        extra_mols_dir=processed.extra_mols_dir,
        override_method=opts.get("method"),
    )
    _rng_set(_post_ctor_for(seed))
    it = iter(dm.predict_dataloader())
    rng_at_entry = _rng_state()

    writer = BoltzWriter(
        data_dir=processed.targets_dir,
        output_dir=str(item_out / "predictions"),
        output_format=opts.get("output_format", "mmcif"),
        boltz2=True,
    )
    t = time.time()
    try:
        batch = next(it)
    except StopIteration:
        raise RuntimeError(
            "the DataLoader yielded no batch for a record the manifest carries"
        ) from None
    timing["featurize_s"] = round(time.time() - t, 2)

    _rng_set(rng_at_entry)
    with torch.inference_mode():
        t = time.time()
        batch = dm.transfer_batch_to_device(batch, DEV, 0)
        timing["h2d_s"] = round(time.time() - t, 2)
        t = time.time()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            pred = MODEL.predict_step(batch, 0, 0)
        torch.cuda.synchronize()
        timing["inference_s"] = round(time.time() - t, 2)
        t = time.time()
        writer.write_on_batch_end(None, MODEL, pred, None, batch, 0, 0)
        timing["write_s"] = round(time.time() - t, 2)

    # Upstream runs a SECOND model right after the structure pass for an input
    # declaring `properties: - affinity`. No lever touches it: it is stock's own
    # code path, run by the kit in a clean interpreter handed the four RNG
    # streams exactly as they stand here -- where stock's one process stands
    # when it reaches that block. AL.execute reuses ONE served interpreter
    # (form `process`), and because THIS process is resident, so is that one:
    # its CUDA context and the affinity model are held across our requests too.
    rec = processed.manifest.records[0]
    if getattr(rec, "affinity", None):
        t = time.time()
        leg_req = AL.request(
            out_dir=item_out,
            targets_dir=processed.targets_dir,
            msa_dir=processed.msa_dir,
            constraints_dir=processed.constraints_dir,
            template_dir=processed.template_dir,
            extra_mols_dir=processed.extra_mols_dir,
            cache=CACHE,
            mol_dir=MOL_DIR,
            num_workers=0,
            diffusion_process_args=MODEL_KWARGS["diffusion_process_args"],
            pairformer_args=MODEL_KWARGS["pairformer_args"],
            msa_args=MODEL_KWARGS["msa_args"],
            **(opts.get("affinity") or {}),
        )
        leg_path = AL.write_request(
            item_out / "_affinity_leg" / f"{stem}_s{seed}", leg_req, _rng_state()
        )
        rc = AL.execute(leg_path)
        affinity_json = item_out / "predictions" / rec.id / f"affinity_{rec.id}.json"
        timing["affinity_s"] = round(time.time() - t, 2)
        if rc != 0 or not affinity_json.is_file():
            raise RuntimeError(
                f"upstream's affinity leg exited {rc} and {affinity_json.name} is "
                f"{'absent' if not affinity_json.is_file() else 'present'} "
                f"(its transcript is above)"
            )

    files = sorted(str(p) for p in (item_out / "predictions").rglob("*") if p.is_file())
    return {
        "out_dir": str(item_out),
        "files": files,
        "timing": timing,
        "peak_alloc_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
        "peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 2),
    }


# ----------------------------------------------------------------------- serve
LAST_REQUEST = time.time()
# How long an orphaned worker keeps the card before giving it back. Long enough
# that a request in flight when the parent died still finishes and its answer is
# written; short enough that a crashed MCP server does not strand several GiB.
ORPHAN_GRACE_S = float(os.environ.get("TOOLUNIVERSE_RESIDENT_ORPHAN_GRACE_S", "120"))


def _orphan_watchdog() -> None:
    """Exit once the process that started this one is gone and nothing is in flight.

    The supervisor starts the worker in a session of its own so that a Ctrl-C to
    the MCP server does not kill a prediction halfway through. The cost of that
    choice is that nothing reaps the worker when the server dies instead of
    exiting cleanly -- and a model nobody can reach, still holding the device, is
    the worst of both worlds on a box meant to share one GPU. Being reparented to
    init is the signal; the grace period is what keeps it from firing on a
    request that outlives a crash.
    """
    while True:
        time.sleep(5)
        if os.getppid() != 1:
            continue
        idle = time.time() - LAST_REQUEST
        if idle < ORPHAN_GRACE_S:
            continue
        say(
            f"orphaned (parent gone) and idle {idle:.0f}s >= {ORPHAN_GRACE_S:.0f}s: "
            f"releasing the GPU and exiting"
        )
        os._exit(0)  # the serve loop is blocked in accept(); nothing to unwind


def _handle(req: dict) -> dict:
    op = req.get("op")
    if op == P.OP_PING:
        return {
            "ok": True,
            "model": args.slug,
            "ready": True,
            "uptime_s": round(time.time() - T0, 1),
            "build_s": round(BUILD_S, 1),
        }
    if op == P.OP_SHUTDOWN:
        return {"ok": True}
    if op == P.OP_PREDICT:
        globals()["LAST_REQUEST"] = time.time()
        torch.cuda.reset_peak_memory_stats()
        return {"ok": True, "result": _predict_one(req)}
    return {"ok": False, "error": f"unknown op {op!r}", "reason": "unknown_op"}


def main() -> int:
    path = args.socket
    if os.path.exists(path):
        os.unlink(path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    os.chmod(path, 0o600)  # this uid only; the MCP server runs as the same user
    srv.listen(16)
    threading.Thread(target=_orphan_watchdog, name="orphan-watchdog", daemon=True).start()
    say(f"listening on {path}")
    try:
        while True:
            conn, _ = srv.accept()
            buf = bytearray()
            try:
                while True:
                    try:
                        req = P.recv_line(conn, buf)
                    except P.ProtocolError:
                        break
                    try:
                        reply = _handle(req)
                    except Exception as exc:  # a bad request must not kill the model
                        reply = {
                            "ok": False,
                            "error": f"{type(exc).__name__}: {exc}",
                            "reason": "request_failed",
                            "traceback": traceback.format_exc(limit=8),
                        }
                    globals()["LAST_REQUEST"] = time.time()
                    P.send_line(conn, reply)
                    if req.get("op") == P.OP_SHUTDOWN:
                        say("shutdown requested")
                        return 0
            finally:
                conn.close()
    finally:
        srv.close()
        if os.path.exists(path):
            os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
