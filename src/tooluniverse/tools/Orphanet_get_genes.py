"""
Orphanet_get_genes

Get genes associated with a rare disease from Orphanet. Returns gene symbols, names, and associat...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_genes(
    operation: Optional[str] = None,
    orpha_code: Optional[str | int] = None,
    orphacode: Optional[int | str] = None,
    orpha_id: Optional[int | str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get genes associated with a rare disease from Orphanet. Returns gene symbols, names, and associat...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_genes)
    orpha_code : str | int
        Orphanet ORPHA code for the disease
    orphacode : int | str
        Alias for orpha_code (the Orphanet disease code).
    orpha_id : int | str
        Alias for orpha_code (the Orphanet disease code).
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
        for k, v in {
            "operation": operation,
            "orpha_code": orpha_code,
            "orphacode": orphacode,
            "orpha_id": orpha_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Orphanet_get_genes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_genes"]
