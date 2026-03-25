"""
KEGG_get_variant

Get detailed KEGG variant information including gene name, mutation type (gain/loss of function),...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_get_variant(
    variant_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed KEGG variant information including gene name, mutation type (gain/loss of function),...

    Parameters
    ----------
    variant_id : str
        KEGG variant ID. Can be with prefix 'hsa_var:673v1' or without '673v1'. Get I...
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
    _args = {k: v for k, v in {"variant_id": variant_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_get_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_get_variant"]
