"""
Transcriptformer Gene Embedding Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for retrieving
pre-computed gene embeddings from the Transcriptformer model. Transcriptformer
is a transformer-based architecture trained on single-cell RNA sequencing data
to learn contextualized gene representations that capture cell-type-specific
and disease-state-specific expression patterns.

The tool provides access to disease-specific embedding stores that enable:
- Gene similarity analysis in specific cellular contexts
- Biomarker discovery and validation
- Pathway analysis and functional annotation
- Drug target identification and prioritization
- Precision medicine applications
- Systems biology research
"""

from fastmcp import FastMCP
import os
import asyncio
import gzip
import json
import numpy as np
import threading
from typing import Union, List, Dict, Tuple, Optional, Any
from tooluniverse.server_security import (
    get_fastmcp_token_auth,
    run_fastmcp_server,
)


# Initialize MCP Server for Transcriptformer gene embedding retrieval
server = FastMCP(
    "Transcriptformer SMCP Server", auth=get_fastmcp_token_auth()
)


_MAX_REQUESTED_GENES = 250
_MAX_GENE_NAME_LENGTH = 64
_MAX_EMBEDDING_DIM = 4096
_MAX_METADATA_COMPRESSED_BYTES = 50_000_000
_MAX_METADATA_JSON_BYTES = 100_000_000
_TRANSCRIPTFORMER_TOOL = None
_TRANSCRIPTFORMER_TOOL_LOCK = threading.Lock()
_TRANSCRIPTFORMER_REQUEST_LOCK = threading.Lock()


def _get_transcriptformer_tool():
    """Discover provider stores once and preserve the metadata cache across calls."""
    global _TRANSCRIPTFORMER_TOOL
    if _TRANSCRIPTFORMER_TOOL is None:
        with _TRANSCRIPTFORMER_TOOL_LOCK:
            if _TRANSCRIPTFORMER_TOOL is None:
                _TRANSCRIPTFORMER_TOOL = TranscriptformerEmbeddingTool()
    return _TRANSCRIPTFORMER_TOOL


