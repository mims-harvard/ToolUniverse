"""
IDR_get_study_datasets

Get datasets (image collections) within a specific IDR imaging study. Each dataset within an IDR ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IDR_get_study_datasets(
    project_id: int,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get datasets (image collections) within a specific IDR imaging study. Each dataset within an IDR ...

    Parameters
    ----------
    project_id : int
        IDR project/study ID (e.g., 101). Obtain from IDR_list_studies.
    limit : int | Any
        Maximum number of datasets to return (default 25, max 1000)
    offset : int | Any
        Offset for pagination
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
    _args = {k: v for k, v in {
        "project_id": project_id,
                "limit": limit,
                "offset": offset
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "IDR_get_study_datasets",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["IDR_get_study_datasets"]
