# ensembl_archive_tool.py
"""
Ensembl Archive API tool for ToolUniverse.

Provides access to the Ensembl Archive endpoint for tracking stable ID
versioning and history. Useful for checking whether an Ensembl ID is
current, what release it was introduced in, and converting between versions.

API: https://rest.ensembl.org/documentation/info/archive_id_get
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool


ENSEMBL_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_HEADERS = {"User-Agent": "ToolUniverse/1.0", "Accept": "application/json"}


class EnsemblArchiveTool(BaseTool):
    """
    Tool for Ensembl Archive API providing stable ID history tracking
    and batch ID version lookups.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 90)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_id_history")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Ensembl Archive API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"Ensembl Archive API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Ensembl REST API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 400:
                return {
                    "error": f"Invalid Ensembl ID format: {arguments.get('ensembl_id', '')}"
                }
            if code == 404:
                return {
                    "error": f"Ensembl ID not found: {arguments.get('ensembl_id', '')}"
                }
            return {"error": f"Ensembl REST API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying Ensembl Archive: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_id_history":
            return self._get_id_history(arguments)
        elif self.endpoint == "batch_lookup":
            return self._batch_lookup(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_id_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get version history for a single Ensembl stable ID."""
        ensembl_id = arguments.get("ensembl_id", "")
        if not ensembl_id:
            return {
                "error": "ensembl_id is required (e.g., 'ENSG00000141510' for TP53)"
            }

        url = f"{ENSEMBL_BASE_URL}/archive/id/{ensembl_id}"
        params = {"content-type": "application/json"}
        response = requests.get(
            url, params=params, headers=ENSEMBL_HEADERS, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        release = data.get("release")
        result = {
            "id": data.get("id"),
            "latest_version": data.get("latest"),
            "current_release": int(release) if release is not None else None,
            "assembly": data.get("assembly"),
            "is_current": bool(data.get("is_current")),
            "type": data.get("type"),
            "version": data.get("version"),
            "possible_replacement": data.get("possible_replacement"),
            "peptide": data.get("peptide"),
        }

        return {
            "data": result,
            "metadata": {
                "source": "Ensembl Archive",
                "ensembl_id": ensembl_id,
            },
        }

    def _batch_lookup(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Batch lookup version histories for multiple Ensembl IDs."""
        ids_str = arguments.get("ensembl_ids", "")
        if not ids_str:
            return {
                "error": "ensembl_ids is required (comma-separated, e.g., 'ENSG00000141510,ENSG00000012048')"
            }

        ids = [i.strip() for i in ids_str.split(",") if i.strip()]
        if len(ids) > 50:
            return {"error": "Maximum 50 IDs per batch request"}

        url = f"{ENSEMBL_BASE_URL}/archive/id"
        params = {"content-type": "application/json"}
        payload = {"id": ids}

        response = requests.post(
            url,
            json=payload,
            params=params,
            headers=ENSEMBL_HEADERS,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        if isinstance(data, list):
            for entry in data:
                entry_release = entry.get("release")
                results.append(
                    {
                        "id": entry.get("id"),
                        "latest_version": entry.get("latest"),
                        "current_release": int(entry_release)
                        if entry_release is not None
                        else None,
                        "assembly": entry.get("assembly"),
                        "is_current": bool(entry.get("is_current")),
                        "type": entry.get("type"),
                    }
                )

        return {
            "data": {
                "queried_ids": len(ids),
                "found": len(results),
                "entries": results,
            },
            "metadata": {
                "source": "Ensembl Archive",
                "batch_size": len(ids),
            },
        }
