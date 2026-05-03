"""
EBI Search API Tool

This tool provides access to the EBI Search API, a unified search interface
across 160+ EBI data resources including Ensembl, UniProt, InterPro, and more.
"""

import requests
from typing import Any, Dict, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("EBISearchRESTTool")
class EBISearchRESTTool(BaseTool):
    """
    EBI Search API tool.
    Generic wrapper for EBI Search API endpoints defined in ebi_search_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/ebisearch/ws/rest"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = (
            120  # Increased to 120s - facet queries can be very slow on EBI API
        )

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")

        # If endpoint template is provided, use it
        if endpoint_template:
            url = endpoint_template
            # Replace placeholders in URL
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name and arguments
        tool_name = self.tool_config.get("name", "")
        domain = args.get("domain", "")
        entry_id = args.get("entry_id", "")

        # For listing domains, use base URL
        if tool_name == "ebi_list_domains":
            return self.base_url

        # For getting entry, use /entry/ path format
        # EBI Search requires the entry ID format from search results (e.g., "P53_HUMAN" not "P04637")
        # We'll use search to find the correct ID if direct lookup fails
        if tool_name == "ebi_get_entry" and domain and entry_id:
            return f"{self.base_url}/{domain}/entry/{entry_id}"

        # For domain info or fields, use domain path
        if domain:
            if tool_name in ["ebi_get_domain_info", "ebi_get_domain_fields"]:
                return f"{self.base_url}/{domain}"
            # For search operations, domain is in path
            return f"{self.base_url}/{domain}"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for EBI Search API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        # For entry retrieval, fields can be specified
        if tool_name == "ebi_get_entry":
            if "fields" in args:
                params["fields"] = args["fields"]
            params["format"] = args.get("format", "json")
            return params

        # For domain info/fields, no query params needed (or just format)
        if tool_name in [
            "ebi_get_domain_info",
            "ebi_get_domain_fields",
            "ebi_list_domains",
        ]:
            params["format"] = args.get("format", "json")
            return params

        # For search operations, include query parameters
        if "query" in args:
            params["query"] = args["query"]
        if "size" in args:
            params["size"] = args["size"]
        if "format" in args:
            params["format"] = args.get("format", "json")
        else:
            params["format"] = "json"

        # Facet parameters - EBI Search requires facets to be available for the domain
        # Users should check available facets first using ebi_get_domain_info
        if "facets" in args and args["facets"]:
            # Facets should be comma-separated or space-separated
            facets = args["facets"]
            if isinstance(facets, list):
                facets = ",".join(facets)
            params["facets"] = facets
        if "facetcount" in args:
            params["facetcount"] = args["facetcount"]

        # Field selection
        if "fields" in args:
            params["fields"] = args["fields"]

        # Pagination
        if "start" in args:
            params["start"] = args["start"]
        if "page" in args:
            params["page"] = args["page"]

        # Sorting
        if "sort" in args:
            params["sort"] = args["sort"]

        return params

    def _find_entry_id_via_search(
        self, domain: str, query: str
    ) -> Optional[Dict[str, Any]]:
        """Find entry ID via search and return entry data"""
        try:
            # Search for the entry
            search_url = f"{self.base_url}/{domain}"
            search_params = {"query": query, "size": 1, "format": "json"}
            search_response = self.session.get(
                search_url, params=search_params, timeout=self.timeout
            )
            search_response.raise_for_status()
            search_data = search_response.json()

            entries = search_data.get("entries", [])
            if entries:
                # Found entry via search - return it with note
                entry = entries[0]
                return {
                    "status": "success",
                    "data": entry,
                    "url": search_response.url,
                    "note": f"Entry found via search. EBI Search get_entry endpoint requires specific ID format. Use ebi_search_domain to find entries, then use the 'id' field from results for ebi_get_entry.",
                    "search_used": True,
                    "entry_id_from_search": entry.get("id", ""),
                    "suggestion": f"For direct entry access, use the 'id' field from search results (e.g., '{entry.get('id', '')}') instead of accession numbers.",
                }
        except Exception:
            pass
        return None

    def _extract_data(self, data: Dict, extract_path: Optional[str] = None) -> Any:
        """Extract specific data from API response"""
        if not extract_path:
            return data

        # Handle different extraction paths
        if extract_path == "entries":
            return data.get("entries", [])
        elif extract_path == "facets":
            return data.get("facets", {})
        elif extract_path == "hitCount":
            return data.get("hitCount", 0)
        elif extract_path == "domain":
            # Domain info is typically at root level or in 'domain' key
            if "domain" in data:
                return data["domain"]
            # Sometimes domain info is the root object itself
            return data
        elif extract_path == "fields":
            # Fields can be in 'fields' key or 'domain.fields'
            if "fields" in data:
                return data["fields"]
            if "domain" in data and "fields" in data["domain"]:
                return data["domain"]["fields"]
            return []
        elif "." in extract_path:
            # Extract nested path like "domain.name"
            parts = extract_path.split(".")
            result = data
            for part in parts:
                if isinstance(result, dict):
                    result = result.get(part, {})
                else:
                    return None
            return result

        return data

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Search API call"""
        tool_name = self.tool_config.get("name", "")

        try:
            # Build URL
            url = self._build_url(arguments)

            # Build parameters
            params = self._build_params(arguments)

            # Make API request
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle get_entry endpoint - if 404, try to find correct ID via search
            if tool_name == "ebi_get_entry" and response.status_code == 404:
                domain = arguments.get("domain", "")
                entry_id = arguments.get("entry_id", "")
                if domain and entry_id:
                    # Try to find the correct entry ID format via search
                    search_result = self._find_entry_id_via_search(domain, entry_id)
                    if search_result:
                        return search_result

            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract data if specified
            extract_path = self.tool_config["fields"].get("extract_path")
            if extract_path:
                result = self._extract_data(data, extract_path)
            else:
                result = data

            # Build response
            response_data = {
                "status": "success",
                "data": result,
                "url": response.url,
            }

            # Add metadata
            if isinstance(data, dict):
                if "hitCount" in data:
                    response_data["hitCount"] = data["hitCount"]
                if "facets" in data:
                    facets = data["facets"]
                    response_data["facets"] = facets
                    # Add note about available facets
                    if isinstance(facets, dict) and facets:
                        available_facets = list(facets.keys())
                        response_data["available_facets"] = available_facets[
                            :10
                        ]  # First 10
                    elif isinstance(facets, list) and facets:
                        response_data["facets_note"] = (
                            f"Found {len(facets)} facet categories"
                        )
                    elif not facets:
                        response_data["facets_note"] = (
                            "No facets returned. Facets may need to be explicitly requested or may not be available for this domain/query."
                        )
                if "domain" in data:
                    response_data["domain"] = data["domain"]

            # Add count for list results
            if isinstance(result, list):
                response_data["count"] = len(result)

            return response_data

        except requests.exceptions.RequestException as e:
            # For get_entry, try fallback via search
            if tool_name == "ebi_get_entry" and "404" in str(e):
                domain = arguments.get("domain", "")
                entry_id = arguments.get("entry_id", "")
                if domain and entry_id:
                    search_result = self._find_entry_id_via_search(domain, entry_id)
                    if search_result:
                        return search_result
            return {
                "status": "error",
                "error": f"EBI Search API error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }
