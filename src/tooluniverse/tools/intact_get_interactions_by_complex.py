"""
intact_get_interactions_by_complex

Search for protein complexes in IntAct database using Complex Web Service. Accepts complex names ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def intact_get_interactions_by_complex(
    complex_id: str,
    size: Optional[int] = 25,
    first: Optional[int] = 0,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for protein complexes in IntAct database using Complex Web Service. Accepts complex names ...

    Parameters
    ----------
    complex_id : str
        Complex name (e.g., 'TP53', 'ndc80'), complex AC (e.g., 'CPX-915'), or gene name
    size : int
        Maximum number of results to return (default: 25, max: 100)
    first : int
        First result index for pagination (default: 0)
    format : str

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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "complex_id": complex_id,
            "size": size,
            "first": first,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "intact_get_interactions_by_complex",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["intact_get_interactions_by_complex"]
