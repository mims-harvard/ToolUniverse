"""ProGen2 held resident on the GPU, answering one request at a time.

Run by the model's own interpreter, with no mode variable, because this kit has
none::

    <model python> progen2_resident_worker.py --socket … --slug … \
        --model progen2-base --kit <checkout>/progen2 --weights-root ~/.progen2

**What this worker holds, and who holds it.** ``[kit] mode = "off"`` (provider.toml
gives the two independent reasons), so nothing of ``progen2_opt`` is imported here
and nothing patches the stock. The worker therefore holds the weights ITSELF --
``weights_held_by = "worker"`` on the ready line and in every reply, which is the
honest answer to the standard's third question and the one that follows from `off`:
under a kit mode the kit's ``oneread_mmap`` lever would replace the load and the
answer would be ``kit``.

**There is no installed ProGen2 package anywhere.** Upstream ``salesforce/progen``
at ``c27a419c`` ships no ``setup.py`` and no ``pyproject.toml`` -- stock/PINS.json
says so: "not a package: a source checkout run from its own progen2/ directory".
So the pinned checkout's directory goes on ``sys.path`` and ``models.progen`` is
imported from there. That directory is ``$PROGEN2_STOCK_DIR``, which launch.py sets
from the kit checkout and which ``stock/check_pins.py`` hashed file-for-file at
setup.

**What this worker does NOT do, and each absence is upstream's own code read
rather than a simplification.**

* It does not ``chdir``. The stock CLIs resolve ``tokenizer.json`` and
  ``./checkpoints/<model>`` against the current directory, which is why the kit
  builds a run directory of symlinks for them. A resident worker also has to write
  a caller's ``out_dir``, so both paths are resolved absolutely here instead.
* It does not fork anything. ``num_workers`` does not arise -- neither stock CLI
  uses a DataLoader -- but the rule behind it does: a resident worker that has run
  host-tensor work must not let a library fork, and nothing here starts a pool.
* It does not reset ``max_memory_reserved`` between requests. ``peak_reserved_gib``
  is a running high-water mark, which is what a host adding budgets up needs, and
  it is why a VRAM ladder must ascend in a fresh worker.

**Numerics are the stock's, op for op.** ``_log_likelihood`` is likelihood.py's own
``ll()`` -- the shift, the terminal removal, the restriction to token ids 5..29, the
``target - 5`` offset and ``torch.nn.functional.cross_entropy`` -- inside
``torch.no_grad()`` and ``torch.cuda.amp.autocast(enabled=fp16)``, which is where
likelihood.py puts them (L163, L176). ``ll_sum`` and ``ll_mean`` are its step 7: the
mean of the left-to-right and right-to-left directions, the reverse being the string
reversed whole, terminals included. Generation is sample.py's ``sample()`` and
``truncate()`` verbatim, with ``generate()`` outside autocast as sample.py has it.

**One size per process**, which is the kit's rule and upstream's shape both: the
size chooses the checkpoint and ``stack.activate`` refuses a second variant in one
process by name. ``--model`` is this script's own argument, as ``--variant`` is
esmc's and e1's.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path

# The seven sizes' upstream checkpoint names, from stock/PINS.json `weights`.
MODEL_NAMES = (
    "progen2-small",
    "progen2-medium",
    "progen2-oas",
    "progen2-base",
    "progen2-large",
    "progen2-BFD90",
    "progen2-xlarge",
)

# ProGen2's alphabet is the tokenizer's own vocabulary minus the three specials and
# the two terminals: 25 letters, A..Z without J (stock/PINS.json `tokenizer.ids`).
AA = set("ABCDEFGHIKLMNOPQRSTUVWXYZ")
# '1' is the N-terminus marker and '2' the C-terminus marker. likelihood.py treats
# ids 3/4 as bos/eos (L185-191) and sample.py truncates at the first one (L78-87).
TERMINALS = ("1", "2")

# Bounds on what one reply may carry. Chai-1's oversized reply was truncated by the
# MCP transport at exactly 100,000 characters, producing invalid JSON rather than an
# honest refusal, so every window below is REFUSED when it is too large and never
# clipped. A per-token log-probability array is one float per residue, so the
# position count is the useful unit here (unlike esmc, where one residue is 2560
# floats and the count has to be in floats).
MAX_POSITIONS_INLINE = 2_048

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--socket", required=True, help="Unix socket to serve on")
ap.add_argument("--slug", default="progen2", help="provider slug, echoed in ping")
ap.add_argument(
    "--model",
    default="progen2-base",
    choices=MODEL_NAMES,
    help="one size per process (the kit's rule): the checkpoint name",
)
ap.add_argument("--kit", default="", help="the kit checkout's progen2/ directory")
ap.add_argument(
    "--weights-root",
    default="",
    help="PROGEN2_WEIGHTS: <root>/<model>/{pytorch_model.bin, config.json}",
)
ap.add_argument(
    "--max-generate-length",
    type=int,
    default=1024,
    help="this provider's ceiling on generate()'s max_length, in tokens",
)
ap.add_argument(
    "--max-num-samples",
    type=int,
    default=16,
    help="this provider's ceiling on num_return_sequences per call",
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
    print(f"[progen2-resident] {msg}", flush=True)


def _load_worker_base():
    """The shared runtime, by path: this process holds ProGen2's pinned stack
    (Python 3.9, torch 2.8.0+cu129, transformers 4.16.2) and nothing of
    ToolUniverse, and importing the package would defeat that."""
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
            f"[progen2-resident] the shared worker runtime is not at {path} "
            f"(set TOOLUNIVERSE_REMOTE_WORKER_BASE to its path)"
        )
    spec = importlib.util.spec_from_file_location("_tu_worker_base", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WB = _load_worker_base()

MODEL_NAME = args.model
# `off` is this kit's own word for "stock ProGen2, exactly as released", and it is
# the only configuration reachable on this architecture. There is no mode VARIABLE
# to read -- the kit has none -- so the manifest's value arrives through launch.py
# only as a fact to report, never as a switch.
KIT_MODE = "off"

KIT_HOME = Path(args.kit).expanduser() if args.kit else None
STOCK_DIR = Path(
    os.environ.get("PROGEN2_STOCK_DIR")
    or (KIT_HOME / "stock" / "src" / "progen2" if KIT_HOME else "")
).expanduser()
WEIGHTS_ROOT = Path(
    args.weights_root or os.environ.get("PROGEN2_WEIGHTS") or ""
).expanduser()
CKPT_DIR = WEIGHTS_ROOT / MODEL_NAME

for label, path, needs in (
    ("the pinned stock checkout", STOCK_DIR, "tokenizer.json"),
    ("the checkpoint directory", CKPT_DIR, "pytorch_model.bin"),
):
    if not (path / needs).is_file():
        raise _refuse(
            f"[progen2-resident] {label} is not at {path} (no {needs}); run "
            f"`tu remote setup progen2` and read its named refusal"
        )

# The stock scripts' own set_env() (sample.py / likelihood.py L35-36). launch.py sets
# it too; a hand-run worker needs it here, and it has to be set before tokenizers is
# imported rather than after.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Upstream is a source checkout, not a package: this is how `models.progen` is found.
sys.path.insert(0, os.fspath(STOCK_DIR))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

from models.progen.modeling_progen import ProGenForCausalLM  # noqa: E402

torch.set_grad_enabled(False)

DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
# sample.py L136-140 / likelihood.py L142-146: no CUDA device means cpu, and cpu
# means fp32. The same rule rather than a different one, so a CPU answer is the
# stock's CPU answer.
FP16 = DEVICE != "cpu"
say(
    f"imports done t={time.time() - T0:.1f}s torch={torch.__version__} "
    f"device={DEVICE} model={MODEL_NAME} kit_mode={KIT_MODE} fp16={FP16}"
)

with open(CKPT_DIR / "config.json") as fh:
    CONFIG = json.load(fh)
# The size's context window. Every mode bounds inputs by it and `score` fails a
# longer sequence by name (kit README, Notes); the stock's causal-bias buffer ends
# there too (modeling_progen.py L65-70), so it is a hard limit rather than a policy.
N_POSITIONS = int(CONFIG.get("n_positions", 1024))

_t = time.time()
# Upstream's own call, verbatim (sample.py L63-67 / likelihood.py L63-67).
# `revision='float16'` is inert for a local directory and is kept because dropping it
# would be an edit to the stock's load; `low_cpu_mem_usage=True` installs every
# checkpoint tensor AS STORED, so the parameters' dtype is config.json's torch_dtype.
MODEL = ProGenForCausalLM.from_pretrained(
    os.fspath(CKPT_DIR),
    revision="float16",
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
).to(torch.device(DEVICE))
MODEL.eval()
BUILD_S = time.time() - _t

TOKENIZER = Tokenizer.from_str((STOCK_DIR / "tokenizer.json").read_text())
PAD_ID = TOKENIZER.encode("<|pad|>").ids[0]
PARAM_BYTES = sum(p.numel() * p.element_size() for p in MODEL.parameters())

say(
    f"model resident on {DEVICE} in {BUILD_S:.1f}s (model={MODEL_NAME} "
    f"n_positions={N_POSITIONS} params={PARAM_BYTES / 2**30:.2f} GiB "
    f"dtype={next(MODEL.parameters()).dtype} weights_held_by=worker "
    f"kit={KIT_MODE} levers_applied=none)"
)


def _set_seed(seed: int, deterministic: bool = True) -> None:
    """likelihood.py / sample.py's own ``set_seed`` (L35-45), per request.

    The stock CLIs call it once because they are one process per call. A resident
    worker is many calls in one process, so a caller that names a seed gets the run
    that seed would have produced on its own.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = not deterministic


