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
            return {"error": f"Ensembl Sequence API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": "Sequence not found. Check your ID or region coordinates."
                }
            if code == 400:
                body = ""
                try:
                    body = e.response.json().get("error", "")
                except Exception:
                    pass
                return {"error": f"Bad request: {body}"}
            return {"error": f"Ensembl API HTTP error: {code}"}
        except Exception as e:
            return {
                "error": f"Unexpected error querying Ensembl Sequence API: {str(e)}"
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "region_sequence":
            return self._get_region_sequence(arguments)
        elif self.endpoint == "id_sequence":
            return self._get_id_sequence(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_region_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get DNA sequence for a genomic region."""
        species = arguments.get("species", "homo_sapiens")
        region = arguments.get("region", "")
        if not region:
            return {
                "error": "region parameter is required (e.g., '17:7668421..7668520:1' or '17:7668421-7668520')"
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
        return {
            "data": {
                "species": species,
                "region": region,
                "molecule": data.get("molecule", "dna"),
                "description": data.get("id", ""),
                "sequence_length": len(seq),
                "sequence": seq[:10000],
            },
            "metadata": {
                "source": "Ensembl REST API - Region Sequence",
                "species": species,
                "region": region,
                "truncated": len(seq) > 10000,
            },
        }

    def _get_id_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get sequence for an Ensembl ID (gene, transcript, or protein)."""
        ensembl_id = arguments.get("ensembl_id", "")
        if not ensembl_id:
            return {
                "error": "ensembl_id parameter is required (e.g., 'ENSP00000269305' for protein, 'ENST00000269305' for transcript)"
            }

        seq_type = arguments.get("type", "protein")

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

        return {
            "data": {
                "ensembl_id": data.get("id", ensembl_id),
                "molecule": molecule,
                "description": data.get("desc"),
                "sequence_length": len(seq),
                "sequence": seq[:10000],
            },
            "metadata": {
                "source": "Ensembl REST API - ID Sequence",
                "ensembl_id": ensembl_id,
                "type": seq_type,
                "truncated": len(seq) > 10000,
            },
        }
