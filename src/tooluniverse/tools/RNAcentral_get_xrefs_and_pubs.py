"""
RNAcentral_get_xrefs_and_pubs

Get paginated cross-references and literature for an RNAcentral entry in one call. xrefs_page and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RNAcentral_get_xrefs_and_pubs(
    accession: str,
    page_size: Optional[int] = 10,
    xrefs_page: Optional[int] = 1,
    publications_page: Optional[int] = 1,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get paginated cross-references and literature for an RNAcentral entry in one call. xrefs_page and...

    Parameters
    ----------
    accession : str
        RNAcentral URS identifier (e.g., 'URS000063A371', 'URS000075C808').
    page_size : int
        Records per sub-resource page (1-50).
    xrefs_page : int
        One-based xref page; continue with data.xrefs.next_page.
    publications_page : int
        One-based publication page; continue with data.publications.next_page.
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
            "accession": accession,
            "page_size": page_size,
            "xrefs_page": xrefs_page,
            "publications_page": publications_page,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RNAcentral_get_xrefs_and_pubs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RNAcentral_get_xrefs_and_pubs"]
