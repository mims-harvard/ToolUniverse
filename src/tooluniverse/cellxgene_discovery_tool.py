# cellxgene_discovery_tool.py
"""
CellxGene Discovery API tool for ToolUniverse.

Provides access to the CZI CellxGene Discovery API for browsing and searching
single-cell RNA-seq datasets and curated collections. Contains 2,000+ datasets
across tissues, diseases, and organisms with cell-type annotations.

API: https://api.cellxgene.cziscience.com/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool


CXG_BASE_URL = "https://api.cellxgene.cziscience.com"


class CellxGeneDiscoveryTool(BaseTool):
    """
    Tool for CZI CellxGene Discovery API providing access to single-cell
    RNA-seq datasets and curated collections.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "list_collections")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CellxGene Discovery API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {"error": f"CellxGene Discovery API timed out after {self.timeout}s"}
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to CellxGene Discovery API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"Collection/dataset not found: {arguments.get('collection_id', '')}"
                }
            return {"error": f"CellxGene Discovery API HTTP error: {code}"}
        except Exception as e:
            return {"error": f"Unexpected error querying CellxGene Discovery: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "list_collections":
            return self._list_collections(arguments)
        elif self.endpoint == "get_collection":
            return self._get_collection(arguments)
        elif self.endpoint == "search_datasets":
            return self._search_datasets(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    def _list_collections(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List curated single-cell collections."""
        limit = min(arguments.get("limit", 20), 100)

        url = f"{CXG_BASE_URL}/curation/v1/collections"
        params = {"visibility": "PUBLIC"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        collections = response.json()

        total = len(collections)
        results = []
        for c in collections[:limit]:
            datasets = c.get("datasets", [])
            total_cells = sum(
                ds.get("cell_count", 0) for ds in datasets if ds.get("cell_count")
            )
            results.append(
                {
                    "collection_id": c.get("collection_id"),
                    "name": c.get("name"),
                    "description": c.get("description", "")[:200]
                    if c.get("description")
                    else None,
                    "doi": c.get("doi"),
                    "contact_name": c.get("contact_name"),
                    "curator_name": c.get("curator_name"),
                    "consortia": c.get("consortia"),
                    "dataset_count": len(datasets),
                    "total_cells": total_cells,
                    "created_at": c.get("created_at"),
                }
            )

        return {
            "data": {
                "total_collections": total,
                "returned": len(results),
                "collections": results,
            },
            "metadata": {
                "source": "CZI CellxGene Discovery",
                "visibility": "PUBLIC",
            },
        }

    def _get_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed collection information with datasets."""
        collection_id = arguments.get("collection_id", "")
        if not collection_id:
            return {"error": "collection_id is required (UUID format)"}

        url = f"{CXG_BASE_URL}/curation/v1/collections/{collection_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        c = response.json()

        datasets = []
        for ds in c.get("datasets", []):
            # Extract tissue/disease/organism labels
            tissues = [t.get("label") for t in ds.get("tissue", []) if t.get("label")]
            diseases = [d.get("label") for d in ds.get("disease", []) if d.get("label")]
            organisms = [
                o.get("label") for o in ds.get("organism", []) if o.get("label")
            ]
            cell_types = [
                ct.get("label") for ct in ds.get("cell_type", []) if ct.get("label")
            ]
            assays = [a.get("label") for a in ds.get("assay", []) if a.get("label")]

            datasets.append(
                {
                    "dataset_id": ds.get("dataset_id"),
                    "name": ds.get("title") or ds.get("name"),
                    "cell_count": ds.get("cell_count"),
                    "tissues": tissues,
                    "diseases": diseases,
                    "organisms": organisms,
                    "cell_types": cell_types[:20],  # Limit long lists
                    "assays": assays,
                    "is_primary_data": ds.get("is_primary_data"),
                }
            )

        return {
            "data": {
                "collection_id": c.get("collection_id"),
                "name": c.get("name"),
                "description": c.get("description"),
                "doi": c.get("doi"),
                "contact_name": c.get("contact_name"),
                "links": c.get("links"),
                "dataset_count": len(datasets),
                "datasets": datasets,
            },
            "metadata": {
                "source": "CZI CellxGene Discovery",
                "collection_id": collection_id,
            },
        }

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search single-cell datasets by tissue, disease, or organism."""
        tissue = arguments.get("tissue", "")
        disease = arguments.get("disease", "")
        organism = arguments.get("organism", "")
        cell_type = arguments.get("cell_type", "")
        limit = min(arguments.get("limit", 20), 100)

        if not any([tissue, disease, organism, cell_type]):
            return {
                "error": "At least one search parameter required: tissue, disease, organism, or cell_type"
            }

        # Fetch full dataset index and filter
        url = f"{CXG_BASE_URL}/dp/v1/datasets/index"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        all_datasets = response.json()

        # Filter datasets
        filtered = all_datasets
        if tissue:
            tissue_lower = tissue.lower()
            filtered = [
                d
                for d in filtered
                if any(
                    tissue_lower in t.get("label", "").lower()
                    for t in d.get("tissue", [])
                )
            ]
        if disease:
            disease_lower = disease.lower()
            filtered = [
                d
                for d in filtered
                if any(
                    disease_lower in dis.get("label", "").lower()
                    for dis in d.get("disease", [])
                )
            ]
        if organism:
            org_lower = organism.lower()
            filtered = [
                d
                for d in filtered
                if any(
                    org_lower in o.get("label", "").lower()
                    for o in d.get("organism", [])
                )
            ]
        if cell_type:
            ct_lower = cell_type.lower()
            filtered = [
                d
                for d in filtered
                if any(
                    ct_lower in ct.get("label", "").lower()
                    for ct in d.get("cell_type", [])
                )
            ]

        total = len(filtered)
        # Sort by cell count descending
        filtered.sort(key=lambda x: x.get("cell_count", 0) or 0, reverse=True)
        filtered = filtered[:limit]

        results = []
        for d in filtered:
            tissues = [t.get("label") for t in d.get("tissue", []) if t.get("label")]
            diseases = [
                dis.get("label") for dis in d.get("disease", []) if dis.get("label")
            ]
            organisms = [
                o.get("label") for o in d.get("organism", []) if o.get("label")
            ]
            results.append(
                {
                    "dataset_id": d.get("id"),
                    "name": d.get("name", ""),
                    "cell_count": d.get("cell_count"),
                    "collection_id": d.get("collection_id"),
                    "tissues": tissues,
                    "diseases": diseases,
                    "organisms": organisms,
                    "explorer_url": d.get("explorer_url"),
                }
            )

        return {
            "data": {
                "total_matching": total,
                "returned": len(results),
                "datasets": results,
            },
            "metadata": {
                "source": "CZI CellxGene Discovery",
                "filters": {
                    "tissue": tissue or None,
                    "disease": disease or None,
                    "organism": organism or None,
                    "cell_type": cell_type or None,
                },
                "total_datasets_searched": len(all_datasets),
            },
        }
