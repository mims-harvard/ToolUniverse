"""
Canonical VCF/BCF variant statistics for ToolUniverse.

Local-compute, deterministic variant summaries over a user-supplied VCF/BCF
file, backed by ``bcftools`` (htslib). The goal is to give every agent the
SAME numbers for "how many SNPs / indels are in this VCF": ad-hoc Python
parsers disagree on multiallelic splitting, indel left-alignment, and PASS/QUAL
filtering, so the same file yields different counts run-to-run. Routing those
questions through ``bcftools stats`` / ``bcftools norm`` makes them reproducible.

No network, no API key. Requires the ``bcftools`` binary on PATH (htslib);
every handler returns a clear error dict if it is missing rather than raising.
"""

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

# bcftools stats on a whole-genome VCF can take a while; cap so a runaway call
# fails cleanly instead of hanging the agent.
_BCFTOOLS_TIMEOUT = 600

# Core record/SNP/indel/MNP counts shared by count_variants and normalize.
_CORE_COUNT_KEYS = ("records", "snps", "indels", "mnps")


def _err(msg: str) -> Dict[str, Any]:
    return {"status": "error", "error": msg}


def _ok(data: Dict[str, Any], **metadata) -> Dict[str, Any]:
    meta = {"engine": "bcftools"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


def _bcftools() -> Optional[str]:
    return shutil.which("bcftools")


def _resolve_vcf(arguments: Dict[str, Any]) -> Any:
    """Return a validated, existing VCF path or an error dict."""
    path = arguments.get("vcf_path")
    if not path or not str(path).strip():
        return _err("Missing required parameter: 'vcf_path'")
    path = os.path.expanduser(str(path).strip())
    if not os.path.isfile(path):
        return _err(f"VCF file not found: {path}")
    return path


def _run(cmds: List[List[str]]) -> Any:
    """Run one command, or a pipe of commands, capturing the final stdout.

    ``cmds`` is a list of argv lists; consecutive commands are connected by a
    pipe (cmd[0] | cmd[1] | ...). Returns stdout text or an error dict.
    """
    try:
        procs: List[subprocess.Popen] = []
        prev_stdout = None
        for i, argv in enumerate(cmds):
            is_last = i == len(cmds) - 1
            p = subprocess.Popen(
                argv,
                stdin=prev_stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # Let the upstream process receive SIGPIPE if a downstream one exits.
            if prev_stdout is not None:
                prev_stdout.close()
            prev_stdout = p.stdout
            procs.append(p)
            if is_last:
                out, _ = p.communicate(timeout=_BCFTOOLS_TIMEOUT)
        # Drain stderr of upstream processes and check their exit codes.
        for p in procs[:-1]:
            p.wait(timeout=_BCFTOOLS_TIMEOUT)
        for p in procs:
            if p.returncode not in (0, None):
                stderr_txt = (p.stderr.read() if p.stderr else b"") or b""
                detail = stderr_txt.decode("utf-8", "replace").strip()
                return _err(f"bcftools failed (exit {p.returncode}): {detail[:400]}")
        return out.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return _err(f"bcftools timed out after {_BCFTOOLS_TIMEOUT}s")
    except FileNotFoundError as e:
        return _err(f"Required binary not found: {e}")
    except Exception as e:  # pragma: no cover - defensive
        return _err(f"bcftools execution error: {e}")


def _parse_stats(text: str) -> Dict[str, Any]:
    """Parse ``bcftools stats`` output into structured counts."""
    summary: Dict[str, Any] = {}
    ts_tv: Dict[str, Any] = {}
    per_sample: List[Dict[str, Any]] = []
    for line in text.splitlines():
        if line.startswith("SN\t"):
            parts = line.split("\t")
            # SN  0  number of records:  1234
            key = parts[2].rstrip(":").replace("number of ", "")
            try:
                summary[key] = int(parts[3])
            except (IndexError, ValueError):
                continue
        elif line.startswith("TSTV\t"):
            parts = line.split("\t")
            # TSTV  0  ts  tv  ts/tv  ts(1stALT)  tv(1stALT)  ts/tv(1stALT)
            try:
                ts_tv = {
                    "ts": int(parts[2]),
                    "tv": int(parts[3]),
                    "ts_tv_ratio": float(parts[4]),
                }
            except (IndexError, ValueError):
                continue
        elif line.startswith("PSC\t"):
            parts = line.split("\t")
            # PSC  id  sample  nRefHom  nNonRefHom  nHets  nTs  nTv  nIndels ...  nMissing
            try:
                per_sample.append(
                    {
                        "sample": parts[2],
                        "nRefHom": int(parts[3]),
                        "nNonRefHom": int(parts[4]),
                        "nHets": int(parts[5]),
                        "nIndels": int(parts[8]),
                        "nMissing": int(parts[13]),
                    }
                )
            except (IndexError, ValueError):
                continue
    result: Dict[str, Any] = {
        "records": summary.get("records"),
        "snps": summary.get("SNPs"),
        "indels": summary.get("indels"),
        "mnps": summary.get("MNPs"),
        "multiallelic_sites": summary.get("multiallelic sites"),
        "multiallelic_snp_sites": summary.get("multiallelic SNP sites"),
        "samples": summary.get("samples"),
    }
    if ts_tv:
        result["ts_tv"] = ts_tv
    if per_sample:
        result["per_sample"] = per_sample
    return result


def _core_counts(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Pick the shared record/SNP/indel/MNP counts from a parsed stats dict."""
    return {k: parsed.get(k) for k in _CORE_COUNT_KEYS}


def _view_filter_argv(arguments: Dict[str, Any]) -> Any:
    """Build the ``bcftools view`` filter args, or None if no filter requested.

    Returns a list of extra argv tokens (without the trailing file), or an error
    dict, or None when nothing needs filtering (caller can stats the file
    directly).
    """
    argv: List[str] = []
    if arguments.get("pass_only"):
        argv += ["-f", "PASS,."]
    region = arguments.get("regions")
    if region:
        # -t (targets) streams without requiring a tabix index, so it works on
        # arbitrary user files; -r would need the VCF to be indexed.
        argv += ["-t", str(region)]
    min_qual = arguments.get("min_qual")
    expr = arguments.get("include_expr")
    include_parts = []
    if min_qual is not None:
        try:
            include_parts.append(f"QUAL>={float(min_qual)}")
        except (TypeError, ValueError):
            return _err(f"'min_qual' must be a number, got {min_qual!r}")
    if expr:
        include_parts.append(f"({expr})")
    if include_parts:
        argv += ["-i", " && ".join(include_parts)]
    return argv or None


@register_tool("VCFStatsTool")
class VCFStatsTool(BaseTool):
    """Deterministic SNP/indel/normalization statistics over a local VCF/BCF."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if _bcftools() is None:
            return _err(
                "bcftools not found on PATH. Install htslib/bcftools "
                "(e.g. `conda install -c bioconda bcftools` or `brew install bcftools`)."
            )
        operation = arguments.get("operation")
        handlers = {
            "summary_stats": self._summary_stats,
            "count_variants": self._count_variants,
            "normalize": self._normalize,
        }
        handler = handlers.get(operation)
        if handler is None:
            return _err(
                f"Unknown or missing 'operation': {operation!r}. "
                f"Expected one of: {', '.join(handlers)}"
            )
        return handler(arguments)

    # ---- operation: summary_stats / count_variants -------------------------
    def _stats(self, arguments: Dict[str, Any], counts_only: bool) -> Dict[str, Any]:
        vcf = _resolve_vcf(arguments)
        if isinstance(vcf, dict):
            return vcf
        filt = _view_filter_argv(arguments)
        if isinstance(filt, dict):
            return filt

        stats_cmd = ["bcftools", "stats", "-s", "-"]
        if filt is None:
            cmds = [stats_cmd + [vcf]]
        else:
            cmds = [["bcftools", "view"] + filt + [vcf], stats_cmd]
        out = _run(cmds)
        if isinstance(out, dict):
            return out
        parsed = _parse_stats(out)

        applied = {
            k: arguments.get(k)
            for k in ("regions", "pass_only", "min_qual", "include_expr")
            if arguments.get(k) not in (None, False, "")
        }
        data = _core_counts(parsed) if counts_only else parsed
        data["filters_applied"] = applied or None
        return _ok(data, file=os.path.basename(vcf))

    def _summary_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._stats(arguments, counts_only=False)

    def _count_variants(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._stats(arguments, counts_only=True)

    # ---- operation: normalize ---------------------------------------------
    def _normalize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        vcf = _resolve_vcf(arguments)
        if isinstance(vcf, dict):
            return vcf

        before = _run([["bcftools", "stats", vcf]])
        if isinstance(before, dict):
            return before

        norm_argv = ["bcftools", "norm"]
        ref = arguments.get("reference_fasta")
        if ref:
            ref = os.path.expanduser(str(ref).strip())
            if not os.path.isfile(ref):
                return _err(f"reference_fasta not found: {ref}")
            # -f enables left-alignment of indels against the reference.
            norm_argv += ["-f", ref]
        # Default: split multiallelic records into biallelic ones, which is what
        # makes per-allele SNP/indel counts deterministic.
        multiallelic = arguments.get("multiallelics", "split")
        if multiallelic == "split":
            norm_argv += ["-m", "-"]
        elif multiallelic == "join":
            norm_argv += ["-m", "+"]
        norm_argv += [vcf, "-Ou"]

        after = _run([norm_argv, ["bcftools", "stats", "-"]])
        if isinstance(after, dict):
            return after

        data = {
            "before": _core_counts(_parse_stats(before)),
            "after": _core_counts(_parse_stats(after)),
            "left_aligned": bool(ref),
            "multiallelics": multiallelic,
        }
        return _ok(data, file=os.path.basename(vcf))