def _lines(text: str) -> list:
    """The content lines of an input, with blank and commented ones dropped.

    ``#`` and ``;`` start a comment. Neither is a residue, a terminal marker or a
    FASTA header, so dropping them cannot discard sequence -- and it lets
    ``smoke/input.txt`` carry the provenance of the sequence it holds, which is the
    one thing a smoke input most needs to say.
    """
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line and not line.startswith(("#", ";")):
            out.append(line)
    return out


def _context(text: str) -> str:
    """One ProGen2 context string out of raw text or a single-record FASTA.

    A string already carrying '1' or '2' is taken as a context the caller built --
    ProGen2's own notation, and what the kit's README types
    (``X=1MGHGVSRPPV…EQ2``). A string of amino acids alone is wrapped ``1<seq>2``,
    the N-to-C form every example uses. Nothing is silently repaired: a terminal in
    the middle is refused, because likelihood.py asserts their absence from the
    scored target and the assertion would otherwise fire inside the forward.
    """
    lines = _lines(text)
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
                f"takes one sequence per request"
            )
        raw = records[0]
    else:
        raw = "".join(lines)
    raw = re.sub(r"\s+", "", raw).upper()
    if not raw:
        raise ValueError("the input carries no sequence")

    body = raw
    if raw[0] in TERMINALS or raw[-1] in TERMINALS:
        if raw[0] not in TERMINALS or raw[-1] not in TERMINALS:
            raise ValueError(
                f"the sequence carries a terminal marker at one end only "
                f"({raw[0]!r} … {raw[-1]!r}); ProGen2 contexts are '1<seq>2' "
                f"(N to C) or '2<seq>1' (C to N), or give the amino acids alone "
                f"and they will be wrapped"
            )
        body = raw[1:-1]
        ctx = raw
    else:
        ctx = TERMINALS[0] + raw + TERMINALS[1]

    bad = sorted(set(body) - AA)
    if bad:
        raise ValueError(
            f"the sequence holds {bad}, which are neither amino-acid letters nor "
            f"ProGen2 terminal markers at the ends"
        )
    if len(ctx) > N_POSITIONS:
        raise ValueError(
            f"the context is {len(ctx)} tokens and {MODEL_NAME}'s context window "
            f"is {N_POSITIONS} (config.json n_positions); the stock refuses a "
            f"longer sequence by name in every mode"
        )
    return ctx


