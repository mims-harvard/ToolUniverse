"""Carbon-A protein-coding gene annotation, run on a provider's GPU.

Carbon-A (``HuggingFaceBio/Carbon-A-1.2B``) assigns every base of a eukaryotic
genome a strand-specific coding probability, and the annotation pipeline that
ships with it turns those probabilities into gene models: a transition network,
a Viterbi decode over a gene grammar, and a confidence network that scores the
probability that a gene's structure is exactly right.

The model is 1.2B parameters with 4.6 GB of weights, needs a CUDA GPU, and runs
at roughly 10 kbp per second, so this is a provider-side tool rather than a
local one. The provider configures where the model and the pipeline live;
callers pass a sequence or the name of a FASTA file in the provider's input
directory.

Two pipeline behaviours are passed through rather than smoothed over, because
both change what the result means:

* Records shorter than ``min_record_length`` are **skipped**, not annotated --
  the pipeline's own floor is 100,000 bp. A short sequence submitted without
  that floor lowered returns no genes, which looks identical to "no genes
  found", so it is refused with an explanation instead.
* The pipeline checks whether the genetic code it used fits the result, and on
  a likely mismatch writes a warning and renames its output directory. That
  warning is surfaced as ``warnings`` on a successful result, since the genes
  are still returned but may be decoded under the wrong code.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool

PIPELINE_ENV = "CARBON_A_PIPELINE"
INPUT_ROOT_ENV = "CARBON_A_INPUT_ROOT"
JOB_ROOT_ENV = "CARBON_A_JOB_ROOT"
MODEL_ENV = "CARBON_A_MODEL"
PYTHON_ENV = "CARBON_A_PYTHON"
ATTN_ENV = "CARBON_A_ATTN_IMPLEMENTATION"

_DEFAULT_MODEL = "HuggingFaceBio/Carbon-A-1.2B"
_DEFAULT_ATTN = "flash_attention_2"
_ATTN_CHOICES = ("flash_attention_2", "sdpa")

# The pipeline's own floor (annotation_pipeline/src/constants.py:
# MIN_RECORD_LENGTH_BP). A record below it is skipped.
_PIPELINE_MIN_RECORD_LENGTH = 100_000
# The threshold the model card reports its gene counts at
# (constants.CONFIDENCE_THRESHOLD).
_DEFAULT_MIN_CONFIDENCE = 0.1

_MAX_SEQUENCE_BP = 3_000_000
_MIN_SEQUENCE_BP = 1_000
_MAX_GENES_RETURNED = 2_000
_MAX_TIMEOUT_SECONDS = 3_600
_MAX_GFF_BYTES = 2_000_000
_MAX_PROTEIN_BYTES = 2_000_000
_LOG_TAIL_CHARS = 2_000
_TERMINATE_GRACE_SECONDS = 20

# Secrets that must never reach a provider subprocess's environment.
_WITHHELD_ENV = ("TOOLUNIVERSE_API_TOKEN", "TOOLUNIVERSE_SERVICE_KEY")

_SEQUENCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._|-]{0,63}$")
_INPUT_SEGMENT = r"\.*[A-Za-z0-9_\-][A-Za-z0-9._\-]*"
_INPUT_FILE_PATTERN = re.compile(rf"^{_INPUT_SEGMENT}(/{_INPUT_SEGMENT})*$")
# IUPAC nucleotide codes plus gap characters, which the pipeline tolerates.
_SEQUENCE_CHARS = re.compile(r"^[ACGTURYSWKMBDHVNacgturyswkmbdhvn\-\.\n\r\t ]+$")

_ALLOWED_ARGUMENTS = frozenset(
    {
        "sequence",
        "sequence_id",
        "input_file",
        "genetic_code",
        "min_confidence",
        "min_record_length",
        "attn_implementation",
        "max_genes",
        "return_gff",
        "return_proteins",
        "timeout_seconds",
        "dry_run",
    }
)

_GENETIC_CODES = {
    # The pipeline ships exactly these tables in codon_tables/.
    "standard": "standard.json",
    "tetrahymena_table6": "GCF_000189635.1.json",
}


class _ProviderFailure(Exception):
    """A failure to report to the caller without leaking provider internals."""


def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "error": message}


def _provider_env() -> Dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _WITHHELD_ENV}
    return env


@register_tool("CarbonATool")
class CarbonATool(BaseTool):
    """Annotate protein-coding genes with Carbon-A on the provider's GPU."""

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        unknown = sorted(set(arguments) - _ALLOWED_ARGUMENTS)
        if unknown:
            return _error(f"Unknown argument(s): {', '.join(unknown)}")
        try:
            plan = self._plan(arguments)
        except ValueError as exc:
            return _error(str(exc))

        if plan["dry_run"]:
            return {
                "status": "success",
                "data": {
                    "dry_run": True,
                    "command": plan["display_command"],
                    "input": plan["input_description"],
                    "genetic_code": plan["genetic_code"],
                    "min_record_length": plan["min_record_length"],
                    "attn_implementation": plan["attn_implementation"],
                },
            }
        try:
            return self._annotate(plan)
        except _ProviderFailure as exc:
            return _error(str(exc))

    # --- argument validation ---------------------------------------------

    def _plan(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence")
        input_file = arguments.get("input_file")
        if bool(sequence) == bool(input_file):
            raise ValueError(
                "Pass exactly one of sequence (inline DNA) or input_file "
                "(a FASTA file in the provider's input directory)."
            )

        dry_run = self._bool(arguments.get("dry_run", False), "dry_run")
        min_confidence = self._number(
            arguments.get("min_confidence", _DEFAULT_MIN_CONFIDENCE),
            "min_confidence",
            0.0,
            1.0,
        )
        max_genes = self._integer(
            arguments.get("max_genes", 200), "max_genes", 1, _MAX_GENES_RETURNED
        )
        timeout_seconds = self._integer(
            arguments.get("timeout_seconds", 900),
            "timeout_seconds",
            1,
            _MAX_TIMEOUT_SECONDS,
        )
        genetic_code = arguments.get("genetic_code") or "standard"
        if genetic_code not in _GENETIC_CODES:
            raise ValueError(
                "genetic_code must be one of "
                f"{', '.join(sorted(_GENETIC_CODES))}, got {genetic_code!r}"
            )
        attn = arguments.get("attn_implementation") or os.environ.get(
            ATTN_ENV, _DEFAULT_ATTN
        )
        if attn not in _ATTN_CHOICES:
            raise ValueError(
                f"attn_implementation must be one of {', '.join(_ATTN_CHOICES)}, "
                f"got {attn!r}"
            )

        min_record_length = arguments.get("min_record_length")
        if min_record_length is None:
            min_record_length = _PIPELINE_MIN_RECORD_LENGTH
        else:
            min_record_length = self._integer(
                min_record_length, "min_record_length", 1, 10_000_000
            )

        pipeline = self._pipeline_script()
        plan: Dict[str, Any] = {
            "dry_run": dry_run,
            "min_confidence": min_confidence,
            "max_genes": max_genes,
            "timeout_seconds": timeout_seconds,
            "genetic_code": genetic_code,
            "attn_implementation": attn,
            "min_record_length": min_record_length,
            "pipeline": pipeline,
            "return_gff": self._bool(arguments.get("return_gff", False), "return_gff"),
            "return_proteins": self._bool(
                arguments.get("return_proteins", False), "return_proteins"
            ),
        }

        if sequence:
            cleaned, length = self._clean_sequence(sequence)
            if length < min_record_length:
                raise ValueError(
                    f"The sequence is {length:,} bp and min_record_length is "
                    f"{min_record_length:,} bp, so the pipeline would skip the "
                    "record and return no genes. Carbon-A's own floor is "
                    f"{_PIPELINE_MIN_RECORD_LENGTH:,} bp because it reads a "
                    "98,304 bp window; pass a longer sequence, or lower "
                    "min_record_length deliberately and treat the result as "
                    "out of the model's reported range."
                )
            plan["sequence"] = cleaned
            plan["sequence_id"] = self._sequence_id(arguments.get("sequence_id"))
            plan["sequence_length"] = length
            plan["input_description"] = (
                f"inline sequence {plan['sequence_id']} ({length:,} bp)"
            )
        else:
            plan["input_file"] = self._input_path(input_file)
            plan["input_description"] = f"provider file {input_file}"

        plan["display_command"] = self._display_command(plan)
        return plan

    @staticmethod
    def _bool(value: Any, name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be true or false, got {value!r}")
        return value

    @staticmethod
    def _integer(value: Any, name: str, low: int, high: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer, got {value!r}")
        if not low <= value <= high:
            raise ValueError(f"{name} must be between {low} and {high}, got {value}")
        return value

    @staticmethod
    def _number(value: Any, name: str, low: float, high: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number, got {value!r}")
        number = float(value)
        if not low <= number <= high:
            raise ValueError(f"{name} must be between {low} and {high}, got {value}")
        return number

    @staticmethod
    def _sequence_id(value: Any) -> str:
        if value is None:
            return "query"
        if not isinstance(value, str) or not _SEQUENCE_ID_PATTERN.match(value):
            raise ValueError(
                "sequence_id must be 1-64 characters of letters, digits, "
                f"'.', '_', '|' or '-', got {value!r}"
            )
        return value

    @staticmethod
    def _clean_sequence(value: Any) -> Tuple[str, int]:
        if not isinstance(value, str):
            raise ValueError(f"sequence must be a string, got {type(value).__name__}")
        if value.lstrip().startswith(">"):
            raise ValueError(
                "sequence takes bare nucleotides, not FASTA. Drop the '>' "
                "header line, or put the FASTA in the provider's input "
                "directory and pass input_file."
            )
        if not _SEQUENCE_CHARS.match(value):
            raise ValueError(
                "sequence must contain only IUPAC nucleotide codes, '-', '.' "
                "and whitespace."
            )
        cleaned = re.sub(r"[\s]", "", value)
        length = len(cleaned)
        if not _MIN_SEQUENCE_BP <= length <= _MAX_SEQUENCE_BP:
            raise ValueError(
                f"sequence must be between {_MIN_SEQUENCE_BP:,} and "
                f"{_MAX_SEQUENCE_BP:,} bp, got {length:,} bp. Carbon-A runs at "
                "roughly 10 kbp/s, so a longer record belongs in the "
                "provider's input directory via input_file."
            )
        return cleaned, length

    @staticmethod
    def _pipeline_script() -> str:
        configured = os.environ.get(PIPELINE_ENV)
        if not configured:
            raise ValueError(
                f"The provider has no {PIPELINE_ENV} configured. It must point "
                "at the Carbon-A annotation pipeline's run_annotation.sh."
            )
        script = os.path.abspath(os.path.expanduser(configured))
        if not os.path.isfile(script):
            raise ValueError(
                f"The provider's {PIPELINE_ENV} does not name a file. "
                "It must point at run_annotation.sh."
            )
        return script

    @staticmethod
    def _input_path(input_file: Any) -> str:
        if not isinstance(input_file, str) or not _INPUT_FILE_PATTERN.match(input_file):
            raise ValueError(
                "input_file must be a relative path inside the provider's "
                "input directory, for example 'yeast/GCF_000146045.2.fna'. "
                "Absolute paths and URLs are rejected."
            )
        root = os.environ.get(INPUT_ROOT_ENV)
        if not root:
            raise ValueError(
                f"The provider has no {INPUT_ROOT_ENV} configured, so "
                "input_file cannot be resolved. Pass sequence instead."
            )
        root_path = os.path.realpath(os.path.expanduser(root))
        candidate = os.path.realpath(os.path.join(root_path, input_file))
        if not (candidate == root_path or candidate.startswith(root_path + os.sep)):
            raise ValueError(
                "input_file resolves outside the provider's input directory."
            )
        if not os.path.isfile(candidate):
            raise ValueError(
                f"input_file '{input_file}' is not in the provider's input directory."
            )
        return candidate

    def _display_command(self, plan: Dict[str, Any]) -> List[str]:
        """The command, with the job directory left out as it is per-call."""
        return self._command(plan, input_path="<input>", output_dir="<workdir>")

    def _command(
        self, plan: Dict[str, Any], input_path: str, output_dir: str
    ) -> List[str]:
        pipeline_dir = os.path.dirname(plan["pipeline"])
        command = [
            "bash",
            plan["pipeline"],
            "--input",
            input_path,
            "--output-dir",
            output_dir,
            "--attn-implementation",
            plan["attn_implementation"],
            "--min-record-length",
            str(plan["min_record_length"]),
            "--codon-table",
            os.path.join(
                pipeline_dir, "codon_tables", _GENETIC_CODES[plan["genetic_code"]]
            ),
        ]
        model = os.environ.get(MODEL_ENV)
        if model:
            command += ["--model", model]
        return command

    # --- running ----------------------------------------------------------

    def _annotate(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        job_root = os.environ.get(JOB_ROOT_ENV) or None
        workdir = tempfile.mkdtemp(prefix="carbon_a_", dir=job_root)
        try:
            if "sequence" in plan:
                input_path = os.path.join(workdir, "input.fna")
                with open(input_path, "w", encoding="ascii") as handle:
                    handle.write(f">{plan['sequence_id']}\n")
                    for offset in range(0, len(plan["sequence"]), 60):
                        handle.write(plan["sequence"][offset : offset + 60] + "\n")
            else:
                input_path = plan["input_file"]

            output_dir = os.path.join(workdir, "out")
            started = time.monotonic()
            self._run_pipeline(plan, input_path, output_dir, workdir)
            runtime = time.monotonic() - started
            return self._collect(plan, output_dir, runtime)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _run_pipeline(
        self,
        plan: Dict[str, Any],
        input_path: str,
        output_dir: str,
        workdir: str,
    ) -> None:
        command = self._command(plan, input_path, output_dir)
        executable = os.environ.get(PYTHON_ENV)
        env = _provider_env()
        if executable:
            # Put the configured interpreter's directory first so the pipeline's
            # own `python`/`hf` calls resolve to the Carbon-A environment.
            env["PATH"] = (
                os.path.dirname(os.path.abspath(executable))
                + os.pathsep
                + env.get("PATH", "")
            )
        try:
            process = subprocess.Popen(
                command,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
            )
        except OSError as exc:
            raise _ProviderFailure(
                f"The Carbon-A pipeline could not be started: {exc}"
            ) from exc
        try:
            output, _ = process.communicate(timeout=plan["timeout_seconds"])
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.communicate(timeout=_TERMINATE_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            raise _ProviderFailure(
                f"Carbon-A did not finish within {plan['timeout_seconds']} s. "
                "It runs at roughly 10 kbp/s, so raise timeout_seconds or "
                "submit a shorter record."
            ) from None
        if process.returncode != 0:
            tail = (output or "")[-_LOG_TAIL_CHARS:].strip()
            raise _ProviderFailure(
                f"The Carbon-A pipeline failed (exit {process.returncode}). "
                f"Last output:\n{tail}"
            )

    # --- reading the outputs ---------------------------------------------

    def _collect(
        self, plan: Dict[str, Any], output_dir: str, runtime: float
    ) -> Dict[str, Any]:
        resolved, warnings = self._resolve_output_dir(output_dir)
        if resolved is None:
            raise _ProviderFailure("The Carbon-A pipeline wrote no output directory.")

        gff_path = os.path.join(resolved, "prediction.gff")
        if not os.path.isfile(gff_path):
            raise _ProviderFailure("The Carbon-A pipeline wrote no prediction.gff.")

        genes, totals = self._parse_gff(gff_path, plan["min_confidence"])
        proteins = self._read_fasta(os.path.join(resolved, "prediction.faa"))

        reported = genes[: plan["max_genes"]]
        for gene in reported:
            sequence = proteins.get(gene["id"])
            if sequence is not None:
                gene["protein_length"] = len(sequence)
                if plan["return_proteins"]:
                    gene["protein"] = sequence

        data: Dict[str, Any] = {
            "input": plan["input_description"],
            "genetic_code": plan["genetic_code"],
            "attn_implementation": plan["attn_implementation"],
            "min_confidence": plan["min_confidence"],
            "min_record_length": plan["min_record_length"],
            "runtime_seconds": round(runtime, 1),
            "genes_predicted": totals["total"],
            "genes_at_or_above_min_confidence": totals["kept"],
            "genes_returned": len(reported),
            "coding_bases": totals["coding_bases"],
            "records_annotated": sorted(totals["records"]),
            "genes": reported,
        }
        if "sequence_length" in plan:
            data["sequence_length"] = plan["sequence_length"]
        if totals["kept"] > len(reported):
            data["genes_note"] = (
                f"Returned the first {len(reported)} of {totals['kept']} genes "
                "at or above min_confidence, in genome order. Raise max_genes "
                "for more, or return_gff for all of them."
            )
        if plan["return_gff"]:
            data["gff"] = self._read_text(gff_path, _MAX_GFF_BYTES)
        if warnings:
            data["warnings"] = warnings
        return {"status": "success", "data": data}

    @staticmethod
    def _resolve_output_dir(output_dir: str) -> Tuple[Optional[str], List[str]]:
        """Find the results, and read the pipeline's own warnings.

        A failed codon-table check renames ``<dir>`` to ``<dir>_WARNING`` and
        appends to WARNINGS.txt, so the renamed directory is where the genes
        are and the warning is part of the answer, not a side note.
        """
        warnings: List[str] = []
        resolved: Optional[str] = None
        if os.path.isdir(output_dir):
            resolved = output_dir
        elif os.path.isdir(output_dir + "_WARNING"):
            resolved = output_dir + "_WARNING"
            warnings.append(
                "The pipeline flagged this run: the genetic code it used may "
                "not fit the sequence, so the gene structures below may be "
                "decoded under the wrong code. Pass genetic_code explicitly if "
                "the organism uses a non-standard one."
            )
        for candidate in (
            os.path.join(os.path.dirname(output_dir), "WARNINGS.txt"),
            os.path.join(resolved or output_dir, "WARNINGS.txt"),
        ):
            if os.path.isfile(candidate):
                try:
                    with open(candidate, "r", encoding="utf-8", errors="replace") as fh:
                        text = fh.read(4000).strip()
                except OSError:
                    continue
                if text:
                    warnings.append(text)
        return resolved, warnings

    @staticmethod
    def _parse_gff(
        path: str, min_confidence: float
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Read gene rows and CDS extents from the pipeline's GFF3."""
        genes: List[Dict[str, Any]] = []
        by_id: Dict[str, Dict[str, Any]] = {}
        transcript_to_gene: Dict[str, str] = {}
        cds_per_transcript: Dict[str, int] = {}
        totals = {
            "total": 0,
            "kept": 0,
            "coding_bases": 0,
            "records": set(),
        }
        try:
            handle = open(path, "r", encoding="utf-8", errors="replace")
        except OSError as exc:
            raise _ProviderFailure(f"prediction.gff could not be read: {exc}") from exc
        with handle:
            for line in handle:
                if not line or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 9:
                    continue
                record, _, feature, start, end, _, strand, _, attributes = parts[:9]
                if feature == "gene":
                    totals["total"] += 1
                    totals["records"].add(record)
                    fields = dict(
                        item.split("=", 1)
                        for item in attributes.split(";")
                        if "=" in item
                    )
                    confidence = fields.get("confidence")
                    try:
                        confidence_value = (
                            float(confidence) if confidence is not None else None
                        )
                    except ValueError:
                        confidence_value = None
                    # A gene without a confidence is counted, matching the
                    # pipeline's own reporting (constants.CONFIDENCE_THRESHOLD).
                    if (
                        confidence_value is not None
                        and confidence_value < min_confidence
                    ):
                        continue
                    totals["kept"] += 1
                    gene = {
                        "id": fields.get("ID") or f"gene{totals['total']}",
                        "record": record,
                        "strand": strand,
                        "start": int(start) if start.isdigit() else None,
                        "end": int(end) if end.isdigit() else None,
                        "confidence": confidence_value,
                        "exons": 0,
                        # utils.py writes status=complete|incomplete; a gene the
                        # pipeline could not close is truncated by a record edge.
                        "incomplete": fields.get("status") == "incomplete",
                    }
                    genes.append(gene)
                    by_id[gene["id"]] = gene
                elif feature == "mRNA":
                    fields = dict(
                        item.split("=", 1)
                        for item in attributes.split(";")
                        if "=" in item
                    )
                    transcript = fields.get("ID")
                    parent = (fields.get("Parent") or "").split(",")[0]
                    if transcript and parent:
                        # CDS rows name the transcript, whose id does not derive
                        # from the gene's ("mrna000001" under "gene000001"), so
                        # the mRNA row is the only link between them.
                        transcript_to_gene[transcript] = parent
                elif feature == "CDS":
                    try:
                        totals["coding_bases"] += int(end) - int(start) + 1
                    except ValueError:
                        pass
                    fields = dict(
                        item.split("=", 1)
                        for item in attributes.split(";")
                        if "=" in item
                    )
                    parent = (fields.get("Parent") or "").split(",")[0]
                    cds_per_transcript[parent] = cds_per_transcript.get(parent, 0) + 1

        for transcript, count in cds_per_transcript.items():
            gene = by_id.get(transcript_to_gene.get(transcript, transcript))
            if gene is None:
                # A CDS whose transcript parents a gene the filter dropped.
                continue
            gene["exons"] += count
        return genes, totals

    @staticmethod
    def _read_fasta(path: str) -> Dict[str, str]:
        """Read prediction.faa as id -> sequence, keyed by the gene id."""
        sequences: Dict[str, str] = {}
        if not os.path.isfile(path):
            return sequences
        try:
            handle = open(path, "r", encoding="utf-8", errors="replace")
        except OSError:
            return sequences
        name: Optional[str] = None
        chunks: List[str] = []
        with handle:
            for line in handle:
                if line.startswith(">"):
                    if name is not None:
                        sequences[name] = "".join(chunks)
                    header = line[1:].strip()
                    name = header.split()[0] if header else None
                    # Protein records are named after the mRNA; key them by the
                    # gene id as well so either spelling resolves.
                    chunks = []
                else:
                    chunks.append(line.strip())
        if name is not None:
            sequences[name] = "".join(chunks)
        for key in list(sequences):
            stem = key.rsplit(".", 1)[0]
            sequences.setdefault(stem, sequences[key])
        return sequences

    @staticmethod
    def _read_text(path: str, limit: int) -> str:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read(limit + 1)
        if len(text) > limit:
            return (
                text[:limit] + f"\n# truncated at {limit} characters; "
                "rerun with return_gff false and read the provider's output "
                "directory for the whole file\n"
            )
        return text
