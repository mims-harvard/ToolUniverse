"""CPU-only local protein similarity searches; no scientific-service uploads."""

import csv
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile

from .base_tool import BaseTool
from .tool_registry import register_tool

PROTEIN = set("ACDEFGHIKLMNPQRSTVWYX")
RESIDUES = set(
    "ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL".split()
)
SEQUENCE_FIELDS = (
    "query,target,fident,alnlen,qstart,qend,qlen,tstart,tend,tlen,evalue,bits,qcov,tcov"
)
STRUCTURE_FIELDS = "query,target,qtmscore,ttmscore,alnlen,qstart,qend,qlen,tstart,tend,tlen,qcov,tcov,fident"


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _integer(args, name, default, minimum, maximum):
    value = args.get(name)
    value = default if value is None else value
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} must be an integer in {minimum}–{maximum}.")
    return value


def _number(args, name, default, minimum, maximum):
    value = args.get(name)
    value = default if value is None else value
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"{name} must be a finite number in {minimum}–{maximum}.")
    return float(value)


def _path(value, operation):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("query_path and reference_path must be nonempty local paths.")
    if value == "builtin:1UBQ":
        suffix = "fasta" if operation == "sequence" else "pdb"
        return Path(
            __file__
        ).parent / "data" / f"protein_similarity_1ubq.{suffix}", "bundled_public_1UBQ"
    return Path(value).expanduser().resolve(), "local_path"


def _fasta_queries(path):
    if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Query FASTA must be an existing file of at most 2 MiB.")
    content = path.read_bytes()
    if len(content) > 2 * 1024 * 1024:
        raise ValueError("Query FASTA exceeds 2 MiB.")
    records = {}
    name = None
    for line in content.decode().splitlines():
        if not line.strip():
            continue
        if line.startswith(">"):
            tokens = line[1:].split()
            if not tokens or tokens[0] in records:
                raise ValueError("FASTA query identifiers must be nonempty and unique.")
            name = tokens[0]
            records[name] = ""
            if len(records) > 50:
                raise ValueError("At most 50 query proteins per call.")
        else:
            if name is None:
                raise ValueError("Query sequence precedes its FASTA identifier.")
            sequence = line.strip()
            if not set(sequence) <= PROTEIN:
                raise ValueError(
                    "Query FASTA accepts uppercase standard amino acids and X; no gaps or stops."
                )
            records[name] += sequence
    if not records or any(not 1 <= len(s) <= 10000 for s in records.values()):
        raise ValueError("Each query must contain 1–10000 protein residues.")
    return {name: len(seq) for name, seq in records.items()}, content