def _log_likelihood(context: str, reduction: str) -> float:
    """likelihood.py's ``ll()`` (L172-199), op for op, for one direction."""
    with torch.no_grad():
        with torch.cuda.amp.autocast(enabled=FP16):
            target = torch.tensor(TOKENIZER.encode(context).ids).to(DEVICE)
            logits = MODEL(target, labels=target).logits

            # shift
            logits = logits[:-1, ...]
            target = target[1:]

            # remove terminals
            bos_token, eos_token = 3, 4
            if target[-1] in [bos_token, eos_token]:
                logits = logits[:-1, ...]
                target = target[:-1]

            if int((target == bos_token).sum()) or int((target == eos_token).sum()):
                raise ValueError(
                    "the sequence carries a terminal marker ('1' or '2') other "
                    "than at its ends; the stock asserts their absence from the "
                    "scored target"
                )

            # remove unused logits
            first_token, last_token = 5, 29
            logits = logits[:, first_token : (last_token + 1)]
            target = target - first_token

            return float(
                -torch.nn.functional.cross_entropy(
                    input=logits.view(-1, logits.size(-1)),
                    target=target.view(-1),
                    reduction=reduction,
                )
            )


def _per_token_log_prob(context: str) -> "np.ndarray":
    """The log-probability of each scored token, left to right.

    Not part of the stock CLI, which prints only the two reductions -- but it is the
    same tensor its ``reduction='mean'`` averages, taken before the reduction rather
    than computed a second way, so the mean of this array is ``ll_mean`` for that
    direction by construction.
    """
    with torch.no_grad():
        with torch.cuda.amp.autocast(enabled=FP16):
            target = torch.tensor(TOKENIZER.encode(context).ids).to(DEVICE)
            logits = MODEL(target, labels=target).logits
            logits = logits[:-1, ...]
            target = target[1:]
            bos_token, eos_token = 3, 4
            if target[-1] in [bos_token, eos_token]:
                logits = logits[:-1, ...]
                target = target[:-1]
            logits = logits[:, 5:30]
            target = target - 5
            lp = torch.log_softmax(logits.float(), dim=-1)
            return (
                lp.gather(1, target.view(-1, 1).long())
                .squeeze(1)
                .cpu()
                .numpy()
                .astype(np.float32)
            )


