"""
RGD_resolve_symbol_or_region

Resolve a rat gene symbol to its native RGD record/ID, or list genes overlapping a genomic region...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RGD_resolve_symbol_or_region(
    symbol: Optional[str] = None,
    species_type_key: Optional[int] = None,
    chromosome: Optional[str] = None,
    start: Optional[int] = None,
    stop: Optional[int] = None,
    map_key: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a rat gene symbol to its native RGD record/ID, or list genes overlapping a genomic region...

    Parameters
    ----------
    symbol : str
        Rat gene symbol, e.g. 'Tp53'. Use this for symbol mode.
    species_type_key : int
        Species type key for symbol mode (default 3=rat, 1=human, 2=mouse).
    chromosome : str
        Chromosome for region mode, e.g. '10'.
    start : int
        Region start (region mode).
    stop : int
        Region stop (region mode).
    map_key : int
        Assembly map key for region mode (e.g. 360 for rat rn7).
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
        for k, v in {
            "symbol": symbol,
            "species_type_key": species_type_key,
            "chromosome": chromosome,
            "start": start,
            "stop": stop,
            "map_key": map_key,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RGD_resolve_symbol_or_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RGD_resolve_symbol_or_region"]
