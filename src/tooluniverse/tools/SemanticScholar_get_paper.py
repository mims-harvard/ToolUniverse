"""
SemanticScholar_get_paper

Get detailed metadata for a specific paper from Semantic Scholar by paper ID, DOI, PubMed ID, or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_get_paper(
    paper_id: str,
    fields: Optional[
        str
    ] = "paperId,title,abstract,tldr,year,citationCount,referenceCount,openAccessPdf,journal,publicationTypes,externalIds,authors,publicationDate,fieldsOfStudy",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed metadata for a specific paper from Semantic Scholar by paper ID, DOI, PubMed ID, or ...

    Parameters
    ----------
    paper_id : str
        Paper identifier. Supports multiple formats: Semantic Scholar ID (e.g., '68d9...
    fields : str
        Comma-separated list of fields to return. Available: paperId,title,abstract,y...
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
        for k, v in {"paper_id": paper_id, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_get_paper",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_get_paper"]
