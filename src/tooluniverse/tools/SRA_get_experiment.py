"""
SRA_get_experiment

Get detailed metadata for a specific SRA experiment by accession number. Returns experiment title...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SRA_get_experiment(
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific SRA experiment by accession number. Returns experiment title...

    Parameters
    ----------
    accession : str
        SRA accession number (e.g., 'SRX26927637', 'SRP000001', 'SRS000001')
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
    _args = {k: v for k, v in {"accession": accession}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "SRA_get_experiment",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SRA_get_experiment"]
