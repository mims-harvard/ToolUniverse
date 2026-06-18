"""
LDSC (LD Score Regression) — MCP Server.

LDSC (Bulik-Sullivan et al., Nature Genetics 2015; partitioned heritability:
Finucane et al., Nature Genetics 2015) estimates SNP-heritability and genetic
correlation from GWAS summary statistics. It is the standard tool for
quantifying polygenic signal and shared genetic architecture between traits.

Served as a ToolUniverse *remote* tool because the analysis requires (a) the
maintained Python-3 engine (NCI ``CBIIT/ldsc``, the modern successor to the
frozen Python-2.7 ``bulik/ldsc``) and (b) multi-GB precomputed LD-score
reference panels (e.g. ``eur_w_ld_chr`` and, for partitioned heritability, the
baseline/baselineLD annotations) that are impractical to bundle with a light
client. A self-hosted server stages those panels once and exposes the analyses.

A hosted alternative for users who cannot stage the panels is NCI's LDscore web
tool (https://ldlink.nih.gov/ldscore), the browser front-end to this same
engine.

Two operations:
  * run_ldsc_heritability        -> SNP-heritability (h2), SE, intercept, ratio
  * run_ldsc_genetic_correlation -> genetic correlation (rg), SE, p, per-trait h2

The server shells out to the configured ``ldsc.py``; both ``LDSC_DIR`` (the
clone path) and ``LDSC_REF_DIR`` (the reference-panel directory) are read from
the environment.

References
----------
Bulik-Sullivan BK, Loh P-R, Finucane HK, et al. "LD Score regression
distinguishes confounding from polygenicity in genome-wide association
studies." Nature Genetics 47, 291-295 (2015).
Finucane HK, Bulik-Sullivan B, Gusev A, et al. "Partitioning heritability by
functional annotation using genome-wide association summary statistics."
Nature Genetics 47, 1228-1235 (2015).
"""

import os
import re
import subprocess
import tempfile
from typing import Any, Dict, Optional

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

LDSC_DIR = os.environ.get("LDSC_DIR", "/opt/ldsc")
LDSC_REF_DIR = os.environ.get("LDSC_REF_DIR", "/data/ldsc")
_TIMEOUT = 1800


def _ref(path_or_name: Optional[str], default: str) -> str:
    """Resolve a reference-panel argument relative to LDSC_REF_DIR when not absolute."""
    name = path_or_name or default
    return name if os.path.isabs(name) else os.path.join(LDSC_REF_DIR, name)


def _run_ldsc(args: list) -> Dict[str, Any]:
    """Run ldsc.py with a temp --out prefix; return parsed log text or an error."""
    ldsc_py = os.path.join(LDSC_DIR, "ldsc.py")
    if not os.path.exists(ldsc_py):
        return {"error": f"ldsc.py not found at {ldsc_py}; set LDSC_DIR to the clone."}
    with tempfile.TemporaryDirectory() as tmp:
        out_prefix = os.path.join(tmp, "ldsc_out")
        cmd = ["python", ldsc_py, *args, "--out", out_prefix]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT)
        except subprocess.TimeoutExpired:
            return {"error": f"LDSC timed out after {_TIMEOUT}s."}
        log_path = out_prefix + ".log"
        if os.path.exists(log_path):
            with open(log_path) as fh:
                log = fh.read()
        else:
            log = proc.stdout
        if proc.returncode != 0:
            return {"error": f"LDSC failed: {proc.stderr[-500:] or log[-500:]}"}
        return {"log": log}


def _search(pattern: str, text: str):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