def _score(req: dict, opts: dict) -> dict:
    ctx = _context(req.get("input") or req.get("sequence") or "")
    reverse = ctx[::-1]
    decimals = max(1, min(8, int(opts.get("decimals", 6))))

    t = time.time()
    lr_sum = _log_likelihood(ctx, "sum")
    rl_sum = _log_likelihood(reverse, "sum")
    lr_mean = _log_likelihood(ctx, "mean")
    rl_mean = _log_likelihood(reverse, "mean")
    if DEVICE != "cpu":
        torch.cuda.synchronize()
    forward_s = time.time() - t

    # likelihood.py step 7 (L288-299): the two directions averaged. This is what the
    # stock prints as ll_sum= and ll_mean=, and what `output_keys` names.
    ll_sum = 0.5 * (lr_sum + rl_sum)
    ll_mean = 0.5 * (lr_mean + rl_mean)

    body = {
        "model": "ProGen2",
        "checkpoint": MODEL_NAME,
        "task": "score",
        "context": ctx if len(ctx) <= 256 else ctx[:253] + "...",
        "sequence_length": len(ctx) - 2,
        "context_tokens": len(ctx),
        "ll_sum": round(ll_sum, decimals),
        "ll_mean": round(ll_mean, decimals),
        "ll_left_to_right_sum": round(lr_sum, decimals),
        "ll_right_to_left_sum": round(rl_sum, decimals),
        "ll_left_to_right_mean": round(lr_mean, decimals),
        "ll_right_to_left_mean": round(rl_mean, decimals),
        "perplexity": round(math.exp(-ll_mean), 4),
        "reduction_note": (
            "ll_sum and ll_mean are the mean of the left-to-right and "
            "right-to-left directions, as likelihood.py prints them"
        ),
        "timing": {"forward_s": round(forward_s, 3)},
        "weights_held_by": "worker",
        "kit_mode": KIT_MODE,
        "levers_applied": [],
    }

    want_inline = bool(opts.get("per_token_log_prob"))
    want_file = bool(opts.get("per_token_file"))
    if want_inline or want_file:
        values = _per_token_log_prob(ctx)
        if want_inline:
            if len(values) > MAX_POSITIONS_INLINE:
                raise ValueError(
                    f"per_token_log_prob was asked for {len(values)} positions; "
                    f"the inline limit is {MAX_POSITIONS_INLINE} -- ask for "
                    f"per_token_file instead"
                )
            body["per_token_log_prob"] = [round(float(x), decimals) for x in values]
            body["per_token_direction"] = "left to right, scored tokens only"
        if want_file:
            out_dir = Path(req.get("out_dir") or ".")
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{req.get('name') or 'progen2'}_log_probs.npy"
            np.save(path, values)
            body["per_token_file"] = {
                "path": str(path),
                "format": "numpy .npy",
                "dtype": "float32",
                "shape": [int(values.shape[0])],
                "bytes": path.stat().st_size,
                "direction": "left to right, scored tokens only",
            }
    return body


