"""ESM C held resident on the GPU, answering one request at a time.

Run by the model's own interpreter with the kit's mode variable in the
environment::

    ESMC_OPT=exact <model python> esmc_resident_worker.py --socket … --slug … --variant 6b

That is the whole activation, and it is the form 30 of the 36 kits offer. The
kit installs ``esmc_opt_autoload.pth``, which imports ``esmc_opt._autoload`` at
interpreter start; with ``ESMC_OPT`` naming a mode, a meta-path finder waits for
the first import of ``esm`` and calls ``esmc_opt.enable(mode, strict=True)``
*before* that package's body executes. The variable's name is the kit's own and
is read off the kit by ``kit_launch``'s probe -- ``_autoload.ENV = "ESMC_OPT"``,
because this kit's ``modes.py`` defines no ``ENV`` at all -- never guessed from
the slug.

**Who holds the weights, and why this one differs from ESMFold2's.** This kit
wraps ``ESMC.from_pretrained`` (``esmc_opt/stack.py``), and under a kit mode its
``pipe`` lever does not merely observe the load: it *replaces* it, with
``from_pretrained_sdk`` doing device-side weight loading sized on the snapshot
directory. So under ``ESMC_OPT=exact`` the kit reads the checkpoint and this
worker holds what the kit built; under ``off`` upstream's own loader reads it
and the worker holds that. Either way exactly one client lives in this process
for its whole life, which is the point -- but the two are not the same claim, so
the ready line and every reply say which, read from the kit's own activation
report rather than assumed.

**One variant per process, and it is a rule of the kit's, not a preference.**
``esmc_opt/stack.py`` refuses a second variant by name: "one lever set per
process", because the levers are resolved per variant. The variant also chooses
the checkpoint, so it cannot come out of the kit's mode row; it is this
script's own ``--variant``. Unlike ESMFold2's, it does not have to be exported
before the trigger import: this kit derives the variant from the model name
passed to ``ESMC.from_pretrained``, which happens after.

**This kit does not degrade.** "A mode is all of its levers": a lever of the
mode that cannot be applied when the client is built makes ``from_pretrained``
print ``NOT ACTIVE: partial activation`` and raise. That failure is upstream's
to report, so nothing here catches it -- a worker that swallowed it would serve
stock under the name of the kit.

**Why hold it.** The checkpoint is 25.4 GiB of fp32 safetensors for a 6-billion
parameter model; ESMFold2, which loads the same one, measured roughly 25 s of
start-up per process. A process that exits after each request pays all of it
again, for a forward pass that then takes well under a second.

One request at a time: two inside one CUDA context would interleave their
allocations and make an out-of-memory attributable to neither.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
from pathlib import Path

# stock/PINS.json "variants": the size -> the SDK model name the kit's own
# variant table maps back (modes.VARIANT_MODEL_NAME), and the hidden width each
# snapshot's config.json declares.
MODEL_NAME = {"300m": "esmc_300m", "600m": "esmc_600m", "6b": "esmc_6b"}
HF_REPO = {
    "300m": "biohub/ESMC-300M",
    "600m": "biohub/ESMC-600M",
    "6b": "biohub/ESMC-6B",
}

# Bounds on what one reply may carry. An ESMC-6B residue vector is 2560 floats,
# which is roughly 23 kB of JSON on its own, and the MCP transport truncated
# Chai-1's oversized reply at exactly 100,000 characters -- producing invalid
# JSON rather than an honest refusal. So the inline window is counted in
# FLOATS, not in residues, and a caller who wants the whole matrix gets a file.
MAX_INLINE_VALUES = 20_000
MAX_POSITIONS_INLINE = 4_000
MAX_RESIDUES = 4_096
AA = set("ACDEFGHIKLMNPQRSTVWYBXZJUO")

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="esmc", help="provider slug, echoed in ping")
ap.add_argument(
    "--variant",
    default="6b",
    choices=sorted(MODEL_NAME),
    help="one variant per process (the kit's rule): the checkpoint size",
)
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
    print(f"[esmc-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds ESM C's pinned stack and
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
            f"[esmc-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

VARIANT = args.variant
MODE = (os.environ.get("ESMC_OPT") or "off").strip().lower() or "off"
# The weights are pinned and verified before this process starts; nothing is
# fetched at request time. run.sh's own Setup block exports both of these and
# this worker is not run through run.sh, so it sets them itself -- and before
# huggingface_hub is imported, which is when HF_HOME is read.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np  # noqa: E402
import torch  # noqa: E402

torch.set_grad_enabled(False)

# The kit's trigger is the top-level `esm` import: the finder fires on it and
# runs esmc_opt.enable() before esm's own body executes.
from esm.models.esmc import ESMC  # noqa: E402
from esm.sdk.api import ESMProtein, LogitsConfig  # noqa: E402

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} variant={VARIANT} mode={MODE}"
)

_t = time.time()
# Upstream's own call, with upstream's own defaults for everything else --
# use_flash_attn stays True, which is both the library default and what the
# kit's modes.load_call names for every mode and regime. Under a kit mode the
# wrapper esmc_opt installed on this classmethod routes the load through the
# pipe lever; under `off` nothing is wrapped and this is the stock load.
CLIENT = ESMC.from_pretrained(MODEL_NAME[VARIANT], device=torch.device(DEVICE))
BUILD_S = time.time() - _t


def _activation_report() -> dict:
    """The kit's own account of what it did, or an empty one under `off`."""
    if MODE in ("", "off"):
        return {}
    try:
        import esmc_opt

        return dict(esmc_opt.status() or {})
    except Exception as exc:  # noqa: BLE001 - the kit's absence is not fatal here
        return {"status_error": f"{type(exc).__name__}: {exc}"}


