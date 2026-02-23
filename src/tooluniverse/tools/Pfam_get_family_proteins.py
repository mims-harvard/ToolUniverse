"""
Pfam_get_family_proteins

Get proteins containing a specific Pfam domain, optionally filtered by species. Returns protein a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Pfam_get_family_proteins(
    pfam_accession: str,
    max_results: Optional[int] = 20,
    reviewed_only: Optional[bool] = True,
    tax_id: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get proteins containing a specific Pfam domain, optionally filtered by species. Returns protein a...

    Parameters
    ----------
    pfam_accession : str
        Pfam family accession. Examples: 'PF00001' (7tm_1 GPCR), 'PF00076' (RRM_1), '...
    max_results : int
        Maximum number of proteins to return (default 20, max 100).
    reviewed_only : bool
        If true (default), return only SwissProt-reviewed proteins. Set false for all...
    tax_id : str | Any
        NCBI taxonomy ID to filter by species. Examples: '9606' (human), '10090' (mou...
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
            "name": "Pfam_get_family_proteins",
            "arguments": {
                "pfam_accession": pfam_accession,
                "max_results": max_results,
                "reviewed_only": reviewed_only,
                "tax_id": tax_id,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Pfam_get_family_proteins"]
