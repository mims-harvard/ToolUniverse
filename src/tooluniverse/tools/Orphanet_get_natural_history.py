"""
Orphanet_get_natural_history

Get natural history data for a rare disease from Orphanet. Returns average age of onset and type ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Orphanet_get_natural_history(
    operation: str,
    orpha_code: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get natural history data for a rare disease from Orphanet. Returns average age of onset and type ...

    Parameters
    ----------
    operation : str
        Operation type (fixed: get_natural_history)
    orpha_code : str
        Orphanet ORPHA code (e.g., 558 for Marfan, 399 for Huntington)
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
            "name": "Orphanet_get_natural_history",
            "arguments": {"operation": operation, "orpha_code": orpha_code},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Orphanet_get_natural_history"]