@register_mcp_tool(
    tool_type_name="run_ldsc_heritability",
    config={
        "description": (
            "Estimate SNP-heritability from GWAS summary statistics with LD Score "
            "regression. Input a munged .sumstats(.gz) file; returns observed-scale "
            "h2 with SE, the LD-score-regression intercept (inflation diagnostic), "
            "and the ratio. Requires LD-score reference panels on the server."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sumstats_path": {
                    "type": "string",
                    "description": "Server-accessible path to a munged .sumstats.gz file (output of munge_sumstats.py).",
                },
                "ref_ld_chr": {
                    "type": "string",
                    "description": "Reference LD-score prefix/dir (default 'eur_w_ld_chr/', resolved under LDSC_REF_DIR).",
                },
                "w_ld_chr": {
                    "type": "string",
                    "description": "Regression-weight LD-score prefix/dir (default same as ref_ld_chr).",
                },
            },
            "required": ["sumstats_path"],
        },
    },
    mcp_config={
        "server_name": "LDSC MCP Server",
        "host": "127.0.0.1",
        "port": 8013,
        "transport": "http",
    },
)
class LdscHeritabilityTool:
    """Estimate SNP-heritability via LD Score regression."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sumstats = arguments.get("sumstats_path")
        if not sumstats:
            return {"error": "Missing required parameter: sumstats_path"}
        ref = _ref(arguments.get("ref_ld_chr"), "eur_w_ld_chr/")
        w = _ref(
            arguments.get("w_ld_chr") or arguments.get("ref_ld_chr"), "eur_w_ld_chr/"
        )

        res = _run_ldsc(["--h2", sumstats, "--ref-ld-chr", ref, "--w-ld-chr", w])
        if "error" in res:
            return res
        log = res["log"]
        h2 = re.search(r"Total Observed scale h2:\s*([\-0-9.]+)\s*\(([\-0-9.]+)\)", log)
        return {
            "model": "LDSC",
            "analysis": "heritability",
            "h2": float(h2.group(1)) if h2 else None,
            "h2_se": float(h2.group(2)) if h2 else None,
            "intercept": _search(r"Intercept:\s*([\-0-9.]+)", log),
            "ratio": _search(r"Ratio:\s*([\-0-9.]+)", log),
            "log_tail": log[-800:],
        }


@register_mcp_tool(
    tool_type_name="run_ldsc_genetic_correlation",
    config={
        "description": (
            "Estimate the genetic correlation (rg) between two traits from their "
            "GWAS summary statistics with cross-trait LD Score regression. Input "
            "two munged .sumstats(.gz) files; returns rg with SE and p-value plus "
            "each trait's h2. Requires LD-score reference panels on the server."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sumstats_path_1": {
                    "type": "string",
                    "description": "Munged .sumstats.gz for trait 1.",
                },
                "sumstats_path_2": {
                    "type": "string",
                    "description": "Munged .sumstats.gz for trait 2.",
                },
                "ref_ld_chr": {
                    "type": "string",
                    "description": "Reference LD-score prefix/dir (default 'eur_w_ld_chr/').",
                },
                "w_ld_chr": {
                    "type": "string",
                    "description": "Regression-weight LD-score prefix/dir (default same as ref_ld_chr).",
                },
            },
            "required": ["sumstats_path_1", "sumstats_path_2"],
        },
    },
    mcp_config={
        "server_name": "LDSC MCP Server",
        "host": "127.0.0.1",
        "port": 8013,
        "transport": "http",
    },
)
class LdscGeneticCorrelationTool:
    """Estimate cross-trait genetic correlation via LD Score regression."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        s1 = arguments.get("sumstats_path_1")
        s2 = arguments.get("sumstats_path_2")
        if not (s1 and s2):
            return {
                "error": "Missing required parameter(s): sumstats_path_1, sumstats_path_2"
            }
        ref = _ref(arguments.get("ref_ld_chr"), "eur_w_ld_chr/")
        w = _ref(
            arguments.get("w_ld_chr") or arguments.get("ref_ld_chr"), "eur_w_ld_chr/"
        )

        res = _run_ldsc(["--rg", f"{s1},{s2}", "--ref-ld-chr", ref, "--w-ld-chr", w])
        if "error" in res:
            return res
        log = res["log"]
        return {
            "model": "LDSC",
            "analysis": "genetic_correlation",
            "rg": _search(r"Genetic Correlation:\s*([\-0-9.]+)", log),
            "rg_se": _search(
                r"Genetic Correlation:\s*[\-0-9.]+\s*\(([\-0-9.]+)\)", log
            ),
            "p_value": _search(r"P:\s*([\-0-9.eE]+)", log),
            "log_tail": log[-800:],
        }


if __name__ == "__main__":
    start_mcp_server()
