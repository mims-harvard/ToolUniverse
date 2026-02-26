"""
Addgene Developers API Tool

Provides programmatic access to Addgene's plasmid catalog via the official
Addgene Developers API (https://developers.addgene.org/).

Supports:
- Searching plasmids by name, gene, species, vector type, purpose, etc.
- Retrieving detailed plasmid information (cloning, inserts, resistance, growth)
- Browsing depositors (PIs) via plasmid catalog queries

API Base: https://api.developers.addgene.org
Authentication: Token-based via ADDGENE_API_KEY environment variable.
Register at https://developers.addgene.org/ to obtain a free token.
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ADDGENE_API_URL = "https://api.developers.addgene.org"


@register_tool("AddgeneTool")
class AddgeneTool(BaseTool):
    """
    Tool for querying the Addgene plasmid repository.

    Addgene is a nonprofit global plasmid repository that archives and
    distributes plasmids for the scientific community. This tool provides
    access to:
    - Plasmid search (by name, gene, species, vector type, purpose)
    - Plasmid detail retrieval (cloning info, inserts, resistance markers)
    - Depositor/PI search

    Requires API token via ADDGENE_API_KEY environment variable.
    Register at https://developers.addgene.org/ for access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.api_key = os.environ.get("ADDGENE_API_KEY", "")

    def _get_headers(self):
        """Get request headers with auth token."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Token " + self.api_key
        return headers

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        if not self.api_key:
            return {
                "status": "error",
                "error": (
                    "Addgene API key required. Set ADDGENE_API_KEY environment variable. "
                    "Register at https://developers.addgene.org/ for access."
                ),
            }

        handlers = {
            "search_plasmids": self._search_plasmids,
            "get_plasmid": self._get_plasmid,
            "search_depositors": self._search_depositors,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, ", ".join(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Addgene API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Addgene API"}
        except Exception as e:
            return {"status": "error", "error": "Operation failed: {}".format(str(e))}

    def _search_plasmids(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search Addgene plasmid catalog.

        Supports filtering by name, genes, species, vector_types, purpose,
        experimental_use, expression, and more.
        """
        query = arguments.get("query")
        organism = arguments.get("organism")
        vector_type = arguments.get("vector_type")
        limit = min(int(arguments.get("limit", 10)), 100)

        params = {"page_size": limit}

        if query:
            params["name"] = query
        if organism:
            params["species"] = organism
        if vector_type:
            params["vector_types"] = vector_type

        response = requests.get(
            ADDGENE_API_URL + "/catalog/plasmid/",
            params=params,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        if response.status_code == 401:
            return {
                "status": "error",
                "error": "Authentication failed. Check your ADDGENE_API_KEY.",
            }

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        return {
            "status": "success",
            "data": {
                "plasmids": results,
                "total_count": data.get("count", len(results)),
                "next_page": data.get("next"),
            },
            "metadata": {
                "source": "Addgene",
                "query": query,
                "organism": organism,
                "vector_type": vector_type,
            },
        }

    def _get_plasmid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information about a specific plasmid.

        Returns full plasmid record including cloning info, inserts,
        resistance markers, growth conditions, article, depositor comments.
        """
        plasmid_id = arguments.get("plasmid_id")
        if not plasmid_id:
            return {
                "status": "error",
                "error": "Missing required parameter: plasmid_id",
            }

        plasmid_id = str(plasmid_id).strip()

        response = requests.get(
            "{}/catalog/plasmid/{}/".format(ADDGENE_API_URL, plasmid_id),
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        if response.status_code == 401:
            return {
                "status": "error",
                "error": "Authentication failed. Check your ADDGENE_API_KEY.",
            }
        if response.status_code == 404:
            return {
                "status": "error",
                "error": "Plasmid ID {} not found in Addgene".format(plasmid_id),
            }

        response.raise_for_status()
        plasmid = response.json()

        return {
            "status": "success",
            "data": plasmid,
            "metadata": {
                "source": "Addgene",
                "plasmid_id": plasmid_id,
                "url": "https://www.addgene.org/{}/".format(plasmid_id),
            },
        }

    def _search_depositors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for depositors (PIs) by querying plasmids and extracting
        unique depositor information.

        The Addgene API does not have a dedicated depositor search endpoint,
        so this searches plasmids filtered by PI name or institution, then
        extracts and deduplicates depositor info from results.
        """
        name = arguments.get("name")
        institution = arguments.get("institution")

        if not name and not institution:
            return {
                "status": "error",
                "error": "At least one of 'name' or 'institution' is required.",
            }

        params = {"page_size": 50}
        if name:
            params["pis"] = name
        if institution:
            # Institution is not a direct filter in the API;
            # we search by article_authors which may contain institution info
            params["article_authors"] = institution

        response = requests.get(
            ADDGENE_API_URL + "/catalog/plasmid/",
            params=params,
            headers=self._get_headers(),
            timeout=self.timeout,
        )

        if response.status_code == 401:
            return {
                "status": "error",
                "error": "Authentication failed. Check your ADDGENE_API_KEY.",
            }

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        # Extract unique depositors from plasmid results
        depositors = {}
        for plasmid in results:
            depositor_list = plasmid.get("depositor", [])
            for dep in depositor_list:
                dep_str = str(dep)
                if dep_str not in depositors:
                    depositors[dep_str] = {
                        "name": dep_str,
                        "plasmid_count": 0,
                        "example_plasmids": [],
                    }
                depositors[dep_str]["plasmid_count"] += 1
                if len(depositors[dep_str]["example_plasmids"]) < 3:
                    depositors[dep_str]["example_plasmids"].append(
                        {"id": plasmid.get("id"), "name": plasmid.get("name")}
                    )

        depositor_list = sorted(
            depositors.values(), key=lambda x: x["plasmid_count"], reverse=True
        )

        return {
            "status": "success",
            "data": {
                "depositors": depositor_list,
                "total_depositors": len(depositor_list),
                "total_plasmids_searched": data.get("count", len(results)),
            },
            "metadata": {
                "source": "Addgene",
                "name_query": name,
                "institution_query": institution,
            },
        }
