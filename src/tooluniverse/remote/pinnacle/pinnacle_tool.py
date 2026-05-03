"""
PINNACLE Protein-Protein Interaction Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for retrieving
PINNACLE (Protein Interaction Network Contextualized Learning) embeddings.
PINNACLE generates cell-type-specific protein-protein interaction embeddings
that capture the functional relationships between proteins in different
cellular contexts.

The tool provides access to pre-computed PPI embeddings that can be used for:
- Drug target prediction and prioritization
- Disease mechanism analysis
- Protein function prediction
- Network-based biomarker discovery
- Systems biology research
"""

from fastmcp import FastMCP
import os
import asyncio
import uuid
from typing import Dict, Tuple, Optional, Any


# Initialize MCP Server for PINNACLE PPI embedding retrieval
server = FastMCP("PINNACLE PPI SMCP Server")


class PinnaclePPITool:
    """
    Comprehensive tool for retrieving cell-type-specific protein-protein interaction embeddings.

    This class provides functionality to:
    - Load pre-computed PINNACLE PPI embeddings from PyTorch checkpoint files
    - Perform flexible cell type matching with fuzzy string matching
    - Retrieve embeddings for specific cellular contexts
    - Handle multiple cell type naming conventions

    PINNACLE embeddings encode protein interactions in a dense vector space,
    where proteins with similar functional roles or interaction patterns
    have similar embedding representations. These embeddings are contextualized
    for specific cell types, capturing cell-type-specific interaction patterns.

    The tool supports various cell types including immune cells, tissue-specific
    cells, and disease-associated cellular contexts.
    """

    def __init__(self, embed_path: Optional[str] = None):
        """
        Initialize the PINNACLE PPI tool by loading pre-computed embeddings.

        Args:
            embed_path (str, optional): Path to the PINNACLE embeddings file (.pth format).
                                      If None, uses PINNACLE_DATA_PATH/pinnacle_embeds/ppi_embed_dict.pth.

        Raises:
            FileNotFoundError: If the specified embeddings file cannot be found.
            Exception: If embedding loading fails due to format issues or corruption.
        """
        # Construct embeddings file path
        if embed_path is None:
            pinnacle_data_path = os.getenv("PINNACLE_DATA_PATH", "")
            self.embed_path = os.path.join(
                pinnacle_data_path, "pinnacle_embeds", "ppi_embed_dict.pth"
            )
        else:
            self.embed_path = embed_path

        # Validate embeddings file exists
        if not os.path.exists(self.embed_path):
            raise FileNotFoundError(
                f"PINNACLE embeddings file not found at {self.embed_path}. Please check your PINNACLE_DATA_PATH."
            )

        # Lazy import torch for loading embeddings
        try:
            import torch
        except ImportError:
            raise ImportError(
                "PINNACLE tool requires 'torch' package. "
                "Install it with: pip install torch"
            ) from None

        # Load PINNACLE PPI embeddings from PyTorch checkpoint
        print(f"Initializing PINNACLE PPI tool from embeddings: {self.embed_path}...")
        self.ppi_dict = torch.load(self.embed_path, weights_only=False)

        # Display available cell types for reference
        available_cell_types = list(self.ppi_dict.keys())
        print(
            f"PINNACLE tool initialized successfully (loaded embeddings for {len(available_cell_types)} cell types)."
        )
        print(
            f"Available cell types: {available_cell_types[:5]}..."
            if len(available_cell_types) > 5
            else f"Available cell types: {available_cell_types}"
        )

    def get_ppi_embeddings(self, cell_type: str) -> Tuple[Dict[str, Any], str]:
        """
        Retrieve cell-type-specific protein-protein interaction embeddings.

        This method performs intelligent matching to find the most appropriate
        embeddings for the requested cell type, supporting both exact and fuzzy
        matching to handle various naming conventions and synonyms.

        Args:
            cell_type (str): Target cell type name (e.g., 'b_cell', 'hepatocyte', 'T-cell').
                           The method handles various naming conventions including spaces,
                           hyphens, underscores, and capitalization differences.

        Returns
            Tuple[Dict[str, torch.Tensor], str]: A tuple containing:
                - Dict mapping protein/gene names to their embedding tensors (empty if no match)
                - Status message indicating match quality and selected cell type

        Note:
            The matching algorithm performs the following steps:
            1. Normalize input by converting to lowercase and standardizing separators
            2. Attempt exact match with normalized names
            3. Perform partial/substring matching for related cell types
            4. Return first partial match if multiple candidates exist
        """
        # Normalize input cell type name for robust matching
        # Convert to lowercase and standardize separators (spaces, hyphens -> underscores)
        formalized_cell_type = (
            cell_type.replace(",", "").replace("-", "_").replace(" ", "_").lower()
        )

        # Search for matching cell types with progressive matching strategy
        matching_cell_types = []

        for cell_key in self.ppi_dict.keys():
            # Normalize stored cell type name using same rules
            formalized_key = (
                cell_key.replace(",", "").replace("-", "_").replace(" ", "_").lower()
            )

            # Priority 1: Exact match (highest confidence)
            if formalized_key == formalized_cell_type:
                return (
                    self.ppi_dict[cell_key],
                    f"Exact match found for cell type '{cell_type}' -> '{cell_key}'.",
                )

            # Priority 2: Partial/substring match (moderate confidence)
            if (
                formalized_cell_type in formalized_key
                or formalized_key in formalized_cell_type
            ):
                matching_cell_types.append(cell_key)

        # Return best partial match if available
        if matching_cell_types:
            best_match = matching_cell_types[0]
            print(
                f"Partial match for '{cell_type}': using '{best_match}' from {len(matching_cell_types)} candidates."
            )
            return (
                self.ppi_dict[best_match],
                f"Partial match for '{cell_type}': using '{best_match}' (from {len(matching_cell_types)} candidates).",
            )

        # No match found - return empty embeddings with helpful error message
        available_types = list(self.ppi_dict.keys())
        message = f"Cell type '{cell_type}' not found in PINNACLE embeddings. Available cell types ({len(available_types)} total): {available_types[:10]}{'...' if len(available_types) > 10 else ''}"
        print(f"[PINNACLE PPI Retrieval]: {message}")
        return {}, message


