"""
OMIM (Online Mendelian Inheritance in Man) API tool for ToolUniverse.

OMIM is a comprehensive database of human genes and genetic disorders,
with particular emphasis on the molecular relationships between genetic
variation and phenotypic expression.

API Documentation: https://omim.org/help/api
Requires API key: https://omim.org/api
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for OMIM API
OMIM_API_URL = "https://api.omim.org/api"


@register_tool("OMIMTool")
class OMIMTool(BaseTool):
    """
    Tool for querying OMIM (Online Mendelian Inheritance in Man).

    OMIM provides:
    - Mendelian disease information
    - Gene-disease relationships
    - Clinical synopses
    - Inheritance patterns

    Requires API key via OMIM_API_KEY environment variable.
    Register at https://omim.org/api for free academic access.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})
        self.api_key = os.environ.get("OMIM_API_KEY", "")

    def _get_params(self, extra_params: Dict = None) -> Dict[str, Any]:
        """Get base parameters with API key."""
        params = {"apiKey": self.api_key, "format": "json"}
        if extra_params:
            params.update(extra_params)
        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute OMIM API call based on operation type."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "OMIM API key required. Set OMIM_API_KEY environment variable. Register at https://omim.org/api",
            }

        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "search":
            return self._search(arguments)
        elif operation == "get_entry":
            return self._get_entry(arguments)
        elif operation == "get_gene_map":
            return self._get_gene_map(arguments)
        elif operation == "get_clinical_synopsis":
            return self._get_clinical_synopsis(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search, get_entry, get_gene_map, get_clinical_synopsis",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search OMIM entries.

        Args:
            arguments: Dict containing:
                - query: Search terms (gene name, disease name, phenotype)
                - limit: Maximum results (default 10, max 20)
                - start: Offset for pagination (default 0)
        """
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        limit = min(arguments.get("limit", 10), 20)
        start = arguments.get("start", 0)

        params = self._get_params(
            {
                "search": query,
                "limit": limit,
                "start": start,
                "include": "all",
            }
        )

        try:
            response = requests.get(
                f"{OMIM_API_URL}/entry/search",
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/OMIM"},
            )
            response.raise_for_status()
            data = response.json()

            # Parse OMIM response
            omim_data = data.get("omim", {})
            search_response = omim_data.get("searchResponse", {})

            return {
                "status": "success",
                "data": {
                    "total_results": search_response.get("totalResults", 0),
                    "start": search_response.get("startIndex", 0),
                    "entries": search_response.get("entryList", []),
                },
                "metadata": {
                    "source": "OMIM",
                    "query": query,
                },
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return {"status": "error", "error": "Invalid API key"}
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_entry(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get OMIM entry by MIM number.

        Args:
            arguments: Dict containing:
                - mim_number: OMIM MIM number (e.g., 164730 for BRAF)
                - include: Data to include (default: all basic data)
        """
        mim_number = arguments.get("mim_number", "")
        if not mim_number:
            return {
                "status": "error",
                "error": "Missing required parameter: mim_number",
            }

        # Clean MIM number (remove any prefix)
        mim_number = str(mim_number).replace("OMIM:", "").replace("MIM:", "").strip()

        include = arguments.get("include", "text,clinicalSynopsis,geneMap")

        params = self._get_params(
            {
                "mimNumber": mim_number,
                "include": include,
            }
        )

        try:
            response = requests.get(
                f"{OMIM_API_URL}/entry",
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/OMIM"},
            )
            response.raise_for_status()
            data = response.json()

            omim_data = data.get("omim", {})
            entry_list = omim_data.get("entryList", [])

            if entry_list:
                entry = entry_list[0].get("entry", {})
                return {
                    "status": "success",
                    "data": entry,
                    "metadata": {
                        "source": "OMIM",
                        "mim_number": mim_number,
                    },
                }
            else:
                return {
                    "status": "error",
                    "error": f"No entry found for MIM: {mim_number}",
                }

        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"HTTP error: {e.response.status_code}"}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_map(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene-disease mapping information.

        Args:
            arguments: Dict containing:
                - mim_number: OMIM MIM number for gene or phenotype
                OR
                - chromosome: Chromosome number (1-22, X, Y)
        """
        mim_number = arguments.get("mim_number", "")
        chromosome = arguments.get("chromosome", "")

        if not mim_number and not chromosome:
            return {
                "status": "error",
                "error": "Either mim_number or chromosome required",
            }

        params = self._get_params({})

        if mim_number:
            mim_number = (
                str(mim_number).replace("OMIM:", "").replace("MIM:", "").strip()
            )
            params["mimNumber"] = mim_number
        else:
            params["chromosome"] = str(chromosome)
            params["limit"] = min(arguments.get("limit", 50), 100)

        try:
            response = requests.get(
                f"{OMIM_API_URL}/geneMap",
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/OMIM"},
            )
            response.raise_for_status()
            data = response.json()

            omim_data = data.get("omim", {})
            gene_map_list = omim_data.get("geneMapList", [])

            return {
                "status": "success",
                "data": {
                    "gene_maps": gene_map_list,
                    "count": len(gene_map_list),
                },
                "metadata": {
                    "source": "OMIM Gene Map",
                    "mim_number": mim_number if mim_number else None,
                    "chromosome": chromosome if chromosome else None,
                },
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_clinical_synopsis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get clinical synopsis (phenotype features) for an OMIM entry.

        Args:
            arguments: Dict containing:
                - mim_number: OMIM MIM number for a phenotype entry
        """
        mim_number = arguments.get("mim_number", "")
        if not mim_number:
            return {
                "status": "error",
                "error": "Missing required parameter: mim_number",
            }

        mim_number = str(mim_number).replace("OMIM:", "").replace("MIM:", "").strip()

        params = self._get_params(
            {
                "mimNumber": mim_number,
                "include": "clinicalSynopsis",
            }
        )

        try:
            response = requests.get(
                f"{OMIM_API_URL}/clinicalSynopsis",
                params=params,
                timeout=self.timeout,
                headers={"User-Agent": "ToolUniverse/OMIM"},
            )
            response.raise_for_status()
            data = response.json()

            omim_data = data.get("omim", {})
            synopsis_list = omim_data.get("clinicalSynopsisList", [])

            if synopsis_list:
                synopsis = synopsis_list[0].get("clinicalSynopsis", {})
                return {
                    "status": "success",
                    "data": synopsis,
                    "metadata": {
                        "source": "OMIM Clinical Synopsis",
                        "mim_number": mim_number,
                    },
                }
            else:
                return {
                    "status": "error",
                    "error": f"No clinical synopsis for MIM: {mim_number}",
                }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
