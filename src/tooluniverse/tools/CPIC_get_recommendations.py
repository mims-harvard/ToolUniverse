"""
CPIC_get_recommendations

Get drug dosing recommendations from a specific CPIC pharmacogenomic guideline. Returns clinicall...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_get_recommendations(
    guideline_id: int,
    limit: Optional[int | Any] = None,
    offset: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get drug dosing recommendations from a specific CPIC pharmacogenomic guideline. Returns clinicall...

    Parameters
    ----------
    guideline_id : int
        CPIC guideline numeric ID (e.g., 100421 for HLA-B/abacavir, 100414 for CYP2D6...
    limit : int | Any
        Maximum number of recommendations to return (default 50)
    offset : int | Any
        Number of recommendations to skip for pagination (default 0)
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

    return get_shared_client().run_one_function(
        {
            "name": "CPIC_get_recommendations",
            "arguments": {
                "guideline_id": guideline_id,
                "limit": limit,
                "offset": offset,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_get_recommendations"]
