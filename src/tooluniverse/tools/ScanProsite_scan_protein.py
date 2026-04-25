"""
ScanProsite_scan_protein

Scan a protein against the PROSITE database of protein motifs, domains, and families. Given a Uni...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ScanProsite_scan_protein(
    seq: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Scan a protein against the PROSITE database of protein motifs, domains, and families. Given a Uni...

    Parameters
    ----------
    seq : str
        UniProt accession to scan for PROSITE motifs. Examples: 'P04637' (TP53, retur...
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
    _args = {k: v for k, v in {
        "seq": seq
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ScanProsite_scan_protein",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["ScanProsite_scan_protein"]
