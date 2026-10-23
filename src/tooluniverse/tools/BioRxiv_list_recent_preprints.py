"""
BioRxiv_list_recent_preprints

List bioRxiv or medRxiv preprints by date range. The live API currently returns 30 records per ba...
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
    List bioRxiv or medRxiv preprints by date range. The live API currently returns 30 records per ba...

    Parameters
    ----------
    start_date : str
        Inclusive start date in YYYY-MM-DD format (e.g., '2024-01-01').
    end_date : str
        Inclusive end date in YYYY-MM-DD format (e.g., '2024-01-03'); must not preced...
    server : str
        Server: 'biorxiv' for biology preprints, 'medrxiv' for health sciences preprints
    cursor : int
        Zero-based record offset. Start at 0, then use metadata.next_cursor; do not a...
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
            "start_date": start_date,
            "end_date": end_date,
            "server": server,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "BioRxiv_list_recent_preprints",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioRxiv_list_recent_preprints"]
