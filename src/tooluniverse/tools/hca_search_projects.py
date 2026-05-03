"""
hca_search_projects

Searches for single-cell projects in the Human Cell Atlas (HCA) Data Coordination Platform (DCP)....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def hca_search_projects(
    action: str,
    organ: Optional[str] = None,
    disease: Optional[str] = None,
    limit: Optional[int] = 10,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Searches for single-cell projects in the Human Cell Atlas (HCA) Data Coordination Platform (DCP)....

    Parameters
    ----------
    action : str
        The specific action to perform. Must be set to 'search_projects'.
    organ : str
        The organ to filter projects by. Examples include 'heart', 'liver', 'brain', ...
    disease : str
        The disease state to filter by. Examples include 'normal', 'cancer', 'covid-1...
    limit : int
        The maximum number of projects to return. The default is 10. Use this to cont...
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
            "action": action,
            "organ": organ,
            "disease": disease,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "hca_search_projects",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["hca_search_projects"]
