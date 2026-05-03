"""
BiGG Models API Tool

This tool provides access to BiGG Models database containing 85+ genome-scale
metabolic models. BiGG provides COBRA models for constraint-based metabolic modeling
and flux balance analysis.

Rate limit: 10 requests per second
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

BIGG_BASE_URL = "http://bigg.ucsd.edu/api/v2"


@register_tool("BiGGModelsTool")
class BiGGModelsTool(BaseTool):
    """
    BiGG Models API tool for metabolic modeling.

    Provides access to:
    - Genome-scale metabolic models (85+ organisms)
    - Reactions, metabolites, and genes
    - Universal reaction/metabolite databases
    - Model downloads in multiple formats
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the BiGG Models API tool."""
        for param in self.required:
            if param not in arguments or arguments[param] is None:
                return {
                    "status": "error",
                    "data": {"error": f"Missing required parameter: {param}"},
                }

        operation = arguments.get("operation")
        if not operation:
            return {
                "status": "error",
                "data": {"error": "Missing required parameter: operation"},
            }

        operation_handlers = {
            "list_models": self._list_models,
            "get_model": self._get_model,
            "get_model_reactions": self._get_model_reactions,
            "get_model_metabolites": self._get_model_metabolites,
            "get_model_genes": self._get_model_genes,
            "get_reaction": self._get_reaction,
            "get_metabolite": self._get_metabolite,
            "get_gene": self._get_gene,
            "search": self._search,
            "get_database_version": self._get_database_version,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "data": {
                    "error": f"Unknown operation: {operation}",
                    "available_operations": list(operation_handlers.keys()),
                },
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "error": f"Operation failed: {str(e)}",
                    "operation": operation,
                },
            }

    def _list_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all available metabolic models."""
        url = f"{BIGG_BASE_URL}/models"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            api_data = response.json()
            result = {
                "status": "success",
                "models": api_data.get("results", []),
                "count": api_data.get(
                    "results_count", len(api_data.get("results", []))
                ),
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"API request failed with status {response.status_code}",
                    "detail": response.text[:500],
                },
            }

    def _get_model(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details for a specific model."""
        model_id = arguments.get("model_id")

        if not model_id:
            return {"status": "error", "data": {"error": "model_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "status": "success",
                "model": response.json(),
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        elif response.status_code == 404:
            return {"status": "error", "data": {"error": f"Model {model_id} not found"}}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"API request failed with status {response.status_code}",
                    "detail": response.text[:500],
                },
            }

    def _get_model_reactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get reactions in a model."""
        model_id = arguments.get("model_id")

        if not model_id:
            return {"status": "error", "data": {"error": "model_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/reactions"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            api_data = response.json()
            reactions = api_data.get("results", api_data)
            result = {
                "status": "success",
                "reactions": reactions if isinstance(reactions, list) else [reactions],
                "count": len(reactions) if isinstance(reactions, list) else 1,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get reactions for model {model_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_model_metabolites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metabolites in a model."""
        model_id = arguments.get("model_id")

        if not model_id:
            return {"status": "error", "data": {"error": "model_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/metabolites"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            api_data = response.json()
            metabolites = api_data.get("results", api_data)
            result = {
                "status": "success",
                "metabolites": metabolites
                if isinstance(metabolites, list)
                else [metabolites],
                "count": len(metabolites) if isinstance(metabolites, list) else 1,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get metabolites for model {model_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_model_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genes in a model."""
        model_id = arguments.get("model_id")

        if not model_id:
            return {"status": "error", "data": {"error": "model_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/genes"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            api_data = response.json()
            genes = api_data.get("results", api_data)
            result = {
                "status": "success",
                "genes": genes if isinstance(genes, list) else [genes],
                "count": len(genes) if isinstance(genes, list) else 1,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get genes for model {model_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_reaction(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get reaction details."""
        model_id = arguments.get("model_id", "universal")
        reaction_id = arguments.get("reaction_id")

        if not reaction_id:
            return {"status": "error", "data": {"error": "reaction_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/reactions/{reaction_id}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "status": "success",
                "reaction": response.json(),
                "reaction_id": reaction_id,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get reaction {reaction_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_metabolite(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get metabolite details."""
        model_id = arguments.get("model_id", "universal")
        metabolite_id = arguments.get("metabolite_id")

        if not metabolite_id:
            return {"status": "error", "data": {"error": "metabolite_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/metabolites/{metabolite_id}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "status": "success",
                "metabolite": response.json(),
                "metabolite_id": metabolite_id,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get metabolite {metabolite_id}",
                    "detail": response.text[:500],
                },
            }

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get gene details from a model."""
        model_id = arguments.get("model_id")
        gene_id = arguments.get("gene_id")

        if not model_id:
            return {"status": "error", "data": {"error": "model_id is required"}}
        if not gene_id:
            return {"status": "error", "data": {"error": "gene_id is required"}}

        url = f"{BIGG_BASE_URL}/models/{model_id}/genes/{gene_id}"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {
                "status": "success",
                "gene": response.json(),
                "gene_id": gene_id,
                "model_id": model_id,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get gene {gene_id}",
                    "detail": response.text[:500],
                },
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search BiGG database."""
        query = arguments.get("query")
        search_type = arguments.get("search_type", "reactions")

        if not query:
            return {"status": "error", "data": {"error": "query is required"}}

        params = {"query": query, "search_type": search_type}

        url = f"{BIGG_BASE_URL}/search"
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            api_data = response.json()
            result = {
                "status": "success",
                "results": api_data.get("results", []),
                "count": api_data.get("results_count", 0),
                "query": query,
                "search_type": search_type,
            }
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Search failed with status {response.status_code}",
                    "detail": response.text[:500],
                },
            }

    def _get_database_version(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get BiGG database version information."""
        url = f"{BIGG_BASE_URL}/database_version"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            result = {"status": "success", **response.json()}
            return {"status": "success", "data": result}
        else:
            return {
                "status": "error",
                "data": {
                    "error": f"Failed to get database version",
                    "detail": response.text[:500],
                },
            }
