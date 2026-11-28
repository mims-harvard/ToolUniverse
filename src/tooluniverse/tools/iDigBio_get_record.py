"""
iDigBio_get_record

Retrieve a single iDigBio biodiversity specimen record by its GBIF occurrence key. Returns the cu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def iDigBio_get_record(
    occurrence_key: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve a single iDigBio biodiversity specimen record by its GBIF occurrence key. Returns the cu...

    Parameters
    ----------
    occurrence_key : str
        GBIF occurrence key of the record, a number such as '6158969750'. iDigBio_sea...
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"occurrence_key": occurrence_key}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "iDigBio_get_record",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["iDigBio_get_record"]