class TranscriptformerEmbeddingTool:
    """
    Comprehensive tool for retrieving contextualized gene embeddings from Transcriptformer models.

    This class provides functionality to:
    - Load and manage disease-specific embedding stores
    - Retrieve gene embeddings for specific cellular contexts (cell type + disease state)
    - Handle both gene symbols and Ensembl IDs with intelligent mapping
    - Cache metadata for efficient repeated queries
    - Support bulk embedding retrieval for pathway analysis

    Transcriptformer embeddings encode gene expression patterns learned from
    single-cell RNA sequencing data, capturing:
    - Cell-type-specific expression signatures
    - Disease-state-dependent gene regulation
    - Co-expression relationships and functional modules
    - Temporal dynamics and developmental trajectories

    The tool supports various disease contexts and cell types, enabling
    precision medicine applications and systems biology research.
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the Transcriptformer embedding tool by discovering available disease stores.

        The tool automatically scans the embedding store directory to identify
        available disease-specific embedding collections and prepares metadata
        caching infrastructure for efficient access.

        Raises:
            FileNotFoundError: If the embedding store base directory cannot be found.
        """
        # Construct path to embedding stores
        if data_dir is None:
            transcriptformer_data_path = os.getenv(
                "TRANSCRIPTFORMER_DATA_PATH", ""
            )
        else:
            transcriptformer_data_path = data_dir
        self.base_dir = os.path.join(
            transcriptformer_data_path, "transcriptformer_embedding", "embedding_store"
        )

        # Validate base directory exists
        if not os.path.exists(self.base_dir):
            raise FileNotFoundError(
                f"Transcriptformer embedding store directory not found at {self.base_dir}. Please check your TRANSCRIPTFORMER_DATA_PATH."
            )

        # Discover available disease-specific embedding stores
        self._disease_directories = {
            d.lower().replace(" ", "_"): d
            for d in os.listdir(self.base_dir)
            if os.path.isdir(os.path.join(self.base_dir, d))
        }
        self.available_diseases: List[str] = sorted(self._disease_directories)

        # Initialize metadata cache for performance optimization
        self.metadata_cache: Dict[str, Dict[str, Any]] = {}

        print(
            f"Transcriptformer tool initialized with {len(self.available_diseases)} disease contexts: {self.available_diseases}"
        )

    def _load_metadata(self, disease: str) -> Dict:
        """
        Load and cache metadata for a specific disease embedding store.

        This method loads comprehensive metadata including gene mappings, available
        cell types, disease states, and embedding matrix organization. Metadata
        is cached to avoid repeated file I/O operations for the same disease.

        Args:
            disease (str): Disease identifier (normalized to lowercase with underscores).

        Returns
            Dict: Cached metadata dictionary containing:
                - store_path: Path to disease-specific embedding store
                - ensembl_ids_ordered: Ordered list of Ensembl gene IDs
                - gene_to_idx: Mapping from Ensembl IDs to matrix indices
                - symbol_to_ensembl: Mapping from gene symbols to Ensembl IDs
                - available_symbols: Sorted list of available gene symbols
                - groups_meta: Metadata for available cell type + disease state combinations
                - available_cell_types: Sorted list of available cell types
                - available_states: Sorted list of available disease states

        Raises:
            FileNotFoundError: If disease is not available or metadata file is missing.
        """
        # Return cached metadata if already loaded
        if disease in self.metadata_cache:
            return self.metadata_cache[disease]

        # Validate disease availability
        if disease not in self.available_diseases:
            raise FileNotFoundError(
                f"Disease '{disease}' is not available. Please choose from available diseases: {self.available_diseases}"
            )

        # Construct paths to disease-specific store and metadata
        store_path = os.path.join(self.base_dir, self._disease_directories[disease])
        metadata_path = os.path.join(store_path, "metadata.json.gz")

        # Validate metadata file exists
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(
                f"Metadata file not found at: {metadata_path}. Please ensure embedding store is properly prepared."
            )

        # Load compressed metadata file
        print(
            f"Loading Transcriptformer metadata from embedding store: {os.path.basename(store_path)}..."
        )
        if os.path.getsize(metadata_path) > _MAX_METADATA_COMPRESSED_BYTES:
            raise ValueError("Transcriptformer metadata exceeds the compressed-size limit")
        with gzip.open(metadata_path, "rb") as f:
            metadata_bytes = f.read(_MAX_METADATA_JSON_BYTES + 1)
        if len(metadata_bytes) > _MAX_METADATA_JSON_BYTES:
            raise ValueError("Transcriptformer metadata exceeds the expansion limit")
        metadata = json.loads(metadata_bytes.decode("utf-8"))

        # Process and cache metadata with normalized keys
        self.metadata_cache[disease] = {
            "store_path": store_path,
            "ensembl_ids_ordered": metadata["ensembl_ids_ordered"],
            "gene_to_idx": {
                gene: i for i, gene in enumerate(metadata["ensembl_ids_ordered"])
            },
            "symbol_to_ensembl": metadata["gene_map_symbol_to_ensembl"],
            "available_symbols": sorted(
                list(metadata["gene_map_symbol_to_ensembl"].keys())
            ),
            "groups_meta": {
                k.lower().replace(" ", "_"): v for k, v in metadata["groups"].items()
            },
            "available_cell_types": sorted(
                list(
                    set(
                        details["cell_type"].lower().replace(" ", "_")
                        for details in metadata["groups"].values()
                    )
                )
            ),
            "available_states": sorted(
                list(
                    set(
                        details["disease_state"].lower().replace(" ", "_")
                        for details in metadata["groups"].values()
                    )
                )
            ),
        }

        cached_data = self.metadata_cache[disease]
        print(
            f"Metadata loaded successfully: {len(cached_data['available_symbols'])} genes, "
            f"{len(cached_data['available_cell_types'])} cell types, "
            f"{len(cached_data['available_states'])} disease states."
        )

        return self.metadata_cache[disease]

    def get_embedding_for_context(
        self,
        state: str,
        cell_type: str,
        gene_names: Union[List[str], None],
        disease: str,
    ) -> Tuple[Optional[Dict[str, np.ndarray]], List[str]]:
        """
        Retrieve contextualized gene embeddings for specific cellular and disease contexts.

        This method loads pre-computed Transcriptformer embeddings that capture gene
        expression patterns in specific combinations of cell type and disease state.
        The embeddings are loaded on-demand from compressed numpy matrices for
        memory efficiency and fast access.

        Args:
            state (str): Disease state context (e.g., 'control', 'disease', 'treated').
                        Must be normalized (lowercase, underscores for spaces).
            cell_type (str): Cell type context (e.g., 'b_cell', 'macrophage', 'epithelial_cell').
                           Must be normalized (lowercase, underscores for spaces).
            gene_names (Union[List[str], None]): Gene identifiers to retrieve embeddings for.
                                               Can be gene symbols (e.g., 'TP53') or Ensembl IDs (e.g., 'ENSG00000141510').
                                               If None, returns embeddings for all available genes.
            disease (str): Disease context identifier (e.g., 'breast_cancer', 'diabetes').
                         Must match available disease stores.

        Returns
            Tuple[Optional[Dict[str, np.ndarray]], List[str]]: A tuple containing:
                - Dictionary mapping gene names to embedding vectors (None if failed)
                - List of context information and error messages

        The embedding vectors are float32 numpy arrays representing learned gene
        representations in the specified cellular context.
        """
        # Normalize input parameters for consistent matching
        disease = disease.lower().replace(" ", "_")
        state = state.lower().replace(" ", "_")
        cell_type = cell_type.lower().replace(" ", "_")

        # Load metadata for the specified disease
        metadata = self._load_metadata(disease)

        context_info = []
        embeddings = {}
        invalid_genes = []

        # Validate disease state parameter
        if state not in metadata["available_states"]:
            context_info.append(
                f"Disease state '{state}' is unavailable for the requested dataset."
            )
            return None, context_info

        # Validate cell type parameter
        if cell_type not in metadata["available_cell_types"]:
            context_info.append(
                f"Cell type '{cell_type}' is unavailable for the requested dataset."
            )
            return None, context_info

        # Process gene names parameter (None means retrieve all genes)
        if gene_names is None:
            # Retrieve embeddings for all genes in this context
            print(
                f"Loading complete gene embedding set for context: {disease} - {state} - {cell_type}"
            )

            # Create gene mapping using symbols as primary keys when available
            for ensembl_id in metadata["ensembl_ids_ordered"]:
                # Find corresponding gene symbol for this Ensembl ID
                gene_symbol = None
                for symbol, ens_id in metadata["symbol_to_ensembl"].items():
                    if ens_id == ensembl_id:
                        gene_symbol = symbol
                        break

                # Use gene symbol as key if available, otherwise use Ensembl ID
                if gene_symbol:
                    embeddings[gene_symbol] = ensembl_id
                else:
                    embeddings[ensembl_id] = ensembl_id
        else:
            # Validate and process specific gene identifiers
            for gene_name in gene_names:
                ensembl_id = None

                # Check if input is an Ensembl ID (starts with 'ENSG')
                if gene_name.upper().startswith("ENSG"):
                    ensembl_id = gene_name.upper()
                    if ensembl_id not in metadata["gene_to_idx"]:
                        invalid_genes.append(gene_name)
                else:
                    # Treat as gene symbol and lookup corresponding Ensembl ID
                    ensembl_id = metadata["symbol_to_ensembl"].get(gene_name.upper())
                    if not ensembl_id:
                        invalid_genes.append(gene_name)

                # Add valid gene to embedding request
                if ensembl_id:
                    embeddings[gene_name] = ensembl_id

            # Report invalid gene identifiers
            if invalid_genes:
                context_info.append(
                    f"Invalid or unavailable gene identifiers: {invalid_genes}"
                )
                context_info.append(
                    f"Please use valid gene symbols or Ensembl IDs from the {disease} dataset."
                )

        # Check if any valid genes were found
        if not embeddings:
            return None, context_info

        # Construct group key for embedding matrix lookup
        # Format: celltype_diseasestate (normalized, no special characters)
        group_key = (
            f"{cell_type}_{state}".replace(" ", "_").replace("(", "").replace(")", "")
        )

        # Validate that the requested context combination exists
        if group_key not in metadata["groups_meta"]:
            context_info.append(
                f"Context combination not available: state='{state}', cell_type='{cell_type}'"
            )
            return None, context_info

        # Load embedding matrix on-demand from compressed numpy file
        npy_path = os.path.join(metadata["store_path"], f"{group_key}.npy")
        if not os.path.exists(npy_path):
            context_info.append(
                f"Embedding matrix is unavailable for context '{group_key}'"
            )
            return None, context_info

        print(f"Loading embedding matrix for context: {group_key}")
        embedding_matrix = np.load(npy_path, allow_pickle=False, mmap_mode="r")
        if (
            embedding_matrix.ndim != 2
            or embedding_matrix.shape[0] != len(metadata["ensembl_ids_ordered"])
            or not 1 <= embedding_matrix.shape[1] <= _MAX_EMBEDDING_DIM
        ):
            raise ValueError("Transcriptformer embedding matrix has an invalid shape")

        # Extract embeddings for requested genes
        final_embeddings = {}
        for gene_name, ensembl_id in embeddings.items():
            gene_idx = metadata["gene_to_idx"].get(ensembl_id)
            if gene_idx is not None:
                # Extract and dequantize embedding vector to float32
                embedding_vector = embedding_matrix[gene_idx].astype(np.float32)
                if not np.isfinite(embedding_vector).all():
                    raise ValueError(
                        "Transcriptformer embedding matrix contains non-finite values"
                    )
                final_embeddings[gene_name] = embedding_vector

        # Add success information to context
        context_info.append(
            f"Successfully retrieved {len(final_embeddings)} gene embeddings for context: {disease} - {state} - {cell_type}"
        )
        if len(final_embeddings) > 0:
            embedding_dim = final_embeddings[next(iter(final_embeddings))].shape[0]
            context_info.append(
                f"Embedding dimensionality: {embedding_dim} features per gene"
            )

        return final_embeddings, context_info


