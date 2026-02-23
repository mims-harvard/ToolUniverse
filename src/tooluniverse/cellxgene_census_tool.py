"""
CELLxGENE Census API Tool

This tool provides access to single-cell RNA-seq data from the CELLxGENE Census.
The Census is a versioned container of single-cell data from CZ CELLxGENE Discover
containing 50M+ cells from human, mouse, and non-human primate cells.
"""

from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("CELLxGENECensusTool")
class CELLxGENECensusTool(BaseTool):
    """
    CELLxGENE Census API tool for accessing single-cell RNA-seq data.
    Provides access to cell metadata, gene expression, and embeddings.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        try:
            import cellxgene_census
            import tiledbsoma
        except ImportError:
            return {
                "status": "error",
                "error": "cellxgene_census package is required. Install with: pip install cellxgene-census",
            }

        try:
            operation = arguments.get("operation", "get_metadata")
            census_version = arguments.get("census_version", "stable")

            if operation == "get_census_versions":
                return self._get_census_versions()

            elif operation == "get_obs_metadata":
                return self._get_obs_metadata(arguments, census_version)

            elif operation == "get_var_metadata":
                return self._get_var_metadata(arguments, census_version)

            elif operation == "get_anndata":
                return self._get_anndata(arguments, census_version)

            elif operation == "get_presence_matrix":
                return self._get_presence_matrix(arguments, census_version)

            elif operation == "get_embeddings":
                return self._get_embeddings(arguments, census_version)

            elif operation == "download_h5ad":
                return self._download_h5ad(arguments, census_version)

            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_census_versions(self) -> Dict[str, Any]:
        """Get list of available Census versions."""
        try:
            import cellxgene_census

            versions = cellxgene_census.get_census_version_directory()
            return {"status": "success", "versions": versions}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_obs_metadata(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Get observation (cell) metadata."""
        try:
            import cellxgene_census

            organism = arguments.get("organism", "Homo sapiens")
            obs_value_filter = arguments.get("obs_value_filter")
            column_names = arguments.get("column_names")

            # Safeguard: Require filter to prevent querying 50M+ cells
            if not obs_value_filter:
                return {
                    "status": "error",
                    "error": "obs_value_filter is required. The Census contains 50M+ cells; "
                    "queries without filters will timeout. Examples: "
                    "'tissue == \"lung\"', 'cell_type == \"T cell\"', "
                    '\'disease == "COVID-19" and tissue == "blood"\'',
                }

            with cellxgene_census.open_soma(census_version=census_version) as census:
                obs_df = cellxgene_census.get_obs(
                    census,
                    organism=organism,
                    value_filter=obs_value_filter,
                    column_names=column_names,
                )

                return {
                    "status": "success",
                    "organism": organism,
                    "num_cells": len(obs_df),
                    "columns": list(obs_df.columns),
                    "data": obs_df.head(100).to_dict(orient="records")
                    if len(obs_df) <= 100
                    else obs_df.head(100).to_dict(orient="records"),
                    "message": f"Showing first 100 of {len(obs_df)} cells"
                    if len(obs_df) > 100
                    else None,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_var_metadata(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Get variable (gene) metadata."""
        try:
            import cellxgene_census

            organism = arguments.get("organism", "Homo sapiens")
            var_value_filter = arguments.get("var_value_filter")
            column_names = arguments.get("column_names")

            with cellxgene_census.open_soma(census_version=census_version) as census:
                var_df = cellxgene_census.get_var(
                    census,
                    organism=organism,
                    value_filter=var_value_filter,
                    column_names=column_names,
                )

                return {
                    "status": "success",
                    "organism": organism,
                    "num_genes": len(var_df),
                    "columns": list(var_df.columns),
                    "data": var_df.head(100).to_dict(orient="records")
                    if len(var_df) <= 100
                    else var_df.head(100).to_dict(orient="records"),
                    "message": f"Showing first 100 of {len(var_df)} genes"
                    if len(var_df) > 100
                    else None,
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_anndata(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Get expression data as AnnData object summary."""
        try:
            import cellxgene_census

            organism = arguments.get("organism", "Homo sapiens")
            obs_value_filter = arguments.get("obs_value_filter")
            var_value_filter = arguments.get("var_value_filter")
            obs_column_names = arguments.get("obs_column_names")
            var_column_names = arguments.get("var_column_names")

            # Safeguard: Require at least one filter to prevent massive queries
            if not obs_value_filter and not var_value_filter:
                return {
                    "status": "error",
                    "error": "At least one filter (obs_value_filter or var_value_filter) is required. "
                    "The Census contains 50M+ cells and 60K+ genes; unfiltered queries will timeout. "
                    'Examples: obs_value_filter=\'tissue == "lung"\', var_value_filter=\'feature_name in ["TP53", "BRCA1"]\'',
                }

            with cellxgene_census.open_soma(census_version=census_version) as census:
                adata = cellxgene_census.get_anndata(
                    census,
                    organism=organism,
                    obs_value_filter=obs_value_filter,
                    var_value_filter=var_value_filter,
                    obs_column_names=obs_column_names,
                    var_column_names=var_column_names,
                )

                return {
                    "status": "success",
                    "organism": organism,
                    "n_obs": adata.n_obs,
                    "n_vars": adata.n_vars,
                    "obs_columns": list(adata.obs.columns),
                    "var_columns": list(adata.var.columns),
                    "message": "AnnData object created. Use Python API directly to access full data.",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_presence_matrix(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Get feature presence matrix."""
        try:
            import cellxgene_census

            organism = arguments.get("organism", "Homo sapiens")

            with cellxgene_census.open_soma(census_version=census_version) as census:
                presence_matrix = cellxgene_census.get_presence_matrix(
                    census, organism=organism
                )

                return {
                    "status": "success",
                    "organism": organism,
                    "shape": presence_matrix.shape,
                    "nnz": presence_matrix.nnz,
                    "density": presence_matrix.nnz
                    / (presence_matrix.shape[0] * presence_matrix.shape[1]),
                    "message": "Presence matrix retrieved. Shape: (genes, datasets)",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_embeddings(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Get pre-calculated embeddings."""
        try:
            import cellxgene_census

            organism = arguments.get("organism", "Homo sapiens")
            embedding_name = arguments.get("embedding_name")

            # Check if experimental module is available (removed in cellxgene_census >= 1.17.0)
            if not hasattr(cellxgene_census, "experimental"):
                return {
                    "status": "success",
                    "data": {
                        "message": (
                            "The cellxgene_census.experimental module for embeddings is no longer available "
                            "in cellxgene_census >= 1.17.0. Pre-calculated embeddings (scVI, Geneformer) "
                            "can be accessed via the obs_embedding obsm slots when querying AnnData objects. "
                            "Use CELLxGENE_query_cells with the embedding coordinate columns to retrieve "
                            "cell embeddings directly."
                        ),
                        "organism": organism,
                        "embedding_name": embedding_name,
                        "available": False,
                    },
                }

            with cellxgene_census.open_soma(census_version=census_version) as census:
                available_embeddings = (
                    cellxgene_census.experimental.get_all_available_embeddings(
                        census_version=census_version
                    )
                )

                if embedding_name:
                    embedding_data = cellxgene_census.experimental.get_embedding(
                        census, organism=organism, embedding_name=embedding_name
                    )
                    return {
                        "status": "success",
                        "data": {
                            "organism": organism,
                            "embedding_name": embedding_name,
                            "shape": list(embedding_data.shape),
                            "message": "Embedding retrieved successfully",
                        },
                    }
                else:
                    return {
                        "status": "success",
                        "data": {
                            "available_embeddings": available_embeddings,
                            "message": "Specify 'embedding_name' to retrieve specific embedding",
                        },
                    }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _download_h5ad(
        self, arguments: Dict[str, Any], census_version: str
    ) -> Dict[str, Any]:
        """Download source H5AD file."""
        try:
            import cellxgene_census

            dataset_id = arguments.get("dataset_id")
            output_path = arguments.get("output_path")

            if not dataset_id:
                return {
                    "status": "error",
                    "error": "dataset_id is required for download_h5ad operation",
                }

            if output_path:
                cellxgene_census.download_source_h5ad(
                    dataset_id=dataset_id,
                    to_path=output_path,
                    census_version=census_version,
                )
                return {
                    "status": "success",
                    "dataset_id": dataset_id,
                    "output_path": output_path,
                    "message": "H5AD file downloaded successfully",
                }
            else:
                uri = cellxgene_census.get_source_h5ad_uri(
                    dataset_id=dataset_id, census_version=census_version
                )
                return {
                    "status": "success",
                    "dataset_id": dataset_id,
                    "uri": uri,
                    "message": "Use this URI to access the H5AD file",
                }
        except Exception as e:
            return {"status": "error", "error": str(e)}
