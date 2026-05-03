"""
NCBI_get_sequence

Retrieve DNA/RNA sequence data from NCBI by accession number. Returns sequences in specified form...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_get_sequence(
    accession: str,
    operation: Optional[str] = None,
    format: Optional[str] = "fasta",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Retrieve DNA/RNA sequence data from NCBI by accession number. Returns sequences in specified form...

    Parameters
    ----------
    operation : str
        Operation type (fixed: fetch_sequence)
    accession : str
        NCBI accession number (e.g., 'U00096', 'NC_045512', 'NM_000546'). Works with ...
    format : str
        Sequence format: 'fasta' for FASTA, 'gb' for GenBank, 'embl' for EMBL, 'gp' f...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
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
            "name": "NCBI_get_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_get_sequence"]
