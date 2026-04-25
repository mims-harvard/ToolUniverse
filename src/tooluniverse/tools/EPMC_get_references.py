"""
EPMC_get_references

Get the reference list (bibliography) of a specific paper from Europe PMC. Given a PubMed ID (PMI...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EPMC_get_references(
    pmid: str,
    page: Optional[int] = 1,
    pageSize: Optional[int] = 25,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the reference list (bibliography) of a specific paper from Europe PMC. Given a PubMed ID (PMI...

    Parameters
    ----------
    pmid : str
        PubMed ID of the article whose references you want. Examples: '25378148', '33...
    page : int
        Page number for paginated results (1-based). Default: 1.
    pageSize : int
        Number of references to return per page (1-1000). Default: 25.
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
    _args = {k: v for k, v in {
        "pmid": pmid,
                "page": page,
                "pageSize": pageSize
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EPMC_get_references",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["EPMC_get_references"]
