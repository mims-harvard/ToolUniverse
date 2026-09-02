"""
FDA_get_drug_names_by_boxed_warning

Find drugs whose FDA label carries a boxed warning matching a phrase you supply. IMPORTANT -- `wa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_get_drug_names_by_boxed_warning(
    warning_text: str,
    indication: Optional[str] = None,
    limit: Optional[int] = None,
    skip: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Find drugs whose FDA label carries a boxed warning matching a phrase you supply. IMPORTANT -- `wa...

    Parameters
    ----------
    warning_text : str
        Phrase to find within the boxed_warning field, matched CONTIGUOUSLY and in or...
    indication : str
        Optional additional phrase, matched the same contiguous way against indicatio...
    limit : int
        Number of LABEL RECORDS to return (not distinct drugs).
    skip : int
        Number of label records to skip before this page. Deduplication runs per page...
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
            "warning_text": warning_text,
            "indication": indication,
            "limit": limit,
            "skip": skip,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_get_drug_names_by_boxed_warning",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_get_drug_names_by_boxed_warning"]
