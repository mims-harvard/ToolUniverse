"""
BioRxiv_list_recent_preprints

List recent bioRxiv or medRxiv preprints by date range. Returns up to 100 preprints posted betwee...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioRxiv_list_recent_preprints(
    start_date: str,
    end_date: str,
    server: Optional[str] = "biorxiv",
    cursor: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List recent bioRxiv or medRxiv preprints by date range. Returns up to 100 preprints posted betwee...

    Parameters
    ----------
    start_date : str
        Start date in YYYY-MM-DD format (e.g., '2024-01-01'). Date range must not exc...
    end_date : str
        End date in YYYY-MM-DD format (e.g., '2024-01-03'). Date range must not excee...
    server : str
        Server: 'biorxiv' for biology preprints, 'medrxiv' for health sciences preprints
    cursor : int
        Pagination cursor (0 for first 100 results, 100 for next 100, etc.)
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
            "name": "BioRxiv_list_recent_preprints",
            "arguments": {
                "start_date": start_date,
                "end_date": end_date,
                "server": server,
                "cursor": cursor,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioRxiv_list_recent_preprints"]
