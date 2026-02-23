"""
TCIA_get_series_metadata

Get detailed DICOM metadata for a specific imaging series in TCIA by its Series Instance UID. Ret...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_series_metadata(
    SeriesInstanceUID: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed DICOM metadata for a specific imaging series in TCIA by its Series Instance UID. Ret...

    Parameters
    ----------
    SeriesInstanceUID : str
        DICOM Series Instance UID (e.g., '1.3.6.1.4.1.14519.5.2.1.6279.6001.141365756...
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
            "name": "TCIA_get_series_metadata",
            "arguments": {"SeriesInstanceUID": SeriesInstanceUID},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_series_metadata"]
