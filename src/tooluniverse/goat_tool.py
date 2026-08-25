# goat_tool.py
"""
GoaT (Genomes on a Tree) tool for ToolUniverse.

GoaT indexes genome sequencing status across the major biodiversity
genomics initiatives (Earth BioGenome Project, Darwin Tree of Life, the
Vertebrate Genomes Project, and ERGA) against the full NCBI taxonomy, so a
single query answers "has this species been sequenced, and how well."

ToolUniverse has no equivalent today: taxonomy tools return classification,
not assembly status.

The API rejects the standard form-encoded query string requests.get()
produces (it encodes spaces as '+' and requires '%20', and flags unescaped
commas), so this tool builds request URLs with urlencode(quote_via=quote)
rather than passing a params dict.

API: https://goat.genomehubs.org/api/v2
No authentication required.
"""

from typing import Any, Dict, List
from urllib.parse import quote, urlencode

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

GOAT_SEARCH_URL = "https://goat.genomehubs.org/api/v2/search"

_DEFAULT_FIELDS = "assembly_level,assembly_span,genome_size,chromosome_number,ploidy"

_COMMON_NAME_CLASSES = ("common_name", "genbank common name")


def _common_name(taxon_names: List[Dict[str, Any]]) -> Any:
    for cls in _COMMON_NAME_CLASSES:
        for entry in taxon_names:
            if entry.get("class") == cls:
                return entry.get("name")
    return None


def _tolid_prefix(taxon_names: List[Dict[str, Any]]) -> Any:
    for entry in taxon_names:
        if entry.get("class") == "tolid prefix":
            return entry.get("name")
    return None


@register_tool("GoaTTool")
class GoaTTool(BaseTool):
    """
    Tool for looking up genome sequencing status via GoaT (Genomes on a
    Tree).

    Supports looking up one species or clade by name or NCBI taxon id,
    returning assembly level, genome size, chromosome number, and ploidy
    where recorded.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_species"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GoaT lookup."""
        try:
            if self.operation == "get_species":
                return self._get_species(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GoaT request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GoaT. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"GoaT returned HTTP {code}"}
        except ValueError:
            return {"status": "error", "error": "GoaT returned a non-JSON response"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying GoaT: {str(e)}"}

    def _get_species(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up sequencing status for a species, genus, or higher clade."""
        taxon = (arguments.get("taxon") or "").strip()
        if not taxon:
            return {
                "status": "error",
                "error": "taxon is required: a scientific name (e.g. "
                "'Panthera leo') or an NCBI taxon id (e.g. 9689).",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 10
        limit = min(limit, 50)

        include_descendants = bool(arguments.get("include_descendants"))
        if taxon.isdigit():
            term = f"tax_tree({taxon})" if include_descendants else f"tax_eq({taxon})"
        else:
            term = f"tax_name({taxon})"

        params = {
            "query": term,
            "result": "taxon",
            "taxonomy": "ncbi",
            "fields": _DEFAULT_FIELDS,
            "size": limit,
        }
        query_string = urlencode(params, quote_via=quote)
        response = requests.get(
            f"{GOAT_SEARCH_URL}?{query_string}", timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()

        if not (payload.get("status") or {}).get("success", True):
            return {
                "status": "error",
                "error": (payload.get("status") or {}).get(
                    "error", "GoaT rejected the query."
                ),
            }

        results = payload.get("results") or []
        if not results:
            return {
                "status": "error",
                "error": f"No GoaT record for '{taxon}'.",
            }

        rows = []
        for hit in results:
            result = hit.get("result") or {}
            fields = result.get("fields") or {}
            taxon_names = result.get("taxon_names") or []
            rows.append(
                {
                    "taxon_id": result.get("taxon_id"),
                    "scientific_name": result.get("scientific_name"),
                    "taxon_rank": result.get("taxon_rank"),
                    "common_name": _common_name(taxon_names),
                    "tolid_prefix": _tolid_prefix(taxon_names),
                    "assembly_level": (fields.get("assembly_level") or {}).get(
                        "value"
                    ),
                    "assembly_span_bp": (fields.get("assembly_span") or {}).get(
                        "value"
                    ),
                    "genome_size_bp": (fields.get("genome_size") or {}).get("value"),
                    "chromosome_number": (
                        fields.get("chromosome_number") or {}
                    ).get("value"),
                    "ploidy": (fields.get("ploidy") or {}).get("value"),
                }
            )

        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "taxon": taxon,
                "total_matching": (payload.get("status") or {}).get("hits"),
                "returned": len(rows),
                "note": "assembly_level is null if no genome assembly is "
                "recorded yet for this taxon.",
                "source": "GoaT (Genomes on a Tree)",
            },
        }