def _run_transcriptformer_embedding_retrieval(
    state: str,
    cell_type: str,
    gene_names: List[str],
    disease: str,
):
    """
    MCP Tool: Retrieves contextualized gene embeddings from Transcriptformer models.

    This tool provides access to pre-computed Transcriptformer embeddings that capture
    gene expression patterns learned from single-cell RNA sequencing data. The embeddings
    are contextualized for specific combinations of disease states and cell types,
    enabling precise analysis of gene behavior in relevant biological contexts.

    Scientific Background:
    - Transcriptformer uses transformer architecture to learn gene representations
    - Embeddings capture cell-type-specific and disease-state-specific expression patterns
    - Model trained on large-scale single-cell RNA-seq datasets
    - Dense vector representations enable similarity analysis and downstream ML applications

    Applications:
    - Gene similarity analysis and functional annotation
    - Biomarker discovery and validation in disease contexts
    - Pathway analysis and systems biology research
    - Drug target identification and prioritization
    - Precision medicine and personalized therapeutics
    - Co-expression network analysis

    Technical Details:
    - Embeddings stored as compressed numpy matrices for efficient access
    - On-demand loading minimizes memory usage
    - Supports both gene symbols and Ensembl ID inputs
    - Float32 precision for optimal balance of accuracy and efficiency

    Args:
        state (str): Disease state context for embedding retrieval. Examples:
                    - 'control': Healthy/normal condition
                    - 'disease': Disease-affected state
                    - 'treated': Post-treatment condition
                    - 'untreated': Pre-treatment condition
                    Must match available states in the disease-specific store.

        cell_type (str): Cell type context for embeddings. Examples:
                    - 'b_cell': B lymphocytes
                    - 't_cell': T lymphocytes
                    - 'macrophage': Tissue macrophages
                    - 'epithelial_cell': Epithelial cells
                    - 'fibroblast': Connective tissue fibroblasts
                    Must match available cell types in the disease store.

        gene_names (List[str]): Gene identifiers for embedding retrieval:
                            - Gene symbols: ['TP53', 'BRCA1', 'EGFR', 'MYC']
                            - Ensembl IDs: ['ENSG00000141510', 'ENSG00000139618']
                            - Mixed formats supported
                            - Supply 1 to 250 identifiers per request

        disease (str): Disease/dataset identifier. Examples:
                    - 'breast_cancer': Breast cancer scRNA-seq data
                    - 'lung_cancer': Lung cancer contexts
                    - 'diabetes': Diabetes-related datasets
                    - 'alzheimer': Alzheimer's disease contexts
                    Must match available disease stores.

    Returns
        dict: Comprehensive embedding retrieval results containing:
            - 'embeddings' (dict, optional): Gene-to-embedding mapping where:
                * Keys: Gene identifiers (symbols or Ensembl IDs as provided)
                * Values: Embedding vectors as lists of float32 values
                Only present when embeddings are successfully retrieved.
            - 'context_info' (list): Detailed retrieval information including:
                * Validation results and parameter processing
                * Number of genes processed and embedding dimensions
                * Warnings about invalid gene identifiers
                * Context combination availability
            - 'error' (str, optional): Error description if retrieval failed

    Example Usage:
        # Retrieve specific cancer-related genes in breast cancer B cells
        result = await run_transcriptformer_embedding_retrieval(
            state="disease",
            cell_type="b_cell",
            gene_names=["TP53", "BRCA1", "EGFR", "MYC"],
            disease="breast_cancer"
        )

        # Mixed gene identifier formats
        result = await run_transcriptformer_embedding_retrieval(
            state="treated",
            cell_type="t_cell",
            gene_names=["CD8A", "ENSG00000153563", "IFNG"],
            disease="immunotherapy_response"
        )
    """

    print("Received Transcriptformer embedding retrieval request")

    # Initialize global Transcriptformer tool instance for MCP server
    # This instance will be used by the MCP tool function to serve embedding requests
    try:
        transcriptformer_tool = _get_transcriptformer_tool()
        print("Transcriptformer tool instance created and ready for MCP server")
    except Exception:
        print("Error creating Transcriptformer tool")
        return {
            "error": "Transcriptformer data are unavailable on the provider.",
            "context_info": ["The provider must verify TRANSCRIPTFORMER_DATA_PATH."],
        }

    try:
        # Validate input parameters
        if (
            not isinstance(disease, str)
            or not disease.strip()
            or len(disease) > 128
        ):
            raise ValueError(
                "Disease parameter cannot be empty. Please specify a valid disease identifier."
            )
        if not isinstance(state, str) or not state.strip() or len(state) > 128:
            raise ValueError(
                "State parameter cannot be empty. Please specify a valid disease state."
            )
        if (
            not isinstance(cell_type, str)
            or not cell_type.strip()
            or len(cell_type) > 128
        ):
            raise ValueError(
                "Cell type parameter cannot be empty. Please specify a valid cell type."
            )
        if (
            not isinstance(gene_names, list)
            or not 1 <= len(gene_names) <= _MAX_REQUESTED_GENES
            or any(
                not isinstance(gene, str)
                or not gene.strip()
                or len(gene) > _MAX_GENE_NAME_LENGTH
                for gene in gene_names
            )
            or len(set(gene_names)) != len(gene_names)
        ):
            raise ValueError(
                "gene_names must contain 1 to 250 unique nonempty strings of at most 64 characters"
            )

        # Execute Transcriptformer embedding retrieval
        embeddings, context_info = transcriptformer_tool.get_embedding_for_context(
            state=state.strip(),
            cell_type=cell_type.strip(),
            gene_names=gene_names,
            disease=disease.strip(),
        )

        # Handle retrieval failure
        if embeddings is None:
            print("Transcriptformer embedding retrieval failed for the requested context")
            return {
                "error": "Failed to retrieve Transcriptformer embeddings for specified context",
                "context_info": context_info
                + [
                    "Please verify disease, state, and cell type parameters.",
                    "Check available contexts using the tool's metadata.",
                ],
            }

        # Convert numpy arrays to JSON-serializable lists
        # This enables downstream processing and API compatibility
        serializable_embeddings = {}
        for gene_name, embedding_vector in embeddings.items():
            serializable_embeddings[gene_name] = embedding_vector.tolist()

        # Log successful completion with key metrics
        num_genes = len(serializable_embeddings)
        embedding_dim = (
            len(next(iter(serializable_embeddings.values())))
            if serializable_embeddings
            else 0
        )
        print("Transcriptformer embedding retrieval completed")

        return {
            "embeddings": serializable_embeddings,
            "context_info": context_info
            + [
                f"Embedding retrieval completed for {num_genes} genes.",
                f"Context: {disease} - {state} - {cell_type}",
                f"Embedding dimensionality: {embedding_dim} features per gene.",
            ],
        }

    except ValueError as e:
        error_message = (
            f"Transcriptformer embedding retrieval validation error: {str(e)}"
        )
        print("Transcriptformer embedding retrieval validation error")
        return {
            "error": error_message,
            "context_info": ["Please verify input parameters and available contexts."],
        }
    except Exception:
        error_message = "Transcriptformer retrieval failed due to an internal provider error."
        print("Unexpected error during Transcriptformer embedding retrieval")
        return {
            "error": error_message,
            "context_info": [
                "Internal server error occurred during embedding retrieval."
            ],
        }


