"""
IDR_list_metadata_keys

List the curated metadata attribute keys available for searching the Image Data Resource (IDR), f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_list_metadata_keys(
    resource: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the curated metadata attribute keys available for searching the Image Data Resource (IDR), f...

    Parameters
    ----------
    resource : str
        Resource type whose metadata keys to list. Default 'image'. Other values: 'sc...
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
    _args = {k: v for k, v in {"resource": resource}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IDR_list_metadata_keys",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IDR_list_metadata_keys"]
