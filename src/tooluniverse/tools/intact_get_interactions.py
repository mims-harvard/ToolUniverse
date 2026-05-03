"""
intact_get_interactions

Get all interactions involving a specific interactor (protein or gene) by identifier. Uses EBI Se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def intact_get_interactions(
    identifier: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get all interactions involving a specific interactor (protein or gene) by identifier. Uses EBI Se...

    Parameters
    ----------
    identifier : str
        IntAct identifier, UniProt ID, or gene name
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
        for k, v in {"identifier": identifier, "format": format}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "intact_get_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["intact_get_interactions"]
