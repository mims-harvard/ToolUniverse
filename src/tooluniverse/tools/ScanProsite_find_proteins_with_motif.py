"""
ScanProsite_find_proteins_with_motif

Reverse PROSITE motif scan: given a PROSITE signature accession (e.g., PS00029 for LEUCINE_ZIPPER...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ScanProsite_find_proteins_with_motif(
    signature_ac: str,
    db: Optional[str] = "sprot",
    skip_frequent: Optional[bool] = True,
    max_results: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Reverse PROSITE motif scan: given a PROSITE signature accession (e.g., PS00029 for LEUCINE_ZIPPER...

    Parameters
    ----------
    signature_ac : str
        PROSITE signature accession starting with 'PS'. Examples: 'PS00029' (LEUCINE_...
    db : str
        Sequence database to search: 'sprot' = Swiss-Prot (reviewed, default), 'tremb...
    skip_frequent : bool
        If true (default), skip very frequent low-information signatures (SKIP-FLAG=T...
    max_results : int
        Maximum number of matching protein records to return (default 50, max 1000). ...
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
            "signature_ac": signature_ac,
            "db": db,
            "skip_frequent": skip_frequent,
            "max_results": max_results,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ScanProsite_find_proteins_with_motif",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ScanProsite_find_proteins_with_motif"]
