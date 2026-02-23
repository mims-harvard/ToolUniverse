"""
FDA_search_drug_labels

Search FDA-approved drug labels (prescribing information) by drug name or medical indication. Dru...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FDA_search_drug_labels(
    limit: int,
    drug_name: Optional[str | Any] = None,
    indication: Optional[str | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search FDA-approved drug labels (prescribing information) by drug name or medical indication. Dru...

    Parameters
    ----------
    drug_name : str | Any
        Brand or generic drug name to search (e.g., 'metformin', 'atorvastatin', 'lis...
    indication : str | Any
        Medical condition to search in indications sections (e.g., 'hypertension', 't...
    limit : int
        Maximum number of results to return (default: 5, max: 20)
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
            "name": "FDA_search_drug_labels",
            "arguments": {
                "drug_name": drug_name,
                "indication": indication,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FDA_search_drug_labels"]
