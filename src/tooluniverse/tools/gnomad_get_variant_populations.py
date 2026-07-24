"""
gnomad_get_variant_populations

Get per-ancestry (population-stratified) allele frequencies for a variant from gnomAD by `variant...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_variant_populations(
    variant_id: str,
    dataset: Optional[str] = "gnomad_r4",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get per-ancestry (population-stratified) allele frequencies for a variant from gnomAD by `variant...

    Parameters
    ----------
    variant_id : str
        Variant ID (format 'chrom-pos-ref-alt', e.g., '1-55051215-G-GA').
    dataset : str
        gnomAD dataset ID. Allowed values: gnomad_r4, gnomad_r4_non_ukb, gnomad_r3, g...
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
        for k, v in {"variant_id": variant_id, "dataset": dataset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_variant_populations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_variant_populations"]
