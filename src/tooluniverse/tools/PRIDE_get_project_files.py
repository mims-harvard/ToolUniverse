"""
PRIDE_get_project_files

Get the complete list of data files for a PRIDE Archive project including raw mass spectrometry f...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PRIDE_get_project_files(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get the complete list of data files for a PRIDE Archive project including raw mass spectrometry f...

    Parameters
    ----------
    accession : str
        PRIDE project accession identifier (format: PXD######, e.g., 'PXD000001'). Fi...
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "PRIDE_get_project_files",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PRIDE_get_project_files"]
