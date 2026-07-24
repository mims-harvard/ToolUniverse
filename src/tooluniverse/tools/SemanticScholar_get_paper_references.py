"""
SemanticScholar_get_paper_references

List the papers that a given paper CITES (its reference list / bibliography), with per-reference ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SemanticScholar_get_paper_references(
    paper_id: str,
    fields: Optional[
        str
    ] = "intents,isInfluential,contexts,title,year,authors,citationCount,externalIds,openAccessPdf",
    limit: Optional[int] = 20,
    offset: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the papers that a given paper CITES (its reference list / bibliography), with per-reference ...

    Parameters
    ----------
    paper_id : str
        Paper identifier whose REFERENCES (cited papers) to list. Semantic Scholar ID...
    fields : str
        Comma-separated fields for each reference record. Citation-edge fields: inten...
    limit : int
        Maximum number of cited papers to return (default 20, max 1000).
    offset : int
        Pagination offset into the reference list (default 0).
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
            "paper_id": paper_id,
            "fields": fields,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SemanticScholar_get_paper_references",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SemanticScholar_get_paper_references"]
