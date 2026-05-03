"""
gnomad_get_variant

Get basic variant metadata from gnomAD by `variant_id` (format like '19-44908822-C-T'). Use `gnom...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_variant(
    variant_id: str,
    dataset: Optional[str] = "gnomad_r3",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get basic variant metadata from gnomAD by `variant_id` (format like '19-44908822-C-T'). Use `gnom...

    Parameters
    ----------
    variant_id : str
        Variant ID (e.g., '19-44908822-C-T').
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
    dict[str, Any]
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
            "name": "gnomad_get_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_variant"]
