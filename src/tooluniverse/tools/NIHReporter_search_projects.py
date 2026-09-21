"""
NIHReporter_search_projects

Full-text search NIH RePORTER, NIH's public database of ~3 million funded research projects since...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NIHReporter_search_projects(
    query: str,
    fiscal_year: Optional[int] = None,
    organization: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Full-text search NIH RePORTER, NIH's public database of ~3 million funded research projects since...

    Parameters
    ----------
    query : str
        Free-text search over title, terms, and abstract, e.g. 'CRISPR gene editing'.
    fiscal_year : int
        Optional NIH fiscal year filter, e.g. 2024.
    organization : str
        Optional grantee institution filter, e.g. 'Broad Institute'.
    limit : int
        Max projects to return, 1-100. Default 25.
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
            "query": query,
            "fiscal_year": fiscal_year,
            "organization": organization,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NIHReporter_search_projects",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NIHReporter_search_projects"]
