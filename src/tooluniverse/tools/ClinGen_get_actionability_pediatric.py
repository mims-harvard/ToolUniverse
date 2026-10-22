"""
ClinGen_get_actionability_pediatric

Get ClinGen clinical actionability curations for pediatric context, including actionable findings...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ClinGen_get_actionability_pediatric(
    gene: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get ClinGen clinical actionability curations for pediatric context, including actionable findings...

    Parameters
    ----------
    gene : str
        Optional: Filter by gene symbol
    limit : int
        Maximum curations per page.
    offset : int
        Zero-based curation offset. Continue with next_offset while has_more is true.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {"gene": gene, "limit": limit, "offset": offset}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ClinGen_get_actionability_pediatric",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ClinGen_get_actionability_pediatric"]
