"""LDlink (NIH) linkage-disequilibrium tool for ToolUniverse.

LDlink computes population-specific LD between variants. The LDproxy module
returns variants in LD with a query SNP (proxies) — essential for resolving
whether a GWAS lead SNP is the likely causal variant or just tags one.

API: https://ldlink.nih.gov/LDlinkRest/  (free; requires a registered token,
read from the LDLINK_TOKEN environment variable).
Register: https://ldlink.nih.gov/?tab=apiaccess
"""

import os
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

LDLINK_URL = "https://ldlink.nih.gov/LDlinkRest"


@register_tool("LDlinkTool")
class LDlinkTool(BaseTool):
    """Find LD proxy variants for a SNP via LDlink's LDproxy module."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.token = os.environ.get("LDLINK_TOKEN", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            return {
                "status": "error",
                "error": (
                    "LDlink requires a free API token. Register at "
                    "https://ldlink.nih.gov/?tab=apiaccess and set the LDLINK_TOKEN "
                    "environment variable."
                ),
            }
        variant = (arguments.get("variant") or arguments.get("rsid") or "").strip()
        if not variant:
            return {
                "status": "error",
                "error": "variant (rsID, e.g. 'rs7903146') is required",
            }

        population = arguments.get("population", "CEU")
        genome_build = arguments.get("genome_build", "grch38")
        try:
            r2_threshold = float(arguments.get("r2_threshold", 0.8))
        except (TypeError, ValueError):
            r2_threshold = 0.8
        try:
            limit = max(1, min(int(arguments.get("limit", 50)), 500))
        except (TypeError, ValueError):
            limit = 50

        params = {
            "var": variant,
            "pop": population,
            "r2_d": "r2",
            "genome_build": genome_build,
            "token": self.token,
        }
        try:
            resp = requests.get(
                f"{LDLINK_URL}/ldproxy", params=params, timeout=self.timeout
            )
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"LDlink returned HTTP {resp.status_code}",
                }
            text = resp.text
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"LDlink timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"LDlink request failed: {e}"}

        if text.lstrip().startswith("{") and '"error"' in text:
            import json as _json

            try:
                return {
                    "status": "error",
                    "error": _json.loads(text).get("error", text[:200]),
                }
            except Exception:
                return {"status": "error", "error": text[:200]}

        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) < 2:
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "LDlink (LDproxy)",
                    "query": variant,
                    "total": 0,
                },
            }
        header = lines[0].split("\t")
        idx = {h.strip(): i for i, h in enumerate(header)}
        proxies = []
        for ln in lines[1:]:
            f = ln.split("\t")
            if len(f) < len(header):
                continue
            try:
                r2 = float(f[idx.get("R2", -1)]) if "R2" in idx else None
            except (ValueError, TypeError):
                r2 = None
            if r2 is not None and r2 < r2_threshold:
                continue
            proxies.append(
                {
                    "rsid": f[idx.get("RS_Number", 0)],
                    "coord": f[idx.get("Coord", 1)] if "Coord" in idx else None,
                    "alleles": f[idx.get("Alleles", 2)] if "Alleles" in idx else None,
                    "maf": f[idx.get("MAF", -1)] if "MAF" in idx else None,
                    "distance": f[idx.get("Distance", -1)]
                    if "Distance" in idx
                    else None,
                    "r2": r2,
                }
            )
        proxies.sort(key=lambda p: (p["r2"] is not None, p["r2"] or 0), reverse=True)
        return {
            "status": "success",
            "data": proxies[:limit],
            "metadata": {
                "source": "LDlink (LDproxy)",
                "query": variant,
                "population": population,
                "genome_build": genome_build,
                "r2_threshold": r2_threshold,
                "total": len(proxies),
                "returned": min(len(proxies), limit),
                "interpretation": (
                    "Proxies with R2 close to 1 are in tight LD with the query SNP; "
                    "the causal variant may be any of them, so a high-R2 proxy in a "
                    "coding region or regulatory element is a better mechanistic "
                    "candidate than the lead SNP itself."
                ),
            },
        }
