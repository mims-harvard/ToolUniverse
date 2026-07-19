# depmap_tool.py
"""
DepMap (Dependency Map) API tool for ToolUniverse.

DepMap provides cancer cell line dependency data from CRISPR knockout screens,
drug sensitivity data, and multi-omics characterization of cancer cell lines.

Data includes:
- CRISPR gene effect scores (gene essentiality)
- Drug sensitivity data
- Cell line metadata (lineage, mutations)
- Gene expression data

API Documentation: https://depmap.sanger.ac.uk/documentation/api/
Base URL: https://api.cellmodelpassports.sanger.ac.uk
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Sanger Cell Model Passports API
DEPMAP_BASE_URL = "https://api.cellmodelpassports.sanger.ac.uk"


def _gene_symbol(item: Dict[str, Any]) -> str:
    """Uppercased gene symbol used as the sort key of the /genes catalog."""
    return item.get("attributes", {}).get("symbol", "").upper()


def _model_symbol(item: Dict[str, Any]) -> str:
    """Uppercased model name used as the sort key of the /models catalog
    (`names` is a list; its first entry is the primary name)."""
    names = item.get("attributes", {}).get("names") or [""]
    return names[0].upper()


@register_tool("DepMapTool")
class DepMapTool(BaseTool):
    """
    Tool for querying DepMap/Sanger Cell Model Passports API.

    Provides access to:
    - Cancer cell line dependency data (CRISPR screens)
    - Drug sensitivity profiles
    - Cell line metadata and annotations
    - Gene effect scores for target validation

    No authentication required for non-commercial use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "get_cell_lines"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DepMap API call."""
        operation = self.operation

        if operation == "get_cell_lines":
            return self._get_cell_lines(arguments)
        elif operation == "get_cell_line":
            return self._get_cell_line(arguments)
        elif operation == "search_cell_lines":
            return self._search_cell_lines(arguments)
        elif operation == "get_gene_dependencies":
            return self._get_gene_dependencies(arguments)
        elif operation == "get_drug_response":
            return self._get_drug_response(arguments)
        elif operation == "search_genes":
            return self._search_genes(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get list of cancer cell lines with metadata.

        Filter by tissue type or cancer type.
        """
        tissue = arguments.get("tissue")
        cancer_type = arguments.get("cancer_type")
        page_size = arguments.get("page_size", 20)

        try:
            # Fix-R19C-3: `filter[model]` on this endpoint doesn't
            # actually filter (confirmed live across multiple syntax
            # variants -- filtered and unfiltered requests return
            # identical results and the identical total count), and
            # `model_name`/`tissue`/`cancer_type`/`sample_site`/`gender`/
            # `ethnicity` aren't real attributes on the model resource at
            # all (only `names`, a list; the rest live on related sample/
            # tissue/cancer_type/patient resources, reachable per-model
            # via `include=`, which isn't practical for a whole page of
            # results without an N+1 request per row). Rather than
            # silently accepting a tissue/cancer_type filter and
            # returning unfiltered results, warn that filtering isn't
            # currently supported by the upstream API; model_name is
            # fixed since it's cheap (no extra request needed).
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"page[size]": min(page_size, 100)}

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Parse cell line data
            cell_lines = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                names = attrs.get("names") or []
                cell_lines.append(
                    {
                        "model_id": item.get("id"),
                        "model_name": names[0] if names else None,
                    }
                )

            result_data = {
                "cell_lines": cell_lines,
                "count": len(cell_lines),
                "total": data.get("meta", {}).get("count", len(cell_lines)),
            }
            if tissue or cancer_type:
                result_data["warning"] = (
                    "The tissue/cancer_type filter had no effect: the "
                    "Sanger Cell Model Passports /models endpoint does not "
                    "support server-side filtering by these fields. The "
                    "results above are unfiltered. Use DepMap_get_cell_line "
                    "on individual model_ids to retrieve their tissue/"
                    "cancer_type."
                )
            return {"status": "success", "data": result_data}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_cell_line(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information for a specific cell line.

        Returns metadata, mutations, and available data types.
        """
        model_id = arguments.get("model_id")
        model_name = arguments.get("model_name")

        if not model_id and not model_name:
            return {
                "status": "error",
                "error": "Either model_id or model_name is required",
            }

        try:
            if model_id:
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"
            else:
                # Search by name first
                search_result = self._search_cell_lines({"query": model_name})
                if (
                    search_result["status"] != "success"
                    or not search_result["data"]["cell_lines"]
                ):
                    return {
                        "status": "success",
                        "data": None,
                        "message": f"Cell line '{model_name}' not found",
                    }
                model_id = search_result["data"]["cell_lines"][0]["model_id"]
                url = f"{DEPMAP_BASE_URL}/models/{model_id}"

            # Fix-R19C-3: the fields below (tissue, cancer_type, gender,
            # ethnicity, msi_status, etc.) don't exist on the model
            # resource's own `attributes` at all -- confirmed live the
            # model only has fields like `names`/`growth_properties`/
            # `mutations_per_mb`/`ploidy`. tissue/cancer_type/gender/
            # ethnicity/msi_status are on separate related resources
            # (sample -> tissue/cancer_type/patient, and a top-level
            # model_msi_status relation), reachable in one request via
            # the JSON:API `include` param.
            params = {
                "include": "sample.tissue,sample.cancer_type,sample.patient,model_msi_status"
            }
            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"Cell line not found: {model_id or model_name}",
                }

            response.raise_for_status()
            data = response.json()

            item = data.get("data", {})
            attrs = item.get("attributes", {})
            included = {
                (inc.get("type"), inc.get("id")): inc.get("attributes", {})
                for inc in data.get("included", [])
            }
            sample = next((v for (t, _), v in included.items() if t == "sample"), {})
            tissue = next((v for (t, _), v in included.items() if t == "tissue"), {})
            cancer_type = next(
                (v for (t, _), v in included.items() if t == "cancer_type"), {}
            )
            patient = next((v for (t, _), v in included.items() if t == "patient"), {})
            msi = next(
                (v for (t, _), v in included.items() if t == "model_msi_status"), {}
            )

            names = attrs.get("names") or []

            return {
                "status": "success",
                "data": {
                    "model_id": item.get("id"),
                    "model_name": names[0] if names else None,
                    "tissue": tissue.get("name"),
                    "cancer_type": cancer_type.get("name"),
                    "tissue_status": sample.get("tissue_status"),
                    "sample_site": sample.get("sample_site"),
                    "gender": patient.get("gender"),
                    "ethnicity": patient.get("ethnicity"),
                    "age_at_sampling": sample.get("age_at_sampling"),
                    "growth_properties": attrs.get("growth_properties"),
                    "msi_status": msi.get("msi_status"),
                    "ploidy": attrs.get("ploidy"),
                    "mutational_burden": attrs.get("mutations_per_mb"),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _find_catalog_page(
        self,
        url: str,
        params: Dict[str, Any],
        query_upper: str,
        symbol_of,
        request_timeout: int,
    ) -> List[Dict[str, Any]]:
        """Binary-search a symbol-sorted, paginated JSON:API catalog for the
        single page that could contain ``query_upper``.

        ``params`` must already request page 1 (``page[number]=1``) with the
        desired ``sort`` and ``page[size]``; it is mutated in place as pages
        are visited. ``symbol_of(item)`` returns an item's uppercased sort
        symbol. Returns that page's list of resource items, or ``[]`` if the
        query sorts outside the whole catalog.

        Comparing the query against each page's first/last symbol (rather
        than scanning linearly from page 1) keeps the cost to
        ~log2(total_pages) round-trips over the full catalog. ``fetched_page``
        is tracked so re-examining the current page reuses the data already in
        hand instead of refetching (which would also risk stale data).
        """
        page_size = params["page[size]"]
        response = requests.get(url, params=params, timeout=request_timeout)
        response.raise_for_status()
        first_data = response.json()
        total_count = first_data.get("meta", {}).get("count", 0)
        total_pages = max(1, -(-total_count // page_size))  # ceil division

        page_items = first_data.get("data", [])
        fetched_page = 1
        lo, hi = 1, total_pages
        while lo <= hi:
            mid = (lo + hi) // 2
            if mid != fetched_page:
                params["page[number]"] = mid
                response = requests.get(url, params=params, timeout=request_timeout)
                response.raise_for_status()
                page_items = response.json().get("data", [])
                fetched_page = mid
            if not page_items:
                hi = mid - 1
                continue
            if query_upper < symbol_of(page_items[0]):
                hi = mid - 1
            elif query_upper > symbol_of(page_items[-1]):
                lo = mid + 1
            else:
                return page_items
        return []

    def _search_cell_lines(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search cell lines by name or identifier.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # Fix-R19C-3: same root cause as _search_genes -- filter[model]
            # doesn't work on this API (confirmed live: identical,
            # unfiltered results regardless of filter value), and
            # `model_name`/`tissue`/`cancer_type` aren't real attributes on
            # the model resource (it only has `names`, a list). The
            # `/models` endpoint DOES support `sort=names` though
            # (confirmed live), so binary-search the ~2266-model catalog by
            # name the same way _search_genes does for the gene catalog.
            url = f"{DEPMAP_BASE_URL}/models"
            params = {"sort": "names", "page[size]": 500, "page[number]": 1}
            query_upper = query.upper()
            # Several sequential round-trips; give each request more headroom
            # than the tool's default (same rationale as _search_genes).
            page_items = self._find_catalog_page(
                url, params, query_upper, _model_symbol, max(self.timeout, 45)
            )

            cell_lines = []
            for item in page_items:
                names = item.get("attributes", {}).get("names") or []
                name = names[0] if names else None
                if name and (
                    name.upper() == query_upper or name.upper().startswith(query_upper)
                ):
                    cell_lines.append(
                        {
                            "model_id": item.get("id"),
                            "model_name": name,
                            "exact_match": name.upper() == query_upper,
                        }
                    )
            cell_lines.sort(key=lambda c: (not c["exact_match"], c["model_name"]))

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "cell_lines": cell_lines,
                    "count": len(cell_lines),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_gene_dependencies(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get CRISPR gene dependency data.

        Returns gene effect scores indicating essentiality in cancer cell lines.
        Negative scores indicate the gene is essential (cell death upon knockout).
        """
        gene_symbol = arguments.get("gene_symbol")
        arguments.get("model_id")

        if not gene_symbol:
            return {"status": "error", "error": "gene_symbol parameter is required"}

        try:
            # Use DepMap_search_genes internally for reliable matching
            search_result = self._search_genes({"query": gene_symbol})

            if search_result.get("status") != "success":
                return search_result

            genes = search_result.get("data", {}).get("genes", [])
            exact_matches = [g for g in genes if g.get("exact_match")]
            matched_gene = exact_matches[0] if exact_matches else None

            if matched_gene is None and genes:
                # No exact match — report candidates
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "candidates": genes[:5],
                        "warning": (
                            f"No exact match for '{gene_symbol}'. "
                            f"Similar: {[g['symbol'] for g in genes[:5]]}. "
                            "Use DepMap_search_genes for disambiguation."
                        ),
                    },
                }

            if matched_gene is None:
                return {
                    "status": "success",
                    "data": {
                        "gene_symbol": gene_symbol,
                        "exact_match": None,
                        "message": (
                            f"Gene '{gene_symbol}' not found in DepMap. "
                            "The Sanger Cell Model Passports API has "
                            "limited gene search capabilities."
                        ),
                    },
                }

            return {
                "status": "success",
                "data": {
                    "gene_symbol": gene_symbol,
                    "matched_gene": matched_gene,
                    "note": (
                        "Gene effect scores: negative = essential "
                        "(cell death upon knockout), zero = no effect, "
                        "positive = growth advantage. "
                        "Full dependency profiles at depmap.org."
                    ),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for genes in DepMap by symbol.

        The Sanger Cell Model Passports API gene filter is limited,
        so this method fetches sorted gene batches and filters client-side.
        """
        query = arguments.get("query")

        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            # Fix-R19C-1: the Sanger API's filter[gene] param doesn't work
            # for exact symbol matching (confirmed live: it silently
            # returns an unrelated, seemingly-arbitrary page of genes
            # regardless of the filter value). The catalog has ~45,751
            # genes; the previous "scan up to 5 pages of 100" approach only
            # ever covered the first ~1% alphabetically, so any gene not
            # starting with A/B (e.g. KRAS, TP53, EGFR) was always
            # reported "not found" -- confirmed live for all three.
            # Results are sorted by symbol, so binary-search the pages by
            # comparing the query against each page's first/last symbol
            # instead of scanning linearly from page 1.
            url = f"{DEPMAP_BASE_URL}/genes"
            params = {"sort": "symbol", "page[size]": 1000, "page[number]": 1}
            query_upper = query.upper()
            # Binary search makes several sequential round-trips (~6 for the
            # full 45k-gene catalog); this API is occasionally slow on an
            # individual request (confirmed live, one page took 22s), so
            # give each request more headroom than the tool's default.
            page_items = self._find_catalog_page(
                url, params, query_upper, _gene_symbol, max(self.timeout, 45)
            )

            genes = []
            for item in page_items:
                attrs = item.get("attributes", {})
                symbol = attrs.get("symbol", "")
                # Check for exact or prefix match
                if symbol.upper() == query_upper or symbol.upper().startswith(
                    query_upper
                ):
                    genes.append(
                        {
                            "gene_id": item.get("id"),
                            "symbol": symbol,
                            "name": attrs.get("name"),
                            "hgnc_id": attrs.get("hgnc_id"),
                            "ensembl_id": attrs.get("ensembl_gene_id"),
                            "exact_match": (symbol.upper() == query_upper),
                        }
                    )

            # Sort: exact matches first
            genes.sort(
                key=lambda g: (
                    not g["exact_match"],
                    g.get("symbol", ""),
                )
            )

            if not genes:
                return {
                    "status": "success",
                    "data": {
                        "query": query,
                        "genes": [],
                        "count": 0,
                        "note": (
                            f"Gene '{query}' not found in DepMap "
                            "gene catalog. The Sanger Cell Model "
                            "Passports API has limited gene search. "
                            "Try using an Ensembl ID or check "
                            "depmap.org directly."
                        ),
                    },
                }

            return {
                "status": "success",
                "data": {
                    "query": query,
                    "genes": genes[:20],
                    "count": len(genes),
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"DepMap API request failed: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _get_drug_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug sensitivity data for cell lines.

        Returns IC50/AUC values for drug-cell line combinations.
        """
        drug_name = arguments.get("drug_name")
        model_id = arguments.get("model_id")

        if not drug_name and not model_id:
            return {
                "status": "error",
                "error": "Either drug_name or model_id is required",
            }

        try:
            # Query drugs endpoint
            url = f"{DEPMAP_BASE_URL}/drugs"
            params = {"page[size]": 20}

            if drug_name:
                params["filter[drug]"] = f"drug_name:{drug_name}"

            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            drugs = []
            for item in data.get("data", []):
                attrs = item.get("attributes", {})
                drugs.append(
                    {
                        "drug_id": item.get("id"),
                        "drug_name": attrs.get("drug_name"),
                        "synonyms": attrs.get("synonyms"),
                        "targets": attrs.get("targets"),
                        "target_pathway": attrs.get("target_pathway"),
                    }
                )

            return {
                "status": "success",
                "data": {
                    "query": drug_name or model_id,
                    "drugs": drugs,
                    "count": len(drugs),
                    "note": "Drug sensitivity data (IC50, AUC) available through DepMap portal.",
                },
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"DepMap API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"DepMap API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}
