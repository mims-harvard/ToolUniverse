"""
USDA_plants_get_wetland_status

Get USACE wetland indicator status by geographic region for a plant from the USDA PLANTS Database...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def USDA_plants_get_wetland_status(
    symbol: Optional[str] = None,
    id: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get USACE wetland indicator status by geographic region for a plant from the USDA PLANTS Database...

    Parameters
    ----------
    symbol : str
        USDA PLANTS symbol, e.g. 'TYLA' (Typha latifolia / common cattail). Resolved ...
    id : int
        Numeric USDA PLANTS Id (e.g. 27001). Use instead of 'symbol' if known.
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
    _args = {k: v for k, v in {"symbol": symbol, "id": id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "USDA_plants_get_wetland_status",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["USDA_plants_get_wetland_status"]