def _pdb_queries(path):
    files = (
        [path]
        if path.is_file()
        else sorted(path.glob("*.pdb"))
        if path.is_dir()
        else []
    )
    if not 1 <= len(files) <= 50:
        raise ValueError(
            "Provide one PDB file or a directory containing 1–50 single-chain .pdb files."
        )
    rows = []
    for file in files:
        if file.suffix.lower() != ".pdb" or file.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Each query must be a .pdb file of at most 2 MiB.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", file.name):
            raise ValueError(
                "Use unique PDB basenames containing letters, digits, underscores, dots or hyphens."
            )
        content = file.read_bytes()
        if len(content) > 2 * 1024 * 1024:
            raise ValueError("Query PDB exceeds 2 MiB.")
        residues = set()
        chains = set()
        models = 0
        for line in content.decode().splitlines():
            if line.startswith("MODEL "):
                models += 1
            if line[:6] not in ("ATOM  ", "HETATM") or line[12:16].strip() != "CA":
                continue
            if line[17:20].strip() not in RESIDUES:
                if (
                    line[:6] == "HETATM"
                    and line[17:20].strip() == "CA"
                    and line[76:78].strip().upper() == "CA"
                ):
                    continue  # An explicit calcium ion is not a protein CA.
                raise ValueError(
                    "Nonstandard protein CA residue labels are unsupported; normalize or extract the intended standard-residue chain explicitly."
                )
            if len(line) < 54 or line[16].strip():
                raise ValueError(
                    "Protein CA records must use fixed-column PDB without alternate locations."
                )
            key = (line[21], line[22:27])
            xyz = [float(line[i : i + 8]) for i in (30, 38, 46)]
            if key in residues or not all(math.isfinite(v) for v in xyz):
                raise ValueError(
                    "Duplicate or nonfinite protein CA coordinates in query."
                )
            residues.add(key)
            chains.add(line[21])
        if models > 1 or len(chains) != 1 or not 3 <= len(residues) <= 10000:
            raise ValueError(
                "Each structure query must contain one model and one protein CA chain of 3–10000 residues; extract the intended chain explicitly."
            )
        rows.append(
            {
                "file": file,
                "content": content,
                "protein_CA_residues": len(residues),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return rows


def _execute(argv, directory, timeout):
    log = directory / "process.log"
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1")
    with log.open("wb") as stream:
        process = subprocess.Popen(
            argv,
            stdout=stream,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=(os.name == "posix"),
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait(timeout=10)
            raise TimeoutError(
                f"Local search exceeded {timeout} seconds; its owned process was stopped."
            )
    if process.returncode:
        # Do not echo native logs, which can contain the caller's file paths.
        raise RuntimeError(f"Local alignment program exited {process.returncode}.")
    return log


def _parse(path, operation, limit, query_lengths=None):
    fields = (SEQUENCE_FIELDS if operation == "sequence" else STRUCTURE_FIELDS).split(
        ","
    )
    grouped = {}
    total = 0
    with path.open() as stream:
        for row in csv.reader(stream, delimiter="\t"):
            if not row:
                continue
            total += 1
            if total > 100000 or len(row) != len(fields):
                raise ValueError("Unexpected or oversized local alignment output.")
            hit = dict(zip(fields, row))
            if not hit["query"] or not hit["target"]:
                raise ValueError("Alignment output has an empty identifier.")
            for field in fields[2:]:
                value = float(hit[field])
                if not math.isfinite(value) or value < 0:
                    raise ValueError("Alignment output has an invalid numeric field.")
                if (
                    field in ["fident", "qcov", "tcov", "qtmscore", "ttmscore"]
                    and value > 1
                ):
                    raise ValueError(
                        "Fraction or TM-score exceeds 1 in alignment output."
                    )
                if field in [
                    "alnlen",
                    "qstart",
                    "qend",
                    "qlen",
                    "tstart",
                    "tend",
                    "tlen",
                ]:
                    if not value.is_integer() or value <= 0:
                        raise ValueError(
                            "Alignment lengths/coordinates must be positive integers."
                        )
                    hit[field] = int(value)
                else:
                    hit[field] = value
            if (
                not 1 <= hit["qstart"] <= hit["qend"] <= hit["qlen"]
                or not 1 <= hit["tstart"] <= hit["tend"] <= hit["tlen"]
            ):
                raise ValueError(
                    "Alignment coordinates fall outside the reported proteins."
                )
            if query_lengths is not None and (
                hit["query"] not in query_lengths
                or hit["qlen"] != query_lengths[hit["query"]]
            ):
                raise ValueError(
                    "Backend query identifiers/lengths do not match the validated protein queries."
                )
            grouped.setdefault(hit["query"], []).append(hit)
    returned = []
    for name in sorted(grouped):
        grouped[name].sort(
            key=lambda h: (
                (-h["bits"], h["evalue"])
                if operation == "sequence"
                else (-h["qtmscore"], -h["qcov"])
            )
        )
        returned.extend(grouped[name][:limit])
    return returned, total


@register_tool("LocalProteinSimilarityTool")
class LocalProteinSimilarityTool(BaseTool):
    """Caller-managed CPU binaries and references; never download or upload."""

    def run(self, arguments):
        stage = "input_validation"
        try:
            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be an object.")
            allowed = set(
                self.tool_config.get("parameter", {}).get("properties", {})
            ) | {"operation"}
            if set(arguments) - allowed:
                raise ValueError("Unsupported local protein similarity argument.")
            operation = (self.tool_config.get("fields") or {}).get("operation")
            if operation not in ["sequence", "structure"]:
                raise ValueError("Unknown local protein similarity operation.")
            query, source = _path(arguments.get("query_path"), operation)
            reference, reference_source = _path(
                arguments.get("reference_path"), operation
            )
            is_database = Path(str(reference) + ".dbtype").is_file()
            if not reference.is_file() and not is_database:
                raise ValueError(
                    "reference_path must be a local reference file or prebuilt database prefix with .dbtype."
                )
            threads = _integer(arguments, "threads", 2, 1, 8)
            timeout = _integer(arguments, "timeout_seconds", 300, 1, 3600)
            limit = _integer(arguments, "max_hits_per_query", 20, 1, 100)
            coverage = _number(arguments, "minimum_query_coverage", 0, 0, 1)
            if operation == "sequence":
                query_lengths, content = _fasta_queries(query)
                query_info = [
                    {
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "records": len(query_lengths),
                    }
                ]
                sensitivity = _number(arguments, "sensitivity", 7.5, 1, 7.5)
                evalue = _number(arguments, "evalue_threshold", 0.001, 0, 1000)
            else:
                structures = _pdb_queries(query)
                query_lengths = {
                    r["file"].stem: r["protein_CA_residues"] for r in structures
                }
                query_info = [
                    {k: v for k, v in r.items() if k not in ["file", "content"]}
                    for r in structures
                ]
            stage = "dependency_check"
            name = "mmseqs" if operation == "sequence" else "foldseek"
            variable = (
                "TOOLUNIVERSE_MMSEQS2_BINARY"
                if operation == "sequence"
                else "TOOLUNIVERSE_FOLDSEEK_BINARY"
            )
            binary = os.environ.get(variable) or shutil.which(name)
            binary = Path(binary).expanduser().resolve() if binary else None
            if binary is None or not binary.is_file() or not os.access(binary, os.X_OK):
                return {
                    "status": "error",
                    "error": f"Install the {name} CPU binary on this host, or set {variable} to its executable. No automatic installation or online fallback.",
                    "stage": stage,
                }
            stage = "local_search"
            with tempfile.TemporaryDirectory(prefix="tu-protein-similarity-") as work:
                work = Path(work)
                output = work / "hits.tsv"
                version_dir = work / "version"
                version_dir.mkdir()
                version_log = _execute(
                    [str(binary), "version"], version_dir, min(10, timeout)
                )
                version = version_log.read_text()[:1000].strip()
                if operation == "structure":
                    staged = work / "queries"
                    staged.mkdir()
                    for row in structures:
                        (staged / row["file"].name).write_bytes(row["content"])
                    native_query = staged
                else:
                    native_query = work / "query.fasta"
                    native_query.write_bytes(content)
                argv = [
                    str(binary),
                    "easy-search",
                    str(native_query),
                    str(reference),
                    str(output),
                    str(work / "tmp"),
                    "--threads",
                    str(threads),
                    "--gpu",
                    "0",
                    "--max-seqs",
                    "1000",
                    "-c",
                    str(coverage),
                    "--cov-mode",
                    "2",
                ]
                if operation == "sequence":
                    argv += [
                        "--search-type",
                        "1",
                        "-s",
                        str(sensitivity),
                        "-e",
                        str(evalue),
                        "--alignment-mode",
                        "3",
                        "--split-memory-limit",
                        "2G",
                        "--format-output",
                        SEQUENCE_FIELDS,
                    ]
                else:
                    argv += [
                        "--alignment-type",
                        "1",
                        "--prefilter-mode",
                        "1",
                        "--exact-tmscore",
                        "1",
                        "-e",
                        "10",
                        "--format-output",
                        STRUCTURE_FIELDS,
                    ]
                _execute(argv, work, timeout)
                stage = "output_validation"
                hits, total = _parse(
                    output,
                    operation,
                    limit,
                    query_lengths,
                )
                if operation == "sequence":
                    if any(
                        h["query"] not in query_lengths
                        or h["qlen"] != query_lengths[h["query"]]
                        for h in hits
                    ):
                        raise ValueError(
                            "Backend query identifiers/lengths do not match the protein FASTA."
                        )
                    count = len(query_lengths)
                else:
                    count = len(structures)
                return {
                    "status": "success",
                    "data": {
                        "operation": operation,
                        "query_count": count,
                        "hits": hits,
                        "backend": name,
                        "binary_version": version,
                        "binary_sha256": _sha(Path(binary)),
                        "backend_hit_count": total,
                        "returned_hit_count": len(hits),
                        "hits_truncated": len(hits) < total,
                        "query_source": source,
                        "reference_source": reference_source,
                        "query_fingerprints": query_info,
                        "GPU_enabled": False,
                        "scientific_service_uploads": 0,
                        "fraction_units": "fident/qcov/tcov and TM-scores are fractions in 0–1, not percentages.",
                        "ranking": "Within-query bit score"
                        if operation == "sequence"
                        else "Within-query query-normalized TM-score",
                        "novelty_certified": False,
                        "binding_verified": False,
                        "limitations": [
                            "Only the supplied local reference snapshot is searched; no hit is not proof of novelty.",
                            "Sequence similarity is not affinity or function; structural similarity is not a binding test.",
                            "Structure mode uses whole single chains, not consensus domain segmentation or an official novelty classifier.",
                        ],
                    },
                }
        except (ValueError, OSError, RuntimeError, TimeoutError, csv.Error) as exc:
            return {"status": "error", "error": str(exc), "stage": stage}
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Local alignment failed ({type(exc).__name__}).",
                "stage": stage,
            }
