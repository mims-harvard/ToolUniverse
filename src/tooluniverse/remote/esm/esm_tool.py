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

from fastmcp import FastMCP
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig

# Initialize MCP Server for ESM protein embeddings
mcp = FastMCP("ESM Embedding MCP Server")

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
    output = client.logits(
        tensor,
        LogitsConfig(return_embeddings=True)
    )

    # output.embeddings[0] has shape [num_tokens, embedding_dim]
    # Mean pool across tokens to get sequence-level embedding
    embedding_tensor = output.embeddings[0]  # Shape: [num_tokens, 960]
    mean_embedding = torch.mean(embedding_tensor, dim=0)  # Shape: [960]

    return mean_embedding.tolist()


@mcp.tool(
    name="esm_embed_sequence",
    description="Generate protein sequence embeddings using ESM-C",
)
def esm_embed_sequence(sequence: str):
    """
    Generate protein embeddings using ESM-C 300M model.

    Args:
        sequence: Protein amino acid sequence (standard 20 amino acids)

    Returns:
        Dictionary containing:
        - model: Model identifier (esmc_300m)
        - embedding_dim: Dimension of embedding (1280)
        - embedding: List of float values representing the embedding
    """
    embedding = compute_embedding(sequence)
    return {
        "model": "esmc_300m",
        "embedding_dim": len(embedding),
        "embedding": embedding,
    }


if __name__ == "__main__":
    # Start MCP server
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8008,
    )
