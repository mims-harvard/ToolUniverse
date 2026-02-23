"""
TCIA_get_series_size

Get the total file size and image count for a specific imaging series in The Cancer Imaging Archi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_series_size(
    SeriesInstanceUID: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the total file size and image count for a specific imaging series in The Cancer Imaging Archi...

    Parameters
    ----------
    SeriesInstanceUID : str
        DICOM Series Instance UID. Example: '1.3.6.1.4.1.14519.5.2.1.6279.6001.100225...
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
            "name": "TCIA_get_series_size",
            "arguments": {"SeriesInstanceUID": SeriesInstanceUID},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_series_size"]
