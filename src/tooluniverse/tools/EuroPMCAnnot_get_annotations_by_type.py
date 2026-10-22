"""
EuroPMCAnnot_get_annotations_by_type

Get annotations of one type from multiple Europe PMC articles. All supplied article IDs are reque...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EuroPMCAnnot_get_annotations_by_type(
    article_ids: str,
    annotation_type: str,
    page_size: Optional[int] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get annotations of one type from multiple Europe PMC articles. All supplied article IDs are reque...

    Parameters
    ----------
    article_ids : str
        Comma-separated article identifiers. Format: 'PMC:PMCXXXXXXX' or 'MED:PMID'. ...
    annotation_type : str
        Annotation type to retrieve. Common values: 'Chemicals', 'Organisms', 'Gene O...
    page_size : int
        Upstream article page size. If omitted, the wrapper requests at least the num...
    limit : int
        Maximum number of annotations returned per article from the shared offset.
    offset : int
        Zero-based annotation offset applied independently within each returned article.
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
            "article_ids": article_ids,
            "annotation_type": annotation_type,
            "page_size": page_size,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EuroPMCAnnot_get_annotations_by_type",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EuroPMCAnnot_get_annotations_by_type"]
