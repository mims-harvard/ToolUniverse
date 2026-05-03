"""
GNPS_compare_spectra

Compare two MS/MS spectra from the GNPS spectral library using Universal Spectrum Identifiers (US...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GNPS_compare_spectra(
    usi1: str,
    usi2: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compare two MS/MS spectra from the GNPS spectral library using Universal Spectrum Identifiers (US...

    Parameters
    ----------
    usi1 : str
        First spectrum USI. Example: 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005...
    usi2 : str
        Second spectrum USI. Example: 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB0000...
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
    _args = {k: v for k, v in {"usi1": usi1, "usi2": usi2}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "GNPS_compare_spectra",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GNPS_compare_spectra"]
