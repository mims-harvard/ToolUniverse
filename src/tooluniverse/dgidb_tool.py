# dgidb_tool.py
"""
DGIdb (Drug Gene Interaction Database) API tool for ToolUniverse.

DGIdb is a comprehensive database of drug-gene interactions and
druggable genes aggregated from multiple sources.

API Documentation: https://www.dgidb.org/api
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for DGIdb GraphQL API
DGIDB_BASE_URL = "https://dgidb.org/api/graphql"


def _unmatched_names(
    requested: list[Any], nodes: list[Any], prefix_match: bool = False
) -> list[str]:
    """Return the requested names DGIdb returned no node for.

    Fix-R30: DGIdb's ``names:`` filter silently omits anything it cannot
    resolve -- it does not error and does not report the omission. Verified
    live against https://dgidb.org/api/graphql::

        {"genes": ["JAK1", "NOTAREALGENEXYZ", "jak2"]}
        -> {"data":{"genes":{"nodes":[{"name":"JAK2"},{"name":"JAK1"}]}}}

    so a typo or an obsolete alias vanishes from an otherwise successful
    answer. The two upstream matching modes were probed directly:

    * genes -- exact, case-insensitive (``jak2`` -> ``JAK2``, but ``JAK``,
      ``ERBB1`` and ``HER2`` all return zero nodes, so there is no prefix
      or alias resolution to allow for).
    * drugs -- case-insensitive *prefix* (``imatinib`` returns both
      ``IMATINIB`` and ``IMATINIB MESYLATE``; ``imatin`` returns the same
      pair; ``mesylate`` returns nothing). Hence ``prefix_match``.

    The caller's original spelling is echoed back, not the normalized form.
    """
    returned = [
        str(node.get("name") or "").strip().lower()
        for node in nodes
        if isinstance(node, dict)
    ]
    unmatched: list[str] = []
    for name in requested:
        key = str(name).strip().lower()
        if not key:
            continue
        if prefix_match:
            matched = any(r.startswith(key) for r in returned)
        else:
            matched = key in returned
        if not matched and name not in unmatched:
            unmatched.append(name)
    return unmatched


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

    @staticmethod
    def _envelope(
        payload: Dict[str, Any],
        collection: str,
        requested: list[Any] | None = None,
        prefix_match: bool = False,
    ) -> Dict[str, Any]:
        """Unwrap the GraphQL ``data`` key into the standard envelope.

        DGIdb's GraphQL responses are shaped ``{"data": {<collection>:
        {"nodes": [...]}}, "errors": [...]}``. Forwarding that verbatim under
        another ``data`` key produced an awkward ``data.data.<collection>``
        shape with no metadata. Unwrap one level so ``data`` holds the payload
        directly and attach a ``metadata.total`` node count.

        Fix-R30: ``requested`` is the caller's input list. Names DGIdb did
        not resolve are dropped from ``nodes`` with no trace, leaving an
        unrecognised symbol byte-indistinguishable from a real gene that
        simply has no interactions on record. When any are missing, report
        ``<collection>_requested`` and ``unmatched_<collection>`` so the two
        cases can be told apart. Both keys are omitted when everything
        matched, keeping the happy-path payload unchanged.
        """
        if payload.get("errors"):
            return {"status": "error", "error": payload["errors"]}
        inner = payload.get("data", {}) or {}
        nodes = (inner.get(collection) or {}).get("nodes", []) or []

        # Fix-R4A-8: `total` counted top-level nodes, which for the
        # interactions tools are GENES, not interactions. Querying PDCD1
        # reported total=1 beside a payload holding 68 drug-gene interactions,
        # and three genes reported total=3 against 140 -- a number that reads
        # as a truncation warning and is the one figure most likely to be
        # quoted in a summary. Name what is actually counted and add the
        # interaction total alongside it.
        interaction_total = sum(
            len(node.get("interactions") or [])
            for node in nodes
            if isinstance(node, dict)
        )
        metadata = {"total": len(nodes), f"{collection}_returned": len(nodes)}
        if interaction_total:
            metadata["interactions_total"] = interaction_total

        if requested:
            unmatched = _unmatched_names(requested, nodes, prefix_match)
            if unmatched:
                metadata[f"{collection}_requested"] = len(requested)
                metadata[f"unmatched_{collection}"] = unmatched

        return {
            "status": "success",
            "data": inner,
            "metadata": metadata,
        }

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

            return self._envelope(data, "genes", requested=genes)
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
            return self._envelope(response.json(), "genes", requested=genes)
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
            return self._envelope(
                response.json(), "drugs", requested=drugs, prefix_match=True
            )
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
            return self._envelope(response.json(), "genes", requested=genes)
        except requests.RequestException as e:
            return {"status": "error", "error": f"DGIdb API request failed: {str(e)}"}
