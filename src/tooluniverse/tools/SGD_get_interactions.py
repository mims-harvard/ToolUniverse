"""
SGD_get_interactions

Get genetic and physical interactions for a yeast gene from SGD. Returns interaction type (Physic...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SGD_get_interactions(
    sgd_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get genetic and physical interactions for a yeast gene from SGD. Returns interaction type (Physic...

    Parameters
    ----------
    sgd_id : str
        SGD locus identifier. Examples: 'S000003219' (RMR1), 'S000005564' (ACT1), 'S0...
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
    _args = {k: v for k, v in {"sgd_id": sgd_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SGD_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SGD_get_interactions"]
