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
from .http_utils import upstream_reason_suffix

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

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        """SpliceAI sends the delta scores as strings: "DS_AL": "0.827".

        The previous maximum guarded on isinstance(val, (int, float)), which
        is False for every one of them, so the maximum stayed at its 0.0
        seed and every variant was reported as benign. For
        chr8-140300616-T-G -- this tool's own test example -- DS_AL is 0.827
        and the answer returned was "benign", where the tool's own
        thresholds make 0.827 high_pathogenicity.
        """
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return None

    DELTA_KEYS = {
        "DS_AG": ("acceptor_gain", "DP_AG"),
        "DS_AL": ("acceptor_loss", "DP_AL"),
        "DS_DG": ("donor_gain", "DP_DG"),
        "DS_DL": ("donor_loss", "DP_DL"),
    }

    def _max_delta(self, scores: Any) -> Dict[str, Any]:
        """The largest delta, which effect produced it, and where.

        A bare maximum does not say what changed, and 0.91 by acceptor loss
        is a different consequence from 0.91 by donor gain. Returns None for
        the score when nothing parseable was present, so that "no prediction"
        stops being reported as 0.0 and therefore benign.
        """
        best: Dict[str, Any] = {
            "max_delta_score": None,
            "max_delta_effect": None,
            "max_delta_key": None,
            "max_delta_offset": None,
            "max_delta_gene": None,
            "max_delta_transcript": None,
        }
        per_effect: Dict[str, Optional[float]] = {}
        for entry in scores or []:
            if not isinstance(entry, dict):
                continue
            for key, (effect, pos_key) in self.DELTA_KEYS.items():
                val = self._as_float(entry.get(key))
                if val is None:
                    continue
                prev = per_effect.get(effect)
                if prev is None or val > prev:
                    per_effect[effect] = val
                if best["max_delta_score"] is None or val > best["max_delta_score"]:
                    best = {
                        "max_delta_score": val,
                        "max_delta_effect": effect,
                        "max_delta_key": key,
                        "max_delta_offset": entry.get(pos_key),
                        "max_delta_gene": entry.get("g_name"),
                        "max_delta_transcript": entry.get("t_id"),
                    }
        best["delta_by_effect"] = per_effect
        return best

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

            summary = self._max_delta(scores)
            max_delta = summary["max_delta_score"]

            return {
                "status": "success",
                "data": {
                    "variant": variant,
                    "genome": f"GRCh{genome}",
                    "scores": scores,
                    "max_delta_score": max_delta,
                    "interpretation": self._interpret_score(max_delta),
                    # Which of the four splice effects produced that score,
                    # where it is relative to the variant, and in which gene
                    # and transcript.
                    "max_delta_effect": summary["max_delta_effect"],
                    "max_delta_key": summary["max_delta_key"],
                    "max_delta_offset": summary["max_delta_offset"],
                    "max_delta_gene": summary["max_delta_gene"],
                    "max_delta_transcript": summary["max_delta_transcript"],
                    "delta_by_effect": summary["delta_by_effect"],
                    "raw_response": data,
                },
                "source": "SpliceAI Lookup (Broad Institute)",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": f"Timeout after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}"
                f"{upstream_reason_suffix(e.response)}",
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
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}"
                f"{upstream_reason_suffix(e.response)}",
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
                # A triage answer of 0.83 does not say what changed. These
                # name the effect behind it and give all four, which is the
                # difference between "high" and "high, by acceptor loss two
                # bases away".
                "max_delta_effect": data["max_delta_effect"],
                "max_delta_offset": data["max_delta_offset"],
                "max_delta_gene": data["max_delta_gene"],
                "max_delta_transcript": data["max_delta_transcript"],
                "delta_by_effect": data["delta_by_effect"],
            },
            "source": "SpliceAI Lookup (Broad Institute)",
        }
