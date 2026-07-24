"""
OpenTargets_get_variant_effect_predictions

Retrieve in-silico functional effect predictions for a variant (chrom_pos_ref_alt) from OpenTarge...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_variant_effect_predictions(
    variantId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve in-silico functional effect predictions for a variant (chrom_pos_ref_alt) from OpenTarge...

    Parameters
    ----------
    variantId : str
        Variant ID in chrom_pos_ref_alt format (e.g., '19_44908822_C_T' for the APOE ...
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
    _args = {k: v for k, v in {"variantId": variantId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_variant_effect_predictions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_variant_effect_predictions"]