@server.tool()
async def run_pinnacle_ppi_retrieval(cell_type: str, embed_path: Optional[str] = None):
    """
    MCP Tool: Retrieves cell-type-specific protein-protein interaction embeddings from PINNACLE.

    This tool provides access to pre-computed PINNACLE (Protein Interaction Network
    Contextualized Learning) embeddings that represent protein-protein interactions
    in specific cellular contexts. These embeddings encode functional relationships
    between proteins as dense vector representations, capturing both direct physical
    interactions and functional associations.

    Scientific Background:
    - PINNACLE embeddings are trained on cell-type-specific protein interaction networks
    - Embeddings capture both local (direct interactions) and global (pathway-level) relationships
    - Cell-type specificity accounts for tissue-specific expression and interaction patterns
    - Dense vector representations enable similarity calculations and downstream ML applications

    Applications:
    - Drug target identification and prioritization
    - Disease mechanism analysis and biomarker discovery
    - Protein function prediction and annotation
    - Network-based drug repurposing
    - Systems biology and pathway analysis
    - Precision medicine and personalized therapeutics

    Technical Details:
    - Embeddings are stored as PyTorch tensors with consistent dimensionality
    - Supports fuzzy matching for cell type names (handles various naming conventions)
    - Returns embeddings for all proteins/genes available in the specified cell type
    - Vector dimensions typically range from 128-512 depending on model configuration

    Args:
        cell_type (str): Target cell type for embedding retrieval. Supports flexible naming:
                        - Standard formats: 'b_cell', 'hepatocyte', 'cardiomyocyte'
                        - Alternative formats: 'B-cell', 'T cell', 'NK cells'
                        - Tissue types: 'liver', 'heart', 'brain', 'immune'
                        The tool performs intelligent matching to find the best available match.

    Returns
        dict: Comprehensive embedding retrieval results containing:
            - 'embeddings' (dict, optional): Protein-to-embedding mapping where:
                * Keys: Gene/protein symbols (e.g., 'TP53', 'EGFR', 'BRCA1')
                * Values: Embedding vectors as lists of floats (e.g., 256-dimensional vectors)
                Only present when embeddings are successfully retrieved.
            - 'context_info' (list): Detailed information about the retrieval process:
                * Match quality (exact vs partial match)
                * Selected cell type name
                * Number of proteins with embeddings
                * Available alternatives if no match found
            - 'error' (str, optional): Error description if retrieval failed

    Example Usage:
        # Retrieve B cell PPI embeddings
        result = await run_pinnacle_ppi_retrieval("b_cell")

        # Get hepatocyte-specific interactions
        result = await run_pinnacle_ppi_retrieval("hepatocyte")

        # Flexible naming support
        result = await run_pinnacle_ppi_retrieval("T-cells")
    """
    # Generate unique request ID for tracking and logging
    request_id = str(uuid.uuid4())[:8]
    print(
        f"[{request_id}] Received PINNACLE PPI embedding retrieval request for cell type: '{cell_type}'"
    )

    try:
        # Brief async pause to allow for proper request handling
        await asyncio.sleep(0.1)

        # Validate input parameter
        if not cell_type or not cell_type.strip():
            raise ValueError(
                "Cell type parameter cannot be empty. Please provide a valid cell type name."
            )

        print(
            f"[{request_id}] Processing PPI embedding retrieval for cell type: '{cell_type.strip()}'"
        )

        # Initialize global PINNACLE tool instance for MCP server
        # This instance will be used by the MCP tool function to serve PPI embedding requests
        try:
            pinnacle_tool = PinnaclePPITool(embed_path=embed_path)
            print("PINNACLE PPI tool instance created and ready for MCP server")
        except Exception as e:
            print(f"Error creating PINNACLE PPI tool: {str(e)}")
            print(
                "Please ensure PINNACLE_DATA_PATH is correctly set and embedding files exist."
            )
            raise e

        # Execute PINNACLE embedding retrieval with intelligent matching
        embeddings, match_message = pinnacle_tool.get_ppi_embeddings(cell_type.strip())

        # Handle case where no embeddings are found
        if not embeddings:
            print(f"[{request_id}] No embeddings found for cell type '{cell_type}'")
            return {
                "error": f"No PINNACLE embeddings available for cell type '{cell_type}'",
                "context_info": [
                    match_message,
                    "Consider checking available cell types or using alternative naming conventions.",
                    "Common formats include: 'b_cell', 'hepatocyte', 'cardiomyocyte', 't_cell', etc.",
                ],
            }

        # Convert PyTorch tensors to JSON-serializable lists
        # This enables downstream processing and API compatibility
        serializable_embeddings = {
            gene: tensor.tolist() if hasattr(tensor, "tolist") else tensor
            for gene, tensor in embeddings.items()
        }

        # Log successful completion with key metrics
        num_proteins = len(serializable_embeddings)
        embedding_dim = (
            len(next(iter(serializable_embeddings.values())))
            if serializable_embeddings
            else 0
        )
        print(
            f"[{request_id}] PINNACLE PPI retrieval completed: {num_proteins} proteins, {embedding_dim}D embeddings"
        )

        return {
            "embeddings": serializable_embeddings,
            "context_info": [
                match_message,
                f"Successfully retrieved embeddings for {num_proteins} proteins/genes.",
                f"Embedding dimensionality: {embedding_dim} features per protein.",
                f"Cell type context: {cell_type} (matched and processed).",
            ],
        }

    except ValueError as e:
        error_message = f"PINNACLE PPI retrieval validation error: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": ["Please verify cell type parameter and format."],
        }
    except Exception as e:
        error_message = f"Unexpected error during PINNACLE PPI retrieval: {str(e)}"
        print(f"[{request_id}] {error_message}")
        return {
            "error": error_message,
            "context_info": [
                "Internal server error occurred during embedding retrieval."
            ],
        }


if __name__ == "__main__":
    print("Starting MCP server for PINNACLE Protein-Protein Interaction Tool...")
    print("Model: PINNACLE (Protein Interaction Network Contextualized Learning)")
    print("Application: Cell-type-specific protein interaction embedding retrieval")
    print("Features: Intelligent cell type matching and dense vector representations")
    print("Server: FastMCP with streamable HTTP transport")
    print("Port: 7001 (configured to avoid conflicts with other biomedical tools)")

    # Launch the MCP server with PINNACLE PPI embedding capabilities
    server.run(
        transport="streamable-http", host="0.0.0.0", port=7001, stateless_http=True
    )
