# dgidb_tool.py
"""
DGIdb (Drug Gene Interaction Database) API tool for ToolUniverse.

DGIdb is a comprehensive database of drug-gene interactions and
druggable genes aggregated from multiple sources.

API Documentation: https://www.dgidb.org/api
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for DGIdb GraphQL API
DGIDB_BASE_URL = "https://dgidb.org/api/graphql"


@register_tool("DGIdbTool")
class DGIdbTool(BaseTool):
    """
    Tool for querying DGIdb REST API.

    DGIdb provides drug-gene interaction data including:
    - Drug-gene interactions from 30+ sources
    - Druggability annotations
    - Gene categories (kinase, ion channel, etc.)

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "interactions")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the DGIdb API call."""
        operation = self.operation

        if operation == "interactions":
            return self._get_interactions(arguments)
        elif operation == "genes":
            return self._get_genes(arguments)
        elif operation == "drugs":
            return self._get_drugs(arguments)
        elif operation == "categories":
            return self._get_gene_categories(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _get_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug-gene interactions for genes using GraphQL.
        """
        genes = (
            arguments.get("genes")
            or arguments.get("gene_name")
            or arguments.get("gene")
            or []
        )

        if not genes:
            return {
                "status": "error",
                "error": "genes parameter is required (list of gene symbols)",
            }

        if isinstance(genes, str):
            genes = [g.strip() for g in genes.split(",")]

        # Feature-68A-001: normalize interaction_types/interaction_sources for client-side filtering
        interaction_types = arguments.get("interaction_types", [])
        interaction_sources = arguments.get("interaction_sources", [])
        if isinstance(interaction_types, str):
            interaction_types = [t.strip() for t in interaction_types.split(",")]
        if isinstance(interaction_sources, str):
            interaction_sources = [s.strip() for s in interaction_sources.split(",")]
        types_lower = [t.lower() for t in interaction_types]
        sources_lower = [s.lower() for s in interaction_sources]

        # GraphQL query for interactions
        query = """
        query GetInteractions($genes: [String!]!) {
            genes(names: $genes) {
                nodes {
                    name
                    longName
                    interactions {
                        drug {
                            name
                            conceptId
                        }
                        interactionTypes {
                            type
                        }
                        sources {
                            fullName
                        }
                    }
                }
            }
        }
        """

        try:
            response = requests.post(
                DGIDB_BASE_URL,
                json={"query": query, "variables": {"genes": genes}},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Feature-68A-001: apply client-side filtering for interaction_types/sources
            if types_lower or sources_lower:
                nodes = data.get("data", {}).get("genes", {}).get("nodes", [])
                for node in nodes:
                    filtered = []
                    for interaction in node.get("interactions", []):
                        if types_lower:
                            int_types = [
                                t.get("type", "").lower()
                                for t in interaction.get("interactionTypes", [])
                            ]
                            if not any(t in int_types for t in types_lower):
                                continue
                        if sources_lower:
                            int_srcs = [
                                s.get("fullName", "").lower()
                                for s in interaction.get("sources", [])
                            ]
                            if not any(s in int_srcs for s in sources_lower):
                                continue
                        filtered.append(interaction)
                    node["interactions"] = filtered

            # Feature-68A-002: wrap in status envelope consistent with other ToolUniverse tools
            return {"status": "success", "data": data}
        except requests.RequestException as e:
            return {"status": "error", "error": f"DGIdb API request failed: {str(e)}"}

    def _get_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene information including druggability using GraphQL.
        """
        genes = (
            arguments.get("genes")
            or arguments.get("gene_name")
            or arguments.get("gene")
            or []
        )

        if not genes:
            return {"status": "error", "error": "genes parameter is required"}

        if isinstance(genes, str):
            genes = [g.strip() for g in genes.split(",")]

        query = """
        query GetGenes($genes: [String!]!) {
            genes(names: $genes) {
                nodes {
                    name
                    longName
                    geneCategories {
                        name
                    }
                }
            }
        }
        """

        try:
            response = requests.post(
                DGIDB_BASE_URL,
                json={"query": query, "variables": {"genes": genes}},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            # Feature-68A-002: wrap in status envelope
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"DGIdb API request failed: {str(e)}"}

    def _get_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get drug information using GraphQL.
        """
        drugs = arguments.get("drugs", [])

        if not drugs:
            return {"status": "error", "error": "drugs parameter is required"}

        if isinstance(drugs, str):
            drugs = [d.strip() for d in drugs.split(",")]

        query = """
        query GetDrugs($drugs: [String!]!) {
            drugs(names: $drugs) {
                nodes {
                    name
                    conceptId
                    approved
                }
            }
        }
        """

        try:
            response = requests.post(
                DGIDB_BASE_URL,
                json={"query": query, "variables": {"drugs": drugs}},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            # Feature-68A-002: wrap in status envelope
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"DGIdb API request failed: {str(e)}"}

    def _get_gene_categories(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get gene categories (druggability annotations) using GraphQL.
        """
        genes = (
            arguments.get("genes")
            or arguments.get("gene_name")
            or arguments.get("gene")
            or []
        )

        if not genes:
            return {"status": "error", "error": "genes parameter is required"}

        if isinstance(genes, str):
            genes = [g.strip() for g in genes.split(",")]

        query = """
        query GetGeneCategories($genes: [String!]!) {
            genes(names: $genes) {
                nodes {
                    name
                    longName
                    geneCategories {
                        name
                    }
                }
            }
        }
        """

        try:
            response = requests.post(
                DGIDB_BASE_URL,
                json={"query": query, "variables": {"genes": genes}},
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            # Feature-68A-002: wrap in status envelope
            return {"status": "success", "data": response.json()}
        except requests.RequestException as e:
            return {"status": "error", "error": f"DGIdb API request failed: {str(e)}"}
