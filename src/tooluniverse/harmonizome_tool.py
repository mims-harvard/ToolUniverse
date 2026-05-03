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

        # Extract gene set names (can be large, limit to first 50)
        gene_sets_raw = data.get("geneSets", [])
        gene_set_limit = arguments.get("gene_set_limit") or 50
        gene_sets = [
            {"name": gs.get("name", "").split("/")[0]}
            for gs in gene_sets_raw[:gene_set_limit]
        ]

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
            },
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "dataset_name": dataset_name,
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

        limit = arguments.get("limit") or 20

        if entity_type == "gene":
            # For gene search, try exact lookup first, then suggest API
            results = []
            try:
                gene_url = f"{HARMONIZOME_BASE_URL}/gene/{query}"
                gene_resp = requests.get(gene_url, timeout=self.timeout)
                if gene_resp.status_code == 200:
                    g = gene_resp.json()
                    if "symbol" in g:
                        results.append(
                            {
                                "symbol": g.get("symbol"),
                                "name": g.get("name"),
                                "ncbi_entrez_gene_id": g.get("ncbiEntrezGeneId"),
                            }
                        )
            except Exception:
                pass
            # Also get suggestions
            try:
                suggest_url = f"{HARMONIZOME_BASE_URL}/suggest"
                suggest_resp = requests.get(
                    suggest_url, params={"q": query}, timeout=self.timeout
                )
                if suggest_resp.status_code == 200:
                    suggestions = suggest_resp.json()
                    if isinstance(suggestions, list):
                        # Try top suggestions as gene symbols
                        for s in suggestions[:10]:
                            if len(results) >= limit:
                                break
                            if any(r.get("symbol") == s for r in results):
                                continue
                            try:
                                g_url = f"{HARMONIZOME_BASE_URL}/gene/{s}"
                                g_resp = requests.get(g_url, timeout=self.timeout)
                                if g_resp.status_code == 200:
                                    g = g_resp.json()
                                    if "symbol" in g:
                                        results.append(
                                            {
                                                "symbol": g.get("symbol"),
                                                "name": g.get("name"),
                                                "ncbi_entrez_gene_id": g.get(
                                                    "ncbiEntrezGeneId"
                                                ),
                                            }
                                        )
                            except Exception:
                                continue
            except Exception:
                pass
            return {
                "status": "success",
                "data": results[:limit],
                "metadata": {
                    "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                    "entity_type": "gene",
                    "query": query,
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
            return {
                "status": "success",
                "data": matches[:limit],
                "metadata": {
                    "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                    "entity_type": "dataset",
                    "query": query,
                    "total_matches": len(matches),
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
        return {
            "status": "success",
            "data": suggestions[:limit],
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "entity_type": "attribute",
                "query": query,
                "total_suggestions": len(suggestions),
            },
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for genes by keyword in Harmonizome."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query is required (e.g., 'kinase', 'tumor suppressor')",
            }

        limit = arguments.get("limit") or 20
        url = f"{HARMONIZOME_BASE_URL}/gene"
        params = {"search": query}

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entities = data.get("entities", [])
        genes = [
            {"symbol": e.get("symbol"), "href": e.get("href")} for e in entities[:limit]
        ]

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "source": "Harmonizome (maayanlab.cloud/Harmonizome)",
                "query": query,
                "total_results": data.get("count", len(genes)),
            },
        }
