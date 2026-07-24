"""
ESM_get_region_sae_features

Aggregate ESMC-6B SAE features over a contiguous residue range to characterize the region's biolo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_get_region_sae_features(
    sequence: str,
    start_position: int,
    end_position: int,
    top_k_features: Optional[int] = 20,
    model: Optional[str] = "esmc-6b-2024-12",
    sae_model: Optional[str] = "esmc-6b-2024-12_k64_codebook16384_layer60",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Aggregate ESMC-6B SAE features over a contiguous residue range to characterize the region's biolo...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code. Up to ~2700 AA.
    start_position : int
        1-indexed inclusive start of the region of interest.
    end_position : int
        1-indexed inclusive end of the region of interest. Must be >= start_position ...
    top_k_features : int
        Number of top features (by total |activation| over region) to return.
    model : str
        ESMC base model
    sae_model : str
        SAE codebook identifier
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
            "start_position": start_position,
            "end_position": end_position,
            "top_k_features": top_k_features,
            "model": model,
            "sae_model": sae_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_get_region_sae_features",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_get_region_sae_features"]
