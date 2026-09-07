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

import threading
from typing import Dict, Any
from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_sequence_input import validate_sequence
from esm.models.esmc import ESMC
from esm.sdk.api import ESMProtein, LogitsConfig


MAX_SEQUENCE_LENGTH = 2046
PROTEIN_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


# Global model cache (lazy load on first use)
_ESM_CLIENT = None
_ESM_INIT_LOCK = threading.Lock()
_ESM_INFERENCE_LOCK = threading.Lock()


def get_client():
    """
    Get or initialize the ESM-C model.
    Uses lazy loading to avoid loading model until first embedding request.
    """
    global _ESM_CLIENT
    if _ESM_CLIENT is None:
        with _ESM_INIT_LOCK:
            if _ESM_CLIENT is None:
                try:
                    _ESM_CLIENT = ESMC.from_pretrained("esmc_300m")
                except ValueError as exc:
                    # The reviewed Biohub source pin uses huggingface_hub's
                    # load_torch_model on the snapshot directory, while the
                    # official ESM-C repository stores its single checkpoint
                    # below data/weights. Load that exact weights-only file.
                    if "does not contain a valid checkpoint" not in str(exc):
                        raise
                    import torch
                    from accelerate import init_empty_weights
                    from esm.tokenization import get_esmc_model_tokenizers
                    from esm.utils.constants.esm3 import data_root

                    device = torch.device(
                        "cuda" if torch.cuda.is_available() else "cpu"
                    )
                    with init_empty_weights():
                        model = ESMC(
                            d_model=960,
                            n_heads=15,
                            n_layers=30,
                            tokenizer=get_esmc_model_tokenizers(),
                            use_flash_attn=True,
                        ).eval()
                    checkpoint = (
                        data_root("esmc-300")
                        / "data/weights/esmc_300m_2024_12_v0.pth"
                    )
                    state_dict = torch.load(
                        checkpoint, map_location=device, weights_only=True
                    )
                    model.load_state_dict(state_dict, assign=True)
                    _ESM_CLIENT = model.to(device)
                    if device.type == "cuda":
                        _ESM_CLIENT = _ESM_CLIENT.to(torch.bfloat16)
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
    with _ESM_INFERENCE_LOCK:
        tensor = client.encode(protein)
        with torch.no_grad():
            output = client.logits(tensor, LogitsConfig(return_embeddings=True))

    # Exclude BOS/EOS special tokens from the residue-level mean.
    embedding_tensor = output.embeddings[0]
    if embedding_tensor.shape[0] < 3:
        raise ValueError("ESM-C returned no residue embeddings.")
    mean_embedding = torch.mean(embedding_tensor[1:-1], dim=0)

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
                    "description": "Protein sequence using the 20 standard amino acids; 1 to 2,046 residues.",
                    "minLength": 1,
                    "maxLength": 2046,
                    "pattern": "^[ACDEFGHIKLMNPQRSTVWYacdefghiklmnpqrstvwy]+$",
                }
            },
            "required": ["sequence"],
        },
    },
    mcp_config={
        "server_name": "ESM Embedding MCP Server",
        # Loopback by default; remote exposure requires TOOLUNIVERSE_API_TOKEN
        # (enforced by the SMCP bind guard at server start).
        "host": "127.0.0.1",
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
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        try:
            sequence = validate_sequence(
                arguments.get("sequence"),
                name="sequence",
                alphabet=PROTEIN_ALPHABET,
                max_length=MAX_SEQUENCE_LENGTH,
            )
        except ValueError as exc:
            return {"error": str(exc)}
        try:
            embedding = compute_embedding(sequence)
            return {
                "model": "esmc_300m",
                "embedding_dim": len(embedding),
                "embedding": embedding,
            }
        except Exception:
            return {"error": "ESM-C embedding failed on the provider."}


if __name__ == "__main__":
    # Start MCP server
    start_mcp_server()
