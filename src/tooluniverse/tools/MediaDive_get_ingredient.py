"""
MediaDive_get_ingredient

Retrieve one MediaDive ingredient's chemical identifiers, synonyms, and how widely it is used. Ex...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MediaDive_get_ingredient(
    ingredient_id: str | int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one MediaDive ingredient's chemical identifiers, synonyms, and how widely it is used. Ex...

    Parameters
    ----------
    ingredient_id : str | int
        MediaDive ingredient identifier, e.g. 3.
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
    _args = {k: v for k, v in {"ingredient_id": ingredient_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "MediaDive_get_ingredient",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MediaDive_get_ingredient"]
