"""
ESM_get_protein_embedding

Get protein sequence embeddings from EvolutionaryScale ESMC (ESM Cambrian) models via the Forge A...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_get_protein_embedding(
    sequence: str,
    model: Optional[str] = "esmc-300m-2024-12",
    return_per_residue: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein sequence embeddings from EvolutionaryScale ESMC (ESM Cambrian) models via the Forge A...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code (e.g. 'MKTAYIAKQRQISFVKSHFS...
    model : str
        ESMC model to use. 'esmc-300m-2024-12' (faster, 300M params) or 'esmc-600m-20...
    return_per_residue : bool
        If true, also return per-residue embedding vectors (one vector per amino acid...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "sequence": sequence,
            "model": model,
            "return_per_residue": return_per_residue,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_get_protein_embedding",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_get_protein_embedding"]
