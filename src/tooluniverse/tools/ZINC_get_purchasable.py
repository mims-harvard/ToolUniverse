"""
ZINC_get_purchasable

Browse ZINC compounds by purchasability tier. Returns compounds available at a specific availabil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_get_purchasable(
    operation: str,
    tier: str,
    count: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Browse ZINC compounds by purchasability tier. Returns compounds available at a specific availabil...

    Parameters
    ----------
    operation : str
        Operation type
    tier : str
        Purchasability tier. in-stock = ready to ship, for-sale = from vendor, on-dem...
    count : int
        Maximum number of results (default: 10, max: 100)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "ZINC_get_purchasable",
            "arguments": {"operation": operation, "tier": tier, "count": count},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_get_purchasable"]
