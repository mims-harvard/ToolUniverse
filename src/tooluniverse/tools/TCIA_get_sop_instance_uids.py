"""
TCIA_get_sop_instance_uids

List the SOP Instance UIDs of every individual DICOM image (slice) within a TCIA imaging series. ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def TCIA_get_sop_instance_uids(
    SeriesInstanceUID: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the SOP Instance UIDs of every individual DICOM image (slice) within a TCIA imaging series. ...

    Parameters
    ----------
    SeriesInstanceUID : str
        DICOM Series Instance UID. Example: '1.3.6.1.4.1.14519.5.2.1.6279.6001.179049...
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
        for k, v in {"SeriesInstanceUID": SeriesInstanceUID}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "TCIA_get_sop_instance_uids",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["TCIA_get_sop_instance_uids"]
