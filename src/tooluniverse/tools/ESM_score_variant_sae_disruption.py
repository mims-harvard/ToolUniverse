"""
ESM_score_variant_sae_disruption

Composite SAE-based variant scoring. Given a protein sequence and a missense variant (position + ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_score_variant_sae_disruption(
    sequence: str,
    position: int,
    ref_aa: str,
    alt_aa: str,
    window: Optional[int] = 8,
    top_k_features: Optional[int] = 10,
    model: Optional[str] = "esmc-6b-2024-12",
    sae_model: Optional[str] = "esmc-6b-2024-12_k64_codebook16384_layer60",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Composite SAE-based variant scoring. Given a protein sequence and a missense variant (position + ...

    Parameters
    ----------
    sequence : str
        Reference protein sequence (canonical isoform). Single-letter codes, no gaps....
    position : int
        1-indexed mutation position. The amino acid at sequence[position-1] must equa...
    ref_aa : str
        Reference amino acid at the mutation position, single-letter code (e.g. 'R')....
    alt_aa : str
        Mutant amino acid, single-letter code (e.g. 'H' for R175H).
    window : int
        Residue window radius around the mutation. Per-feature activations are summed...
    top_k_features : int
        Number of top LOST and top GAINED features to return. Default 10.
    model : str
        ESMC backbone (default esmc-6b-2024-12).
    sae_model : str
        SAE checkpoint (default layer-60 6B SAE).
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
            "position": position,
            "ref_aa": ref_aa,
            "alt_aa": alt_aa,
            "window": window,
            "top_k_features": top_k_features,
            "model": model,
            "sae_model": sae_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_score_variant_sae_disruption",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_score_variant_sae_disruption"]
