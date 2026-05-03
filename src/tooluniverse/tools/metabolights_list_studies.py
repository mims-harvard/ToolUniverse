"""
metabolights_list_studies

List all MetaboLights studies with pagination. Returns a list of study IDs (e.g., 'MTBLS1', 'MTBL...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def metabolights_list_studies(
    size: Optional[int] = 20,
    page: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    List all MetaboLights studies with pagination. Returns a list of study IDs (e.g., 'MTBLS1', 'MTBL...

    Parameters
    ----------
    size : int
        Number of studies per page (default: 20)
    page : int
        Page number (default: 0)
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
    _args = {k: v for k, v in {"size": size, "page": page}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "metabolights_list_studies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["metabolights_list_studies"]
