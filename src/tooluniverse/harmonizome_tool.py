# harmonizome_tool.py
"""
Harmonizome tool for ToolUniverse.

Harmonizome (Ma'ayan Lab, Mount Sinai) integrates data from 100+ genomics
datasets covering gene expression, protein interactions, pathways, diseases,
drug targets, and more into a unified gene-centric resource.

API: https://maayanlab.cloud/Harmonizome/api/1.0/
No authentication required.
"""

import requests
from typing import Dict, Any
from urllib.parse import quote
from .base_tool import BaseTool
from .tool_registry import register_tool

HARMONIZOME_BASE_URL = "https://maayanlab.cloud/Harmonizome/api/1.0"


@register_tool("HarmonizomeTool")
class HarmonizomeTool(BaseTool):
    """
    Tool for querying Harmonizome gene and dataset information.

    Supports:
    - Gene details (symbol, name, description, synonyms, proteins)
    - Dataset catalog (100+ integrated genomics datasets)

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_gene")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Harmonizome API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Harmonizome API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Harmonizome API"}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Gene not found in Harmonizome. Check the gene symbol.",
                }
            return {"status": "error", "error": f"Harmonizome API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        handlers = {
            "get_gene": self._get_gene,
            "list_datasets": self._list_datasets,
            "get_dataset": self._get_dataset,
            "search": self._search,
            "search_genes": self._search_genes,
            "get_gene_set_members": self._get_gene_set_members,
        }
        handler = handlers.get(self.endpoint)
        if handler:
            return handler(arguments)
        return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene details from Harmonizome."""
        gene_symbol = arguments.get("gene_symbol", "")
        if not gene_symbol:
            return {
                "status": "error",
                "error": "gene_symbol is required (e.g., 'TP53').",
            }

        url = f"{HARMONIZOME_BASE_URL}/gene/{gene_symbol}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        # Check if we got an error response
        if data.get("status") == 404 or "message" in data:
            return {
                "status": "error",
                "error": f"Gene '{gene_symbol}' not found: {data.get('message', 'unknown')}",
            }

        proteins = []
        for p in data.get("proteins", []):
            proteins.append(
                {
                    "symbol": p.get("symbol"),
                    "href": p.get("href"),
                }
            )

        return {
            "status": "success",
            "data": {
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "ncbi_entrez_gene_id": data.get("ncbiEntrezGeneId"),
                "ncbi_entrez_gene_url": data.get("ncbiEntrezGeneUrl"),
                "description": data.get("description"),
                "synonyms": data.get("synonyms", []),
                "proteins": proteins,
            },
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
            },
        }

    def _list_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available Harmonizome datasets."""
        url = f"{HARMONIZOME_BASE_URL}/dataset"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entities = data.get("entities", [])
        datasets = []
        for e in entities:
            datasets.append(
                {
                    "name": e.get("name"),
                    "href": e.get("href"),
                }
            )

        return {
            "status": "success",
            "data": datasets,
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "total_datasets": len(datasets),
            },
        }

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific Harmonizome dataset."""
        dataset_name = arguments.get("dataset_name", "")
        if not dataset_name:
            return {
                "status": "error",
                "error": "dataset_name is required (e.g., 'CTD Gene-Disease Associations'). Use Harmonizome_list_datasets to find names.",
            }
        gene_set_limit = arguments.get("gene_set_limit", 50)
        gene_set_offset = arguments.get("gene_set_offset", 0)
        if gene_set_limit is None:
            gene_set_limit = 50
        if gene_set_offset is None:
            gene_set_offset = 0
        if (
            isinstance(gene_set_limit, bool)
            or not isinstance(gene_set_limit, int)
            or not 1 <= gene_set_limit <= 1000
        ):
            return {
                "status": "error",
                "error": "gene_set_limit must be an integer between 1 and 1000",
            }
        if (
            isinstance(gene_set_offset, bool)
            or not isinstance(gene_set_offset, int)
            or gene_set_offset < 0
        ):
            return {
                "status": "error",
                "error": "gene_set_offset must be a non-negative integer",
            }

        # URL-encode: spaces become + in Harmonizome API
        encoded_name = dataset_name.replace(" ", "+")
        url = f"{HARMONIZOME_BASE_URL}/dataset/{encoded_name}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        if "message" in data:
            return {
                "status": "error",
                "error": f"Dataset not found: {data.get('message', dataset_name)}",
            }

        # Extract a recoverable page of gene-set names (some datasets have
        # thousands, e.g. CTD disease associations).
        gene_sets_raw = data.get("geneSets", [])
        gene_sets = [
            {"name": gs.get("name", "").split("/")[0]}
            for gs in gene_sets_raw[gene_set_offset : gene_set_offset + gene_set_limit]
        ]
        next_gene_set_offset = gene_set_offset + len(gene_sets)
        has_more_gene_sets = next_gene_set_offset < len(gene_sets_raw)

        return {
            "status": "success",
            "data": {
                "name": data.get("name"),
                "description": data.get("description"),
                "association": data.get("association"),
                "measurement": data.get("measurement"),
                "attribute_type": data.get("attributeType"),
                "attribute_group": data.get("attributeGroup"),
                "dataset_group": data.get("datasetGroup"),
                "pubmed_ids": data.get("pubMedIds", []),
                "gene_sets": gene_sets,
                "total_gene_sets": len(gene_sets_raw),
                "gene_sets_returned": len(gene_sets),
                "gene_set_limit": gene_set_limit,
                "gene_set_offset": gene_set_offset,
                "has_more_gene_sets": has_more_gene_sets,
                "next_gene_set_offset": (
                    next_gene_set_offset if has_more_gene_sets else None
                ),
            },
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "dataset_name": dataset_name,
                "total_gene_sets": len(gene_sets_raw),
                "gene_sets_returned": len(gene_sets),
                "gene_set_limit": gene_set_limit,
                "gene_set_offset": gene_set_offset,
                "has_more_gene_sets": has_more_gene_sets,
                "next_gene_set_offset": (
                    next_gene_set_offset if has_more_gene_sets else None
                ),
            },
        }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Harmonizome for genes, datasets, or attributes by keyword."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required."}

        entity_type = arguments.get("entity_type", "gene")
        if entity_type not in ("gene", "dataset", "attribute"):
            return {
                "status": "error",
                "error": f"entity_type must be 'gene', 'dataset', or 'attribute', got '{entity_type}'",
            }

        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 100",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}

        if entity_type == "gene":
            # For gene search, try exact lookup first, then suggest API
            results = []
            try:
                gene_url = f"{HARMONIZOME_BASE_URL}/gene/{quote(query, safe='')}"
                gene_resp = requests.get(gene_url, timeout=self.timeout)
                if gene_resp.status_code == 200:
                    g = gene_resp.json()
                    if (
                        isinstance(g, dict)
                        and g.get("status") in (400, 404)
                        and not g.get("symbol")
                    ):
                        g = None
                    if g is None:
                        pass
                    elif not isinstance(g, dict) or not g.get("symbol"):
                        return {
                            "status": "error",
                            "error": "Harmonizome exact gene lookup returned malformed data",
                            "search_stage": "exact_gene_lookup",
                        }
                    else:
                        results.append(
                            {
                                "symbol": g.get("symbol"),
                                "name": g.get("name"),
                                "ncbi_entrez_gene_id": g.get("ncbiEntrezGeneId"),
                            }
                        )
                elif gene_resp.status_code != 404:
                    return {
                        "status": "error",
                        "error": f"Harmonizome exact gene lookup returned HTTP {gene_resp.status_code}",
                        "search_stage": "exact_gene_lookup",
                    }
            except Exception as exc:
                return {
                    "status": "error",
                    "error": f"Harmonizome exact gene lookup failed: {exc}",
                    "search_stage": "exact_gene_lookup",
                }
            # Also get suggestions
            try:
                suggest_url = f"{HARMONIZOME_BASE_URL}/suggest"
                suggest_resp = requests.get(
                    suggest_url, params={"q": query}, timeout=self.timeout
                )
                if suggest_resp.status_code != 200:
                    return {
                        "status": "error",
                        "error": f"Harmonizome suggestion lookup returned HTTP {suggest_resp.status_code}",
                        "search_stage": "suggestion_lookup",
                    }
                suggestions = suggest_resp.json()
                if not isinstance(suggestions, list) or not all(
                    isinstance(item, str) for item in suggestions
                ):
                    return {
                        "status": "error",
                        "error": "Harmonizome suggestion lookup returned malformed data",
                        "search_stage": "suggestion_lookup",
                    }
            except Exception as exc:
                return {
                    "status": "error",
                    "error": f"Harmonizome suggestion lookup failed: {exc}",
                    "search_stage": "suggestion_lookup",
                }

            suggestions_examined = 0
            rejected_non_gene_suggestions = 0
            # /suggest is a mixed-entity endpoint. Resolve enough candidates
            # to fill the requested page plus one real-gene lookahead.
            for suggestion in suggestions:
                if len(results) >= offset + limit + 1:
                    break
                suggestions_examined += 1
                if any(r.get("symbol") == suggestion for r in results):
                    continue
                g_url = f"{HARMONIZOME_BASE_URL}/gene/{quote(suggestion, safe='')}"
                try:
                    g_resp = requests.get(g_url, timeout=self.timeout)
                    if g_resp.status_code == 404:
                        rejected_non_gene_suggestions += 1
                        continue
                    if g_resp.status_code != 200:
                        return {
                            "status": "error",
                            "error": (
                                "Harmonizome suggestion resolution returned "
                                f"HTTP {g_resp.status_code} for {suggestion!r}"
                            ),
                            "search_stage": "suggestion_gene_resolution",
                            "candidate": suggestion,
                        }
                    g = g_resp.json()
                except Exception as exc:
                    return {
                        "status": "error",
                        "error": f"Harmonizome suggestion resolution failed for {suggestion!r}: {exc}",
                        "search_stage": "suggestion_gene_resolution",
                        "candidate": suggestion,
                    }
                if (
                    isinstance(g, dict)
                    and g.get("status") in (400, 404)
                    and not g.get("symbol")
                ):
                    rejected_non_gene_suggestions += 1
                    continue
                if not isinstance(g, dict) or not g.get("symbol"):
                    return {
                        "status": "error",
                        "error": f"Harmonizome returned malformed gene data for {suggestion!r}",
                        "search_stage": "suggestion_gene_resolution",
                        "candidate": suggestion,
                    }
                if any(r.get("symbol") == g["symbol"] for r in results):
                    continue
                results.append(
                    {
                        "symbol": g.get("symbol"),
                        "name": g.get("name"),
                        "ncbi_entrez_gene_id": g.get("ncbiEntrezGeneId"),
                    }
                )

            page = results[offset : offset + limit]
            has_more = len(results) > offset + limit
            suggestions_exhausted = suggestions_examined == len(suggestions)
            return {
                "status": "success",
                "data": page,
                "metadata": {
                    "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                    "entity_type": "gene",
                    "query": query,
                    "returned": len(page),
                    "offset": offset,
                    "limit": limit,
                    "has_more": has_more,
                    "next_offset": offset + len(page) if has_more else None,
                    "total_results": len(results) if suggestions_exhausted else None,
                    "total_results_known": suggestions_exhausted,
                    "suggestions_total": len(suggestions),
                    "suggestions_examined": suggestions_examined,
                    "rejected_non_gene_suggestions": rejected_non_gene_suggestions,
                    "suggestions_exhausted": suggestions_exhausted,
                    "result_set_complete": bool(
                        offset == 0
                        and suggestions_exhausted
                        and len(page) == len(results)
                    ),
                    "query_semantics": (
                        "exact symbol plus mixed suggestions that resolve to Harmonizome genes"
                    ),
                },
            }

        if entity_type == "dataset":
            # Filter the dataset list by query
            ds_url = f"{HARMONIZOME_BASE_URL}/dataset"
            ds_resp = requests.get(ds_url, timeout=self.timeout)
            ds_resp.raise_for_status()
            ds_data = ds_resp.json()
            query_lower = query.lower()
            matches = [
                {"name": e.get("name"), "href": e.get("href")}
                for e in ds_data.get("entities", [])
                if query_lower in (e.get("name") or "").lower()
            ]
            page = matches[offset : offset + limit]
            next_offset = offset + len(page)
            has_more = next_offset < len(matches)
            return {
                "status": "success",
                "data": page,
                "metadata": {
                    "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                    "entity_type": "dataset",
                    "query": query,
                    "total_matches": len(matches),
                    "returned": len(page),
                    "offset": offset,
                    "has_more": has_more,
                    "next_offset": next_offset if has_more else None,
                },
            }

        # attribute search: use suggest endpoint
        suggest_url = f"{HARMONIZOME_BASE_URL}/suggest"
        suggest_resp = requests.get(
            suggest_url, params={"q": query}, timeout=self.timeout
        )
        suggest_resp.raise_for_status()
        suggestions = suggest_resp.json()
        if not isinstance(suggestions, list):
            suggestions = []
        page = suggestions[offset : offset + limit]
        next_offset = offset + len(page)
        has_more = next_offset < len(suggestions)
        return {
            "status": "success",
            "data": page,
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "entity_type": "attribute",
                "query": query,
                "total_suggestions": len(suggestions),
                "returned": len(page),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
            },
        }

    def _get_gene_set_members(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve Harmonizome gene-set members or per-gene associations.

        Two modes via `mode`:
        - "gene_set" (default): member genes of a curated attribute set, each with
          thresholdValue + standardizedValue. Requires `attribute` and `dataset`.
          Endpoint: /gene_set/{attribute}/{dataset}
        - "gene": the full per-gene association table across all datasets.
          Requires `gene_symbol`. Endpoint: /gene/{symbol}?showAssociations=true
        """
        mode = arguments.get("mode", "gene_set")
        limit = max(1, int(arguments.get("limit") or 100))
        offset = max(0, int(arguments.get("offset", 0)))

        def _encode(value: str) -> str:
            # Harmonizome path encoding: spaces -> '+'. Other reserved chars are
            # already correctly URL-encoded in the hrefs the API returns.
            return requests.utils.quote(value, safe="+/").replace("%20", "+")

        if mode == "gene":
            gene_symbol = arguments.get("gene_symbol", "")
            if not gene_symbol:
                return {
                    "status": "error",
                    "error": "gene_symbol is required for mode='gene' (e.g., 'DTD2').",
                }
            url = f"{HARMONIZOME_BASE_URL}/gene/{requests.utils.quote(gene_symbol, safe='')}"
            response = requests.get(
                url, params={"showAssociations": "true"}, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == 404 or "message" in data:
                return {
                    "status": "error",
                    "error": f"Gene '{gene_symbol}' not found: {data.get('message', 'unknown')}",
                }
            associations_raw = data.get("associations", [])
            associations = [
                {
                    "gene_set": (a.get("geneSet") or {}).get("name"),
                    "gene_set_href": (a.get("geneSet") or {}).get("href"),
                    "threshold_value": a.get("thresholdValue"),
                    "standardized_value": a.get("standardizedValue"),
                }
                for a in associations_raw[offset : offset + limit]
            ]
            next_offset = offset + len(associations)
            has_more = next_offset < len(associations_raw)
            return {
                "status": "success",
                "data": {
                    "symbol": data.get("symbol"),
                    "name": data.get("name"),
                    "ncbi_entrez_gene_id": data.get("ncbiEntrezGeneId"),
                    "associations": associations,
                },
                "metadata": {
                    "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                    "mode": "gene",
                    "gene_symbol": gene_symbol,
                    "total_associations": len(associations_raw),
                    "returned": len(associations),
                    "offset": offset,
                    "has_more": has_more,
                    "next_offset": next_offset if has_more else None,
                },
            }

        # mode == "gene_set"
        attribute = arguments.get("attribute", "")
        dataset = arguments.get("dataset", "")
        if not attribute or not dataset:
            return {
                "status": "error",
                "error": "attribute and dataset are required for mode='gene_set' "
                "(e.g., attribute='heart', dataset='GTEx Tissue Gene Expression Profiles').",
            }
        url = f"{HARMONIZOME_BASE_URL}/gene_set/{_encode(attribute)}/{_encode(dataset)}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "message" in data:
            return {
                "status": "error",
                "error": f"Gene set not found: {data.get('message', f'{attribute}/{dataset}')}",
            }
        associations_raw = data.get("associations", [])
        members = [
            {
                "gene": (a.get("gene") or {}).get("symbol"),
                "gene_href": (a.get("gene") or {}).get("href"),
                "threshold_value": a.get("thresholdValue"),
                "standardized_value": a.get("standardizedValue"),
            }
            for a in associations_raw[offset : offset + limit]
        ]
        next_offset = offset + len(members)
        has_more = next_offset < len(associations_raw)
        return {
            "status": "success",
            "data": {
                "attribute": (data.get("attribute") or {}).get("name", attribute),
                "dataset": (data.get("dataset") or {}).get("name", dataset),
                "members": members,
            },
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "mode": "gene_set",
                "attribute": attribute,
                "dataset": dataset,
                "total_associations": len(associations_raw),
                "returned": len(members),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
            },
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve gene symbols without using the API's ignored search param."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query is required (e.g., 'kinase', 'tumor suppressor')",
            }

        result = self._search({**arguments, "entity_type": "gene"})
        if result.get("status") == "success":
            result["metadata"].update(
                {
                    "query_semantics": "exact gene symbol and symbol-like suggestions",
                    "total_results_known": result["metadata"].get(
                        "total_results_known", False
                    ),
                    "note": (
                        "Harmonizome's /gene collection endpoint ignores text-search "
                        "parameters, so this tool deliberately uses exact symbol lookup "
                        "plus gene-resolvable suggestions. Descriptive terms such as "
                        "'kinase' may return no genes instead of unrelated catalog rows."
                    ),
                }
            )
        return result
