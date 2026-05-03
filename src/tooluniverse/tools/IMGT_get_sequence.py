"""
IMGT_get_sequence

Get immunoglobulin/T cell receptor sequence from IMGT by accession number. IMGT is the reference ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IMGT_get_sequence(
    accession: str,
    operation: Optional[str] = None,
    format: Optional[str] = "fasta",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get immunoglobulin/T cell receptor sequence from IMGT by accession number. IMGT is the reference ...

    Parameters
    ----------
    operation : str

    accession : str
        IMGT/LIGM-DB accession or EMBL/GenBank accession
    format : str
        Output format: fasta or embl (default: fasta)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "operation": operation,
            "accession": accession,
            "format": format,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "IMGT_get_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IMGT_get_sequence"]
