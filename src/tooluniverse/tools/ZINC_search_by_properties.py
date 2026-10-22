"""
ZINC_search_by_properties

NOT SUPPORTED by ZINC22 (CartBlanche22): molecular-property-range search (filtering by MW / LogP ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_search_by_properties(
    operation: Optional[str] = "search_by_properties",
    mwt_min: Optional[float] = None,
    mwt_max: Optional[float] = None,
    logp_min: Optional[float] = None,
    logp_max: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    NOT SUPPORTED by ZINC22 (CartBlanche22): molecular-property-range search (filtering by MW / LogP ...

    Parameters
    ----------
    operation : str
        Operation type
    mwt_min : float
        Minimum molecular weight (NOTE: property-range search is not supported by Car...
    mwt_max : float
        Maximum molecular weight (not supported; see error)
    logp_min : float
        Minimum LogP (not supported; see error)
    logp_max : float
        Maximum LogP (not supported; see error)
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
            "operation": operation,
            "mwt_min": mwt_min,
            "mwt_max": mwt_max,
            "logp_min": logp_min,
            "logp_max": logp_max,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ZINC_search_by_properties",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_search_by_properties"]
