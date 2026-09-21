"""
NIHReporter_get_project

Retrieve one NIH-funded project by its project number or application id from NIH RePORTER: title,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NIHReporter_get_project(
    project_num: Optional[str] = None,
    appl_id: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve one NIH-funded project by its project number or application id from NIH RePORTER: title,...

    Parameters
    ----------
    project_num : str
        NIH project number, e.g. '5R21EB036298-03'.
    appl_id : int
        NIH application id, e.g. 11326711. Alternative to project_num.
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
        for k, v in {"project_num": project_num, "appl_id": appl_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NIHReporter_get_project",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NIHReporter_get_project"]
