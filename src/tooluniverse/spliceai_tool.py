"""
SpliceAI Lookup REST API Tool

This tool provides access to SpliceAI and Pangolin splice prediction scores
via the Broad Institute's SpliceAI Lookup web service.

SpliceAI is a deep learning model that predicts splice-altering variants from
pre-mRNA sequences. It was developed by Illumina and provides delta scores
for acceptor gain/loss and donor gain/loss.

Pangolin is an alternative splice prediction model with similar functionality.

Note: The public API has rate limits (a few queries per minute per user).
For batch processing, users should set up a local instance.

API Documentation: https://github.com/broadinstitute/SpliceAI-lookup
"""

import requests
import re
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URLs for SpliceAI and Pangolin APIs
SPLICEAI_URLS = {
    "37": "https://spliceai-37-xwkwwwxdwq-uc.a.run.app/spliceai/",
    "38": "https://spliceai-38-xwkwwwxdwq-uc.a.run.app/spliceai/",
}

PANGOLIN_URLS = {
    "37": "https://pangolin-37-xwkwwwxdwq-uc.a.run.app/pangolin/",
    "38": "https://pangolin-38-xwkwwwxdwq-uc.a.run.app/pangolin/",
}


@register_tool("SpliceAITool")
class SpliceAITool(BaseTool):
    """
    SpliceAI and Pangolin Splice Prediction API tool.

    Provides access to deep learning-based splice prediction scores
    from the Broad Institute's SpliceAI Lookup service.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "")
        self.timeout = fields.get("timeout", 60)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to operation handler based on config."""
        operation = self.operation or arguments.get("operation")

        if not operation:
            return {"status": "error", "error": "Missing: operation"}

        operation_map = {
            "predict_splice": self._predict_splice,
            "predict_splice_pangolin": self._predict_splice_pangolin,
            "get_max_delta": self._get_max_delta,
        }

        handler = operation_map.get(operation)
        if not handler:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        return handler(arguments)

    def _normalize_variant(self, variant: str) -> str:
        """Normalize variant format to chr-pos-ref-alt."""
        # Remove spaces and standardize
        variant = variant.strip()

        # Handle various formats:
        # chr8-140300616-T-G (already normalized)
        # chr8:140300616:T:G (colon separated)
        # 8-140300616-T-G (without chr prefix)
        # 8:140300616:T:G (without chr prefix, colon)

        # Replace colons with dashes
        if ":" in variant:
            variant = variant.replace(":", "-")

        # Ensure chr prefix
        if not variant.lower().startswith("chr"):
            variant = "chr" + variant

        return variant

    def _validate_variant(self, variant: str) -> Optional[str]:
        """Validate variant format. Returns error message if invalid, None if valid."""
        pattern = r"^chr[\dXYMT]+-\d+-[ACGTN]+-[ACGTN]+$"
        if not re.match(pattern, variant, re.IGNORECASE):
            return f"Invalid variant format: {variant}. Expected format: chr-pos-ref-alt (e.g., chr8-140300616-T-G)"
        return None

    def _interpret_score(self, delta_score: float) -> str:
        """Interpret SpliceAI delta score."""
        if delta_score is None:
            return "unknown"
        if delta_score >= 0.8:
            return "high_pathogenicity"
        elif delta_score >= 0.5:
            return "moderate_pathogenicity"
        elif delta_score >= 0.2:
            return "low_pathogenicity"
        else:
            return "benign"

    def _predict_splice(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get SpliceAI predictions for a variant."""
        variant = arguments.get("variant")
        if not variant:
            return {"status": "error", "error": "Missing required parameter: variant"}

        genome = str(arguments.get("genome", "38"))
        if genome not in ["37", "38"]:
            return {"status": "error", "error": "genome must be '37' or '38'"}

        # Normalize and validate variant
        variant = self._normalize_variant(variant)
        error = self._validate_variant(variant)
        if error:
            return {"status": "error", "error": error}

        try:
            # Build URL
            base_url = SPLICEAI_URLS[genome]
            params = {"hg": genome, "variant": variant}

            # Optional parameters
            if "distance" in arguments:
                params["distance"] = arguments["distance"]
            if "mask" in arguments:
                params["mask"] = 1 if arguments["mask"] else 0

            response = requests.get(base_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Check for error in response
            if "error" in data:
                return {"status": "error", "error": data["error"]}

            # Extract and interpret scores
            scores = data.get("scores", [])

            # Find maximum delta score
            max_delta = 0.0
            for score_entry in scores:
                if isinstance(score_entry, dict):
                    for key in ["DS_AG", "DS_AL", "DS_DG", "DS_DL"]:
                        val = score_entry.get(key)
                        if val is not None and isinstance(val, (int, float)):
                            max_delta = max(max_delta, val)

            return {
                "status": "success",
                "data": {
                    "variant": variant,
                    "genome": f"GRCh{genome}",
                    "scores": scores,
                    "max_delta_score": max_delta,
                    "interpretation": self._interpret_score(max_delta),
                    "raw_response": data,
                },
                "source": "SpliceAI Lookup (Broad Institute)",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            error_text = ""
            try:
                error_text = e.response.text[:200]
            except Exception:
                pass
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {error_text}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _predict_splice_pangolin(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Pangolin splice predictions for a variant."""
        variant = arguments.get("variant")
        if not variant:
            return {"status": "error", "error": "Missing required parameter: variant"}

        genome = str(arguments.get("genome", "38"))
        if genome not in ["37", "38"]:
            return {"status": "error", "error": "genome must be '37' or '38'"}

        # Normalize and validate variant
        variant = self._normalize_variant(variant)
        error = self._validate_variant(variant)
        if error:
            return {"status": "error", "error": error}

        try:
            # Build URL
            base_url = PANGOLIN_URLS[genome]
            params = {"hg": genome, "variant": variant}

            # Optional parameters
            if "distance" in arguments:
                params["distance"] = arguments["distance"]
            if "mask" in arguments:
                params["mask"] = 1 if arguments["mask"] else 0

            response = requests.get(base_url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # Check for error in response
            if "error" in data:
                return {"status": "error", "error": data["error"]}

            return {
                "status": "success",
                "data": {
                    "variant": variant,
                    "genome": f"GRCh{genome}",
                    "scores": data.get("scores", []),
                    "raw_response": data,
                },
                "source": "Pangolin (via SpliceAI Lookup)",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            error_text = ""
            try:
                error_text = e.response.text[:200]
            except Exception:
                pass
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {error_text}",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_max_delta(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get just the maximum delta score and interpretation for a variant."""
        result = self._predict_splice(arguments)

        if result["status"] != "success":
            return result

        data = result["data"]
        return {
            "status": "success",
            "data": {
                "variant": data["variant"],
                "genome": data["genome"],
                "max_delta_score": data["max_delta_score"],
                "interpretation": data["interpretation"],
                "pathogenicity_threshold": "≥0.2 (low), ≥0.5 (moderate), ≥0.8 (high)",
            },
            "source": "SpliceAI Lookup (Broad Institute)",
        }
