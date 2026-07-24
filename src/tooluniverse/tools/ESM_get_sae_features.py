"""
ESM_get_sae_features

Run a protein sequence through an ESMC Sparse Autoencoder (SAE) and return sparse feature activat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_get_sae_features(
    sequence: str,
    model: Optional[str] = "esmc-6b-2024-12",
    sae_model: Optional[str] = "esmc-6b-2024-12_k64_codebook16384_layer60",
    position: Optional[int] = None,
    window: Optional[int] = 8,
    top_k_per_residue: Optional[int] = 64,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Run a protein sequence through an ESMC Sparse Autoencoder (SAE) and return sparse feature activat...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code (e.g. 'MEEPQSDPSVEPPLSQETFS...
    model : str
        ESMC backbone model. Currently SAE is only released for esmc-6b-2024-12 (defa...
    sae_model : str
        SAE checkpoint name. Default is the layer-60 SAE matching esmc-6b backbone.
    position : int
        Optional 1-indexed residue position. If set, only activations within +/- wind...
    window : int
        Residue window radius around position (only used when position is set). Defau...
    top_k_per_residue : int
        Cap features returned per residue, sorted by absolute activation. Default 64 ...
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
            "sae_model": sae_model,
            "position": position,
            "window": window,
            "top_k_per_residue": top_k_per_residue,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_get_sae_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_get_sae_features"]
