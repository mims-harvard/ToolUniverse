"""
RxTerms_search_drugs

Drug-name autocomplete via the NLM Clinical Table Search Service (RxTerms). Given a partial or fu...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxTerms_search_drugs(
    terms: str,
    max_results: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Drug-name autocomplete via the NLM Clinical Table Search Service (RxTerms). Given a partial or fu...

    Parameters
    ----------
    terms : str
        Drug name or prefix to search, e.g. 'metformin', 'atorvas', 'insulin aspart'.
    max_results : int
        Maximum number of matches to return (default 20, max 500).
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
        for k, v in {"terms": terms, "max_results": max_results}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "RxTerms_search_drugs",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxTerms_search_drugs"]
