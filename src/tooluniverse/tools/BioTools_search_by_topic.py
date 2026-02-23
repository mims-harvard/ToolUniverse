"""
BioTools_search_by_topic

Search the ELIXIR Bio.tools registry for bioinformatics tools by EDAM scientific topic. Returns t...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def BioTools_search_by_topic(
    topic: str,
    page: Optional[int] = 1,
    size: Optional[int] = 10,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the ELIXIR Bio.tools registry for bioinformatics tools by EDAM scientific topic. Returns t...

    Parameters
    ----------
    topic : str
        EDAM topic name. Examples: 'Proteomics', 'Genomics', 'Transcriptomics', 'Stru...
    page : int
        Page number (1-based). Default: 1.
    size : int
        Results per page (1-50). Default: 10.
    format : str
        Response format. Must be 'json'.
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
            "name": "BioTools_search_by_topic",
            "arguments": {"topic": topic, "page": page, "size": size, "format": format},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["BioTools_search_by_topic"]
