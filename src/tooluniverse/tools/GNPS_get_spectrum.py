"""
GNPS_get_spectrum

Retrieve a mass spectrometry (MS/MS) reference spectrum from the GNPS spectral library using a Un...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GNPS_get_spectrum(
    usi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve a mass spectrometry (MS/MS) reference spectrum from the GNPS spectral library using a Un...

    Parameters
    ----------
    usi : str
        Universal Spectrum Identifier. Format: 'mzspec:GNPS:GNPS-LIBRARY:accession:CC...
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
    _args = {k: v for k, v in {"usi": usi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GNPS_get_spectrum",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GNPS_get_spectrum"]
