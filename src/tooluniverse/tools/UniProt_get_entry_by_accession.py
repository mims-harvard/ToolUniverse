"""
UniProt_get_entry_by_accession

Get a UniProtKB entry plus its separate Publications-view bibliography. By default this returns e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProt_get_entry_by_accession(
    accession: str,
    compact: Optional[bool] = True,
    include_publications: Optional[bool] = True,
    publication_source: Optional[str] = "computational",
    publication_limit: Optional[int] = 25,
    publication_cursor: Optional[str] = None,
    comment_limit: Optional[int] = 25,
    comment_offset: Optional[int] = 0,
    feature_limit: Optional[int] = 100,
    feature_offset: Optional[int] = 0,
    reference_limit: Optional[int] = 25,
    reference_offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a UniProtKB entry plus its separate Publications-view bibliography. By default this returns e...

    Parameters
    ----------
    accession : str
        UniProtKB entry accession, e.g., P05067.
    compact : bool
        Return a bounded summary instead of the complete UniProtKB JSON entry. Defaul...
    include_publications : bool
        Also query UniProt's per-entry publications endpoint, which includes computat...
    publication_source : str
        Publication source filter. Default: computational, the bibliography class omi...
    publication_limit : int
        Maximum additional publications per page.
    publication_cursor : str
        Opaque cursor from metadata.next_publication_cursor. Omit for the first page.
    comment_limit : int
        Maximum compact-view comments to return.
    comment_offset : int
        Zero-based offset into all entry comments.
    feature_limit : int
        Maximum compact-view features to return; each feature retains its complete ne...
    feature_offset : int
        Zero-based offset into all entry features.
    reference_limit : int
        Maximum compact-view curated entry references to return.
    reference_offset : int
        Zero-based offset into all curated entry references.
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
            "compact": compact,
            "include_publications": include_publications,
            "publication_source": publication_source,
            "publication_limit": publication_limit,
            "publication_cursor": publication_cursor,
            "comment_limit": comment_limit,
            "comment_offset": comment_offset,
            "feature_limit": feature_limit,
            "feature_offset": feature_offset,
            "reference_limit": reference_limit,
            "reference_offset": reference_offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "UniProt_get_entry_by_accession",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProt_get_entry_by_accession"]
