"""
ModelDB_get_paper

Get details of a scientific paper referenced in ModelDB by its paper ID. Returns the paper title,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ModelDB_get_paper(
    paper_id: int,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get details of a scientific paper referenced in ModelDB by its paper ID. Returns the paper title,...

    Parameters
    ----------
    paper_id : int
        Numeric paper ID from ModelDB. Examples: 4307 (Migliore et al 1995), 3860 (Ho...
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
    _args = {k: v for k, v in {"paper_id": paper_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ModelDB_get_paper",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ModelDB_get_paper"]
