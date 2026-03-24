"""
IntAct Molecular Interaction Database Tool

This tool provides access to the IntAct database for protein-protein interactions,
molecular interactions, and interaction evidence.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("IntActRESTTool")
class IntActRESTTool(BaseTool):
    """
    IntAct REST API tool.
    Generic wrapper for IntAct API endpoints defined in intact_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/intact/ws"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config["fields"].get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            # Replace placeholders in URL
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            return url

        # Build URL based on tool name
        if tool_name == "intact_get_interactor":
            identifier = args.get("identifier", "")
            if identifier:
                return f"{self.base_url}/interactor/findInteractor/{identifier}"

        elif tool_name == "intact_get_interactions":
            identifier = args.get("identifier", "")
            if identifier:
                return f"{self.base_url}/interaction/findInteractions"

        elif tool_name == "intact_search_interactions":
            return f"{self.base_url}/interaction/find"

        elif tool_name == "intact_get_interaction_details":
            interaction_id = args.get("interaction_id", "")
            if interaction_id:
                return f"{self.base_url}/interaction/{interaction_id}"

        elif tool_name == "intact_get_interaction_network":
            identifier = args.get("identifier", "")
            if identifier:
                return f"{self.base_url}/interaction/findInteractions/{identifier}"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for IntAct API"""
        params = {}
        tool_name = self.tool_config.get("name", "")

        # For search operations
        if tool_name == "intact_search_interactions":
            if "query" in args:
                params["query"] = args["query"]
            else:
                params["query"] = "*"
            params["format"] = args.get("format", "json")

        # For interaction retrieval by identifier
        elif tool_name == "intact_get_interactions":
            identifier = args.get("identifier", "")
            if identifier:
                params["query"] = identifier
            params["format"] = args.get("format", "json")

        # For interactor retrieval (paginated)
        elif tool_name == "intact_get_interactor":
            params["page"] = args.get("page", 0)
            params["pageSize"] = args.get("pageSize", 10)

        # For interaction details
        elif tool_name == "intact_get_interaction_details":
            params["format"] = args.get("format", "json")

        # For network/interactions (paginated)
        elif tool_name == "intact_get_interaction_network":
            params["page"] = args.get("page", 0)
            params["pageSize"] = args.get("pageSize", 20)

        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the IntAct API call"""
        # Normalize protein_id / gene_symbol / uniprot_id / protein_name → identifier
        if "identifier" not in arguments:
            for alias in (
                "uniprot_id",
                "protein_id",
                "gene_symbol",
                "gene",
                "gene_name",
                "protein_name",
                "protein",
            ):
                if arguments.get(alias):
                    arguments = dict(arguments, identifier=arguments[alias])
                    break

        tool_name = self.tool_config.get("name", "")

        # Use Complex Web Service for complex queries
        if tool_name == "intact_get_interactions_by_complex":
            return self._use_complex_web_service(arguments)

        elif tool_name == "intact_get_complex_details":
            return self._get_complex_details(arguments)
        # Use EBI Search API as primary method since IntAct direct API is unreliable
        # EBI Search has an 'intact' domain that works reliably
        if tool_name in [
            "intact_get_interactions",
            "intact_search_interactions",
            "intact_get_interactions_by_organism",
        ]:
            return self._use_ebi_search(arguments, tool_name)

        try:
            # Build URL
            url = self._build_url(arguments)

            # Build parameters
            params = self._build_params(arguments)

            # Make API request
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Check if response is HTML (API endpoint not available)
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                # Fallback to EBI Search
                return self._use_ebi_search(arguments, tool_name)

            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Handle paginated responses from findInteractor/findInteractions
            if isinstance(data, dict) and "content" in data:
                content = data["content"]
                total = data.get("totalElements", len(content))
                meta: Dict[str, Any] = {
                    "url": response.url,
                    "count": len(content),
                    "totalElements": total,
                }
                if total > len(content):
                    meta["note"] = (
                        f"Showing {len(content)} of {total} results. "
                        "Use page/pageSize params for more."
                    )
                return {"status": "success", "data": content, "metadata": meta}

            # Build response
            meta = {"url": response.url}
            if isinstance(data, list):
                meta["count"] = len(data)
            elif isinstance(data, dict) and isinstance(data.get("data"), list):
                meta["count"] = len(data["data"])
            return {"status": "success", "data": data, "metadata": meta}

        except requests.exceptions.RequestException:
            # Fallback to EBI Search if direct API fails
            return self._use_ebi_search(arguments, tool_name)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
            }

    def _use_ebi_search(
        self, arguments: Dict[str, Any], tool_name: str
    ) -> Dict[str, Any]:
        """Use EBI Search API as fallback for IntAct queries"""
        try:
            ebi_search_url = "https://www.ebi.ac.uk/ebisearch/ws/rest/intact"
            # Request name+description fields so entries carry interactor info (Feature-122A-002)
            params = {"format": "json", "fields": "name,description"}

            # Map tool names to their query parameter key and default size
            tool_query_config = {
                "intact_get_interactions": ("identifier", 25),
                "intact_get_interactor": ("identifier", 10),
                "intact_get_interactions_by_publication": ("pubmed_id", 25),
                "intact_get_interactions_by_experiment": ("experiment_id", 25),
                "intact_get_interaction_network": ("identifier", 50),
                "intact_get_interactions_by_organism": ("taxid", 25),
            }

            if tool_name == "intact_search_interactions":
                params["query"] = arguments.get("query", "*")
                params["size"] = arguments.get("max", 25)
            elif tool_name in tool_query_config:
                query_key, default_size = tool_query_config[tool_name]
                query_value = arguments.get(query_key, "")
                if query_value:
                    params["query"] = query_value
                    params["size"] = (
                        arguments.get("size") or arguments.get("limit") or default_size
                    )

            response = self.session.get(
                ebi_search_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Transform EBI Search response to match expected format
            raw_entries = data.get("entries", [])

            # Flatten fields into each entry for easier consumption (Feature-122A-002)
            entries = []
            for entry in raw_entries:
                flat: Dict[str, Any] = {
                    "id": entry.get("id", ""),
                    "source": entry.get("source", ""),
                }
                fields = entry.get("fields", {})
                names = fields.get("name", [])
                descs = fields.get("description", [])
                if names:
                    flat["interaction_name"] = names[0]
                if descs:
                    flat["interactor_descriptions"] = descs
                entries.append(flat)

            # Extract interaction IDs for easy access
            interaction_ids = [e["id"] for e in entries if e.get("id")]

            # For interactor lookup, try to get more details if possible
            if tool_name == "intact_get_interactor" and entries:
                # Return first matching entry as interactor details
                return {
                    "status": "success",
                    "data": entries[0] if entries else {},
                    "metadata": {
                        "url": response.url,
                        "count": len(entries),
                        "hitCount": data.get("hitCount", len(entries)),
                        "interaction_ids": interaction_ids[:10],
                        "note": "Data retrieved via EBI Search API (IntAct domain). For detailed interactor info, use IntAct website.",
                    },
                }

            note = "Data retrieved via EBI Search API (IntAct domain). Use interaction_ids to get details with intact_get_interaction_details or intact_get_interaction_network."
            if tool_name == "intact_get_interactions_by_organism":
                note = "Interactions retrieved via EBI Search API (IntAct domain) filtered by organism taxonomy ID. Use interaction_ids to get detailed interaction information."

            return {
                "status": "success",
                "data": entries,
                "metadata": {
                    "url": response.url,
                    "count": len(entries),
                    "hitCount": data.get("hitCount", len(entries)),
                    "interaction_ids": interaction_ids,
                    "note": note,
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"IntAct query failed (tried EBI Search fallback): {str(e)}",
            }

    def _use_complex_web_service(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Use IntAct Complex Web Service for complex queries"""
        try:
            complex_id = arguments.get("complex_id", "")
            if not complex_id:
                return {
                    "status": "error",
                    "error": "complex_id parameter is required",
                }

            # Complex Web Service endpoint - query goes in path, not params
            from urllib.parse import quote

            complex_id_encoded = quote(complex_id, safe="")
            complex_url = (
                f"https://www.ebi.ac.uk/intact/complex-ws/search/{complex_id_encoded}"
            )
            params = {
                "format": "json",
                "first": arguments.get("first", 0),
                "number": arguments.get("size", 25),
            }

            response = self.session.get(
                complex_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Extract complex information
            elements = data.get("elements", [])
            total = data.get("totalNumberOfResults", 0)

            # Extract complex ACs for reference
            complex_ac_list = []
            for element in elements:
                complex_ac = element.get("complexAC", "")
                if complex_ac:
                    complex_ac_list.append(complex_ac)

            return {
                "status": "success",
                "data": elements,
                "metadata": {
                    "url": response.url,
                    "count": len(elements),
                    "totalNumberOfResults": total,
                    "complex_ac_list": complex_ac_list,
                    "note": "Data retrieved via IntAct Complex Web Service. Use complex_ac_list to reference specific complexes.",
                },
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"IntAct Complex Web Service query failed: {str(e)}",
            }

    def _get_complex_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific complex by complex AC"""
        try:
            complex_ac = arguments.get("complex_ac", "")
            if not complex_ac:
                return {
                    "status": "error",
                    "error": "complex_ac parameter is required (e.g., 'CPX-915')",
                }

            # Complex Web Service details endpoint
            complex_url = (
                f"https://www.ebi.ac.uk/intact/complex-ws/complex/{complex_ac}"
            )
            params = {
                "format": "json",
            }

            response = self.session.get(
                complex_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            return {
                "status": "success",
                "data": data,
                "metadata": {
                    "url": response.url,
                    "complex_ac": data.get("complexAc", complex_ac),
                    "complex_name": data.get("name", ""),
                    "note": "Data retrieved via IntAct Complex Web Service. Includes complex details, participants, functions, properties, and related information.",
                },
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Complex '{complex_ac}' not found. Verify the complex AC is correct (e.g., 'CPX-915'). Use intact_get_interactions_by_complex to search for complexes.",
                }
            return {
                "status": "error",
                "error": f"IntAct Complex Web Service query failed: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"IntAct Complex Web Service query failed: {str(e)}",
            }
