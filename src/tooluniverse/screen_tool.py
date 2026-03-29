import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("SCREENRESTTool")
class SCREENRESTTool(BaseTool):
    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Accept 'query' as alias for 'gene_name'
            if "query" in arguments and "gene_name" not in arguments:
                arguments = dict(arguments)
                arguments["gene_name"] = arguments.pop("query")
            gene_name = arguments.get("gene_name", "")
            element_type = arguments.get("element_type", "enhancer")
            limit = int(arguments.get("limit", 10))

            if not gene_name:
                return {
                    "status": "error",
                    "error": "gene_name (or query) is required.",
                }

            # Use ENCODE API as SCREEN alternative for regulatory element experiments
            url = (
                f"https://www.encodeproject.org/search/"
                f"?type=Experiment"
                f"&target.label={gene_name}"
                f"&format=json&limit={limit}"
            )

            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            experiments = data.get("@graph", [])
            results = [
                {
                    "accession": e.get("accession", ""),
                    "assay_title": e.get("assay_title", ""),
                    "target": e.get("target", {}).get("label", "")
                    if isinstance(e.get("target"), dict)
                    else "",
                    "biosample": e.get("biosample_ontology", {}).get("term_name", "")
                    if isinstance(e.get("biosample_ontology"), dict)
                    else "",
                    "status": e.get("status", ""),
                }
                for e in experiments
            ]

            return {
                "status": "success",
                "data": {
                    "gene_name": gene_name,
                    "element_type": element_type,
                    "count": len(results),
                    "regulatory_elements": results,
                },
                "metadata": {
                    "source": "ENCODE (SCREEN alternative)",
                    "url": url,
                },
            }
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "error": f"SCREEN API HTTP error: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"SCREEN API error: {str(e)}"}
