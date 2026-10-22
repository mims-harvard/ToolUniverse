"""
LOINC_search_tests

Search LOINC lab tests and clinical observations with the NLM Clinical Tables count+offset pagina...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOINC_search_tests(
    terms: str,
    max_results: Optional[int] = 20,
    offset: Optional[int] = 0,
    exclude_copyrighted: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search LOINC lab tests and clinical observations with the NLM Clinical Tables count+offset pagina...

    Parameters
    ----------
    terms : str
        Search terms for lab tests or observations (e.g., 'cholesterol', 'blood gluco...
    max_results : int
        Page size (default 20, range 1-500). Sent as count; maxList does not support ...
    offset : int
        Zero-based first result. Continue with metadata.next_offset; offset + max_res...
    exclude_copyrighted : bool
        Exclude items with external copyright notices (default: true)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "terms": terms,
            "max_results": max_results,
            "offset": offset,
            "exclude_copyrighted": exclude_copyrighted,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LOINC_search_tests",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOINC_search_tests"]
