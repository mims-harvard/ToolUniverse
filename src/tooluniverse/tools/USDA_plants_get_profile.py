"""
USDA_plants_get_profile

Get a USDA PLANTS Database profile for a plant by its PLANTS symbol (e.g. 'ABBA' = balsam fir): s...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USDA_plants_get_profile(
    symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a USDA PLANTS Database profile for a plant by its PLANTS symbol (e.g. 'ABBA' = balsam fir): s...

    Parameters
    ----------
    symbol : str
        USDA PLANTS symbol, e.g. 'ABBA' (balsam fir), 'ACRU' (red maple), 'QUAL' (whi...
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
    _args = {k: v for k, v in {"symbol": symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USDA_plants_get_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USDA_plants_get_profile"]
