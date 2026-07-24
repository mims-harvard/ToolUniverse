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

    @staticmethod
    def _pvalue_sort_key(assoc):
        """Numeric p-value for sorting; unparseable/missing sort last."""
        try:
            return float(assoc.get("p_value"))
        except (TypeError, ValueError):
            return float("inf")

    def run(self, arguments):
        gene_name = arguments.get("gene_name")
        if not gene_name:
            return {"status": "error", "error": "Missing required parameter: gene_name"}

        # Default of 100 (was 5): a well-studied gene has hundreds of GWAS
        # associations (TCF7L2 has 902), and the API returns them UNSORTED, so a
        # size-5 default silently surfaced 5 arbitrary rows -- for TCF7L2 all 5
        # were anthropometric (hip/waist/BMI) while its 37 flagship type-2-
        # diabetes associations were hidden, misleading a clinician into thinking
        # it is not a T2D locus. Also matches the sibling trait-search default.
        size = int(arguments.get("size") or arguments.get("limit") or 100)
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

            # The API does not order by significance, but the tool description
            # promises the "strongest" associations -- sort the returned set by
            # p-value (most significant first) so the top rows are the strongest.
            associations = sorted(associations, key=self._pvalue_sort_key)

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
