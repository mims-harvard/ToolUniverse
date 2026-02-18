# interpro_ext_tool.py
"""
InterPro Extended API tool for ToolUniverse.

Provides access to InterPro API endpoints for querying proteins by domain,
complementing existing domain-centric search tools.

API: https://www.ebi.ac.uk/interpro/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool


INTERPRO_API_BASE_URL = "https://www.ebi.ac.uk/interpro/api"


class InterProExtTool(BaseTool):
    """
    Extended InterPro API tool for protein-by-domain queries.

    Complements existing InterPro tools (get_protein_domains, search_domains,
    get_domain_details) by providing reverse lookup: find all proteins
    containing a specific domain.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "proteins_by_domain")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the InterPro API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"InterPro API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to InterPro API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"Domain not found in InterPro: {arguments.get('domain_id', '')}"
                }
            return {"error": f"InterPro API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying InterPro API: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "proteins_by_domain":
            return self._get_proteins_by_domain(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _get_proteins_by_domain(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteins containing a specific InterPro domain."""
        domain_id = arguments.get("domain_id", "")
        if not domain_id:
            return {
                "error": "domain_id parameter is required (InterPro accession, e.g., IPR011615)"
            }

        page_size = min(int(arguments.get("page_size", 20)), 50)
        reviewed_only = arguments.get("reviewed_only", False)

        # Build URL for protein search by domain
        db = "reviewed" if reviewed_only else "uniprot"
        url = f"{INTERPRO_API_BASE_URL}/protein/{db}/entry/interpro/{domain_id}"
        params = {"page_size": page_size}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        total_count = data.get("count", 0)
        results = data.get("results", [])

        proteins = []
        for r in results:
            meta = r.get("metadata", {})
            proteins.append(
                {
                    "accession": meta.get("accession"),
                    "name": meta.get("name"),
                    "source_database": meta.get("source_database"),
                    "length": meta.get("length"),
                    "source_organism": meta.get("source_organism", {}).get(
                        "scientificName"
                    ),
                    "tax_id": meta.get("source_organism", {}).get("taxId"),
                }
            )

        return {
            "data": {
                "domain_id": domain_id,
                "total_proteins": total_count,
                "proteins": proteins,
                "page_size": page_size,
                "reviewed_only": reviewed_only,
            },
            "metadata": {
                "source": "InterPro API - Proteins by Domain",
                "domain_id": domain_id,
            },
        }
