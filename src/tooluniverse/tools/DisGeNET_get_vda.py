"""
DisGeNET_get_vda

Get variant-disease associations from DisGeNET. Query by rsID or gene symbol to find disease-asso...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DisGeNET_get_vda(
    operation: str,
    variant: Optional[str] = None,
    gene: Optional[str] = None,
    limit: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get variant-disease associations from DisGeNET. Query by rsID or gene symbol to find disease-asso...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_vda)
    variant : str
        Variant rsID (e.g., rs1234) - optional if gene provided
    gene : str
        Gene symbol to get all variants - optional if variant provided
    limit : int
        Maximum results (default: 25)
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
        {
            "name": "DisGeNET_get_vda",
            "arguments": {
                "operation": operation,
                "variant": variant,
                "gene": gene,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DisGeNET_get_vda"]