def _generate(req: dict, opts: dict) -> dict:
    raw = "".join(_lines(req.get("input") or req.get("sequence") or ""))
    # A bare '1' is sample.py's own --context default's spirit: the start token
    # alone, which asks for an unconditioned sequence. Anything else is a prompt and
    # goes through the same validation as a scored sequence, except that an unclosed
    # prompt is exactly what generation is for -- so a prefix needs its '1' and NOT
    # its '2'.
    context = re.sub(r"\s+", "", raw).upper() or TERMINALS[0]
    if context[0] not in TERMINALS:
        context = TERMINALS[0] + context
    bad = sorted(set(context[1:]) - AA - set(TERMINALS))
    if bad:
        raise ValueError(
            f"the prompt holds {bad}, which are neither amino-acid letters nor "
            f"ProGen2 terminal markers"
        )

    num_samples = int(opts.get("num_samples", 1))
    max_length = int(opts.get("max_length", 256))
    temperature = float(opts.get("temperature", 0.2))
    top_p = float(opts.get("top_p", 0.95))
    seed = int(req.get("seed") if req.get("seed") is not None else opts.get("seed", 42))

    # Bounded in the worker as well as in the tool, for the esmc reason: a request
    # that did not come through the MCP server must not be able to allocate a K/V
    # cache nothing budgeted for. The generate route's reserve is roughly linear in
    # num_samples x max_length -- see provider.toml [gpu].
    if not 1 <= num_samples <= args.max_num_samples:
        raise ValueError(
            f"num_samples must be between 1 and {args.max_num_samples} "
            f"(this provider's ceiling; the budget under [gpu] is declared at it)"
        )
    ceiling = min(args.max_generate_length, N_POSITIONS)
    if not len(context) < max_length <= ceiling:
        raise ValueError(
            f"max_length must be greater than the {len(context)}-token prompt and "
            f"at most {ceiling} (this provider's ceiling, and {MODEL_NAME}'s "
            f"context window is {N_POSITIONS})"
        )
    if not 0.0 < temperature <= 2.0:
        raise ValueError("temperature must be greater than 0 and at most 2.0")
    if not 0.0 < top_p <= 1.0:
        raise ValueError("top_p must be greater than 0 and at most 1.0")

    _set_seed(seed, deterministic=bool(opts.get("rng_deterministic", True)))

    t = time.time()
    with torch.no_grad():
        # sample.py's sample() (L69-76), verbatim: no autocast around generate(),
        # which is where the stock puts it (PINS.json precision.fp16_true_means).
        input_ids = torch.tensor(TOKENIZER.encode(context).ids).view([1, -1]).to(DEVICE)
        tokens_batch = MODEL.generate(
            input_ids,
            do_sample=True,
            temperature=temperature,
            max_length=max_length,
            top_p=top_p,
            num_return_sequences=num_samples,
            pad_token_id=PAD_ID,
        )
        completions = TOKENIZER.decode_batch(
            [
                tokens_batch[i, ...].detach().cpu().numpy().tolist()
                for i in range(tokens_batch.shape[0])
            ]
        )
    if DEVICE != "cpu":
        torch.cuda.synchronize()
    sample_s = time.time() - t

    def truncate(sample: str, terminals=TERMINALS) -> str:
        """sample.py's ``truncate`` (L78-87), verbatim."""
        pos = []
        for terminal in terminals:
            find_pos = sample.find(terminal, 1)
            if find_pos != -1:
                pos.append(find_pos)
        if len(pos) > 0:
            return sample[: (min(pos) + 1)]
        return sample

    truncations = [truncate(c) for c in completions]
    sequences = []
    for i, text in enumerate(truncations):
        body = text[1:-1] if text[-1:] in TERMINALS else text[1:]
        sequences.append(
            {
                "index": i,
                "context_and_completion": text,
                "sequence": body,
                "length": len(body),
                "terminated": text[-1:] in TERMINALS,
            }
        )

    return {
        "model": "ProGen2",
        "checkpoint": MODEL_NAME,
        "task": "generate",
        "prompt": context,
        "num_samples": num_samples,
        "max_length": max_length,
        "temperature": temperature,
        "top_p": top_p,
        "seed": seed,
        "sequences": sequences,
        "timing": {"sample_s": round(sample_s, 3)},
        "weights_held_by": "worker",
        "kit_mode": KIT_MODE,
        "levers_applied": [],
    }


def _predict_one(req: dict) -> dict:
    opts = dict(req.get("options") or {})
    task = str(opts.get("task") or "score").lower()
    if task not in ("score", "generate"):
        raise ValueError(f"options.task must be 'score' or 'generate', not {task!r}")
    body = _generate(req, opts) if task == "generate" else _score(req, opts)
    if DEVICE != "cpu":
        # A running high-water mark, deliberately NOT reset per request: a host
        # adding budgets up needs this worker's worst case, and a per-request peak
        # under-reports whatever the caching allocator's pool has grown to. The
        # consequence for measurement is that a ladder must ascend in a fresh
        # worker.
        body["peak_reserved_gib"] = round(torch.cuda.max_memory_reserved() / 2**30, 2)
    return body


def _ready() -> dict:
    return {
        "build_s": round(BUILD_S, 1),
        "device": DEVICE,
        "checkpoint": MODEL_NAME,
        "n_positions": N_POSITIONS,
        "fp16": FP16,
        "parameter_bytes": PARAM_BYTES,
        "weights_held_by": "worker",
        "kit_mode": KIT_MODE,
        "levers_applied": [],
        "max_generate_length": min(args.max_generate_length, N_POSITIONS),
        "max_num_samples": args.max_num_samples,
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
