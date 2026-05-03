import requests
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("GWASGeneSearch")
class GWASGeneSearch(BaseTool):
    """
    Local tool wrapper for GWAS Catalog REST API.
    Searches associations by gene name.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/gwas/rest/api"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def run(self, arguments):
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Missing required parameter: gene_name"}

        # Search for associations by gene name
        size = int(arguments.get("size", 5))
        url = f"{self.base_url}/v2/associations"
        params = {"mapped_gene": gene_name, "size": size, "page": 0}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Extract associations from _embedded structure
            associations = []
            if "_embedded" in data and "associations" in data["_embedded"]:
                associations = data["_embedded"]["associations"]

            return {
                "gene_name": gene_name,
                "association_count": len(associations),
                "associations": associations,
                "total_found": (
                    data.get("page", {}).get("totalElements", 0)
                    if "page" in data
                    else 0
                ),
            }

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
