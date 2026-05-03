"""
hca_get_file_manifest

Retrieves a list of downloadable files for a specific Human Cell Atlas (HCA) project identified b...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def hca_get_file_manifest(
    action: str,
    project_id: str,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieves a list of downloadable files for a specific Human Cell Atlas (HCA) project identified b...

    Parameters
    ----------
    action : str
        The specific action to perform. Must be set to 'get_file_manifest'.
    project_id : str
        The unique UUID of the project (entryId) for which to retrieve files. This ID...
    limit : int
        The maximum number of files to list. The default is 10.
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
        for k, v in {"action": action, "project_id": project_id, "limit": limit}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "hca_get_file_manifest",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["hca_get_file_manifest"]
