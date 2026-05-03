"""
CryoET_list_annotations

List biological annotations (segmentations, point annotations, surface meshes) for a specific cry...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CryoET_list_annotations(
    operation: str,
    run_id: int,
    curator_recommended_only: Optional[bool] = False,
    limit: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List biological annotations (segmentations, point annotations, surface meshes) for a specific cry...

    Parameters
    ----------
    operation : str
        Operation type
    run_id : int
        Numeric run ID (e.g. 3430). Obtain from CryoET_list_runs.
    curator_recommended_only : bool
        If true, return only curator-recommended high-quality annotations (default: f...
    limit : int
        Maximum number of annotations to return (default: 20).
    offset : int
        Number of annotations to skip for pagination (default: 0).
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
            "curator_recommended_only": curator_recommended_only,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CryoET_list_annotations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CryoET_list_annotations"]
