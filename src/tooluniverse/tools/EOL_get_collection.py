"""
EOL_get_collection

Get a curated collection from the Encyclopedia of Life. EOL collections are user-curated lists of...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EOL_get_collection(
    collection_id: int,
    page: Optional[int] = 1,
    per_page: Optional[int] = 50,
    filter: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a curated collection from the Encyclopedia of Life. EOL collections are user-curated lists of...

    Parameters
    ----------
    collection_id : int
        EOL collection ID. Example: 176 (Fingertip Fauna), 6 (a sample collection).
    page : int
        Page number for paginated results.
    per_page : int
        Number of items per page (max 500).
    filter : str
        Filter items by type: 'taxa', 'text', 'image', 'sound', 'video', 'collection'...
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

    return get_shared_client().run_one_function(
        {
            "name": "EOL_get_collection",
            "arguments": {
                "collection_id": collection_id,
                "page": page,
                "per_page": per_page,
                "filter": filter,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EOL_get_collection"]
