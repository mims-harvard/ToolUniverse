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

        try:
            associations, total = self._fetch(gene_name, size)
            resolved_name = gene_name

            # `mapped_gene` matches the catalog's symbol literally, so writing an
            # interleukin the way clinicians do ("IL-23R") returns an ordinary
            # empty result rather than the 112 associations filed under "IL23R".
            # Genuinely hyphenated symbols are unaffected because they match on
            # the first attempt (HLA-A returns 107), so only retry after a miss --
            # and say which spelling produced the answer.
            fallback_note = None
            if not associations and "-" in gene_name:
                candidate = gene_name.replace("-", "")
                retry_associations, retry_total = self._fetch(candidate, size)
                if retry_associations:
                    associations, total = retry_associations, retry_total
                    resolved_name = candidate
                    fallback_note = (
                        f"No GWAS Catalog associations are filed under "
                        f"'{gene_name}'; these results are for '{candidate}', "
                        f"the unhyphenated symbol the catalog uses."
                    )

            result = {
                "gene_name": resolved_name,
                "association_count": len(associations),
                "associations": associations,
                "total_found": total,
            }
            if fallback_note:
                result["queried_gene_name"] = gene_name
                result["gene_name_note"] = fallback_note
            return result

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _fetch(self, gene_name, size):
        """Return (associations sorted by p-value, total matches) for a symbol."""
        response = self.session.get(
            f"{self.base_url}/v2/associations",
            params={"mapped_gene": gene_name, "size": size, "page": 0},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        associations = data.get("_embedded", {}).get("associations", [])
        # The API does not order by significance, but the tool description
        # promises the "strongest" associations -- sort the returned set by
        # p-value (most significant first) so the top rows are the strongest.
        associations = sorted(associations, key=self._pvalue_sort_key)
        return associations, data.get("page", {}).get("totalElements", 0)
