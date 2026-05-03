"""
euhealthinfo_search_primary_care_workforce

This tool is designed to conduct metadata searches for datasets related to the primary-care workf...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def euhealthinfo_search_primary_care_workforce(
    limit: Optional[int] = 25,
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
    This tool is designed to conduct metadata searches for datasets related to the primary-care workf...

    Parameters
    ----------
    limit : int
        Maximum number of results to return. Default 25.
    country : str
        Country filter. Accepts full names (e.g., 'Germany') or ISO-3166 codes ('DE',...
    language : str
        Language filter. Accepts ISO 639-1 codes (e.g., 'en') or full names (e.g., 'E...
    term_override : str
        Override the default topic seed terms with a custom query string. Defaults in...
    method : str
        Search strategy: 'keyword' (text only), 'embedding' (vector), or 'hybrid' (bl...
    alpha : float
        Blend ratio used when method='hybrid' (0=text, 1=embedding).
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
            "limit": limit,
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
            "name": "euhealthinfo_search_primary_care_workforce",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["euhealthinfo_search_primary_care_workforce"]
