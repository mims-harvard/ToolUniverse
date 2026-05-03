import requests
from typing import Any, Dict, Optional
from urllib.parse import quote
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("GeneOntologyTool")
class GeneOntologyTool(BaseTool):
    """
    A general-purpose tool for calling the Gene Ontology (GO) API.
    It is configured via a dictionary that defines the specific API endpoint.
    """

    def __init__(self, tool_config: Dict):
        """
        Initializes the tool with a configuration.

        Args:
            tool_config (Dict): A dictionary containing 'fields' with an 'endpoint'.
        """
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]
        self.extract_path = tool_config["fields"].get("extract_path")
        self.timeout = 20

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Builds the request URL from arguments."""
        url = self.endpoint
        for key, value in args.items():
            url = url.replace(f"{{{key}}}", quote(str(value)))
        return url

    def _extract_data(self, data: Dict, extract_path: str) -> Any:
        """Extract specific data from the GO API response using custom paths."""

        if extract_path == "response.docs[0]":
            # Extract single document from GOlr response
            response = data.get("response", {})
            docs = response.get("docs", [])
            if docs:
                return docs[0]
            else:
                return {"status": "error", "error": "No GO term found"}

        elif extract_path == "response.docs":
            # Extract all documents from GOlr response
            response = data.get("response", {})
            docs = response.get("docs", [])
            return docs

        elif extract_path == "associations[*].subject":
            # Extract gene/protein information from Biolink associations
            result = []
            # Handle both dict with associations and direct list from Biolink API
            if isinstance(data, list):
                # Direct list of associations from Biolink API
                associations = data
            else:
                # Dictionary response with associations key
                associations = data.get("associations", [])

            for assoc in associations:
                subject = assoc.get("subject", {})
                result.append(subject)
            return result

        # For simple paths, try direct access
        try:
            if "." in extract_path:
                keys = extract_path.split(".")
                result = data
                for key in keys:
                    if "[" in key and "]" in key:
                        # Handle array indexing like "docs[0]"
                        array_key = key.split("[")[0]
                        index_str = key.split("[")[1].split("]")[0]
                        result = result.get(array_key, [])
                        if index_str.isdigit():
                            index = int(index_str)
                            if index < len(result):
                                result = result[index]
                            else:
                                return {
                                    "status": "error",
                                    "error": f"Index {index} out of range",
                                }
                        else:
                            return {
                                "status": "error",
                                "error": f"Invalid array index: {index_str}",
                            }
                    else:
                        result = result.get(key, {})
                return result
            else:
                return data.get(extract_path)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to extract data using path '{extract_path}': {e}",
            }

    def run(self, arguments: Any = None) -> Any:
        """
        Executes the API call and returns the data.

        Args:
            arguments (Dict[str, Any]): Parameters for the API call.

        Returns
            Any: The JSON data from the API or an error dictionary.
        """
        # Normalize arguments
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return {
                "status": "error",
                "error": "Invalid arguments type; expected a mapping/dict.",
            }

        # Handle different endpoint formats
        if "?" in self.endpoint:
            # This is a complete URL with query parameters (GOlr format)
            url = self.endpoint
            for key, value in arguments.items():
                url = url.replace(f"{{{key}}}", quote(str(value)))
            params = {}
        else:
            # This is a template URL (Biolink format)
            url_args = arguments.copy()
            params = {}

            # Move query parameters to params dict for Biolink API
            if "taxon" in arguments:
                params["taxon"] = url_args.pop("taxon")
            if "rows" in arguments:
                params["rows"] = url_args.pop("rows")
            if "start" in arguments:
                params["start"] = url_args.pop("start")

            # Build URL with remaining arguments
            url = self._build_url(url_args)

        try:
            resp = requests.get(
                url,
                params=params,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error": "The requested resource was not found (404 Not Found).",
                }
            return {
                "status": "error",
                "error": f"GO API request failed with HTTP status: {e.response.status_code}",
                "detail": e.response.text,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"A network error occurred while requesting the GO API: {e}",
            }
        except ValueError:
            return {
                "status": "error",
                "error": "Failed to parse GO API response, which may not be valid JSON.",
                "content": resp.text,
            }

        # If extract_path is configured, extract the corresponding subset
        if self.extract_path:
            result = self._extract_data(data, self.extract_path)

            # Handle empty results
            if isinstance(result, list) and len(result) == 0:
                return {
                    "status": "error",
                    "error": f"No data found for path: {self.extract_path}",
                }
            elif isinstance(result, dict) and "error" in result:
                return result

            return result

        return data

    # Method bindings for backward compatibility and convenience
    def search_terms(self, query: str) -> Any:
        return self.run({"query": query})

    def get_term_details(self, id: str) -> Any:
        return self.run({"id": id})

    def get_genes_for_term(
        self, id: str, taxon: Optional[str] = None, rows: Optional[int] = None
    ) -> Any:
        args = {"id": id}
        if taxon:
            args["taxon"] = taxon
        if rows:
            args["rows"] = rows
        return self.run(args)

    def get_terms_for_gene(self, id: str) -> Any:
        return self.run({"id": id})
