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

import os
import subprocess
import tempfile
from typing import Any, Dict, List

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_TIMEOUT = 1800
_VALID_FORMATS = {"AUTO", "BAM", "BED", "BAMPE", "BEDPE", "ELAND", "SAM", "BOWTIE"}


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
        summary["median_peak_width"] = sorted(widths)[n_peaks // 2]
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
                    "description": "Server-accessible path to the treatment/ChIP alignment file (BAM/BED/BED-PE).",
                },
                "control": {
                    "type": "string",
                    "description": "Server-accessible path to the input/control alignment file (optional but recommended).",
                },
                "format": {
                    "type": "string",
                    "description": "Input format: AUTO (default), BAM, BED, BAMPE, or BEDPE. Use BAMPE/BEDPE for paired-end (e.g. ATAC-seq).",
                },
                "genome_size": {
                    "type": "string",
                    "description": "Effective genome size: 'hs' (human, default), 'mm' (mouse), 'ce' (worm), 'dm' (fly), or a number (e.g. '2.7e9').",
                },
                "qvalue": {
                    "type": "number",
                    "description": "q-value (minimum FDR) cutoff to call significant peaks (default 0.05).",
                },
                "top_n": {
                    "type": "integer",
                    "description": "Number of top peaks (by score) to return (default 50).",
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
        treatment = arguments.get("treatment")
        if not treatment:
            return {"error": "Missing required parameter: treatment"}
        if not os.path.exists(treatment):
            return {"error": f"Treatment file not found: {treatment}"}

        control = arguments.get("control") or None
        if control and not os.path.exists(control):
            return {"error": f"Control file not found: {control}"}

        fmt = (arguments.get("format") or "AUTO").upper()
        if fmt not in _VALID_FORMATS:
            return {
                "error": f"Invalid format '{fmt}'; expected one of {sorted(_VALID_FORMATS)}."
            }
        genome_size = str(arguments.get("genome_size") or "hs")

        try:
            qvalue = float(arguments.get("qvalue") or 0.05)
        except (TypeError, ValueError):
            return {"error": "Parameter 'qvalue' must be a number."}
        top_n = arguments.get("top_n")
        try:
            top_n = 50 if top_n is None else int(top_n)
        except (TypeError, ValueError):
            return {"error": "Parameter 'top_n' must be an integer."}
        nomodel = bool(arguments.get("nomodel", False))
        try:
            extsize = int(arguments.get("extsize") or 200)
        except (TypeError, ValueError):
            return {"error": "Parameter 'extsize' must be an integer."}

        name = "macs3_run"
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [
                "macs3",
                "callpeak",
                "-t",
                treatment,
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
                cmd[4:4] = ["-c", control]
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

            narrowpeak = os.path.join(tmp, f"{name}_peaks.narrowPeak")
            if not os.path.exists(narrowpeak):
                stderr = (proc.stderr or "")[-500:]
                return {
                    "error": f"MACS3 did not produce a narrowPeak output (returncode {proc.returncode}): {stderr}"
                }

            try:
                parsed = _parse_narrowpeak(narrowpeak, top_n)
            except OSError as exc:
                return {"error": f"Failed to read narrowPeak output: {exc}"}

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
