#!/usr/bin/env python3
"""Exercise a Carbon-A deployment end to end, through ToolUniverse.

Starts the Carbon-A MCP server on a loopback port, connects to it the way a
client does, annotates a genome, and checks the result against the thing that
can actually falsify it: the NCBI reference annotation for the same genome.

With ``--genome-dir`` pointing at a directory that holds both the genome FASTA
and its ``genomic.gff``, the pipeline's own ``run_evaluation.sh`` is run on the
prediction and its nucleotide, exon and gene F1 are reported, so a deployment
can be compared against the numbers the model card publishes. Without it, the
run is still checked for internal consistency -- genes inside the record, exon
counts, confidences in [0, 1], proteins starting at a methionine -- but nothing
confirms the genes are the right ones.

Nothing here is a unit test: it needs the GPU, the weights and minutes of
runtime. ``tests/unit/test_carbon_a_tool.py`` covers the contract without them.

Usage:
    python scripts/remote_validation/carbon_a_live_validation.py \\
        --out carbon_a_validation \\
        --genome-dir "$CARBON_A_INPUT_ROOT/GCF_000146045.2"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _genome_fasta(genome_dir: Path) -> Path:
    candidates = sorted(genome_dir.glob("*_genomic.fna")) + sorted(
        genome_dir.glob("*_genomic.fna.gz")
    )
    candidates = [p for p in candidates if not p.name.startswith("cds_from")]
    if not candidates:
        raise SystemExit(f"no *_genomic.fna in {genome_dir}")
    return candidates[0]


def _relative_to_input_root(path: Path) -> str:
    root = os.environ.get("CARBON_A_INPUT_ROOT")
    if not root:
        raise SystemExit(
            "CARBON_A_INPUT_ROOT must be set, and the genome must sit inside it, "
            "so the client can name the file the way a real caller does."
        )
    root_path = Path(os.path.realpath(os.path.expanduser(root)))
    try:
        return str(Path(os.path.realpath(path)).relative_to(root_path))
    except ValueError:
        raise SystemExit(
            f"{path} is not inside CARBON_A_INPUT_ROOT ({root_path})."
        ) from None


async def _call(port: int, arguments: dict) -> dict:
    from fastmcp import Client

    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        tools = [tool.name for tool in await client.list_tools()]
        if "carbon_a_annotate_cds" not in tools:
            raise SystemExit(f"server advertises {tools}, not carbon_a_annotate_cds")
        result = await client.call_tool("carbon_a_annotate_cds", arguments)
    payload = result.content[0].text if result.content else "{}"
    return json.loads(payload)


def _start_server(port: int, log_path: Path) -> subprocess.Popen:
    log = log_path.open("w", encoding="utf-8")
    env = dict(os.environ, TOOLUNIVERSE_MCP_PORT=str(port))
    process = subprocess.Popen(
        [sys.executable, "-m", "tooluniverse.remote.carbon_a.carbon_a_mcp_server"],
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
    )
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit(
                f"the server exited with {process.returncode}; see {log_path}"
            )
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return process
        time.sleep(1)
    process.terminate()
    raise SystemExit(f"the server did not start within 120 s; see {log_path}")


def _consistency(result: dict) -> list[str]:
    """Checks that do not need a reference annotation."""
    problems = []
    data = result.get("data") or {}
    genes = data.get("genes") or []
    if result.get("status") != "success":
        return [f"status was {result.get('status')}: {result.get('error')}"]
    if not genes:
        problems.append("no genes were returned")
    if data.get("genes_predicted", 0) < data.get("genes_at_or_above_min_confidence", 0):
        problems.append("more genes passed the confidence filter than were predicted")
    for gene in genes:
        if gene.get("start") is None or gene.get("end") is None:
            problems.append(f"{gene.get('id')}: missing coordinates")
            continue
        if gene["start"] > gene["end"]:
            problems.append(f"{gene['id']}: start after end")
        if gene.get("strand") not in ("+", "-"):
            problems.append(f"{gene['id']}: strand {gene.get('strand')!r}")
        confidence = gene.get("confidence")
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            problems.append(f"{gene['id']}: confidence {confidence}")
        if gene.get("exons", 0) < 1:
            problems.append(f"{gene['id']}: no CDS features")
        protein = gene.get("protein")
        if protein and not gene.get("incomplete") and not protein.startswith("M"):
            problems.append(
                f"{gene['id']}: complete gene's protein starts with {protein[:1]!r}"
            )
    if data.get("coding_bases", 0) <= 0:
        problems.append("no coding bases were reported")
    return problems


def _reference_genes(genome_dir: Path) -> dict[str, set[tuple[int, int]]]:
    """Protein-coding gene intervals from the NCBI reference annotation."""
    reference: dict[str, set[tuple[int, int]]] = {}
    path = genome_dir / "genomic.gff"
    if not path.is_file():
        return reference
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 9 or parts[2] != "gene":
                continue
            if "gene_biotype=protein_coding" not in parts[8]:
                continue
            try:
                reference.setdefault(parts[0], set()).add(
                    (int(parts[3]), int(parts[4]))
                )
            except ValueError:
                continue
    return reference


def _against_reference(genome_dir: Path, genes: list[dict]) -> dict | None:
    """Score the genes the tool returned against the NCBI reference.

    This checks the tool's own output rather than the pipeline's files. The
    pipeline's run_evaluation.sh needs a prediction.fna of CDS nucleotides,
    which this operation does not return, so scoring its files would say
    nothing about whether the tool reported them correctly.

    Exact locus agreement is the strict measure: the predicted gene's start and
    end both equal a reference protein-coding gene's. Overlap is the loose one.
    """
    reference = _reference_genes(genome_dir)
    if not reference:
        print(f"  (no genomic.gff in {genome_dir}; skipping)")
        return None
    total_reference = sum(len(spans) for spans in reference.values())

    exact = overlapping = off_record = 0
    hit: set[tuple[str, int, int]] = set()
    for gene in genes:
        record = gene.get("record")
        start, end = gene.get("start"), gene.get("end")
        spans = reference.get(record)
        if spans is None:
            off_record += 1
            continue
        if start is None or end is None:
            continue
        if (start, end) in spans:
            exact += 1
            hit.add((record, start, end))
            continue
        for span in spans:
            if start <= span[1] and span[0] <= end:
                overlapping += 1
                hit.add((record, span[0], span[1]))
                break

    returned = len(genes)
    return {
        "genes_compared": returned,
        "reference_protein_coding_genes": total_reference,
        "exact_locus_match": exact,
        "overlapping_only": overlapping,
        "no_reference_gene_at_locus": returned - exact - overlapping - off_record,
        "on_a_record_absent_from_the_reference": off_record,
        "exact_fraction_of_compared": round(exact / returned, 4) if returned else None,
        "reference_genes_hit": len(hit),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="carbon_a_validation")
    parser.add_argument(
        "--genome-dir",
        required=True,
        help=(
            "Directory with the genome FASTA and, for the reference comparison, "
            "its NCBI genomic.gff. Must sit inside CARBON_A_INPUT_ROOT."
        ),
    )
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--max-genes", type=int, default=2000)
    parser.add_argument("--genetic-code", default="standard")
    parser.add_argument("--attn-implementation", default=None)
    args = parser.parse_args()

    genome_dir = Path(args.genome_dir).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    fasta = _genome_fasta(genome_dir)
    relative = _relative_to_input_root(fasta)

    port = _free_port()
    print(f"starting the Carbon-A server on 127.0.0.1:{port}")
    server = _start_server(port, out_dir / "server.log")
    try:
        print("1. a dry run, to check the provider configuration")
        dry = asyncio.run(_call(port, {"input_file": relative, "dry_run": True}))
        (out_dir / "dry_run.json").write_text(json.dumps(dry, indent=2))
        if dry.get("status") != "success":
            print(f"   FAILED: {dry.get('error')}")
            return 1
        print(f"   command: {' '.join(dry['data']['command'])}")

        print(f"2. annotating {relative} ({fasta.stat().st_size / 1e6:.1f} MB)")
        arguments = {
            "input_file": relative,
            "max_genes": args.max_genes,
            "timeout_seconds": args.timeout_seconds,
            "genetic_code": args.genetic_code,
            "return_gff": True,
            "return_proteins": True,
        }
        if args.attn_implementation:
            arguments["attn_implementation"] = args.attn_implementation
        started = time.monotonic()
        result = asyncio.run(_call(port, arguments))
        elapsed = time.monotonic() - started
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()

    gff_text = (result.get("data") or {}).pop("gff", "")
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    if gff_text:
        (out_dir / "prediction.gff").write_text(gff_text, encoding="utf-8")

    if result.get("status") != "success":
        print(f"   FAILED: {result.get('error')}")
        return 1
    data = result["data"]
    print(f"   {elapsed:.0f} s wall clock, {data['runtime_seconds']} s reported")
    print(
        f"   {data['genes_predicted']} genes predicted, "
        f"{data['genes_at_or_above_min_confidence']} at confidence "
        f">= {data['min_confidence']}"
    )
    print(
        f"   {data['coding_bases']:,} coding bases over "
        f"{len(data['records_annotated'])} records"
    )
    for warning in data.get("warnings", []):
        print(f"   WARNING: {warning}")

    print("3. internal consistency")
    problems = _consistency(result)
    for problem in problems:
        print(f"   PROBLEM: {problem}")
    if not problems:
        print("   clean")

    print("4. the returned genes against the NCBI reference annotation")
    metrics = _against_reference(genome_dir, data.get("genes") or [])
    if metrics:
        (out_dir / "reference_comparison.json").write_text(
            json.dumps(metrics, indent=2)
        )
        for key, value in metrics.items():
            print(f"   {key}: {value}")
        if metrics["on_a_record_absent_from_the_reference"]:
            problems.append(
                f"{metrics['on_a_record_absent_from_the_reference']} genes sit on a "
                "record the reference does not have"
            )
    else:
        print("   not run; the genes above are unverified against a reference")

    print(f"\nartifacts in {out_dir}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
