# lipidmaps_gene_tool.py
"""
LIPID MAPS Proteome Database (LMPD) gene/protein REST tool for ToolUniverse.

The existing ``LipidMapsTool`` only exposes the LIPID MAPS *compound*
(structure) context. LIPID MAPS also serves a curated proteome database
(LMPD) that links lipid-metabolism **genes** and **proteins/enzymes** to the
resource. This tool wraps those gene and protein contexts, which were
previously unreachable as ToolUniverse tools.

It lets you resolve a lipid-related enzyme/gene from a gene symbol, NCBI Gene
ID, UniProt accession, RefSeq protein id, or the LIPID MAPS protein id
(``lmp_id``) and retrieve its annotation (gene name, synonyms, chromosome,
map location, NCBI summary, species, and protein cross-references / sequence).

REST shape (no key):
    GET /rest/{context}/{input_item}/{input_value}/{output_item}/json
e.g. https://www.lipidmaps.org/rest/protein/uniprot_id/P49327/all/json

API docs: https://lipidmaps.org/resources/rest
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

LIPIDMAPS_BASE_URL = "https://www.lipidmaps.org/rest"

# LIPID MAPS sits behind Cloudflare and 403s the default python-requests UA
# with a "Just a moment..." challenge page. A normal browser UA passes the
# JS-less challenge for plain REST endpoints.
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 ToolUniverse/LipidMapsGene"
    ),
    "Accept": "application/json,text/plain,*/*",
}

# Input items the LMPD gene route accepts.
_GENE_INPUT_ITEMS = {"gene_symbol", "gene_id", "gene_name", "lmp_id"}
# Input items the LMPD protein route accepts.
_PROTEIN_INPUT_ITEMS = {
    "uniprot_id",
    "gene_symbol",
    "gene_id",
    "gene_name",
    "lmp_id",
    "refseq_id",
    "mrna_id",
    "protein_entry",
}


@register_tool("LipidMapsGeneTool")
class LipidMapsGeneTool(BaseTool):
    """Query the LIPID MAPS Proteome Database (LMPD) gene/protein contexts.

    Configured per tool via ``fields.context`` ("gene" or "protein") and
    ``fields.input_item`` (the default lookup key). The lookup key may be
    overridden per call with the ``input_item`` argument.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.context = fields.get("context", "protein")
        self.input_item = fields.get("input_item", "uniprot_id")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an LMPD gene/protein lookup. Never raises."""
        try:
            input_value = arguments.get("input_value")
            if input_value is None or not str(input_value).strip():
                return {
                    "status": "error",
                    "error": "Parameter 'input_value' is required (e.g. a gene "
                    "symbol 'FASN', UniProt id 'P49327', or NCBI gene id '2194').",
                }
            input_value = str(input_value).strip()
            output_item = str(arguments.get("output_item") or "all").strip()

            # Allow the lookup key to be overridden per call, else use the
            # config default for this tool.
            input_item = str(arguments.get("input_item") or self.input_item).strip()

            allowed = (
                _GENE_INPUT_ITEMS if self.context == "gene" else _PROTEIN_INPUT_ITEMS
            )
            if input_item not in allowed:
                return {
                    "status": "error",
                    "error": f"Unsupported input_item '{input_item}' for the "
                    f"{self.context} context. Supported: " + ", ".join(sorted(allowed)),
                }

            sub_path = f"{self.context}/{input_item}/{input_value}/{output_item}/json"
            return self._make_request(sub_path, input_item, input_value)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"LIPID MAPS request timed out after {self.timeout}s.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to LIPID MAPS. Check network connectivity.",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"LIPID MAPS request failed: {str(e)}",
            }
        except Exception as e:  # noqa: BLE001 - run() must never raise
            return {
                "status": "error",
                "error": f"Unexpected error querying LIPID MAPS LMPD: {str(e)}",
            }

    def _make_request(
        self, sub_path: str, input_item: str, input_value: str
    ) -> Dict[str, Any]:
        """Fetch and normalize an LMPD response.

        LIPID MAPS returns:
          - a flat JSON object for a single match,
          - a {"Row1": {...}, "Row2": {...}} keyed dict for multiple matches,
          - an empty list ``[]`` (or empty body / "null") for no match.
        Always returns ``data`` as a list of records for a consistent shape.
        """
        url = f"{LIPIDMAPS_BASE_URL}/{sub_path}"
        response = requests.get(url, timeout=self.timeout, headers=_REQUEST_HEADERS)
        response.raise_for_status()

        raw_text = response.text.strip()
        if not raw_text or raw_text.lower() == "null" or raw_text in ('""', "{}", "[]"):
            return {
                "status": "success",
                "data": [],
                "metadata": {
                    "source": "LIPID MAPS Proteome Database (LMPD)",
                    "context": self.context,
                    "input_item": input_item,
                    "input_value": input_value,
                    "total_results": 0,
                },
            }

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "error",
                "error": "LIPID MAPS returned a non-JSON response "
                f"(first 200 chars: {raw_text[:200]}).",
            }

        records = self._to_record_list(payload)
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "LIPID MAPS Proteome Database (LMPD)",
                "context": self.context,
                "input_item": input_item,
                "input_value": input_value,
                "total_results": len(records),
            },
        }

    @staticmethod
    def _to_record_list(payload: Any) -> list:
        """Flatten a LIPID MAPS payload into a list of record dicts."""
        if isinstance(payload, list):
            return [r for r in payload if isinstance(r, dict)]
        if isinstance(payload, dict):
            row_keys = sorted(k for k in payload if k.startswith("Row"))
            if row_keys:
                return [payload[k] for k in row_keys if isinstance(payload[k], dict)]
            # Single flat record.
            return [payload]
        return []
