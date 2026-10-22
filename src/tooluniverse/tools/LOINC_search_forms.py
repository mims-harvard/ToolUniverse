"""
LOINC_search_forms

Search official available LOINC forms using NLM's type=form endpoint, including PHQ-9, GAD-7, and...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LOINC_search_forms(
    terms: str,
    max_results: Optional[int] = 20,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Search official available LOINC forms using NLM's type=form endpoint, including PHQ-9, GAD-7, and...

    Parameters
    ----------
    terms : str
        Search terms for clinical forms or survey instruments (e.g., 'PHQ-9', 'depres...
    max_results : int
        Page size (default 20, range 1-500).
    offset : int
        Zero-based first form. Continue with metadata.next_offset; offset + max_resul...
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
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LOINC_search_forms",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LOINC_search_forms"]
