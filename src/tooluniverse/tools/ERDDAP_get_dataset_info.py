"""
ERDDAP_get_dataset_info

Get metadata and variable information for a specific ERDDAP dataset by its Dataset ID from NOAA C...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ERDDAP_get_dataset_info(
    datasetID: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata and variable information for a specific ERDDAP dataset by its Dataset ID from NOAA C...

    Parameters
    ----------
    datasetID : str
        ERDDAP dataset identifier. Examples: 'erdATssta8day' (AVHRR SST 8-day), 'goes...
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
    _args = {k: v for k, v in {"datasetID": datasetID}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ERDDAP_get_dataset_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ERDDAP_get_dataset_info"]
