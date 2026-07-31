"""
ENCORI_scan_RBP_motifs

Scan RBP binding-motif enrichment via ENCORI (starBase) RBPMotifScan module. Provide 'motif' (e.g...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ENCORI_scan_RBP_motifs(
    motif: Optional[str] = None,
    rbp: Optional[str] = None,
    assembly: Optional[str] = None,
    length: Optional[str] = None,
    rank_limit: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Scan RBP binding-motif enrichment via ENCORI (starBase) RBPMotifScan module. Provide 'motif' (e.g...

    Parameters
    ----------
    motif : str
        RNA sequence motif to scan for (use U or T), e.g. 'UGCAUG'. Mutually exclusiv...
    rbp : str
        RNA-binding protein symbol whose motifs are wanted, e.g. 'MBNL2' (alias: 'RBP').
    assembly : str
        Genome assembly (default 'hg38').
    length : str
        Motif length class: 'short' (default) or 'long'.
    rank_limit : int
        Per-dataset motif rank cutoff sent to ENCORI (1-100, default 10).
    limit : int
        Maximum motif rows to return (1-500, default 100).
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
            "motif": motif,
            "rbp": rbp,
            "assembly": assembly,
            "length": length,
            "rank_limit": rank_limit,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ENCORI_scan_RBP_motifs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ENCORI_scan_RBP_motifs"]
