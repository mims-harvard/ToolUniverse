"""
DNA_translate_reading_frames

Translate a DNA sequence to protein in all 3 forward reading frames and identify the longest ORF....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_translate_reading_frames(
    operation: str,
    sequence: str,
    frame: Optional[str | Any] = "all",
    genetic_code: Optional[int | Any] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Translate a DNA sequence to protein in all 3 forward reading frames and identify the longest ORF....

    Parameters
    ----------
    operation : str
        Operation type
    sequence : str
        DNA sequence (A, T, G, C only). Case insensitive. Spaces and newlines are str...
    frame : str | Any
        Reading frame to translate: '1', '2', '3', or 'all' (default). Frame 1 starts...
    genetic_code : int | Any
        NCBI genetic code number. Currently only 1 (standard) is supported.
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
            "operation": operation,
            "sequence": sequence,
            "frame": frame,
            "genetic_code": genetic_code,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_translate_reading_frames",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_translate_reading_frames"]
