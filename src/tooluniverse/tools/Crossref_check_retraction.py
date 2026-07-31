"""
Crossref_check_retraction

Check whether a published paper (by DOI) has been retracted, withdrawn, corrected, or flagged wit...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Crossref_check_retraction(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Check whether a published paper (by DOI) has been retracted, withdrawn, corrected, or flagged wit...

    Parameters
    ----------
    doi : str
        The DOI of the paper to check, e.g. '10.1016/S0140-6736(97)11096-0'. A full h...
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
    _args = {k: v for k, v in {"doi": doi}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "Crossref_check_retraction",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Crossref_check_retraction"]