REPORT = _activation_report()
LEVERS = [str(x) for x in (REPORT.get("levers_applied") or [])]
# Read, not assumed: the `pipe` lever replaces ESMC.from_pretrained's loader
# with its own device-side one, so when it applied the kit did the reading.
HOLDER = "kit" if "pipe" in LEVERS else "worker"
# `hidden_size` is the aligned spelling; the published config.json files still
# say `d_model` and esm maps the one onto the other at load
# (esm/models/esmc/config.py _LEGACY_KEYS), so both are asked for.
_CFG = CLIENT.model.config
EMBED_DIM = int(getattr(_CFG, "hidden_size", 0) or getattr(_CFG, "d_model", 0) or 0)
say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s "
    f"(variant={VARIANT} d_model={EMBED_DIM} weights_held_by={HOLDER} "
    f"kit={MODE} levers_applied={','.join(LEVERS) or 'none'})"
)


def _sequence(text: str) -> str:
    """One protein sequence out of a raw string or a single-record FASTA."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    if any(ln.startswith(">") for ln in lines):
        records, current = [], []
        for ln in lines:
            if ln.startswith(">"):
                if current:
                    records.append("".join(current))
                current = []
            elif ln:
                current.append(ln)
        if current:
            records.append("".join(current))
        if len(records) != 1:
            raise ValueError(
                f"the input FASTA holds {len(records)} records; this operation "
                f"embeds one sequence per request"
            )
        seq = records[0]
    else:
        seq = "".join(lines)
    seq = re.sub(r"\s+", "", seq).upper()
    if not seq:
        raise ValueError("the input carries no sequence")
    bad = sorted(set(seq) - AA)
    if bad:
        raise ValueError(f"the sequence holds {bad} , which are not amino-acid letters")
    if len(seq) > MAX_RESIDUES:
        raise ValueError(
            f"the sequence is {len(seq)} residues; this worker accepts "
            f"{MAX_RESIDUES} at most (a longer one is a memory decision, not a "
            f"model limit: ESM C uses rotary position embeddings)"
        )
    return seq


def _floats(tensor, decimals: int) -> list:
    return [round(float(x), decimals) for x in tensor.reshape(-1).tolist()]


def _predict_one(req: dict) -> dict:
    """One forward pass. The request carries the sequence; the options decide
    how much of the (large) result comes back inline."""
    seq = _sequence(req.get("input") or req.get("sequence") or "")
    opts = dict(req.get("options") or {})
    decimals = max(1, min(8, int(opts.get("decimals", 5))))
    top_n = max(0, min(200, int(opts.get("top_n", 10))))

    if DEVICE == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()
    protein_tensor = CLIENT.encode(ESMProtein(sequence=seq))
    out = CLIENT.logits(
        protein_tensor,
        LogitsConfig(sequence=True, return_embeddings=True),
    )
    if DEVICE == "cuda":
        torch.cuda.synchronize()
    forward_s = time.time() - t

    # [1, L+2, ...]: the tokenizer wraps the sequence in BOS and EOS, so the
    # residue rows are 1..L and row 0 is the sequence-level (BOS) vector.
    emb = out.embeddings[0].float()
    logits = out.logits.sequence[0].float()
    tokens = protein_tensor.sequence
    if emb.shape[0] != len(seq) + 2:
        raise RuntimeError(
            f"the model returned {emb.shape[0]} positions for {len(seq)} "
            f"residues; expected {len(seq) + 2} (BOS + residues + EOS)"
        )
    residues = emb[1:-1]  # (L, d)
    res_logits = logits[1:-1]  # (L, 64)
    res_tokens = tokens[1 : 1 + len(seq)].to(res_logits.device)

    log_probs = torch.log_softmax(res_logits, dim=-1)
    observed = log_probs.gather(1, res_tokens.long().unsqueeze(1)).squeeze(1)
    mean_ll = float(observed.mean())

    mean_vec = residues.mean(dim=0)
    body = {
        "model": "ESM C",
        "variant": VARIANT,
        "hf_repo": HF_REPO[VARIANT],
        "sequence_length": len(seq),
        "embedding_dim": int(residues.shape[1]),
        "pooling": "mean over residues, BOS/EOS excluded",
        "mean_embedding": _floats(mean_vec, decimals),
        "mean_embedding_norm": round(float(mean_vec.norm()), 6),
        "mean_log_likelihood": round(mean_ll, 6),
        "pseudo_perplexity": round(math.exp(-mean_ll), 4),
        "timing": {"forward_s": round(forward_s, 3)},
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "levers_applied": LEVERS,
    }
    if opts.get("include_cls_embedding"):
        body["cls_embedding"] = _floats(emb[0], decimals)

    if top_n:
        order = torch.argsort(observed)[:top_n]
        body["least_likely_residues"] = [
            {
                "position": int(i) + 1,
                "residue": seq[int(i)],
                "log_prob": round(float(observed[int(i)]), 6),
            }
            for i in order
        ]

    if opts.get("per_residue_log_prob"):
        if len(seq) > MAX_POSITIONS_INLINE:
            raise ValueError(
                f"per_residue_log_prob was asked for a {len(seq)}-residue "
                f"sequence; the inline limit is {MAX_POSITIONS_INLINE} positions"
            )
        body["per_residue_log_prob"] = [round(float(x), decimals) for x in observed]

    window = opts.get("residue_range")
    if window:
        start, end = int(window[0]), int(window[1])
        if not (1 <= start <= end <= len(seq)):
            raise ValueError(
                f"residue_range {[start, end]} is outside 1..{len(seq)} "
                f"(1-based and inclusive)"
            )
        count = (end - start + 1) * int(residues.shape[1])
        if count > MAX_INLINE_VALUES:
            raise ValueError(
                f"residue_range {[start, end]} is {count} floats, over the "
                f"{MAX_INLINE_VALUES} an inline reply may carry; narrow the "
                f"range (at d={int(residues.shape[1])} that is "
                f"{MAX_INLINE_VALUES // max(1, int(residues.shape[1]))} residues) "
                f"or ask for per_residue_file"
            )
        body["residue_embeddings"] = {
            "start": start,
            "end": end,
            "values": [_floats(residues[i], decimals) for i in range(start - 1, end)],
        }

    if opts.get("per_residue_file"):
        out_dir = Path(req.get("out_dir") or ".")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{req.get('name') or 'esmc'}_residue_embeddings.npy"
        # float32 on purpose: the model computes in bfloat16 and float32 is the
        # smallest format that carries every bit of it without a dtype a
        # downstream reader may not have.
        np.save(path, residues.cpu().numpy().astype(np.float32))
        body["per_residue_file"] = {
            "path": str(path),
            "format": "numpy .npy",
            "dtype": "float32",
            "shape": [int(residues.shape[0]), int(residues.shape[1])],
            "bytes": path.stat().st_size,
        }

    if DEVICE == "cuda":
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "variant": VARIANT,
        "embedding_dim": EMBED_DIM,
        "weights_held_by": HOLDER,
        "kit_mode": MODE,
        "levers_applied": LEVERS,
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
