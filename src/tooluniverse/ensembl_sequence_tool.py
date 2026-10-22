# ensembl_sequence_tool.py
"""
Ensembl Sequence API tool for ToolUniverse.

Provides access to Ensembl REST API sequence endpoints for retrieving
DNA and protein sequences by Ensembl ID or genomic coordinates.

API: https://rest.ensembl.org/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


ENSEMBL_REST_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


class EnsemblSequenceTool(BaseTool):
    """
    Tool for Ensembl sequence retrieval endpoints providing DNA and protein
    sequences for genes, transcripts, proteins, and genomic regions.

    Complements existing Ensembl tools by providing direct sequence access
    for specific region coordinates and protein/cDNA sequence retrieval.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "region_sequence")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl sequence API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Ensembl Sequence API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": "Sequence not found. Check your ID or region coordinates.",
                }
            if code == 400:
                body = ""
                try:
                    body = e.response.json().get("error", "")
                except Exception:
                    pass
                return {"status": "error", "error": f"Bad request: {body}"}
            return {"status": "error", "error": f"Ensembl API HTTP error: {code}"}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Ensembl Sequence API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "region_sequence":
            return self._get_region_sequence(arguments)
        elif self.endpoint == "id_sequence":
            return self._get_id_sequence(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _page_parameters(arguments: Dict[str, Any]):
        max_length = arguments.get("max_length", 10000)
        sequence_offset = arguments.get("sequence_offset", 0)
        if (
            isinstance(max_length, bool)
            or not isinstance(max_length, int)
            or max_length < 1
        ):
            return None, None, "max_length must be a positive integer"
        if (
            isinstance(sequence_offset, bool)
            or not isinstance(sequence_offset, int)
            or sequence_offset < 0
        ):
            return None, None, "sequence_offset must be a non-negative integer"
        return max_length, sequence_offset, None

    @staticmethod
    def _paginate_sequence(seq: str, max_length: int, sequence_offset: int):
        page = seq[sequence_offset : sequence_offset + max_length]
        has_more = sequence_offset + len(page) < len(seq)
        return page, {
            "sequence_length": len(seq),
            "sequence_returned_length": len(page),
            "sequence_offset": sequence_offset,
            "max_length": max_length,
            "has_more": has_more,
            "next_sequence_offset": (
                sequence_offset + len(page) if has_more else None
            ),
            "result_set_complete": sequence_offset == 0 and len(page) == len(seq),
        }

    def _get_region_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get DNA sequence for a genomic region."""
        max_length, sequence_offset, page_error = self._page_parameters(arguments)
        if page_error:
            return {"status": "error", "error": page_error}
        species = arguments.get("species", "homo_sapiens")
        region = arguments.get("region", "")
        if not region:
            return {
                "status": "error",
                "error": "region parameter is required (e.g., '17:7668421..7668520:1' or '17:7668421-7668520')",
            }

        # Normalize region format: accept both 17:start-end and 17:start..end
        region = region.replace("-", "..")

        # Add strand if not present
        if region.count(":") < 2 and ".." in region:
            region = region + ":1"

        url = f"{ENSEMBL_REST_BASE_URL}/sequence/region/{species}/{region}"
        params = {"content-type": "application/json"}
        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        seq = data.get("seq", "")
        sequence_page, pagination = self._paginate_sequence(
            seq, max_length, sequence_offset
        )
        return {
            "status": "success",
            "data": {
                "species": species,
                "region": region,
                "molecule": data.get("molecule", "dna"),
                "description": data.get("id", ""),
                **pagination,
                "sequence": sequence_page,
            },
            "metadata": {
                "source": "Ensembl REST API - Region Sequence",
                "species": species,
                "region": region,
                "truncated": not pagination["result_set_complete"],
                "has_more": pagination["has_more"],
                "next_sequence_offset": pagination["next_sequence_offset"],
            },
        }

    def _get_id_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get sequence for an Ensembl ID (gene, transcript, or protein)."""
        max_length, sequence_offset, page_error = self._page_parameters(arguments)
        if page_error:
            return {"status": "error", "error": page_error}
        ensembl_id = arguments.get("ensembl_id", "")
        if not ensembl_id:
            return {
                "status": "error",
                "error": "ensembl_id parameter is required (e.g., 'ENSP00000269305' for protein, 'ENST00000269305' for transcript)",
            }

        seq_type = arguments.get("type")
        if not seq_type:
            if ensembl_id.upper().startswith("ENSP"):
                seq_type = "protein"
            elif ensembl_id.upper().startswith("ENST"):
                seq_type = "cdna"
            else:
                seq_type = "genomic"

        url = f"{ENSEMBL_REST_BASE_URL}/sequence/id/{ensembl_id}"
        params = {"content-type": "application/json"}
        if seq_type:
            params["type"] = seq_type

        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        seq = data.get("seq", "")
        molecule = data.get("molecule", "")
        sequence_page, pagination = self._paginate_sequence(
            seq, max_length, sequence_offset
        )

        return {
            "status": "success",
            "data": {
                "ensembl_id": data.get("id", ensembl_id),
                "molecule": molecule,
                "description": data.get("desc"),
                **pagination,
                "sequence": sequence_page,
            },
            "metadata": {
                "source": "Ensembl REST API - ID Sequence",
                "ensembl_id": ensembl_id,
                "type": seq_type,
                "truncated": not pagination["result_set_complete"],
                "has_more": pagination["has_more"],
                "next_sequence_offset": pagination["next_sequence_offset"],
            },
        }