@server.tool()
async def run_transcriptformer_embedding_retrieval(
    state: str,
    cell_type: str,
    gene_names: List[str],
    disease: str,
):
    """Retrieve embeddings without blocking the MCP event loop."""

    def execute():
        # Metadata discovery/cache population and matrix reads share provider
        # state, so serialize calls until a future store implementation proves
        # safe concurrent access.
        with _TRANSCRIPTFORMER_REQUEST_LOCK:
            return _run_transcriptformer_embedding_retrieval(
                state,
                cell_type,
                gene_names,
                disease,
            )

    return await asyncio.to_thread(execute)


if __name__ == "__main__":
    print("Starting MCP server for Transcriptformer Gene Embedding Tool...")
    print("Model: Transcriptformer (Transformer-based gene representation learning)")
    print("Application: Contextualized gene embedding retrieval from single-cell data")
    print("Features: Disease-specific and cell-type-specific gene representations")
    print("Server: FastMCP with streamable HTTP transport")
    print("Port: 7000 (configured for biomedical embedding services)")
    print("Timeout: Extended for large embedding matrix operations")

    # Launch the MCP server with Transcriptformer embedding capabilities
    # Extended timeout for handling large embedding matrices
    run_fastmcp_server(
        server,
        host=os.getenv("TOOLUNIVERSE_MCP_HOST", "127.0.0.1"),
        port=7000,
        stateless_http=True,
    )
