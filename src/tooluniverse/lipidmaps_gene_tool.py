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
from urllib.parse import quote

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

_GENE_OUTPUT_ITEMS = {
    "all",
    "lmp_id",
    "gene_id",
    "gene_name",
    "gene_symbol",
    "gene_synonyms",
    "alt_names",
    "chromosome",
    "map_location",
    "summary",
    "taxid",
    "species",
    "species_long",
}
_PROTEIN_OUTPUT_ITEMS = {
    "all",
    "lmp_id",
    "gene_id",
    "gene_name",
    "gene_symbol",
    "taxid",
    "species",
    "species_long",
    "mrna_id",
    "refseq_id",
    "protein_gi",
    "uniprot_id",
    "protein_entry",
    "protein_name",
    "seqlength",
    "seq",
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
            if not isinstance(input_value, str) or not input_value.strip():
                return {
                    "status": "error",
                    "error": "Parameter 'input_value' must be a non-empty string (e.g. a gene "
                    "symbol 'FASN', UniProt id 'P49327', or NCBI gene id '2194').",
                }
            input_value = input_value.strip()
            output_item = arguments.get("output_item", "all")
            if not isinstance(output_item, str) or not output_item.strip():
                return {
                    "status": "error",
                    "error": "Parameter 'output_item' must be a non-empty string.",
                }
            output_item = output_item.strip()

            # Allow the lookup key to be overridden per call, else use the
            # config default for this tool.
            input_item = arguments.get("input_item", self.input_item)
            if not isinstance(input_item, str) or not input_item.strip():
                return {
                    "status": "error",
                    "error": "Parameter 'input_item' must be a non-empty string.",
                }
            input_item = input_item.strip()

            if self.context not in ("gene", "protein"):
                return {
                    "status": "error",
                    "error": f"Unsupported LIPID MAPS context '{self.context}'.",
                }

            allowed = (
                _GENE_INPUT_ITEMS if self.context == "gene" else _PROTEIN_INPUT_ITEMS
            )
            if input_item not in allowed:
                return {
                    "status": "error",
                    "error": f"Unsupported input_item '{input_item}' for the "
                    f"{self.context} context. Supported: " + ", ".join(sorted(allowed)),
                }

            allowed_outputs = (
                _GENE_OUTPUT_ITEMS if self.context == "gene" else _PROTEIN_OUTPUT_ITEMS
            )
            if output_item not in allowed_outputs:
                return {
                    "status": "error",
                    "error": f"Unsupported output_item '{output_item}' for the "
                    f"{self.context} context. Supported: "
                    + ", ".join(sorted(allowed_outputs)),
                }

            sub_path = "/".join(
                quote(segment, safe="")
                for segment in (
                    self.context,
                    input_item,
                    input_value,
                    output_item,
                    "json",
                )
            )
            return self._make_request(sub_path, input_item, input_value, output_item)
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
        self, sub_path: str, input_item: str, input_value: str, output_item: str
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
                    "result_set_complete": True,
                    "output_item": output_item,
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

        try:
            records = self._to_record_list(payload)
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "LIPID MAPS Proteome Database (LMPD)",
                "context": self.context,
                "input_item": input_item,
                "input_value": input_value,
                "total_results": len(records),
                "result_set_complete": True,
                "output_item": output_item,
                "field_scope_complete": output_item == "all",
            },
        }

    @staticmethod
    def _to_record_list(payload: Any) -> list:
        """Flatten a LIPID MAPS payload into a list of record dicts."""
        if isinstance(payload, list):
            if any(not isinstance(record, dict) for record in payload):
                raise ValueError("LIPID MAPS returned a malformed record list")
            return payload
        if isinstance(payload, dict):
            row_keys = [key for key in payload if key.startswith("Row")]
            if row_keys:
                if len(row_keys) != len(payload):
                    raise ValueError(
                        "LIPID MAPS mixed row records with unexpected response fields"
                    )
                if any(
                    not key[3:].isdigit() or not isinstance(payload[key], dict)
                    for key in row_keys
                ):
                    raise ValueError(
                        "LIPID MAPS returned a malformed keyed row response"
                    )
                row_keys.sort(key=lambda key: int(key[3:]))
                return [payload[key] for key in row_keys]
            # Single flat record.
            return [payload]
        raise ValueError("LIPID MAPS returned an unexpected JSON response shape")
