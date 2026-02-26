"""
PROSITE_scan_sequence

Scan a raw protein amino acid sequence against all PROSITE patterns and profiles to find matching...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PROSITE_scan_sequence(
    sequence: str,
    skip_frequent: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Scan a raw protein amino acid sequence against all PROSITE patterns and profiles to find matching...

    Parameters
    ----------
    sequence : str
        Protein amino acid sequence in single-letter code (e.g., 'MKTAYIAKQRQ...'). M...
    skip_frequent : bool
        If true (default), skip frequent low-information patterns like glycosylation ...
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
            "name": "PROSITE_scan_sequence",
            "arguments": {"sequence": sequence, "skip_frequent": skip_frequent},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PROSITE_scan_sequence"]
