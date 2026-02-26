"""
GenCC (Gene Curation Coalition) tool for ToolUniverse.

GenCC aggregates gene-disease validity classifications from multiple expert
curators (ClinGen, Ambry Genetics, Genomics England PanelApp, OMIM, Orphanet,
etc.). It provides standardized gene-disease validity evidence levels:
Definitive, Strong, Moderate, Limited, Disputed, Refuted, Animal Model Only,
and No Known Disease Relationship.

Since GenCC has no REST API, this tool downloads and parses the TSV bulk
export from https://search.thegencc.org/download/action/submissions-export-tsv

API Documentation:
- GenCC website: https://thegencc.org
- Data downloads: https://search.thegencc.org/download

Data is cached for 1 hour to avoid repeated downloads.
"""

import csv
import io
import time
import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

GENCC_TSV_URL = "https://search.thegencc.org/download/action/submissions-export-tsv"

# Cache for GenCC data (module-level)
_gencc_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 3600,  # 1 hour cache
}

# Classification hierarchy from most to least confident
CLASSIFICATION_ORDER = {
    "Definitive": 1,
    "Strong": 2,
    "Moderate": 3,
    "Limited": 4,
    "Animal Model Only": 5,
    "Disputed": 6,
    "Refuted": 7,
    "No Known Disease Relationship": 8,
}


def _download_gencc_data() -> List[Dict[str, str]]:
    """Download and parse GenCC TSV data with caching."""
    now = time.time()
    if (
        _gencc_cache["data"] is not None
        and (now - _gencc_cache["timestamp"]) < _gencc_cache["ttl"]
    ):
        return _gencc_cache["data"]

    response = requests.get(
        GENCC_TSV_URL,
        timeout=120,
        headers={"User-Agent": "ToolUniverse/GenCC"},
    )
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text), delimiter="\t")
    records = list(reader)

    _gencc_cache["data"] = records
    _gencc_cache["timestamp"] = now
    return records


