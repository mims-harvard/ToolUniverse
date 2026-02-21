"""
ESM Cambrian (ESMC) Protein Embedding Tool - MCP Server

This module provides an MCP (Model Context Protocol) server for generating
protein sequence embeddings using EvolutionaryScale's ESM-C models. ESM-C uses
transformer architecture trained on billions of diverse protein sequences to
learn contextualized protein representations that capture biologically
meaningful information about protein structure and function.

The tool provides access to multiple ESM-C model sizes:
- esmc_300m: 300M parameters (recommended for most use cases)
- esmc_600m: 600M parameters (higher quality embeddings)
- esmc_6b: 6B parameters (best quality, requires significant resources)

Embeddings are 960-dimensional vectors (mean-pooled across tokens) that enable:
- Protein similarity analysis
- Functional annotation and prediction
- Structural property inference
- Drug-target interaction prediction
- Protein engineering and design
"""

from typing import Dict, Any
from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig


# Global model cache (lazy load on first use)
_ESM_CLIENT = None


def get_client():
    """
    Get or initialize the ESM-C model.
    Uses lazy loading to avoid loading model until first embedding request.
    """
    global _ESM_CLIENT
    if _ESM_CLIENT is None:
        _ESM_CLIENT = ESMC.from_pretrained("esmc_300m")
        _ESM_CLIENT.eval()
    return _ESM_CLIENT


def compute_embedding(sequence: str):
    """
    Core embedding computation logic.

    Args:
        sequence: Protein amino acid sequence

    Returns:
        List of float values representing the embedding
    """
    import torch

    client = get_client()
    protein = ESMProtein(sequence=sequence)
    tensor = client.encode(protein)
    output = client.logits(tensor, LogitsConfig(return_embeddings=True))

    # output.embeddings[0] has shape [num_tokens, embedding_dim]
    # Mean pool across tokens to get sequence-level embedding
    embedding_tensor = output.embeddings[0]  # Shape: [num_tokens, 960]
    mean_embedding = torch.mean(embedding_tensor, dim=0)  # Shape: [960]

    return mean_embedding.tolist()


@register_mcp_tool(
    tool_type_name="esm_embed_sequence",
    config={
        "description": "Generate protein sequence embeddings using ESM-C (Cambrian). ESM-C uses transformer architecture trained on billions of diverse protein sequences to generate high-quality embeddings that capture biologically meaningful information about protein structure and function.",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": "Protein amino acid sequence using standard 20 amino acids (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y)",
                }
            },
            "required": ["sequence"],
        },
    },
    mcp_config={
        "server_name": "ESM Embedding MCP Server",
        "host": "0.0.0.0",
        "port": 8008,
        "transport": "http",
    },
)
class ESMEmbeddingTool:
    """
    ESM-C Protein Embedding Tool.

    Generates contextualized protein embeddings using the ESM-C model
    trained on billions of diverse protein sequences.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate protein embeddings using ESM-C 300M model.

        Args:
            arguments: Dictionary containing:
                - sequence: Protein amino acid sequence (standard 20 amino acids)

        Returns:
            Dictionary containing:
            - model: Model identifier (esmc_300m)
            - embedding_dim: Dimension of embedding (960, mean-pooled across tokens)
            - embedding: List of float values representing the embedding
        """
        sequence = arguments.get("sequence", "")
        embedding = compute_embedding(sequence)
        return {
            "model": "esmc_300m",
            "embedding_dim": len(embedding),
            "embedding": embedding,
        }


if __name__ == "__main__":
    # Start MCP server
    start_mcp_server()
