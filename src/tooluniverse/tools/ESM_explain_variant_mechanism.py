"""
ESM_explain_variant_mechanism

One-call composite for variant mechanism: runs ESMC-6B SAE variant disruption + describe_sae_feat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_explain_variant_mechanism(
    sequence: str,
    position: int,
    ref_aa: str,
    alt_aa: str,
    window: Optional[int] = 8,
    top_k_features: Optional[int] = 5,
    include_descriptions: Optional[bool] = True,
    model: Optional[str] = "esmc-6b-2024-12",
    sae_model: Optional[str] = "esmc-6b-2024-12_k64_codebook16384_layer60",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    One-call composite for variant mechanism: runs ESMC-6B SAE variant disruption + describe_sae_feat...

    Parameters
    ----------
    sequence : str
        Reference (wild-type) protein amino acid sequence in single-letter code. Up t...
    position : int
        1-indexed residue position of the variant
    ref_aa : str
        Single-letter wild-type amino acid (must match sequence[position-1])
    alt_aa : str
        Single-letter substituted amino acid
    window : int
        Residue window centered on the mutation for activation summation.
    top_k_features : int
        Number of top lost / top gained features to describe and include in the categ...
    include_descriptions : bool
        If true (default), call ESM_describe_sae_feature on each top feature to get c...
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
            "position": position,
            "ref_aa": ref_aa,
            "alt_aa": alt_aa,
            "window": window,
            "top_k_features": top_k_features,
            "include_descriptions": include_descriptions,
            "model": model,
            "sae_model": sae_model,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_explain_variant_mechanism",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_explain_variant_mechanism"]