@register_tool("GenCCTool")
class GenCCTool(BaseTool):
    """
    Tool for querying GenCC gene-disease validity classifications.

    GenCC (Gene Curation Coalition) aggregates gene-disease validity
    assessments from multiple expert curators worldwide. Classifications
    range from Definitive to Refuted, following ClinGen gene-disease
    validity framework standards.

    No authentication required. Data is downloaded from GenCC bulk export.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 120)
        self.parameter = tool_config.get("parameter", {})

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute GenCC operation."""
        operation = arguments.get("operation", "")

        if operation == "search_gene":
            return self._search_gene(arguments)
        elif operation == "search_disease":
            return self._search_disease(arguments)
        elif operation == "get_classifications":
            return self._get_classifications(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_gene, search_disease, get_classifications",
            }

    def _search_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene-disease validity classifications for a gene.

        Args:
            arguments: Dict containing:
                - gene_symbol: HGNC gene symbol (e.g., BRCA2, TP53)
                - classification: Optional filter by classification level
        """
        gene_symbol = arguments.get("gene_symbol", "").strip().upper()
        if not gene_symbol:
            return {
                "status": "error",
                "error": "Missing required parameter: gene_symbol",
            }

        classification_filter = arguments.get("classification", "")

        try:
            records = _download_gencc_data()

            # Filter by gene symbol
            matches = [
                r for r in records if r.get("gene_symbol", "").upper() == gene_symbol
            ]

            # Optional classification filter
            if classification_filter:
                matches = [
                    r
                    for r in matches
                    if classification_filter.lower()
                    in r.get("classification_title", "").lower()
                ]

            # Build structured results
            results = []
            seen = set()
            for r in matches:
                key = (
                    r.get("disease_curie", ""),
                    r.get("submitter_title", ""),
                    r.get("classification_title", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "gene_symbol": r.get("gene_symbol", ""),
                        "gene_curie": r.get("gene_curie", ""),
                        "disease_title": r.get("disease_title", ""),
                        "disease_curie": r.get("disease_curie", ""),
                        "classification": r.get("classification_title", ""),
                        "mode_of_inheritance": r.get("moi_title", ""),
                        "submitter": r.get("submitter_title", ""),
                        "submitted_date": r.get("submitted_as_date", ""),
                    }
                )

            # Sort by classification strength
            results.sort(
                key=lambda x: CLASSIFICATION_ORDER.get(x["classification"], 99)
            )

            return {
                "status": "success",
                "data": {
                    "gene_symbol": gene_symbol,
                    "submissions": results,
                    "submission_count": len(results),
                    "unique_diseases": len(set(r["disease_curie"] for r in results)),
                },
                "metadata": {
                    "source": "GenCC (Gene Curation Coalition)",
                    "gene_symbol": gene_symbol,
                },
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to download GenCC data: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find genes with validity evidence for a disease.

        Args:
            arguments: Dict containing:
                - disease: Disease name or MONDO/OMIM ID to search
                - classification: Optional filter by classification level
        """
        disease = arguments.get("disease", "").strip()
        if not disease:
            return {"status": "error", "error": "Missing required parameter: disease"}

        classification_filter = arguments.get("classification", "")

        try:
            records = _download_gencc_data()

            # Search by disease name (case-insensitive contains) or disease curie
            disease_lower = disease.lower()
            matches = [
                r
                for r in records
                if disease_lower in r.get("disease_title", "").lower()
                or disease_lower in r.get("disease_curie", "").lower()
                or disease_lower in r.get("disease_original_curie", "").lower()
            ]

            # Optional classification filter
            if classification_filter:
                matches = [
                    r
                    for r in matches
                    if classification_filter.lower()
                    in r.get("classification_title", "").lower()
                ]

            # Deduplicate and structure results
            results = []
            seen = set()
            for r in matches:
                key = (
                    r.get("gene_symbol", ""),
                    r.get("disease_curie", ""),
                    r.get("submitter_title", ""),
                    r.get("classification_title", ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {
                        "gene_symbol": r.get("gene_symbol", ""),
                        "gene_curie": r.get("gene_curie", ""),
                        "disease_title": r.get("disease_title", ""),
                        "disease_curie": r.get("disease_curie", ""),
                        "classification": r.get("classification_title", ""),
                        "mode_of_inheritance": r.get("moi_title", ""),
                        "submitter": r.get("submitter_title", ""),
                        "submitted_date": r.get("submitted_as_date", ""),
                    }
                )

            # Sort by classification strength
            results.sort(
                key=lambda x: CLASSIFICATION_ORDER.get(x["classification"], 99)
            )

            return {
                "status": "success",
                "data": {
                    "disease": disease,
                    "submissions": results,
                    "submission_count": len(results),
                    "unique_genes": len(set(r["gene_symbol"] for r in results)),
                },
                "metadata": {
                    "source": "GenCC (Gene Curation Coalition)",
                    "disease": disease,
                },
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to download GenCC data: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_classifications(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of all gene-disease validity classification levels.

        Returns classification levels with counts and descriptions.
        Optionally filter by submitter organization.

        Args:
            arguments: Dict containing:
                - submitter: Optional filter by submitting organization name
        """
        submitter_filter = arguments.get("submitter", "")

        try:
            records = _download_gencc_data()

            if submitter_filter:
                records = [
                    r
                    for r in records
                    if submitter_filter.lower() in r.get("submitter_title", "").lower()
                ]

            # Count classifications
            classification_counts = {}
            submitter_counts = {}
            for r in records:
                cls = r.get("classification_title", "Unknown")
                classification_counts[cls] = classification_counts.get(cls, 0) + 1
                sub = r.get("submitter_title", "Unknown")
                submitter_counts[sub] = submitter_counts.get(sub, 0) + 1

            # Build ordered classification summary
            classifications = []
            for cls_name in sorted(
                classification_counts.keys(),
                key=lambda x: CLASSIFICATION_ORDER.get(x, 99),
            ):
                classifications.append(
                    {
                        "classification": cls_name,
                        "count": classification_counts[cls_name],
                        "rank": CLASSIFICATION_ORDER.get(cls_name, 99),
                    }
                )

            # Top submitters
            top_submitters = sorted(submitter_counts.items(), key=lambda x: -x[1])[:20]

            return {
                "status": "success",
                "data": {
                    "classifications": classifications,
                    "total_submissions": len(records),
                    "unique_genes": len(set(r.get("gene_symbol", "") for r in records)),
                    "unique_diseases": len(
                        set(r.get("disease_curie", "") for r in records)
                    ),
                    "top_submitters": [
                        {"name": s[0], "count": s[1]} for s in top_submitters
                    ],
                },
                "metadata": {
                    "source": "GenCC (Gene Curation Coalition)",
                    "note": "Classifications follow ClinGen gene-disease validity framework",
                },
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"Failed to download GenCC data: {str(e)}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
