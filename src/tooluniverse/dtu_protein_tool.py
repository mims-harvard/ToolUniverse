"""
DTU Health Tech protein predictors (local-compute via the biolib cloud runner).

Wraps three machine-learning protein predictors published by DTU Health Tech
(Technical University of Denmark) and related groups on the BioLib platform,
run through the ``pybiolib`` Python package:

  - deeptmhmm : DTU/DeepTMHMM      -> transmembrane topology (TM helices / beta
                                      barrels, signal peptide, inside/outside)
  - signalp   : DTU/SignalP_6      -> signal-peptide detection + cleavage site
  - deeploc   : KU/DeepLocPro      -> (prokaryotic) subcellular localization

NOTE on DeepLoc: the original eukaryotic "DeepLoc 2.0" web predictor is NOT
published as a runnable app on BioLib. The closest runnable subcellular
localization predictor from the same DeepLoc family is ``KU/DeepLocPro``
(prokaryotic). ``deeploc`` is mapped to it. See module docstring / tool
description so callers are not misled.

How it runs
-----------
``biolib.load('DTU/DeepTMHMM').cli(args='--fasta input.fasta')`` submits a job
to the BioLib cloud, waits for completion, and exposes output files. Jobs run
ANONYMOUSLY (no account required) but are queued on shared compute, so a single
prediction commonly takes 2-5 minutes. This is a genuine remote compute job,
not a local model -- the only local dependency is the ``pybiolib`` client.

Dependency handling: ``biolib`` is imported at module load behind a guarded
try/except. If it is missing, ``BIOLIB_AVAILABLE`` is False and ``run()``
returns a clean error telling the caller to ``pip install pybiolib`` -- it never
raises ImportError to the framework.
"""

import os
import re
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool

# ---------------------------------------------------------------------------
# Guarded optional dependency (framework optional-dep design)
# ---------------------------------------------------------------------------
try:
    import biolib  # noqa: F401

    BIOLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when dep absent
    biolib = None
    BIOLIB_AVAILABLE = False


# Map the user-facing model choice -> (BioLib app URI, CLI fasta flag).
_MODEL_MAP = {
    "deeptmhmm": ("DTU/DeepTMHMM", "--fasta"),
    "signalp": ("DTU/SignalP_6", "--fastafile"),
    "deeploc": ("KU/DeepLocPro", "--fasta"),
}

# Hard ceiling on how long we will block waiting for a BioLib job, in seconds.
# BioLib jobs queue on shared compute and routinely take 2-5 minutes.
_DEFAULT_MAX_WAIT = 600
_MAX_ALLOWED_WAIT = 1800

# Refuse absurdly large inputs so we never submit something that will hang.
_MAX_SEQ_LEN = 5000
_MAX_RECORDS = 50


