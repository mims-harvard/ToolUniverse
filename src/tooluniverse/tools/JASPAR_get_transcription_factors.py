"""
JASPAR_get_transcription_factors

List all JASPAR transcription factor binding profiles. Returns all matrices; does NOT support fil...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def JASPAR_get_transcription_factors(
    collection: Optional[str] = "CORE",
    page: Optional[int] = 1,
    page_size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all JASPAR transcription factor binding profiles. Returns all matrices; does NOT support fil...

    Parameters
    ----------
    collection : str
        JASPAR collection (e.g., CORE).
    page : int
        Page number (1-based).
    page_size : int
        Results per page (JASPAR `page_size`).
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
        k: v
        for k, v in {
            "collection": collection,
            "page": page,
            "page_size": page_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "JASPAR_get_transcription_factors",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["JASPAR_get_transcription_factors"]
