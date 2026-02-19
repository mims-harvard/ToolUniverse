# cadd_tool.py
"""
CADD (Combined Annotation Dependent Depletion) API tool for ToolUniverse.

CADD scores the deleteriousness of single nucleotide variants, multi-nucleotide
substitutions, and insertion/deletion variants in the human genome.

PHRED-scaled scores interpretation:
- PHRED >= 10: Top 10% most deleterious
- PHRED >= 20: Top 1% most deleterious
- PHRED >= 30: Top 0.1% most deleterious

API Documentation: https://cadd.gs.washington.edu/api
Note: API is experimental, not for high-throughput use (thousands of variants).
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for CADD API (BIH mirror - working instance)
CADD_BASE_URL = "https://cadd.bihealth.org/api/v1.0"


@register_tool("CADDTool")
class CADDTool(BaseTool):
    """
    Tool for querying CADD API for variant deleteriousness scores.

    CADD integrates diverse annotations into a single metric (PHRED score)
    by contrasting variants that survived natural selection with simulated mutations.

    PHRED score interpretation:
    - >= 10: Top 10% most deleterious (likely damaging)
    - >= 20: Top 1% most deleterious (damaging)
    - >= 30: Top 0.1% most deleterious (highly damaging)
    - Common pathogenic threshold: 15-20

    Supported genome builds: GRCh37, GRCh38
    Current version: v1.7

    No authentication required. API is experimental.
    """

    # Default CADD version
    DEFAULT_VERSION = "GRCh38-v1.7"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_variant_score"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CADD API call."""
        operation = self.operation

        if operation == "get_variant_score":
            return self._get_variant_score(arguments)
        elif operation == "get_position_scores":
            return self._get_position_scores(arguments)
        elif operation == "get_range_scores":
            return self._get_range_scores(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _interpret_phred(self, phred) -> str:
        """Interpret PHRED score for user-friendly output."""
        if phred is None:
            return "unknown"
        try:
            phred = float(phred)
        except (ValueError, TypeError):
            return "unknown"
        if phred >= 30:
            return "highly_deleterious (top 0.1%)"
        elif phred >= 20:
            return "deleterious (top 1%)"
        elif phred >= 15:
            return "likely_deleterious (commonly used pathogenic threshold)"
        elif phred >= 10:
            return "possibly_deleterious (top 10%)"
        else:
            return "likely_benign"

    def _get_variant_score(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CADD score for a specific SNV.

        Query format: chrom:pos_ref_alt (e.g., 7:140453136_A_T for BRAF V600E)
        """
        chrom = arguments.get("chrom") or arguments.get("chromosome")
        pos = arguments.get("pos") or arguments.get("position")
        ref = arguments.get("ref") or arguments.get("reference")
        alt = arguments.get("alt") or arguments.get("alternate")
        version = arguments.get("version", self.DEFAULT_VERSION)
        include_annotations = arguments.get("include_annotations", False)

        # Validate required parameters
        if not chrom:
            return {
                "status": "error",
                "error": "chrom/chromosome parameter is required",
            }
        if not pos:
            return {"status": "error", "error": "pos/position parameter is required"}
        if not ref:
            return {"status": "error", "error": "ref/reference parameter is required"}
        if not alt:
            return {"status": "error", "error": "alt/alternate parameter is required"}

        # Clean chromosome
        chrom = str(chrom).replace("chr", "")

        try:
            # Build URL for specific variant
            version_suffix = "_inclAnno" if include_annotations else ""
            url = f"{CADD_BASE_URL}/{version}{version_suffix}/{chrom}:{pos}_{ref}_{alt}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No CADD score found for {chrom}:{pos} {ref}>{alt}",
                }

            response.raise_for_status()
            data = response.json()

            # Parse response - CADD returns array of results
            if isinstance(data, list) and len(data) > 0:
                result = data[0]
                phred = result.get("PHRED")
                raw_score = result.get("RawScore")

                # Convert string scores to float
                try:
                    phred = float(phred) if phred is not None else None
                except (ValueError, TypeError):
                    phred = None
                try:
                    raw_score = float(raw_score) if raw_score is not None else None
                except (ValueError, TypeError):
                    raw_score = None

                return {
                    "status": "success",
                    "data": {
                        "chrom": chrom,
                        "pos": pos,
                        "ref": ref,
                        "alt": alt,
                        "phred_score": phred,
                        "raw_score": raw_score,
                        "interpretation": self._interpret_phred(phred)
                        if phred
                        else None,
                        "version": version,
                        "annotations": result if include_annotations else None,
                        "thresholds": {
                            "highly_deleterious": "PHRED >= 30 (top 0.1%)",
                            "deleterious": "PHRED >= 20 (top 1%)",
                            "likely_pathogenic": "PHRED >= 15 (common threshold)",
                            "possibly_deleterious": "PHRED >= 10 (top 10%)",
                        },
                    },
                }
            else:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No CADD score found for {chrom}:{pos} {ref}>{alt}",
                    "raw_response": data,
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CADD API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CADD API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_position_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CADD scores for all possible SNVs at a genomic position.

        Returns scores for A, C, G, T substitutions at the given position.
        """
        chrom = arguments.get("chrom") or arguments.get("chromosome")
        pos = arguments.get("pos") or arguments.get("position")
        version = arguments.get("version", self.DEFAULT_VERSION)

        if not chrom:
            return {
                "status": "error",
                "error": "chrom/chromosome parameter is required",
            }
        if not pos:
            return {"status": "error", "error": "pos/position parameter is required"}

        chrom = str(chrom).replace("chr", "")

        try:
            url = f"{CADD_BASE_URL}/{version}/{chrom}:{pos}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No CADD scores found for {chrom}:{pos}",
                }

            response.raise_for_status()
            data = response.json()

            # Parse all variants at this position
            variants = []
            if isinstance(data, list):
                for item in data:
                    phred = item.get("PHRED")
                    variants.append(
                        {
                            "ref": item.get("Ref"),
                            "alt": item.get("Alt"),
                            "phred_score": phred,
                            "raw_score": item.get("RawScore"),
                            "interpretation": self._interpret_phred(phred)
                            if phred
                            else None,
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "chrom": chrom,
                    "pos": pos,
                    "variants": variants,
                    "version": version,
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CADD API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CADD API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_range_scores(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CADD scores for a genomic range (max 100bp).

        Returns all pre-computed scores in the specified range.
        """
        chrom = arguments.get("chrom") or arguments.get("chromosome")
        start = arguments.get("start")
        end = arguments.get("end")
        version = arguments.get("version", self.DEFAULT_VERSION)

        if not chrom:
            return {
                "status": "error",
                "error": "chrom/chromosome parameter is required",
            }
        if not start:
            return {"status": "error", "error": "start parameter is required"}
        if not end:
            return {"status": "error", "error": "end parameter is required"}

        chrom = str(chrom).replace("chr", "")

        try:
            start = int(start)
            end = int(end)
        except (ValueError, TypeError):
            return {"status": "error", "error": "start and end must be integers"}

        # Validate range (API limit is 100bp)
        if end - start > 100:
            return {
                "status": "error",
                "error": f"Range too large: {end - start}bp. CADD API allows max 100bp range.",
            }

        try:
            url = f"{CADD_BASE_URL}/{version}/{chrom}:{start}-{end}"

            response = requests.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No CADD scores found for {chrom}:{start}-{end}",
                }

            response.raise_for_status()
            data = response.json()

            # Parse all variants in range
            # CADD range API returns list of lists with header as first row:
            # [['Chrom', 'Pos', 'Ref', 'Alt', 'RawScore', 'PHRED'], [data...], ...]
            variants = []
            if isinstance(data, list) and len(data) > 1:
                # First row is header
                headers = data[0] if isinstance(data[0], list) else None
                if headers:
                    # Create mapping from header names to indices
                    header_map = {h: i for i, h in enumerate(headers)}

                    for row in data[1:]:  # Skip header row
                        if isinstance(row, list) and len(row) >= len(headers):
                            phred = (
                                row[header_map.get("PHRED", -1)]
                                if "PHRED" in header_map
                                else None
                            )
                            if phred:
                                try:
                                    phred = float(phred)
                                except (ValueError, TypeError):
                                    phred = None
                            variants.append(
                                {
                                    "pos": row[header_map.get("Pos", 1)]
                                    if "Pos" in header_map
                                    else None,
                                    "ref": row[header_map.get("Ref", 2)]
                                    if "Ref" in header_map
                                    else None,
                                    "alt": row[header_map.get("Alt", 3)]
                                    if "Alt" in header_map
                                    else None,
                                    "phred_score": phred,
                                    "raw_score": row[header_map.get("RawScore", 4)]
                                    if "RawScore" in header_map
                                    else None,
                                    "interpretation": self._interpret_phred(phred)
                                    if phred
                                    else None,
                                }
                            )
                else:
                    # Fallback: try to parse as dict (old format)
                    for item in data:
                        if isinstance(item, dict):
                            phred = item.get("PHRED")
                            variants.append(
                                {
                                    "pos": item.get("Pos"),
                                    "ref": item.get("Ref"),
                                    "alt": item.get("Alt"),
                                    "phred_score": phred,
                                    "raw_score": item.get("RawScore"),
                                    "interpretation": self._interpret_phred(phred)
                                    if phred
                                    else None,
                                }
                            )

            return {
                "status": "success",
                "data": {
                    "chrom": chrom,
                    "start": start,
                    "end": end,
                    "variants": variants,
                    "count": len(variants),
                    "version": version,
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"CADD API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"CADD API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
