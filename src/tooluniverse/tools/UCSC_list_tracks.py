"""
UCSC_list_tracks

Discover available UCSC Genome Browser annotation tracks for a genome assembly, and inspect a tra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UCSC_list_tracks(
    genome: str,
    track: Optional[str] = None,
    name_filter: Optional[str] = None,
    max_tracks: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Discover available UCSC Genome Browser annotation tracks for a genome assembly, and inspect a tra...

    Parameters
    ----------
    genome : str
        UCSC genome assembly identifier. Examples: 'hg38', 'hg19', 'mm39', 'mm10', 'd...
    track : str
        Optional. When set, return this track's column schema instead of the track li...
    name_filter : str
        Optional substring filter (case-insensitive) applied to track name/shortLabel...
    max_tracks : int
        Maximum number of tracks to return when listing (default 500). The total matc...
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
            "genome": genome,
            "track": track,
            "name_filter": name_filter,
            "max_tracks": max_tracks,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UCSC_list_tracks",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UCSC_list_tracks"]
