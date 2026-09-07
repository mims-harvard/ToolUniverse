"""
MACS3 (Model-based Analysis of ChIP-Seq, v3) — MCP Server.

MACS (Zhang et al., Genome Biology 2008; MACS3: Gaspar 2021 / the macs3-project
maintained successor) is the field-standard peak caller for ChIP-seq and
ATAC-seq. ``macs3 callpeak`` models the read distribution along the genome to
identify regions of significant read enrichment (peaks) over a background /
input control, and is the typical first analysis step after alignment.

Served as a ToolUniverse *remote* tool because the analysis (a) shells out to
the ``macs3`` command-line engine (a compiled/Cython dependency) and (b) takes
large server-side alignment files (BAM / BED / BED-PE) as input rather than
inlined data. A self-hosted server stages the aligned reads once and exposes
peak calling.

One operation is served:
  * run_macs3_callpeak -> number of peaks, top-N peaks by score, summary stats

The server shells out to ``macs3 callpeak`` and parses the resulting
``<name>_peaks.narrowPeak`` (ENCODE narrowPeak = BED6+4: chrom, start, end,
name, score, strand, signalValue, pValue, qValue, peak).

References
----------
Zhang Y, Liu T, Meyer CA, et al. "Model-based Analysis of ChIP-Seq (MACS)."
Genome Biology 9, R137 (2008).
"""

import math
import os
import statistics
import subprocess
import tempfile
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_data_path import resolve_remote_data_path

_TIMEOUT = 1800
_VALID_FORMATS = {
    "AUTO",
    "BAM",
    "BAMPE",
    "BED",
    "BEDPE",
    "BOWTIE",
    "ELAND",
    "ELANDEXPORT",
    "ELANDMULTI",
    "FRAG",
    "SAM",
}
_ALIGNMENT_SUFFIXES = {
    ".bam",
    ".bed",
    ".bed.gz",
    ".bedpe",
    ".bowtie",
    ".eland",
    ".sam",
    ".tsv",
    ".tsv.gz",
    ".txt",
}
_MAX_TOP_N = 1000
_MAX_EXTSIZE = 1_000_000


def _parse_narrowpeak(path: str, top_n: int) -> Dict[str, Any]:
    """Parse an ENCODE narrowPeak (BED6+4) file -> count, top-N peaks, summary."""
    peaks: List[Dict[str, Any]] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(("#", "track", "browser")):
                continue
            cols = line.split("\t")
            if len(cols) < 9:
                continue
            try:
                peaks.append(
                    {
                        "chrom": cols[0],
                        "start": int(cols[1]),
                        "end": int(cols[2]),
                        "name": cols[3],
                        "score": float(cols[4]),
                        "signal_value": float(cols[6]),
                        "p_value": float(cols[7]),
                        "q_value": float(cols[8]),
                    }
                )
            except (ValueError, IndexError):
                continue

    n_peaks = len(peaks)
    top = sorted(peaks, key=lambda p: p["score"], reverse=True)[: max(top_n, 0)]
    top_peaks = [
        {
            "chrom": p["chrom"],
            "start": p["start"],
            "end": p["end"],
            "score": p["score"],
            "signal_value": p["signal_value"],
            "q_value": p["q_value"],
        }
        for p in top
    ]

    summary: Dict[str, Any] = {"n_peaks": n_peaks}
    if n_peaks:
        widths = [p["end"] - p["start"] for p in peaks]
        scores = [p["score"] for p in peaks]
        summary["mean_peak_width"] = round(sum(widths) / n_peaks, 2)
        summary["median_peak_width"] = statistics.median(widths)
        summary["max_score"] = max(scores)
        summary["mean_score"] = round(sum(scores) / n_peaks, 2)
    return {"n_peaks": n_peaks, "top_peaks": top_peaks, "summary": summary}