@register_tool("DTUProteinTool")
class DTUProteinTool(BaseTool):
    """Run DTU Health Tech protein predictors (DeepTMHMM / SignalP / DeepLoc).

    Takes a protein FASTA (inline sequence/FASTA text or a file path) plus a
    model choice, submits the job to the BioLib cloud via ``pybiolib``, waits
    (bounded) for the result, and returns a parsed prediction.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})

    # ------------------------------------------------------------------ run
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not BIOLIB_AVAILABLE:
            return {
                "status": "error",
                "error": (
                    "The 'pybiolib' package is required to run DTU protein "
                    "predictors. Install it with: pip install pybiolib"
                ),
            }

        model = str(arguments.get("model", "deeptmhmm")).strip().lower()
        if model not in _MODEL_MAP:
            return {
                "status": "error",
                "error": (
                    f"Unknown model '{model}'. Choose one of: "
                    f"{', '.join(sorted(_MODEL_MAP))}."
                ),
            }

        # Resolve the FASTA input into a text blob.
        fasta_text, err = self._resolve_fasta(arguments)
        if err:
            return {"status": "error", "error": err}

        records = self._parse_fasta(fasta_text)
        if not records:
            return {
                "status": "error",
                "error": (
                    "No protein records found. Provide a FASTA sequence via "
                    "'sequence' / 'fasta' (inline text or amino-acid string) "
                    "or 'fasta_path' (path to a .fasta file)."
                ),
            }
        if len(records) > _MAX_RECORDS:
            return {
                "status": "error",
                "error": (
                    f"Too many sequences ({len(records)}); max {_MAX_RECORDS} "
                    "per call to keep cloud runtime bounded."
                ),
            }
        for name, seq in records:
            if len(seq) > _MAX_SEQ_LEN:
                return {
                    "status": "error",
                    "error": (
                        f"Sequence '{name}' has length {len(seq)} > "
                        f"{_MAX_SEQ_LEN}; split or shorten it."
                    ),
                }

        max_wait = self._clamp_wait(arguments.get("max_wait_time"))
        return self._run_biolib(model, records, max_wait)

    # ----------------------------------------------------------- input prep
    def _resolve_fasta(
        self, arguments: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (fasta_text, error). Accepts a path, FASTA text, or a bare
        amino-acid sequence."""
        path = arguments.get("fasta_path")
        if path:
            if not os.path.isfile(path):
                return None, f"fasta_path does not exist: {path}"
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    return fh.read(), None
            except OSError as exc:
                return None, f"Could not read fasta_path: {exc}"

        text = arguments.get("sequence") or arguments.get("fasta")
        if not text or not str(text).strip():
            return None, (
                "Provide a protein via 'sequence'/'fasta' (FASTA text or a bare "
                "amino-acid string) or 'fasta_path' (file path)."
            )
        text = str(text).strip()
        # Bare amino-acid string (no header) -> wrap it.
        if not text.startswith(">"):
            cleaned = re.sub(r"\s+", "", text).upper()
            text = f">query\n{cleaned}"
        return text, None

    @staticmethod
    def _parse_fasta(text: str) -> List[Tuple[str, str]]:
        """Parse FASTA text into [(name, sequence), ...]."""
        records: List[Tuple[str, str]] = []
        name: Optional[str] = None
        chunks: List[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if name is not None:
                    records.append((name, "".join(chunks)))
                name = line[1:].strip().split()[0] if line[1:].strip() else "query"
                chunks = []
            else:
                chunks.append(re.sub(r"\s+", "", line).upper())
        if name is not None:
            records.append((name, "".join(chunks)))
        # Drop records with empty sequence.
        return [(n, s) for n, s in records if s]

    @staticmethod
    def _clamp_wait(value: Any) -> int:
        try:
            wait = int(value)
        except (TypeError, ValueError):
            return _DEFAULT_MAX_WAIT
        return max(30, min(wait, _MAX_ALLOWED_WAIT))

    # --------------------------------------------------------- biolib runner
    def _run_biolib(
        self, model: str, records: List[Tuple[str, str]], max_wait: int
    ) -> Dict[str, Any]:
        app_uri, fasta_flag = _MODEL_MAP[model]

        # Write the FASTA into a temp dir. BioLib uploads input files by their
        # path RELATIVE to the current working directory, so we run cli() from
        # inside the temp dir and reference the file by bare name (an absolute
        # path resolves to a non-existent path inside the remote sandbox ->
        # "FASTA file not found").
        tmp_dir = tempfile.mkdtemp(prefix="dtu_protein_")
        fasta_name = "input.fasta"
        fasta_path = os.path.join(tmp_dir, fasta_name)
        try:
            with open(fasta_path, "w", encoding="utf-8") as fh:
                for name, seq in records:
                    fh.write(f">{name}\n{seq}\n")
        except OSError as exc:
            return {"status": "error", "error": f"Could not stage FASTA: {exc}"}

        try:
            app = biolib.load(app_uri)
        except Exception as exc:  # network / not-found / auth
            return {
                "status": "error",
                "error": f"Could not load BioLib app '{app_uri}': {exc}",
            }

        cli_args = self._build_cli_args(model, fasta_flag, fasta_name)
        prev_cwd = os.getcwd()
        try:
            os.chdir(tmp_dir)
            try:
                job = app.cli(args=cli_args, blocking=True)
            except TypeError:
                # Older/newer signature without 'blocking' kwarg.
                job = app.cli(args=cli_args)
        except Exception as exc:
            return self._job_error(app_uri, exc)
        finally:
            os.chdir(prev_cwd)

        # Wait (bounded) for completion if the API is non-blocking.
        wait_err = self._wait_for_job(job, max_wait)
        if wait_err:
            return {"status": "error", "error": wait_err}

        outputs = self._collect_outputs(job)
        if not outputs:
            stdout = self._safe_stdout(job)
            return {
                "status": "error",
                "error": (
                    f"BioLib app '{app_uri}' produced no output files. "
                    f"Job stdout (truncated): {stdout[:500]}"
                ),
            }

        parsed = self._parse_outputs(model, outputs, records)
        return {
            "status": "success",
            "data": {
                "model": model,
                "app": app_uri,
                "num_sequences": len(records),
                "predictions": parsed,
            },
        }

    @staticmethod
    def _build_cli_args(model: str, fasta_flag: str, fasta_name: str) -> str:
        # fasta_name is a bare filename; cli() runs from the temp dir (cwd).
        args = f"{fasta_flag} {fasta_name}"
        if model == "signalp":
            # SignalP-6 needs organism, a text output format, and an output dir
            # (without --output_dir the BioLib app writes no files).
            args += " --organism other --format txt --mode fast --output_dir output"
        elif model == "deeploc":
            # DeepLocPro takes an output dir flag. NOTE: the upstream
            # KU/DeepLocPro app currently crashes during ESM embedding with a
            # device-mismatch RuntimeError; this tool surfaces that as a clean
            # error until the app is fixed.
            args += " --output output"
        return args

    @staticmethod
    def _job_error(app_uri: str, exc: Exception) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": f"BioLib job for '{app_uri}' failed to start: {exc}",
        }

    def _wait_for_job(self, job: Any, max_wait: int) -> Optional[str]:
        """Block (bounded) until the job finishes. Returns an error string on
        timeout/failure, else None. Tolerant of API differences across
        pybiolib versions."""
        waiter = getattr(job, "wait", None)
        if callable(waiter):
            try:
                try:
                    waiter(timeout=max_wait)
                except TypeError:
                    waiter()
            except Exception as exc:
                name = type(exc).__name__
                if "Timeout" in name or "timeout" in str(exc).lower():
                    return (
                        f"BioLib job did not finish within {max_wait}s "
                        "(jobs queue on shared compute; raise max_wait_time)."
                    )
                return f"BioLib job wait failed: {exc}"
        # Verify the job actually succeeded when an exit code is exposed.
        getter = getattr(job, "get_exit_code", None)
        if callable(getter):
            try:
                code = getter()
                if code not in (None, 0):
                    stdout = self._safe_stdout(job)
                    return (
                        f"BioLib job exited with code {code}. "
                        f"stdout (truncated): {stdout[:500]}"
                    )
            except Exception:
                pass
        return None

    @staticmethod
    def _safe_stdout(job: Any) -> str:
        getter = getattr(job, "get_stdout", None)
        if not callable(getter):
            return ""
        try:
            out = getter()
            return (
                out.decode("utf-8", "replace") if isinstance(out, bytes) else str(out)
            )
        except Exception:
            return ""

    @staticmethod
    def _collect_outputs(job: Any) -> Dict[str, str]:
        """Return {filename: text_content} for all readable output files."""
        outputs: Dict[str, str] = {}
        lister = getattr(job, "list_output_files", None)
        if not callable(lister):
            return outputs
        try:
            files = lister()
        except Exception:
            return outputs
        for f in files or []:
            name = getattr(f, "path", None) or str(f)
            try:
                handle = job.get_output_file(name)
                data = handle.get_data()
                if isinstance(data, bytes):
                    # Skip binary (e.g. plot.png); keep text outputs only.
                    if name.lower().endswith((".png", ".jpg", ".pdf", ".gz")):
                        continue
                    data = data.decode("utf-8", "replace")
                outputs[name] = data
            except Exception:
                continue
        return outputs

    # ----------------------------------------------------------- parsers
    def _parse_outputs(
        self,
        model: str,
        outputs: Dict[str, str],
        records: List[Tuple[str, str]],
    ) -> List[Dict[str, Any]]:
        if model == "deeptmhmm":
            return self._parse_deeptmhmm(outputs, records)
        if model == "signalp":
            return self._parse_signalp(outputs, records)
        return self._parse_deeploc(outputs, records)

    @staticmethod
    def _find_output(outputs: Dict[str, str], *suffixes: str) -> Optional[str]:
        for name, content in outputs.items():
            low = name.lower()
            if any(low.endswith(sfx) for sfx in suffixes):
                return content
        return None

    def _parse_deeptmhmm(
        self, outputs: Dict[str, str], records: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """Parse DeepTMHMM .3line topology + .gff3 region table."""
        results: List[Dict[str, Any]] = []
        three_line = self._find_output(outputs, ".3line") or ""
        gff3 = self._find_output(outputs, ".gff3", ".gff") or ""

        # .3line: blocks of (>name | TYPE) / sequence / topology-string.
        topo_by_name: Dict[str, Dict[str, str]] = {}
        block: List[str] = []
        for line in three_line.splitlines():
            if line.startswith(">"):
                self._flush_3line(block, topo_by_name)
                block = [line]
            elif line.strip():
                block.append(line)
        self._flush_3line(block, topo_by_name)

        # .gff3: per-protein region rows -> [{kind, start, end}]
        regions_by_name = self._parse_gff_regions(gff3)

        for name, seq in records:
            info = topo_by_name.get(name, {})
            results.append(
                {
                    "id": name,
                    "sequence_length": len(seq),
                    "classification": info.get("type"),
                    "topology": info.get("topology"),
                    "regions": regions_by_name.get(name, []),
                }
            )
        return results

    @staticmethod
    def _flush_3line(block: List[str], out: Dict[str, Dict[str, str]]) -> None:
        if len(block) < 3 or not block[0].startswith(">"):
            return
        header = block[0][1:].strip()
        # ">name | TYPE"
        parts = [p.strip() for p in header.split("|")]
        name = parts[0].split()[0] if parts[0] else "query"
        ptype = parts[1] if len(parts) > 1 else None
        out[name] = {"type": ptype, "topology": block[2].strip()}

    @staticmethod
    def _parse_gff_regions(gff: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse a region table into {name: [{kind, start, end}]}.

        Handles two layouts seen across DTU tools:
          * Standard GFF3 (SignalP): seqid, source, type, start, end, ...
          * DeepTMHMM TMRs.gff3:      seqid, kind,   start, end
        Layout is detected per-row by where the two integer columns sit.
        """
        regions: Dict[str, List[Dict[str, Any]]] = {}
        for line in gff.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            cols = [c.strip() for c in line.split("\t")]
            if len(cols) < 4:
                continue
            name = cols[0]
            parsed = None
            # Standard GFF3: kind=col2, start=col3, end=col4.
            if len(cols) >= 5 and cols[3].isdigit() and cols[4].isdigit():
                parsed = (cols[2], int(cols[3]), int(cols[4]))
            # DeepTMHMM custom: kind=col1, start=col2, end=col3.
            elif cols[2].isdigit() and cols[3].isdigit():
                parsed = (cols[1], int(cols[2]), int(cols[3]))
            if parsed:
                kind, start, end = parsed
                regions.setdefault(name, []).append(
                    {"kind": kind, "start": start, "end": end}
                )
        return regions

    def _parse_signalp(
        self, outputs: Dict[str, str], records: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """Parse SignalP-6 prediction_results.txt / .gff3."""
        results: List[Dict[str, Any]] = []
        txt = self._find_output(outputs, "prediction_results.txt", ".txt") or ""
        gff = self._find_output(outputs, ".gff3", ".gff") or ""

        # prediction_results.txt rows:
        #   ID  Prediction  OTHER  SP(..)  ...  CS Position
        # The last column holds e.g. "CS pos: 22-23. Pr: 0.8406" for SP hits.
        calls: Dict[str, Dict[str, Any]] = {}
        for line in txt.splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                continue
            cs = None
            m = re.search(r"CS pos:\s*(\d+)", cols[-1])
            if m:
                cs = int(m.group(1))
            calls[cols[0].strip()] = {
                "prediction": cols[1].strip(),
                "cleavage_site": cs,
            }

        # Fallback: the signal_peptide region end from the GFF3 output.
        cleavage = self._parse_gff_regions(gff)

        for name, seq in records:
            call = calls.get(name, {})
            cs = call.get("cleavage_site")
            if cs is None:
                for r in cleavage.get(name, []):
                    if "signal" in r.get("kind", "").lower():
                        cs = r.get("end")
            results.append(
                {
                    "id": name,
                    "sequence_length": len(seq),
                    "prediction": call.get("prediction"),
                    "has_signal_peptide": (
                        bool(call.get("prediction"))
                        and call["prediction"].upper() != "OTHER"
                    )
                    if call.get("prediction")
                    else None,
                    "cleavage_site": cs,
                }
            )
        return results

    def _parse_deeploc(
        self, outputs: Dict[str, str], records: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """Parse DeepLoc(Pro) CSV/TSV results (ID, Localization, ...)."""
        results: List[Dict[str, Any]] = []
        table = self._find_output(outputs, ".csv", ".tsv", ".txt") or ""

        rows: Dict[str, Dict[str, Any]] = {}
        header: List[str] = []
        delim = "\t" if "\t" in table.splitlines()[0] else ","
        for i, line in enumerate(table.splitlines()):
            if not line.strip():
                continue
            cols = [c.strip() for c in line.split(delim)]
            if i == 0:
                header = [c.lower() for c in cols]
                continue
            rec = dict(zip(header, cols))
            rid = (
                rec.get("protein_id")
                or rec.get("id")
                or rec.get("name")
                or (cols[0] if cols else None)
            )
            if rid:
                rows[rid] = rec

        for name, seq in records:
            rec = rows.get(name, {})
            loc = (
                rec.get("localization") or rec.get("prediction") or rec.get("location")
            )
            results.append(
                {
                    "id": name,
                    "sequence_length": len(seq),
                    "localization": loc,
                    "details": rec or None,
                }
            )
        return results
