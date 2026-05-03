# opencravat_tool.py
"""
OpenCRAVAT (Open Custom Ranked Analysis of Variants Toolkit) API tool.

OpenCRAVAT aggregates 182+ variant annotation sources into a single query,
including ClinVar, gnomAD, SIFT, PolyPhen-2, CADD, REVEL, AlphaMissense,
SpliceAI, GERP, PhastCons, DANN, FATHMM, and many more.

API: https://run.opencravat.org/submit/annotate (single variant, no auth)
API: https://run.opencravat.org/submit/annotators (list available annotators)
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

OPENCRAVAT_BASE_URL = "https://run.opencravat.org/submit"


@register_tool("OpenCRAVATTool")
class OpenCRAVATTool(BaseTool):
    """
    Tool for querying OpenCRAVAT variant annotation API.

    Supports single-variant annotation with configurable annotator selection.
    No authentication required for the public annotation endpoint.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "annotate_variant"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the OpenCRAVAT API call."""
        op = self.operation
        if op == "annotate_variant":
            return self._annotate_variant(arguments)
        if op == "list_annotators":
            return self._list_annotators(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    def _annotate_variant(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Annotate a single variant with multiple annotation sources."""
        chrom = arguments.get("chrom") or arguments.get("chromosome", "")
        pos = arguments.get("pos") or arguments.get("position")
        ref_base = arguments.get("ref_base") or arguments.get("ref", "")
        alt_base = arguments.get("alt_base") or arguments.get("alt", "")
        annotators = arguments.get("annotators")

        if not all([chrom, pos, ref_base, alt_base]):
            return {
                "status": "error",
                "error": "chrom, pos, ref_base, and alt_base are all required",
            }

        # Ensure chr prefix
        if not str(chrom).startswith("chr"):
            chrom = f"chr{chrom}"

        params = {
            "chrom": chrom,
            "pos": int(pos),
            "ref_base": ref_base.upper(),
            "alt_base": alt_base.upper(),
        }
        if annotators:
            params["annotators"] = annotators

        try:
            resp = requests.get(
                f"{OPENCRAVAT_BASE_URL}/annotate",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "OpenCRAVAT API request timed out"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"OpenCRAVAT API error: {e}"}
        except ValueError:
            return {"status": "error", "error": "Invalid JSON response from OpenCRAVAT"}

        crx = data.get("crx", {})
        result = {
            "gene": crx.get("hugo"),
            "amino_acid_change": crx.get("achange"),
            "coding_change": crx.get("cchange"),
            "consequence": crx.get("so"),
            "transcript": crx.get("transcript"),
            "chrom": crx.get("chrom", chrom),
            "pos": crx.get("pos", pos),
            "ref_base": crx.get("ref_base", ref_base),
            "alt_base": crx.get("alt_base", alt_base),
            "annotations": {},
            "module_versions": data.get("module_versions", {}),
        }

        # Collect all annotation results
        skip_keys = {"crx", "alternateAlleles", "module_versions", "originalInput"}
        for key, val in data.items():
            if key not in skip_keys and val is not None:
                result["annotations"][key] = val

        return {"status": "success", "data": result}

    def _list_annotators(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available annotators on the OpenCRAVAT server."""
        category = arguments.get("category")

        try:
            resp = requests.get(
                f"{OPENCRAVAT_BASE_URL}/annotators",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"OpenCRAVAT API error: {e}"}
        except ValueError:
            return {"status": "error", "error": "Invalid JSON response from OpenCRAVAT"}

        annotators = []
        for name, info in data.items():
            entry = {
                "name": name,
                "title": info.get("title", ""),
                "description": info.get("description", ""),
                "type": info.get("type", ""),
            }
            if category and category.lower() not in entry["type"].lower():
                continue
            annotators.append(entry)

        annotators.sort(key=lambda x: x["name"])

        return {"status": "success", "data": annotators}
