"""
CryoET_list_tomograms

List tomographic reconstructions for a specific experimental run from the CryoET Data Portal. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CryoET_list_tomograms(
    operation: str,
    run_id: int,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List tomographic reconstructions for a specific experimental run from the CryoET Data Portal. Ret...

    Parameters
    ----------
    operation : str
        Operation type
    run_id : int
        Numeric run ID (e.g. 3430). Obtain from CryoET_list_runs.
    limit : int
        Maximum number of tomograms to return (default: 10).
    offset : int
        Number of tomograms to skip for pagination (default: 0).
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
        for k, v in {
            "operation": operation,
            "run_id": run_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CryoET_list_tomograms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CryoET_list_tomograms"]
