#!/usr/bin/env python3
"""Does carbonx survive its neighbours, and its own engine dying?

`verify_provider.py` answers whether the provider serves, and
`carbonx_capability_eval.py` answers whether the answers are any good. Neither
asks what happens when two callers arrive at once, or when the thing holding
the model dies -- and carbonx is the first provider on this standard whose
model is a SEPARATE PROCESS, so both questions have answers here that they do
not have anywhere else.

WHAT IT CHECKS, AND WHY IN THIS SHAPE.

**Attribution, not latency.** The worker answers serially by construction
(`worker_base.serve`) and the engine runs with `-np 1`, so concurrency cannot
make this provider faster and is not measured for speed. What it can do is
answer two callers with each other's work -- one worker, one HTTP connection,
one slot -- and that failure looks like a plausible answer to somebody else's
question, which no status code reveals. So every caller asks for the
translation of a DIFFERENT human CDS start: the answer is a deterministic
function of the input, so a misattributed answer scores at chance (~5-15%)
against the input it was given instead of merely looking slightly wrong.
Truth is computed here from the standard genetic code, and the sequences come
from Ensembl, so nothing is asserted from memory.

**The engine's death, which nothing used to see.** `--crash-the-engine`
SIGKILLs the `llama-server` child and then asks for one more answer. The
expected result is a single named refusal naming the engine, the worker
exiting, and the NEXT request answering correctly after the supervisor
rebuilds. Before this provider carried `_EngineGone` the measured result was
instead `ConnectionRefusedError` in 0.0 s, forever, from a worker that kept
answering `ping` with `ready: true`.

It is OFF BY DEFAULT because it kills a process, and `--crash-the-engine`
says so out loud rather than hiding behind a verbosity flag.

Run it against a provider already serving::

    tu remote run carbonx &
    python scripts/remote_validation/carbonx_resilience_check.py --callers 8
    python scripts/remote_validation/carbonx_resilience_check.py --crash-the-engine

Exit codes follow STANDARD section 8: 0 ok, 1 a check failed, 2 usage,
3 nothing was there to test.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

# Transcripts whose first 60 bases this model translates exactly, so a wrong
# answer is a real finding and not the known one-residue drift that appears at
# 100 amino acids.
TRANSCRIPTS = {
    "TP53": "ENST00000269305",
    "BRAF": "ENST00000646891",
    "AGT": "ENST00000366667",
    "CD4": "ENST00000263100",
}
QUESTION = (
    "Translate this coding DNA sequence into its protein sequence. "
    "Reply with the amino-acid sequence only, in one-letter code."
)
CONTEXT = "The sequence is the first 60 bases of a human CDS."
WINDOW = 60
AA_RUN = re.compile(r"[ACDEFGHIKLMNPQRSTVWY]{8,}")
ENGINE_PATTERN = "carbonx/llama.cpp-b11742/llama-server"
WORKER_PATTERN = "carbonx_resident_worker"

_BASES = "TCAG"
_AAS = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON = {
    a + b + c: _AAS[i]
    for i, (a, b, c) in enumerate(
        (a, b, c) for a in _BASES for b in _BASES for c in _BASES
    )
}


def translate(dna: str) -> str:
    return "".join(CODON[dna[i : i + 3]] for i in range(0, len(dna) - 2, 3))


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch_cds(transcript: str, tries: int = 6) -> str:
    """The CDS from Ensembl. `;` between query parameters now 500s -- use `&`."""
    url = (
        f"https://rest.ensembl.org/sequence/id/{transcript}"
        f"?type=cds&content-type=text/plain"
    )
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read().decode().strip().upper()
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
    raise SystemExit(f"carbonx-resilience: Ensembl never answered for {transcript}: {last}")


def build_truth() -> dict:
    out = {}
    for gene, transcript in TRANSCRIPTS.items():
        dna = fetch_cds(transcript)[:WINDOW]
        if len(dna) != WINDOW or set(dna) - set("ACGT"):
            raise SystemExit(f"carbonx-resilience: {gene} CDS is not usable: {dna!r}")
        out[gene] = {"transcript": transcript, "dna": dna, "protein": translate(dna)}
    return out


def protein_of(answer: str) -> str:
    runs = AA_RUN.findall(answer or "")
    return max(runs, key=len) if runs else ""


def identity(got: str, want: str) -> float:
    if not got or not want:
        return 0.0
    n = min(len(got), len(want))
    return sum(1 for i in range(n) if got[i] == want[i]) / max(len(got), len(want))


def _ps_pids(pattern: str) -> list:
    """PIDs whose argv contains ``pattern``, without matching this process.

    `pgrep -f` matches the checker's own command line, and a zombie's argv is
    empty, so both are filtered rather than trusted.
    """
    out = subprocess.run(
        ["ps", "-eo", "pid=,args="], capture_output=True, text=True
    ).stdout
    mine = {os.getpid(), os.getppid()}
    pids = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        head, _, args = line.partition(" ")
        if not head.isdigit() or int(head) in mine:
            continue
        if pattern in args and "ps -eo" not in args:
            pids.append(int(head))
    return pids


def device_gib() -> float:
    out = subprocess.run(
        ["nvidia-smi", "--query-compute-apps=used_memory",
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True,
    ).stdout
    vals = [float(x) for x in out.split() if x.strip().isdigit()]
    return sum(vals) / 1024 if vals else 0.0


def wait_gone(pattern: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _ps_pids(pattern):
            return True
        time.sleep(0.25)
    return False


async def ask(endpoint: str, truth: dict, gene: str, timeout: float):
    from fastmcp import Client

    started = time.time()
    try:
        async with asyncio.timeout(timeout):
            # Its own connection, so the callers are independent and not
            # multiplexed by one client object.
            async with Client(endpoint) as client:
                res = await client.call_tool(
                    "carbonx_ask_dna",
                    {
                        "question": QUESTION,
                        "sequences": {"cds": truth[gene]["dna"]},
                        "context": CONTEXT,
                        "max_tokens": 128,
                        "seed": 0,
                    },
                )
                payload = json.loads(res.content[0].text)
        return {
            "gene": gene,
            "dur": round(time.time() - started, 1),
            "answer": payload.get("answer", ""),
            "error": payload.get("error"),
        }
    except asyncio.TimeoutError:
        return {"gene": gene, "dur": round(time.time() - started, 1),
                "answer": "", "error": f"caller gave up after {timeout}s"}
    except Exception as exc:  # noqa: BLE001 - a checker reports, it does not raise
        return {"gene": gene, "dur": round(time.time() - started, 1),
                "answer": "", "error": f"{type(exc).__name__}: {exc}"}


async def check_attribution(endpoint: str, truth: dict, callers: int,
                            timeout: float) -> bool:
    genes = [list(truth)[i % len(truth)] for i in range(callers)]

    log("-- one request first, which also loads the engine")
    warm = await ask(endpoint, truth, genes[0], timeout)
    if warm["error"]:
        log(f"   the provider is not answering at all: {warm['error']}")
        return False
    log(f"   {warm['dur']}s")

    samples: list = []
    stop = threading.Event()

    def sample() -> None:
        while not stop.is_set():
            samples.append(device_gib())
            stop.wait(1.0)

    watcher = threading.Thread(target=sample, daemon=True)
    watcher.start()

    log(f"-- {callers} callers arriving at once, each on its own connection")
    origin = time.time()
    rows = await asyncio.gather(
        *[ask(endpoint, truth, g, timeout) for g in genes]
    )
    total = time.time() - origin
    stop.set()
    watcher.join(timeout=4)

    ok = True
    for i, row in enumerate(rows):
        got = protein_of(row["answer"])
        own = identity(got, truth[row["gene"]]["protein"])
        best = max(truth, key=lambda k: identity(got, truth[k]["protein"]))
        if row["error"]:
            log(f"   {i:>3} {row['gene']:6} ERROR {row['error'][:70]}")
            ok = False
        elif own <= 0.5:
            log(f"   {i:>3} {row['gene']:6} MISATTRIBUTED -> {best} "
                f"({own * 100:.0f}% to its own input); said {got!r}")
            ok = False
        else:
            log(f"   {i:>3} {row['gene']:6} {row['dur']:>5.1f}s  "
                f"own input {own * 100:.0f}%")

    held = [s for s in samples if s > 0]
    log(f"   {sum(1 for r in rows if not r['error'])}/{callers} answered in "
        f"{total:.1f}s" + (
            f"; footprint {min(held):.2f}-{max(held):.2f} GiB"
            if held else "; footprint unavailable"))
    return ok


async def check_recovery(endpoint: str, truth: dict, timeout: float) -> bool:
    engines = _ps_pids(ENGINE_PATTERN)
    if not engines:
        log("-- no llama-server is running; send one request first")
        return False

    log(f"-- SIGKILL the engine {engines}, the death the supervisor cannot see")
    for pid in engines:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    wait_gone(ENGINE_PATTERN)

    log("-- the request that meets the dead engine")
    first = await ask(endpoint, truth, "TP53", timeout)
    err = first["error"] or ""
    log(f"   {first['dur']}s  {err[:160]}")
    named = "worker_exiting" in err and "llama-server" in err
    if not named:
        log("   FAILED: an engine death must be named as a verdict about the "
            "worker, not reported as one more failed request")
    gone = wait_gone(WORKER_PATTERN, timeout=30.0)
    if not gone:
        log("   FAILED: the worker is still up, so nothing will rebuild it")

    log("-- the next request, which must recover")
    second = await ask(endpoint, truth, "BRAF", timeout)
    if second["error"]:
        log(f"   FAILED: {second['error'][:160]}")
        return False
    got = protein_of(second["answer"])
    own = identity(got, truth["BRAF"]["protein"])
    log(f"   {second['dur']}s  own input {own * 100:.0f}%  engine="
        f"{_ps_pids(ENGINE_PATTERN)}")
    return named and gone and own > 0.5


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--endpoint", default="http://127.0.0.1:8064/mcp")
    ap.add_argument("--callers", type=int, default=8,
                    help="simultaneous callers for the attribution check")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="per-request ceiling; a rebuild is inside it")
    ap.add_argument("--crash-the-engine", action="store_true",
                    help="SIGKILL the llama-server child and check recovery")
    args = ap.parse_args()

    if args.callers < 2:
        ap.error("--callers must be at least 2; one caller tests nothing here")

    log("building ground truth from Ensembl and the standard genetic code")
    truth = build_truth()
    for gene, row in truth.items():
        log(f"   {gene:6} {row['transcript']}  {row['protein']}")

    verdicts = {}
    log("\n=== attribution under concurrency ===")
    verdicts["attribution"] = asyncio.run(
        check_attribution(args.endpoint, truth, args.callers, args.timeout)
    )

    if args.crash_the_engine:
        log("\n=== recovery from an engine crash ===")
        verdicts["recovery"] = asyncio.run(
            check_recovery(args.endpoint, truth, args.timeout)
        )
    else:
        log("\n=== recovery: NOT RUN (pass --crash-the-engine) ===")

    log("")
    for name, ok in verdicts.items():
        log(f"{name}: {'ok' if ok else 'FAILED'}")
    return 0 if all(verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
