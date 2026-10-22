"""
FDA_search_drug_labels

Search FDA-approved drug labels by drug name or indication. Results use native openFDA pagination...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_search_drug_labels(
    drug_name: Optional[str] = None,
    indication: Optional[str] = None,
    limit: Optional[int] = 5,
    offset: Optional[int] = 0,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA-approved drug labels by drug name or indication. Results use native openFDA pagination...

    Parameters
    ----------
    drug_name : str
        Brand or generic drug name to search (e.g., 'metformin', 'atorvastatin', 'lis...
    indication : str
        Medical condition to search in indications sections (e.g., 'hypertension', 't...
    limit : int
        Maximum number of results to return (default: 5, max: 20)
    offset : int
        Zero-based label offset. Continue with metadata.next_offset while metadata.ha...
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
            "drug_name": drug_name,
            "indication": indication,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "FDA_search_drug_labels",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_search_drug_labels"]
