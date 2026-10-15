"""
BioThings_get_metadata

Describe a BioThings API: record counts, build date and version, upstream sources, and optionally...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioThings_get_metadata(
    api: str,
    include_fields: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Describe a BioThings API: record counts, build date and version, upstream sources, and optionally...

    Parameters
    ----------
    api : str
        API slug, e.g. 'semmeddb'. See BioThings_list_apis.
    include_fields : bool
        If true, also fetch the full list of queryable field names.
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
        for k, v in {"api": api, "include_fields": include_fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioThings_get_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioThings_get_metadata"]