@register_mcp_tool(
    tool_type_name="run_macs3_callpeak",
    config={
        "description": (
            "Call ChIP-seq / ATAC-seq peaks from an aligned reads file with "
            "MACS3 `callpeak` (Zhang et al. 2008; macs3-project). Models read "
            "enrichment over a background/input control to identify significant "
            "peaks — the standard first step after alignment. Input is a "
            "server-accessible BAM/BED/BED-PE alignment file; returns the number "
            "of peaks, the top-N peaks by score, and summary statistics, parsed "
            "from the ENCODE narrowPeak output."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "treatment": {
                    "type": "string",
                    "description": "Treatment/ChIP alignment file inside the provider-configured data directory (BAM/BED/BED-PE).",
                },
                "control": {
                    "type": "string",
                    "description": "Input/control alignment file inside the provider-configured data directory (optional but recommended).",
                },
                "format": {
                    "type": "string",
                    "enum": [
                        "AUTO",
                        "BAM",
                        "BAMPE",
                        "BED",
                        "BEDPE",
                        "BOWTIE",
                        "ELAND",
                        "ELANDEXPORT",
                        "ELANDMULTI",
                        "FRAG",
                        "SAM",
                    ],
                    "default": "AUTO",
                    "description": "MACS3 input format. AUTO is the default; BAMPE, BEDPE, and FRAG must be selected explicitly for paired-end or fragment data.",
                },
                "genome_size": {
                    "type": "string",
                    "default": "hs",
                    "description": "Effective genome size: 'hs' (human, default), 'mm' (mouse), 'ce' (worm), 'dm' (fly), or a number (e.g. '2.7e9').",
                },
                "qvalue": {
                    "type": "number",
                    "default": 0.05,
                    "exclusiveMinimum": 0,
                    "maximum": 1,
                    "description": "q-value (minimum FDR) cutoff to call significant peaks (default 0.05).",
                },
                "top_n": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 1000,
                    "description": "Number of top peaks (by score) to return (default 50).",
                },
                "nomodel": {
                    "type": ["boolean", "null"],
                    "default": False,
                    "description": "Skip the shift-model step and pass --extsize. Use for appropriate single-end data; paired-end and FRAG modes infer fragment lengths. Default false.",
                },
                "extsize": {
                    "type": ["integer", "null"],
                    "default": 200,
                    "minimum": 1,
                    "maximum": 1000000,
                    "description": "Fragment extension size used with nomodel (default 200; ~147 for ATAC).",
                },
            },
            "required": ["treatment"],
        },
    },
    mcp_config={
        "server_name": "MACS3 MCP Server",
        "host": "127.0.0.1",
        "port": 8021,
        "transport": "http",
    },
)
class Macs3CallpeakTool:
    """Run MACS3 callpeak and return peak count, top peaks, and summary stats."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        treatment_value = arguments.get("treatment")
        if not treatment_value:
            return {"error": "Missing required parameter: treatment"}
        try:
            treatment = resolve_remote_data_path(
                treatment_value, allowed_suffixes=_ALIGNMENT_SUFFIXES
            )
        except ValueError as exc:
            return {"error": f"Invalid treatment file: {exc}"}

        control_value = arguments.get("control") or None
        control = None
        if control_value:
            try:
                control = resolve_remote_data_path(
                    control_value, allowed_suffixes=_ALIGNMENT_SUFFIXES
                )
            except ValueError as exc:
                return {"error": f"Invalid control file: {exc}"}

        format_value = arguments.get("format") or "AUTO"
        if not isinstance(format_value, str):
            return {"error": "Parameter 'format' must be a string."}
        fmt = format_value.upper()
        if fmt not in _VALID_FORMATS:
            return {
                "error": f"Invalid format '{fmt}'; expected one of {sorted(_VALID_FORMATS)}."
            }
        genome_size = arguments.get("genome_size") or "hs"
        if not isinstance(genome_size, str):
            return {"error": "Parameter 'genome_size' must be a string."}

        qvalue_value = arguments.get("qvalue", 0.05)
        if (
            isinstance(qvalue_value, bool)
            or not isinstance(qvalue_value, (int, float))
            or not math.isfinite(qvalue_value)
            or not 0 < qvalue_value <= 1
        ):
            return {"error": "Parameter 'qvalue' must be a finite number in (0, 1]."}
        qvalue = float(qvalue_value)

        top_n = arguments.get("top_n")
        top_n = 50 if top_n is None else top_n
        if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= _MAX_TOP_N:
            return {"error": f"Parameter 'top_n' must be an integer from 1 to {_MAX_TOP_N}."}

        nomodel_value = arguments.get("nomodel", False)
        nomodel = False if nomodel_value is None else nomodel_value
        if not isinstance(nomodel, bool):
            return {"error": "Parameter 'nomodel' must be a boolean."}

        extsize_value = arguments.get("extsize", 200)
        extsize = 200 if extsize_value is None else extsize_value
        if (
            isinstance(extsize, bool)
            or not isinstance(extsize, int)
            or not 1 <= extsize <= _MAX_EXTSIZE
        ):
            return {
                "error": f"Parameter 'extsize' must be an integer from 1 to {_MAX_EXTSIZE}."
            }

        name = "macs3_run"
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [
                "macs3",
                "callpeak",
                "-t",
                str(treatment),
                "-f",
                fmt,
                "-g",
                genome_size,
                "-n",
                name,
                "--outdir",
                tmp,
                "-q",
                str(qvalue),
            ]
            if control:
                cmd[4:4] = ["-c", str(control)]
            # --nomodel skips the cross-correlation shift-model step (which needs
            # paired +/- strand peaks); required for ATAC-seq and single-end data.
            if nomodel:
                cmd += ["--nomodel", "--extsize", str(extsize)]

            try:
                proc = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=_TIMEOUT
                )
            except FileNotFoundError:
                return {
                    "error": "macs3 executable not found on the server; install with `pip install macs3`."
                }
            except subprocess.TimeoutExpired:
                return {"error": f"MACS3 timed out after {_TIMEOUT}s."}
            except OSError:
                return {"error": "MACS3 could not be started by the provider."}

            narrowpeak = os.path.join(tmp, f"{name}_peaks.narrowPeak")
            if proc.returncode != 0:
                return {
                    "error": f"MACS3 failed on the provider (returncode {proc.returncode})."
                }
            if not os.path.exists(narrowpeak):
                return {
                    "error": "MACS3 completed without producing a narrowPeak output."
                }

            try:
                parsed = _parse_narrowpeak(narrowpeak, top_n)
            except OSError:
                return {"error": "Failed to read the MACS3 narrowPeak output."}

        return {
            "tool": "MACS3 callpeak",
            "n_peaks": parsed["n_peaks"],
            "top_peaks": parsed["top_peaks"],
            "summary": parsed["summary"],
            "format": fmt,
            "genome_size": genome_size,
            "qvalue": qvalue,
            "control_used": bool(control),
        }


if __name__ == "__main__":
    start_mcp_server()
