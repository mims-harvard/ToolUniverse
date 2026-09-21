"""
OSDR_list_files

List the downloadable data files for one NASA OSDR study: raw and processed files across assay ty...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OSDR_list_files(
    study_id: str,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the downloadable data files for one NASA OSDR study: raw and processed files across assay ty...

    Parameters
    ----------
    study_id : str
        OSDR study accession, e.g. 'OSD-1' or '1'.
    limit : int
        Max files to return, 1-200. Default 50.
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
        k: v for k, v in {"study_id": study_id, "limit": limit}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OSDR_list_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OSDR_list_files"]
