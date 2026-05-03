"""
euhealthinfo_deepdive

This tool identifies and retrieves relevant links related to publicly accessible datasets and inf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def euhealthinfo_deepdive(
    uuids: Optional[list[str]] = None,
    topic: Optional[str] = None,
    limit: Optional[int] = 10,
    links_per: Optional[int] = 3,
    country: Optional[str] = None,
    language: Optional[str] = None,
    term_override: Optional[str] = None,
    method: Optional[str] = "hybrid",
    alpha: Optional[float] = 0.5,
    top_k: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    This tool identifies and retrieves relevant links related to publicly accessible datasets and inf...

    Parameters
    ----------
    uuids : list[str]
        Dataset UUIDs to deep-dive (format 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'). I...
    topic : str
        Topic name to resolve seeds from (e.g., 'euhealthinfo_search_cancer'). Used w...
    limit : int
        Maximum number of datasets to resolve when using 'topic'. Default 10.
    links_per : int
        Maximum number of outgoing links to classify per dataset. Default 3.
    country : str
        Country filter applied when resolving seeds from 'topic'. Accepts full names ...
    language : str
        Language filter applied when resolving seeds from 'topic'. Accepts ISO 639-1 ...
    term_override : str
        Overrides the default topic seed terms with a custom query string when using ...
    method : str
        Search strategy used when resolving from topic (ignored if 'uuids' are given).
    alpha : float
        Blend ratio used when method='hybrid'.
    top_k : int
        Number of candidate documents to retrieve before filtering.
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
            "uuids": uuids,
            "topic": topic,
            "limit": limit,
            "links_per": links_per,
            "country": country,
            "language": language,
            "term_override": term_override,
            "method": method,
            "alpha": alpha,
            "top_k": top_k,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "euhealthinfo_deepdive",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["euhealthinfo_deepdive"]
