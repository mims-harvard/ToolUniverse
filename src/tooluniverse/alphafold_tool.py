import requests
import re
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

ALPHAFOLD_BASE_URL = "https://alphafold.ebi.ac.uk/api"


@register_tool("AlphaFoldRESTTool")
class AlphaFoldRESTTool(BaseTool):
    """
    AlphaFold Protein Structure Database API tool.
    Generic wrapper for AlphaFold API endpoints from alphafold_tools.json.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        fields = tool_config.get("fields", {})
        parameter = tool_config.get("parameter", {})

        self.endpoint_template: str = fields["endpoint"]
        self.required: List[str] = parameter.get("required", [])
        self.output_format: str = fields.get("return_format", "JSON")
        self.auto_query_params: Dict[str, Any] = fields.get("auto_query_params", {})

    def _build_url(self, arguments: Dict[str, Any]) -> str | Dict[str, Any]:
        # Example: endpoint_template = "/annotations/{qualifier}.json"
        url_path = self.endpoint_template
        # Find placeholders like {qualifier} in the path
        placeholders = re.findall(r"\{([^{}]+)\}", url_path)
        used = set()

        # Replace placeholders with provided arguments
        #   ex. if arguments = {"qualifier": "P69905", "type": "MUTAGEN"}
        for ph in placeholders:
            if ph not in arguments or arguments[ph] is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter '{ph}'",
                }
            url_path = url_path.replace(f"{{{ph}}}", str(arguments[ph]))
            used.add(ph)
        # Now url_path = "/annotations/P69905.json"

        # Treat all remaining args as query parameters
        #   "type" wasn't a placeholder, so it becomes a query param
        query_args = {k: v for k, v in arguments.items() if k not in used}

        # Add auto_query_params from config (e.g., type=MUTAGEN)
        query_args.update(self.auto_query_params)

        if query_args:
            from urllib.parse import urlencode

            url_path += "?" + urlencode(query_args)

        # Final example: annotations/P69905.json?type=MUTAGEN
        return ALPHAFOLD_BASE_URL + url_path

    def _make_request(self, url: str) -> Dict[str, Any]:
        """Perform a GET request and handle common errors."""
        try:
            resp = requests.get(
                url,
                timeout=30,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ToolUniverse/AlphaFold",
                },
            )
        except Exception as e:
            return {
                "status": "error",
                "error": "Request to AlphaFold API failed",
                "detail": str(e),
            }

        if resp.status_code == 404:
            # Try to provide more context about 404 errors
            # Check if protein exists in AlphaFold DB
            try:
                qualifier_match = re.search(r"/annotations/([^/]+)\.json", url)
                if qualifier_match:
                    accession = qualifier_match.group(1)
                    base = ALPHAFOLD_BASE_URL
                    check_url = f"{base}/uniprot/summary/{accession}.json"
                    check_resp = requests.get(check_url, timeout=10)
                    if check_resp.status_code == 200:
                        return {
                            "status": "error",
                            "error": "No MUTAGEN annotations available",
                            "reason": (
                                "Protein exists in AlphaFold DB but "
                                "has no MUTAGEN annotations"
                            ),
                            "endpoint": url,
                        }
                    else:
                        return {
                            "status": "error",
                            "error": "Protein not found in AlphaFold DB",
                            "endpoint": url,
                        }
            except Exception:
                pass  # Fall through to generic error
            return {"status": "error", "error": "Not found", "endpoint": url}
        if resp.status_code == 500:
            return {
                "status": "error",
                "error": "AlphaFold EBI API is temporarily unavailable (HTTP 500). "
                "Try again later or download structures directly from "
                "https://alphafold.ebi.ac.uk/download or via PDB.",
                "endpoint": url,
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"AlphaFold API returned {resp.status_code}",
                "detail": resp.text,
                "endpoint": url,
            }

        return {"response": resp}

    def run(self, arguments: Dict[str, Any]):
        """Execute the tool with provided arguments."""
        # Normalize uniprot_id / uniprot_accession → qualifier
        if "qualifier" not in arguments:
            for alias in ("uniprot_id", "uniprot_accession", "accession"):
                if arguments.get(alias):
                    arguments = dict(arguments, qualifier=arguments[alias])
                    break

        # Validate required params
        missing = [k for k in self.required if k not in arguments]
        if missing:
            return {
                "status": "error",
                "error": f"Missing required parameter(s): {', '.join(missing)}. Tip: pass qualifier=<UniProt accession>, e.g. 'P69905'.",
            }

        # Build URL
        url = self._build_url(arguments)
        if isinstance(url, dict) and "error" in url:
            return {**url, "query": arguments}

        # Make request
        result = self._make_request(url)
        if "error" in result:
            return {**result, "query": arguments}

        resp = result["response"]

        # Parse JSON
        if self.output_format.upper() == "JSON":
            try:
                data = resp.json()
                if not data or (isinstance(data, dict) and not data):
                    return {
                        "status": "error",
                        "error": "No MUTAGEN annotations available",
                        "reason": (
                            "Protein exists in AlphaFold DB but "
                            "has no MUTAGEN annotations from UniProt"
                        ),
                        "endpoint": url,
                        "query": arguments,
                    }

                return {
                    "status": "success",
                    "data": data,
                    "metadata": {
                        "count": len(data) if isinstance(data, list) else 1,
                        "source": "AlphaFold Protein Structure DB",
                        "endpoint": url,
                        "query": arguments,
                    },
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": "Failed to parse JSON response",
                    "raw": resp.text,
                    "detail": str(e),
                    "endpoint": url,
                    "query": arguments,
                }

        # Fallback for non-JSON output
        return {
            "status": "success",
            "data": resp.text,
            "metadata": {"endpoint": url, "query": arguments},
        }
