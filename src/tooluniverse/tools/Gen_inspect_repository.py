"""
Gen_inspect_repository

Inspect bounded metadata in an existing local Gen genome version control repository. List the act...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Gen_inspect_repository(
    repository_path: str,
    view: str,
    branch: Optional[str] = None,
    limit: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Inspect bounded metadata in an existing local Gen genome version control repository. List the act...

    Parameters
    ----------
    repository_path : str
        A path to an existing Gen workspace, relative to TOOLUNIVERSE_GEN_ROOT. The w...
    view : str
        Metadata to inspect: branches and current branch state, recent operation hist...
    branch : str
        Optional branch name for the operations view. Omit to inspect the checked-out...
    limit : int
        Maximum number of branch, operation, or sample records to return.
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
            "repository_path": repository_path,
            "view": view,
            "branch": branch,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Gen_inspect_repository",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Gen_inspect_repository"]
