"""
gnomad_get_sv_detail

Get detailed information for a specific gnomAD structural variant by its ID (e.g., DEL_chr17_24e4...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_sv_detail(
    variant_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific gnomAD structural variant by its ID (e.g., DEL_chr17_24e4...

    Parameters
    ----------
    variant_id : str
        gnomAD structural variant ID (e.g., 'DEL_chr17_24e4872b', 'DUP_chr22_abc12345').
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

    return get_shared_client().run_one_function(
        {"name": "gnomad_get_sv_detail", "arguments": {"variant_id": variant_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_sv_detail"]
